"""ACC Simulation runner with proper position tracking."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


def load_yaml(filepath):
    """Load YAML configuration file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def load_sensor_data(filepath):
    """Load sensor data from CSV file."""
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'time': float(row['time']),
                'ref_ego_speed': float(row['ego_speed']) if row['ego_speed'] else 0.0,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'ref_distance': float(row['distance']) if row['distance'] else None
            }
            data.append(entry)
    return data


def run_simulation():
    """Run the ACC simulation with proper position tracking."""
    # Load configurations
    vehicle_config = load_yaml('vehicle_params.yaml')
    tuning_config = load_yaml('tuning_results.yaml')
    
    # Load sensor data for lead vehicle information
    sensor_data = load_sensor_data('sensor_data.csv')
    
    # Initialize ACC system
    acc = AdaptiveCruiseControl(vehicle_config)
    
    # Update with tuned PID gains
    acc.set_pid_gains(tuning_config['pid_speed'], tuning_config['pid_distance'])
    
    # Simulation parameters
    dt = vehicle_config['simulation']['dt']
    
    # Initial state - ego vehicle
    ego_speed = 0.0
    ego_position = 0.0
    
    # Lead vehicle state
    lead_position = None
    lead_active = False
    
    # Results storage
    results = []
    
    # Run simulation
    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        
        # Handle lead vehicle
        if lead_speed is not None:
            if not lead_active:
                initial_distance = sensor['ref_distance'] if sensor['ref_distance'] else 50.0
                lead_position = ego_position + initial_distance
                lead_active = True
            distance = lead_position - ego_position
        else:
            lead_active = False
            lead_position = None
            distance = None
        
        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )
        
        # Format output strings
        if lead_speed is not None and distance is not None:
            ttc = acc.compute_ttc(ego_speed, lead_speed, distance)
            ttc_str = '' if ttc == float('inf') else f'{ttc:.2f}'
            distance_str = f'{distance:.2f}'
            dist_error_str = f'{distance_error:.2f}' if distance_error is not None else ''
        else:
            ttc_str = ''
            distance_str = ''
            dist_error_str = ''
        
        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 10),
            'acceleration_cmd': round(accel_cmd, 10),
            'mode': mode,
            'distance_error': dist_error_str,
            'distance': distance_str,
            'ttc': ttc_str
        })
        
        # Update states
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        ego_position += ego_speed * dt
        
        if lead_active and lead_speed is not None:
            lead_position += lead_speed * dt
    
    # Write results
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 
                      'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total timesteps: {len(results)}")
    
    analyze_results(results, vehicle_config)
    return results


def analyze_results(results, config):
    """Analyze simulation results and print metrics."""
    set_speed = config['acc_settings']['set_speed']
    
    # Rise time (to 90% of set speed)
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break
    
    # Max speed during initial cruise (before t=30)
    cruise_speeds = [r['ego_speed'] for r in results if r['time'] < 30]
    max_cruise_speed = max(cruise_speeds) if cruise_speeds else 0
    
    # Overshoot
    overshoot = ((max_cruise_speed - set_speed) / set_speed) * 100 if max_cruise_speed > set_speed else 0
    
    # Speed SS error (t=25-29s before lead appears)
    ss_cruise = [r['ego_speed'] for r in results if 25 <= r['time'] < 30]
    ss_speed_error = abs(set_speed - sum(ss_cruise) / len(ss_cruise)) if ss_cruise else 0
    
    # Also check final cruise (t=140-150)
    final_cruise = [r['ego_speed'] for r in results if r['time'] >= 140 and r['mode'] == 'cruise']
    if final_cruise:
        final_ss = abs(set_speed - sum(final_cruise) / len(final_cruise))
        ss_speed_error = max(ss_speed_error, final_ss)
    
    # Min distance during follow mode
    follow_dist = []
    for r in results:
        if r['distance'] and r['mode'] in ['follow', 'emergency']:
            try:
                follow_dist.append(float(r['distance']))
            except:
                pass
    min_distance = min(follow_dist) if follow_dist else float('inf')
    
    # Distance SS error - use stable middle portion of follow mode (t=50-100)
    dist_errors = []
    for r in results:
        if r['distance_error'] and 50 <= r['time'] <= 100:
            try:
                dist_errors.append(float(r['distance_error']))
            except:
                pass
    
    if dist_errors:
        ss_dist_error = abs(sum(dist_errors) / len(dist_errors))
    else:
        # Fallback to all follow mode data
        all_errors = [float(r['distance_error']) for r in results if r['distance_error']]
        ss_dist_error = abs(sum(all_errors) / len(all_errors)) if all_errors else 0
    
    print(f"\n=== Performance Metrics ===")
    if rise_time:
        print(f"Rise time (to 90% of {set_speed} m/s): {rise_time:.1f}s")
    else:
        print("Rise time: N/A")
    print(f"Maximum cruise speed: {max_cruise_speed:.2f} m/s")
    print(f"Speed overshoot: {overshoot:.2f}%")
    print(f"Steady-state speed error: {ss_speed_error:.3f} m/s")
    print(f"Minimum following distance: {min_distance:.2f} m")
    print(f"Steady-state distance error: {ss_dist_error:.2f} m")
    
    print(f"\n=== Target Compliance ===")
    print(f"Rise time < 10s: {'PASS' if rise_time and rise_time < 10 else 'FAIL'}")
    print(f"Overshoot < 5%: {'PASS' if overshoot < 5 else 'FAIL'}")
    print(f"Speed SS error < 0.5 m/s: {'PASS' if ss_speed_error < 0.5 else 'FAIL'}")
    print(f"Distance SS error < 2m: {'PASS' if ss_dist_error < 2 else 'FAIL'}")
    print(f"Min distance > 5m: {'PASS' if min_distance > 5 else 'FAIL'}")


if __name__ == '__main__':
    run_simulation()
