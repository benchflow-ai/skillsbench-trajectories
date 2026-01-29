"""Adaptive Cruise Control (ACC) system logic."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control with cruise, follow, and emergency modes."""

    def __init__(self, config):
        self.config = config
        self.pid_speed = None
        self.pid_distance = None

    def set_controllers(self, pid_speed, pid_distance):
        self.pid_speed = pid_speed
        self.pid_distance = pid_distance

    def _accel_limits(self):
        vehicle_cfg = self.config.get('vehicle', {})
        max_accel = float(vehicle_cfg.get('max_acceleration', 3.0))
        max_decel = float(vehicle_cfg.get('max_deceleration', -8.0))
        return max_decel, max_accel

    def compute(self, ego_speed, lead_speed, distance, dt):
        """Compute acceleration command and mode.

        Args:
            ego_speed (float): Ego vehicle speed (m/s).
            lead_speed (float|None): Lead vehicle speed (m/s) or None if absent.
            distance (float|None): Distance to lead vehicle (m) or None if absent.
            dt (float): Timestep (s).

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
        """
        if self.pid_speed is None or self.pid_distance is None:
            raise RuntimeError('PID controllers not configured')

        acc_cfg = self.config.get('acc_settings', {})
        set_speed = float(acc_cfg.get('set_speed', 30.0))
        time_headway = float(acc_cfg.get('time_headway', 1.5))
        min_gap = float(acc_cfg.get('min_distance', 10.0))
        emergency_ttc = float(acc_cfg.get('emergency_ttc_threshold', 3.0))

        max_decel, max_accel = self._accel_limits()

        if lead_speed is None or distance is None:
            mode = 'cruise'
            speed_error = set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            accel_cmd = max(max_decel, min(max_accel, accel_cmd))
            return accel_cmd, mode, None

        rel_speed = ego_speed - lead_speed
        if rel_speed > 0.0:
            ttc = distance / max(rel_speed, 1e-6)
        else:
            ttc = float('inf')

        if ttc < emergency_ttc:
            mode = 'emergency'
            self.pid_speed.reset()
            self.pid_distance.reset()
            accel_cmd = max_decel
            return accel_cmd, mode, None

        d_safe = min_gap + time_headway * ego_speed
        raw_distance_error = distance - d_safe

        mode = 'follow'
        if raw_distance_error >= 0.0:
            # Safe or far: prioritize speed control, treat distance error as zero.
            distance_error = 0.0
            speed_error = set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
        else:
            # Too close: use distance control to open the gap.
            distance_error = raw_distance_error
            accel_cmd = self.pid_distance.compute(distance_error, dt)

        # Prevent accelerating beyond the set speed in follow mode.
        if ego_speed >= set_speed and accel_cmd > 0.0:
            accel_cmd = 0.0

        accel_cmd = max(max_decel, min(max_accel, accel_cmd))
        return accel_cmd, mode, distance_error
