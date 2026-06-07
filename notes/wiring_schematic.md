# HeatsinkLab Wind Tunnel — Carrier Board Wiring Schematic

3D-printable carrier board for the ESP32-S3 dev board.  
Traces made with copper tape. All peripherals connect via JST-XH plug-in connectors.

---

## Board Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HeatsinkLab Carrier Board                        │
│                                                                     │
│  [PWR_IN J1]                                                        │
│  12V+ ──┬──► HEATER MOSFET Q1 (IRLZ44N)                           │
│  GND  ──┼──►   DRAIN ──► INA226 V_IN+ ──► INA226 V_IN− ──► [J3]  │
│         │    GATE <── GPIO4 (10kΩ pull-down to GND)                │
│         │    SOURCE ──► GND rail                                    │
│         │                                                           │
│         └──► FAN PWR MOSFET Q2 (IRLZ44N)                          │
│               DRAIN ──► [FAN_OUT J4]                               │
│               GATE <── GPIO10 (10kΩ pull-down to GND)              │
│               SOURCE ──► GND rail                                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────┐           │
│  │               ESP32-S3 Dev Board                    │           │
│  │         (USB-C powered from lab PC)                 │           │
│  │                                                     │           │
│  │  GPIO4  ────────────────────────► Q1 GATE          │           │
│  │  GPIO5  ──────────────────────────────── [J4 pin3] │           │
│  │  GPIO10 ────────────────────────► Q2 GATE          │           │
│  │  GPIO11 (MISO) ─┐                                  │           │
│  │  GPIO12 (CS)   ─┼──────────────────────────► [J6]  │           │
│  │  GPIO13 (SCK)  ─┘                                  │           │
│  │  GPIO15 (SDA) ──┬───────────────────────────► [J7]  │           │
│  │  GPIO16 (SCL) ──┼───────────────────────────► [J8]  │           │
│  │                 ├───────────────────────────► [J9]  │           │
│  │  3V3 ──────────►┼── sensor VCC rail                │           │
│  │  GND ──────────►┴── common GND rail                │           │
│  └─────────────────────────────────────────────────────┘           │
│                                                                     │
│  On-board passives:                                                 │
│    R1, R2  4.7kΩ  I2C pull-ups (SDA → 3.3V, SCL → 3.3V)          │
│    R3, R4  10kΩ   MOSFET gate pull-downs (Q1, Q2 gate → GND)      │
│    INA226  module soldered in-line in heater power path            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Connector Reference

| Ref | Label       | Type        | Pins | Pin 1      | Pin 2      | Pin 3       | Pin 4       | Pin 5     |
|-----|-------------|-------------|------|------------|------------|-------------|-------------|-----------|
| J1  | PWR_IN      | JST-XH 2p   | 2    | 12V+       | GND        | —           | —           | —         |
| J2  | HEATER_OUT  | JST-XH 2p   | 2    | HEATER+    | HEATER−    | —           | —           | —         |
| J3  | INA226_PWR  | *(on-board)* | —   | *(series in heater path — not a plug connector)* | | | | |
| J4  | FAN         | JST-XH 3p   | 3    | FAN+ (12V via Q2) | GND  | GPIO5(PWM)  | —           | —         |
| J6  | THERMO      | JST-XH 5p   | 5    | 3.3V       | GND        | GPIO11(MISO)| GPIO12(CS)  | GPIO13(SCK)|
| J7  | INA226_I2C  | JST-XH 4p   | 4    | 3.3V       | GND        | GPIO15(SDA) | GPIO16(SCL) | —         |
| J8  | SDP510      | JST-XH 4p   | 4    | 3.3V       | GND        | GPIO15(SDA) | GPIO16(SCL) | —         |
| J9  | EZO_HUM     | JST-XH 4p   | 4    | 3.3V       | GND        | GPIO15(SDA) | GPIO16(SCL) | —         |
| J10 | EXT1        | JST-XH 4p   | 4    | 3.3V       | GND        | *spare GPIO*| *spare GPIO*| —         |

> J7, J8, J9 share the same SDA/SCL traces. Route one I2C bus trace across the board and branch to three side-by-side connectors.

---

## Power Path Detail

### Heater circuit (high current — use wire or wide copper tape ≥10mm)

```
J1 pin 1 (12V+)
    │
    └──► Q1 DRAIN
              │
         INA226 V_IN+
              │
         INA226 V_IN−   ← shunt resistor measures current here
              │
    J2 pin 1 (HEATER+) ──► heater element (+) ──► heater element (−) ──► J2 pin 2 (HEATER−)
                                                                                │
J1 pin 2 (GND) ◄───────────────────────────────────────────────────────────────┘
Q1 SOURCE ──► GND rail
```

### Fan circuit

```
J1 pin 1 (12V+)
    │
    └──► Q2 DRAIN
              │
    J4 pin 1 (FAN+) ──► fan (+)
    J4 pin 2 (FAN−) ──► fan (−) ──► GND rail
Q2 SOURCE ──► GND rail

J4 pin 3 (GPIO5) ──► fan PWM signal wire (if fan has separate PWM input)
J4 pin 2 (GND)
```

> If your fan is a simple 2-wire brushless (12V / GND only with no PWM input), GPIO5 drives Q2 as a second PWM switch and GPIO10 is unused. If the fan has a separate PWM input (3- or 4-wire fan), GPIO5 goes to the PWM pin and Q2 is just the power switch driven by GPIO10.

---

## I2C Bus

```
GPIO15 (SDA) ──┬──[4.7kΩ R1]──► 3.3V
               ├──► J7 pin 3  (INA226)
               ├──► J8 pin 3  (SDP510)
               └──► J9 pin 3  (EZO-HUM)

GPIO16 (SCL) ──┬──[4.7kΩ R2]──► 3.3V
               ├──► J7 pin 4  (INA226)
               ├──► J8 pin 4  (SDP510)
               └──► J9 pin 4  (EZO-HUM)
```

I2C addresses (no conflicts):

| Sensor  | I2C Address |
|---------|-------------|
| SDP510  | 0x40        |
| INA226  | 0x41        |
| EZO-HUM | 0x6F        |

---

## GPIO → Connector Map

| ESP32-S3 GPIO | Signal         | Goes to             |
|---------------|----------------|---------------------|
| GPIO 4        | Heater PWM     | Q1 gate (on-board)  |
| GPIO 5        | Fan PWM        | J4 pin 3            |
| GPIO 10       | Fan power EN   | Q2 gate (on-board)  |
| GPIO 11       | SPI MISO       | J6 pin 3            |
| GPIO 12       | SPI CS         | J6 pin 4            |
| GPIO 13       | SPI SCK        | J6 pin 5            |
| GPIO 15       | I2C SDA        | J7, J8, J9 pin 3    |
| GPIO 16       | I2C SCL        | J7, J8, J9 pin 4    |
| 3V3           | Sensor VCC     | J6–J10 pin 1        |
| GND           | Common ground  | All connectors pin 2 + 12V GND |
| USB-C         | Serial + power | Lab PC              |

---

## Copper Tape Trace Guidelines

| Trace type          | Minimum width | Notes |
|---------------------|---------------|-------|
| Heater power (12V)  | 15 mm+        | Use stranded wire soldered alongside tape for reliability |
| Fan power (12V)     | 10 mm+        | Fan draws less current than heater |
| GPIO signal traces  | 3–5 mm        | Very low current |
| I2C SDA/SCL         | 3–5 mm        | Keep away from heater traces |
| 3.3V sensor rail    | 5 mm          | Low current (all sensors combined <100 mA) |
| GND plane           | Flood fill    | Connect all GND pads with wide copper tape pour |

**Solder all trace crossings and connector pads** — copper tape alone has high contact resistance at joints.

---

## Bill of Materials

| Qty | Part                         | Notes                                      |
|-----|------------------------------|--------------------------------------------|
| 2   | IRLZ44N N-channel MOSFET     | TO-220, logic-level gate (3.3V compatible) |
| 1   | INA226 breakout module       | Or bare IC + 0.1Ω shunt resistor          |
| 2   | 4.7kΩ resistor               | I2C pull-ups, 0805 SMD or through-hole    |
| 2   | 10kΩ resistor                | MOSFET gate pull-downs                     |
| 1   | JST-XH 2-pin connector pair  | J1 PWR_IN                                  |
| 1   | JST-XH 2-pin connector pair  | J2 HEATER_OUT                              |
| 1   | JST-XH 3-pin connector pair  | J4 FAN (12V / GND / PWM)                   |
| 1   | JST-XH 5-pin connector pair  | J6 THERMO (MAX6675 SPI)                    |
| 3   | JST-XH 4-pin connector pair  | J7 INA226_I2C, J8 SDP510, J9 EZO_HUM      |
| 1   | JST-XH 4-pin connector pair  | J10 EXT1 (future sensor)                   |
| —   | Copper tape (various widths) | 3mm + 10mm + 15mm rolls recommended        |
| —   | 3D-printed carrier board     | Design to fit your ESP32-S3 dev board footprint |

> **JST-XH vs JST-PH:** JST-XH is 2.54mm pitch (standard breadboard pitch) — easier to crimp by hand. JST-PH is 2.0mm pitch — smaller but harder to crimp without the proper tool. Either works; XH is recommended for this build.

---

## Safety Notes

- The heater MOSFET gate pull-down resistor (R3/R4, 10kΩ) is **mandatory** — it ensures the heater stays OFF if the GPIO floats during ESP32 boot.
- The heater power path carries high current. Use **wire soldered to the copper tape** for the 12V+ and HEATER+ runs — copper tape alone will heat up and delaminate under load.
- GND must be continuous across the whole board. Bridge ESP32 GND, 12V GND, and all sensor GNDs at a single point to avoid ground loops.
- `SET RUN OFF` is sent by the firmware/backend when the test completes. The MOSFET gate pull-down provides a hardware backup if the ESP32 resets unexpectedly.
