"""Adaptive Cruise Control System Implementation"""

from pid_controller import PIDController


class AdaptiveCruiseControl:
    """
    Adaptive Cruise Control (ACC) system that manages vehicle speed and following distance.

    The ACC operates in three modes:
    - cruise: Maintain set speed when no lead vehicle is detected
    - follow: Maintain safe following distance when lead vehicle is present
    - emergency: Emergency braking when Time-To-Collision (TTC) is critically low
    """

    def __init__(self, config):
        """
        Initialize ACC system with configuration.

        Args:
            config: Nested dictionary from vehicle_params.yaml containing:
                - acc_settings: set_speed, time_headway, min_distance, emergency_ttc_threshold
                - vehicle: max_acceleration, max_deceleration
                - pid_speed: kp, ki, kd for speed controller
                - pid_distance: kp, ki, kd for distance controller
        """
        # ACC settings
        self.set_speed = config['acc_settings']['set_speed']
        self.time_headway = config['acc_settings']['time_headway']
        self.min_distance = config['acc_settings']['min_distance']
        self.emergency_ttc_threshold = config['acc_settings']['emergency_ttc_threshold']

        # Vehicle constraints
        self.max_acceleration = config['vehicle']['max_acceleration']
        self.max_deceleration = config['vehicle']['max_deceleration']

        # PID controllers
        self.speed_controller = PIDController(
            config['pid_speed']['kp'],
            config['pid_speed']['ki'],
            config['pid_speed']['kd']
        )

        self.distance_controller = PIDController(
            config['pid_distance']['kp'],
            config['pid_distance']['ki'],
            config['pid_distance']['kd']
        )

    def compute(self, ego_speed, lead_speed, distance, dt):
        """
        Compute acceleration command based on current state.

        Args:
            ego_speed: Current speed of ego vehicle (m/s)
            lead_speed: Speed of lead vehicle (m/s), or None if no lead vehicle
            distance: Distance to lead vehicle (m), or None if no lead vehicle
            dt: Time step (seconds)

        Returns:
            tuple: (acceleration_cmd, mode, distance_error)
                - acceleration_cmd: Commanded acceleration (m/s^2)
                - mode: Operating mode ('cruise', 'follow', or 'emergency')
                - distance_error: Distance error in follow mode, None otherwise
        """
        # Cruise mode: No lead vehicle detected
        if lead_speed is None or distance is None:
            mode = 'cruise'
            speed_error = self.set_speed - ego_speed
            acceleration_cmd = self.speed_controller.compute(speed_error, dt)
            distance_error = None

        else:
            # Calculate Time-To-Collision (TTC)
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
            else:
                ttc = float('inf')

            # Emergency mode: TTC below threshold
            if ttc < self.emergency_ttc_threshold:
                mode = 'emergency'
                # Apply maximum deceleration
                acceleration_cmd = self.max_deceleration
                distance_error = None

            # Follow mode: Maintain safe following distance
            else:
                mode = 'follow'
                # Desired distance based on time headway
                desired_distance = self.min_distance + self.time_headway * ego_speed
                distance_error = distance - desired_distance

                # Use distance controller to directly compute acceleration
                # Positive distance_error means we're too far, need to speed up
                # Negative distance_error means we're too close, need to slow down
                distance_accel = self.distance_controller.compute(distance_error, dt)

                # Also consider relative velocity for smoother following
                relative_velocity = ego_speed - lead_speed
                velocity_accel = self.speed_controller.compute(-relative_velocity, dt)

                # Combine both controls
                acceleration_cmd = distance_accel + velocity_accel

                # If we're above set speed and distance is good, don't accelerate further
                if ego_speed > self.set_speed and distance_error > 0:
                    acceleration_cmd = min(0, acceleration_cmd)

        # Clamp acceleration to vehicle limits
        acceleration_cmd = max(self.max_deceleration, min(self.max_acceleration, acceleration_cmd))

        return acceleration_cmd, mode, distance_error
