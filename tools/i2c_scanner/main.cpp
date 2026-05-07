#include <Arduino.h>
#include <Wire.h>

#define PIN_SDA 15
#define PIN_SCL 16

void setup() {
    Serial.begin(115200);
    delay(1500);

    Wire.begin(PIN_SDA, PIN_SCL);

    Serial.println("\nScanning I2C bus (SDA=15, SCL=16)...");

    int found = 0;
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        uint8_t err = Wire.endTransmission();
        if (err == 0) {
            Serial.printf("  Found device at 0x%02X\n", addr);
            found++;
        }
    }

    if (found == 0)
        Serial.println("  No devices found — check wiring.");
    else
        Serial.printf("Done. %d device(s) found.\n", found);
}

void loop() {}
