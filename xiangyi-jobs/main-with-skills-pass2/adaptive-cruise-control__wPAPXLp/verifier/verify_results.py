
import csv

def verify():
    with open('simulation_results.csv', 'r') as f:
        reader = list(csv.DictReader(f))
    
    # Rise time
    rise_time = None
    for row in reader:
        if float(row['ego_speed']) >= 30.0 * 0.9:
            rise_time = float(row['time'])
            break
    
    # Overshoot (cruise)
    max_speed_cruise = 0
    for row in reader:
        t = float(row['time'])
        if t < 30:
            max_speed_cruise = max(max_speed_cruise, float(row['ego_speed']))
    overshoot = (max_speed_cruise - 30.0) / 30.0 if max_speed_cruise > 30.0 else 0
    
    # SSE speed at t=29.9
    sse_speed = 0
    for row in reader:
        if float(row['time']) == 29.9:
            sse_speed = abs(30.0 - float(row['ego_speed']))
            break
            
    # SSE distance at t=70.0
    sse_distance = 0
    for row in reader:
        if float(row['time']) == 70.0:
            sse_distance = abs(float(row['distance_error']))
            break
            
    # Min distance
    min_dist = float('inf')
    for row in reader:
        if row['distance']:
            min_dist = min(min_dist, float(row['distance']))
            
    print(f"Rise Time: {rise_time}")
    print(f"Overshoot: {overshoot}")
    print(f"SSE Speed: {sse_speed}")
    print(f"SSE Distance: {sse_distance}")
    print(f"Min Distance: {min_dist}")

if __name__ == "__main__":
    verify()
