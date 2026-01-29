# Adaptive Cruise Control (ACC) System Report

## System Design

The Adaptive Cruise Control (ACC) system is designed to maintain a user-defined set speed while automatically adjusting the vehicle's speed to maintain a safe following distance when a lead vehicle is detected.

### Architecture
The system consists of three main components:
1.  **Perception Layer**: Interprets sensor data (lead vehicle speed and distance) from the `sensor_data.csv`.
2.  **Control Logic**: A state machine that selects the appropriate control mode and calculates the acceleration command.
3.  **Actuation**: Applies the acceleration command to the vehicle model, respecting acceleration limits ([-8.0, 3.0] m/s²).

### Modes of Operation
-   **Cruise Mode**: Active when no lead vehicle is detected. The system uses a PID controller to reach and maintain the set speed (30 m/s).
-   **Follow Mode**: Active when a lead vehicle is detected and the Time-To-Collision (TTC) is above the emergency threshold. The system maintains a target distance $d_{target} = d_{min} + t_{headway} 	imes v_{ego}$, where $d_{min} = 10m$ and $t_{headway} = 1.5s$.
-   **Emergency Mode**: Triggered when the TTC falls below 3.0 seconds. The system applies maximum deceleration (-8.0 m/s²) to avoid collision.

## PID Tuning Methodology

The PID parameters were tuned iteratively to meet the performance targets.

### Speed Control Tuning
-   Priority was given to minimizing overshoot while maintaining a rise time under 10 seconds.
-   A derivative-heavy approach ($K_d=0.5$) with moderate proportional gain ($K_p=0.6$) was used to achieve a fast but damped response.
-   Integral gain was kept at 0 to avoid windup during the initial acceleration phase.

### Distance Control Tuning
-   The distance controller was tuned to minimize steady-state error and avoid oscillations.
-   An integral term ($K_i=0.2$) was introduced to eliminate steady-state distance error during constant-speed following.
-   Proportional and derivative gains were balanced to ensure stable following without excessive oscillation.

### Final PID Gains
| Controller | Kp | Ki | Kd |
| :--- | :--- | :--- | :--- |
| Speed | 0.6 | 0.0 | 0.5 |
| Distance | 1.0 | 0.2 | 0.5 |

## Simulation Results

The simulation was run for 150 seconds with a timestep of 0.1s.

### Performance Metrics
| Metric | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| Speed Rise Time | < 10s | 9.80s | PASS |
| Speed Overshoot | < 5% | 0.00% | PASS |
| Speed SS Error | < 0.5 m/s | 0.0029 m/s | PASS |
| Distance SS Error | < 2m | 0.10m* | PASS |
| Minimum Distance | > 5m | 19.33m | PASS |

*Calculated during steady following period (t=40s to 60s).*

### Summary
The ACC system successfully met all performance requirements. It reached the target speed of 30 m/s in 9.8 seconds with no overshoot. When a lead vehicle appeared at $t=30s$, the system smoothly transitioned to follow mode, maintaining the target distance with minimal error. The system remained stable throughout the 150-second simulation, including handling the lead vehicle's eventual departure.
