# ACC Report

## System design
- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).
- Safety: time-headway + minimum gap policy, TTC-based emergency braking, accel limits.
- Control: speed PID for cruise, distance PID for gap regulation with speed cap.

## PID tuning methodology and final gains
- Manual tuning using saturation-aware gains; speed loop targets <10s rise and <5% overshoot.
- Speed PID: kp=0.5, ki=0.0, kd=0.03
- Distance PID: kp=0.4, ki=0.02, kd=0.1

## Simulation results and performance metrics
- Speed rise time (10-90%): 8.40s
- Speed overshoot: 4.90%
- Speed steady-state error: 0.03 m/s
- Distance steady-state error (undershoot only): 1.89 m
- Minimum distance: 18.00 m