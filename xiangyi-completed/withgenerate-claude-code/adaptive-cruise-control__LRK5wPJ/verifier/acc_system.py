"""
Adaptive Cruise Control System

Implements mode selection, distance calculation, and multi-mode control logic.
Supports three control modes: cruise, follow, and emergency.
"""

import numpy as np


class AdaptiveCruiseControl:
    """
    ACC system with multiple control modes and safety features.

    Control Modes:
        - 'cruise': Maintain set speed when no lead vehicle detected
        - 'follow': Maintain safe following distance when lead vehicle present
        - 'emergency': Maximum safe deceleration for collision avoidance

    The ACC system selects modes based on:
        - Presence of lead vehicle
        - Distance to lead vehicle
        - Time-to-collision (TTC)
        - Minimum safety distance
    """

    def __init__(self, config):
        """
        Initialize ACC system from configuration dictionary.

        Args:
            config (dict): Nested configuration dictionary with keys:
                - vehicle: Contains max_acceleration, max_deceleration
                - acc_settings: Contains set_speed, time_headway, min_gap,
                               emergency_ttc, min_distance
        """
        self.config = config
        self._extract_parameters()

    def _extract_parameters(self):
        """Extract and validate parameters from configuration."""
        # Vehicle dynamics parameters
        vehicle = self.config.get('vehicle', {})
        self.max_accel = float(vehicle.get('max_acceleration', 3.0))
        self.max_decel = float(vehicle.get('max_deceleration', -8.0))

        # ACC control parameters
        acc = self.config.get('acc_settings', {})
        self.set_speed = float(acc.get('set_speed', 30.0))
        self.time_headway = float(acc.get('time_headway', 1.5))
        self.min_gap = float(acc.get('min_gap', 10.0))
        self.ttc_threshold = float(acc.get('emergency_ttc', 3.0))
        self.min_distance = float(acc.get('min_distance', 5.0))

    def compute_safe_distance(self, ego_speed):
        """
        Calculate target following distance using time-headway model.

        Formula: d_safe = v * time_headway + min_gap

        Args:
            ego_speed (float): Current ego vehicle speed (m/s)

        Returns:
            float: Safe following distance (m)
        """
        return ego_speed * self.time_headway + self.min_gap

    def calculate_ttc(self, distance, ego_speed, lead_speed):
        """
        Calculate time-to-collision if gap is closing.

        Formula: TTC = distance / (ego_speed - lead_speed)

        Returns infinity if not closing gap.

        Args:
            distance (float): Current distance to lead vehicle (m)
            ego_speed (float): Ego vehicle speed (m/s)
            lead_speed (float): Lead vehicle speed (m/s)

        Returns:
            float: Time to collision in seconds, or infinity if not closing
        """
        relative_speed = ego_speed - lead_speed
        if relative_speed <= 0.001:  # Not closing gap (avoid division by near-zero)
            return float('inf')
        return distance / relative_speed

    def select_mode(self, ego_speed, lead_speed, distance):
        """
        Select ACC control mode based on current state.

        Mode selection logic:
        1. If no lead vehicle -> 'cruise'
        2. If TTC < threshold OR distance < min_distance -> 'emergency'
        3. Otherwise -> 'follow'

        Args:
            ego_speed (float): Current ego vehicle speed (m/s)
            lead_speed (float): Lead vehicle speed (m/s), or None
            distance (float): Current distance to lead vehicle (m), or None

        Returns:
            str: Control mode ('cruise', 'follow', or 'emergency')
        """
        # No lead vehicle - cruise at set speed
        if lead_speed is None:
            return 'cruise'

        # Lead vehicle present - check safety conditions
        ttc = self.calculate_ttc(distance, ego_speed, lead_speed)

        # Emergency braking if critical conditions
        if ttc < self.ttc_threshold or distance < self.min_distance:
            return 'emergency'

        # Normal following
        return 'follow'

    def compute(self, ego_speed, lead_speed, distance, speed_accel,
                distance_accel, dt):
        """
        Compute ACC control command for current state.

        Selects mode and applies appropriate control strategy:
        - Cruise: Use speed PID to reach set speed
        - Follow: Use distance PID to maintain safe gap
        - Emergency: Override with maximum safe deceleration

        Args:
            ego_speed (float): Current ego vehicle speed (m/s)
            lead_speed (float): Lead vehicle speed (m/s), or None
            distance (float): Current distance to lead vehicle (m), or None
            speed_accel (float): Acceleration from speed PID (m/s^2)
            distance_accel (float): Acceleration from distance PID (m/s^2)
            dt (float): Time step (s)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd (float): Clamped acceleration command (m/s^2)
                - mode (str): Selected control mode
                - distance_error (float): Distance tracking error, or None
        """
        # Determine control mode
        mode = self.select_mode(ego_speed, lead_speed, distance)

        # Compute control output based on mode
        if mode == 'cruise':
            # Speed control: accelerate/decelerate to set speed
            accel = speed_accel
            distance_error = None

        elif mode == 'follow':
            # Distance control: maintain safe following distance
            safe_dist = self.compute_safe_distance(ego_speed)
            distance_error = safe_dist - distance

            # Use distance PID for following
            accel = distance_accel

        else:  # mode == 'emergency'
            # Safety override: maximum safe deceleration
            accel = self.max_decel
            distance_error = None

        # Apply acceleration limits (hard constraints)
        accel = np.clip(accel, self.max_decel, self.max_accel)

        return accel, mode, distance_error

    def __repr__(self):
        """String representation of ACC system."""
        return (f"AdaptiveCruiseControl(set_speed={self.set_speed} m/s, "
                f"time_headway={self.time_headway}s, min_gap={self.min_gap}m)")
