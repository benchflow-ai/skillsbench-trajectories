import csv
import yaml
import math
from acc_system import AdaptiveCruiseControl

def load_params(yaml_file):
    with open(yaml_file, 'r') as f:
        return yaml.safe_load(f)

def run_simulation():
    # Load configs
    vehicle_params = load_params('vehicle_params.yaml')
    tuning_results = load_params('tuning_results.yaml')
    
    # Initialize ACC
    acc = AdaptiveCruiseControl(vehicle_params)
    acc.update_gains(tuning_results['pid_speed'], tuning_results['pid_distance'])
    
    # Simulation constants
    dt = vehicle_params['simulation']['dt']
    mass = vehicle_params['vehicle']['mass']
    drag_coef = vehicle_params['vehicle']['drag_coefficient']
    
    # Load Sensor Data
    sensor_data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sensor_data.append(row)
            
    # Pre-process Lead Position
    # We need to reconstruct where the lead car actually was.
    # Pos_Lead(t) = Pos_Ego_Ref(t) + Dist_Ref(t)
    
    ref_ego_pos = 0.0
    lead_positions = [] # Same length as sensor_data
    lead_speeds = []
    
    for i, row in enumerate(sensor_data):
        time = float(row['time'])
        ref_ego_spd = float(row['ego_speed']) if row['ego_speed'] else 0.0
        
        # Lead data
        l_spd_raw = row['lead_speed']
        dist_raw = row['distance']
        
        has_lead = (l_spd_raw and l_spd_raw.strip() != '' and 
                    dist_raw and dist_raw.strip() != '')
        
        if has_lead:
            l_spd = float(l_spd_raw)
            dist = float(dist_raw)
            l_pos = ref_ego_pos + dist
            lead_positions.append(l_pos)
            lead_speeds.append(l_spd)
        else:
            lead_positions.append(None)
            lead_speeds.append(None)
        
        # Update ref pos for next step
        # Assuming constant velocity within the step or Euler integration
        ref_ego_pos += ref_ego_spd * dt

    # Run Control Loop
    sim_ego_speed = 0.0 # Start at 0 per prompt "initial speed ~0 m/s" 
                        # (actually row 0 has ego_speed 0.0)
    sim_ego_pos = 0.0
    
    results = []
    
    for i, row in enumerate(sensor_data):
        time = float(row['time'])
        
        # Get Environment State
        l_pos = lead_positions[i]
        l_spd = lead_speeds[i]
        
        if l_pos is not None:
            current_dist = l_pos - sim_ego_pos
            current_lead_spd = l_spd
        else:
            current_dist = None
            current_lead_spd = None
            
        # Run ACC
        # Note: 'distance' passed to compute is the current simulated distance
        accel_cmd, mode, dist_error = acc.compute(sim_ego_speed, current_lead_spd, current_dist, dt)
        
        # Physics Update
        # F_drag = C * v^2
        f_drag = drag_coef * sim_ego_speed * sim_ego_speed
        a_net = accel_cmd - (f_drag / mass)
        
        # Record state BEFORE update (or after? "0.0, 0.0" implies state at t)
        # Usually logs state at time t.
        # TTC calculation for logging
        ttc = ''
        if current_dist is not None and current_lead_spd is not None:
            rel_spd = sim_ego_speed - current_lead_spd
            if rel_spd > 0.001:
                ttc_val = current_dist / rel_spd
                ttc = f"{ttc_val:.2f}"
        
        # Log
        # time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
        results.append({
            'time': f"{time:.1f}",
            'ego_speed': f"{sim_ego_speed:.2f}",
            'acceleration_cmd': f"{accel_cmd:.2f}",
            'mode': mode,
            'distance_error': f"{dist_error:.2f}" if dist_error is not None else '',
            'distance': f"{current_dist:.2f}" if current_dist is not None else '',
            'ttc': ttc
        })
        
        # Update State
        sim_ego_speed += a_net * dt
        if sim_ego_speed < 0: sim_ego_speed = 0.0
        
        sim_ego_pos += sim_ego_speed * dt

    # Write Results
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    run_simulation()
