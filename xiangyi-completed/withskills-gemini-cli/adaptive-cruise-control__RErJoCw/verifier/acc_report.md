# Adaptive Cruise Control (ACC) System Report

## System Design

The ACC system is designed as a mode-based controller that switches between speed control and distance control based on the presence of a lead vehicle and safety constraints.

### Architecture
- **Perception Layer**: Processes sensor data (`lead_speed`, `distance`) to determine lead vehicle presence and calculate Time-to-Collision (TTC).
- **Control Layer**: 
    - **Cruise Mode**: Active when no lead vehicle is detected. Uses a PID controller to maintain the target set speed (30 m/s).
    - **Follow Mode**: Active when a lead vehicle is detected. Uses a PID controller to maintain a safe following distance ($d_{safe} = v_{ego} 	imes t_{headway} + d_{min}$). To ensure safety and legality, the acceleration command is the minimum of the distance control output and a speed-limiting control output.
    - **Emergency Mode**: Triggered when TTC falls below the emergency threshold (3.0s). Applies maximum deceleration (-8.0 m/s²) to avoid or mitigate collision.
- **Actuation Layer**: Clamps acceleration commands to physical limits ([-8.0, 3.0] m/s²) and updates vehicle speed using a kinematic model.

### Safety Features
- **Anti-Windup**: Integral clamping is implemented in the PID controller to prevent overshoot and long settling times after saturation.
- **Minimum Gap**: A constant minimum gap of 10.0m is maintained even at zero speed.
- **TTC Monitoring**: Continuous monitoring of Time-to-Collision for emergency intervention.

## PID Tuning Methodology and Final Gains

### Methodology
Tuning was performed iteratively:
1. **Speed Control Tuning**: Adjusted $K_p$ to meet the rise time requirement (< 10s). $K_i$ was added to eliminate steady-state error, with integral clamping to keep overshoot below 5%.
2. **Distance Control Tuning**: $K_p$ and $K_d$ were tuned to provide a responsive but stable approach to the lead vehicle. $K_i$ ensures zero steady-state error during constant-speed following.

### Final Gains
| Controller | $K_p$ | $K_i$ | $K_d$ |
| :--- | :--- | :--- | :--- |
| **Speed (Cruise)** | 0.6 | 0.1 | 0.1 |
| **Distance (Follow)** | 0.6 | 0.1 | 0.2 |

## Simulation Results and Performance Metrics

The simulation was conducted over a 150s duration with a 0.1s timestep.

### Performance Summary
| Metric | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| Speed Rise Time | < 10.0s | 8.1s | **PASS** |
| Speed Overshoot | < 5.0% | 3.97% | **PASS** |
| Speed SS Error | < 0.5 m/s | 0.07 m/s | **PASS** |
| Distance SS Error | < 2.0m | 0.28m | **PASS** |
| Minimum Distance | > 5.0m | 19.65m | **PASS** |

### Discussion
The system successfully reached the target speed of 30 m/s within 8.1 seconds with minimal overshoot. When the lead vehicle was detected at $t=30s$, the system seamlessly transitioned to `follow` mode, maintaining the safe distance with high precision (error < 0.3m). The system also correctly handled the lead vehicle accelerating beyond the set speed by capping the ego speed at 30 m/s, and safely tracked the lead vehicle during deceleration.
