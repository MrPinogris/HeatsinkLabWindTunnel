## PID GUI Ideas (Student Lab Focus)

## Prioritization Framework

Use this scoring model for each backlog item:

- `Importance` (1..5): impact on heatsink-comparison quality.
- `Necessity` (1..5): required for a usable student lab workflow.
- `Dependency` (0 or 1): blocks other high-value work.
- `Effort` (1..5): engineering cost/complexity.
- `Score = 2*Importance + 2*Necessity + 2*Dependency - Effort`

Sort by highest `Score` first.

## Backlog Template

Copy this block for each candidate feature:

```text
Title:
Goal:
Category: [GUI | Firmware | Data | Safety | Analysis | Reporting]

Importance (1-5):
Necessity (1-5):
Dependency (0/1):
Effort (1-5):
Score:

Dependencies:
Acceptance Criteria:
- ...
- ...

Notes:
```

## Suggested Priorities (Given Current Project Goal)

### P0 (Now)

1. Structured experiment workflow
- Add phase markers/events in graph + CSV.
- Add core auto-metrics (rise time, settling, overshoot, steady-state error).

2. Stable/upgrade-proof data model
- Introduce schema versioning (`schema_version`) and run metadata (`run_id`, `heatsink_id`).
- Keep placeholders for upcoming sensors.

3. Safety + reproducibility baseline
- Ensure `RUN ON/OFF`, sensor-fault behavior, and configuration capture per run.

### P1 (Power Sensor Arrival)

1. Add power telemetry
- Log `voltage`, `current`, `power_in`.

2. Equilibrium/dissipation analysis
- Detect steady state and estimate dissipation from power balance.

3. Comparison KPIs
- Per-run summary for heatsink ranking under same conditions.

### P2 (Pressure + Airspeed Sensor Arrival)

1. Airflow telemetry
- Log `airspeed` and `delta_p`.

2. Closed-loop airspeed control
- Add a fan control loop to maintain target airspeed.

3. Condition lock for fair comparison
- Test at fixed setpoint + fixed airspeed + recorded pressure drop.

1. Experiment Presets
- Save/load full test setups (SP, mode, gains, fan, thresholds, y-scale).
- One-click presets like `Step Response`, `Disturbance Test`, `Manual Bias Find`.

2. Guided Lab Mode
- Wizard flow: `Connect -> Preheat -> Run -> Disturb -> Analyze -> Save`.
- Lock irrelevant controls per step to reduce mistakes.

3. Auto Test Scripts
- Scripted sequences:
  - Setpoint steps (`30 -> 60 -> 80 C`)
  - Fan disturbance pulse
  - Hold test (steady-state)
- Write phase markers to CSV.

4. Performance Metrics Auto-Compute
- Show `rise time`, `settling time`, `overshoot`, `steady-state error`, `IAE/ISE`.
- Compute metrics per phase and export.

5. Cursor/Probe Tool
- Click graph to read exact values at time `t`.
- Delta mode between two points: `ΔT`, `ΔPWM`, `Δt`, slope.

6. Annotation Markers
- Buttons to add markers (`Fan ON`, `Heatsink Changed`, `Mode Switch`) to CSV/log.
- Draw vertical marker lines with labels on graph.

7. Safety Layer
- Configurable max-temp cutoff, max-PWM duration, sensor-fault lockout.
- Big status indicator: `SAFE / RUNNING / FAULT`.

8. Heatsink Comparison View
- Overlay multiple runs from CSV.
- Normalize time to event (e.g., step start).
- Compare key metrics side by side.

9. Student Report Export
- Generate PDF/HTML report with:
  - Graphs
  - Config used
  - Metrics
  - Student notes
  - Pass/fail checks

10. PID Learning Overlay
- Show `P`, `I`, `D`, and output decomposition with hints:
  - High overshoot: lower `Kp` or raise `D`
  - Steady-state offset: increase `Ki` or bias

11. Access Levels
- `Student mode`: limited controls.
- `Instructor mode`: full tuning, thresholds, scripting.

12. Scoring/Checklist
- Define rubric targets (e.g., overshoot < 5%, settling < 120s).
- Auto-score each run for objective grading.

## Suggested Next Two

1. Add phase markers + annotations in CSV/graph.
2. Add automatic rise/settling/overshoot metrics panel.
