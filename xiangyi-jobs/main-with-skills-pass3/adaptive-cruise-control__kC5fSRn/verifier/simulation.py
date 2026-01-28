import yaml
import csv
from acc_system import AdaptiveCruiseControl

def load_config(config_file):
    """Load YAML configuration file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def load_sensor_data(sensor_file):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert to appropriate types, handle empty values
            time = float(row['time'])
            ego_speed = float(row['ego_speed']) if row['ego_speed'] else 0.0
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': time,
                'ego_speed': ego_speed,
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data

def run_simulation():
    """Run ACC simulation and generate results."""
    # Load configuration
    config = load_config('vehicle_params.yaml')
    tuning = load_config('tuning_results.yaml')
    sensor_data = load_sensor_data('sensor_data.csv')
    
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_controllers(tuning['pid_speed'], tuning['pid_distance'])
    
    # Simulation parameters
    dt = config['simulation']['dt']
    max_acceleration = config['vehicle']['max_acceleration']
    max_deceleration = config['vehicle']['max_deceleration']
    
    # Initialize state
    ego_speed = 0.0
    results = []
    
    # Run simulation
    for i, sensor in enumerate(sensor_data):
        time = sensor['time']
        lead_speed = sensor['lead_speed']
        distance = sensor['distance']
        
        # Compute ACC command
        acceleration_cmd, mode, distance_error = acc.compute(
            ego_speed, lead_speed, distance, dt
        )
        
        # Calculate TTC if lead vehicle present
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None
        
        # Store results
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': acceleration_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        })
        
        # Update ego speed for next iteration (if not last iteration)
        if i < len(sensor_data) - 1:
            ego_speed += acceleration_cmd * dt
            ego_speed = max(0.0, ego_speed)  # Ensure non-negative speed
    
    return results

def save_results(results, output_file):
    """Save simulation results to CSV file."""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(['time', 'ego_speed', 'acceleration_cmd', 'mode', 
                        'distance_error', 'distance', 'ttc'])
        
        # Write data
        for row in results:
            writer.writerow([
                f"{row['time']:.1f}",
                f"{row['ego_speed']:.1f}" if row['ego_speed'] is not None else '',
                f"{row['acceleration_cmd']:.1f}" if row['acceleration_cmd'] is not None else '',
                row['mode'],
                f"{row['distance_error']:.2f}" if row['distance_error'] is not None else '',
                f"{row['distance']:.2f}" if row['distance'] is not None else '',
                f"{row['ttc']:.2f}" if row['ttc'] is not None else ''
            ])

if __name__ == '__main__':
    print("Running ACC simulation...")
    results = run_simulation()
    save_results(results, 'simulation_results.csv')
    print(f"Simulation complete. Generated {len(results)} data points.")
