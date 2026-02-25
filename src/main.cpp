#include <Arduino.h>
#include "max6675.h"
#include "PIDController.h"
#include <math.h>

// ---------------- PIN DEFINITIES ----------------
// Kies veilige GPIO's voor jouw ESP32-S3 board!
const int heaterMosfetPin = 9;

const int thermocoupleSCK = 10;
const int thermocoupleCS  = 11;
const int thermocoupleSO  = 12;

// ---------------- PWM INSTELLINGEN ----------------
const int pwmChannel = 0;
const int pwmFreq = 500;      // 20 kHz (goed voor MOSFET)
const int pwmResolution = 8;    // 8-bit (0–255)

// ---------------- OBJECTEN ----------------
MAX6675 thermocouple(thermocoupleSCK, thermocoupleCS, thermocoupleSO);
PIDController pid(12.0, 0.6, 0.0);   // kp, ki, kd

// ---------------- CONTROL TIMING (millis) ----------------
const uint32_t controlPeriodMs = 500;   // MAX6675 ~4Hz => >= 250ms
uint32_t lastControlMs = 0;

// ---------------- SETPOINT ----------------
const float setpoint = 70.0;

// ---------------- FUNCTIES ----------------
void setPWM(int duty)
{
  duty = constrain(duty, 0, 255);
  ledcWrite(pwmChannel, duty);
}

// -------- Glitch reject --------
float lastGoodTemp = NAN;

bool isValidTemp(float t) {
  if (isnan(t)) return false;
  if (t < -20 || t > 400) return false;   // plausibel bereik
  return true;
}

float readTempFiltered(float t) { 

  if (!isValidTemp(t)) return NAN;

  if (!isnan(lastGoodTemp)) {
    float maxJump = 100.0; // °C per sample (bij 300ms loop)
    if (fabs(t - lastGoodTemp) > maxJump) {
      // glitch -> negeer
      return lastGoodTemp;
    }
  }

  lastGoodTemp = t;
  return t;
}

// -------- EMA smoothing --------
float emaTemp = NAN;
const float alpha = 0.25; // 0..1 (lager = meer smoothing)

float smoothTemp(float t) {
  if (isnan(emaTemp)) emaTemp = t;
  emaTemp = alpha * t + (1.0f - alpha) * emaTemp;
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
const float stuckEpsilon = 0.01f;   // “exact gelijk” drempel
const uint16_t stuckLimit = 30;     // 30 samples * 300ms = 9s stuck

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

void setup()
{
  Serial.begin(115200);
  delay(500);

  // PWM initialiseren
  ledcSetup(pwmChannel, pwmFreq, pwmResolution);
  ledcAttachPin(heaterMosfetPin, pwmChannel);

  setPWM(0);
  pid.reset();

  Serial.println("System started");
}

void loop() {
  

  // --- millis-based control loop ---
  uint32_t now = millis();
  if ((now - lastControlMs) < controlPeriodMs) {
    return; // nog niet tijd om opnieuw te regelen
  }
  lastControlMs = now;
  float rawTemp = thermocouple.readCelsius();
  float t = readTempFiltered(rawTemp);     // glitch reject
  if (isnan(t)) {
    setPWM(0);
    pid.reset();
    Serial.println("Temp read error -> heater OFF (NaN/out of range)");
    return;
  }

  // stuck watchdog op de (gefilterde) raw value
  if (stuckDetected(t)) {
    setPWM(0);
    pid.reset();
    Serial.println("Thermocouple STUCK detected -> heater OFF + PID reset");
    // korte cooldown zodat je niet 1000x dezelfde melding krijgt
    delay(500);
    sameCount = 0;
    return;
  }

  float t_smooth = smoothTemp(t);   // EMA smoothing

  int pwm = (int)pid.calculate(setpoint, t_smooth);
  pwm = limitPWMChange(pwm, 15);    // max 15 counts per loop

  setPWM(pwm);

  Serial.printf("Rawtemp %.2f °C | Temp: %.2f °C | Smooth: %.2f °C | PWM: %d | SP: %.2f\n",
                rawTemp, t, t_smooth, pwm, setpoint);
}