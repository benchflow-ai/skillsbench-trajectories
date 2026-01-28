import yaml
import pandas as pd
import itertools
from acc_system import AdaptiveCruiseControl

def rise_time(times, values, target):
    """Calculate rise time (10% to 90% of target)."""
    t10 = t90 = None
    for t, v in zip(times, values):
        if t10 is None and v >= 0.1 * target:
            t10 = t
        if t90 is None and v >= 0.9 * target:
            t90 = t
            break
    if t10 is not None and t90 is not None:
        return t90 - t10
    return None

def overshoot_percent(values, target):
    """Calculate overshoot percentage."""
    max_val = max(values)
    if max_val <= target:
        return 0.0
    return ((max_val - target) / target) * 100

def steady_state_error(values, target, final_fraction=0.1):
    """Calculate steady-state error."""
    n = len(values)
    start = int(n * (1 - final_fraction))
    if start >= n:
        start = max(0, n - 1)
    final_avg = sum(values[start:]) / len(values[start:])
    return abs(target - final_avg)

def run_simulation_with_gains(config, pid_speed_gains, pid_distance_gains):
    """Run simulation with specific PID gains."""
    config_copy = dict(config)
    config_copy['pid_speed'] = pid_speed_gains
    config_copy['pid_distance'] = pid_distance_gains
    
    acc = AdaptiveCruiseControl(config_copy)
    dt = config['simulation']['dt']
    sensor_df = pd.read_csv('sensor_data.csv')
    
    ego_speed = 0.0
    results = []
    
    for idx, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None
        
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
        new_speed = ego_speed + accel_cmd * dt
        new_speed = max(0.0, new_speed)
        
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
        
        result = {
            'time': time,
            'ego_speed': new_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)
        ego_speed = new_speed
    
    return results

def evaluate_results(results, config):
    """Evaluate simulation results against targets."""
    set_speed = config['acc_settings']['set_speed']
    dt = config['simulation']['dt']
    
    speeds = [r['ego_speed'] for r in results]
    times = [r['time'] for r in results]
    
    # Speed metrics
    rt = rise_time(times, speeds, set_speed)
    overshoot = overshoot_percent(speeds, set_speed)
    sse = steady_state_error(speeds, set_speed)
    
    # Distance metrics
    follow_results = [r for r in results if r['mode'] == 'follow']
    min_distance = float('inf')
    distance_sse = 0
    
    if follow_results:
        distances = [r['distance'] for r in follow_results]
        min_distance = min(distances)
        distance_errors = [r['distance_error'] for r in follow_results if r['distance_error'] is not None]
        if distance_errors:
            distance_sse = abs(distance_errors[-1])
    
    # Safety metric
    ttc_values = [r['ttc'] for r in results if r['ttc'] is not None]
    min_ttc = min(ttc_values) if ttc_values else float('inf')
    
    # Calculate fitness score (lower is better)
    score = 0
    penalties = {}
    
    # Safety is top priority
    if min_ttc < 3.0:
        score += (3.0 - min_ttc) * 1000  # Heavy penalty
        penalties['min_ttc'] = f'{min_ttc:.2f}'
    
    if min_distance < 5.0:
        score += (5.0 - min_distance) * 100
        penalties['min_distance'] = f'{min_distance:.2f}'
    
    # Distance control
    if distance_sse > 2.0:
        score += (distance_sse - 2.0) * 50
        penalties['distance_sse'] = f'{distance_sse:.3f}'
    
    # Speed targets
    if rt is None or rt > 10.0:
        score += 100
        penalties['rise_time'] = 'FAIL'
    elif rt > 8.0:
        score += (rt - 8.0) * 5
    
    if overshoot > 5.0:
        score += (overshoot - 5.0) * 10
        penalties['overshoot'] = f'{overshoot:.1f}%'
    
    if sse > 0.5:
        score += (sse - 0.5) * 5
        penalties['speed_sse'] = f'{sse:.3f}'
    
    return {
        'score': score,
        'rise_time': rt,
        'overshoot': overshoot,
        'speed_sse': sse,
        'distance_sse': distance_sse,
        'min_distance': min_distance,
        'min_ttc': min_ttc,
        'penalties': penalties
    }

def main():
    """Tune PID parameters with focus on safety and distance control."""
    print("Loading configuration...")
    config = yaml.safe_load(open('vehicle_params.yaml'))
    
    # Broader ranges for independent tuning
    # Speed control: focus on moderate Kp with good damping
    kp_speed_values = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    ki_speed_values = [0.05, 0.1, 0.2, 0.3]
    kd_speed_values = [0.5, 1.0, 1.5, 2.0, 2.5]
    
    # Distance control: needs stronger response
    kp_dist_values = [2.0, 3.0, 4.0, 5.0, 6.0]
    ki_dist_values = [0.1, 0.2, 0.3, 0.5]
    kd_dist_values = [1.0, 1.5, 2.0, 2.5, 3.0]
    
    best_score = float('inf')
    best_gains = None
    best_metrics = None
    
    total = len(kp_speed_values) * len(ki_speed_values) * len(kd_speed_values) * \
            len(kp_dist_values) * len(ki_dist_values) * len(kd_dist_values)
    print(f"Testing {total} combinations...")
    
    tested = 0
    for kp_s, ki_s, kd_s, kp_d, ki_d, kd_d in itertools.product(
        kp_speed_values, ki_speed_values, kd_speed_values,
        kp_dist_values, ki_dist_values, kd_dist_values
    ):
        pid_speed_gains = {'kp': kp_s, 'ki': ki_s, 'kd': kd_s}
        pid_distance_gains = {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}
        
        try:
            results = run_simulation_with_gains(config, pid_speed_gains, pid_distance_gains)
            metrics = evaluate_results(results, config)
            
            if metrics['score'] < best_score:
                best_score = metrics['score']
                best_gains = (pid_speed_gains, pid_distance_gains)
                best_metrics = metrics
                print(f"New best: score={best_score:.1f}, TTC={metrics['min_ttc']:.2f}s, dist_sse={metrics['distance_sse']:.2f}m")
            
            tested += 1
            if tested % 500 == 0:
                print(f"  Tested {tested}/{total}...")
        except Exception as e:
            pass
    
    print(f"\n=== Best Configuration ===")
    print(f"Speed gains: {best_gains[0]}")
    print(f"Distance gains: {best_gains[1]}")
    print(f"\nMetrics:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {best_metrics['overshoot']:.2f}% (target: <5%)")
    print(f"  Speed SSE: {best_metrics['speed_sse']:.3f} m/s (target: <0.5)")
    print(f"  Distance SSE: {best_metrics['distance_sse']:.3f} m (target: <2)")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (target: >5)")
    print(f"  Min TTC: {best_metrics['min_ttc']:.2f}s (target: >3)")
    if best_metrics['penalties']:
        print(f"\nRemaining issues: {best_metrics['penalties']}")
    
    # Save tuned gains
    tuning_results = {
        'pid_speed': best_gains[0],
        'pid_distance': best_gains[1],
        'metrics': {
            'rise_time': best_metrics['rise_time'],
            'overshoot': best_metrics['overshoot'],
            'speed_sse': best_metrics['speed_sse'],
            'distance_sse': best_metrics['distance_sse'],
            'min_distance': best_metrics['min_distance'],
            'min_ttc': best_metrics['min_ttc']
        }
    }
    
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False, sort_keys=False)
    
    print("\nTuned gains saved to tuning_results.yaml")

if __name__ == '__main__':
    main()
