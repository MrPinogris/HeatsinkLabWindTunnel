#include "SerialProtocol.h"
#include "ExtSensorRegistry.h"
#include "PIDController.h"
#include <Preferences.h>
#include <stdlib.h>
#include <string.h>

// ── External references ───────────────────────────────────────────────────────
// Defined in main.cpp
extern SystemState  sys;
extern PIDController pid;

// Actuator helpers defined in main.cpp
extern void setFanSpeedPercent(float percent);
extern void applyPidTunings();
extern void resetSmartState();

// ── NVS ───────────────────────────────────────────────────────────────────────
static Preferences prefs;

static const char *modeToText(ControlMode mode) {
    switch (mode) {
        case MODE_MANUAL: return "MANUAL";
        case MODE_SMART:  return "SMART";
        case MODE_AUTO:
        default:          return "AUTO";
    }
}

static bool parseMode(const char *text, ControlMode &mode) {
    if (strcmp(text, "AUTO")   == 0) { mode = MODE_AUTO;   return true; }
    if (strcmp(text, "MANUAL") == 0) { mode = MODE_MANUAL; return true; }
    if (strcmp(text, "SMART")  == 0) { mode = MODE_SMART;  return true; }
    return false;
}

// ── Command buffer ────────────────────────────────────────────────────────────
static const size_t CMD_BUF_SIZE = 96;
static char  cmdBuf[CMD_BUF_SIZE];
static size_t cmdLen = 0;

// ── NVS ───────────────────────────────────────────────────────────────────────

void SerialProtocol::loadConfig() {
    prefs.begin("heatctl", false);

    sys.pidKp       = prefs.getFloat("kp",       sys.pidKp);
    sys.pidKi       = prefs.getFloat("ki",       sys.pidKi);
    sys.pidKd       = prefs.getFloat("kd",       sys.pidKd);
    sys.pidBias     = constrain(prefs.getFloat("bias",   sys.pidBias),    -255.0f, 255.0f);
    sys.setpointBias= constrain(prefs.getFloat("spbias", sys.setpointBias),-200.0f, 200.0f);
    sys.setpoint    = constrain(prefs.getFloat("sp",     sys.setpoint),    -20.0f, 400.0f);
    sys.emaAlpha    = constrain(prefs.getFloat("alpha",  sys.emaAlpha),    0.001f,   1.0f);
    sys.maxPwmStep  = constrain(prefs.getInt  ("maxstep",sys.maxPwmStep),      0,    255);
    sys.smartEnterCount = (uint16_t)constrain(prefs.getInt("entcnt", sys.smartEnterCount), 1, 400);
    sys.smartExitCount  = (uint16_t)constrain(prefs.getInt("extcnt", sys.smartExitCount),  1, 400);
    sys.fanSpeedPercent = constrain(prefs.getFloat("fanpct", sys.fanSpeedPercent), 0.0f, 100.0f);
    sys.fanPwmInverted  = prefs.getBool("faninv", sys.fanPwmInverted);

    if (prefs.isKey("mode")) {
        int modeRaw = prefs.getInt("mode", (int)MODE_AUTO);
        if (modeRaw < (int)MODE_AUTO || modeRaw > (int)MODE_SMART) modeRaw = (int)MODE_AUTO;
        sys.controlMode = (ControlMode)modeRaw;
    } else {
        // Backward compat with pre-refactor config
        bool manual = prefs.getBool("manual", false);
        sys.controlMode = manual ? MODE_MANUAL : MODE_AUTO;
    }

    if (prefs.isKey("manpwmf")) {
        sys.manualPwmTarget = constrain(prefs.getFloat("manpwmf", sys.manualPwmTarget), 0.0f, 255.0f);
    } else {
        sys.manualPwmTarget = constrain((float)prefs.getInt("manpwm", (int)sys.manualPwmTarget), 0.0f, 255.0f);
    }
}

void SerialProtocol::saveConfig() {
    prefs.putFloat("kp",      sys.pidKp);
    prefs.putFloat("ki",      sys.pidKi);
    prefs.putFloat("kd",      sys.pidKd);
    prefs.putFloat("bias",    sys.pidBias);
    prefs.putFloat("spbias",  sys.setpointBias);
    prefs.putFloat("sp",      sys.setpoint);
    prefs.putFloat("alpha",   sys.emaAlpha);
    prefs.putInt  ("maxstep", sys.maxPwmStep);
    prefs.putInt  ("entcnt",  sys.smartEnterCount);
    prefs.putInt  ("extcnt",  sys.smartExitCount);
    prefs.putFloat("fanpct",  sys.fanSpeedPercent);
    prefs.putBool ("faninv",  sys.fanPwmInverted);
    prefs.putInt  ("mode",    (int)sys.controlMode);
    prefs.putFloat("manpwmf", sys.manualPwmTarget);
    // Backward-compat keys
    prefs.putBool("manual",  sys.controlMode == MODE_MANUAL);
    prefs.putInt ("manpwm",  (int)lroundf(sys.manualPwmTarget));
}

// ── printConfig ───────────────────────────────────────────────────────────────

void SerialProtocol::printConfig() {
    float kp, ki, kd;
    pid.getTunings(kp, ki, kd);
    Serial.printf(
        "CFG KP: %.3f | KI: %.3f | KD: %.3f | BIAS: %.2f | SPBIAS: %.2f | SP: %.2f"
        " | ALPHA: %.3f | MAXSTEP: %d | ENTCNT: %d | EXTCNT: %d | FAN: %.1f"
        " | FANINV: %d | MODE: %s | MANPWM: %.2f | RUN: %s\n",
        kp, ki, kd, pid.getBias(), sys.setpointBias, sys.setpoint,
        sys.emaAlpha, sys.maxPwmStep, sys.smartEnterCount, sys.smartExitCount,
        sys.fanSpeedPercent, sys.fanPwmInverted ? 1 : 0,
        modeToText(sys.controlMode), sys.manualPwmTarget,
        sys.controlEnabled ? "ON" : "OFF");
}

// ── emitTelemetry ─────────────────────────────────────────────────────────────
// Format is IDENTICAL to the original Serial.printf in main.cpp (line 743).
// ExtSensorRegistry::emitAll() appends extension sensors before the newline.

void SerialProtocol::emitTelemetry(const CoreSensorData &s,
                                   int pwm,
                                   float pTerm, float iTerm, float dTerm, float pidOut,
                                   const char *stateText) {
    float effectiveSetpoint = constrain(sys.setpoint + sys.setpointBias, -20.0f, 400.0f);
    float absError = fabsf(effectiveSetpoint - s.smoothTemp);

    Serial.printf(
        "Rawtemp %.2f C | Temp: %.2f C | Smooth: %.2f C | PWM: %d"
        " | P: %.2f | I: %.2f | D: %.2f | OUT: %.2f"
        " | BIAS: %.2f | SPBIAS: %.2f | SP: %.2f | EFFSP: %.2f"
        " | FAN: %.1f | FANPWM: %d | MODE: %s | STATE: %s"
        " | MANPWM: %.2f | HOLDPWM: %.2f | ENTPROG: %.1f | EXTPROG: %.1f"
        " | EABS: %.2f | RUN: %s | FANINV: %d"
        " | V: %.3f V | I: %.4f A | W: %.3f W | EQPWM: %.1f",
        s.rawTemp, s.filteredTemp, s.smoothTemp, pwm,
        pTerm, iTerm, dTerm, pidOut,
        sys.pidBias, sys.setpointBias, sys.setpoint, effectiveSetpoint,
        sys.fanSpeedPercent, sys.fanPwmApplied,
        modeToText(sys.controlMode), stateText,
        sys.manualPwmTarget, sys.smartHoldPwmTarget,
        sys.smartEnterProgressPct, sys.smartExitProgressPct,
        absError,
        sys.controlEnabled ? "ON" : "OFF", sys.fanPwmInverted ? 1 : 0,
        s.inaVoltage, s.inaCurrent, s.inaPower, sys.eqPwm);

    // Append any registered extension sensors (airspeed, pressure, humidity…)
    extSensors.emitAll();

    Serial.print("\n");
}

// ── handleCommand ─────────────────────────────────────────────────────────────

static void handleCommand(char *line) {
    while (*line == ' ' || *line == '\t') line++;
    if (*line == '\0') return;

    if (strcmp(line, "GET") == 0) {
        SerialProtocol::printConfig();
        return;
    }

    char *command = strtok(line, " \t");
    if (!command || strcmp(command, "SET") != 0) {
        Serial.println("ERR Unknown command. Use SET <KP|KI|KD|BIAS|SPBIAS|SP|ALPHA|MAXSTEP|ENTERCNT|EXITCNT|FAN|FANINV|MODE|MANPWM|RUN> <value> or GET");
        return;
    }

    char *key       = strtok(NULL, " \t");
    char *valueText = strtok(NULL, " \t");
    if (!key || !valueText) {
        Serial.println("ERR Usage: SET <KP|KI|KD|BIAS|SPBIAS|SP|ALPHA|MAXSTEP|ENTERCNT|EXITCNT|FAN|FANINV|MODE|MANPWM|RUN> <value>");
        return;
    }

    // ── MAXSTEP ──────────────────────────────────────────────────────────────
    if (strcmp(key, "MAXSTEP") == 0) {
        int v = atoi(valueText);
        if (v < 0 || v > 255) { Serial.println("ERR MAXSTEP must be in range 0..255"); return; }
        sys.maxPwmStep = v;
        Serial.printf("OK MAXSTEP set to %d\n", sys.maxPwmStep);
        SerialProtocol::saveConfig();
        SerialProtocol::printConfig();
        return;
    }

    // ── MODE ─────────────────────────────────────────────────────────────────
    if (strcmp(key, "MODE") == 0) {
        ControlMode newMode = MODE_AUTO;
        if (!parseMode(valueText, newMode)) { Serial.println("ERR MODE must be AUTO, MANUAL, or SMART"); return; }
        sys.controlMode = newMode;
        pid.reset();
        resetSmartState();
        Serial.printf("OK MODE set to %s\n", modeToText(sys.controlMode));
        SerialProtocol::saveConfig();
        SerialProtocol::printConfig();
        return;
    }

    // ── ENTERCNT ─────────────────────────────────────────────────────────────
    if (strcmp(key, "ENTERCNT") == 0) {
        int v = atoi(valueText);
        if (v < 1 || v > 400) { Serial.println("ERR ENTERCNT must be in range 1..400"); return; }
        sys.smartEnterCount = (uint16_t)v;
        sys.smartEnterProgressPct = 0.0f;
        Serial.printf("OK ENTERCNT set to %u\n", sys.smartEnterCount);
        SerialProtocol::saveConfig();
        SerialProtocol::printConfig();
        return;
    }

    // ── EXITCNT ──────────────────────────────────────────────────────────────
    if (strcmp(key, "EXITCNT") == 0) {
        int v = atoi(valueText);
        if (v < 1 || v > 400) { Serial.println("ERR EXITCNT must be in range 1..400"); return; }
        sys.smartExitCount = (uint16_t)v;
        sys.smartExitProgressPct = 0.0f;
        Serial.printf("OK EXITCNT set to %u\n", sys.smartExitCount);
        SerialProtocol::saveConfig();
        SerialProtocol::printConfig();
        return;
    }

    // ── RUN ──────────────────────────────────────────────────────────────────
    if (strcmp(key, "RUN") == 0) {
        if (strcmp(valueText, "ON") == 0) {
            sys.controlEnabled = true;
            pid.reset();
            resetSmartState();
            setFanSpeedPercent(sys.fanSpeedPercent);
            Serial.println("OK RUN set to ON");
        } else if (strcmp(valueText, "OFF") == 0) {
            sys.controlEnabled = false;
            // Actuator shutdown is handled in main loop when controlEnabled == false.
            // Signal the change; main.cpp will cut PWM on next tick.
            pid.reset();
            resetSmartState();
            Serial.println("OK RUN set to OFF");
        } else {
            Serial.println("ERR RUN must be ON or OFF");
            return;
        }
        SerialProtocol::printConfig();
        return;
    }

    // ── MANPWM ───────────────────────────────────────────────────────────────
    if (strcmp(key, "MANPWM") == 0) {
        float v = atof(valueText);
        if (v < 0.0f || v > 255.0f) { Serial.println("ERR MANPWM must be in range 0..255"); return; }
        sys.manualPwmTarget = v;
        Serial.printf("OK MANPWM set to %.2f\n", sys.manualPwmTarget);
        SerialProtocol::saveConfig();
        SerialProtocol::printConfig();
        return;
    }

    // ── FANINV ───────────────────────────────────────────────────────────────
    if (strcmp(key, "FANINV") == 0) {
        if      (strcmp(valueText, "1") == 0 || strcmp(valueText, "ON")   == 0 || strcmp(valueText, "TRUE")  == 0) sys.fanPwmInverted = true;
        else if (strcmp(valueText, "0") == 0 || strcmp(valueText, "OFF")  == 0 || strcmp(valueText, "FALSE") == 0) sys.fanPwmInverted = false;
        else { Serial.println("ERR FANINV must be 0/1 or OFF/ON"); return; }
        setFanSpeedPercent(sys.fanSpeedPercent);
        Serial.printf("OK FANINV set to %d\n", sys.fanPwmInverted ? 1 : 0);
        SerialProtocol::saveConfig();
        SerialProtocol::printConfig();
        return;
    }

    // ── Float parameters ──────────────────────────────────────────────────────
    float value = atof(valueText);

    if (strcmp(key, "KP") == 0) {
        sys.pidKp = value;
        applyPidTunings();
        Serial.printf("OK KP set to %.3f\n", sys.pidKp);
    } else if (strcmp(key, "KI") == 0) {
        sys.pidKi = value;
        applyPidTunings();
        Serial.printf("OK KI set to %.3f\n", sys.pidKi);
    } else if (strcmp(key, "KD") == 0) {
        sys.pidKd = value;
        applyPidTunings();
        Serial.printf("OK KD set to %.3f\n", sys.pidKd);
    } else if (strcmp(key, "BIAS") == 0) {
        if (value < -255.0f || value > 255.0f) { Serial.println("ERR BIAS must be in range -255..255"); return; }
        sys.pidBias = value;
        applyPidTunings();
        Serial.printf("OK BIAS set to %.2f\n", sys.pidBias);
    } else if (strcmp(key, "SPBIAS") == 0) {
        if (value < -200.0f || value > 200.0f) { Serial.println("ERR SPBIAS must be in range -200..200"); return; }
        sys.setpointBias = value;
        Serial.printf("OK SPBIAS set to %.2f\n", sys.setpointBias);
    } else if (strcmp(key, "SP") == 0) {
        if (value < -20.0f || value > 400.0f) { Serial.println("ERR SP must be in range -20..400"); return; }
        sys.setpoint = value;
        Serial.printf("OK SP set to %.2f\n", sys.setpoint);
    } else if (strcmp(key, "ALPHA") == 0) {
        if (value <= 0.0f || value > 1.0f) { Serial.println("ERR ALPHA must be in range (0..1]"); return; }
        sys.emaAlpha = value;
        sensors.setEmaAlpha(value);
        Serial.printf("OK ALPHA set to %.3f\n", sys.emaAlpha);
    } else if (strcmp(key, "FAN") == 0) {
        if (value < 0.0f || value > 100.0f) { Serial.println("ERR FAN must be in range 0..100 (percent)"); return; }
        setFanSpeedPercent(value);
        Serial.printf("OK FAN set to %.1f %% (raw %d, 255=off 0=full)\n", sys.fanSpeedPercent, sys.fanPwmApplied);
    } else {
        Serial.println("ERR Unknown key. Use KP, KI, KD, BIAS, SPBIAS, SP, ALPHA, MAXSTEP, ENTERCNT, EXITCNT, FAN, FANINV, MODE, MANPWM, RUN");
        return;
    }

    SerialProtocol::saveConfig();
    SerialProtocol::printConfig();
}

// ── processCommands ───────────────────────────────────────────────────────────

void SerialProtocol::processCommands() {
    while (Serial.available() > 0) {
        char c = (char)Serial.read();
        if (c == '\r') continue;
        if (c == '\n') {
            cmdBuf[cmdLen] = '\0';
            handleCommand(cmdBuf);
            cmdLen = 0;
            continue;
        }
        if (cmdLen < (CMD_BUF_SIZE - 1)) {
            cmdBuf[cmdLen++] = c;
        } else {
            cmdLen = 0;
            Serial.println("ERR Command too long");
        }
    }
}
