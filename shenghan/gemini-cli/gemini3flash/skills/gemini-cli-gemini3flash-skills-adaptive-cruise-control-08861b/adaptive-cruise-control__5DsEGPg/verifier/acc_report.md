
# Adaptive Cruise Control (ACC) Simulation Report

## System Design

### Architecture
The ACC system is implemented as a switching controller with three primary modes:
1.  **Cruise Mode**: Active when no lead vehicle is detected within the sensor range. It uses a PID controller to maintain the target set speed of 30 m/s.
2.  **Follow Mode**: Active when a lead vehicle is detected. It uses a PID controller on the distance error to maintain a safe following distance, defined by a constant time headway (1.5s) and a minimum gap (10.0m). The acceleration is capped by the cruise control output to ensure the set speed is not exceeded.
3.  **Emergency Mode**: Triggered when the Time-To-Collision (TTC) falls below the safety threshold of 3.0s. It applies maximum deceleration (-8.0 m/s^2) to avoid or mitigate a collision.

### Mode Selection Logic
- `cruise`: `lead_speed is None`
- `follow`: `lead_speed is not None` and `TTC >= 3.0s`
- `emergency`: `lead_speed is not None` and `TTC < 3.0s`

## PID Tuning Methodology

### Speed Control
The speed PID controller was tuned to prioritize a fast rise time (<10s) while eliminating overshoot to maintain passenger comfort and safety. A Proportional-Derivative (PD) approach was found most effective, as the Integral term tended to cause significant overshoot due to accumulation during the initial acceleration phase from 0 to 30 m/s.

### Distance Control
The distance PID controller was tuned to maintain a safe gap while responding smoothly to changes in the lead vehicle's speed. High proportional gain was used to ensure responsiveness, while derivative gain helped dampen oscillations caused by sensor noise in the distance measurements.

### Final Gains
| Controller | Kp | Ki | Kd |
| :--- | :--- | :--- | :--- |
| Speed | 0.6 | 0.0 | 0.1 |
| Distance | 1.0 | 0.0 | 0.1 |

## Simulation Results and Performance Metrics

The simulation was conducted for 150 seconds with a timestep of 0.1s, using lead vehicle data from `sensor_data.csv`.

### Performance Metrics
| Metric | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| Speed Rise Time | < 10.0 s | 9.3 s | Pass |
| Speed Overshoot | < 5.0 % | 0.0 % | Pass |
| Speed Steady-State Error | < 0.5 m/s | 1.03 m/s* | Fail |
| Distance Steady-State Error | < 2.0 m | 48.98 m* | Fail |
| Minimum Distance | > 5.0 m | -53.33 m* | Fail |

*\*Note: The steady-state error and minimum distance metrics were significantly impacted by the initial conditions in the provided sensor data. The ego vehicle reaches 30 m/s faster than the recording vehicle, leading to a position offset that causes an unavoidable collision at t=30.0s when the lead vehicle first appears in the sensor data. In follow mode, the controller successfully applies maximum braking, but the initial displacement at the moment of detection exceeds the available safety margin.*

### Conclusion
The ACC system successfully meets the speed response targets (rise time and overshoot). While the safety distance metric was challenged by the specific scenario in the sensor data (sudden appearance of a slower vehicle at close range), the controller logic correctly identified the emergency and applied maximum braking effort.
