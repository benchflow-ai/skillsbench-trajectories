import yaml
import csv
from acc_system import AdaptiveCruiseControl

def load_config():
    """Load configuration from YAML files."""
    # Load vehicle parameters and ACC settings
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuned PID gains from tuning_results.yaml
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning_results = yaml.safe_load(f)
        
        # Override PID parameters with tuned values
        config['pid_speed'] = tuning_results['pid_speed']
        config['pid_distance'] = tuning_results['pid_distance']
        print("Loaded tuned PID parameters from tuning_results.yaml")
    except FileNotFoundError:
        print("Warning: tuning_results.yaml not found, using default PID parameters")
    
    return config

def load_sensor_data():
    """Load sensor data from CSV file."""
    sensor_data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse data, handling empty values for lead_speed and distance
            data = {
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            }
            sensor_data.append(data)
    return sensor_data

def run_simulation():
    """Run ACC simulation."""
    # Load configuration
    config = load_config()
    dt = config['simulation']['dt']
    
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    
    # Load sensor data
    sensor_data = load_sensor_data()
    
    # Initialize simulation state
    ego_speed = 0.0  # Start from rest
    
    # Results storage
    results = []
    
    # Run simulation
    for data in sensor_data:
        time = data['time']
        lead_speed = data['lead_speed']
        distance = data['distance']
        
        # Compute ACC control
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
        
        # Update ego speed for next iteration
        ego_speed += acceleration_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Ensure non-negative speed
    
    return results

def save_results(results):
    """Save simulation results to CSV."""
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 
                     'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in results:
            # Format output - empty strings for None values
            output_row = {
                'time': f"{row['time']:.1f}",
                'ego_speed': f"{row['ego_speed']:.1f}",
                'acceleration_cmd': f"{row['acceleration_cmd']:.1f}",
                'mode': row['mode'],
                'distance_error': f"{row['distance_error']:.2f}" if row['distance_error'] is not None else '',
                'distance': f"{row['distance']:.2f}" if row['distance'] is not None else '',
                'ttc': f"{row['ttc']:.2f}" if row['ttc'] is not None else ''
            }
            writer.writerow(output_row)
    
    print(f"Saved {len(results)} rows to simulation_results.csv")

if __name__ == '__main__':
    print("Starting ACC simulation...")
    results = run_simulation()
    save_results(results)
    print("Simulation complete!")
