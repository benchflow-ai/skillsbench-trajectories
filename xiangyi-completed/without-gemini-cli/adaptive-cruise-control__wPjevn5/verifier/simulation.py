import yaml
import csv
import math
from acc_system import AdaptiveCruiseControl

def run_simulation():
    # Load params
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
        
    # Update config with tuned PIDs
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']
    
    acc = AdaptiveCruiseControl(config)
    
    # Simulation state
    ego_speed = 0.0
    sim_distance = None
    
    dt = config['simulation']['dt']
    max_accel = config['vehicle']['max_acceleration']
    max_decel = config['vehicle']['max_deceleration']
    
    # Read CSV
    input_data = []
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            input_data.append(row)
            
    results = []
    
    # Check if header matches expectation
    # Expected: time,ego_speed,lead_speed,distance
    
    # Loop
    lead_present_prev = False
    
    for row in input_data:
        t = float(row['time'])
        
        # Parse inputs
        lead_speed_raw = row['lead_speed']
        dist_raw = row['distance']
        
        lead_speed = None
        if lead_speed_raw and lead_speed_raw.strip():
            lead_speed = float(lead_speed_raw)
            
        # Physics Update (Distance)
        # We need to update distance based on PREVIOUS step's speeds
        # But here we are iterating time steps.
        # Let's assume the loop step corresponds to the state at time t.
        # We compute control for time t.
        # Then we integrate for t+1.
        
        # Handling Lead Vehicle
        if lead_speed is not None:
            if not lead_present_prev:
                # Just detected. Initialize distance from sensor.
                if dist_raw and dist_raw.strip():
                    sim_distance = float(dist_raw)
                else:
                    # Should not happen given logic, but fallback
                    sim_distance = 100.0 
            else:
                # Integrate distance
                # d_new = d_old + (v_lead_prev - v_ego_prev) * dt
                # But we don't have v_lead_prev easily unless we store it.
                # Actually, simplest Euler integration:
                # d[k] = d[k-1] + (v_lead[k-1] - v_ego[k-1]) * dt
                # So we need to do the physics update at the END of the loop or keep track.
                pass
        else:
            sim_distance = None
            
        lead_present_prev = (lead_speed is not None)
        
        # Compute Control
        acc_cmd, mode, d_error = acc.compute(ego_speed, lead_speed, sim_distance, dt)
        
        # Calculate TTC for logging
        ttc = None
        if lead_speed is not None and sim_distance is not None:
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0 and sim_distance > 0:
                ttc = sim_distance / rel_speed
            elif rel_speed <= 0:
                ttc = float('inf')
        
        # Log Result
        # Format: time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
        results.append({
            'time': t,
            'ego_speed': ego_speed,
            'acceleration_cmd': acc_cmd,
            'mode': mode,
            'distance_error': d_error if d_error is not None else '',
            'distance': sim_distance if sim_distance is not None else '',
            'ttc': ttc if ttc is not None else ''
        })
        
        # Update Physics for NEXT step
        # v_ego_new = v_ego + acc * dt
        # But we need to handle the distance integration too.
        # distance[k+1] = distance[k] + (v_lead[k] - v_ego[k]) * dt
        # We need v_lead for the integration.
        # If v_lead is None now, but becomes not None next step, we handle init then.
        # If v_lead is not None now, we update for next step.
        
        # Update speed
        # Apply physical limits (though acc_cmd is already clamped, physics is same)
        ego_speed += acc_cmd * dt
        if ego_speed < 0: ego_speed = 0
        
        # Update distance
        if sim_distance is not None and lead_speed is not None:
            sim_distance += (lead_speed - ego_speed) * dt
            
    # Write results
    with open('simulation_results.csv', 'w', newline='') as f:
        fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

if __name__ == "__main__":
    run_simulation()
