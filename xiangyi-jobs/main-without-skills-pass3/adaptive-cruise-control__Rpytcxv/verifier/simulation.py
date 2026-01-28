import yaml
import csv
import math
from acc_system import AdaptiveCruiseControl

def main():
    # Load configurations
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
        
    # Merge tuning into config
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']
    
    # Initialize ACC
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    # Read Sensor Data
    data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
             data.append({
                'time': float(row['time']),
                'ego_speed_csv': float(row['ego_speed']) if row['ego_speed'] else 0.0,
                'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                'distance': float(row['distance']) if row['distance'] else None
            })

    # Simulation Loop
    ego_speed = 0.0
    
    results = []
    
    for i, row in enumerate(data):
        t = row['time']
        
        # Get lead state directly from CSV (Replay Mode)
        lead_v = row['lead_speed']
        dist = row['distance']
            
        # Call ACC
        acc_cmd, mode, dist_err = acc.compute(ego_speed, lead_v, dist, dt)
        
        # Calculate TTC for logging based on SIMULATED ego speed and CSV data
        ttc = None
        if dist is not None and lead_v is not None:
            rel_v = ego_speed - lead_v
            if rel_v > 0.001:
                ttc = dist / rel_v
        
        # Log
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': acc_cmd,
            'mode': mode,
            'distance_error': dist_err,
            'distance': dist,
            'ttc': ttc
        })
        
        # Update Physics (Speed only, Position is irrelevant in Replay Mode)
        ego_speed += acc_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
    # Write Results to CSV
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc'])
        
        for r in results:
            # Format fields
            t_str = f"{r['time']:.1f}"
            v_str = f"{r['ego_speed']:.2f}" 
            a_str = f"{r['acceleration_cmd']:.2f}" 
            m_str = r['mode']
            
            de_str = f"{r['distance_error']:.2f}" if r['distance_error'] is not None else ""
            d_str = f"{r['distance']:.2f}" if r['distance'] is not None else ""
            ttc_str = f"{r['ttc']:.2f}" if r['ttc'] is not None else ""
            
            writer.writerow([t_str, v_str, a_str, m_str, de_str, d_str, ttc_str])

if __name__ == "__main__":
    main()
