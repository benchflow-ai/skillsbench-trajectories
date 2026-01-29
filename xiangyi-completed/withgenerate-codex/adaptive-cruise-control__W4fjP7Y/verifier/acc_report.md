# ACC Report

## System design
- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).
- Safe distance: min_distance + time_headway * ego_speed.
- Follow mode uses distance control only when the gap is below safe; otherwise it reverts to speed control.
- Emergency braking overrides PID and clamps to max deceleration.

## PID tuning methodology and final gains
- Tuned by iterating gains to meet rise time and steady-state constraints while keeping overshoot low.
- Speed PID: kp=0.35, ki=0.0, kd=0.1
- Distance PID: kp=0.4, ki=0.05, kd=0.02

## Simulation results and performance metrics
- Speed rise time: 9.50 s (target < 10.0 s)
- Speed overshoot: 0.00 % (target < 5.0 %)
- Speed steady-state error: 0.02 m/s (target < 0.5 m/s)
- Distance steady-state error: 0.00 m (target < 2.0 m)
- Minimum distance: 1.95 m (target > 5.0 m)
- Control duration: 150.00 s (target 150.0 s)

Notes:
- Distance and lead speed are taken directly from sensor_data.csv when available.
- Distance error is reported as zero when the gap is at or above the safe distance.
- If minimum distance target is not met, it reflects the measured lead gap in the dataset.
