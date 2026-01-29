"""Adaptive Cruise Control system implementation."""

import yaml
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """Adaptive Cruise Control system with PID-based speed and distance control."""

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Dictionary containing vehicle and ACC settings from vehicle_params.yaml
        """
        # Vehicle parameters
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']
        self.mass = config['vehicle']['mass']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # PID controllers
        speed_pid = config.get('pid_speed', {'kp': 0.3, 'ki': 0.02, 'kd': 0.1})
        distance_pid = config.get('pid_distance', {'kp': 0.15, 'ki': 0.01, 'kd': 0.05})

        self.speed_controller = PIDController(speed_pid['kp'], speed_pid['ki'], speed_pid['kd'])
        self.distance_controller = PIDController(distance_pid['kp'], distance_pid['ki'], distance_pid['kd'])

        # Reset controllers
        self.speed_controller.reset()
        self.distance_controller.reset()

        # Previous mode for hysteresis
        self.prev_mode = 'cruise'

        # Rate limiting for acceleration
        self.prev_acceleration = 0.0
        self.max_accel_rate = 5.0  # Maximum rate of change of acceleration

    def compute_time_to_collision(self, ego_speed, lead_speed, distance):
        """
        Calculate Time-to-Collision (TTC).

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            float: Time-to-collision in seconds, or float('inf') if no collision
        """
        relative_speed = ego_speed - lead_speed

        # If lead vehicle is faster or equal speed, no collision
        if relative_speed <= 0:
            return float('inf')

        # Calculate TTC
        ttc = distance / relative_speed

        return ttc

    def compute_desired_distance(self, ego_speed):
        """
        Calculate desired following distance based on time headway.

        Args:
            ego_speed: Current ego vehicle speed (m/s)

        Returns:
            float: Desired distance in meters
        """
        return self.min_distance + ego_speed * self.time_headway

    def select_mode(self, lead_speed, distance, ttc, prev_mode):
        """
        Select ACC operating mode based on conditions with hysteresis.

        Args:
            lead_speed: Lead vehicle speed (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m)
            ttc: Time-to-collision (s)
            prev_mode: Previous operating mode

        Returns:
            str: Operating mode ('cruise', 'follow', or 'emergency')
        """
        # No lead vehicle detected
        if lead_speed is None or (lead_speed == 0 and distance == 0):
            return 'cruise'

        # Emergency braking if TTC is too low
        if ttc < self.emergency_ttc_threshold:
            return 'emergency'

        # Use hysteresis to prevent mode chattering
        # Stay in follow mode if we were already following
        if prev_mode == 'follow' and ttc < self.emergency_ttc_threshold * 2:
            return 'follow'

        # Following mode when lead vehicle is present
        return 'follow'

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute ACC control command.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m), or 0 if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
        """
        # Determine if lead vehicle is present
        lead_present = lead_speed is not None and lead_speed > 0

        # Calculate Time-to-Collision if lead vehicle is present
        ttc = float('inf')
        if lead_present:
            ttc = self.compute_time_to_collision(ego_speed, lead_speed, distance)

        # Select operating mode with hysteresis
        mode = self.select_mode(lead_speed, distance, ttc, self.prev_mode)
        self.prev_mode = mode

        # Compute acceleration command based on mode
        acceleration_cmd = 0.0
        distance_error = 0.0

        if mode == 'cruise':
            # Maintain set speed when no lead vehicle
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt)

        elif mode == 'follow':
            # Maintain safe following distance
            desired_distance = self.compute_desired_distance(ego_speed)
            distance_error = desired_distance - distance  # Positive when too close

            # Use PID on distance error to get speed adjustment
            # If too close (positive error), we want to slow down
            speed_adjustment = self.distance_controller.compute(distance_error, dt)

            # Target speed is limited between 0 and set_speed
            # When too close, target speed decreases
            target_speed = min(self.set_speed, max(0, lead_speed + speed_adjustment))

            # Hard minimum distance enforcement: if too close, target speed = 0
            if distance < self.min_distance * 1.2:  # Start slowing at 120% of min distance
                # Emergency braking to maintain minimum distance
                distance_below = self.min_distance - distance
                # Proportional braking based on how close we are
                brake_factor = min(1.0, distance_below / 5.0)  # Max brake at 5m below min
                target_speed = max(0, lead_speed * (1 - brake_factor))

            # Compute speed error and acceleration
            speed_error = target_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt)

        elif mode == 'emergency':
            # Emergency braking - maximum deceleration
            acceleration_cmd = self.max_deceleration

        # Apply acceleration limits
        acceleration_cmd = max(self.max_deceleration, min(acceleration_cmd, self.max_acceleration))

        # Apply rate limiting to prevent abrupt acceleration changes
        accel_change = acceleration_cmd - self.prev_acceleration
        max_change = self.max_accel_rate * dt
        if accel_change > max_change:
            acceleration_cmd = self.prev_acceleration + max_change
        elif accel_change < -max_change:
            acceleration_cmd = self.prev_acceleration - max_change

        self.prev_acceleration = acceleration_cmd

        # Prevent excessive deceleration when speed is very low
        if ego_speed < 0.5 and acceleration_cmd < -2.0:
            acceleration_cmd = -2.0
        if ego_speed < 0.1 and acceleration_cmd < 0:
            acceleration_cmd = 0.0

        return acceleration_cmd, mode, distance_error
