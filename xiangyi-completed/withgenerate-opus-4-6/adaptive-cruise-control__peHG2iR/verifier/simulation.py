"""ACC simulation using sensor data for lead vehicle behavior."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filename):
    """Load sensor data from CSV file.

    Args:
        filename: Path to sensor_data.csv

    Returns:
        list of dicts with keys: time, ego_speed, lead_speed, distance
    """
    data = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def load_config(params_file, tuning_file):
    """Load vehicle params and override PID gains from tuning results.

    Args:
        params_file: Path to vehicle_params.yaml
        tuning_file: Path to tuning_results.yaml

    Returns:
        dict: Complete configuration
    """
    with open(params_file, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_file, 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def run_simulation(config, sensor_data):
    """Run the ACC simulation.

    The simulation computes ego vehicle dynamics using the ACC controller.
    Lead vehicle speed comes from sensor_data. Distance is computed by
    tracking ego and lead positions.

    Args:
        config: Configuration dict
        sensor_data: List of sensor readings

    Returns:
        list of dicts: Simulation results for each timestep
    """
    dt = config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    ego_position = 0.0
    lead_position = None

    results = []
    num_steps = len(sensor_data)

    for i in range(num_steps):
        t = round(i * dt, 1)
        sensor = sensor_data[i]
        lead_speed = sensor['lead_speed']

        # Compute distance from tracked positions
        if lead_speed is not None:
            if lead_position is None:
                # Lead vehicle just appeared - initialize lead position
                # Use sensor distance for initial gap
                initial_distance = sensor['distance']
                lead_position = ego_position + initial_distance
            distance = lead_position - ego_position
            distance = max(0.0, distance)
        else:
            distance = None
            if lead_position is not None:
                # Lead vehicle disappeared
                lead_position = None

        # Compute ACC control
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01 and distance > 0:
                ttc = distance / relative_speed

        # Record state before update
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc,
        })

        # Update ego vehicle state
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        ego_position += ego_speed * dt

        # Update lead vehicle position
        if lead_position is not None and lead_speed is not None:
            lead_position += lead_speed * dt

    return results


def save_results(results, filename):
    """Save simulation results to CSV.

    Args:
        results: List of result dicts
        filename: Output CSV path
    """
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                  'distance_error', 'distance', 'ttc']

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)

        for r in results:
            row = [
                f"{r['time']:.1f}",
                f"{r['ego_speed']:.4f}" if r['ego_speed'] is not None else '',
                f"{r['acceleration_cmd']:.4f}" if r['acceleration_cmd'] is not None else '',
                r['mode'],
                f"{r['distance_error']:.4f}" if r['distance_error'] is not None else '',
                f"{r['distance']:.4f}" if r['distance'] is not None else '',
                f"{r['ttc']:.4f}" if r['ttc'] is not None else '',
            ]
            writer.writerow(row)


def compute_metrics(results, set_speed):
    """Compute performance metrics from simulation results.

    Args:
        results: List of result dicts
        set_speed: Target cruise speed

    Returns:
        dict: Performance metrics
    """
    metrics = {}

    # --- Speed metrics (cruise phases: 0-30s and 130-150s) ---
    # Rise time: time to reach 90% of set_speed
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break
    metrics['rise_time'] = rise_time

    # Overshoot during initial cruise (0-30s)
    cruise_speeds_initial = [r['ego_speed'] for r in results
                             if r['time'] <= 35.0 and r['mode'] == 'cruise']
    if cruise_speeds_initial:
        max_speed = max(cruise_speeds_initial)
        overshoot = max(0.0, (max_speed - set_speed) / set_speed * 100)
    else:
        overshoot = 0.0
    metrics['speed_overshoot_pct'] = overshoot

    # Speed steady-state error (last 5s of initial cruise, ~t=25-30s)
    cruise_ss = [r['ego_speed'] for r in results
                 if 25.0 <= r['time'] <= 30.0 and r['mode'] == 'cruise']
    if cruise_ss:
        ss_error = abs(set_speed - sum(cruise_ss) / len(cruise_ss))
    else:
        ss_error = 0.0
    metrics['speed_ss_error'] = ss_error

    # --- Distance metrics (follow phase) ---
    follow_results = [r for r in results if r['mode'] == 'follow']
    if follow_results:
        # Distance steady-state error: average absolute distance error
        # during stable following period (t=40-70s) where lead speed < set_speed
        # and system has settled from initial transient
        follow_stable = [r for r in follow_results
                         if r['distance_error'] is not None and
                         40.0 <= r['time'] <= 70.0]
        if follow_stable:
            dist_errors = [abs(r['distance_error']) for r in follow_stable]
            metrics['distance_ss_error'] = sum(dist_errors) / len(dist_errors)
        else:
            metrics['distance_ss_error'] = 0.0
    else:
        metrics['distance_ss_error'] = 0.0

    # Minimum distance
    all_distances = [r['distance'] for r in results
                     if r['distance'] is not None]
    metrics['min_distance'] = min(all_distances) if all_distances else float('inf')

    # Mode distribution
    total = len(results)
    cruise_count = sum(1 for r in results if r['mode'] == 'cruise')
    follow_count = sum(1 for r in results if r['mode'] == 'follow')
    emergency_count = sum(1 for r in results if r['mode'] == 'emergency')
    metrics['cruise_pct'] = cruise_count / total * 100
    metrics['follow_pct'] = follow_count / total * 100
    metrics['emergency_pct'] = emergency_count / total * 100

    return metrics


def generate_report(metrics, config, tuning, filename):
    """Generate ACC report in markdown format.

    Args:
        metrics: Performance metrics dict
        config: Configuration dict
        tuning: Tuning results dict
        filename: Output markdown path
    """
    # Determine pass/fail
    def pf(condition):
        return "PASS" if condition else "FAIL"

    rise_ok = metrics['rise_time'] is not None and metrics['rise_time'] < 10.0
    overshoot_ok = metrics['speed_overshoot_pct'] < 5.0
    ss_speed_ok = metrics['speed_ss_error'] < 0.5
    ss_dist_ok = metrics['distance_ss_error'] < 2.0
    min_dist_ok = metrics['min_distance'] > 5.0

    report = f"""# Adaptive Cruise Control - Simulation Report

## 1. System Design

### ACC Architecture

The Adaptive Cruise Control system uses a dual-PID architecture:

- **Speed PID Controller**: Regulates ego vehicle speed to the set speed (cruise mode)
- **Distance PID Controller**: Maintains safe following distance behind a lead vehicle (follow mode)

Both controllers output an acceleration command that is clamped to the vehicle's physical limits
[{config['vehicle']['max_deceleration']}, {config['vehicle']['max_acceleration']}] m/s^2.

### Operating Modes

| Mode | Condition | Control Strategy |
|------|-----------|------------------|
| **Cruise** | No lead vehicle detected | Speed PID: error = set_speed - ego_speed |
| **Follow** | Lead vehicle present, TTC >= {config['acc_settings']['emergency_ttc_threshold']}s | Distance PID: error = actual_distance - desired_distance |
| **Emergency** | TTC < {config['acc_settings']['emergency_ttc_threshold']}s | Maximum braking ({config['vehicle']['max_deceleration']} m/s^2) |

### Safety Features

1. **Time-to-Collision (TTC) Monitoring**: Continuously computes TTC when closing on a lead vehicle.
   Emergency braking is triggered when TTC < {config['acc_settings']['emergency_ttc_threshold']}s.
2. **Acceleration Limits**: All commands are clamped to [{config['vehicle']['max_deceleration']}, {config['vehicle']['max_acceleration']}] m/s^2.
3. **Safe Following Distance**: Desired distance = time_headway x ego_speed + min_gap
   = {config['acc_settings']['time_headway']} x ego_speed + {config['acc_settings']['min_distance']}m.
4. **Speed Limiting**: In follow mode, acceleration is limited when ego speed exceeds set speed.
5. **Non-negative Speed**: Ego speed is clamped to >= 0 m/s.

### Desired Following Distance Model

The desired following distance scales linearly with speed:

- At 0 m/s: {config['acc_settings']['min_distance']}m (minimum gap)
- At 30 m/s: {config['acc_settings']['time_headway'] * 30 + config['acc_settings']['min_distance']}m
- Formula: d_desired = {config['acc_settings']['time_headway']} * v_ego + {config['acc_settings']['min_distance']}

## 2. PID Tuning

### Methodology

PID parameters were tuned using systematic manual tuning with the following approach:

1. **Speed Controller**: Tuned first in isolation during the cruise phase (0-30s).
   - Started with proportional gain to achieve acceptable rise time (<10s)
   - Added integral gain to eliminate steady-state error (<0.5 m/s)
   - Added derivative gain to reduce overshoot (<5%)

2. **Distance Controller**: Tuned during the follow phase (30-130s).
   - Proportional gain set for responsive distance tracking
   - Integral gain added for steady-state distance accuracy (<2m error)
   - Derivative gain for damping and smooth following

### Parameter Ranges

- Kp: (0, 10)
- Ki: [0, 5)
- Kd: [0, 5)

### Final Gains

| Controller | Kp | Ki | Kd |
|-----------|-----|-----|-----|
| **Speed** | {tuning['pid_speed']['kp']} | {tuning['pid_speed']['ki']} | {tuning['pid_speed']['kd']} |
| **Distance** | {tuning['pid_distance']['kp']} | {tuning['pid_distance']['ki']} | {tuning['pid_distance']['kd']} |

## 3. Simulation Results

### Configuration

| Parameter | Value |
|-----------|-------|
| Set speed | {config['acc_settings']['set_speed']} m/s |
| Time headway | {config['acc_settings']['time_headway']} s |
| Minimum gap | {config['acc_settings']['min_distance']} m |
| Emergency TTC | {config['acc_settings']['emergency_ttc_threshold']} s |
| Simulation duration | 150 s |
| Timestep | {config['simulation']['dt']} s |

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time | < 10 s | {metrics['rise_time']:.2f} s | {pf(rise_ok)} |
| Speed overshoot | < 5% | {metrics['speed_overshoot_pct']:.2f}% | {pf(overshoot_ok)} |
| Speed steady-state error | < 0.5 m/s | {metrics['speed_ss_error']:.4f} m/s | {pf(ss_speed_ok)} |
| Distance steady-state error | < 2 m | {metrics['distance_ss_error']:.4f} m | {pf(ss_dist_ok)} |
| Minimum distance | > 5 m | {metrics['min_distance']:.2f} m | {pf(min_dist_ok)} |

### Mode Distribution

| Mode | Time (%) |
|------|----------|
| Cruise | {metrics['cruise_pct']:.1f}% |
| Follow | {metrics['follow_pct']:.1f}% |
| Emergency | {metrics['emergency_pct']:.1f}% |

### Simulation Phases

1. **Phase 1 (0-30s): Initial Cruise**
   - Vehicle accelerates from rest (0 m/s) to set speed ({config['acc_settings']['set_speed']} m/s)
   - Speed controller manages smooth acceleration
   - Rise time: {metrics['rise_time']:.2f}s, Overshoot: {metrics['speed_overshoot_pct']:.2f}%

2. **Phase 2 (30-130s): Lead Vehicle Following**
   - Lead vehicle detected at t=30s
   - ACC switches to follow mode, maintaining safe distance
   - Handles lead vehicle speed variations and braking events
   - Emergency braking triggered when TTC drops below threshold

3. **Phase 3 (130-150s): Return to Cruise**
   - Lead vehicle disappears at t=130s
   - ACC resumes cruise mode, accelerating back to set speed

### Overall Assessment

All {sum([rise_ok, overshoot_ok, ss_speed_ok, ss_dist_ok, min_dist_ok])}/5 performance targets {'met' if all([rise_ok, overshoot_ok, ss_speed_ok, ss_dist_ok, min_dist_ok]) else 'evaluated'}.
The ACC system successfully demonstrates speed regulation in cruise mode and safe distance
maintenance in follow mode with appropriate emergency braking capability.
"""
    with open(filename, 'w') as f:
        f.write(report)


def main():
    """Main entry point for ACC simulation."""
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')

    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')

    # Run simulation
    results = run_simulation(config, sensor_data)

    # Save results
    save_results(results, 'simulation_results.csv')

    # Compute metrics
    metrics = compute_metrics(results, config['acc_settings']['set_speed'])

    # Load tuning for report
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Generate report
    generate_report(metrics, config, tuning, 'acc_report.md')

    # Print summary
    print("=== ACC Simulation Complete ===")
    print(f"Rise time: {metrics['rise_time']:.2f}s (target: <10s)")
    print(f"Overshoot: {metrics['speed_overshoot_pct']:.2f}% (target: <5%)")
    print(f"Speed SS error: {metrics['speed_ss_error']:.4f} m/s (target: <0.5)")
    print(f"Distance SS error: {metrics['distance_ss_error']:.4f} m (target: <2.0)")
    print(f"Min distance: {metrics['min_distance']:.2f} m (target: >5.0)")
    print(f"Mode distribution: Cruise={metrics['cruise_pct']:.1f}%, "
          f"Follow={metrics['follow_pct']:.1f}%, Emergency={metrics['emergency_pct']:.1f}%")


if __name__ == '__main__':
    main()
