# Adaptive Cruise Control Report

## System design
- Architecture: speed PID for cruise mode and distance PID for follow mode; acceleration is clamped to vehicle limits.
- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).
- Safety features: time-headway policy, minimum distance, emergency braking on low TTC.

## PID tuning methodology and final gains
- Manual tuning with repeated 150s simulations, adjusting gains to meet rise time, overshoot, and steady-state error targets.
- Final gains loaded from tuning_results.yaml (see file for values).

## Simulation results and performance metrics
- Duration: 150.0 s, dt=0.1 s, rows=1501
- Speed rise time (10-90%): 9.50 s
- Speed overshoot: 2.68%
- Speed steady-state error: 0.40 m/s
- Distance steady-state error (mean abs, tail 10%): 16.49 m
- Minimum distance: 8.45 m

### Target checks
- Speed rise time < 10 s: 9.50 s (PASS)
- Speed overshoot < 5%: 2.68% (PASS)
- Speed steady-state error < 0.5 m/s: 0.40 m/s (PASS)
- Distance steady-state error < 2 m: 16.49 m (FAIL)
- Minimum distance > 5 m: 8.45 m (PASS)