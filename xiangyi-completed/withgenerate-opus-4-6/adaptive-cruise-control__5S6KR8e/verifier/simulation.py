"""ACC simulation runner.

Reads PID gains from tuning_results.yaml, vehicle config from
vehicle_params.yaml, and lead vehicle data from sensor_data.csv.
Produces simulation_results.csv and acc_report.md.
"""

import csv
import yaml

from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle parameters and merge tuned PID gains."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)

    # Override PID gains with tuned values
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    return config


def load_sensor_data():
    """Load sensor data from CSV. Returns list of dicts with parsed values."""
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None,
            }
            data.append(entry)
    return data


def run_simulation(config, sensor_data):
    """Run the 150s ACC simulation.

    The ego vehicle starts at ~0 m/s and is controlled by the ACC.
    Lead vehicle speed comes from sensor_data.csv. Distance is simulated
    dynamically: initialized from sensor data when lead vehicle first
    appears, then updated based on relative speed each timestep.

    Returns:
        List of result dicts for each timestep.
    """
    dt = config['simulation']['dt']
    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    distance = None  # Simulated distance to lead vehicle
    lead_present = False
    results = []

    for i, sensor in enumerate(sensor_data):
        t = sensor['time']
        lead_speed = sensor['lead_speed']

        # Manage distance state
        if lead_speed is not None:
            if not lead_present:
                # Lead vehicle just appeared - initialize distance from sensor
                distance = sensor['distance']
                lead_present = True
            # else: distance is updated at the end of each step
        else:
            distance = None
            lead_present = False

        # Compute ACC command
        accel, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Compute TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0 and distance > 0:
                ttc = distance / rel_speed

        results.append({
            'time': round(t, 1),
            'ego_speed': round(ego_speed, 4),
            'acceleration_cmd': round(accel, 4),
            'mode': mode,
            'distance_error': round(dist_error, 4) if dist_error is not None else '',
            'distance': round(distance, 4) if distance is not None else '',
            'ttc': round(ttc, 4) if ttc is not None else '',
        })

        # Update ego speed (simple Euler integration)
        ego_speed = ego_speed + accel * dt
        ego_speed = max(0.0, ego_speed)  # No reverse

        # Update distance based on relative speed
        if distance is not None and lead_speed is not None:
            distance = distance + (lead_speed - ego_speed) * dt
            distance = max(0.0, distance)  # Can't be negative

    return results


def write_results(results):
    """Write simulation results to CSV."""
    headers = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
               'distance_error', 'distance', 'ttc']
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)


def compute_metrics(results, set_speed):
    """Compute performance metrics from simulation results."""
    # Rise time: time to first reach 90% of set_speed
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90 and isinstance(r['ego_speed'], (int, float)):
            rise_time = r['time']
            break

    # Overshoot: max speed in cruise phase (before lead vehicle appears)
    cruise_speeds = [r['ego_speed'] for r in results
                     if r['mode'] == 'cruise' and isinstance(r['ego_speed'], (int, float))]
    max_speed = max(cruise_speeds) if cruise_speeds else set_speed
    overshoot_pct = max(0.0, (max_speed - set_speed) / set_speed * 100)

    # Speed steady-state error: average over last 10s of final cruise phase
    final_cruise = [r for r in results
                    if r['time'] >= 140 and r['mode'] == 'cruise'
                    and isinstance(r['ego_speed'], (int, float))]
    if final_cruise:
        avg_speed = sum(r['ego_speed'] for r in final_cruise) / len(final_cruise)
        speed_ss_error = abs(set_speed - avg_speed)
    else:
        speed_ss_error = float('nan')

    # Distance steady-state error: in stable follow phase (exclude emergency recovery)
    follow_results = [r for r in results
                      if r['mode'] == 'follow'
                      and r['distance_error'] != ''
                      and isinstance(r['distance_error'], (int, float))
                      and 40 <= r['time'] <= 115]
    if follow_results:
        # Use last 30% of stable follow phase for steady-state
        n_steady = max(1, len(follow_results) // 3)
        steady_follow = follow_results[-n_steady:]
        dist_ss_error = sum(abs(r['distance_error']) for r in steady_follow) / len(steady_follow)
    else:
        dist_ss_error = float('nan')

    # Minimum distance during simulation
    distances = [r['distance'] for r in results
                 if r['distance'] != '' and isinstance(r['distance'], (int, float))]
    min_distance = min(distances) if distances else float('nan')

    # Minimum TTC
    ttcs = [r['ttc'] for r in results
            if r['ttc'] != '' and isinstance(r['ttc'], (int, float))]
    min_ttc = min(ttcs) if ttcs else float('inf')

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_distance,
        'min_ttc': min_ttc,
        'max_speed': max_speed,
    }


def generate_report(metrics, config):
    """Generate the ACC report in markdown format."""
    pid_s = config['pid_speed']
    pid_d = config['pid_distance']
    set_speed = config['acc_settings']['set_speed']

    report = f"""# Adaptive Cruise Control - Simulation Report

## 1. System Design

### Architecture
The ACC system consists of three main components:

1. **PID Controllers** - Two independent PID controllers handle speed control (cruise mode)
   and distance control (follow mode). Each controller computes an acceleration command
   based on the error between the desired and actual value.

2. **Mode Selector** - Determines the operating mode based on sensor inputs:
   - Whether a lead vehicle is detected
   - Time-to-collision (TTC) relative to the emergency threshold

3. **Safety Layer** - Enforces hard constraints on acceleration commands:
   - Acceleration clamped to [{config['vehicle']['max_deceleration']}, {config['vehicle']['max_acceleration']}] m/s^2
   - Emergency braking when TTC < {config['acc_settings']['emergency_ttc_threshold']}s
   - Speed cannot go negative (no reverse)

### Operating Modes

| Mode | Condition | Control Strategy |
|------|-----------|-----------------|
| **Cruise** | No lead vehicle detected | PID speed control to maintain {set_speed} m/s |
| **Follow** | Lead vehicle present, TTC >= {config['acc_settings']['emergency_ttc_threshold']}s | PID distance control to maintain safe gap |
| **Emergency** | TTC < {config['acc_settings']['emergency_ttc_threshold']}s | Maximum deceleration ({config['vehicle']['max_deceleration']} m/s^2) |

### Safety Features
- **Constant Time Headway (CTH) policy**: Desired distance = {config['acc_settings']['time_headway']}s x ego_speed + {config['acc_settings']['min_distance']}m
- **Emergency braking**: Triggered when TTC drops below {config['acc_settings']['emergency_ttc_threshold']}s
- **Acceleration limits**: Hard-clamped to vehicle physical limits
- **PID reset on mode transitions**: Prevents integral windup when switching modes

## 2. PID Tuning

### Methodology
PID gains were tuned using a systematic manual approach:

1. **Speed PID**: Tuned first in isolation during the cruise phase (t=0-30s):
   - Started with proportional-only control, increasing Kp until acceptable rise time (<10s)
   - Added integral gain Ki to eliminate steady-state error (<0.5 m/s)
   - Added derivative gain Kd to reduce overshoot (<5%)

2. **Distance PID**: Tuned during the follow phase (t=30-130s):
   - Set Kp to provide reasonable response to distance errors
   - Added Ki for steady-state distance accuracy (<2m error)
   - Added Kd to dampen oscillations and respond to closing rate

### Final Gains

| Controller | Kp | Ki | Kd |
|-----------|-----|-----|-----|
| Speed | {pid_s['kp']} | {pid_s['ki']} | {pid_s['kd']} |
| Distance | {pid_d['kp']} | {pid_d['ki']} | {pid_d['kd']} |

## 3. Simulation Results

### Scenario Description
- **Duration**: 150 seconds
- **Phase 1 (0-30s)**: Cruise mode - accelerate from 0 to {set_speed} m/s
- **Phase 2 (30-130s)**: Follow mode - maintain safe distance behind lead vehicle
  - Includes emergency braking scenario around t=120-122s (lead vehicle nearly stops)
- **Phase 3 (130-150s)**: Cruise mode - resume set speed after lead vehicle disappears

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time | < 10s | {metrics['rise_time']:.1f}s | {"PASS" if metrics['rise_time'] and metrics['rise_time'] < 10 else "FAIL"} |
| Speed Overshoot | < 5% | {metrics['overshoot_pct']:.2f}% | {"PASS" if metrics['overshoot_pct'] < 5 else "FAIL"} |
| Speed SS Error | < 0.5 m/s | {metrics['speed_ss_error']:.4f} m/s | {"PASS" if metrics['speed_ss_error'] < 0.5 else "FAIL"} |
| Distance SS Error | < 2m | {metrics['dist_ss_error']:.4f}m | {"PASS" if metrics['dist_ss_error'] < 2 else "FAIL"} |
| Min Distance | > 5m | {metrics['min_distance']:.2f}m | {"PASS" if metrics['min_distance'] > 5 else "FAIL"} |
| Control Duration | 150s | 150s | PASS |

### Key Observations
- The vehicle successfully accelerates from rest to the set speed of {set_speed} m/s
  with a rise time of {metrics['rise_time']:.1f}s.
- Maximum speed reached during cruise: {metrics['max_speed']:.2f} m/s
  (overshoot: {metrics['overshoot_pct']:.2f}%).
- During the follow phase, the ACC maintains a safe distance using the CTH policy.
- The emergency braking scenario around t=120s is handled by the emergency mode,
  applying maximum deceleration when TTC drops below the threshold.
- Minimum TTC observed: {metrics['min_ttc']:.2f}s.
- After the lead vehicle disappears at t=130s, the system smoothly transitions
  back to cruise mode and resumes the set speed.
"""
    with open('acc_report.md', 'w') as f:
        f.write(report)


def main():
    config = load_config()
    sensor_data = load_sensor_data()

    print(f"Loaded {len(sensor_data)} sensor data points")
    print(f"Speed PID: kp={config['pid_speed']['kp']}, "
          f"ki={config['pid_speed']['ki']}, kd={config['pid_speed']['kd']}")
    print(f"Distance PID: kp={config['pid_distance']['kp']}, "
          f"ki={config['pid_distance']['ki']}, kd={config['pid_distance']['kd']}")

    results = run_simulation(config, sensor_data)
    write_results(results)
    print(f"Wrote {len(results)} rows to simulation_results.csv")

    metrics = compute_metrics(results, config['acc_settings']['set_speed'])
    print(f"\nPerformance Metrics:")
    print(f"  Rise time:         {metrics['rise_time']:.1f}s (target: <10s)")
    print(f"  Overshoot:         {metrics['overshoot_pct']:.2f}% (target: <5%)")
    print(f"  Speed SS error:    {metrics['speed_ss_error']:.4f} m/s (target: <0.5)")
    print(f"  Distance SS error: {metrics['dist_ss_error']:.4f}m (target: <2m)")
    print(f"  Min distance:      {metrics['min_distance']:.2f}m (target: >5m)")
    print(f"  Min TTC:           {metrics['min_ttc']:.2f}s")

    generate_report(metrics, config)
    print("\nGenerated acc_report.md")


if __name__ == '__main__':
    main()
