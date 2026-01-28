# ACC Report

## System design
- The ACC uses two PID controllers: a speed controller for free cruising and a distance controller for following.
- Modes are selected by lead availability and TTC: cruise (no lead), follow (lead present), emergency (TTC below threshold).
- Safety features include time-headway spacing, minimum gap enforcement, and emergency braking at the TTC threshold.

## PID tuning methodology and final gains
- Manual tuning was performed to meet rise time, overshoot, and steady-state error targets under the given accel limits.
- Final gains are loaded from tuning_results.yaml at runtime.

Final gains:

```yaml
pid_speed:
  kp: 0.4000
  ki: 0.0200
  kd: 0.1000
pid_distance:
  kp: 0.5000
  ki: 0.0500
  kd: 0.1000
```

## Simulation results and performance metrics
- Speed rise time (10-90%): 8.80 s (target < 10 s)
- Speed overshoot: 2.41 % (target < 5 %)
- Speed steady-state error: 0.216 m/s (target < 0.5 m/s)
- Distance steady-state error (follow mode): 0.802 m (target < 2 m)
- Minimum distance observed: 5.61 m (target > 5 m)