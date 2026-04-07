#ifndef SYSTEMSTATE_H
#define SYSTEMSTATE_H

#include <Arduino.h>

// ── Control modes ──────────────────────────────────────────────────────────────
enum ControlMode {
    MODE_AUTO   = 0,  // PID continuously drives heater toward setpoint
    MODE_MANUAL = 1,  // Fixed PWM, direct control
    MODE_SMART  = 2   // PID until stable, then locks PWM (used for Tester mode)
};

// ── Shared system state ────────────────────────────────────────────────────────
// All configurable parameters and runtime state in one place.
// Populated from NVS on boot (SerialProtocol::loadConfig), updated by
// handleCommand(), and read by the control loop and telemetry emitter.
struct SystemState {
    // PID tunings
    float pidKp;
    float pidKi;
    float pidKd;
    float pidBias;
    float setpointBias;

    // Setpoint & filter
    float setpoint;
    float emaAlpha;
    int   maxPwmStep;

    // Fan
    float fanSpeedPercent;
    bool  fanPwmInverted;
    int   fanPwmApplied;   // actual raw PWM written to pin this tick

    // Control mode & enable
    ControlMode controlMode;
    float       manualPwmTarget;
    bool        controlEnabled;

    // SMART mode configuration
    uint16_t smartEnterCount;  // consecutive stable samples needed to enter HOLD
    uint16_t smartExitCount;   // consecutive drifting samples needed to exit HOLD

    // SMART mode runtime (written by loop, read by telemetry)
    bool  smartHoldActive;
    float smartHoldPwmTarget;
    float smartEnterProgressPct;
    float smartExitProgressPct;

    // Equilibrium PWM estimate (EMA of PWM near-stable)
    float eqPwm;
};

// Defined in main.cpp
extern SystemState sys;

#endif // SYSTEMSTATE_H
