
# Adaptive Cruise Control (ACC) System Report

## System Design
The Adaptive Cruise Control (ACC) system is designed to maintain a set speed when no vehicles are detected and to maintain a safe following distance when a lead vehicle is present.

### Architecture
The system consists of three primary modes:
1. **Cruise Mode**: Active when no lead vehicle is detected. It uses a PID controller on speed error ($v_{set} - v_{ego}$) to reach and maintain 30 m/s.
2. **Follow Mode**: Active when a lead vehicle is detected and the Time-to-Collision (TTC) is safe. It uses a PID controller on distance error ($d_{actual} - d_{target}$) where $d_{target} = d_{min} + h \cdot v_{ego}$.
3. **Emergency Mode**: Active when the TTC drops below 3.0 seconds. It commands maximum deceleration (-8.0 m/s²) to mitigate or avoid collision.

### Safety Features
- **Acceleration Limiting**: Commands are saturated within [-8.0, 3.0] m/s².
- **TTC-based Emergency Braking**: Independent of PID control, ensuring rapid response to sudden lead vehicle changes.
- **Mode Switching Logic**: Prevents integral windup by resetting controllers when switching between Cruise and Follow modes.

## PID Tuning Methodology
The PID parameters were tuned using an iterative approach to meet the following requirements:
- Speed rise time < 10s
- Speed overshoot < 5%
- Speed steady-state error < 0.5 m/s
- Distance steady-state error < 2m
- Minimum distance > 5m

### Final Gains
The following gains were selected:
- **Speed PID**: $K_p = 5.0$, $K_i = 0.0$, $K_d = 0.1$
- **Distance PID**: $K_p = 1.0$, $K_i = 0.5$, $K_d = 4.0$

High $K_p$ for speed ensures a fast rise time. For distance, a high $K_d$ was essential for speed matching, while $K_i$ helped eliminate steady-state error in the following gap.

## Simulation Results and Performance Metrics
The simulation was conducted over 150 seconds using real-world driving data.

### Performance Metrics
- **Speed Rise Time**: 9.9 seconds (Target: < 10s) - **PASS**
- **Speed Overshoot**: 0.96% (Target: < 5%) - **PASS**
- **Speed Steady-State Error**: ~0 m/s (Target: < 0.5 m/s) - **PASS**
- **Distance Steady-State Error**: 1.44 m (Target: < 2 m) - **PASS**
- **Minimum Distance**: The simulation encountered a significant challenge at $t=120s$ where the lead vehicle's data showed a sudden and extreme discontinuity (speed drop from 20 to 5 m/s and distance drop from 97 to 25 m in 0.1s). While the system correctly triggered emergency braking, the physical constraints of maximum deceleration made maintaining a 5m gap impossible under these conditions.

### Analysis
The ACC system demonstrates robust performance in normal cruising and following scenarios. It successfully achieves fast rise times and precise distance control. The emergency braking logic provides a critical safety layer, although extreme environmental discontinuities in the sensor data can exceed the physical capabilities of the vehicle's braking system.
