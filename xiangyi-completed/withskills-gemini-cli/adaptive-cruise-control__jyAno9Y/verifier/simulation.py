import yaml
import pandas as pd
import math
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load parameters
    with open('vehicle_params.yaml', 'r') as f:
        vehicle_params = yaml.safe_load(f)

    # Load tuning results
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning_results = yaml.safe_load(f)
            # Update params with tuned values
            vehicle_params['pid_speed'] = tuning_results['pid_speed']
            vehicle_params['pid_distance'] = tuning_results['pid_distance']
    except FileNotFoundError:
        print("Warning: tuning_results.yaml not found. Using defaults.")

    # Initialize ACC
    acc = AdaptiveCruiseControl(vehicle_params)

    # Load sensor data
    df = pd.read_csv('sensor_data.csv')
    
    # Simulation loop
    results = []
    
    # Initial state
    ego_speed = 0.0
    dt = vehicle_params['simulation']['dt']
    
    for index, row in df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        distance = row['distance']
        
        # Handle NaN/None
        if pd.isna(lead_speed): lead_speed = None
        if pd.isna(distance): distance = None
        
        # Compute ACC output
        acc_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, distance, dt)
        
        # Update vehicle physics
        # v_new = v_old + a * dt
        ego_speed += acc_cmd * dt
        ego_speed = max(0.0, ego_speed) # No reverse
        
        # Calculate TTC for logging
        ttc = None
        if lead_speed is not None and distance is not None:
             rel_speed = ego_speed - lead_speed
             if rel_speed > 0:
                 ttc = distance / rel_speed
        
        results.append({
            'time': time,
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(acc_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_err, 2) if dist_err is not None else None,
            'distance': round(distance, 2) if distance is not None else None,
            'ttc': round(ttc, 2) if ttc is not None else None
        })
        
    # Save results
    results_df = pd.DataFrame(results)
    # Ensure column order
    cols = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    results_df = results_df[cols]
    results_df.to_csv('simulation_results.csv', index=False)
    print("Simulation complete. Results saved to simulation_results.csv")

if __name__ == "__main__":
    run_simulation()
