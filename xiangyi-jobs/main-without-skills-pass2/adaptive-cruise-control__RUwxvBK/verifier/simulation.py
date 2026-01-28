"""
ACC Simulation - Runs vehicle simulation using ACC system
Reads PID gains from tuning_results.yaml and sensor data from sensor_data.csv
"""

import csv
import yaml
from typing import Optional
from pid_controller import PIDController
from acc_system import AdaptiveCruiseControl


def load_sensor_data(filename: str) -> list:
    """
    Load sensor data from CSV file.
    
    Args:
        filename: Path to sensor_data.csv
        
    Returns:
        List of dicts with time, ego_speed, lead_speed, distance
    """
    data = []
    with open(filename, 'r') as f:
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
    """
    Run the ACC simulation.
    """
    # Load vehicle parameters
    with open('vehicle_params.yaml', 'r') as f:
        vehicle_config = yaml.safe_load(f)
    
    # Load tuned PID parameters
    with open('tuning_results.yaml', 'r') as f:
        tuning_config = yaml.safe_load(f)
    
    # Override PID parameters with tuned values
    config = vehicle_config.copy()
    config['pid_speed'] = tuning_config['pid_speed']
    config['pid_distance'] = tuning_config['pid_distance']
    
    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')
    
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    
    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']
    
    # Initial state
    ego_speed = 0.0  # Start from rest
    
    # For distance tracking, we need to know when lead vehicle appears
    # and track the distance based on relative speeds
    distance = None  # Will be set when lead vehicle first appears
    initial_distance_set = False
    
    # Results storage
    results = []
    
    # Run simulation
    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        sensor_distance = sensor['distance']  # Initial/reference distance from sensor
        
        # Handle distance tracking
        if lead_speed is not None:
            if not initial_distance_set and sensor_distance is not None:
                # First time seeing lead vehicle - use sensor distance
                distance = sensor_distance
                initial_distance_set = True
            elif distance is not None:
                # Update distance based on relative speeds from previous step
                # This was already done at end of previous iteration
                pass
        else:
            # No lead vehicle
            distance = None
            initial_distance_set = False
        
        # Compute ACC command
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed=ego_speed,
            lead_speed=lead_speed,
            distance=distance,
            dt=dt
        )
        
        # Calculate TTC
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
        
        # Store result
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)
        
        # Update ego vehicle state for next timestep
        ego_speed = ego_speed + acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed can't be negative
        
        # Update distance for next timestep if lead vehicle present
        if distance is not None and lead_speed is not None:
            # Distance changes based on relative speed
            # If ego is faster than lead, distance decreases
            relative_speed = ego_speed - lead_speed
            distance = distance - relative_speed * dt
            distance = max(0.1, distance)  # Minimum distance to avoid division issues
    
    # Write results to CSV
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 
                      'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            row = {
                'time': f"{result['time']:.1f}",
                'ego_speed': f"{result['ego_speed']:.1f}" if result['ego_speed'] is not None else '',
                'acceleration_cmd': f"{result['acceleration_cmd']:.1f}",
                'mode': result['mode'],
                'distance_error': f"{result['distance_error']:.2f}" if result['distance_error'] is not None else '',
                'distance': f"{result['distance']:.1f}" if result['distance'] is not None else '',
                'ttc': f"{result['ttc']:.2f}" if result['ttc'] is not None else ''
            }
            writer.writerow(row)
    
    print(f"Simulation complete. Results written to simulation_results.csv")
    print(f"Total timesteps: {len(results)}")
    
    # Calculate and print performance metrics
    analyze_results(results, config)
    
    return results


def analyze_results(results: list, config: dict):
    """
    Analyze simulation results and print performance metrics.
    """
    set_speed = config['acc_settings']['set_speed']
    
    # Find rise time (time to reach 90% of set speed for first time)
    rise_time = None
    for r in results:
        if r['ego_speed'] >= 0.9 * set_speed:
            rise_time = r['time']
            break
    
    # Find max speed during cruise phase (before lead vehicle appears)
    cruise_results = [r for r in results if r['mode'] == 'cruise']
    if cruise_results:
        max_cruise_speed = max(r['ego_speed'] for r in cruise_results)
        overshoot = ((max_cruise_speed - set_speed) / set_speed) * 100 if max_cruise_speed > set_speed else 0
    else:
        max_cruise_speed = 0
        overshoot = 0
    
    # Calculate steady-state speed error (during stable cruise, t=15-30s)
    stable_cruise = [r for r in results if r['mode'] == 'cruise' and 15 <= r['time'] <= 30]
    if stable_cruise:
        avg_cruise_speed = sum(r['ego_speed'] for r in stable_cruise) / len(stable_cruise)
        speed_ss_error = abs(set_speed - avg_cruise_speed)
    else:
        speed_ss_error = None
    
    # Distance metrics (during follow mode, after settling)
    follow_results = [r for r in results if r['mode'] == 'follow' and r['time'] >= 35]
    if follow_results:
        distance_errors = [abs(r['distance_error']) for r in follow_results if r['distance_error'] is not None]
        avg_distance_error = sum(distance_errors) / len(distance_errors) if distance_errors else None
        distances = [r['distance'] for r in follow_results if r['distance'] is not None]
        min_distance = min(distances) if distances else None
    else:
        avg_distance_error = None
        min_distance = None
    
    # Also check minimum distance across all follow mode
    all_follow = [r for r in results if r['mode'] in ['follow', 'emergency']]
    if all_follow:
        all_distances = [r['distance'] for r in all_follow if r['distance'] is not None]
        absolute_min_distance = min(all_distances) if all_distances else None
    else:
        absolute_min_distance = None
    
    # Print metrics
    print("\n=== Performance Metrics ===")
    print(f"Rise time (to 90% of {set_speed} m/s): {rise_time:.1f}s" if rise_time else "Rise time: N/A")
    print(f"Max cruise speed: {max_cruise_speed:.2f} m/s")
    print(f"Speed overshoot: {overshoot:.2f}%")
    print(f"Speed steady-state error: {speed_ss_error:.3f} m/s" if speed_ss_error is not None else "Speed SS error: N/A")
    print(f"Average distance error (after settling): {avg_distance_error:.2f}m" if avg_distance_error else "Avg distance error: N/A")
    print(f"Minimum distance (after settling): {min_distance:.2f}m" if min_distance else "Min distance: N/A")
    print(f"Absolute minimum distance: {absolute_min_distance:.2f}m" if absolute_min_distance else "Abs min distance: N/A")
    
    # Check against targets
    print("\n=== Target Compliance ===")
    print(f"Rise time <10s: {'PASS' if rise_time and rise_time < 10 else 'FAIL'}")
    print(f"Overshoot <5%: {'PASS' if overshoot < 5 else 'FAIL'}")
    print(f"Speed SS error <0.5 m/s: {'PASS' if speed_ss_error is not None and speed_ss_error < 0.5 else 'FAIL'}")
    print(f"Distance SS error <2m: {'PASS' if avg_distance_error is not None and avg_distance_error < 2 else 'FAIL' if avg_distance_error else 'N/A'}")
    print(f"Min distance >5m: {'PASS' if absolute_min_distance and absolute_min_distance > 5 else 'FAIL' if absolute_min_distance else 'N/A'}")


if __name__ == "__main__":
    run_simulation()
