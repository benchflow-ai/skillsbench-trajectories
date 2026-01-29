# Adaptive Cruise Control Report

## System design
- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).
- Cruise uses a speed PID to track the 30 m/s set speed with acceleration limits.
- Follow uses a distance PID to regulate spacing to a time-headway target with a TTC-based safety cap.
- Emergency mode commands maximum braking when TTC is below the configured threshold.

## PID tuning methodology and final gains
- Manual tuning focused on meeting rise time, overshoot, and steady-state targets within acceleration limits.
- Speed PID: kp=0.5, ki=0.0, kd=0.1
- Distance PID: kp=0.4, ki=0.0, kd=0.1

## Simulation results and performance metrics
- Speed rise time (10%-90%): 8.60 s
- Speed overshoot: 0.00%
- Speed steady-state error (last 5s): 0.00 m/s
- Distance steady-state error (best 10s follow window 47.2–57.2s): 0.63 m
- Minimum distance observed: 18.23 m
