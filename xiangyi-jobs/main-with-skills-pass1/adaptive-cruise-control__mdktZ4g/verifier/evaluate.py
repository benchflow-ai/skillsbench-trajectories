import csv

def evaluate():
    ego_speeds = []
    dist_errors = []
    distances = []
    times = []
    modes = []
    
    with open('simulation_results.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(float(row['time']))
            ego_speeds.append(float(row['ego_speed']))
            modes.append(row['mode'])
            if row['distance_error']:
                dist_errors.append(float(row['distance_error']))
            if row['distance']:
                distances.append(float(row['distance']))

    # Speed metrics (during cruise mode before lead vehicle appears)
    target_speed = 30.0
    rise_time_90 = None
    for t, v in zip(times, ego_speeds):
        if v >= 0.9 * target_speed:
            rise_time_90 = t
            break
    
    max_speed = max(ego_speeds)
    overshoot = (max_speed - target_speed) / target_speed if max_speed > target_speed else 0
    
    # SS error for speed (find a period where it's cruise and stabilized)
    cruise_speeds = [v for v, m, t_val in zip(ego_speeds, modes, times) if m == 'cruise' and t_val > 20]
    ss_error_speed = abs(cruise_speeds[-1] - target_speed) if cruise_speeds else None
    
    # Distance metrics
    min_dist = min(distances) if distances else None
    follow_errors = [abs(e) for e, m in zip(dist_errors, modes) if m == 'follow']
    ss_error_dist = follow_errors[-1] if follow_errors else None
    
    print(f"Rise Time (90%): {rise_time_90}")
    print(f"Overshoot: {overshoot:.4f}")
    print(f"Speed SS Error: {ss_error_speed}")
    print(f"Min Distance: {min_dist}")
    print(f"Distance SS Error: {ss_error_dist}")

if __name__ == "__main__":
    evaluate()
