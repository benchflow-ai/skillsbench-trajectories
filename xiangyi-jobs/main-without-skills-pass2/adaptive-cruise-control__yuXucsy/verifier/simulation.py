import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl

def run_simulation():
    """Run ACC simulation and generate results."""
    
    # Load configuration
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuned PID parameters
    with open('tuning_results.yaml', 'r') as f:
        pid_params = yaml.safe_load(f)
    
    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')
    
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_controllers(
        pid_params['pid_speed'],
        pid_params['pid_distance']
    )
    
    # Simulation parameters
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']
    
    # Initialize results storage
    results = []
    
    # Initial state
    ego_speed = 0.0
    
    # Run simulation
    for idx, row in sensor_data.iterrows():
        time = row['time']
        
        # Get lead vehicle data (may be NaN)
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None
        
        # Compute ACC control
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
        
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
        result_row = {
            'time': time,
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(distance_error, 2) if distance_error is not None else '',
            'distance': round(distance, 2) if distance is not None else '',
            'ttc': round(ttc, 2) if ttc is not None else ''
        }
        results.append(result_row)
        
        # Update ego speed for next iteration
        if idx < len(sensor_data) - 1:
            ego_speed = ego_speed + accel_cmd * dt
            ego_speed = max(0, ego_speed)  # Speed cannot be negative
    
    # Save results to CSV
    results_df = pd.DataFrame(results)
    results_df.to_csv('simulation_results.csv', index=False)
    
    print(f"Simulation complete. Generated {len(results)} data points.")
    
    # Calculate and print performance metrics
    calculate_metrics(results_df, sensor_data)

def calculate_metrics(results_df, sensor_data):
    """Calculate and print performance metrics."""
    
    # Speed metrics (cruise mode)
    cruise_data = results_df[results_df['mode'] == 'cruise'].copy()
    
    if len(cruise_data) > 0:
        # Find when speed reaches 90% of set speed (27 m/s)
        target_90 = 27.0
        rise_time_idx = cruise_data[cruise_data['ego_speed'] >= target_90].first_valid_index()
        if rise_time_idx is not None:
            rise_time = cruise_data.loc[rise_time_idx, 'time']
            print(f"Speed rise time (0 to 90% of 30 m/s): {rise_time:.1f}s")
        
        # Maximum speed (overshoot)
        max_speed = cruise_data['ego_speed'].max()
        overshoot = ((max_speed - 30.0) / 30.0) * 100
        print(f"Maximum speed: {max_speed:.2f} m/s (overshoot: {overshoot:.2f}%)")
        
        # Steady-state error (last 10s of cruise mode)
        steady_state_data = cruise_data[cruise_data['time'] >= cruise_data['time'].max() - 10]
        if len(steady_state_data) > 0:
            ss_error = abs(30.0 - steady_state_data['ego_speed'].mean())
            print(f"Speed steady-state error: {ss_error:.3f} m/s")
    
    # Distance metrics (follow mode)
    follow_data = results_df[results_df['mode'] == 'follow'].copy()
    
    if len(follow_data) > 0:
        # Convert distance_error to numeric, handling empty strings
        follow_data['distance_error_num'] = pd.to_numeric(follow_data['distance_error'], errors='coerce')
        follow_data['distance_num'] = pd.to_numeric(follow_data['distance'], errors='coerce')
        
        # Distance steady-state error
        ss_dist_error = follow_data['distance_error_num'].abs().mean()
        print(f"Distance steady-state error: {ss_dist_error:.3f} m")
        
        # Minimum distance
        min_dist = follow_data['distance_num'].min()
        print(f"Minimum distance: {min_dist:.2f} m")
    
    # Emergency braking events
    emergency_data = results_df[results_df['mode'] == 'emergency']
    print(f"Emergency braking events: {len(emergency_data)} timesteps")

if __name__ == '__main__':
    run_simulation()
