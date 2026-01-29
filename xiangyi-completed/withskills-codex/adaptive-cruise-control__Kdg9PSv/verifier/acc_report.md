# Adaptive Cruise Control Report

## System design
- Dual PID structure: speed PID for cruise mode and distance PID for following.
- Mode logic: cruise (no lead), follow (lead present), emergency (TTC below threshold).
- Safety features: time headway + minimum gap policy, emergency braking override, accel limits.

## PID tuning methodology and final gains
- Manual tuning to meet rise time, overshoot, and steady-state error targets under accel limits.
- Distance controller tuned to maintain time headway with minimal steady-state error.

Final gains (from tuning_results.yaml):
- Speed PID: kp=0.6, ki=0.0, kd=0.05
- Distance PID: kp=1.2, ki=0.01, kd=1.2

## Simulation results and performance metrics
- Rise time (10-90%): 8.30s
- Speed overshoot: 0.00%
- Speed steady-state error: 0.017 m/s
- Distance steady-state error: 1.432 m
- Minimum distance: 8.045 m

Targets: rise time <10s, overshoot <5%, speed SSE <0.5 m/s, distance SSE <2m, minimum distance >5m.