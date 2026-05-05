#include "SensorManager.h"
#include "max6675.h"
#include "INA226.h"
#include <Wire.h>
#include <math.h>

// ── Pin definitions (must match main.cpp) ─────────────────────────────────────
static const int PIN_SCK = 13;
static const int PIN_CS  = 12;
static const int PIN_SO  = 11;
static const int PIN_SDA = 15;
static const int PIN_SCL = 16;

// ── EZO-HUM constants ─────────────────────────────────────────────────────────
static const uint8_t  EZO_HUM_ADDR          = 0x6F;
static const uint32_t EZO_RESPONSE_DELAY_MS = 300;

// ── Sensor constants ──────────────────────────────────────────────────────────
static const float SUPPLY_VOLTAGE   = 12.0f;  // nominal PSU voltage used for power calc
static const float MAX_JUMP_C       = 100.0f; // glitch reject: max allowed single-tick jump
static const float STUCK_EPSILON_C  = 0.01f;  // below this delta → "same" reading
static const uint16_t STUCK_LIMIT   = 30;     // consecutive "same" ticks before stuck declared

// ── Differential pressure sensor ADC ─────────────────────────────────────────
// Set PIN_PRESSURE2 to 0 to disable channel 2 (leave unconnected).
static const int   PIN_PRESSURE1  = 6;       // GPIO for sensor 1 ADC input
static const int   PIN_PRESSURE2  = 7;       // GPIO for sensor 2 ADC input (0 = unused)
static const float P_R1           = 2200.0f; // voltage divider top resistor, Ω
static const float P_R2           = 5100.0f; // voltage divider bottom resistor, Ω
static const float P_DIV_GAIN     = P_R2 / (P_R1 + P_R2); // ~0.6986
static const float P_VREF         = 3.3f;    // ADC reference voltage
static const int   P_N_SAMPLES    = 32;      // oversampling count
static const float P_EMA_ALPHA    = 0.15f;   // EMA smoothing factor

// ── Sensor objects ────────────────────────────────────────────────────────────
static MAX6675 thermocouple(PIN_SCK, PIN_CS, PIN_SO);
static INA226  ina226(0x40);

// ── Singleton instance ────────────────────────────────────────────────────────
SensorManager sensors;

// ── Public methods ────────────────────────────────────────────────────────────

void SensorManager::begin(float emaAlphaInit) {
    _emaAlpha = emaAlphaInit;

    Wire.begin(PIN_SDA, PIN_SCL);

    // EZO-HUM: enable temperature output, disable dew point (sent once at boot)
    Wire.beginTransmission(EZO_HUM_ADDR);
    Wire.write("O,T,1\r");
    Wire.endTransmission();
    delay(300);
    Wire.beginTransmission(EZO_HUM_ADDR);
    Wire.write("O,Dew,0\r");
    Wire.endTransmission();
    delay(300);

    // Configure ADC pins for pressure sensors (11dB = 0-3.3V range)
    analogReadResolution(12);
    if (PIN_PRESSURE1 > 0) analogSetPinAttenuation(PIN_PRESSURE1, ADC_11db);
    if (PIN_PRESSURE2 > 0) analogSetPinAttenuation(PIN_PRESSURE2, ADC_11db);

    // Seed EMA with first pressure reading so filter starts from a real value
    if (PIN_PRESSURE1 > 0) {
        uint32_t acc = 0;
        for (int i = 0; i < P_N_SAMPLES; i++) { acc += analogRead(PIN_PRESSURE1); }
        float vPin = ((float)acc / P_N_SAMPLES) / 4095.0f * P_VREF;
        float vSens = vPin / P_DIV_GAIN;
        _emaP1 = 3500.0f * constrain((vSens - 0.25f) / 3.75f, 0.0f, 1.0f);
    }
    if (PIN_PRESSURE2 > 0) {
        uint32_t acc = 0;
        for (int i = 0; i < P_N_SAMPLES; i++) { acc += analogRead(PIN_PRESSURE2); }
        float vPin = ((float)acc / P_N_SAMPLES) / 4095.0f * P_VREF;
        float vSens = vPin / P_DIV_GAIN;
        _emaP2 = 3500.0f * constrain((vSens - 0.25f) / 3.75f, 0.0f, 1.0f);
    }

    _inaOk = ina226.begin();
    if (_inaOk) {
        ina226.setMaxCurrentShunt(2.0f, 0.0353f);  // 2 A max, ~35.3 mΩ shunt
        ina226.setAverage(INA226_1024_SAMPLES);
        ina226.setShuntVoltageConversionTime(INA226_8300_us);
        ina226.setBusVoltageConversionTime(INA226_8300_us);
        Serial.println("INA226 OK");
    } else {
        Serial.println("INA226 NOT FOUND – check wiring");
    }
}

void SensorManager::setEmaAlpha(float alpha) {
    _emaAlpha = alpha;
}

void SensorManager::resetEma() {
    _emaTemp = NAN;
}

void SensorManager::resetStuck() {
    _lastTempForStuck = NAN;
    _sameCount = 0;
}

CoreSensorData SensorManager::read() {
    CoreSensorData d;

    // ── INA226 ─────────────────────────────────────────────────────────────
    d.inaOk = _inaOk;
    if (_inaOk) {
        d.inaVoltage = SUPPLY_VOLTAGE;
        d.inaCurrent = ina226.getCurrent();
        d.inaPower   = d.inaVoltage * d.inaCurrent;
    } else {
        d.inaVoltage = 0.0f;
        d.inaCurrent = 0.0f;
        d.inaPower   = 0.0f;
    }

    // ── Thermocouple ───────────────────────────────────────────────────────
    float raw = thermocouple.readCelsius();
    d.rawTemp = raw;

    float filtered = applyGlitchReject(raw);
    d.filteredTemp = filtered;

    if (!isnan(filtered)) {
        d.smoothTemp = applyEma(filtered);
        d.tempStuck  = checkStuck(filtered);
    } else {
        d.smoothTemp = NAN;
        d.tempStuck  = false;
    }

    // ── EZO-HUM: read previous response if ≥300 ms have elapsed ──────────
    if (_ezoReadPending && (millis() - _ezoSendTime >= EZO_RESPONSE_DELAY_MS)) {
        Wire.requestFrom(EZO_HUM_ADDR, (uint8_t)20);
        uint8_t status = Wire.available() ? Wire.read() : 0xFF;
        char buf[24] = {};
        uint8_t idx = 0;
        if (status == 0x01) {
            while (Wire.available() && idx < sizeof(buf) - 1) {
                char c = Wire.read();
                if (c == 0 || c == '\r') break;
                buf[idx++] = c;
            }
        }
        _ezoReadPending = false;
        char *comma = strchr(buf, ',');
        if (comma) {
            *comma = '\0';
            _humidityPct = atof(buf);
            _humTemp     = atof(comma + 1);
            _ezoHumOk    = true;
        }
    }

    // ── EZO-HUM: send new read command for next tick ──────────────────────
    Wire.beginTransmission(EZO_HUM_ADDR);
    Wire.write('R');
    Wire.endTransmission();
    _ezoReadPending = true;
    _ezoSendTime    = millis();

    d.humidityPct = _humidityPct;
    d.humTemp     = _humTemp;
    d.ezoHumOk    = _ezoHumOk;

    // ── Differential pressure sensors ──────────────────────────────────────
    auto readPressurePa = [](int pin, float &ema) -> float {
        // 32-sample oversampled read
        uint32_t acc = 0;
        for (int i = 0; i < P_N_SAMPLES; i++) {
            acc += analogRead(pin);
            delayMicroseconds(200);
        }
        float vPin  = ((float)acc / P_N_SAMPLES) / 4095.0f * P_VREF;
        float vSens = vPin / P_DIV_GAIN;                      // undo divider
        float raw   = 3500.0f * constrain((vSens - 0.25f) / 3.75f, 0.0f, 1.0f);
        ema = P_EMA_ALPHA * raw + (1.0f - P_EMA_ALPHA) * ema; // EMA
        return raw;
    };

    if (PIN_PRESSURE1 > 0) {
        d.deltaP1Raw  = readPressurePa(PIN_PRESSURE1, _emaP1);
        d.deltaP1Filt = _emaP1;
    } else {
        d.deltaP1Raw = d.deltaP1Filt = 0.0f;
    }
    if (PIN_PRESSURE2 > 0) {
        d.deltaP2Raw  = readPressurePa(PIN_PRESSURE2, _emaP2);
        d.deltaP2Filt = _emaP2;
    } else {
        d.deltaP2Raw = d.deltaP2Filt = 0.0f;
    }

    return d;
}

// ── Private helpers ───────────────────────────────────────────────────────────

bool SensorManager::isValidTemp(float t) const {
    if (isnan(t)) return false;
    if (t < -20.0f || t > 400.0f) return false;
    return true;
}

float SensorManager::applyGlitchReject(float t) {
    if (!isValidTemp(t)) return NAN;

    if (!isnan(_lastGoodTemp)) {
        if (fabsf(t - _lastGoodTemp) > MAX_JUMP_C) {
            return _lastGoodTemp;  // discard spike, return last known good
        }
    }

    _lastGoodTemp = t;
    return t;
}

float SensorManager::applyEma(float t) {
    if (isnan(_emaTemp)) _emaTemp = t;
    _emaTemp = _emaAlpha * t + (1.0f - _emaAlpha) * _emaTemp;
    return _emaTemp;
}

bool SensorManager::checkStuck(float t) {
    if (isnan(_lastTempForStuck)) {
        _lastTempForStuck = t;
        _sameCount = 0;
        return false;
    }

    if (fabsf(t - _lastTempForStuck) < STUCK_EPSILON_C) {
        _sameCount++;
    } else {
        _sameCount = 0;
        _lastTempForStuck = t;
    }

    return (_sameCount >= STUCK_LIMIT);
}
