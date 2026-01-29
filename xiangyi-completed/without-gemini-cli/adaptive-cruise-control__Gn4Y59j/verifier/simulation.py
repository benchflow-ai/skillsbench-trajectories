import csv
import yaml
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load parameters
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load tuning results
    try:
        with open('tuning_results.yaml', 'r') as f:
            tuning = yaml.safe_load(f)
            config['pid_speed'].update(tuning['pid_speed'])
            config['pid_distance'].update(tuning['pid_distance'])
    except FileNotFoundError:
        pass

    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    results = []
    ego_speed = 0.0 # Initial speed
    sim_distance = None
    prev_lead_speed = None
    
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            lead_speed = float(row['lead_speed']) if row['lead_speed'] else None
            csv_distance = float(row['distance']) if row['distance'] else None
            
            if lead_speed is not None:
                if sim_distance is None:
                    # Initialize distance when lead vehicle first appears
                    sim_distance = csv_distance
                else:
                    # Update simulated distance based on previous relative speed
                    # d_new = d_old + (v_lead_old - v_ego_old) * dt
                    # But we use the lead_speed from current row as v_lead_old? 
                    # Actually better to use prev_lead_speed if available
                    v_lead_eff = prev_lead_speed if prev_lead_speed is not None else lead_speed
                    sim_distance += (v_lead_eff - ego_speed) * dt
                
                prev_lead_speed = lead_speed
            else:
                sim_distance = None
                prev_lead_speed = None

            accel_cmd, mode, dist_err = acc.compute(ego_speed, lead_speed, sim_distance, dt)
            
            # Calculate TTC for results
            ttc = None
            if lead_speed is not None and sim_distance is not None:
                rel_speed = ego_speed - lead_speed
                if rel_speed > 0:
                    ttc = sim_distance / rel_speed
            
            results.append({
                'time': time,
                'ego_speed': ego_speed,
                'acceleration_cmd': accel_cmd,
                'mode': mode,
                'distance_error': dist_err,
                'distance': sim_distance,
                'ttc': ttc
            })
            
            # Update ego speed for next step
            ego_speed += accel_cmd * dt
            ego_speed = max(0, ego_speed)

    # Save results
    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open('simulation_results.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            row_to_write = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}
            row_to_write = {k: ('' if v is None else v) for k, v in row_to_write.items()}
            writer.writerow(row_to_write)

if __name__ == "__main__":
    run_simulation()