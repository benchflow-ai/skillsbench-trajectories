"""
ACC Simulation runner.
Reads PID gains from tuning_results.yaml and runs 150s simulation.
Properly simulates distance based on relative velocities.
"""

import csv
import yaml
from typing import Optional
from acc_system import AdaptiveCruiseControl


def load_config():
    """Load vehicle parameters and merge with tuned PID gains."""
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
    
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']
    
    return config


def load_sensor_data():
    """Load sensor data from CSV file."""
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def run_simulation():
    """Run the ACC simulation for 150 seconds."""
    config = load_config()
    sensor_data = load_sensor_data()
    acc = AdaptiveCruiseControl(config)
    
    dt = config['simulation']['dt']
    
    # Initial state
    ego_speed = 0.0
    simulated_distance = None  # Will be set when lead vehicle first appears
    lead_was_present = False
    
    results = []
    
    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']  # Real sensor measurement
        
        # Handle distance simulation
        if lead_speed is not None:
            if not lead_was_present:
                # Lead vehicle just appeared - use sensor distance as initial
                simulated_distance = sensor_distance
                lead_was_present = True
            # else: simulated_distance will be updated at end of loop
            current_distance = simulated_distance
        else:
            # No lead vehicle
            simulated_distance = None
            current_distance = None
            lead_was_present = False
        
        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, current_distance, dt
        )
        
        # Calculate TTC if lead vehicle present
        ttc = None
        if lead_speed is not None and current_distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01:
                ttc = current_distance / relative_speed
        
        # Store result
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': current_distance,
            'ttc': ttc
        }
        results.append(result)
        
        # Update ego speed for next timestep
        ego_speed = ego_speed + accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
        # Update simulated distance for next timestep
        if simulated_distance is not None and lead_speed is not None:
            # Distance changes based on relative speed
            # If ego is faster than lead, distance decreases
            relative_speed = ego_speed - lead_speed
            simulated_distance = simulated_distance - relative_speed * dt
            # Ensure distance doesn't go negative
            simulated_distance = max(0.1, simulated_distance)
    
    return results


def save_results(results, filename='simulation_results.csv'):
    """Save simulation results to CSV file."""
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 
                  'distance_error', 'distance', 'ttc']
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in results:
            formatted = {
                'time': f"{row['time']:.1f}" if row['time'] is not None else '',
                'ego_speed': f"{row['ego_speed']:.1f}" if row['ego_speed'] is not None else '',
                'acceleration_cmd': f"{row['acceleration_cmd']:.2f}" if row['acceleration_cmd'] is not None else '',
                'mode': row['mode'],
                'distance_error': f"{row['distance_error']:.2f}" if row['distance_error'] is not None else '',
                'distance': f"{row['distance']:.2f}" if row['distance'] is not None else '',
                'ttc': f"{row['ttc']:.2f}" if row['ttc'] is not None else ''
            }
            writer.writerow(formatted)
    
    print(f"Results saved to {filename}")


def analyze_results(results):
    """Analyze simulation results and compute performance metrics."""
    metrics = {}
    set_speed = 30.0
    
    # Rise time (time to reach 90% of set speed)
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break
    metrics['rise_time'] = rise_time
    
    # Max speed and overshoot
    max_speed = max(r['ego_speed'] for r in results)
    overshoot = ((max_speed - set_speed) / set_speed) * 100 if max_speed > set_speed else 0
    metrics['max_speed'] = max_speed
    metrics['overshoot_percent'] = overshoot
    
    # Steady-state speed error (last 10 seconds of cruise mode)
    cruise_end_results = [r for r in results if r['mode'] == 'cruise' and r['time'] >= 140]
    if cruise_end_results:
        avg_speed = sum(r['ego_speed'] for r in cruise_end_results) / len(cruise_end_results)
        ss_speed_error = abs(set_speed - avg_speed)
    else:
        ss_speed_error = None
    metrics['steady_state_speed_error'] = ss_speed_error
    
    # Distance metrics
    follow_results = [r for r in results if r['mode'] == 'follow']
    if follow_results:
        distances = [r['distance'] for r in follow_results if r['distance'] is not None]
        if distances:
            min_distance = min(distances)
            metrics['min_distance'] = min_distance
        
        dist_errors = [abs(r['distance_error']) for r in follow_results if r['distance_error'] is not None]
        if dist_errors:
            metrics['avg_distance_error'] = sum(dist_errors) / len(dist_errors)
            
            # Steady-state distance error (last portion of follow mode)
            late_follow = [r for r in follow_results if r['distance_error'] is not None][-200:]
            if late_follow:
                ss_dist_error = sum(abs(r['distance_error']) for r in late_follow) / len(late_follow)
                metrics['steady_state_distance_error'] = ss_dist_error
    
    # Emergency count
    metrics['emergency_count'] = sum(1 for r in results if r['mode'] == 'emergency')
    
    # Mode distribution
    mode_counts = {'cruise': 0, 'follow': 0, 'emergency': 0}
    for r in results:
        mode_counts[r['mode']] += 1
    metrics['mode_distribution'] = mode_counts
    
    return metrics


def print_metrics(metrics):
    """Print performance metrics."""
    print("\n" + "="*50)
    print("SIMULATION PERFORMANCE METRICS")
    print("="*50)
    
    print("\nSpeed Control:")
    rt = metrics.get('rise_time')
    print(f"  Rise time (to 90% of 30 m/s): {rt:.1f} s" if rt else "  Rise time: N/A")
    print(f"  Maximum speed: {metrics.get('max_speed', 0):.2f} m/s")
    print(f"  Overshoot: {metrics.get('overshoot_percent', 0):.2f}%")
    sse = metrics.get('steady_state_speed_error')
    print(f"  Steady-state speed error: {sse:.3f} m/s" if sse is not None else "  Steady-state speed error: N/A")
    
    print("\nDistance Control:")
    md = metrics.get('min_distance')
    print(f"  Minimum distance: {md:.2f} m" if md else "  Minimum distance: N/A")
    ade = metrics.get('avg_distance_error')
    print(f"  Average distance error: {ade:.2f} m" if ade else "  Average distance error: N/A")
    dse = metrics.get('steady_state_distance_error')
    print(f"  Steady-state distance error: {dse:.2f} m" if dse is not None else "  Steady-state distance error: N/A")
    
    print("\nMode Distribution:")
    dist = metrics.get('mode_distribution', {})
    total = sum(dist.values())
    for mode, count in dist.items():
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {mode}: {count} ({pct:.1f}%)")
    
    print("\nSafety:")
    print(f"  Emergency braking events: {metrics.get('emergency_count', 0)}")
    
    # Target compliance
    print("\n" + "="*50)
    print("TARGET COMPLIANCE")
    print("="*50)
    
    rt = metrics.get('rise_time')
    if rt and rt < 10:
        print(f"  [PASS] Rise time {rt:.1f}s < 10s")
    else:
        print(f"  [FAIL] Rise time {rt}s >= 10s" if rt else "  [FAIL] Rise time not measured")
    
    os = metrics.get('overshoot_percent', 100)
    if os < 5:
        print(f"  [PASS] Overshoot {os:.2f}% < 5%")
    else:
        print(f"  [FAIL] Overshoot {os:.2f}% >= 5%")
    
    sse = metrics.get('steady_state_speed_error')
    if sse is not None and sse < 0.5:
        print(f"  [PASS] Speed SS error {sse:.3f} m/s < 0.5 m/s")
    else:
        print(f"  [FAIL] Speed SS error {sse} m/s >= 0.5 m/s" if sse else "  [FAIL] Speed SS error not measured")
    
    dse = metrics.get('steady_state_distance_error')
    if dse is not None and dse < 2:
        print(f"  [PASS] Distance SS error {dse:.2f}m < 2m")
    elif dse is not None:
        print(f"  [FAIL] Distance SS error {dse:.2f}m >= 2m")
    
    md = metrics.get('min_distance')
    if md and md > 5:
        print(f"  [PASS] Min distance {md:.2f}m > 5m")
    else:
        print(f"  [FAIL] Min distance {md}m <= 5m" if md else "  [INFO] Min distance not applicable")
    
    return metrics


if __name__ == "__main__":
    print("Running ACC Simulation...")
    print("Loading configuration and sensor data...")
    
    results = run_simulation()
    save_results(results)
    metrics = analyze_results(results)
    print_metrics(metrics)
    
    print(f"\nSimulation complete. {len(results)} timesteps processed.")
