#include "ExtSensorRegistry.h"
#include <string.h>

// ── Singleton instance ────────────────────────────────────────────────────────
ExtSensorRegistry extSensors;

// ── Constructor ───────────────────────────────────────────────────────────────
ExtSensorRegistry::ExtSensorRegistry() : _count(0) {
    memset(_slots, 0, sizeof(_slots));
}

// ── Public methods ────────────────────────────────────────────────────────────

int8_t ExtSensorRegistry::registerSensor(const char *key, const char *unit) {
    if (_count >= EXT_SENSOR_MAX_COUNT) {
        Serial.println("ERR ExtSensorRegistry: registry full — increase EXT_SENSOR_MAX_COUNT");
        return -1;
    }
    ExtSensorSlot &slot = _slots[_count];
    strncpy(slot.key,  key,  sizeof(slot.key)  - 1);
    strncpy(slot.unit, unit, sizeof(slot.unit) - 1);
    slot.key[sizeof(slot.key)   - 1] = '\0';
    slot.unit[sizeof(slot.unit) - 1] = '\0';
    slot.value   = 0.0f;
    slot.present = true;
    return (int8_t)(_count++);
}

void ExtSensorRegistry::update(int8_t slotIndex, float value) {
    if (slotIndex < 0 || slotIndex >= (int8_t)_count) return;
    _slots[slotIndex].value = value;
}

void ExtSensorRegistry::emitAll() const {
    for (uint8_t i = 0; i < _count; i++) {
        if (_slots[i].present) {
            Serial.printf(" | %s: %.2f %s", _slots[i].key, _slots[i].value, _slots[i].unit);
        }
    }
}

uint8_t ExtSensorRegistry::count() const {
    return _count;
}
