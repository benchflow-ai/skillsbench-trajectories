"""Adaptive Cruise Control (ACC) system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.set_speed = float(config['acc_settings']['set_speed'])
        self.time_headway = float(config['acc_settings']['time_headway'])
        self.min_distance = float(config['acc_settings']['min_distance'])
        self.emergency_ttc_threshold = float(
            config['acc_settings']['emergency_ttc_threshold']
        )
        self.max_accel = float(config['vehicle']['max_acceleration'])
        self.max_decel = float(config['vehicle']['max_deceleration'])

        pid_speed = config['pid_speed']
        pid_distance = config['pid_distance']

        self.speed_controller = PIDController(
            pid_speed['kp'],
            pid_speed['ki'],
            pid_speed['kd'],
            output_min=self.max_decel,
            output_max=self.max_accel,
        )
        self.distance_controller = PIDController(
            pid_distance['kp'],
            pid_distance['ki'],
            pid_distance['kd'],
            output_min=self.max_decel,
            output_max=self.max_accel,
        )
        self.last_mode = None

    def _safe_distance(self, ego_speed):
        return ego_speed * self.time_headway + self.min_distance

    def _determine_mode(self, lead_present, ttc):
        if not lead_present:
            return 'cruise'
        if ttc is not None and ttc < self.emergency_ttc_threshold:
            return 'emergency'
        return 'follow'

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = lead_speed is not None and distance is not None
        ttc = None
        if lead_present:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed

        mode = self._determine_mode(lead_present, ttc)
        if mode != self.last_mode:
            if mode == 'cruise':
                self.distance_controller.reset()
            elif mode == 'follow':
                self.distance_controller.reset()
            elif mode == 'emergency':
                self.distance_controller.reset()
            self.last_mode = mode

        distance_error = None

        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.speed_controller.compute(speed_error, dt)
        elif mode == 'emergency':
            distance_error = distance - self._safe_distance(ego_speed)
            accel_cmd = self.max_decel
        else:  # follow
            safe_distance = self._safe_distance(ego_speed)
            distance_error = distance - safe_distance

            if distance_error < 0:
                accel_cmd = self.distance_controller.compute(distance_error, dt)
            else:
                max_follow_speed = self.set_speed * 1.049
                closing_speed = lead_speed + (distance_error / max(self.time_headway, 0.1))
                desired_speed = min(max_follow_speed, closing_speed)
                accel_cmd = self.speed_controller.compute(desired_speed - ego_speed, dt)

        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        return accel_cmd, mode, distance_error
