## HeatsinkLab Wind Tunnel — Feature Backlog

---

## ⚑ END GOAL — Definition of "Project Complete"

> **If an agent is asked to "finish the project", this section defines what finished means.**
> Implement every P0 item and any other backlog item needed until the workflow below works end-to-end without exception.

The project is **not done** until every student can complete the following workflow without assistance, without engineering knowledge, and without any manual steps beyond what is listed:

```
1. Plug ESP32 into lab PC via USB
2. Open GUI (double-click start.bat)
3. Follow guided wizard → select port → click Connect → sensors verified automatically
4. Type heatsink ID (e.g. "HS-03-copper-fin")
5. Press ONE button: "Start Test"
6. Wait — temperatures step automatically, soak, record, step again
7. Results CSV downloads automatically when test finishes
8. Remove heatsink, insert next one, repeat from step 4
```

**The student must NEVER need to:**
- Know what PID is or touch any PID setting
- Know what a COM port is beyond selecting one from a list
- Manually add temperatures one by one
- Click a Download button after the test
- Do anything after pressing Start Test except wait and swap heatsinks

**The project IS done when:**
- The guided connection wizard exists and works (step 3)
- The heatsink ID field exists and is required (step 4)
- Temperature range/batch entry exists so the test list is set up in seconds (step 5)
- The test runs fully automatically — no clicks mid-test (step 6)
- Results CSV downloads automatically on completion (step 7)
- The heater shuts off automatically after every test (safety, step 7)
- Sensor health is verified before allowing a test to start (reliability)

All of the above are software-only changes to `server.py` and `index.html`. No firmware required.

---

## Target CSV Schema (Final)

```text
timestamp, run_id, heatsink_id, sp_temp, temp, amb_temp, pwm_heater, fan_cmd, fan_pwm,
airspeed, delta_p1, delta_p2, humidity_pct, vin, iin, pin, mode, state, event
```

Fields `airspeed`, `delta_p1`, `delta_p2`, `humidity_pct` are reserved placeholders — they will be populated once the corresponding hardware sensors are connected. Preserve them in the schema even before the sensors exist.

---

## Prioritisation Framework

```
Score = 2×Importance + 2×Necessity + 2×Dependency − Effort

Importance  (1–5): impact on heatsink-comparison quality
Necessity   (1–5): required for a usable student lab workflow
Dependency  (0/1): blocks other high-value work
Effort      (1–5): engineering cost / complexity
```

Sort by highest Score first.

---

## Backlog Template

```text
Title:
Goal:
Category: [GUI | Backend | Firmware | Data | Safety | Analysis | Reporting | Build]

Importance (1-5):
Necessity (1-5):
Dependency (0/1):
Effort (1-5):
Score:

Dependencies:
Acceptance Criteria:
- ...

Notes:
```

---

## Backlog (sorted by score, highest first)

---

```text
Title: Safety Layer
Goal: Configurable max-temperature cutoff with a persistent SAFE / RUNNING / FAULT status indicator visible at all times
Category: Safety / GUI / Backend

Importance (1-5): 5
Necessity (1-5): 5
Dependency (0/1): 1
Effort (1-5): 4
Score: 19

Dependencies: none (software-side status indicator can be done now; hardware watchdog MCU is a separate physical build)
Acceptance Criteria:
- GUI shows a persistent status badge at the top: SAFE (grey), RUNNING (green), FAULT (red)
- FAULT is triggered by: temperature exceeding configurable limit, thermocouple stuck, INA226 absent, test stalled indefinitely
- On FAULT: GUI automatically sends SET RUN OFF and blocks further test start until acknowledged
- Instructor can configure max allowed temperature (default 120 C for lab safety)
- Each fault shows a fault code with a human-readable explanation (e.g. "FAULT F02: Thermocouple stuck at 25.0 C for 15s")
- Student can reset FAULT only after manually confirming the issue is resolved (confirm dialog)

Notes: The hardware safety watchdog (separate MCU with independent power) is a physical build item outside this software scope.
This item covers the software-side safety indicator and automatic shutdown logic in server.py and index.html.
```

---

```text
Title: Post-Test Auto Shutdown
Goal: Automatically cut heater power when a test finishes — heater must never stay on unattended
Category: Backend / GUI

Importance (1-5): 5
Necessity (1-5): 5
Dependency (0/1): 0
Effort (1-5): 1
Score: 17

Dependencies: none
Acceptance Criteria:
- When the last temperature step completes its soak and results are recorded: send SET RUN OFF automatically
- Set fan to a low idle speed (e.g. 20%) for 60s cool-down, then SET FAN 0
- Log a TEST_COMPLETE event in the raw CSV
- GUI shows "Test complete — heater off" status message prominently
- If test is manually stopped mid-run: also send SET RUN OFF immediately
- Auto-shutdown also triggers if a FAULT is detected during a test

Notes: Safety-critical. The heater must never remain on after a test finishes.
Currently the firmware stays in RUN ON state indefinitely after a test unless the user manually clicks a button.
This is a one-line fix in the test completion handler in index.html.
```

---

```text
Title: Temperature Range / Batch Entry
Goal: Let students specify a temperature range (start, stop, step) instead of adding temperatures one-by-one
Category: GUI

Importance (1-5): 4
Necessity (1-5): 5
Dependency (0/1): 0
Effort (1-5): 2
Score: 16

Dependencies: none
Acceptance Criteria:
- Tester panel has a "Range" row: Start degC, Stop degC, Step degC with a "Generate List" button
- Clicking Generate populates the temperature list automatically (e.g. 40, 50, 60, 70, 80 C)
- Also support pasting a comma-separated list directly (e.g. "40, 55, 70, 85")
- Generated list is editable — students can remove individual entries before starting
- One-by-one Add button remains available as a fallback
- Default values shown on first open: Start 40, Stop 80, Step 10 (covers typical lab range)

Notes: Currently students must add every temperature individually by typing and clicking Add.
For a 7-point test this is 7x type + click. This is the biggest friction point in the current Tester mode.
```

---

```text
Title: Guided Connection Wizard
Goal: Walk students through device connection with step-by-step instructions instead of a bare port dropdown
Category: GUI / Backend

Importance (1-5): 4
Necessity (1-5): 4
Dependency (0/1): 1
Effort (1-5): 3
Score: 15

Dependencies: Sensor Health Check (merge as last wizard step)
Acceptance Criteria:
- On first open (or when not connected): a wizard panel guides the student:
    Step 1 — "Plug the USB cable into the ESP32 and into this PC" [Refresh ports] shows detected ports
    Step 2 — "Select the COM port from the list and click Connect"
    Step 3 — "Checking device..." with animated spinner during 2.5s handshake (not a silent wait)
    Step 4 — "Device connected" or "Connection failed: try a different USB cable or port"
- If handshake fails: show actionable message ("Check USB cable, check Device Manager, try replugging")
- After connect: show sensor health check before allowing test start (see Sensor Health Check item)
- Wizard can be dismissed by experienced users who already know what to do

Notes: Currently there is zero guidance. Students see a bare COM port dropdown and a Connect button.
The 2.5s handshake is completely silent — no indication anything is happening.
This is the first thing new students encounter and currently causes the most confusion.
```

---

```text
Title: Airflow Telemetry Integration
Goal: Log and display airspeed and differential pressure once hardware sensors are connected
Category: Backend / GUI / Data

Importance (1-5): 5
Necessity (1-5): 4
Dependency (0/1): 1
Effort (1-5): 3
Score: 15

Dependencies: Hardware sensor wiring + firmware update to output airspeed/delta_p in telemetry
Acceptance Criteria:
- server.py TELEM_RE parses airspeed (m/s) and delta_p1, delta_p2 (Pa) from telemetry
- Live values shown in GUI sidebar
- Fields logged to raw CSV (schema_version bumped)
- Results CSV includes avg airspeed and avg delta_p per test point
- If sensor is absent (value = 0 or NaN): show "—" in display, do not block test

Notes: Follow the 4-step sensor extension pattern in CLAUDE.md.
The firmware output format must be updated when sensors are physically wired.
CSV schema already reserves these column names — do not rename them.
This item requires firmware changes — confirm with user before starting.
```

---

```text
Title: Auto Result Download on Test Completion
Goal: Automatically save/download both CSVs when a test finishes — no manual button clicks required
Category: GUI / Backend

Importance (1-5): 4
Necessity (1-5): 4
Dependency (0/1): 0
Effort (1-5): 2
Score: 14

Dependencies: Post-Test Auto Shutdown (should trigger at the same moment)
Acceptance Criteria:
- When test completes: Results CSV is automatically downloaded to the browser Downloads folder
- Raw CSV is already being written server-side — ensure it is finalized (flush + close) on test end
- GUI shows "Results saved: heatsink_results_HS-01_2026-03-29.csv" confirmation message
- Student does not need to click any download button
- If browser blocks auto-download: show a prominent "Download Results" button as fallback
- Raw CSV filename includes heatsink ID and timestamp

Notes: Currently students must click two separate download buttons after the test.
Many will close the browser tab immediately, losing the in-memory Results table.
```

---

```text
Title: Startup Sensor Health Check
Goal: Verify all required sensors are responding correctly right after connection, before allowing a test to start
Category: GUI / Backend

Importance (1-5): 4
Necessity (1-5): 4
Dependency (0/1): 0
Effort (1-5): 3
Score: 13

Dependencies: Guided Connection Wizard (health check becomes the final step)
Acceptance Criteria:
- After successful handshake: backend reads 3 telemetry frames and checks:
    Thermocouple: temperature is non-zero, not stuck, and in plausible range (15–45 C at room temp)
    INA226: voltage reading is non-zero (confirms power monitoring is active)
- GUI shows a sensor checklist:
    GREEN  Thermocouple: 23.4 C OK
    GREEN  Power monitor: 12.1V OK
    RED    Power monitor: 0V — check INA226 wiring
- Start Test button is disabled if any required sensor is RED
- Optional sensors (airspeed, pressure, humidity) show YELLOW "not connected" — test still allowed
- Student sees clear fix instructions for each failed check

Notes: Without INA226 power readings the R_th calculation produces invalid results (division near zero).
Currently the system silently produces NaN or infinite R_th if INA226 is not connected.
```

---

```text
Title: Dual-File Release Build
Goal: A single installer for the GUI and a pre-compiled firmware binary for lab technicians with no dev tools
Category: Build

Importance (1-5): 3
Necessity (1-5): 5
Dependency (0/1): 1
Effort (1-5): 4
Score: 13

Dependencies: all core features must be stable before packaging
Acceptance Criteria:
- GUI installer: single .exe or .bat that installs Python dependencies and creates a desktop shortcut
- Firmware binary: pre-built .bin file that can be flashed via esptool (no PlatformIO needed)
- Clear README for lab technician: "Run installer, plug in ESP32, run flash_firmware.bat"
- Version number embedded in GUI footer and firmware CFG output so mismatches are detectable

Notes: End goal is that a lab technician with no programming knowledge can set up the entire system.
Firmware binary also allows re-flashing a corrupted or replaced ESP32 without a dev environment.
```

---

```text
Title: Heatsink ID Input
Goal: Let students label each test with a heatsink identifier so result files are self-documenting
Category: GUI / Data

Importance (1-5): 3
Necessity (1-5): 4
Dependency (0/1): 0
Effort (1-5): 2
Score: 12

Dependencies: none
Acceptance Criteria:
- Tester panel has a "Heatsink ID" text field above the Start button (e.g. "HS-01-copper-fin")
- ID is included in:
    Results CSV filename: heatsink_results_HS-01_2026-03-29T143022.csv
    Results CSV header row
    Raw CSV filename: serial_HS-01_2026-03-29T143022.csv
- If field is empty: warn student before allowing test start ("Please enter a heatsink ID")
- ID is remembered until manually cleared (so student doesn't retype for re-runs of the same heatsink)

Notes: Currently all result files have generic timestamped names.
Students have no way to tell which file belongs to which heatsink without opening them.
```

---

```text
Title: Experiment Presets
Goal: Save and load full test configurations (temperature list, fan speed, soak time) with a name
Category: GUI

Importance (1-5): 3
Necessity (1-5): 3
Dependency (0/1): 0
Effort (1-5): 2
Score: 8

Dependencies: Temperature Range Entry recommended first
Acceptance Criteria:
- "Save Preset" button stores current test config (temps, fan %, soak time) under a user-chosen name
- "Load Preset" dropdown fills all fields instantly
- Presets persisted in browser localStorage (no server-side storage needed)
- Default presets shipped: "Lab Standard 40-80 step 10", "Quick 3-point", "Natural Convection"
- Can delete a custom preset

Notes: Useful for instructors who want to standardise the test procedure across student groups.
Reduces setup time when running the same test repeatedly on different heatsinks.
```

---

```text
Title: Tooltips
Goal: Show brief plain-language explanations when hovering over controls and metric readouts
Category: GUI

Importance (1-5): 3
Necessity (1-5): 3
Dependency (0/1): 0
Effort (1-5): 1
Score: 8

Dependencies: none
Acceptance Criteria:
- All buttons, sliders, and metric readouts have a tooltip on hover
- Written in plain language — no engineering jargon
- Examples:
    Setpoint: "Target temperature in °C that the heater will try to reach"
    R_th: "Thermal resistance — how well this heatsink transfers heat. Lower is better."
    EqPWM: "Heater power at steady state (0–255). Lower means less power needed = better heatsink."
    Fan %: "Cooling fan speed. 0 = no forced airflow. 100 = maximum airflow."
- Tooltips updated as new features are added

Notes: Students have no PID background. Every unexplained number causes confusion and instructor questions.
```

---

```text
Title: In-App User Manual
Goal: Built-in help panel explaining all features and how to interpret results, available offline
Category: GUI

Importance (1-5): 2
Necessity (1-5): 4
Dependency (0/1): 0
Effort (1-5): 2
Score: 8

Dependencies: tooltips recommended first
Acceptance Criteria:
- A help button opens a panel or modal with the full user manual embedded in the page
- Sections: Getting Started, Running a Test, Understanding Results, Troubleshooting
- Explains R_th, k, EqPWM in plain language with typical example values
- Explains how to import the CSV into Excel using the Power Query formula (see CSV Export Customisation item)
- Available offline (embedded in index.html, not an external link)
- Current MANUAL.md content migrated here and kept in sync

Notes: MANUAL.md currently exists as a standalone file that students are unlikely to find.
Embedding it in the GUI ensures it is always one click away.
```

---

```text
Title: Graph Cursor / Probe Tool
Goal: Allow students to read exact values at any point in time on the live graph
Category: GUI

Importance (1-5): 3
Necessity (1-5): 2
Dependency (0/1): 0
Effort (1-5): 1
Score: 7

Dependencies: none
Acceptance Criteria:
- Cursor mode toggled on/off with a button
- Cursor slides along the time axis as mouse moves over the graph
- Tooltip shows all active series values at the cursor position
- Delta mode: click two points to see delta-T, delta-PWM, delta-time between them
- Does not interfere with normal chart pan/zoom

Notes: Useful for students reading values at specific moments (e.g. exactly when HOLD state was entered).
Low effort — Chart.js has crosshair plugin support built in.
```

---

```text
Title: CSV Export Customisation
Goal: Let users choose which columns to include in the exported CSV before downloading
Category: GUI / Data

Importance (1-5): 3
Necessity (1-5): 2
Dependency (0/1): 0
Effort (1-5): 2
Score: 6

Dependencies: none
Acceptance Criteria:
- When triggering CSV download: show a column-selection panel with checkboxes
- Checkboxes grouped by category: Temperature, PID Terms, Fan, Power, Metadata, Future Sensors
- Default selection: columns most relevant for student lab analysis (exclude raw PID internals)
- "Select all" and "Reset to default" buttons
- Companion .txt file with the matching Power Query formula is included in the download

Power Query formula (all current + future columns):
= Table.TransformColumnTypes(
    #"Promoted Headers",
    {
        {"timestamp_iso", type datetimezone},
        {"elapsed_s", type number},
        {"raw_temp_c", type number},
        {"temp_filtered_c", type number},
        {"temp_smooth_c", type number},
        {"pwm", Int64.Type},
        {"p_term", type number},
        {"i_term", type number},
        {"d_term", type number},
        {"pid_out", type number},
        {"pid_bias", type number},
        {"setpoint_bias_c", type number},
        {"setpoint_c", type number},
        {"effective_setpoint_c", type number},
        {"fan_speed_pct", type number},
        {"fan_pwm_raw", Int64.Type},
        {"mode", type text},
        {"state", type text},
        {"manual_pwm_cmd", type number},
        {"hold_pwm", type number},
        {"enter_progress_pct", type number},
        {"exit_progress_pct", type number},
        {"abs_error_c", type number},
        {"run_state", type text},
        {"fan_inverted", type number},
        {"vin", type number},
        {"iin", type number},
        {"pin", type number},
        {"airspeed", type number},
        {"delta_p1", type number},
        {"delta_p2", type number},
        {"humidity_pct", type number}
    },
    "en-US"
)

Notes: Lower priority than the core workflow features.
Students at this stage don't need column selection — the full CSV is acceptable.
The Power Query formula above must be updated each time a new sensor column is added (bump schema_version too).
```

---

```text
Title: Closed-Loop Fan Airspeed Control
Goal: Control fan speed by feedback to maintain a target airspeed rather than a fixed PWM percentage
Category: Backend / Firmware

Importance (1-5): 4
Necessity (1-5): 3
Dependency (0/1): 0
Effort (1-5): 4
Score: 6

Dependencies: Airspeed sensor hardware + Airflow Telemetry Integration
Acceptance Criteria:
- GUI has a "Target airspeed (m/s)" input in the Tester panel alongside fan %
- Backend runs a simple feedback loop: adjust fan PWM until measured airspeed matches target
- Enables fair heatsink comparison: identical airspeed for all heatsinks tested
- Manual fan % control remains as fallback
- Results CSV records actual measured airspeed per test step, not just commanded fan %

Notes: Requires both software changes AND the airspeed sensor to be physically connected.
Deprioritised until airspeed hardware arrives.
```

---

```text
Title: Humidity and Ambient Conditions Logging
Goal: Log ambient humidity per test point for improved experiment repeatability
Category: Backend / Data

Importance (1-5): 3
Necessity (1-5): 2
Dependency (0/1): 0
Effort (1-5): 2
Score: 6

Dependencies: Humidity sensor hardware (e.g. SHT31 on I2C) + firmware update
Acceptance Criteria:
- Follow the 4-step sensor extension pattern in CLAUDE.md
- server.py parses humidity_pct from telemetry, broadcasts in telemetry message
- Field added to CSV_FIELDS (schema_version bumped)
- Shown in GUI sidebar
- Results CSV includes avg humidity per test point
- If sensor absent: field shows dash, test not blocked

Notes: Humidity affects air density and thus heat transfer.
Logging it enables students to compare results across different days and conditions.
Deprioritised until sensor hardware arrives.
```

---

```text
Title: Expert / Instructor Mode
Goal: Toggle between a simplified student view and a full-featured expert view
Category: GUI

Importance (1-5): 2
Necessity (1-5): 2
Dependency (0/1): 0
Effort (1-5): 3
Score: 5

Dependencies: none
Acceptance Criteria:
- Toggle between Student mode (test controls only) and Expert mode (all PID tuning, manual PWM, raw telemetry)
- GUI remembers last mode in localStorage
- In Student mode: PID sliders, manual PWM, bias inputs hidden
- In Expert mode: everything visible, same as current GUI
- Instructors can optionally lock mode so students cannot switch to Expert

Notes: The current GUI shows PID tuning sliders to students who don't need them.
This causes accidental parameter changes and confusion.
Lower priority — implement after guided wizard, batch entry, and auto-download are complete.
```

---

```text
Title: PID Learning Overlay
Goal: Visualise P, I, D term contributions separately with hints for understanding PID behaviour
Category: GUI

Importance (1-5): 2
Necessity (1-5): 1
Dependency (0/1): 0
Effort (1-5): 3
Score: 3

Dependencies: Expert / Instructor Mode recommended first
Acceptance Criteria:
- Toggleable overlay showing P, I, D contributions as separate chart series
- Hints shown for extreme values: "High overshoot: lower Kp or increase Kd"
- Only visible in Expert mode

Notes: Educational feature for advanced PID labs.
The primary use case of this project (heatsink comparison) does not involve PID tuning by students.
Very low priority — implement only after all core workflow features are done.
```

---

## Current P0 Priorities (Implement Next)

> These are the items that stand between the current state and the End Goal above.
> Implement them in order. When all five are done, the 8-step student workflow is complete.
> All are software-only changes to `server.py` and `index.html`. No firmware required.

| Priority | Item | Score | End Goal Step | Why |
|----------|------|-------|---------------|-----|
| 1 | Post-Test Auto Shutdown | 17 | Step 7 (safety) | Heater must not stay on after test — safety-critical |
| 2 | Temperature Range / Batch Entry | 16 | Step 5 | Biggest friction point — students can't add 7 temps one-by-one |
| 3 | Guided Connection Wizard | 15 | Step 3 | Biggest confusion point — students don't know what a COM port is |
| 4 | Startup Sensor Health Check | 13 | Step 3 (final) | Prevents silent invalid R_th results if INA226 is not connected |
| 5 | Heatsink ID Input | 12 | Step 4 | Makes result files self-documenting; required before Start Test |
| 6 | Auto Result Download | 14 | Step 7 | Students must not need to click Download — results must save automatically |
