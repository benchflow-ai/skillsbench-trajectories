import math

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_settings = config['acc_settings']
        vehicle = config['vehicle']

        self.set_speed = float(acc_settings['set_speed'])
        self.time_headway = float(acc_settings['time_headway'])
        self.min_distance = float(acc_settings['min_distance'])
        self.emergency_ttc_threshold = float(acc_settings['emergency_ttc_threshold'])

        self.max_acceleration = float(vehicle['max_acceleration'])
        self.max_deceleration = float(vehicle['max_deceleration'])

        pid_speed = config['pid_speed']
        pid_distance = config['pid_distance']

        self.speed_controller = PIDController(
            pid_speed['kp'], pid_speed['ki'], pid_speed['kd']
        )
        self.distance_controller = PIDController(
            pid_distance['kp'], pid_distance['ki'], pid_distance['kd']
        )

        self.speed_controller.output_limits = (
            self.max_deceleration,
            self.max_acceleration,
        )
        self.distance_controller.output_limits = (
            self.max_deceleration,
            self.max_acceleration,
        )

        self._last_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None

        if not lead_present:
            if self._last_mode in ('follow', 'emergency'):
                self.distance_controller.reset()
            self._last_mode = 'cruise'
            error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(error, dt)
            acceleration_cmd = self._clamp_accel(acceleration_cmd)
            return acceleration_cmd, 'cruise', None

        relative_speed = ego_speed - lead_speed
        ttc = math.inf
        if relative_speed > 1e-6:
            ttc = distance / relative_speed

        desired_gap = self.min_distance + self.time_headway * ego_speed
        distance_error = distance - desired_gap

        if ttc < self.emergency_ttc_threshold:
            self.distance_controller.reset()
            self._last_mode = 'emergency'
            return self.max_deceleration, 'emergency', distance_error

        acceleration_cmd = self.distance_controller.compute(distance_error, dt)
        if ego_speed >= self.set_speed and acceleration_cmd > 0.0:
            acceleration_cmd = 0.0

        acceleration_cmd = self._clamp_accel(acceleration_cmd)
        self._last_mode = 'follow'
        return acceleration_cmd, 'follow', distance_error

    def _clamp_accel(self, acceleration_cmd):
        return max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))
