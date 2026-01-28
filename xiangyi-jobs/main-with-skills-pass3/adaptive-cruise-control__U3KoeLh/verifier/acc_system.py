import math
from pid_controller import PIDController


def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))


class AdaptiveCruiseControl:
    def __init__(self, config, pid_speed=None, pid_distance=None):
        acc_settings = config['acc_settings']
        vehicle = config['vehicle']

        self.set_speed = acc_settings['set_speed']
        self.time_headway = acc_settings['time_headway']
        self.min_distance = acc_settings['min_distance']
        self.emergency_ttc = acc_settings['emergency_ttc_threshold']

        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        # Initialize PID controllers
        if pid_speed is None:
            pid_cfg = config.get('pid_speed', {'kp': 0.1, 'ki': 0.0, 'kd': 0.0})
            pid_speed = PIDController(pid_cfg['kp'], pid_cfg['ki'], pid_cfg['kd'],
                                      output_min=self.max_decel, output_max=self.max_accel)
        if pid_distance is None:
            pid_cfg = config.get('pid_distance', {'kp': 0.1, 'ki': 0.0, 'kd': 0.0})
            pid_distance = PIDController(pid_cfg['kp'], pid_cfg['ki'], pid_cfg['kd'],
                                         output_min=-10.0, output_max=10.0)

        self.speed_pid = pid_speed
        self.distance_pid = pid_distance

    def compute(self, ego_speed, lead_speed, distance, dt):
        distance_error = None
        ttc = None

        # Determine if lead vehicle is present
        lead_present = lead_speed is not None and not (isinstance(lead_speed, float) and math.isnan(lead_speed))
        if not lead_present:
            # Cruise control
            self.distance_pid.reset()
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = clamp(accel_cmd, self.max_decel, self.max_accel)
            return accel_cmd, mode, distance_error

        # Lead vehicle present
        if distance is not None and not (isinstance(distance, float) and math.isnan(distance)):
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed

        # Emergency override for very close distance
        if distance is not None and distance < self.min_distance:
            mode = 'emergency'
            self.speed_pid.reset()
            self.distance_pid.reset()
            accel_cmd = self.max_decel
            return accel_cmd, mode, distance_error

        # Emergency mode based on TTC
        if ttc is not None and ttc < self.emergency_ttc:
            mode = 'emergency'
            self.speed_pid.reset()
            self.distance_pid.reset()
            accel_cmd = self.max_decel
            return accel_cmd, mode, distance_error

        # Follow mode
        mode = 'follow'
        safe_distance = ego_speed * self.time_headway + self.min_distance
        if distance is not None:
            distance_error = distance - safe_distance
            # Only react when too close (negative error)
            if distance_error >= 0:
                distance_error = 0.0

        # When safe distance is satisfied, behave like cruise
        if distance_error is None or distance_error == 0.0:
            self.distance_pid.reset()
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_pid.compute(speed_error, dt)
            accel_cmd = clamp(accel_cmd, self.max_decel, self.max_accel)
            return accel_cmd, mode, distance_error

        # Distance control when too close
        speed_adjust = self.distance_pid.compute(distance_error, dt)
        target_speed = min(self.set_speed, max(0.0, lead_speed + speed_adjust))
        speed_error = target_speed - ego_speed
        accel_cmd = self.speed_pid.compute(speed_error, dt)
        accel_cmd = clamp(accel_cmd, self.max_decel, self.max_accel)

        return accel_cmd, mode, distance_error
