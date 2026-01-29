"""Adaptive Cruise Control (ACC) system implementation."""

import yaml
from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control system that maintains set speed or safe following distance.

    The system operates in three modes:
    - 'cruise': Maintains set speed when no lead vehicle is detected
    - 'follow': Maintains safe following distance when lead vehicle is present
    - 'emergency': Emergency braking when time-to-collision is below threshold
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration parameters.

        Args:
            config: Nested dictionary containing:
                - vehicle: mass, max_acceleration, max_deceleration
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - pid_speed: kp, ki, kd
                - pid_distance: kp, ki, kd
        """
        # Vehicle parameters
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # PID controllers for speed and distance control
        self.speed_pid = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )

        self.distance_pid = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

        self.last_distance_error = 0.0

    def compute_time_to_collision(self, ego_speed, lead_speed, distance):
        """
        Calculate Time-To-Collision (TTC) in seconds.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s)
            distance: Distance to lead vehicle (m)

        Returns:
            float: Time-to-collision in seconds, or float('inf') if lead_speed <= ego_speed
        """
        if lead_speed is None or lead_speed is False:
            return float('inf')

        relative_speed = ego_speed - lead_speed

        # If lead vehicle is faster or at same speed, TTC is infinite
        if relative_speed <= 0:
            return float('inf')

        # TTC = distance / relative_speed
        ttc = distance / relative_speed
        return ttc

    def compute_desired_distance(self, ego_speed):
        """
        Calculate desired following distance based on time headway policy.

        Args:
            ego_speed: Current ego vehicle speed (m/s)

        Returns:
            float: Desired distance in meters (min_distance + time_headway * speed)
        """
        return self.min_distance + self.time_headway * ego_speed

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m), or None if no lead vehicle
            dt: Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: 'cruise', 'follow', or 'emergency'
                - distance_error: Error in following distance (m)
        """
        mode = 'cruise'
        acceleration_cmd = 0.0
        distance_error = None

        # Check if lead vehicle is present (lead_speed and distance are not None/empty)
        if lead_speed is None or lead_speed == '' or distance is None or distance == '':
            # No lead vehicle - maintain set speed
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_pid.compute(speed_error, dt)
            distance_error = None

        else:
            # Lead vehicle present - check for emergency condition
            ttc = self.compute_time_to_collision(ego_speed, lead_speed, distance)

            if ttc < self.emergency_ttc_threshold:
                # Emergency situation - maximum deceleration
                mode = 'emergency'
                acceleration_cmd = self.max_deceleration
                distance_error = self.compute_desired_distance(ego_speed) - distance

            else:
                # Normal following mode - maintain safe distance
                mode = 'follow'

                # Calculate desired distance
                desired_distance = self.compute_desired_distance(ego_speed)
                distance_error = desired_distance - distance

                # Calculate desired speed - should not exceed set speed
                # Use conservative approach: cap at set speed
                desired_speed = min(self.set_speed, lead_speed + 1.0)

                # Calculate speed error
                speed_error = desired_speed - ego_speed

                # Primary control: distance-based with conservative gains
                distance_accel = -self.distance_pid.compute(distance_error, dt)

                # Secondary control: speed limiting to prevent overshoot
                speed_accel = self.speed_pid.compute(speed_error, dt)

                # Combine controls (60% distance, 40% speed for better speed control)
                acceleration_cmd = 0.6 * distance_accel + 0.4 * speed_accel

                # Hard cap: never accelerate beyond set speed
                if acceleration_cmd > 0 and ego_speed >= self.set_speed - 0.5:
                    acceleration_cmd = 0.0

                # Additional constraint: don't accelerate if we're already faster than lead vehicle
                if ego_speed > lead_speed + 0.5 and distance_error < 5:
                    acceleration_cmd = min(acceleration_cmd, 0.0)

                # If we're too close, force stronger deceleration
                if distance_error > 0:
                    if distance_error > 10:
                        acceleration_cmd = max(acceleration_cmd, -4.0)
                    elif distance_error > 5:
                        acceleration_cmd = min(acceleration_cmd, -1.0)

                # Ensure we don't exceed acceleration limits
                acceleration_cmd = max(
                    self.max_deceleration,
                    min(self.max_acceleration, acceleration_cmd)
                )

        # Apply acceleration limits
        acceleration_cmd = max(
            self.max_deceleration,
            min(self.max_acceleration, acceleration_cmd)
        )

        return acceleration_cmd, mode, distance_error


def load_config(yaml_path):
    """Load configuration from YAML file."""
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    return config
