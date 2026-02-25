#include "PIDController.h"

PIDController::PIDController(float kp_, float ki_, float kd_)
    : kp(kp_), ki(ki_), kd(kd_), integral(0.0f), lastError(0.0f), lastTime(0) {}

void PIDController::reset() {
    integral = 0.0f;
    lastError = 0.0f;
    lastTime = millis();
}

float PIDController::calculate(float setpoint, float measured) {
    unsigned long now = millis();
    float dt = (now - lastTime) / 1000.0f;
    if (dt <= 0) dt = 0.001f;
    lastTime = now;

    float error = setpoint - measured;

    integral += error * dt;
    integral = constrain(integral, -255.0f, 255.0f);

    float derivative = (error - lastError) / dt;
    lastError = error;

    float output = kp * error + ki * integral + kd * derivative;
    return constrain(output, 0.0f, 255.0f);
}

void PIDController::setTunings(float kp_, float ki_, float kd_) {
    kp = kp_;
    ki = ki_;
    kd = kd_;
}

void PIDController::getTunings(float &kp_, float &ki_, float &kd_) const {
    kp_ = kp;
    ki_ = ki;
    kd_ = kd;
}
