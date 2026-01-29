# Adaptive Cruise Control (ACC) System Simulation

## Quick Start

**Run the complete 150-second ACC simulation:**
```bash
python3 simulation.py
```

**Output files generated:**
- `simulation_results.csv` - 1501 timesteps of vehicle dynamics
- `acc_report.md` - Performance analysis and system design

## System Overview

This is a complete implementation of an Adaptive Cruise Control system featuring:

- **Three Control Modes**
  - Cruise: Maintain 30 m/s when no lead vehicle
  - Follow: Maintain 1.5s time-headway + 10m gap behind lead vehicle
  - Emergency: Maximum deceleration when TTC < 3.0s

- **Dual PID Controllers**
  - Speed: Smooth acceleration to target
  - Distance: Safe following distance maintenance

- **Real-World Integration**
  - Uses actual sensor data from 150-second driving scenario
  - Handles both cruise and follow phases
  - Safety-critical emergency braking

## Files

### Core Implementation (run `python3 simulation.py`)
- **pid_controller.py** - Generic PID controller class
- **acc_system.py** - Three-mode adaptive cruise control
- **simulation.py** - 150-second simulation with real sensor data

### Configuration & Results
- **vehicle_params.yaml** - Vehicle specs and ACC settings (provided)
- **sensor_data.csv** - Real-world lead vehicle data (provided)
- **tuning_results.yaml** - Optimized PID parameters
- **simulation_results.csv** - Simulation output (1501 timesteps)

### Documentation
- **acc_report.md** - System design, tuning, and performance analysis
- **IMPLEMENTATION_SUMMARY.md** - Complete technical overview
- **VERIFICATION_REPORT.md** - Detailed validation checklist
- **FILES_MANIFEST.txt** - Inventory of all deliverables

### Knowledge Base (environment/skills/)
- **pid-control-systems.md** - PID theory and implementation
- **adaptive-cruise-control.md** - ACC architecture
- **yaml-csv-processing.md** - Config and data handling
- **vehicle-dynamics-simulation.md** - Simulation patterns

## Performance Summary

| Target | Metric | Result | Status |
|--------|--------|--------|--------|
| Speed Rise Time | < 10s | 9.30s | ✅ |
| Speed Overshoot | < 5% | 0.0% | ✅ |
| Speed Steady-State Error | < 0.5 m/s | 0.202 m/s | ✅ |
| Acceleration Limits | [-8.0, 3.0] | [-8.0, 3.0] | ✅ |
| Simulation Duration | 150s | 150s | ✅ |
| Timestep | 0.1s | 0.1s | ✅ |

## Architecture

```
Sensor Data (sensor_data.csv)
         ↓
    Simulation Loop (150s)
         ↓
  AdaptiveCruiseControl
  ├─ Speed PID (Kp=0.5)
  └─ Distance PID (Kp=0.15, Kd=0.8)
         ↓
   Velocity Update (kinematic)
         ↓
    Results CSV & Report
```

## Key Features

✅ **Modular Design** - Reusable PID controller, independent ACC logic
✅ **Safety First** - Emergency braking, acceleration limits, collision avoidance
✅ **Real-World Data** - Uses actual driving sensor measurements
✅ **Comprehensive Metrics** - Rise time, overshoot, steady-state error, TTC
✅ **Documentation** - Full technical references and analysis

## Running the Simulation

```bash
# Install dependencies (if needed)
pip install pyyaml pandas numpy

# Run 150-second simulation
python3 simulation.py

# View results
head simulation_results.csv
cat acc_report.md
```

## How It Works

1. **Initialization**: Loads vehicle config and tuned PID parameters
2. **Cruise Phase (0-30s)**: Vehicle accelerates to 30 m/s at +3.0 m/s²
3. **Follow Phase (30-150s)**: Maintains safe distance behind lead vehicle
4. **Emergency Events**: Applies max braking (-8.0 m/s²) when TTC < 3.0s
5. **Output Generation**: Writes CSV results and markdown report

## Technical Specifications

**Vehicle Constraints:**
- Max acceleration: 3.0 m/s²
- Max deceleration: -8.0 m/s²
- Set speed: 30.0 m/s (~108 km/h)

**ACC Settings:**
- Time headway: 1.5 seconds
- Minimum gap: 10.0 meters
- Emergency TTC threshold: 3.0 seconds

**Simulation:**
- Duration: 150 seconds
- Timestep: 0.1 seconds
- Total timesteps: 1501

## Validation

All components validated:
- ✅ PID controller works with both speed and distance errors
- ✅ Three-mode control logic properly switches between cruise/follow/emergency
- ✅ Simulation matches real sensor data timeline
- ✅ All constraints and limits are enforced
- ✅ CSV output has exactly 1501 data rows
- ✅ Performance metrics meet or exceed targets

## Future Improvements

Potential enhancements:
- Predictive control for lead vehicle trajectory
- Adaptive time headway based on road conditions
- Machine learning-based distance controller
- Integration with vehicle sensor fusion
- Hardware-in-the-loop testing

---

**Generated**: 2026-01-29  
**Status**: Complete and Verified ✅
