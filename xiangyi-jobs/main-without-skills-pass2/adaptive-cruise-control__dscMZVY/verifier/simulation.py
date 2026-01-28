import csv
import yaml
import math
from acc_system import AdaptiveCruiseControl

def load_config(config_file='vehicle_params.yaml'):
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def load_tuning_results(tuning_file='tuning_results.yaml'):
    """Load PID tuning results if available."""
    try:
        with open(tuning_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None

def load_sensor_data(sensor_file='sensor_data.csv'):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            ego_speed = float(row['ego_speed'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data

def run_simulation(config, tuning_results=None):
    """Run ACC simulation.
    
    Args:
        config: Configuration dictionary
        tuning_results: Optional tuning results to override defaults
        
    Returns:
        list: Simulation results
    """
    # Apply tuning results if provided
    if tuning_results:
        if 'pid_speed' in tuning_results:
            config['pid_speed'].update(tuning_results['pid_speed'])
        if 'pid_distance' in tuning_results:
            config['pid_distance'].update(tuning_results['pid_distance'])
    
    # Create ACC system
    acc = AdaptiveCruiseControl(config)
    
    # Load sensor data
    sensor_data = load_sensor_data()
    
    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']
    
    # Results storage
    results = []
    
    # Initial state
    ego_speed = 0.0
    
    # Run simulation
    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']
        
        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )
        
        # Calculate TTC
        if distance is not None and lead_speed is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0.01:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None
        
        # Store result (before updating speed)
        result = {
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)
        
        # Update speed for next iteration
        if i < len(sensor_data) - 1:
            ego_speed = ego_speed + accel_cmd * dt
            # Clamp to reasonable limits
            ego_speed = max(0, ego_speed)
    
    return results

def save_results(results, output_file='simulation_results.csv'):
    """Save simulation results to CSV."""
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 
                      'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            row = {
                'time': result['time'],
                'ego_speed': result['ego_speed'],
                'acceleration_cmd': result['acceleration_cmd'],
                'mode': result['mode'],
                'distance_error': result['distance_error'] if result['distance_error'] is not None else '',
                'distance': result['distance'] if result['distance'] is not None else '',
                'ttc': result['ttc'] if result['ttc'] is not None else ''
            }
            writer.writerow(row)

def calculate_metrics(results):
    """Calculate performance metrics from simulation results."""
    metrics = {}
    
    # Find cruise phase (no lead vehicle)
    cruise_results = [r for r in results if r['mode'] == 'cruise']
    if cruise_results:
        cruise_speeds = [r['ego_speed'] for r in cruise_results]
        # Rise time: time to reach 95% of set speed (30 m/s)
        target = 30 * 0.95
        rise_time = None
        for r in cruise_results:
            if r['ego_speed'] >= target:
                rise_time = r['time']
                break
        metrics['speed_rise_time'] = rise_time
        
        # Steady-state error in cruise (last 10 seconds of cruise)
        if cruise_results[-1]['time'] > 10:
            late_cruise = [r for r in cruise_results if r['time'] > cruise_results[-1]['time'] - 10]
            if late_cruise:
                avg_speed = sum(r['ego_speed'] for r in late_cruise) / len(late_cruise)
                metrics['speed_steady_state_error'] = abs(30 - avg_speed)
            else:
                metrics['speed_steady_state_error'] = abs(30 - cruise_speeds[-1])
        else:
            metrics['speed_steady_state_error'] = abs(30 - cruise_speeds[-1])
        
        # Max overshoot
        max_speed = max(cruise_speeds)
        overshoot = max(0, (max_speed - 30) / 30 * 100)
        metrics['speed_overshoot_percent'] = overshoot
    
    # Follow phase metrics
    follow_results = [r for r in results if r['mode'] == 'follow' and r['distance_error'] is not None]
    if follow_results:
        distance_errors = [r['distance_error'] for r in follow_results]
        metrics['distance_steady_state_error'] = abs(sum(distance_errors[-100:]) / min(100, len(distance_errors)))
        
        distances = [r['distance'] for r in follow_results if r['distance'] is not None]
        if distances:
            metrics['min_distance'] = min(distances)
    
    # Emergency events
    emergency_results = [r for r in results if r['mode'] == 'emergency']
    metrics['emergency_events'] = len(emergency_results)
    
    return metrics

if __name__ == '__main__':
    # Load configuration
    config = load_config()
    
    # Load tuning results if available
    tuning_results = load_tuning_results()
    
    # Run simulation
    results = run_simulation(config, tuning_results)
    
    # Save results
    save_results(results)
    
    # Calculate and print metrics
    metrics = calculate_metrics(results)
    print("Simulation complete. Results saved to simulation_results.csv")
    print("\nPerformance Metrics:")
    for key, value in metrics.items():
        if value is not None:
            print(f"  {key}: {value:.2f}")
