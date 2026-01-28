import yaml
import csv
from acc_system import AdaptiveCruiseControl

def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def load_sensor_data(sensor_file):
    """Load sensor data from CSV file."""
    data = []
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert empty strings to None for lead_speed and distance
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            distance = float(row['distance']) if row['distance'] else None
            data.append({
                'time': float(row['time']),
                'ego_speed': float(row['ego_speed']),
                'lead_speed': lead_speed,
                'distance': distance
            })
    return data

def run_simulation():
    """Run ACC simulation and save results."""
    # Load configuration
    config = load_config('vehicle_params.yaml')
    
    # Load tuned PID parameters
    tuned_params = load_config('tuning_results.yaml')
    
    # Load sensor data
    sensor_data = load_sensor_data('sensor_data.csv')
    
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_controllers(tuned_params['pid_speed'], tuned_params['pid_distance'])
    
    # Simulation parameters
    dt = config['simulation']['dt']
    
    # Initialize state
    ego_speed = 0.0
    results = []
    
    # Run simulation
    for i, sensor_row in enumerate(sensor_data):
        time = sensor_row['time']
        lead_speed = sensor_row['lead_speed']
        distance = sensor_row['distance']
        
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
        if i < len(sensor_data) - 1:
            ego_speed += acceleration_cmd * dt
            ego_speed = max(0.0, ego_speed)  # Speed cannot be negative
    
    # Write results to CSV
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in results:
            # Format values appropriately
            output_row = {
                'time': f"{row['time']:.1f}",
                'ego_speed': f"{row['ego_speed']:.1f}",
                'acceleration_cmd': f"{row['acceleration_cmd']:.1f}",
                'mode': row['mode'],
                'distance_error': f"{row['distance_error']:.1f}" if row['distance_error'] is not None else '',
                'distance': f"{row['distance']:.1f}" if row['distance'] is not None else '',
                'ttc': f"{row['ttc']:.1f}" if row['ttc'] is not None else ''
            }
            writer.writerow(output_row)
    
    print("Simulation complete. Results saved to simulation_results.csv")
    return results

if __name__ == '__main__':
    run_simulation()
