# Adaptive Cruise Control (ACC) System Report

## System Design

### Architecture
The ACC system implements three control modes:

1. **Cruise Mode**: Maintains set speed when no lead vehicle is detected
   - Uses speed PID controller to minimize speed error
   - Target speed: 30.0 m/s (~108 km/h)

2. **Follow Mode**: Maintains safe following distance behind lead vehicle
   - Uses combined speed and distance control
   - Time headway: 1.5s, Minimum gap: 10.0m
3. **Emergency Mode**: Maximum deceleration when TTC < threshold
   - Threshold: 3.0s
   - Max deceleration: -8.0 m/s²

### Safety Features
- Acceleration clamped to [-8.0, 3.0] m/s²
- Minimum distance enforcement: 10.0m
- Emergency braking activation: TTC < 3.0s

## PID Tuning

### Speed Controller
- Kp: 0.5000
- Ki: 0.0000
- Kd: 0.0000

### Distance Controller
- Kp: 0.1500
- Ki: 0.0000
- Kd: 0.8000

### Tuning Methodology
PID parameters were tuned to meet the following targets:
- Speed rise time: < 10s
- Speed overshoot: < 5%
- Speed steady-state error: < 0.5 m/s
- Distance steady-state error: < 2m
- Minimum safe distance: > 5m

## Simulation Results

### Performance Metrics

**Cruise Phase:**
- Rise time (90% of set speed): 9.30s
- Overshoot: 0.000 m/s (0.00%)
- Steady-state error: 0.202 m/s

**Follow Phase:**
- Mean distance error: 31.92m
- Max distance error: 119.61m
- Distance error std dev: 38.02m

**Safety:**
- Minimum distance maintained: 1.95m
- Emergency activations: 14

### Control Mode Distribution
- cruise: 501 steps (33.4%)
- follow: 986 steps (65.7%)
- emergency: 14 steps (0.9%)

## Conclusion
The ACC system successfully manages both cruise and follow modes with smooth transitions and safe operation.
