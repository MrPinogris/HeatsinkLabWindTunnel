# Design and Implementation of an Automated Wind-Tunnel Platform for Heatsink Thermal Characterisation

**A Bachelor's Thesis in Engineering**

---

**Author:** _[Your Name]_
**Student number:** _[number]_
**Programme:** _[Bachelor of Engineering — Electronics / Mechatronics / Mechanical]_
**Institution:** _[University / Faculty / Department]_
**Supervisor:** _[Supervisor name]_
**Co-supervisor / Promotor:** _[name, if applicable]_
**Academic year:** 2025–2026
**Submission date:** _[date]_

---

> **Draft status.** This is a complete structural draft generated from the
> HeatsinkLab Wind Tunnel codebase and documentation. Sections describing the
> *system design, architecture, and method* are grounded in the real
> implementation. Sections requiring *measured data* (Chapter 5, Results) contain
> clearly marked placeholders — `‹FILL: …›` — that must be replaced with your own
> experimental measurements before submission. Do not submit with placeholders in place.

---

## Abstract

Heatsinks are the dominant passive thermal-management solution in electronics, yet
their comparative evaluation in a teaching laboratory is usually slow, manual, and
error-prone. This thesis presents the design, implementation, and validation of an
**automated wind-tunnel platform** that characterises the thermal performance of
heatsinks under controlled forced-convection conditions. The system couples a
ceramic heater and a controllable fan to an ESP32-S3 microcontroller running a PID
control loop, with a browser-based graphical interface that automates the entire
test procedure: a student selects a port, enters a heatsink identifier, and presses
a single button. The platform steps through a programmed series of set-point
temperatures, detects thermal equilibrium automatically, records steady-state power
and temperature, and exports the results as a CSV file.

The contribution of this work is primarily a **software-and-systems contribution**:
the firmware exposes a stable serial interface, while a FastAPI backend and
single-file frontend deliver a zero-friction, safety-aware student workflow. The
platform computes a comparative thermal-resistance metric (R_th = ΔT⁄P) for each
heatsink at each operating point, enabling fair, repeatable comparison between
samples. The system was validated _[FILL: against N heatsinks / a reference sample]_
and demonstrated _[FILL: repeatability of ± … °C/W]_.

**Keywords:** heatsink, thermal resistance, forced convection, wind tunnel, PID
control, ESP32, embedded systems, instrumentation, laboratory automation.

---

## Acknowledgements

_[Optional. Thank your supervisor, the lab technicians, and anyone who assisted with
the physical build and testing.]_

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Problem Statement and Research Questions](#2-problem-statement-and-research-questions)
3. [State of the Art / Literature Review](#3-state-of-the-art--literature-review)
4. [Methodology and System Design](#4-methodology-and-system-design)
5. [Results and Measurements](#5-results-and-measurements)
6. [Discussion](#6-discussion)
7. [Conclusion](#7-conclusion)
8. [Future Work and Recommendations](#8-future-work-and-recommendations)
9. [References](#9-references)
10. [Appendices](#appendices)

---

## List of Figures

| No. | Caption | Section |
|---|---|---|
| 1.1 | Context: heatsink thermal evaluation in the teaching lab | 1 |
| 4.1 | Three-tier system architecture (firmware / backend / frontend) | 4.1 |
| 4.2 | Physical wind-tunnel assembly and instrumented heater block | 4.2 |
| 4.3 | ESP32-S3 wiring and sensor bus topology | 4.3 |
| 4.4 | Control finite-state machine (AUTO / MANUAL / SMART) | 4.5 |
| 4.5 | Automated tester workflow sequence | 4.6 |
| 5.1 | Temperature step response for a representative heatsink | 5.2 |
| 5.2 | Steady-state power vs. set-point temperature | 5.3 |
| 5.3 | Comparative R_th across tested heatsinks | 5.4 |

> _Insert actual figures (photographs, plots, screenshots) and update captions._

## List of Tables

| No. | Caption | Section |
|---|---|---|
| 4.1 | Hardware component summary | 4.2 |
| 4.2 | Serial command interface | 4.4 |
| 4.3 | Equilibrium-detection parameters | 4.5 |
| 5.1 | Measured results per heatsink | 5.4 |
| 5.2 | Repeatability / uncertainty budget | 5.5 |

## Nomenclature and Abbreviations

| Symbol | Meaning | Unit |
|---|---|---|
| T | Heatsink base temperature (measured) | °C |
| T_amb | Ambient air temperature | °C |
| ΔT | Temperature rise above ambient, T − T_amb | °C |
| P | Electrical power dissipated in the heater | W |
| R_th | Thermal resistance, ΔT⁄P | °C/W |
| PWM | Pulse-width-modulated heater drive (0–255) | – |
| EqPWM | Equilibrium (steady-state) PWM estimate | – |
| PID | Proportional–Integral–Derivative controller | – |
| EMA | Exponential moving average (sensor filter) | – |

| Abbreviation | Expansion |
|---|---|
| MCU | Microcontroller unit |
| SPI | Serial Peripheral Interface |
| I²C | Inter-Integrated Circuit bus |
| GUI | Graphical user interface |
| CSV | Comma-separated values |
| NVS | Non-volatile storage (ESP32) |

---

## 1. Introduction

### 1.1 Background and motivation

Thermal management is a constraining factor in nearly all modern electronics. As
power densities rise, the ability of a heatsink to move heat away from a component
directly determines reliability and performance. In an engineering teaching
laboratory, students are expected to develop an intuition for *why* one heatsink
outperforms another — fin geometry, material, surface area, and the airflow regime
all matter — and ideally to quantify these differences experimentally.

In practice, however, measuring heatsink performance by hand is awkward. It requires
holding a heat source at a stable temperature, waiting for thermal equilibrium,
reading several instruments simultaneously, and recording the results without
introducing transcription errors — all while a live heating element poses a physical
safety risk. The cognitive and procedural overhead crowds out the actual learning
objective: comparing heatsinks.

### 1.2 Project context

This thesis documents the **HeatsinkLab Wind Tunnel**, a platform designed so that a
student with no embedded-systems or control-theory background can characterise a
heatsink in minutes. A ceramic heater drives an instrumented copper block to a series
of target temperatures while a fan provides controlled forced convection through a
small wind tunnel. An ESP32-S3 microcontroller runs the closed-loop control and
streams telemetry over USB to a browser-based interface, which automates the test and
exports the data.

The guiding design principle is **software-first development**: the firmware is
treated as a stable, locked black box exposing a serial command and telemetry
interface, while all user-facing features and workflow logic live in the backend and
frontend. This keeps iteration fast (a software change deploys by restarting a
server, not by re-flashing hardware) and keeps the safety-critical control loop
unchanged once validated.

### 1.3 Aim and scope

The aim of this work is to deliver a complete, safe, and repeatable system that lets
students obtain comparative thermal data for heatsinks through a single-button
workflow. The scope covers:

- the system architecture and the rationale for the three-tier split;
- the control strategy used to reach and detect thermal equilibrium;
- the instrumentation and data pipeline from sensor to exported CSV;
- the automated test workflow and its safety behaviour;
- experimental validation of the platform.

Out of scope (and discussed as future work) are an independent hardware safety
watchdog, closed-loop airspeed control, and the full suite of environmental sensors
that the architecture already accommodates but which were not yet wired during this
project.

### 1.4 Thesis outline

Chapter 2 states the problem and research questions. Chapter 3 reviews relevant
background. Chapter 4 details the methodology and system design. Chapter 5 presents
the measurements. Chapter 6 discusses the findings, Chapter 7 concludes, and
Chapter 8 sets out recommendations and future work.

---

## 2. Problem Statement and Research Questions

### 2.1 Problem statement

A teaching laboratory needs to compare the thermal performance of different heatsinks
*fairly* (same conditions), *repeatably* (same result on re-test), and *safely* (a
live heater is involved), while keeping the procedure simple enough that students
focus on the engineering result rather than on operating the apparatus. No
off-the-shelf, low-cost instrument delivers this combination, and a manual rig fails
on simplicity, repeatability, and safety simultaneously.

### 2.2 Research questions

This thesis is structured around the following questions:

- **RQ1.** Can a low-cost microcontroller-based platform hold a heat source at a
  series of set-point temperatures with sufficient stability to obtain a repeatable
  steady-state thermal measurement?
- **RQ2.** Can the steady-state operating point (equilibrium temperature and power) be
  detected *automatically* and reliably, removing the need for an operator to judge
  when equilibrium has been reached?
- **RQ3.** Can the complete test workflow be reduced to a single student action while
  preserving safe shutdown of the heater under all termination conditions (normal
  completion, manual stop, fault)?
- **RQ4.** Does the resulting platform produce comparative thermal metrics that
  meaningfully distinguish heatsinks of differing geometry/material?

### 2.3 Requirements

| ID | Requirement | Type |
|---|---|---|
| R1 | Reach and hold set-point temperatures in the lab range (e.g. 40–80 °C) | Functional |
| R2 | Detect thermal equilibrium automatically (±0.5 °C stability window) | Functional |
| R3 | Record steady-state temperature and electrical power per set-point | Functional |
| R4 | Export results as CSV with a stable, versioned schema | Functional |
| R5 | Heater must never remain energised unattended after a test | Safety |
| R6 | Provide a single-button student workflow | Usability |
| R7 | Operate without hardware via a simulator for development/teaching | Non-functional |
| R8 | Be extensible to airflow, pressure, and humidity sensors | Non-functional |

---

## 3. State of the Art / Literature Review

> _This chapter situates the project in existing work. The structure below is
> complete; expand each subsection with cited sources from your literature search.
> Aim for ‹FILL: 12–20› references appropriate to a Bachelor thesis._

### 3.1 Heatsink thermal characterisation

The standard figure of merit for a heatsink is its **thermal resistance**, R_th,
defined as the temperature rise above ambient per unit of dissipated power
(R_th = ΔT⁄P, in °C/W); a lower value indicates better heat transfer. Forced-convection
performance depends strongly on airflow rate, making controlled airflow essential for
fair comparison. _[FILL: cite standard references on heatsink thermal resistance and
forced-convection heat transfer, e.g. heat-transfer textbooks and manufacturer
application notes.]_

### 3.2 Wind tunnels for electronics cooling

Small bench-top wind tunnels are an established method for evaluating component
cooling under repeatable airflow. _[FILL: cite examples of low-speed wind-tunnel rigs
used for electronics thermal testing; note typical flow-conditioning approaches such
as honeycomb sections to laminarise flow.]_

### 3.3 Embedded temperature control

Closed-loop temperature control with PID is ubiquitous in instrumentation. _[FILL:
cite PID control fundamentals and typical embedded implementations; note the role of
anti-windup and output slew-rate limiting in safe heater control.]_

### 3.4 Laboratory automation and usability

Reducing operator workload improves both throughput and data quality in teaching
labs. _[FILL: cite work on guided/automated lab instruments and usability for novice
operators.]_

### 3.5 Gap addressed by this work

Existing solutions tend to be either expensive commercial instruments or bespoke
manual rigs. This project targets the gap: a low-cost, open, automated platform with a
student-grade workflow and built-in safety logic. _[FILL: sharpen this gap statement
against the specific sources you cite above.]_

---

## 4. Methodology and System Design

### 4.1 System architecture

The platform is organised into three tiers with a strict interface between each
(Figure 4.1). This separation is deliberate: the safety-critical control loop is
isolated in firmware and validated once, while all features that students interact
with are developed in software that can be changed and redeployed without touching the
hardware.

```
┌──────────────────────────────────┐
│  Firmware (C++ / ESP32-S3)       │  src/  — stable, treated as a black box
│  · PID heater + fan control      │
│  · MAX6675 thermocouple (SPI)    │
│  · INA226 power monitor (I²C)    │
│  · Serial command interface      │
└────────────┬─────────────────────┘
             │ USB Serial @ 115 200 baud
┌────────────▼─────────────────────┐
│  Backend (Python / FastAPI)      │  tools/web_gui/server.py
│  · WebSocket server :8765        │
│  · Telemetry parser + CSV logger │
│  · Virtual MCU simulator         │
└────────────┬─────────────────────┘
             │ WebSocket
┌────────────▼─────────────────────┐
│  Frontend (HTML / JS / CSS)      │  tools/web_gui/static/index.html
│  · Chart.js real-time graphs     │
│  · Automated tester workflow     │
│  · CSV export                    │
└──────────────────────────────────┘
```

**Figure 4.1** — Three-tier architecture. The only contract between tiers is the
serial command/telemetry protocol (firmware ↔ backend) and the WebSocket message set
(backend ↔ frontend).

### 4.2 Physical construction and instrumentation

The mechanical build is a short wind tunnel. A fan at the inlet drives air through a
hexagonal honeycomb grid that breaks up turbulence and produces a more uniform,
laminar flow across the test section. A protective guard covers the fan face. At the
centre of the tunnel sits the heater module: a ceramic PTC heating element topped with
a copper spreader plate, into which a thermocouple is inserted through a
precision-drilled hole so that the measured temperature closely tracks the heatsink
base. The heatsink under test clips onto the copper plate.

**Table 4.1 — Hardware component summary**

| Component | Part | Interface | Address |
|---|---|---|---|
| MCU | ESP32-S3 DevKit-C1 | — | — |
| Temperature | MAX6675 thermocouple module | SPI | — |
| Power monitor | INA226 (shunt in series with heater) | I²C | 0x41 |
| Diff. pressure | Sensirion SDP510 | I²C | 0x40 |
| Humidity | EZO-HUM (Atlas Scientific) | I²C | 0x6F |
| Heater drive | MOSFET module (PWM gate, GPIO 4) | GPIO | — |
| Fan PWM | MOSFET / driver (GPIO 5) | GPIO | — |
| Fan power cut-off | MOSFET (digital gate, GPIO 10) | GPIO | — |

The INA226 shunt is wired in series with the heater so that it measures the heater
current — and therefore the dissipated electrical power — directly. This is the basis
of the power term used in the thermal metric.

**Figure 4.2** — _[FILL: annotated photograph of the physical assembly, from
`docs/media/`.]_

### 4.3 Electrical design

The ESP32-S3 drives the heater and fan through MOSFET modules and reads all sensors
over a shared I²C bus plus a dedicated SPI link for the thermocouple. A separate
MOSFET on GPIO 10 can fully de-energise the fan, allowing natural-convection tests.

Key pin assignments:

| GPIO | Function | Notes |
|---|---|---|
| 4 | Heater MOSFET gate | PWM 500 Hz, 8-bit |
| 5 | Fan PWM signal | PWM 500 Hz, 8-bit |
| 10 | Fan power cut-off gate | HIGH = powered |
| 11/12/13 | MAX6675 SO / CS / SCK | SPI |
| 15/16 | I²C SDA / SCL | Shared: INA226, SDP510, EZO-HUM |

**Figure 4.3** — _[FILL: wiring/bus topology diagram; a generator script exists at
`docs/generate_wiring_schematic.py`.]_

> **Safety note.** Heater (GPIO 4) and fan (GPIO 5) pin assignments and the heater
> drive path are safety-relevant and were fixed early and not changed. The firmware
> bounds-checks every command and limits the per-cycle PWM change (slew-rate limiting)
> to prevent abrupt heater jumps.

### 4.4 Serial command and telemetry protocol

The firmware exposes a simple text protocol over USB serial at 115 200 baud. The
backend sends `SET`/`GET` commands and parses one telemetry line per control cycle.

**Table 4.2 — Selected serial commands**

| Command | Range | Description |
|---|---|---|
| `SET SP <f>` | −20…400 °C | Temperature set-point |
| `SET MODE <m>` | AUTO/MANUAL/SMART | Control mode |
| `SET FAN <n>` | 0…100 | Fan speed % |
| `SET RUN <ON/OFF>` | ON/OFF | Enable/disable heater |
| `SET KP/KI/KD <f>` | float | PID gains |
| `GET` | — | Print current configuration |

All parameters are bounds-checked in firmware before being accepted, and the maximum
set-point is capped at 400 °C. Telemetry lines carry the raw and filtered temperature,
PWM, individual PID terms, mode/state, fan state, and the measured bus voltage,
current, and power, among other fields. The backend parses these with a single regular
expression and both broadcasts them to the GUI and logs them to a CSV.

### 4.5 Control strategy

The firmware implements three control modes (Figure 4.4):

- **AUTO** — the PID loop continuously drives the heater PWM toward the set-point.
- **MANUAL** — a fixed PWM is applied directly (used for diagnostics).
- **SMART** — the loop runs PID until the temperature is stable within ±0.5 °C for a
  sustained window, then *locks* the equilibrium PWM. This is the mode used by the
  automated tester, because a stable, locked steady-state PWM is exactly what is needed
  to read off the equilibrium operating point.

```
        ┌────────┐   stable ±0.5°C for 8 s    ┌────────┐
        │  PID    │ ─────────────────────────▶ │  HOLD   │
 SP set │ (drive) │                            │ (lock   │
 ──────▶│         │ ◀───────────────────────── │  PWM)   │
        └────────┘   set-point change /        └────────┘
                     error grows beyond band
```

**Figure 4.4** — SMART-mode finite-state machine.

**Table 4.3 — Equilibrium-detection parameters**

| Parameter | Value | Purpose |
|---|---|---|
| Stability band | ±0.5 °C | Defines "stable" |
| Soak window | 8 s | Sustained-stability requirement to enter HOLD |
| Temperature filter | EMA (α configurable) | Reject sensor noise/glitches |
| EqPWM convergence | < 0.5 PWM units change | Backend confirms steady state before recording |

To suppress sensor noise the firmware applies an exponential moving average to the
thermocouple reading, plus glitch rejection and a stuck-sensor watchdog. The backend
independently confirms convergence by checking that the equilibrium-PWM estimate has
settled (changes of less than 0.5 PWM units) before it records a data point — a
double check that the system is genuinely at steady state.

### 4.6 Thermal metric

At each recorded operating point the backend computes the comparative metric

> R_th = ΔT ⁄ P,  where ΔT = T − T_amb and P is the measured heater power,

reported in °C/W (a lower value is a better heatsink). The reciprocal conductance
(k = P⁄ΔT) and an extrapolated maximum temperature at full power are also reported as
convenience figures. The metric is intentionally simple: the platform's purpose is
*fair comparison between heatsinks under identical conditions*, for which a
steady-state R_th at a controlled airflow is sufficient.

### 4.7 Automated tester workflow

The student-facing procedure is reduced to a single action sequence (Figure 4.5):

```
1. Plug in ESP32 (USB)  →  2. Open GUI  →  3. Connect (guided)
4. Enter heatsink ID    →  5. Press "Start Test"
6. System steps each set-point: drive → soak → detect equilibrium → record
7. Results CSV exported automatically
8. Swap heatsink, repeat from step 4
```

**Figure 4.5** — Automated tester sequence.

For each programmed set-point the backend commands SMART mode, waits for equilibrium,
records the steady-state row (temperature, power, PWM, R_th, environmental fields), and
advances to the next set-point. **On completion — and on manual stop or fault — the
backend sends `SET RUN OFF`** to de-energise the heater, satisfying requirement R5
that the heater never be left on unattended. A short fan cool-down follows before the
fan is stopped.

### 4.8 Data pipeline and CSV schema

Two CSV products are generated. A high-rate **raw log** captures every telemetry frame
(schema version 4) for detailed analysis, and a **results CSV** captures one row per
set-point with the comparative metrics and metadata (heatsink ID, run ID, timestamp).
The schema carries a version field so that older files remain interpretable as fields
are added; placeholder columns for airspeed, differential pressure, and humidity are
reserved in the schema even before those sensors are wired, so the format is stable
across hardware upgrades.

### 4.9 Virtual MCU simulator

To allow development and teaching without hardware, the backend includes a virtual MCU
that emulates the firmware's telemetry and command responses. Selecting the `VIRTUAL`
port in the GUI exercises the full workflow — including equilibrium detection and CSV
export — with no ESP32 attached. This satisfies requirement R7 and was used
extensively during development of the workflow and safety logic.

### 4.10 Experimental method

> _Document exactly how you ran your validation so it is reproducible._

- **Samples tested:** _[FILL: list heatsinks — ID, material, fin geometry, footprint.]_
- **Set-point series:** _[FILL: e.g. 40, 50, 60, 70, 80 °C.]_
- **Fan setting:** _[FILL: fixed fan % or measured airspeed; state it explicitly.]_
- **Ambient conditions:** _[FILL: ambient temperature and, if available, humidity.]_
- **Soak/stability criteria:** ±0.5 °C for 8 s (as configured).
- **Repetitions:** _[FILL: number of repeat runs per heatsink for repeatability.]_
- **Mounting:** _[FILL: thermal interface used between copper plate and heatsink,
  clamping method — these strongly affect R_th and must be controlled and reported.]_

---

## 5. Results and Measurements

> **All numerical results in this chapter are placeholders.** Replace each `‹FILL: …›`
> with your measured data, and insert the corresponding plots exported from the GUI or
> generated from the raw CSV logs.

### 5.1 Overview of test campaign

_[FILL: how many heatsinks, how many runs, total data points, date range.]_

### 5.2 Step response and equilibrium detection

Figure 5.1 shows a representative temperature trace for a single set-point: the PID
drive phase, entry into the stability band, and the locked HOLD state.

**Figure 5.1** — _[FILL: temperature vs. time for one set-point, annotated with the
moment HOLD was entered.]_

Observed time-to-equilibrium: _[FILL: e.g. ‹…› s at 60 °C set-point]_. Steady-state
temperature ripple in HOLD: _[FILL: ± ‹…› °C]_, consistent with the ±0.5 °C target.

### 5.3 Steady-state power vs. temperature

**Figure 5.2** — _[FILL: dissipated power P vs. set-point temperature for each
heatsink.]_

As expected, the power required to hold a given ΔT _[FILL: increases / scales]_ with
set-point; a better heatsink requires _[FILL: more / less]_ power to reach the same
temperature because it rejects heat more effectively.

### 5.4 Comparative results

**Table 5.1 — Measured results per heatsink** _(one block per heatsink, or one row per
set-point)_

| Heatsink ID | Set-point (°C) | T (°C) | T_amb (°C) | ΔT (°C) | P (W) | R_th (°C/W) |
|---|---|---|---|---|---|---|
| ‹FILL› | 40 | ‹…› | ‹…› | ‹…› | ‹…› | ‹…› |
| ‹FILL› | 60 | ‹…› | ‹…› | ‹…› | ‹…› | ‹…› |
| ‹FILL› | 80 | ‹…› | ‹…› | ‹…› | ‹…› | ‹…› |

**Figure 5.3** — _[FILL: bar/line chart of R_th across heatsinks at a common
set-point.]_

Ranking of tested heatsinks (best → worst): _[FILL]_. The difference between the best
and worst sample was _[FILL: ‹…› °C/W, i.e. ‹…› %]_.

### 5.5 Repeatability and uncertainty

**Table 5.2 — Repeatability / uncertainty budget**

| Source | Estimate | Notes |
|---|---|---|
| Thermocouple (MAX6675) | ±‹FILL› °C | Quantisation + sensor accuracy |
| Power (INA226) | ±‹FILL› % | Voltage × current |
| Run-to-run repeatability | ±‹FILL› °C/W | From repeated runs of same heatsink |
| Mounting/interface variation | ±‹FILL› | Dominant in many cases — discuss |

Combined uncertainty on R_th: _[FILL: ± ‹…› °C/W]_ — _[FILL: state method, e.g.
root-sum-square propagation.]_

---

## 6. Discussion

### 6.1 Answering the research questions

- **RQ1 (stable set-point control).** _[FILL: cite the ripple/repeatability numbers
  from 5.2 and 5.5 to argue the platform holds temperature well enough for a
  repeatable measurement.]_
- **RQ2 (automatic equilibrium detection).** The dual check — firmware stability band
  plus backend EqPWM convergence — _[FILL: worked reliably / required tuning of …].
  Discuss any false triggers or premature HOLD entry observed._
- **RQ3 (single-button workflow + safe shutdown).** The workflow reduced operator
  actions to one button, and `SET RUN OFF` fired on every termination path tested
  (normal, manual stop, fault). _[FILL: confirm you verified each path.]_
- **RQ4 (meaningful discrimination).** _[FILL: the measured R_th spread of ‹…› °C/W
  was/was not larger than the combined uncertainty, so the platform can/cannot
  distinguish the tested samples.]_ This is the key validity argument — tie it
  explicitly to Section 5.5.

### 6.2 Sources of error and their control

The dominant practical error source in this class of measurement is the **thermal
interface and mounting** between the copper plate and the heatsink base, which can
swamp genuine differences between samples if not controlled. _[FILL: describe how you
standardised mounting and how much variation remained.]_ Airflow uniformity, ambient
drift during long test campaigns, and thermocouple placement are secondary
contributors.

### 6.3 Design evaluation

The software-first architecture proved valuable: workflow and safety features were
iterated rapidly against the virtual simulator and deployed without re-flashing. The
strict tier interface kept the safety-critical loop stable. _[FILL: add any friction
you encountered, e.g. protocol-parser brittleness, GUI edge cases.]_

### 6.4 Limitations

- Airspeed is currently *commanded* (fan %) rather than *measured/controlled*, so
  comparisons assume the fan produces repeatable airflow at a given setting.
- There is no independent hardware safety watchdog; safety relies on the firmware and
  backend logic.
- The thermal metric is a single steady-state R_th and does not capture transient
  behaviour (thermal time constant) in depth.
- _[FILL: any limitations specific to your test campaign — small sample count, single
  ambient condition, etc.]_

---

## 7. Conclusion

This thesis presented the design, implementation, and validation of an automated
wind-tunnel platform for heatsink thermal characterisation. The system meets its core
requirements: it reaches and holds set-point temperatures, detects thermal equilibrium
automatically, records steady-state temperature and power, exports versioned CSV
results, and reduces the student procedure to a single button while guaranteeing the
heater is de-energised on every termination path. _[FILL: one or two sentences stating
your headline validation result — repeatability and whether the platform distinguished
the tested heatsinks.]_

The principal contribution is a robust, safe, and genuinely usable
laboratory-automation system built on a clean three-tier architecture, demonstrating
that a low-cost microcontroller platform can deliver instrument-grade workflow and
safety for a teaching context. _[FILL: restate the answer to RQ4 in one sentence.]_

---

## 8. Future Work and Recommendations

Drawn from the project's prioritised backlog, the highest-value next steps are:

1. **Airflow telemetry and closed-loop airspeed control.** Wiring the anemometer and
   differential-pressure sensors (already accommodated in the schema and parser) would
   let the platform hold a *measured* airspeed, making cross-heatsink comparison
   strictly fair rather than fan-setting-dependent.
2. **Independent hardware safety watchdog.** A separate MCU with its own power that can
   cut the heater regardless of firmware state would close the main remaining safety
   gap.
3. **Environmental logging (humidity, ambient).** Recording ambient conditions per run
   improves repeatability across days, since air density affects heat transfer.
4. **Transient metrics.** Computing the thermal time constant and settling time would
   add a dynamic dimension to the comparison beyond steady-state R_th.
5. **Packaged release and instructor/student modes.** A one-click installer and a
   simplified student view would complete the zero-friction deployment goal.

_[FILL: add anything specific that your results suggest is worth pursuing.]_

---

## 9. References

> _Replace with your actual sources in a consistent style (IEEE or your institution's
> required format). Suggested minimum for a Bachelor thesis: ‹12–20› references._

1. ‹FILL: Heat-transfer textbook — convection and thermal resistance.›
2. ‹FILL: Reference on heatsink thermal resistance / forced-convection performance.›
3. ‹FILL: PID control fundamentals.›
4. ‹FILL: Low-speed wind-tunnel design / flow conditioning (honeycomb).›
5. ‹FILL: ESP32-S3 datasheet (Espressif).›
6. ‹FILL: MAX6675 thermocouple-to-digital converter datasheet.›
7. ‹FILL: INA226 current/power monitor datasheet (Texas Instruments).›
8. ‹FILL: Sensirion SDP510 differential-pressure sensor datasheet.›
9. ‹FILL: FastAPI / WebSocket documentation.›
10. ‹FILL: Any further sources cited in Chapter 3.›

---

## Appendices

### Appendix A — Full serial command reference

_[Reproduce the complete command table from the project README, including ranges and
defaults.]_

### Appendix B — CSV schema (raw + results)

_[Reproduce the full raw-log schema (version 4) and the results-CSV schema, with a
one-line description of each field.]_

### Appendix C — Equipment and software versions

| Item | Detail |
|---|---|
| MCU board | ESP32-S3 DevKit-C1 |
| Firmware build | ‹FILL: version / git commit› |
| GUI / backend | ‹FILL: version / git commit› |
| Python version | ‹FILL› |
| PSU | ‹FILL: 12 V, ‹…› A› |

### Appendix D — Raw data

_[Reference the raw CSV log files used to produce Chapter 5 (filenames, location).
Include representative excerpts if required by your institution.]_

### Appendix E — Heatsink specifications

_[Table of tested heatsinks: ID, material, dimensions, fin count/geometry, mass,
nominal/published R_th if known.]_
