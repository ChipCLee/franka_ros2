#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import math
import time

class CircleTrajectoryPublisher(Node):
    def __init__(self):
        super().__init__('circle_trajectory_publisher')
        self.publisher = self.create_publisher(
            JointTrajectory,
            '/position_joint_trajectory_controller/joint_trajectory',
            10
        )
        self.get_logger().info("Circle Trajectory Publisher started. Drawing circle infinitely...")

    def publish_circle(self):
        msg = JointTrajectory()
        msg.joint_names = [
            'fr3_joint1', 'fr3_joint2', 'fr3_joint3', 'fr3_joint4', 
            'fr3_joint5', 'fr3_joint6', 'fr3_joint7'
        ]
        
        num_points = 50
        duration_per_circle = 5.0  # seconds
        
        for i in range(num_points + 1):
            angle = (2.0 * math.pi * i) / num_points
            
            # Oscillate joints in quadrature to draw a circle/ellipse
            joint1 = 0.3 * math.cos(angle)
            joint2 = -0.4 + 0.08 * math.sin(angle)  # Shifted up
            joint3 = 0.0
            joint4 = -1.8 + 0.08 * math.sin(angle)  # Kept bent
            joint5 = 0.0
            joint6 = 1.571 + 0.05 * math.cos(angle)
            joint7 = 0.785
            
            point = JointTrajectoryPoint()
            point.positions = [joint1, joint2, joint3, joint4, joint5, joint6, joint7]
            
            # Calculate time from start for this point
            t_sec = (duration_per_circle * i) / num_points
            sec = int(t_sec)
            nanosec = int((t_sec - sec) * 1e9)
            point.time_from_start = Duration(sec=sec, nanosec=nanosec)
            
            msg.points.append(point)
            
        self.publisher.publish(msg)
        self.get_logger().info("Published a full circle trajectory.")

def main():
    rclpy.init()
    node = CircleTrajectoryPublisher()
    
    try:
        while rclpy.ok():
            node.publish_circle()
            # Sleep for 5 seconds (the duration of the circle trajectory)
            # to let the robot execute the movement before sending the next one
            time.sleep(5.0)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
