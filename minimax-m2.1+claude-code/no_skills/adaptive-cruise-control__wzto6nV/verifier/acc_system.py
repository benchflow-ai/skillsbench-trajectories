"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with speed and distance control.

    Modes:
        - cruise: No lead vehicle detected, maintain set speed
        - follow: Lead vehicle detected, maintain safe following distance
        - emergency: TTC below threshold, maximum deceleration
    """

    def __init__(self, config: dict):
        """Initialize ACC system with configuration.

        Args:
            config: Nested dict from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - pid_speed: kp, ki, kd for speed control
                - pid_distance: kp, ki, kd for distance control
                - vehicle: max_acceleration, max_deceleration
        """
        acc_settings = config['acc_settings']
        pid_speed = config.get('pid_speed', {'kp': 0.1, 'ki': 0.01, 'kd': 0.0})
        pid_distance = config.get('pid_distance', {'kp': 0.1, 'ki': 0.01, 'kd': 0.0})
        vehicle = config.get('vehicle', {'max_acceleration': 3.0, 'max_deceleration': -8.0})

        # ACC settings
        self.set_speed = acc_settings['set_speed']
        self.time_headway = acc_settings['time_headway']
        self.min_distance = acc_settings['min_distance']
        self.ttc_threshold = acc_settings['emergency_ttc_threshold']

        # Acceleration limits
        self.max_accel = vehicle['max_acceleration']
        self.max_decel = vehicle['max_deceleration']

        # PID controllers
        self.speed_pid = PIDController(
            kp=pid_speed['kp'],
            ki=pid_speed['ki'],
            kd=pid_speed['kd']
        )
        self.distance_pid = PIDController(
            kp=pid_distance['kp'],
            ki=pid_distance['ki'],
            kd=pid_distance['kd']
        )

    def compute(self, ego_speed: float, lead_speed: float | None,
                distance: float | None, dt: float) -> tuple:
        """Compute acceleration command based on sensor data.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), None if not detected
            distance: Distance to lead vehicle (m), None if not detected
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Error in following distance (m)
        """
        # Determine mode
        mode = self._determine_mode(lead_speed, distance, ego_speed)

        if mode == 'cruise':
            # Speed control mode - maintain set speed
            speed_error = self.set_speed - ego_speed
            acc_cmd = self.speed_pid.compute(speed_error, dt)
            distance_error = 0.0

        elif mode == 'follow':
            # Distance control mode - maintain safe following distance
            desired_distance = self._calculate_desired_distance(ego_speed)
            # distance_error > 0 means we need more distance (too close)
            # distance_error < 0 means we have extra space (can go faster)
            distance_error = desired_distance - distance

            # Calculate target speed based on distance error
            # If we're too close (positive error), target speed < lead_speed
            # If we have extra space (negative error), target speed > lead_speed
            if lead_speed is not None:
                # Base target speed is lead vehicle speed
                target_speed = lead_speed

                # Adjust target speed based on distance error
                # If distance_error > 0 (we're too close), decrease target_speed to slow down
                # If distance_error < 0 (we have extra space), increase target_speed
                distance_correction = -self.distance_pid.compute(distance_error, dt)
                target_speed += distance_correction

                # Speed error relative to adjusted target
                speed_error = target_speed - ego_speed
            else:
                # Fallback to set speed if no lead speed
                speed_error = self.set_speed - ego_speed

            # Use speed PID for final acceleration command
            acc_cmd = self.speed_pid.compute(speed_error, dt)

        else:  # emergency
            # Maximum deceleration for emergency braking
            acc_cmd = self.max_decel
            distance_error = 0.0

        # Apply acceleration limits
        acc_cmd = max(self.max_decel, min(self.max_accel, acc_cmd))

        # Prevent overshoot of set speed in cruise mode
        if mode == 'cruise' and ego_speed > self.set_speed:
            acc_cmd = min(0.0, acc_cmd)
            acc_cmd = max(self.max_decel, acc_cmd)

        return acc_cmd, mode, distance_error

    def _determine_mode(self, lead_speed: float | None,
                        distance: float | None, ego_speed: float) -> str:
        """Determine ACC operating mode.

        Args:
            lead_speed: Lead vehicle speed or None
            distance: Distance to lead vehicle or None
            ego_speed: Current ego speed

        Returns:
            Mode string: 'cruise', 'follow', or 'emergency'
        """
        # No lead vehicle detected
        if lead_speed is None or distance is None:
            return 'cruise'

        # Calculate Time To Collision
        ttc = self._calculate_ttc(ego_speed, lead_speed, distance)

        # Emergency braking condition
        if ttc is not None and ttc < self.ttc_threshold:
            return 'emergency'

        return 'follow'

    def _calculate_ttc(self, ego_speed: float, lead_speed: float,
                       distance: float) -> float | None:
        """Calculate Time To Collision.

        Args:
            ego_speed: Current ego speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            TTC in seconds, or None if approaching vehicle is not closing gap
        """
        # Relative speed (positive means ego is closing gap)
        relative_speed = lead_speed - ego_speed

        # Only calculate TTC if ego is approaching lead vehicle
        if relative_speed >= 0:
            return float('inf')

        return abs(distance / relative_speed)

    def _calculate_desired_distance(self, ego_speed: float) -> float:
        """Calculate desired following distance based on time headway.

        Args:
            ego_speed: Current ego speed (m/s)

        Returns:
            Desired following distance (m)
        """
        return self.min_distance + ego_speed * self.time_headway

    def reset(self):
        """Reset ACC system state."""
        self.speed_pid.reset()
        self.distance_pid.reset()
