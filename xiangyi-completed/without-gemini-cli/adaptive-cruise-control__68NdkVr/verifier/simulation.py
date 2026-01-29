import csv
import yaml
from acc_system import AdaptiveCruiseControl

def run_simulation(params_file, tuning_file, sensor_file, output_file):
    with open(params_file, 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        with open(tuning_file, 'r') as f:
            tuning = yaml.safe_load(f)
            config['pid_speed'].update(tuning['pid_speed'])
            config['pid_distance'].update(tuning['pid_distance'])
    except FileNotFoundError:
        pass

    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    ego_speed = 0.0
    sim_dist = None
    
    results = []
    
    with open(sensor_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = float(row['time'])
            ls = float(row['lead_speed']) if row['lead_speed'] else None
            dist_csv = float(row['distance']) if row['distance'] else None
            
            if ls is not None:
                if sim_dist is None:
                    sim_dist = dist_csv
                else:
                    sim_dist += (ls - ego_speed) * dt
            else:
                sim_dist = None
            
            acc_cmd, mode, dist_err, ttc = acc.compute(ego_speed, ls, sim_dist, dt)
            
            results.append({
                'time': t,
                'ego_speed': ego_speed,
                'acceleration_cmd': acc_cmd,
                'mode': mode,
                'distance_error': dist_err,
                'distance': sim_dist,
                'ttc': ttc
            })
            
            ego_speed += acc_cmd * dt
            ego_speed = max(0.0, ego_speed)

    fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            row_to_write = {
                'time': f"{res['time']:.1f}",
                'ego_speed': f"{res['ego_speed']:.1f}",
                'acceleration_cmd': f"{res['acceleration_cmd']:.1f}",
                'mode': res['mode'],
                'distance_error': f"{res['distance_error']:.2f}" if res['distance_error'] is not None else '',
                'distance': f"{res['distance']:.2f}" if res['distance'] is not None else '',
                'ttc': f"{res['ttc']:.2f}" if res['ttc'] != float('inf') else ''
            }
            writer.writerow(row_to_write)

if __name__ == "__main__":
    run_simulation('vehicle_params.yaml', 'tuning_results.yaml', 'sensor_data.csv', 'simulation_results.csv')