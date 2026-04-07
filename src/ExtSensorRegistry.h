#ifndef EXTSENSORREGISTRY_H
#define EXTSENSORREGISTRY_H

#include <Arduino.h>

// ── ExtSensorRegistry ──────────────────────────────────────────────────────────
// Lightweight fixed-size registry for future/optional extension sensors.
// Each registered sensor automatically appends its value to the telemetry
// stream via emitAll(), so adding a new sensor requires only two lines in
// main.cpp — no edits to the telemetry format string needed.
//
// Maximum slots is set at compile time by EXT_SENSOR_MAX_COUNT.
// All storage is in a fixed array — no heap allocation.
//
// ── HOW TO ADD A NEW EXTENSION SENSOR ─────────────────────────────────────────
//
// Step A — In setup() (main.cpp), register the sensor slot once:
//
//     int8_t mySlot = extSensors.registerSensor("AIRSPEED", "m/s");
//     // Returns slot index (0..7) on success, -1 if registry is full.
//     // Store the index in a file-scope variable so loop() can use it.
//
// Step B — In loop() (main.cpp), update the slot with the current reading:
//
//     extSensors.update(mySlot, measuredAirspeed);
//
// That's it for firmware. The sensor will automatically appear in telemetry:
//     ... | AIRSPEED: 2.35 m/s
//
// Step C — Follow the remaining steps in the 4-step sensor pattern in CLAUDE.md:
//   - Add a named capture group to TELEM_RE in server.py
//   - Add a readout element to index.html
//   - Bump schema_version and add the field to CSV_FIELDS
//
// ── Planned sensors (register when hardware is connected) ─────────────────────
//   extSensors.registerSensor("AIRSPEED", "m/s")    — anemometer
//   extSensors.registerSensor("DELTA_P1", "Pa")     — differential pressure ch1
//   extSensors.registerSensor("DELTA_P2", "Pa")     — differential pressure ch2
//   extSensors.registerSensor("HUMIDITY", "%RH")    — ambient humidity (SHT31)
// ──────────────────────────────────────────────────────────────────────────────

#define EXT_SENSOR_MAX_COUNT 8  // increase if more than 8 extension sensors needed

struct ExtSensorSlot {
    char  key[16];    // telemetry key, e.g. "AIRSPEED"
    char  unit[8];    // unit label, e.g. "m/s"
    float value;      // latest reading
    bool  present;    // true once registered
};

class ExtSensorRegistry {
public:
    ExtSensorRegistry();

    // Register a new sensor slot. Call once in setup().
    // Returns the slot index (use it in update()), or -1 if registry is full.
    int8_t registerSensor(const char *key, const char *unit);

    // Update a slot's value. Call every loop tick after reading the sensor.
    void update(int8_t slotIndex, float value);

    // Append "| KEY: <value> UNIT" to Serial for every registered slot.
    // Called at the end of SerialProtocol::emitTelemetry().
    // Outputs nothing when no sensors are registered (registry is empty).
    void emitAll() const;

    // Number of registered sensors (0..EXT_SENSOR_MAX_COUNT).
    uint8_t count() const;

private:
    ExtSensorSlot _slots[EXT_SENSOR_MAX_COUNT];
    uint8_t       _count;
};

// Singleton — defined in ExtSensorRegistry.cpp
extern ExtSensorRegistry extSensors;

#endif // EXTSENSORREGISTRY_H
