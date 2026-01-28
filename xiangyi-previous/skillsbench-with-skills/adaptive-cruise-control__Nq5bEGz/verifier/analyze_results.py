import csv
import numpy as np

def analyze_simulation():
    """Analyze simulation results and compute performance metrics."""
    
    with open('simulation_results.csv', 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    # Extract data
    times = [float(row['time']) for row in data]
    speeds = [float(row['ego_speed']) for row in data]
    modes = [row['mode'] for row in data]
    distances = [float(row['distance']) if row['distance'] else None for row in data]
    distance_errors = [float(row['distance_error']) if row['distance_error'] else None for row in data]
    
    # Speed control metrics (cruise phase)
    set_speed = 30.0
    target_90 = 0.9 * set_speed
    
    # Find rise time
    rise_time = None
    for i, speed in enumerate(speeds):
        if speed >= target_90:
            rise_time = times[i]
            break
    
    # Find overshoot in first 50 seconds
    cruise_idx = min(500, len(speeds))
    max_speed_cruise = max(speeds[:cruise_idx])
    overshoot = max(0, max_speed_cruise - set_speed)
    overshoot_pct = (overshoot / set_speed) * 100
    
    # Steady-state error (last 10 seconds of cruise phase before lead vehicle)
    # Find when lead vehicle appears
    lead_appears_idx = None
    for i, d in enumerate(distances):
        if d is not None:
            lead_appears_idx = i
            break
    
    if lead_appears_idx and lead_appears_idx > 100:
        ss_speeds = speeds[lead_appears_idx-100:lead_appears_idx]
        speed_ss_error = abs(np.mean(ss_speeds) - set_speed)
    else:
        ss_speeds = speeds[-100:]
        speed_ss_error = abs(np.mean(ss_speeds) - set_speed)
    
    # Distance control metrics (follow phase)
    valid_dist_errors = [abs(e) for e in distance_errors if e is not None]
    valid_distances = [d for d in distances if d is not None]
    
    if valid_dist_errors:
        distance_ss_error = np.mean(valid_dist_errors[-100:])
        min_distance = min(valid_distances)
    else:
        distance_ss_error = 0
        min_distance = float('inf')
    
    # Count mode transitions
    mode_counts = {'cruise': 0, 'follow': 0, 'emergency': 0}
    for mode in modes:
        mode_counts[mode] += 1
    
    metrics = {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'distance_ss_error': distance_ss_error,
        'min_distance': min_distance,
        'mode_counts': mode_counts,
        'total_steps': len(data)
    }
    
    return metrics

if __name__ == '__main__':
    metrics = analyze_simulation()
    print("\n=== Simulation Performance Metrics ===")
    print(f"Rise Time: {metrics['rise_time']:.2f} s (target: <10s)")
    print(f"Overshoot: {metrics['overshoot']:.2f} m/s ({metrics['overshoot_pct']:.2f}%) (target: <5%)")
    print(f"Speed Steady-State Error: {metrics['speed_ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"Distance Steady-State Error: {metrics['distance_ss_error']:.3f} m (target: <2m)")
    print(f"Minimum Distance: {metrics['min_distance']:.2f} m (target: >5m)")
    print(f"\nMode Distribution:")
    for mode, count in metrics['mode_counts'].items():
        pct = (count / metrics['total_steps']) * 100
        print(f"  {mode}: {count} steps ({pct:.1f}%)")
