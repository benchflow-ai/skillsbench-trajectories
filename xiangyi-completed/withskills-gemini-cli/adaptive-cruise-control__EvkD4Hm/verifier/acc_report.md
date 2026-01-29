# Adaptive Cruise Control Simulation Report

## 1. System Design
The ACC system is implemented using a hierarchical control architecture:
- **Supervisor**: A state machine determines the operating mode ('cruise', 'follow', 'emergency') based on sensor inputs (lead vehicle detection, Time-to-Collision).
- **Controllers**: Two distinct PID controllers manage longitudinal dynamics:
  - `PID_Speed`: Maintains the set speed (30 m/s) in free-flow conditions.
  - `PID_Distance`: Maintains a safe time-gap (1.5s) when following a lead vehicle.
- **Safety**: Acceleration is clamped to vehicle limits [-8.0, 3.0] m/s^2. Emergency braking is triggered if TTC < 3.0s.

## 2. PID Tuning Methodology
Gains were optimized using a randomized search algorithm against synthetic scenarios:
- **Speed Loop**: Tuned on a 0-30m/s step response to minimize rise time and overshoot.
- **Distance Loop**: Tuned on a closing-gap scenario to minimize steady-state error and prevent safety violations.

### Final Gains
#### Speed Controller
- Kp: 4.123
- Ki: 0.016
- Kd: 1.720
#### Distance Controller
- Kp: 2.570
- Ki: 0.946
- Kd: 0.415

## 3. Simulation Results
The system was tested on a 150s real-world driving scenario.

### Speed Control Performance (Cruise Phase)
- **Rise Time (0-30 m/s)**: 8.00 s (Target: <10s)
- **Overshoot**: 0.27% (Target: <5%)
- **Steady-State Error**: 0.220 m/s (Target: <0.5 m/s)

### Distance Control Performance (Follow Phase)
- **Minimum Distance Maintained**: 18.36 m (Target: >5m)
- **Mean Distance Error**: 1.43 m
- **Max Deceleration**: -8.00 m/s^2

### Conclusion
The ACC system met all safety and performance requirements.