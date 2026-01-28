# ACC Simulation Report

## System design
- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).
- Safety: acceleration clamped to vehicle limits and emergency braking when TTC < threshold.
- Following control: target distance = max(min gap, time headway * ego speed, TTC safety buffer).
- Follow mode allows up to a 5% speed margin to safely close large gaps.

## PID tuning methodology and final gains
- Tuned for fast cruise rise time with minimal overshoot, then adjusted follow gains to stabilize headway tracking.
- Speed PID: kp=0.5, ki=0.0, kd=0.0.
- Distance PID: kp=0.4, ki=0.0, kd=0.05.

## Simulation results and performance metrics
- Rise time (10-90% of 30.0 m/s): 8.4 s.
- Speed overshoot: 0% .
- Speed steady-state error (last 5s): 0 m/s.
- Distance steady-state error (10s steady window before emergency/end): 0.46 m.
- Minimum distance observed: 9.46 m.