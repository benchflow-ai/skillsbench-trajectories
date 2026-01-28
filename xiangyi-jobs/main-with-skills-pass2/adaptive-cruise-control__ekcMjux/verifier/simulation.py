import csv
import yaml
from acc_system import AdaptiveCruiseControl

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def run_simulation():
    # Load config
    params = load_yaml('vehicle_params.yaml')
    try:
        tuning = load_yaml('tuning_results.yaml')
        # Update params with tuned values
        if 'pid_speed' in tuning:
            params['pid_speed'] = tuning['pid_speed']
        if 'pid_distance' in tuning:
            params['pid_distance'] = tuning['pid_distance']
    except FileNotFoundError:
        print("Warning: tuning_results.yaml not found. Using default params.")

    acc = AdaptiveCruiseControl(params)
    
    dt = params['simulation']['dt']
    max_accel = params['vehicle']['max_acceleration']
    max_decel = params['vehicle']['max_deceleration']
    
    # Read sensor data
    sensor_data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_data.append(row)
            
    # Simulation State
    ego_speed = 0.0
    ego_pos_sim = 0.0
    
    results = []
    
    # CSV Data check: ensure we process exactly the rows in CSV
    # The prompt says 1501 rows (t=0 to 150).
    
    lead_active = False
    p_lead = 0.0 # Absolute position of lead car in simulation frame
    
    for i, row in enumerate(sensor_data):
        time = float(row['time'])
        
        # Parse CSV inputs
        try:
            v_lead_csv = float(row['lead_speed']) if row['lead_speed'] else None
            d_csv = float(row['distance']) if row['distance'] else None
            # v_ego_csv unused for position now
        except ValueError:
            v_lead_csv = None
            d_csv = None

        # Update Lead Vehicle Position Logic
        current_distance = None
        current_lead_speed = None
        
        if v_lead_csv is not None and d_csv is not None:
            if not lead_active:
                # Lead vehicle just appeared (or reappeared)
                # Initialize its position relative to CURRENT ego position
                # This ensures the scenario "starts" with the car at distance d_csv
                p_lead = ego_pos_sim + d_csv
                lead_active = True
            else:
                # Update lead position based on lead velocity
                # We use the velocity from the CSV row. 
                # Assuming this velocity held for the last dt (or will hold for next dt).
                # Simple Euler: p_lead += v * dt
                p_lead += v_lead_csv * dt
            
            current_distance = p_lead - ego_pos_sim
            current_lead_speed = v_lead_csv
            
        else:
            lead_active = False
            current_distance = None
            current_lead_speed = None

        # Run ACC
        accel_cmd, mode, dist_error = acc.compute(ego_speed, current_lead_speed, current_distance, dt)
        
        # Calculate TTC for results (if applicable)
        ttc = None
        if current_distance is not None and current_lead_speed is not None:
            rel_speed = ego_speed - current_lead_speed
            if rel_speed > 0:
                ttc = current_distance / rel_speed
                
        # Store Result (Before updating state for next step)
        results.append({
            'time': time,
            'ego_speed': ego_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': dist_error if dist_error is not None else '',
            'distance': current_distance if current_distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        })
        
        # Update Ego State for next step
        # Simple Euler integration
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed) # No reversing
        
        ego_pos_sim += ego_speed * dt

    # Write Results
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

if __name__ == '__main__':
    run_simulation()
