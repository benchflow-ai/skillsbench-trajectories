"""Adaptive Cruise Control system implementation."""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """ACC system that manages speed control and safe following distance."""

    def __init__(self, config):
        """
        Initialize ACC system.

        Args:
            config: Configuration dictionary with nested keys from vehicle_params.yaml
                   e.g., config['acc_settings']['set_speed']
        """
        # Extract ACC settings
        self.set_speed = config["acc_settings"]["set_speed"]
        self.time_headway = config["acc_settings"]["time_headway"]
        self.min_distance = config["acc_settings"]["min_distance"]
        self.emergency_ttc_threshold = config["acc_settings"]["emergency_ttc_threshold"]

        # Vehicle constraints
        self.max_accel = config["vehicle"]["max_acceleration"]
        self.max_decel = config["vehicle"]["max_deceleration"]

        # Initialize PID controllers
        pid_speed_cfg = config.get("pid_speed", {})
        pid_distance_cfg = config.get("pid_distance", {})

        self.pid_speed = PIDController(
            kp=pid_speed_cfg.get("kp", 0.1),
            ki=pid_speed_cfg.get("ki", 0.01),
            kd=pid_speed_cfg.get("kd", 0.0),
        )

        self.pid_distance = PIDController(
            kp=pid_distance_cfg.get("kp", 0.1),
            ki=pid_distance_cfg.get("ki", 0.01),
            kd=pid_distance_cfg.get("kd", 0.0),
        )

        self.mode = "cruise"
        self._prev_mode = None

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command for ACC.

        Args:
            ego_speed: Current ego vehicle speed (m/s)
            lead_speed: Lead vehicle speed (m/s) or None if no lead vehicle
            distance: Distance to lead vehicle (m) or None if no lead vehicle
            dt: Time step in seconds

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                   acceleration_cmd: Command acceleration (m/s^2)
                   mode: Operating mode ('cruise', 'follow', or 'emergency')
                   distance_error: Distance error from desired spacing (m)
        """
        distance_error = None

        if lead_speed is None or distance is None:
            # No lead vehicle detected - cruise at set speed
            self.mode = "cruise"
            speed_error = self.set_speed - ego_speed
            accel_cmd = self.pid_speed.compute(speed_error, dt)
            distance_error = None
        else:
            # Lead vehicle detected - check for emergency condition
            if ego_speed > 0:
                ttc = distance / (ego_speed - lead_speed) if (ego_speed > lead_speed) else float('inf')
            else:
                ttc = float('inf')

            if ttc < self.emergency_ttc_threshold and ego_speed > lead_speed:
                # Emergency braking
                self.mode = "emergency"
                accel_cmd = self.max_decel
            else:
                # Follow mode - maintain safe distance and match lead speed
                self.mode = "follow"

                # Reset controllers when switching modes
                if self._prev_mode != "follow":
                    self.pid_speed.reset()
                    self.pid_distance.reset()
                self._prev_mode = self.mode

                # Calculate desired distance: min_distance + time_headway * ego_speed
                desired_distance = self.min_distance + self.time_headway * ego_speed

                # Distance error (positive means too close)
                distance_error = desired_distance - distance

                # Speed error relative to lead vehicle
                speed_error = lead_speed - ego_speed

                # Primary: match lead vehicle speed (strong control)
                speed_accel = self.pid_speed.compute(speed_error, dt)

                # Secondary: maintain safe distance (weaker control)
                distance_accel = self.pid_distance.compute(distance_error, dt)

                # Combine: primarily follow lead speed, distance as additional constraint
                # If too close (distance_error > 0), prioritize deceleration
                if distance_error > 0:
                    accel_cmd = min(speed_accel, distance_accel)
                else:
                    accel_cmd = 0.85 * speed_accel + 0.15 * distance_accel

        # Clamp acceleration to physical limits
        accel_cmd = max(self.max_decel, min(self.max_accel, accel_cmd))

        return accel_cmd, self.mode, distance_error
