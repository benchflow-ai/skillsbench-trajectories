import math
from pid_controller import PIDController

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        self.acc_settings = config['acc_settings']
        self.vehicle_params = config['vehicle']
        
        # Initialize PIDs (will be updated with tuned values later)
        # Default placeholders, expected to be overwritten or passed in config if structure allowed
        # But the prompt says simulation.py reads PID gains from tuning_results.yaml
        # However, acc_system might need to accept PID instances or params.
        # The prompt says constructor takes 'config' from vehicle_params.yaml.
        # It implies the ACC class manages the logic, but maybe the PIDs are initialized inside or passed.
        # Let's assume we initialize PIDs here, but we will provide methods to update gains or pass them in config.
        # Actually, simulation.py reads tuning_results.yaml. 
        # I'll add a method to update_gains or initialize with them if present in config.
        
        self.pid_speed = PIDController(
            config.get('pid_speed', {}).get('kp', 0.1),
            config.get('pid_speed', {}).get('ki', 0.01),
            config.get('pid_speed', {}).get('kd', 0.0)
        )
        self.pid_distance = PIDController(
            config.get('pid_distance', {}).get('kp', 0.1),
            config.get('pid_distance', {}).get('ki', 0.01),
            config.get('pid_distance', {}).get('kd', 0.0)
        )

    def update_gains(self, speed_gains, distance_gains):
        self.pid_speed.kp = speed_gains['kp']
        self.pid_speed.ki = speed_gains['ki']
        self.pid_speed.kd = speed_gains['kd']
        self.pid_speed.reset()
        
        self.pid_distance.kp = distance_gains['kp']
        self.pid_distance.ki = distance_gains['ki']
        self.pid_distance.kd = distance_gains['kd']
        self.pid_distance.reset()

    def compute(self, ego_speed, lead_speed, distance, dt):
        # Determine mode
        mode = 'cruise'
        distance_error = None
        accel_cmd = 0.0
        
        # Check if lead vehicle is present
        # In sensor_data.csv, missing data might be empty string or NaN. 
        # The caller should handle parsing. If distance is None or NaN, no car.
        
        if distance is None or distance == '' or math.isnan(float(distance)):
            mode = 'cruise'
            error = self.acc_settings['set_speed'] - ego_speed
            accel_cmd = self.pid_speed.compute(error, dt)
        else:
            dist = float(distance)
            l_speed = float(lead_speed) if lead_speed is not None else 0.0
            
            # Calculate TTC
            # TTC = distance / relative_speed (rel_speed = ego - lead)
            rel_speed = ego_speed - l_speed
            ttc = float('inf')
            if rel_speed > 0.001:
                ttc = dist / rel_speed
            
            if ttc < self.acc_settings['emergency_ttc_threshold']:
                mode = 'emergency'
                # Emergency braking: max deceleration
                accel_cmd = self.vehicle_params['max_deceleration']
                # Still calculate distance error for reporting
                desired_distance = self.acc_settings['min_distance'] + self.acc_settings['time_headway'] * ego_speed
                distance_error = dist - desired_distance
            else:
                mode = 'follow'
                desired_distance = self.acc_settings['min_distance'] + self.acc_settings['time_headway'] * ego_speed
                distance_error = dist - desired_distance
                # Distance control
                # error > 0 means too far, accel. error < 0 means too close, decel.
                accel_cmd = self.pid_distance.compute(distance_error, dt)

        # Clamp acceleration
        accel_cmd = max(self.vehicle_params['max_deceleration'], 
                        min(self.vehicle_params['max_acceleration'], accel_cmd))
        
        return accel_cmd, mode, distance_error
