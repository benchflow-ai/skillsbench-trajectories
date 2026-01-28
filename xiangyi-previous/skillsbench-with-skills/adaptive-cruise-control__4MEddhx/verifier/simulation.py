import csv
import yaml
from acc_system import AdaptiveCruiseControl

def load_config(vehicle_params_file, tuning_results_file):
    """Load configuration from YAML files."""
    with open(vehicle_params_file, 'r') as f:
        vehicle_config = yaml.safe_load(f)
    
    with open(tuning_results_file, 'r') as f:
        tuning_config = yaml.safe_load(f)
    
    # Merge tuning results into vehicle config
    vehicle_config['pid_speed'] = tuning_config['pid_speed']
    vehicle_config['pid_distance'] = tuning_config['pid_distance']
    
    return vehicle_config

def load_sensor_data(sensor_file):
    """Load sensor data from CSV."""
    data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_val = float(row['time'])
            ego_speed = float(row['ego_speed'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'].strip() else None
            distance = float(row['distance']) if row['distance'].strip() else None
            data.append({
                'time': time_val,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data

def simulate_acc(config, sensor_data):
    """Run ACC simulation."""
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    results = []
    
    current_speed = 0.0
    
    for i, sensor_row in enumerate(sensor_data):
        time_val = sensor_row['time']
        lead_speed = sensor_row['lead_speed']
        distance = sensor_row['distance']
        
        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(
            current_speed, lead_speed, distance, dt
        )
        
        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            speed_diff = current_speed - lead_speed
            if speed_diff > 0.01:
                ttc = distance / speed_diff
            else:
                ttc = None
        else:
            ttc = None
        
        # Update speed based on acceleration
        current_speed += accel_cmd * dt
        
        # Clamp speed to non-negative
        current_speed = max(0.0, current_speed)
        
        # Store result
        result = {
            'time': time_val,
            'ego_speed': current_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)
    
    return results

def save_results(results, output_file):
    """Save simulation results to CSV."""
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 
                      'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            row = {
                'time': f"{result['time']:.1f}",
                'ego_speed': f"{result['ego_speed']:.1f}",
                'acceleration_cmd': f"{result['acceleration_cmd']:.1f}",
                'mode': result['mode'],
                'distance_error': f"{result['distance_error']:.2f}" if result['distance_error'] is not None else '',
                'distance': f"{result['distance']:.2f}" if result['distance'] is not None else '',
                'ttc': f"{result['ttc']:.2f}" if result['ttc'] is not None else ''
            }
            writer.writerow(row)

if __name__ == '__main__':
    # Load configuration
    config = load_config('vehicle_params.yaml', 'tuning_results.yaml')
    
    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')
    
    # Run simulation
    print(f"Running ACC simulation for {len(sensor_data)} timesteps...")
    results = simulate_acc(config, sensor_data)
    
    # Save results
    save_results(results, 'simulation_results.csv')
    print(f"Simulation complete. Results saved to simulation_results.csv")
    print(f"Total rows: {len(results)}")
