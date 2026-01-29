# ACC Simulation Report

## System Design
- **Architecture**: PID-based Control with Mode Switching.
- **Modes**:
    - `cruise`: Maintains set speed (30.0 m/s) using Speed PID.
    - `follow`: Maintains safe distance using Distance PID.
    - `emergency`: Applies max deceleration when TTC < 3.0s.
- **Safety**: 
    - Safe distance model: `d = v * 1.5 + 10.0`.
    - Acceleration clamping: [-8.0, 3.0] m/s^2.

## PID Tuning
Parameters loaded from `tuning_results.yaml`:
- **Speed PID**: Kp=2.0, Ki=0.0, Kd=0.0
- **Distance PID**: Kp=0.3, Ki=0.05, Kd=0.2

## Simulation Performance
### Speed Control
- **Rise Time**: 8.30 s (Target < 10s)
- **Overshoot**: 0.00 % (Target < 5%)
- **Steady-State Error**: 0.14 m/s (Target < 0.5 m/s)

### Distance Control
- **Steady-State Error**: 0.16 m (Target < 2m)

