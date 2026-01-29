"""Test the actual PID class."""

from pid_controller import PIDController

pid = PIDController(kp=4.0, ki=0.8, kd=1.0, output_limits=(-8.0, 3.0))

dt = 0.1
ego_speed = 0.0

print("Testing PID class directly:")
for i in range(200):
    t = i * dt
    error = 30.0 - ego_speed
    output = pid.compute(error, dt)
    ego_speed += output * dt
    ego_speed = max(0.0, ego_speed)

    if t < 15.0 and (t % 1.0 < 0.05 or (t > 8.0 and t < 12.0)):
        print(f"t={t:.1f}: err={error:.2f}, integral={pid.integral:.2f}, out={output:.2f}, ego={ego_speed:.2f}")
