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

// ── Sensor constants ──────────────────────────────────────────────────────────
static const float SUPPLY_VOLTAGE   = 12.0f;  // nominal PSU voltage used for power calc
static const float MAX_JUMP_C       = 100.0f; // glitch reject: max allowed single-tick jump
static const float STUCK_EPSILON_C  = 0.01f;  // below this delta → "same" reading
static const uint16_t STUCK_LIMIT   = 30;     // consecutive "same" ticks before stuck declared

// ── Sensor objects ────────────────────────────────────────────────────────────
static MAX6675 thermocouple(PIN_SCK, PIN_CS, PIN_SO);
static INA226  ina226(0x40);

// ── Singleton instance ────────────────────────────────────────────────────────
SensorManager sensors;

// ── Public methods ────────────────────────────────────────────────────────────

void SensorManager::begin(float emaAlphaInit) {
    _emaAlpha = emaAlphaInit;

    Wire.begin(PIN_SDA, PIN_SCL);
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
