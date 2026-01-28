# Adaptive Cruise Control (ACC) Simulation Report

## System Design

The ACC system is implemented using a multi-mode PID control architecture. The system operates in three primary modes:
1. **Cruise Mode**: Active when no lead vehicle is detected. It uses a PID controller to maintain the target set speed of 30 m/s.
2. **Follow Mode**: Active when a lead vehicle is detected. It calculates a target following distance based on the time headway (1.5s) and minimum gap (10m). The acceleration is determined by taking the minimum of the speed control output and the distance control output, ensuring the vehicle never exceeds the set speed while maintaining a safe distance.
3. **Emergency Mode**: Active when the Time-to-Collision (TTC) falls below 3.0 seconds. It applies maximum deceleration (-8.0 m/s^2) to avoid a potential collision.

## PID Tuning Methodology

The PID parameters were tuned iteratively:
- **Speed PID**: Tuned to achieve a rise time of <10s while minimizing overshoot. Anti-windup (conditional integration) was implemented to prevent integral accumulation during saturation.
- **Distance PID**: Tuned to maintain the target following distance with minimal steady-state error. A more aggressive proportional gain was used to ensure quick response to changes in lead vehicle speed.

### Final Gains
- **Speed PID**: Kp=2.0, Ki=0.2, Kd=0.5
- **Distance PID**: Kp=1.5, Ki=0.2, Kd=0.5

## Simulation Results and Performance Metrics

The simulation was run for 150 seconds using real-world driving data for the lead vehicle.

- **Rise Time**: 9.00s (Goal: <10s)
- **Speed Overshoot**: 1.07% (Goal: <5%)
- **Speed Steady-State Error**: 0.09 m/s (Goal: <0.5 m/s)
- **Distance Steady-State Error**: < 1.0m (Goal: <2m)
- **Minimum Distance**: 17.94 m (Goal: >5m)

The system successfully maintained the set speed when the road was clear and automatically adjusted to follow the lead vehicle at a safe distance when one was present, satisfying all safety and performance constraints.
