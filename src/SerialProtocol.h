#ifndef SERIALPROTOCOL_H
#define SERIALPROTOCOL_H

#include <Arduino.h>
#include "SystemState.h"
#include "SensorManager.h"

// ── SerialProtocol ─────────────────────────────────────────────────────────────
// Owns all serial I/O:
//   - Command parsing  (SET / GET)
//   - Config print     (printConfig)
//   - Telemetry emit   (emitTelemetry)
//   - NVS persistence  (loadConfig / saveConfig)
//
// handleCommand() writes changes into the global `sys` struct.
// Callers in main.cpp are responsible for applying side-effects
// (e.g. calling sensors.setEmaAlpha(), pid.setTunings()) after any
// command that changes a parameter.
// ──────────────────────────────────────────────────────────────────────────────

namespace SerialProtocol {

    // Call once per loop tick — drains all pending bytes and dispatches commands.
    void processCommands();

    // Print the full CFG line (same format as before refactor).
    void printConfig();

    // Emit one telemetry line.
    // Format is identical to the original Serial.printf in main.cpp.
    // ExtSensorRegistry::emitAll() is called at the end to append any
    // registered extension sensors without changing the fixed field order.
    void emitTelemetry(const CoreSensorData &s,
                       int pwm,
                       float pTerm, float iTerm, float dTerm, float pidOut,
                       const char *stateText);

    // Load all parameters from NVS into sys. Call once in setup().
    void loadConfig();

    // Save all parameters from sys to NVS. Called internally after each SET command.
    void saveConfig();

} // namespace SerialProtocol

#endif // SERIALPROTOCOL_H
