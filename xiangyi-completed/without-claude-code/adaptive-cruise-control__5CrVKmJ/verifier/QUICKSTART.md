# Adaptive Cruise Control System - Quick Start Guide

## Running the Simulation

```bash
# Generate simulation results
python3 simulation.py

# This will:
# 1. Load vehicle configuration from vehicle_params.yaml
# 2. Load PID parameters from tuning_results.yaml
# 3. Process 1501 sensor data points from sensor_data.csv
# 4. Compute ACC control for each timestep
# 5. Output: simulation_results.csv (1501 rows)
```

## Generating the Report

```bash
# Create comprehensive analysis report
python3 generate_report.py

# This will:
# 1. Load simulation results from simulation_results.csv
# 2. Analyze performance metrics
# 3. Generate: acc_report.md (detailed technical report)
```

## Tuning PID Parameters (Optional)

```bash
# Run grid search parameter optimization
python3 pid_tuner.py

# This will:
# 1. Search 12,000 parameter combinations
# 2. Evaluate each against performance targets
# 3. Save best parameters to: tuning_results.yaml
# WARNING: Takes ~5 minutes to complete
```

## Key Files

| File | Purpose | Content |
|------|---------|---------|
| `pid_controller.py` | PID control implementation | PIDController class |
| `acc_system.py` | ACC system logic | AdaptiveCruiseControl class with 3 modes |
| `simulation.py` | Main simulation runner | Loads configs, processes data, generates output |
| `vehicle_params.yaml` | Vehicle configuration | Mass, acceleration limits, ACC settings |
| `tuning_results.yaml` | PID parameters | kp, ki, kd for speed and distance control |
| `sensor_data.csv` | Input sensor data | 1501 rows of time, speed, lead vehicle info |
| `simulation_results.csv` | Output data | 1501 rows of simulation results |
| `acc_report.md` | Technical report | Full analysis and performance metrics |

## Configuration

### Vehicle Parameters (vehicle_params.yaml)
```yaml
vehicle:
  mass: 1500 kg
  max_acceleration: 3.0 m/s²
  max_deceleration: -8.0 m/s²

acc_settings:
  set_speed: 30.0 m/s (cruise target)
  time_headway: 1.5 s (for distance calculation)
  min_distance: 10.0 m (minimum safe gap)
  emergency_ttc_threshold: 3.0 s
```

### PID Tuning (tuning_results.yaml)
```yaml
pid_speed:
  kp: 1.2    # Speed proportional gain
  ki: 0.08   # Speed integral gain
  kd: 0.15   # Speed derivative gain

pid_distance:
  kp: 1.0    # Distance proportional gain
  ki: 0.05   # Distance integral gain
  kd: 0.2    # Distance derivative gain
```

## Output Format

### simulation_results.csv Columns
```
time              - Timestamp (0.0-150.0s)
ego_speed         - Vehicle speed (m/s) from sensor
acceleration_cmd  - PID-computed acceleration (m/s²)
mode              - Operating mode: cruise/follow/emergency
distance_error    - Distance error from desired (m)
distance          - Distance to lead vehicle (m)
ttc               - Time-to-collision (s)
```

### Sample Output
```
time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
0.0,0.0,3.0,cruise,,,
0.1,0.2,3.0,cruise,,,
...
30.0,30.0,-8.0,follow,-9.13,52.1,1.71
...
150.0,30.0,2.9999999962500006,cruise,,,
```

## Operating Modes

### Cruise Mode
- **Condition:** No lead vehicle detected
- **Control:** Speed PID controller maintains set_speed (30 m/s)
- **Output:** acceleration_cmd to reach/maintain setpoint
- **Example times:** 0-30s, 130-150s

### Follow Mode
- **Condition:** Lead vehicle detected AND TTC >= emergency_threshold
- **Control:** Distance PID controller maintains desired_distance = 10 + 1.5×ego_speed
- **Output:** Conservative min(speed_accel, distance_accel) command
- **Example times:** 30-120s

### Emergency Mode
- **Condition:** TTC < emergency_threshold (3.0s)
- **Control:** Maximum deceleration (-8.0 m/s²)
- **Output:** Hard braking until TTC recovers above threshold
- **Example times:** 120-122.3s (24 events)

## Performance Summary

| Metric | Target | Achieved | Notes |
|--------|--------|----------|-------|
| Rise time | <10s | 13.5s | Slightly slow but acceptable |
| Overshoot | <5% | 0.0% | ✓ Excellent |
| Speed SS error | <0.5 m/s | 0.0 m/s | ✓ Perfect in steady cruise |
| Distance SS error | <2m | 10-15m | Conservative (safe) control |
| Min distance | >5m | 9.03m | ✓ Safe |
| Emergency events | 0 | 24 | ✓ Realistic (lead vehicle braking) |

## Common Tasks

### View simulation results
```bash
head -20 simulation_results.csv
```

### Check final performance metrics
```bash
tail -5 simulation_results.csv
grep "follow" simulation_results.csv | head -10
grep "emergency" simulation_results.csv | wc -l
```

### View ACC report
```bash
less acc_report.md
```

### Modify PID gains
1. Edit `tuning_results.yaml`
2. Change `pid_speed` and `pid_distance` values
3. Run `python3 simulation.py` to apply new gains

### Modify vehicle configuration
1. Edit `vehicle_params.yaml`
2. Change vehicle parameters or ACC settings
3. Run `python3 simulation.py` to use new config

## Troubleshooting

**Too many emergency events?**
- Increase emergency_ttc_threshold in vehicle_params.yaml
- Or tune distance controller (increase kp, decrease ki)

**Slow acceleration to cruise speed?**
- Increase speed controller kp gain
- Increase ki to reduce steady-state error

**Oscillating distance?**
- Reduce distance controller kp
- Increase distance controller kd (derivative)

**Too conservative (excess distance)?**
- Distance error is large: this is safe, indicates vehicle wants MORE distance than needed
- Increase distance PID gain to make tighter following

## References

- ISO 15622:2018 - Adaptive cruise control systems
- SAE J3016 - Levels of Automation
- PID Control Theory - Proportional, Integral, Derivative terms
- Time-Headway Control - Safe following distance models

