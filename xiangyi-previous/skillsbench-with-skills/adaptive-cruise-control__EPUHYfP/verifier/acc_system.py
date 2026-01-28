from pid_controller import PIDController
import math

class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_settings = config['acc_settings']
        vehicle = config['vehicle']
        pid_speed_cfg = config.get('pid_speed', {})
        pid_distance_cfg = config.get('pid_distance', {})

        self.set_speed = acc_settings['set_speed']
        self.time_headway = acc_settings['time_headway']
        self.min_distance = acc_settings['min_distance']
        self.emergency_ttc_threshold = acc_settings['emergency_ttc_threshold']
        self.follow_buffer = acc_settings.get('follow_buffer', 0.0)

        self.max_acceleration = vehicle['max_acceleration']
        self.max_deceleration = vehicle['max_deceleration']

        self.pid_speed = PIDController(pid_speed_cfg.get('kp', 0.1),
                                       pid_speed_cfg.get('ki', 0.01),
                                       pid_speed_cfg.get('kd', 0.0))
        self.pid_distance = PIDController(pid_distance_cfg.get('kp', 0.1),
                                          pid_distance_cfg.get('ki', 0.01),
                                          pid_distance_cfg.get('kd', 0.0))

    def compute(self, ego_speed, lead_speed, distance, dt):
        # Determine if lead vehicle is present
        if lead_speed is not None and distance is not None:
            desired_distance = self.min_distance + self.time_headway * ego_speed
            if distance > desired_distance + self.follow_buffer:
                lead_speed = None
                distance = None

        if lead_speed is None or distance is None:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            distance_error = None
        else:
            # Calculate time to collision
            rel_speed = ego_speed - lead_speed
            if rel_speed > 0:
                ttc = distance / max(rel_speed, 1e-5)
            else:
                ttc = math.inf

            desired_distance = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - desired_distance

            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                accel_cmd = self.max_deceleration
                # reset PID to avoid windup during emergency
                self.pid_speed.reset()
                self.pid_distance.reset()
            else:
                mode = 'follow'
                speed_adjust = self.pid_distance.compute(distance_error, dt)
                target_speed = max(0.0, lead_speed + speed_adjust)
                accel_cmd = self.pid_speed.compute(target_speed - ego_speed, dt)

        # Apply acceleration limits
        accel_cmd = max(self.max_deceleration, min(self.max_acceleration, accel_cmd))
        return accel_cmd, mode, distance_error
