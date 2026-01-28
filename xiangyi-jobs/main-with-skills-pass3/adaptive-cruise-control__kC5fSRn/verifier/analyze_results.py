import csv
import numpy as np

def analyze_simulation_results(results_file):
    """Analyze simulation results and calculate performance metrics."""
    
    # Load results
    times = []
    speeds = []
    modes = []
    distances = []
    distance_errors = []
    
    with open(results_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(float(row['time']))
            speeds.append(float(row['ego_speed']))
            modes.append(row['mode'])
            
            if row['distance']:
                distances.append(float(row['distance']))
            else:
                distances.append(None)
            
            if row['distance_error']:
                distance_errors.append(float(row['distance_error']))
            else:
                distance_errors.append(None)
    
    times = np.array(times)
    speeds = np.array(speeds)
    
    # Speed control metrics (cruise phase before lead vehicle)
    set_speed = 30.0
    cruise_indices = [i for i, mode in enumerate(modes) if mode == 'cruise']
    
    # Rise time: time to reach 90% of set_speed
    target_90 = 0.9 * set_speed
    rise_idx = np.where(speeds >= target_90)[0]
    if len(rise_idx) > 0:
        rise_time = times[rise_idx[0]]
    else:
        rise_time = None
    
    # Overshoot: maximum speed above set_speed during cruise
    if cruise_indices:
        cruise_speeds = speeds[cruise_indices]
        max_speed = np.max(cruise_speeds)
        overshoot = max(0, max_speed - set_speed)
        overshoot_pct = (overshoot / set_speed) * 100
    else:
        overshoot_pct = 0
    
    # Steady-state error for speed (last 5 seconds of cruise mode)
    cruise_times = times[cruise_indices]
    if len(cruise_times) > 0:
        last_cruise_time = cruise_times[-1]
        steady_state_start = max(0, last_cruise_time - 5.0)
        steady_indices = [i for i in cruise_indices 
                         if times[i] >= steady_state_start]
        if steady_indices:
            steady_speeds = speeds[steady_indices]
            speed_ss_error = np.abs(np.mean(steady_speeds) - set_speed)
        else:
            speed_ss_error = None
    else:
        speed_ss_error = None
    
    # Distance control metrics (follow phase)
    follow_indices = [i for i, mode in enumerate(modes) if mode in ['follow', 'emergency']]
    
    if follow_indices:
        follow_distances = [distances[i] for i in follow_indices if distances[i] is not None]
        follow_errors = [distance_errors[i] for i in follow_indices if distance_errors[i] is not None]
        
        # Minimum distance
        min_distance = min(follow_distances) if follow_distances else None
        
        # Steady-state distance error (last 20 seconds of simulation)
        steady_follow_indices = [i for i in follow_indices if times[i] >= 130.0]
        if steady_follow_indices:
            steady_errors = [distance_errors[i] for i in steady_follow_indices 
                           if distance_errors[i] is not None]
            if steady_errors:
                distance_ss_error = np.abs(np.mean(steady_errors))
            else:
                distance_ss_error = None
        else:
            distance_ss_error = None
    else:
        min_distance = None
        distance_ss_error = None
    
    # Print results
    print("\n=== Performance Metrics ===")
    print(f"\nSpeed Control (Cruise Mode):")
    print(f"  Rise Time (to 90%): {rise_time:.2f}s" if rise_time else "  Rise Time: N/A")
    print(f"  Overshoot: {overshoot_pct:.2f}%")
    print(f"  Steady-State Error: {speed_ss_error:.3f} m/s" if speed_ss_error is not None else "  Steady-State Error: N/A")
    
    print(f"\nDistance Control (Follow Mode):")
    print(f"  Minimum Distance: {min_distance:.2f}m" if min_distance else "  Minimum Distance: N/A")
    print(f"  Steady-State Error: {distance_ss_error:.3f}m" if distance_ss_error is not None else "  Steady-State Error: N/A")
    
    print(f"\n=== Requirements Check ===")
    print(f"  Rise Time < 10s: {'PASS' if rise_time and rise_time < 10 else 'FAIL'}")
    print(f"  Overshoot < 5%: {'PASS' if overshoot_pct < 5 else 'FAIL'}")
    print(f"  Speed SS Error < 0.5 m/s: {'PASS' if speed_ss_error is not None and speed_ss_error < 0.5 else 'FAIL'}")
    print(f"  Distance SS Error < 2m: {'PASS' if distance_ss_error is not None and distance_ss_error < 2 else 'FAIL'}")
    print(f"  Minimum Distance > 5m: {'PASS' if min_distance and min_distance > 5 else 'FAIL'}")
    
    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance
    }

if __name__ == '__main__':
    metrics = analyze_simulation_results('simulation_results.csv')
