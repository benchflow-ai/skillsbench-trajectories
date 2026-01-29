import csv
import yaml
import math
from acc_system import AdaptiveCruiseControl

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def run_simulation():
    # Load parameters
    params = load_yaml('vehicle_params.yaml')
    tuning = load_yaml('tuning_results.yaml')
    
    # Update params with tuning results
    params['pid_speed'].update(tuning['pid_speed'])
    params['pid_distance'].update(tuning['pid_distance'])
    
    # Setup ACC
    acc = AdaptiveCruiseControl(params)
    
    # Simulation Constants
    dt = params['simulation']['dt']
    mass = params['vehicle']['mass']
    drag_coeff = params['vehicle']['drag_coefficient']
    
    # State
    ego_speed = 0.0
    current_distance = None
    
    results = []
    
    # header for results
    headers = ['time', 'ego_speed', 'acceleration_cmd', 'mode', 'distance_error', 'distance', 'ttc']
    
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        # We need to handle the loop carefully.
        # The sensor data corresponds to time t.
        # We run the controller at time t.
        # Then we update state to t+dt.
        
        # However, the output requires 1501 rows corresponding to the input.
        # So we process row, store state, then update.
        
        for row in reader:
            time_str = row['time']
            current_time = float(time_str)
            
            # Parse inputs
            lead_speed_str = row['lead_speed']
            lead_dist_str = row['distance'] # Only used for initialization
            
            lead_speed = None
            if lead_speed_str and lead_speed_str.strip():
                lead_speed = float(lead_speed_str)
            
            # Distance Logic
            # If lead exists in data
            if lead_speed is not None:
                if current_distance is None:
                    # Lead just appeared, initialize from CSV
                    if lead_dist_str and lead_dist_str.strip():
                        current_distance = float(lead_dist_str)
                    else:
                        # Should not happen if lead_speed is present based on file check
                        current_distance = 100.0 # Default fallback
                else:
                    # Already tracking, distance was updated in previous step
                    pass
            else:
                current_distance = None
            
            # Run ACC
            acc_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, current_distance, dt)
            
            # Calculate TTC for reporting
            ttc_val = None
            if current_distance is not None and lead_speed is not None:
                rel_v = ego_speed - lead_speed
                if rel_v > 0:
                    ttc_val = current_distance / rel_v
            
            # Store result (Current State + Command computed)
            # Format: time,ego_speed,acceleration_cmd,mode,distance_error,distance,ttc
            res_row = {
                'time': time_str,
                'ego_speed': f"{ego_speed:.2f}",
                'acceleration_cmd': f"{acc_cmd:.2f}",
                'mode': mode,
                'distance_error': f"{dist_error:.2f}" if dist_error is not None else "",
                'distance': f"{current_distance:.2f}" if current_distance is not None else "",
                'ttc': f"{ttc_val:.2f}" if ttc_val is not None else ""
            }
            results.append(res_row)
            
            # Physics Update (for next step)
            # Drag force: Fd = 0.5 * rho * Cd * A * v^2 ??
            # Or just Fd = Cd * v^2 as discussed?
            # Given the lack of Area/Density, and Cd=0.3 (which is typical for Cd, not Fd constant), 
            # I will assume standard Area=2.2, rho=1.225.
            # Fd = 0.5 * 1.225 * 0.3 * 2.2 * v^2 = 0.4 * v^2 approx.
            # If I use just 0.3 * v^2 it is similar. 
            # I will use Fd = 0.3 * v^2 (Treating Cd as lumped constant per my previous thought, 
            # or simply using the provided number as the only drag parameter).
            # To be safe and "physical", I'll treat it as Cd and assume standard constants.
            # But "drag_coefficient: 0.3" strongly implies the dimensionless Cd.
            # I will assume A=2.2 m^2 (average car), rho=1.225 kg/m^3.
            rho = 1.225
            area = 2.2
            drag_force = 0.5 * rho * drag_coeff * area * (ego_speed ** 2)
            
            # Net Accel
            # F_net = m * a_cmd - F_drag  Wait, a_cmd is usually engine/brake output.
            # If a_cmd is the requested acceleration, the car tries to achieve it.
            # Does the controller output net acceleration or engine force/accel?
            # Usually ACC output is "desired acceleration". The lower level controller handles throttle/brake to achieve it.
            # So, should I apply drag? 
            # If the ACC requests +1.0 m/s^2, the car (ideally) accelerates at 1.0.
            # If I subtract drag, I am simulating an open-loop throttle which is NOT what a_cmd usually represents in ACC.
            # ACC command -> Low Level Control -> Throttle/Brake.
            # "Simulation of the vehicle": 
            # If I assume the ACC output IS the realized acceleration (ideal lower level control), 
            # then v_next = v + a_cmd * dt.
            # BUT, the prompt mentions "steady-state error < 0.5 m/s". 
            # If I assume ideal actuation, P-control would have 0 steady state error.
            # The existence of steady state error suggests a disturbance or plant mismatch.
            # Drag acts as a disturbance if the controller outputs *force* or *throttle*.
            # But the method returns `acceleration_cmd` and limits are in m/s^2.
            # I will assume the system is slightly non-ideal or I should apply drag to the *command*?
            # No, physics: $a_{actual} = a_{cmd} - F_{drag}/m$. 
            # This implies $a_{cmd}$ is "engine acceleration".
            # This makes the most sense for creating a control challenge (steady state error).
            
            acc_actual = acc_cmd - (drag_force / mass)
            
            ego_speed += acc_actual * dt
            if ego_speed < 0: ego_speed = 0 # No reverse
            
            if current_distance is not None and lead_speed is not None:
                # Update distance for next step
                # d_next = d + (v_lead - v_ego_avg) * dt
                # Using simple Euler with current velocities
                current_distance += (lead_speed - ego_speed) * dt

    # Write results
    with open('simulation_results.csv', 'w') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    run_simulation()
