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

// ── SDP510 differential pressure sensor (I2C) ────────────────────────────────
static const uint8_t SDP610_ADDR      = 0x40;  // fixed I2C address
static const float   SDP610_SCALE     = 60.0f; // counts/Pa (500 Pa range variant)
static const float   SDP610_EMA_ALPHA = 0.15f; // EMA smoothing factor

// ── Sensor objects ────────────────────────────────────────────────────────────
static MAX6675 thermocouple(PIN_SCK, PIN_CS, PIN_SO);
static INA226  ina226(0x41);  // A0 wired to VCC → address 0x41

// ── Singleton instance ────────────────────────────────────────────────────────
SensorManager sensors;

// ── Public methods ────────────────────────────────────────────────────────────

void SensorManager::begin(float emaAlphaInit) {
    _emaAlpha = emaAlphaInit;

    Wire.begin(PIN_SDA, PIN_SCL);
    Wire.setTimeOut(200);  // SDP610 clock-stretches up to 80ms; default timeout is too short

    // EZO-HUM: enable temperature output, disable dew point (sent once at boot)
    Wire.beginTransmission(EZO_HUM_ADDR);
    Wire.write("O,T,1\r");
    Wire.endTransmission();
    delay(300);
    Wire.beginTransmission(EZO_HUM_ADDR);
    Wire.write("O,Dew,0\r");
    Wire.endTransmission();
    delay(300);

    // SDP510: trigger first measurement, then read back to confirm sensor present
    Wire.beginTransmission(SDP610_ADDR);
    Wire.write(0xF1);
    uint8_t sdpErr = Wire.endTransmission();
    if (sdpErr != 0) {
        Serial.printf("SDP510 NOT FOUND – trigger error %u (check wiring SDA=15 SCL=16)\n", sdpErr);
    } else {
        // sensor will clock-stretch on requestFrom; read back first measurement
        if (Wire.requestFrom((uint8_t)SDP610_ADDR, (uint8_t)3) == 3) {
            uint8_t msb = Wire.read();
            uint8_t lsb = Wire.read();
            Wire.read();  // CRC
            int16_t raw = (int16_t)((uint16_t)(msb << 8) | lsb);
            float pa = (float)raw / SDP610_SCALE;
            _emaP1 = pa;  // seed EMA with first real reading
            Serial.printf("SDP510 OK – first reading: %.2f Pa\n", pa);
        } else {
            Serial.println("SDP510 found but read timed out – check Wire.setTimeOut()");
            _emaP1 = 0.0f;
        }
    }
    _emaP2 = 0.0f;

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

    // ── SDP610 differential pressure (I2C, clock-stretching single-shot) ──────
    Wire.beginTransmission(SDP610_ADDR);
    Wire.write(0xF1);
    Wire.endTransmission();
    if (Wire.requestFrom((uint8_t)SDP610_ADDR, (uint8_t)3) == 3) {
        uint8_t msb = Wire.read();
        uint8_t lsb = Wire.read();
        Wire.read();  // CRC — discard (factory-calibrated sensor)
        int16_t raw = (int16_t)((uint16_t)(msb << 8) | lsb);
        float pa = (float)raw / SDP610_SCALE;
        _emaP1 = SDP610_EMA_ALPHA * pa + (1.0f - SDP610_EMA_ALPHA) * _emaP1;
        d.deltaP1Raw  = pa;
        d.deltaP1Filt = _emaP1;
    } else {
        d.deltaP1Raw  = _emaP1;  // hold last good on I2C failure
        d.deltaP1Filt = _emaP1;
    }
    d.deltaP2Raw  = 0.0f;  // no second pressure channel
    d.deltaP2Filt = 0.0f;

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
