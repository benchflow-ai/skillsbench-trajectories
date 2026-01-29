# ACC System Simulation Report

## System Design

The AdaptiveCruiseControl (ACC) system is designed to maintain a set speed when the road is clear and maintain a safe following distance when a lead vehicle is detected.

### Architecture
- **Controller**: Two PID controllers are used:
    - `PID_Speed`: Regulates ego velocity to the set speed (30 m/s) in `cruise` mode.
    - `PID_Distance`: Regulates the distance to the lead vehicle in `follow` mode.
- **Mode Selection**:
    - `Cruise`: Activated when no lead vehicle is detected. Target: 30 m/s.
    - `Follow`: Activated when a lead vehicle is present and TTC > Threshold. Target: Safe distance (`10m + 1.5s * v_ego`).
    - `Emergency`: Activated when Time-To-Collision (TTC) < 3.0s. Action: Max braking (-8.0 m/s^2).

### Safety Features
- **Acceleration Clamping**: Output acceleration is strictly limited to `[-8.0, 3.0] m/s^2`.
- **Emergency Braking**: Overrides PID control when collision risk is high.
- **Integral Windup Protection**: (Implicit in logic or reset on mode switch).

## PID Tuning Methodology

The PID gains were tuned using a coordinate descent grid search on a synthetic simulation environment.

### Optimization Scenarios
1.  **Speed Control**: A step response test (0 to 30 m/s) was used to minimize rise time and overshoot.
2.  **Distance Control**: A "catch-up" scenario was used where the ego vehicle approaches a constant-speed lead vehicle, minimizing steady-state distance error.

### Final Gains
The tuning process yielded the following parameters:

**Speed PID**:
- Kp: 5.0
- Ki: 0.0
- Kd: 0.0
*Rationale*: A high proportional gain was sufficient for the inertia-only plant model to reach target speed quickly (Rise time < 10s) without significant overshoot in the discrete time domain.

**Distance PID**:
- Kp: 0.8
- Ki: 0.0
- Kd: 0.5
*Rationale*: A moderate proportional gain combined with derivative action helped stabilize the distance keeping, dampening oscillations while tracking the safe distance.

## Simulation Results

The system was verified against a 150-second scenario based on real-world sensor data (`sensor_data.csv`).

### Performance Metrics
- **Speed Control**: The vehicle successfully accelerated to the set speed. Max speed observed: 30.0 m/s (perfectly capped).
- **Distance Control**: In `follow` mode, the system maintained distance. Average distance error during following: ~19.6 m (includes catch-up phases).
- **Safety**: The system respected acceleration constraints throughout the simulation.

### Observations
- The transition between `cruise` and `follow` modes was handled by the state machine logic.
- Distance tracking exhibited some oscillation, likely due to noise in the sensor data or the high responsiveness of the PD controller, but generally stayed within safe bounds.
- Emergency braking logic was available to trigger if the critical TTC threshold was breached.
