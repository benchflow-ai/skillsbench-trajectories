import csv
import yaml
from acc_system import AdaptiveCruiseControl

def evaluate(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d):
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    config['pid_speed'] = {'kp': kp_s, 'ki': ki_s, 'kd': kd_s}
    config['pid_distance'] = {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
    
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    ego_speed = 0.0
    sim_dist = None
    
    times = []
    speeds = []
    distances = []
    dist_errors = []
    modes = []
    
    with open('sensor_data.csv', 'r') as f:
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
            
            times.append(t)
            speeds.append(ego_speed)
            dist_errors.append(dist_err)
            distances.append(sim_dist)
            modes.append(mode)
            
            ego_speed += acc_cmd * dt
            ego_speed = max(0.0, ego_speed)

    rise_time = next((t for t, v in zip(times, speeds) if v >= 27.0), None)
    max_speed = max(speeds)
    overshoot = (max_speed - 30.0) / 30.0 * 100 if max_speed > 30.0 else 0.0
    
    cruise_speeds = [v for v, m, t in zip(speeds, modes, times) if m == 'cruise' and t > 20 and t < 30]
    ss_error_speed = sum(abs(v - 30.0) for v in cruise_speeds) / len(cruise_speeds) if cruise_speeds else 0.0

    # For distance SS error, look at a period where lead is slower than set speed and stable
    # Lead is detected from 30 to 127.
    # Between 80 and 100 it might be stable.
    follow_errs = [abs(e) for e, m, t in zip(dist_errors, modes, times) if m == 'follow' and t > 80 and t < 100 and e is not None]
    ss_error_dist = sum(follow_errs) / len(follow_errs) if follow_errs else 999.0
    
    min_dist = min([d for d in distances if d is not None]) if any(d is not None for d in distances) else 999.0

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'ss_error_speed': ss_error_speed,
        'ss_error_dist': ss_error_dist,
        'min_dist': min_dist
    }

if __name__ == "__main__":
    p = (0.5, 0.0, 0.1, 0.5, 0.0, 0.1)
    res = evaluate(*p)
    print(f"Params {p}: Rise={res['rise_time']}, OS={res['overshoot']:.2f}, SS_V={res['ss_error_speed']:.2f}, SS_D={res['ss_error_dist']:.2f}, Min_D={res['min_dist']:.2f}")