# Adaptive Cruise Control Simulation Report

## System Design

The ACC system uses a dual PID controller architecture:
- **Speed Controller**: Maintains the set speed (30.0 m/s) when no lead vehicle is present.
- **Distance Controller**: Maintains a safe following distance defined by `time_headway * ego_speed + min_distance`.

### Modes
- **Cruise**: Active when no lead vehicle is detected. Controls speed.
- **Follow**: Active when a lead vehicle is detected within range. Controls following distance.
- **Emergency**: Active when Time-To-Collision (TTC) falls below 3.0s. Applies maximum braking.

## PID Tuning

The PID controllers were tuned to meet specific performance criteria.

### Speed PID Gains
- **Kp**: 5.0
- **Ki**: 0.0
- **Kd**: 0.0

### Distance PID Gains
- **Kp**: 2.0
- **Ki**: 0.0
- **Kd**: 0.0

## Simulation Results

The simulation was run for 150 seconds using real-world lead vehicle data.

### Performance Metrics

| Metric | Value | Target | Status |
| :--- | :--- | :--- | :--- |
| **Speed Rise Time** | 8.00 s | < 10 s | PASS |
| **Speed Overshoot** | 0.00 % | < 5 % | PASS |
| **Speed SS Error** | 0.000 m/s | < 0.5 m/s | PASS |
| **Distance SS Error** | 1.41 m | < 2 m | PASS |
| **Minimum Distance** | 19.12 m | > 5 m | PASS |

### Analysis

The system successfully transitions between Cruise and Follow modes based on the lead vehicle's presence. The PID controllers maintain stability and meet the safety requirements.

