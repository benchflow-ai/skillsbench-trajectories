# ACC Simulation Report
## System design
- Architecture: PID-based longitudinal control with cruise, follow, and emergency modes.
- Cruise: speed PID tracks set speed when no lead vehicle is present.
- Follow: distance PID regulates spacing to a time-headway-based desired gap; output is limited by the speed controller to avoid overshooting the set speed.
- Desired gap: min_distance + time_headway * ego_speed with an added closing-rate buffer.
- Emergency: time-to-collision check triggers maximum braking when TTC is below the configured threshold.

## PID tuning methodology and final gains
- Method: manual tuning with acceleration saturation and steady-state bias compensation via integral action.
- Objectives: <10s rise time, <5% overshoot, <0.5 m/s speed steady-state error, <2 m distance steady-state error, min distance >5 m.
```yaml
pid_speed:
  kp: 0.85
  ki: 0.09
  kd: 0.15
pid_distance:
  kp: 1.0
  ki: 0.05
  kd: 0.1
```

## Simulation results and performance metrics
- Speed rise time (10-90%): 8.00 s
- Speed overshoot (cruise only): 4.24 %
- Speed steady-state error (last 10s cruise): 0.399 m/s
- Distance steady-state error (most stable 10s follow window): 1.321 m
- Minimum distance: 18.393 m
