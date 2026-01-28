"""
Adaptive Cruise Control (ACC) System implementation.

The ACC system maintains a set cruising speed and automatically adjusts speed
to maintain a safe following distance when a vehicle is detected ahead.
"""

import math
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that manages both speed and distance control.

    Operating modes:
        - 'cruise': No lead vehicle detected, maintain set speed
        - 'follow': Lead vehicle detected, maintain safe following distance
        - 'emergency': TTC (Time-To-Collision) below threshold, apply emergency braking
    """

    def __init__(self, config):
        """
        Initialize the ACC system with configuration from vehicle_params.yaml.

        Args:
            config (dict): Configuration dictionary with keys:
                - 'vehicle': Vehicle specs
                - 'acc_settings': ACC control parameters
                - 'pid_speed': Speed controller gains (kp, ki, kd)
                - 'pid_distance': Distance controller gains (kp, ki, kd)
        """
        # Vehicle parameters
        self.vehicle = config.get('vehicle', {})
        self.mass = self.vehicle.get('mass', 1500)
        self.max_accel = self.vehicle.get('max_acceleration', 3.0)
        self.max_decel = self.vehicle.get('max_deceleration', -8.0)

        # ACC settings
        self.acc_settings = config.get('acc_settings', {})
        self.set_speed = self.acc_settings.get('set_speed', 30.0)
        self.time_headway = self.acc_settings.get('time_headway', 1.5)
        self.min_distance = self.acc_settings.get('min_distance', 10.0)
        self.emergency_ttc_threshold = self.acc_settings.get('emergency_ttc_threshold', 3.0)

        # Initialize PID controllers
        pid_speed_cfg = config.get('pid_speed', {})
        self.pid_speed = PIDController(
            pid_speed_cfg.get('kp', 0.1),
            pid_speed_cfg.get('ki', 0.01),
            pid_speed_cfg.get('kd', 0.0)
        )

        pid_distance_cfg = config.get('pid_distance', {})
        self.pid_distance = PIDController(
            pid_distance_cfg.get('kp', 0.1),
            pid_distance_cfg.get('ki', 0.01),
            pid_distance_cfg.get('kd', 0.0)
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on ego vehicle state and lead vehicle data.

        Args:
            ego_speed (float): Current speed of ego vehicle (m/s)
            lead_speed (float or None): Speed of lead vehicle (m/s), None if not present
            distance (float or None): Distance to lead vehicle (m), None if not present
            dt (float): Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error for diagnostics (m)
        """
        distance_error = None
        mode = 'cruise'
        accel_cmd = 0.0

        # Mode selection and control logic
        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise control mode
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)

        else:
            # Lead vehicle detected - check for emergency condition
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)

            if ttc is not None and ttc < self.emergency_ttc_threshold:
                # Emergency braking mode
                mode = 'emergency'
                accel_cmd = self.max_decel
            else:
                # Normal following mode
                mode = 'follow'

                # Desired distance is based on time headway and minimum gap
                desired_distance = self.time_headway * ego_speed + self.min_distance
                distance_error = desired_distance - distance

                # Use distance controller with some speed control blending
                accel_cmd = self.pid_distance.compute(distance_error, dt)

                # Also consider speed: if we're significantly below lead speed, speed up
                # to maintain formation, but don't exceed the set speed
                if ego_speed < lead_speed and distance_error > 2.0:
                    speed_boost = self.pid_speed.compute(self.set_speed - ego_speed, dt) * 0.3
                    accel_cmd += speed_boost

        # Clamp acceleration to vehicle limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, mode, distance_error

    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """
        Compute Time-To-Collision (TTC).

        TTC is the time until collision if both vehicles maintain constant speeds.
        Negative or very large TTC values indicate no collision risk.

        Args:
            ego_speed (float): Ego vehicle speed (m/s)
            lead_speed (float): Lead vehicle speed (m/s)
            distance (float): Distance to lead vehicle (m)

        Returns:
            float or None: TTC in seconds, or None if no collision risk
        """
        relative_speed = ego_speed - lead_speed

        # If relative speed is non-positive, no collision risk
        if relative_speed <= 0:
            return float('inf')

        # TTC = distance / relative_speed
        if distance <= 0:
            return 0.0
        else:
            ttc = distance / relative_speed
            return ttc

    def reset(self):
        """Reset all PID controller states."""
        self.pid_speed.reset()
        self.pid_distance.reset()
