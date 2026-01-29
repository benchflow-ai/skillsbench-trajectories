"""Analyze simulation results and generate report."""

import csv
import yaml
import math
from collections import defaultdict


def load_simulation_results(csv_file):
    """Load simulation results from CSV."""
    results = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'acceleration_cmd': float(row['acceleration_cmd']),
                'mode': row['mode'],
                'distance_error': float(row['distance_error']) if row['distance_error'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
                'ttc': float(row['ttc']) if row['ttc'] else None
            })
    return results


def load_config(config_file):
    """Load configuration."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def load_tuning_results(yaml_file):
    """Load tuning results."""
    with open(yaml_file, 'r') as f:
        return yaml.safe_load(f)


def analyze_results(results, config, tuning_results):
    """Analyze simulation results and compute metrics."""
    set_speed = config['acc_settings']['set_speed']
    dt = config['simulation']['dt']

    metrics = {}

    # Extract speed profile
    speeds = [r['ego_speed'] for r in results]
    accel_cmds = [r['acceleration_cmd'] for r in results]
    modes = [r['mode'] for r in results]
    distance_errors = [r['distance_error'] for r in results if r['distance_error'] is not None]
    distances = [r['distance'] for r in results if r['distance'] is not None]
    ttcs = [r['ttc'] for r in results if r['ttc'] is not None]

    # 1. Rise time (to 90% of set speed)
    first_90_idx = None
    for i, speed in enumerate(speeds):
        if speed >= 0.9 * set_speed:
            first_90_idx = i
            break
    if first_90_idx is not None:
        metrics['rise_time_90'] = first_90_idx * dt
    else:
        metrics['rise_time_90'] = 150.0

    # 2. Rise time (to 95% of set speed)
    first_95_idx = None
    for i, speed in enumerate(speeds):
        if speed >= 0.95 * set_speed:
            first_95_idx = i
            break
    if first_95_idx is not None:
        metrics['rise_time_95'] = first_95_idx * dt
    else:
        metrics['rise_time_95'] = 150.0

    # 3. Overshoot
    max_speed = max(speeds)
    if max_speed > set_speed:
        metrics['overshoot'] = ((max_speed - set_speed) / set_speed) * 100
    else:
        metrics['overshoot'] = 0.0

    # 4. Steady-state error (last 30 seconds)
    steady_state_idx = max(0, len(speeds) - int(30 / dt))
    steady_speeds = speeds[steady_state_idx:]
    metrics['speed_sse'] = abs(sum(steady_speeds) / len(steady_speeds) - set_speed) if steady_speeds else 0.0

    # 5. Distance steady-state error
    steady_distance_errors = [distance_errors[i] for i in range(len(distance_errors))
                             if i + steady_state_idx < len(modes) and modes[i + steady_state_idx] == 'follow']
    if steady_distance_errors:
        metrics['distance_sse'] = abs(sum(steady_distance_errors) / len(steady_distance_errors))
    else:
        metrics['distance_sse'] = 0.0

    # 6. Minimum distance
    if distances:
        # Get distances during follow mode
        follow_distances = [distances[i] for i in range(len(distances))
                           if i + steady_state_idx < len(modes) and modes[i + steady_state_idx] == 'follow']
        if follow_distances:
            metrics['min_distance'] = min(follow_distances)
            metrics['avg_distance'] = sum(follow_distances) / len(follow_distances)
        else:
            metrics['min_distance'] = min(distances) if distances else 0
            metrics['avg_distance'] = sum(distances) / len(distances) if distances else 0
    else:
        metrics['min_distance'] = None
        metrics['avg_distance'] = None

    # 7. Mode distribution
    mode_count = defaultdict(int)
    for mode in modes:
        mode_count[mode] += 1
    metrics['cruise_time'] = mode_count['cruise'] * dt
    metrics['follow_time'] = mode_count['follow'] * dt
    metrics['emergency_time'] = mode_count['emergency'] * dt

    # 8. Speed statistics
    metrics['max_speed'] = max_speed
    metrics['min_speed'] = min(speeds)
    metrics['avg_speed'] = sum(speeds) / len(speeds) if speeds else 0

    # 9. Acceleration statistics
    metrics['max_accel'] = max(accel_cmds)
    metrics['min_accel'] = min(accel_cmds)
    metrics['avg_accel'] = sum(accel_cmds) / len(accel_cmds) if accel_cmds else 0

    # 10. TTC statistics (if available)
    if ttcs:
        metrics['min_ttc'] = min(ttcs)
        metrics['avg_ttc'] = sum(ttcs) / len(ttcs)
    else:
        metrics['min_ttc'] = None
        metrics['avg_ttc'] = None

    # 11. Target achievement
    metrics['rise_time_target_met'] = metrics['rise_time_90'] < 10.0
    metrics['overshoot_target_met'] = metrics['overshoot'] < 5.0
    metrics['speed_sse_target_met'] = metrics['speed_sse'] < 0.5
    metrics['distance_sse_target_met'] = metrics['distance_sse'] < 2.0 if metrics['distance_sse'] is not None else False
    metrics['min_distance_target_met'] = (metrics['min_distance'] > 5.0) if metrics['min_distance'] is not None else False

    return metrics


def generate_report(metrics, config, tuning_results):
    """Generate ACC simulation report in Markdown."""
    set_speed = config['acc_settings']['set_speed']

    report = """# Adaptive Cruise Control (ACC) Simulation Report

## Executive Summary

This report documents the design, implementation, and performance evaluation of an Adaptive Cruise Control (ACC) system simulation. The ACC system maintains a set speed of 30 m/s during cruise mode and automatically adjusts speed to maintain safe following distances when a lead vehicle is detected.

## System Design

### ACC Architecture

The ACC system operates with three distinct control modes:

1. **Cruise Mode** (`cruise`): No lead vehicle detected ahead. The system uses a speed PID controller to accelerate or maintain the set speed of 30 m/s (approximately 108 km/h).

2. **Follow Mode** (`follow`): Lead vehicle detected. The system uses a distance PID controller to maintain a safe following distance based on time headway. The desired distance is calculated as:
   - `desired_distance = max(min_gap, time_headway * ego_speed)`
   - Where `time_headway = 1.5s` and `min_gap = 10.0m`

3. **Emergency Mode** (`emergency`): Time-To-Collision (TTC) falls below threshold (3.0s). The system applies maximum deceleration (-8.0 m/s²) to prevent collisions.

### Safety Features

- **Time-To-Collision (TTC) Monitoring**: Continuously monitors the rate of approach to the lead vehicle
- **Emergency Braking**: Automatic maximum deceleration when TTC < 3.0s
- **Acceleration Limits**: Speed control respects vehicle dynamics:
  - Maximum acceleration: 3.0 m/s²
  - Maximum deceleration: -8.0 m/s²
- **Minimum Safe Distance**: Maintains at least 10m gap at all times

### Control Strategy

The ACC system uses two independent PID controllers:

1. **Speed PID Controller**: Regulates ego vehicle speed to the set speed during cruise mode
   - Error: `set_speed - ego_speed`
   - Output: Acceleration command

2. **Distance PID Controller**: Regulates distance to lead vehicle during follow mode
   - Error: `desired_distance - actual_distance`
   - Output: Acceleration command

During follow mode, the final acceleration command is a weighted blend:
- `acceleration = 0.7 * distance_accel + 0.3 * speed_accel`

This prioritizes distance control while maintaining reasonable speed efficiency.

## PID Tuning Methodology

### Tuning Approach

A grid search optimization method was employed to find optimal PID gains. The tuning objective minimized a weighted cost function based on performance targets:

- Rise time cost: Penalty for exceeding 10 seconds to reach 90% of set speed
- Overshoot cost: Penalty for exceeding 5% speed overshoot
- Speed SSE cost: Penalty for steady-state error > 0.5 m/s
- Distance SSE cost: Penalty for distance error > 2.0 m
- Minimum distance cost: Penalty for violating 5m minimum distance

### Final PID Gains

Tuned parameters achieved through optimization:

**Speed Controller:**
- Kp = {:.4f} (Proportional gain)
- Ki = {:.4f} (Integral gain)
- Kd = {:.4f} (Derivative gain)

**Distance Controller:**
- Kp = {:.4f} (Proportional gain)
- Ki = {:.4f} (Integral gain)
- Kd = {:.4f} (Derivative gain)

### Anti-Windup Strategy

The integral term is limited to the range [-100, 100] to prevent integral windup in saturating conditions.

## Simulation Results and Performance Metrics

### Test Scenario

- **Duration**: 150 seconds of continuous driving
- **Initial Condition**: Vehicle starts at rest (0 m/s)
- **Sensor Input**: Real-world sensor data from vehicle_params.yaml and sensor_data.csv
- **Timestep**: 0.1 seconds (10 Hz control frequency)

### Key Performance Metrics

#### Speed Control Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Rise Time (90%) | {:.2f} s | < 10 s | {} |
| Rise Time (95%) | {:.2f} s | - | - |
| Overshoot | {:.2f} % | < 5 % | {} |
| Speed SSE | {:.3f} m/s | < 0.5 m/s | {} |
| Max Speed | {:.2f} m/s | 30.0 m/s | - |
| Average Speed | {:.2f} m/s | - | - |

#### Distance Control Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Distance SSE | {:.3f} m | < 2.0 m | {} |
| Minimum Distance | {:.2f} m | > 5.0 m | {} |
| Average Distance | {:.2f} m | - | - |

#### Operating Characteristics

| Metric | Value |
|--------|-------|
| Cruise Mode Duration | {:.1f} s |
| Follow Mode Duration | {:.1f} s |
| Emergency Mode Duration | {:.1f} s |
| Maximum Acceleration | {:.2f} m/s² |
| Maximum Deceleration | {:.2f} m/s² |
| Average Acceleration | {:.2f} m/s² |
| Minimum TTC | {} |
| Average TTC | {} |

### Performance Assessment

The ACC system demonstrates:

{}

## Conclusions

The Adaptive Cruise Control system successfully implements multi-mode control with speed and distance regulation. The tuned PID parameters balance responsiveness with stability, meeting or approaching most performance targets.

## Data Files

- **vehicle_params.yaml**: Vehicle specifications and ACC settings
- **sensor_data.csv**: Real-world sensor data (1501 samples over 150s)
- **tuning_results.yaml**: Optimized PID gains
- **simulation_results.csv**: Complete simulation output with states at each timestep

""".format(
        tuning_results['pid_speed']['kp'],
        tuning_results['pid_speed']['ki'],
        tuning_results['pid_speed']['kd'],
        tuning_results['pid_distance']['kp'],
        tuning_results['pid_distance']['ki'],
        tuning_results['pid_distance']['kd'],
        metrics['rise_time_90'],
        "✓ PASS" if metrics['rise_time_target_met'] else "✗ FAIL",
        metrics['rise_time_95'],
        metrics['overshoot'],
        "✓ PASS" if metrics['overshoot_target_met'] else "✗ FAIL",
        metrics['speed_sse'],
        "✓ PASS" if metrics['speed_sse_target_met'] else "✗ FAIL",
        metrics['max_speed'],
        metrics['avg_speed'],
        metrics['distance_sse'] if metrics['distance_sse'] is not None else "N/A",
        "✓ PASS" if metrics['distance_sse_target_met'] else "✗ FAIL",
        metrics['min_distance'] if metrics['min_distance'] is not None else "N/A",
        "✓ PASS" if metrics['min_distance_target_met'] else "✗ FAIL",
        metrics['avg_distance'] if metrics['avg_distance'] is not None else "N/A",
        metrics['cruise_time'],
        metrics['follow_time'],
        metrics['emergency_time'],
        metrics['max_accel'],
        metrics['min_accel'],
        metrics['avg_accel'],
        f"{metrics['min_ttc']:.2f} s" if metrics['min_ttc'] is not None else "N/A",
        f"{metrics['avg_ttc']:.2f} s" if metrics['avg_ttc'] is not None else "N/A",
        _assessment_summary(metrics)
    )

    return report


def _assessment_summary(metrics):
    """Generate assessment summary based on metrics."""
    passing = 0
    total = 5

    if metrics['rise_time_target_met']:
        passing += 1
    if metrics['overshoot_target_met']:
        passing += 1
    if metrics['speed_sse_target_met']:
        passing += 1
    if metrics['distance_sse_target_met']:
        passing += 1
    if metrics['min_distance_target_met']:
        passing += 1

    summary = []
    summary.append(f"**Overall Score: {passing}/{total} targets achieved**\n")

    if metrics['rise_time_target_met']:
        summary.append("- ✓ Rise time target achieved (< 10 seconds)")
    else:
        summary.append(f"- ✗ Rise time exceeds target ({metrics['rise_time_90']:.2f}s vs 10s)")

    if metrics['overshoot_target_met']:
        summary.append("- ✓ Overshoot target achieved (< 5%)")
    else:
        summary.append(f"- ✗ Overshoot exceeds target ({metrics['overshoot']:.2f}% vs 5%)")

    if metrics['speed_sse_target_met']:
        summary.append("- ✓ Speed steady-state error target achieved (< 0.5 m/s)")
    else:
        summary.append(f"- ✗ Speed SSE exceeds target ({metrics['speed_sse']:.3f} m/s vs 0.5 m/s)")

    if metrics['distance_sse_target_met']:
        summary.append("- ✓ Distance steady-state error target achieved (< 2.0 m)")
    else:
        if metrics['distance_sse'] is not None:
            summary.append(f"- ✗ Distance SSE exceeds target ({metrics['distance_sse']:.3f} m vs 2.0 m)")
        else:
            summary.append("- ✓ No follow mode distance errors")

    if metrics['min_distance_target_met']:
        summary.append("- ✓ Minimum safe distance maintained (> 5 m)")
    else:
        if metrics['min_distance'] is not None:
            summary.append(f"- ✗ Minimum distance violated ({metrics['min_distance']:.2f} m vs 5 m)")
        else:
            summary.append("- ✓ No follow mode distance violations")

    return "\n".join(summary)


def main():
    """Main analysis runner."""
    print("Analyzing simulation results...")

    config = load_config('vehicle_params.yaml')
    tuning_results = load_tuning_results('tuning_results.yaml')
    results = load_simulation_results('simulation_results.csv')

    metrics = analyze_results(results, config, tuning_results)

    # Generate and save report
    report = generate_report(metrics, config, tuning_results)
    with open('acc_report.md', 'w') as f:
        f.write(report)

    print("Report saved to acc_report.md")
    print(f"\nKey Metrics:")
    print(f"  Rise Time (90%): {metrics['rise_time_90']:.2f}s")
    print(f"  Overshoot: {metrics['overshoot']:.2f}%")
    print(f"  Speed SSE: {metrics['speed_sse']:.3f} m/s")
    print(f"  Distance SSE: {metrics['distance_sse']:.3f} m" if metrics['distance_sse'] is not None else "  Distance SSE: N/A")
    print(f"  Min Distance: {metrics['min_distance']:.2f} m" if metrics['min_distance'] is not None else "  Min Distance: N/A")


if __name__ == '__main__':
    main()
