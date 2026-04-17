#ifndef SENSORMANAGER_H
#define SENSORMANAGER_H

#include <Arduino.h>

// ── CoreSensorData ─────────────────────────────────────────────────────────────
// Snapshot of all sensor readings for one control tick.
// Returned by SensorManager::read() — stack-allocated, no heap use.
//
// ── HOW TO ADD A NEW SENSOR VALUE ─────────────────────────────────────────────
// 1. Add your field(s) below with a comment naming the sensor and bus slot.
//    Use float for measured values, bool for health/presence flags.
//
//    Example — second thermocouple (MAX6675 #2 on its own CS pin):
//        float rawTemp2;        // MAX6675 #2, SPI slot 1
//        float filteredTemp2;   // glitch-rejected
//        float smoothTemp2;     // EMA-filtered
//
//    Example — differential pressure (e.g. DLVR-L10D on I2C):
//        float deltaP1;         // channel 1, Pa
//        float deltaP2;         // channel 2, Pa
//        bool  pressureOk;      // false if sensor not found on I2C
//
//    Example — airspeed (analog/pulse anemometer):
//        float airspeed;        // m/s
//
//    Example — ambient humidity (e.g. SHT31 on I2C):
//        float humidityPct;     // %RH
//        bool  humidityOk;
//
// 2. Initialise the new field(s) to 0.0f / false in SensorManager::read()
//    before the sensor is wired, so telemetry is always well-formed.
//
// 3. Populate the field(s) in SensorManager::read() once the hardware exists.
//
// 4. Register the value with ExtSensorRegistry (setup: registerSensor,
//    loop: update) so it appears in the telemetry stream automatically.
//    OR add it to the fixed telemetry line in SerialProtocol::emitTelemetry()
//    if it is a core sensor that must always be present (like temperature).
//
// 5. Follow the full 4-step sensor pattern in CLAUDE.md for backend + CSV.
// ──────────────────────────────────────────────────────────────────────────────
struct CoreSensorData {
    // ── Thermocouple (MAX6675, SPI slot 0) ────────────────────────────────
    float rawTemp;       // direct thermocouple reading, NAN on read error
    float filteredTemp;  // glitch-rejected (>100 °C jump discarded)
    float smoothTemp;    // EMA-filtered (alpha set via SET ALPHA)

    // ── Power monitor (INA226, I2C 0x40) ──────────────────────────────────
    float inaVoltage;    // bus voltage, V  (set to supplyVoltage constant)
    float inaCurrent;    // current, A
    float inaPower;      // computed power, W  (= inaVoltage × inaCurrent)
    bool  inaOk;         // false if INA226 not found on I2C at boot

    // ── EZO-HUM humidity probe (I2C 0x6F) ─────────────────────────────────
    float humidityPct;   // relative humidity, %RH  (0 if sensor absent)
    float humTemp;       // ambient temperature from probe, °C
    bool  ezoHumOk;      // false if no valid response received yet

    // ── Status flags ───────────────────────────────────────────────────────
    bool  tempStuck;     // true this tick if stuck-watchdog fired (heater cut)
};

// ── SensorManager ──────────────────────────────────────────────────────────────
// Owns all sensor objects, signal conditioning, and health detection.
// Call begin() once in setup(), then read() once per control tick.
class SensorManager {
public:
    // Initialise I2C, INA226, and set initial EMA alpha.
    // MAX6675 is initialised via its constructor (no extra begin needed).
    void begin(float emaAlphaInit);

    // Update EMA smoothing coefficient (called when SET ALPHA is received).
    void setEmaAlpha(float alpha);

    // Read all sensors and return a snapshot for this tick.
    // Safe to call even if a sensor is absent — absent fields return 0 or NAN.
    CoreSensorData read();

    // Reset EMA state (e.g. on mode change or RUN OFF → ON).
    void resetEma();

    // Reset stuck-sensor watchdog counters.
    void resetStuck();

private:
    float    _emaAlpha        = 0.25f;
    float    _emaTemp         = NAN;
    float    _lastGoodTemp    = NAN;
    float    _lastTempForStuck= NAN;
    uint16_t _sameCount       = 0;
    bool     _inaOk           = false;

    // EZO-HUM state
    bool     _ezoReadPending  = false;
    uint32_t _ezoSendTime     = 0;
    float    _humidityPct     = 0.0f;
    float    _humTemp         = 0.0f;
    bool     _ezoHumOk        = false;

    bool  isValidTemp(float t) const;
    float applyGlitchReject(float t);
    float applyEma(float t);
    bool  checkStuck(float t);
};

// Singleton — defined in SensorManager.cpp
extern SensorManager sensors;

#endif // SENSORMANAGER_H
