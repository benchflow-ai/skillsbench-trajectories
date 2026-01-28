import csv

def calculate_metrics():
    data = []
    with open('simulation_results.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
            
    # Speed Rise Time (0 -> 30)
    # Target 30. Rise time 0->90% (27)
    # Start time is 0.
    t_start = 0.0
    t_90 = None
    max_speed = 0.0
    
    # Distance metrics (during 'follow' mode)
    min_distance = float('inf')
    max_dist_error = 0.0
    steady_state_dist_error = 0.0 # Average of last few follow points?
    follow_points = []
    
    for row in data:
        t = float(row['time'])
        v = float(row['ego_speed'])
        mode = row['mode']
        
        max_speed = max(max_speed, v)
        
        if v >= 27.0 and t_90 is None:
            t_90 = t
            
        if mode == 'follow':
            dist = float(row['distance'])
            err = float(row['distance_error'])
            min_distance = min(min_distance, dist)
            max_dist_error = max(max_dist_error, abs(err))
            follow_points.append(abs(err))
            
    rise_time = t_90 if t_90 else -1
    overshoot = (max_speed - 30.0) / 30.0 * 100
    
    # Distance Steady State: average error of last 5 seconds of following?
    # Hard to define "steady state" in dynamic following.
    # We'll just report mean absolute error.
    mean_dist_error = sum(follow_points) / len(follow_points) if follow_points else 0.0
    
    print(f"Rise Time (0-27m/s): {rise_time} s")
    print(f"Max Speed Overshoot: {overshoot:.2f} %")
    print(f"Min Following Distance: {min_distance:.2f} m")
    print(f"Max Distance Error: {max_dist_error:.2f} m")
    print(f"Mean Distance Error: {mean_dist_error:.2f} m")

if __name__ == '__main__':
    calculate_metrics()
