from pid_controller import PIDController


class AdaptiveCruiseControl:
    def __init__(self, config):
        self.config = config
        acc_cfg = config.get('acc_settings', {})
        self.set_speed = float(acc_cfg.get('set_speed', 30.0))
        self.time_headway = float(acc_cfg.get('time_headway', 1.5))
        self.min_distance = float(acc_cfg.get('min_distance', 10.0))
        self.emergency_ttc_threshold = float(acc_cfg.get('emergency_ttc_threshold', 3.0))

        vehicle_cfg = config.get('vehicle', {})
        self.max_accel = float(vehicle_cfg.get('max_acceleration', 3.0))
        self.max_decel = float(vehicle_cfg.get('max_deceleration', -8.0))
        self.rel_speed_gain = 8.0

        speed_pid_cfg = config.get('pid_speed', {})
        dist_pid_cfg = config.get('pid_distance', {})
        self.pid_speed = PIDController(
            speed_pid_cfg.get('kp', 0.1),
            speed_pid_cfg.get('ki', 0.01),
            speed_pid_cfg.get('kd', 0.0),
        )
        self.pid_distance = PIDController(
            dist_pid_cfg.get('kp', 0.1),
            dist_pid_cfg.get('ki', 0.01),
            dist_pid_cfg.get('kd', 0.0),
        )

        self._mode = None

    def _reset_controllers(self):
        self.pid_speed.reset()
        self.pid_distance.reset()

    def compute(self, ego_speed, lead_speed, distance, dt):
        lead_present = (lead_speed is not None) and (distance is not None)

        ttc = float('inf')
        if lead_present:
            rel_speed = max(ego_speed - lead_speed, 0.0)
            if rel_speed > 1e-3 and distance > 0.0:
                ttc = distance / rel_speed

        if not lead_present:
            mode = 'cruise'
        elif ttc < self.emergency_ttc_threshold:
            mode = 'emergency'
        else:
            mode = 'follow'

        if mode != self._mode:
            self._reset_controllers()
            self._mode = mode

        distance_error = None
        if mode == 'cruise':
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
        elif mode == 'emergency':
            accel_cmd = self.max_decel
        else:
            desired_gap = self.min_distance + self.time_headway * ego_speed
            distance_error = distance - desired_gap
            rel_speed = lead_speed - ego_speed
            control_error = distance_error + self.rel_speed_gain * rel_speed
            accel_cmd = self.pid_distance.compute(control_error, dt)
            # Report only gap violations (negative values indicate too close).
            distance_error = min(distance_error, 0.0)

        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))
        return accel_cmd, mode, distance_error
