"""Test PID controller behavior"""

from pid_controller import PIDController

# Test with different gains
test_configs = [
    (0.1, 0.01, 0.0, "Original"),
    (0.15, 0.02, 0.05, "Low D"),
    (0.2, 0.03, 0.1, "Medium D"),
]

for kp, ki, kd, label in test_configs:
    print(f"\n{'='*50}")
    print(f"Testing: {label}")
    print(f"Gains: kp={kp}, ki={ki}, kd={kd}\n")

    pid = PIDController(kp, ki, kd)
    dt = 0.1
    set_speed = 30.0
    ego_speed = 0.0

    for i in range(100):
        time = i * dt
        error = set_speed - ego_speed

        accel = pid.compute(error, dt, output_limits=(-8.0, 3.0))

        if i < 15 or i % 10 == 0:
            print(f"t={time:.1f}s: speed={ego_speed:.2f}, error={error:.2f}, accel={accel:.2f}")

        # Update speed
        ego_speed += accel * dt
        ego_speed = max(0, ego_speed)

        if abs(error) < 0.5 and abs(accel) < 0.5:
            print(f"t={time:.1f}s: CONVERGED at speed={ego_speed:.2f}")
            break
