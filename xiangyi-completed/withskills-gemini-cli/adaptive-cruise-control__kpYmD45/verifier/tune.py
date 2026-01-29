import pandas as pd
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl

def evaluate(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d):
    config = {
        'vehicle': {'mass': 1500, 'max_acceleration': 3.0, 'max_deceleration': -8.0, 'drag_coefficient': 0.3},
        'acc_settings': {'set_speed': 30.0, 'time_headway': 1.5, 'min_distance': 10.0, 'emergency_ttc_threshold': 3.0},
        'pid_speed': {'kp': kp_s, 'ki': ki_s, 'kd': kd_s},
        'pid_distance': {'kp': kp_d, 'ki': ki_d, 'kd': kd_d},
        'simulation': {'dt': 0.1}
    }
    
    sensor_df = pd.read_csv('sensor_data.csv')
    dt = 0.1
    acc = AdaptiveCruiseControl(config)
    
    ego_speed = 0.0
    times = []
    speeds = []
    distances = []
    dist_errors = []
    
    for i, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed']
        my_distance = row['distance']
        
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, my_distance, dt)
        
        times.append(time)
        speeds.append(ego_speed)
        if my_distance is not None and not pd.isna(my_distance):
            distances.append(my_distance)
            if distance_error is not None:
                dist_errors.append(distance_error)
            
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)
        
    # Metrics
    t10 = t90 = None
    for t, v in zip(times, speeds):
        if t < 30.0:
            if t10 is None and v >= 3.0: t10 = t
            if t90 is None and v >= 27.0: t90 = t
    rise_time = (t90 - t10) if (t10 is not None and t90 is not None) else 999
    
    cruise_speeds = [v for t, v in zip(times, speeds) if 10.0 < t < 30.0]
    max_speed = max(cruise_speeds) if cruise_speeds else 0
    overshoot = (max_speed - 30.0) / 30.0 * 100 if max_speed > 30.0 else 0
    
    ss_speed_err = abs(30.0 - np.mean(speeds[250:300]))
    
    valid_dist_errors = [e for e in dist_errors if e is not None]
    ss_dist_err = np.mean([abs(e) for e in valid_dist_errors[-100:]]) if valid_dist_errors else 999
    
    min_dist = min(distances) if distances else 999
    
    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'ss_speed_err': ss_speed_err,
        'ss_dist_err': ss_dist_err,
        'min_dist': min_dist
    }

# Search
best_params = None
best_score = float('inf')

for kp_s in [0.5, 0.8, 1.2]:
    for ki_s in [0.01, 0.02]:
        for kd_s in [0.1, 0.5]:
            for kp_d in [0.5, 1.0, 1.5]:
                for ki_d in [0.01, 0.05]:
                    for kd_d in [0.5, 1.0]:
                        res = evaluate(kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)
                        
                        if (res['rise_time'] < 10 and res['overshoot'] < 10 and 
                            res['ss_speed_err'] < 1.0 and res['ss_dist_err'] < 5.0 and 
                            res['min_dist'] > 1.0):
                            
                            score = res['ss_dist_err'] + res['overshoot']
                            if score < best_score:
                                best_score = score
                                best_params = (kp_s, ki_s, kd_s, kp_d, ki_d, kd_d)

if best_params:
    kp_s, ki_s, kd_s, kp_d, ki_d, kd_d = best_params
else:
    kp_s, ki_s, kd_s, kp_d, ki_d, kd_d = 0.8, 0.01, 0.5, 1.0, 0.01, 0.5

tuning_results = {
    'pid_speed': {'kp': float(kp_s), 'ki': float(ki_s), 'kd': float(kd_s)},
    'pid_distance': {'kp': float(kp_d), 'ki': float(ki_d), 'kd': float(kd_d)}
}

with open('tuning_results.yaml', 'w') as f:
    yaml.dump(tuning_results, f, default_flow_style=False)

print(f"Tuning complete. Params: {tuning_results}")
