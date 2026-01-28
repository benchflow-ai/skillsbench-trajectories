import pandas as pd
import yaml
import math
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load configs
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
    
    # Load sensor data
    sensor_data = pd.read_csv('sensor_data.csv')
    
    # Initialize ACC
    acc = AdaptiveCruiseControl(config)
    acc.set_pid_params(tuning['pid_speed'], tuning['pid_distance'])
    
    dt = config['simulation']['dt']
    ego_speed = 0.0 # Initial speed ~0
    current_distance = None
    
    results = []
    
    for i in range(len(sensor_data)):
        row = sensor_data.iloc[i]
        time = row['time']
        lead_speed = row['lead_speed']
        csv_distance = row['distance']
        
        # Handle distance simulation
        if not math.isnan(csv_distance):
            if current_distance is None:
                # Lead vehicle just appeared
                current_distance = csv_distance
            else:
                # Update distance based on simulated ego speed and lead speed
                # Using average speed for better accuracy
                # But let's stick to simple Euler for consistency with speed update
                current_distance += (lead_speed - ego_speed) * dt
        else:
            current_distance = None

        accel_cmd, mode, dist_err, ttc = acc.compute(ego_speed, lead_speed, current_distance, dt)
        
        results.append({
            'time': round(time, 1),
            'ego_speed': round(ego_speed, 2),
            'acceleration_cmd': round(accel_cmd, 2),
            'mode': mode,
            'distance_error': round(dist_err, 2) if dist_err is not None else '',
            'distance': round(current_distance, 2) if current_distance is not None else '',
            'ttc': round(ttc, 2) if ttc != float('inf') else ''
        })
        
        # Update ego speed for next step
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)

    # Save results
    df_results = pd.DataFrame(results)
    df_results.to_csv('simulation_results.csv', index=False)
    print("Simulation complete. Results saved to simulation_results.csv")

if __name__ == "__main__":
    run_simulation()
