#include <Arduino.h>
#include "max6675.h"
#include "PIDController.h"
#include <Preferences.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// ---------------- PIN DEFINITIES ----------------
const int heaterMosfetPin = 9;
const int fanPwmPin = 8;

const int thermocoupleSCK = 12;
const int thermocoupleCS  = 11;
const int thermocoupleSO  = 10;

// ---------------- PWM INSTELLINGEN ----------------
const int heaterPwmChannel = 0;
const int fanPwmChannel = 1;
const int pwmFreq = 500;
const int pwmResolution = 8;

// ---------------- OBJECTEN ----------------
MAX6675 thermocouple(thermocoupleSCK, thermocoupleCS, thermocoupleSO);
float pidKp = 8.0f;
float pidKi = 0.06f;
float pidKd = 0.0f;
float pidBias = 0.0f;
float setpointBias = 0.0f;
PIDController pid(pidKp, pidKi, pidKd);
Preferences preferences;

// ---------------- CONTROL TIMING (millis) ----------------
const uint32_t controlPeriodMs = 500;
uint32_t lastControlMs = 0;

// ---------------- SETPOINT ----------------
float setpoint = 70.0f;
float fanSpeedPercent = 0.0f;
int fanPwmRaw = 255;
float emaAlpha = 0.25f;
int maxPwmStep = 15;

void saveConfigToNvs();
void loadConfigFromNvs();

// ---------------- FUNCTIES ----------------
void setPWM(int duty)
{
  duty = constrain(duty, 0, 255);
  ledcWrite(heaterPwmChannel, duty);
}

int fanPercentToRaw(float percent) {
  float clamped = constrain(percent, 0.0f, 100.0f);
  int raw = (int)lroundf(255.0f * (1.0f - (clamped / 100.0f)));
  return constrain(raw, 0, 255);
}

void setFanSpeedPercent(float percent) {
  fanSpeedPercent = constrain(percent, 0.0f, 100.0f);
  fanPwmRaw = fanPercentToRaw(fanSpeedPercent);
  ledcWrite(fanPwmChannel, fanPwmRaw);
}

void saveConfigToNvs() {
  preferences.putFloat("kp", pidKp);
  preferences.putFloat("ki", pidKi);
  preferences.putFloat("kd", pidKd);
  preferences.putFloat("bias", pidBias);
  preferences.putFloat("spbias", setpointBias);
  preferences.putFloat("sp", setpoint);
  preferences.putFloat("alpha", emaAlpha);
  preferences.putInt("maxstep", maxPwmStep);
  preferences.putFloat("fanpct", fanSpeedPercent);
}

void loadConfigFromNvs() {
  pidKp = preferences.getFloat("kp", pidKp);
  pidKi = preferences.getFloat("ki", pidKi);
  pidKd = preferences.getFloat("kd", pidKd);
  pidBias = constrain(preferences.getFloat("bias", pidBias), -255.0f, 255.0f);
  setpointBias = constrain(preferences.getFloat("spbias", setpointBias), -200.0f, 200.0f);
  setpoint = constrain(preferences.getFloat("sp", setpoint), -20.0f, 400.0f);
  emaAlpha = constrain(preferences.getFloat("alpha", emaAlpha), 0.001f, 1.0f);
  maxPwmStep = constrain(preferences.getInt("maxstep", maxPwmStep), 0, 255);
  fanSpeedPercent = constrain(preferences.getFloat("fanpct", fanSpeedPercent), 0.0f, 100.0f);
}

// -------- Glitch reject --------
float lastGoodTemp = NAN;

bool isValidTemp(float t) {
  if (isnan(t)) return false;
  if (t < -20 || t > 400) return false;
  return true;
}

float readTempFiltered(float t) {
  if (!isValidTemp(t)) return NAN;

  if (!isnan(lastGoodTemp)) {
    float maxJump = 100.0f;
    if (fabs(t - lastGoodTemp) > maxJump) {
      return lastGoodTemp;
    }
  }

  lastGoodTemp = t;
  return t;
}

// -------- EMA smoothing --------
float emaTemp = NAN;

float smoothTemp(float t) {
  if (isnan(emaTemp)) emaTemp = t;
  emaTemp = emaAlpha * t + (1.0f - emaAlpha) * emaTemp;
  return emaTemp;
}

// -------- PWM slew-rate limit --------
int lastPWM = 0;

int limitPWMChange(int pwm, int maxStep) {
  if (pwm > lastPWM + maxStep) pwm = lastPWM + maxStep;
  if (pwm < lastPWM - maxStep) pwm = lastPWM - maxStep;
  lastPWM = pwm;
  return pwm;
}

// -------- Stuck watchdog --------
float lastTempForStuck = NAN;
uint16_t sameCount = 0;
const float stuckEpsilon = 0.01f;
const uint16_t stuckLimit = 30;

bool stuckDetected(float t) {
  if (isnan(lastTempForStuck)) {
    lastTempForStuck = t;
    sameCount = 0;
    return false;
  }

  if (fabs(t - lastTempForStuck) < stuckEpsilon) {
    sameCount++;
  } else {
    sameCount = 0;
    lastTempForStuck = t;
  }

  return (sameCount >= stuckLimit);
}

// -------- Runtime commands over serial --------
const size_t commandBufferSize = 96;
char commandBuffer[commandBufferSize];
size_t commandLen = 0;

void printConfig() {
  float kp;
  float ki;
  float kd;
  pid.getTunings(kp, ki, kd);
  Serial.printf("CFG KP: %.3f | KI: %.3f | KD: %.3f | BIAS: %.2f | SPBIAS: %.2f | SP: %.2f | ALPHA: %.3f | MAXSTEP: %d | FAN: %.1f\n",
                kp, ki, kd, pid.getBias(), setpointBias, setpoint, emaAlpha, maxPwmStep, fanSpeedPercent);
}

void applyPidTunings() {
  pid.setTunings(pidKp, pidKi, pidKd);
  pid.setBias(pidBias);
  pid.reset();
}

void handleCommand(char *line) {
  while (*line == ' ' || *line == '\t') {
    line++;
  }

  if (*line == '\0') {
    return;
  }

  if (strcmp(line, "GET") == 0) {
    printConfig();
    return;
  }

  char *command = strtok(line, " \t");
  if (!command || strcmp(command, "SET") != 0) {
    Serial.println("ERR Unknown command. Use SET <KP|KI|KD|BIAS|SPBIAS|SP|ALPHA|MAXSTEP|FAN> <value> or GET");
    return;
  }

  char *key = strtok(NULL, " \t");
  char *valueText = strtok(NULL, " \t");
  if (!key || !valueText) {
    Serial.println("ERR Usage: SET <KP|KI|KD|BIAS|SPBIAS|SP|ALPHA|MAXSTEP|FAN> <value>");
    return;
  }

  if (strcmp(key, "MAXSTEP") == 0) {
    int valueInt = atoi(valueText);
    if (valueInt < 0 || valueInt > 255) {
      Serial.println("ERR MAXSTEP must be in range 0..255");
      return;
    }
    maxPwmStep = valueInt;
    Serial.printf("OK MAXSTEP set to %d\n", maxPwmStep);
    saveConfigToNvs();
    printConfig();
    return;
  }

  float value = atof(valueText);
  if (strcmp(key, "KP") == 0) {
    pidKp = value;
    applyPidTunings();
    Serial.printf("OK KP set to %.3f\n", pidKp);
  } else if (strcmp(key, "KI") == 0) {
    pidKi = value;
    applyPidTunings();
    Serial.printf("OK KI set to %.3f\n", pidKi);
  } else if (strcmp(key, "KD") == 0) {
    pidKd = value;
    applyPidTunings();
    Serial.printf("OK KD set to %.3f\n", pidKd);
  } else if (strcmp(key, "BIAS") == 0) {
    if (value < -255.0f || value > 255.0f) {
      Serial.println("ERR BIAS must be in range -255..255");
      return;
    }
    pidBias = value;
    applyPidTunings();
    Serial.printf("OK BIAS set to %.2f\n", pidBias);
  } else if (strcmp(key, "SPBIAS") == 0) {
    if (value < -200.0f || value > 200.0f) {
      Serial.println("ERR SPBIAS must be in range -200..200");
      return;
    }
    setpointBias = value;
    Serial.printf("OK SPBIAS set to %.2f\n", setpointBias);
  } else if (strcmp(key, "SP") == 0) {
    if (value < -20.0f || value > 400.0f) {
      Serial.println("ERR SP must be in range -20..400");
      return;
    }
    setpoint = value;
    Serial.printf("OK SP set to %.2f\n", setpoint);
  } else if (strcmp(key, "ALPHA") == 0) {
    if (value <= 0.0f || value > 1.0f) {
      Serial.println("ERR ALPHA must be in range (0..1]");
      return;
    }
    emaAlpha = value;
    Serial.printf("OK ALPHA set to %.3f\n", emaAlpha);
  } else if (strcmp(key, "FAN") == 0) {
    if (value < 0.0f || value > 100.0f) {
      Serial.println("ERR FAN must be in range 0..100 (percent)");
      return;
    }
    setFanSpeedPercent(value);
    Serial.printf("OK FAN set to %.1f %% (raw %d, 255=off 0=full)\n", fanSpeedPercent, fanPwmRaw);
  } else {
    Serial.println("ERR Unknown key. Use KP, KI, KD, BIAS, SPBIAS, SP, ALPHA, MAXSTEP, FAN");
    return;
  }

  saveConfigToNvs();
  printConfig();
}

void processSerialCommands() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      commandBuffer[commandLen] = '\0';
      handleCommand(commandBuffer);
      commandLen = 0;
      continue;
    }
    if (commandLen < (commandBufferSize - 1)) {
      commandBuffer[commandLen++] = c;
    } else {
      commandLen = 0;
      Serial.println("ERR Command too long");
    }
  }
}

void setup()
{
  Serial.begin(115200);
  delay(500);
  preferences.begin("heatctl", false);
  loadConfigFromNvs();

  ledcSetup(heaterPwmChannel, pwmFreq, pwmResolution);
  ledcAttachPin(heaterMosfetPin, heaterPwmChannel);
  ledcSetup(fanPwmChannel, pwmFreq, pwmResolution);
  ledcAttachPin(fanPwmPin, fanPwmChannel);

  setPWM(0);
  setFanSpeedPercent(fanSpeedPercent);
  pid.setBias(pidBias);
  pid.setTunings(pidKp, pidKi, pidKd);
  pid.reset();

  Serial.println("System started");
  Serial.println("Commands: GET, SET KP <v>, SET KI <v>, SET KD <v>, SET BIAS <v>, SET SPBIAS <v>, SET SP <v>, SET ALPHA <v>, SET MAXSTEP <v>, SET FAN <0..100>");
  printConfig();
}

void loop() {
  processSerialCommands();

  uint32_t now = millis();
  if ((now - lastControlMs) < controlPeriodMs) {
    return;
  }
  lastControlMs = now;

  float rawTemp = thermocouple.readCelsius();
  float t = readTempFiltered(rawTemp);
  if (isnan(t)) {
    setPWM(0);
    pid.reset();
    Serial.println("Temp read error -> heater OFF (NaN/out of range)");
    return;
  }

  if (stuckDetected(t)) {
    setPWM(0);
    pid.reset();
    Serial.println("Thermocouple STUCK detected -> heater OFF + PID reset");
    delay(500);
    sameCount = 0;
    return;
  }

  float tSmooth = smoothTemp(t);
  float effectiveSetpoint = setpoint + setpointBias;
  effectiveSetpoint = constrain(effectiveSetpoint, -20.0f, 400.0f);

  int pwm = (int)pid.calculate(effectiveSetpoint, tSmooth);
  pwm = limitPWMChange(pwm, maxPwmStep);

  setPWM(pwm);

  Serial.printf("Rawtemp %.2f C | Temp: %.2f C | Smooth: %.2f C | PWM: %d | BIAS: %.2f | SPBIAS: %.2f | SP: %.2f | EFFSP: %.2f | FAN: %.1f | FANPWM: %d\n",
                rawTemp, t, tSmooth, pwm, pidBias, setpointBias, setpoint, effectiveSetpoint, fanSpeedPercent, fanPwmRaw);
}
