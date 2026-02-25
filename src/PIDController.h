#ifndef PIDCONTROLLER_H
#define PIDCONTROLLER_H

#include <Arduino.h>

class PIDController {
private:
    float kp, ki, kd;
    float integral;
    float lastError;
    unsigned long lastTime;

public:
    PIDController(float kp_, float ki_, float kd_);

    void reset();
    float calculate(float setpoint, float measured);
};

#endif