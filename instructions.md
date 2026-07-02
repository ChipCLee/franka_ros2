# Franka ROS2 Simulation & Control Instructions

This guide explains how to start the Franka ROS2 Gazebo/RViz simulation on the server (`nuc5`) and send movement commands in both **Joint Trajectory space** and **Cartesian space (X, Y, Z)**.

---

## 1. Start the VNC Server and Simulation

On the `nuc5` server, follow these steps to set up the graphical VNC display and launch the Docker container.

### Step A: Start the TigerVNC Server
Start the VNC server on display `:2` (port `5902`) and allow local connections:
```bash
# Start VNC Server
vncserver :2 -localhost no

# Disable access control to allow docker containers to output to display :2
DISPLAY=:2 xhost +
```

### Step B: Launch the Docker Simulation Container
Launch the docker container with the appropriate environment variables, display redirection, and hardware acceleration groups (`993` for `render` and `44` for `video`):
```bash
docker run --network host \
  --privileged \
  --cap-add=SYS_NICE \
  --ulimit rtprio=99 \
  --ulimit rttime=-1 \
  --device /dev/dri \
  --group-add 993 --group-add 44 \
  --name franka_sim \
  -e ROS_DOMAIN_ID=3 \
  -e DISPLAY=:2 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -d ghcr.io/rr-aa-cl/franka_ros2:humble \
  ros2 launch franka_gazebo_bringup gazebo_franka_arm_example_controller.launch.py controller:=joint_state_broadcaster load_gripper:=true
```
*VNC Connection String*: Connect to the GUI via VNC at `10.180.68.126:5902` using the password `pw4aios`.

---

## 2. Move the Robot Arm (Joint Trajectory Control)

We configured a position-based joint trajectory controller (`position_joint_trajectory_controller`) inside the container. 

### Step A: Load and Activate the Joint Trajectory Controller
Run these commands to load and activate the controller:
```bash
docker exec franka_sim /bin/bash -c "source /ros2_ws/install/setup.bash && \
  ros2 control load_controller position_joint_trajectory_controller && \
  ros2 control set_controller_state position_joint_trajectory_controller inactive && \
  ros2 control set_controller_state position_joint_trajectory_controller active"
```

### Step B: Send Joint Command
Publish a command to the `/position_joint_trajectory_controller/joint_trajectory` topic. The joint order is `[fr3_joint1, fr3_joint2, fr3_joint3, fr3_joint4, fr3_joint5, fr3_joint6, fr3_joint7]`:
```bash
docker exec franka_sim /bin/bash -c 'source /ros2_ws/install/setup.bash && \
  ros2 topic pub -1 /position_joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
  "{joint_names: [fr3_joint1, fr3_joint2, fr3_joint3, fr3_joint4, fr3_joint5, fr3_joint6, fr3_joint7], \
  points: [{positions: [0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785], time_from_start: {sec: 2, nanosec: 0}}]}"'
```

---

## 3. Move the Robot Arm in Cartesian Space (X, Y, Z)

To command the end effector (TCP) to move to a specific Cartesian location $(x, y, z)$, you have two main approaches:

### Option A: Interactive Control via MoveIt!
MoveIt! provides full Cartesian path planning and collision checking. You can launch MoveIt! with the simulation backend to command the robot in RViz:
1. Run the MoveIt! launch file in a new container:
   ```bash
   docker run --network host \
     --privileged \
     --name franka_moveit \
     -e DISPLAY=:2 \
     -v /tmp/.X11-unix:/tmp/.X11-unix \
     -d ghcr.io/rr-aa-cl/franka_ros2:humble \
     ros2 launch franka_fr3_moveit_config moveit.launch.py use_fake_hardware:=true
   ```
2. Open your VNC client (`10.180.68.126:5902`).
3. In the RViz GUI, drag the interactive orange/blue marker at the end-effector to the desired Cartesian coordinates $(x, y, z)$.
4. In the **Motion Planning** panel under the "Planning" tab, click **Plan and Execute**. The arm will automatically compute the Inverse Kinematics (IK) and move.

### Option B: Programmatic Control via Python script (IK)
You can compute Inverse Kinematics (IK) programmatically using libraries like `ikpy` or `pinocchio` inside Python, and publish the resulting joint angles to the `/position_joint_trajectory_controller/joint_trajectory` topic.

Here is an example Python script to compute joint configurations from $(x, y, z)$ and send the command:

```python
#!/usr/bin/env python3
import rclcpp
from rclcpp.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

# Example packages like ikpy or pinocchio can be used to solve:
# joints = inverse_kinematics(target_x, target_y, target_z)

class CartesianCommander(Node):
    def __init__(self):
        super().__init__('cartesian_commander')
        self.publisher = self.create_publisher(
            JointTrajectory, 
            '/position_joint_trajectory_controller/joint_trajectory', 
            10
        )
        
    def send_target_joints(self, target_positions):
        msg = JointTrajectory()
        msg.joint_names = [
            'fr3_joint1', 'fr3_joint2', 'fr3_joint3', 'fr3_joint4', 
            'fr3_joint5', 'fr3_joint6', 'fr3_joint7'
        ]
        
        point = JointTrajectoryPoint()
        point.positions = target_joints
        point.time_from_start = Duration(sec=3, nanosec=0)
        msg.points.append(point)
        
        self.publisher.publish(msg)
        self.get_logger().info('Commanded joint positions sent successfully!')

def main():
    rclcpp.init()
    node = CartesianCommander()
    
    # Example joint angles corresponding to a target Cartesian location
    # Replace these with your IK solver output
    target_joints = [0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785]
    
    node.send_target_joints(target_joints)
    rclcpp.shutdown()

if __name__ == '__main__':
    main()
```

---

## 4. How to Get the Current Pose (Joints & Cartesian Space)

To monitor or log the robot's current pose, you can read the joint angles directly or compute the Cartesian coordinate $(x, y, z)$ of the end effector.

### A. Get Current Joint Positions
You can read the active joint angles from the `/joint_states` topic:
```bash
docker exec franka_sim /bin/bash -c "source /ros2_ws/install/setup.bash && ros2 topic echo --once /joint_states"
```

### B. Get Current Cartesian Pose (X, Y, Z)
The Cartesian pose of the end-effector relative to the robot's base is broadcasted in the TF (Transform) tree. You can print the current coordinate $(x, y, z)$ and orientation (quaternion) by querying TF:
```bash
docker exec franka_sim /bin/bash -c "source /ros2_ws/install/setup.bash && ros2 run tf2_ros tf2_echo world fr3_hand"
```
*(Use `fr3_link0` instead of `world` if you want the coordinates relative to the arm's base plate rather than the simulation world).*

### C. Get Current Cartesian Pose via Python (TF Listener)
Here is an example Python snippet to query the end-effector transform in code:

```python
#!/usr/bin/env python3
import rclcpp
from rclcpp.node import Node
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

class TFListenerNode(Node):
    def __init__(self):
        super().__init__('tf_listener_node')
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Call query function periodically
        self.timer = self.create_timer(1.0, self.get_current_pose)

    def get_current_pose(self):
        try:
            # Lookup transform from world base to the end-effector (hand)
            t = self.tf_buffer.lookup_transform(
                'world',
                'fr3_hand',
                rclcpp.time.Time()
            )
            translation = t.transform.translation
            rotation = t.transform.rotation
            
            self.get_logger().info(
                f"Cartesian Pose:\n"
                f"  X: {translation.x:.4f}\n"
                f"  Y: {translation.y:.4f}\n"
                f"  Z: {translation.z:.4f}\n"
                f"  Orientation (qx, qy, qz, qw): "
                f"({rotation.x:.4f}, {rotation.y:.4f}, {rotation.z:.4f}, {rotation.w:.4f})"
            )
        except TransformException as ex:
            self.get_logger().warning(f"Could not transform: {ex}")

def main():
    rclcpp.init()
    node = TFListenerNode()
    try:
        rclcpp.spin(node)
    except KeyboardInterrupt:
        pass
    rclcpp.shutdown()

if __name__ == '__main__':
    main()
```

---

## 5. Switching from Simulation to a Real Robot

When you are ready to transition your control scripts from the Gazebo simulation to a physical Franka robot (e.g. FR3), follow these configurations:

### Step A: Start the Real Robot Driver
Instead of starting Gazebo via `franka_gazebo_bringup`, launch the hardware bringup driver using `franka_bringup` and supply the physical IP address of the robot:
```bash
docker run --network host \
  --privileged \
  --cap-add=SYS_NICE \
  --ulimit rtprio=99 \
  --ulimit rttime=-1 \
  --name franka_real \
  -e ROS_DOMAIN_ID=3 \
  -d ghcr.io/rr-aa-cl/franka_ros2:humble \
  ros2 launch franka_bringup franka.launch.py robot_ip:=192.168.3.100 robot_type:=fr3
```
*Note: Make sure to replace `robot_ip` with the actual IP address configured on your physical arm.*

### Step B: MoveIt! Launch for the Real Robot
To use MoveIt! for Cartesian planning on the real robot, launch it with `use_fake_hardware:=false` and provide the robot IP:
```bash
docker run --network host \
  --privileged \
  --name franka_moveit_real \
  -d ghcr.io/rr-aa-cl/franka_ros2:humble \
  ros2 launch franka_fr3_moveit_config moveit.launch.py robot_ip:=192.168.3.100 use_fake_hardware:=false
```

### Critical Requirements for Real Hardware
1. **Real-time Linux Kernel (PREEMPT_RT)**: 
   The host machine driving the physical robot MUST run a real-time kernel to avoid communication packet loss and safety shutdowns. (The `nuc5` server is already running a realtime kernel: `6.8.1-1046-realtime #47-Ubuntu SMP PREEMPT_RT`).
2. **Franka Control Interface (FCI)**:
   Verify that FCI is unlocked/active on the Franka Desk web interface, and the physical external activation key (safety button) is released.
3. **No GUI Redirection Required**:
   When driving the real robot without Gazebo, you do not need display variables (`DISPLAY=:2`) or render devices (`--device /dev/dri`) in your docker command, unless you still wish to visualize state output via RViz on VNC.

---

## 6. Mounting the Robot on a Table in the Simulation

Yes, it is possible to mount the robot on a table. In Gazebo/ROS2, you can achieve this using two common approaches:

### Method A: Modifying the URDF / Xacro description (Recommended)
You can define a table link directly in the robot description files so that the robot is mounted relative to the table surface rather than the world origin.

1. Open the description file inside the container workspace at `/ros2_ws/src/franka_description/robots/fr3/fr3.urdf.xacro` (cloned dynamically inside the container by the entrypoint import script).
2. Add a `table` link and attach it to the `world` link.
3. Attach the robot base (`fr3_link0`) to the top of the table instead of the `world` link:

```xml
<!-- Define the Table Link -->
<link name="table">
  <visual>
    <origin xyz="0 0 0.4" rpy="0 0 0"/>
    <geometry>
      <box size="1.0 2.0 0.8"/> <!-- 80cm tall table, 2.0m wide to cover workspace -->
    </geometry>
    <material name="wood">
      <color rgba="0.6 0.4 0.2 1.0"/>
    </material>
  </visual>
  <collision>
    <origin xyz="0 0 0.4" rpy="0 0 0"/>
    <geometry>
      <box size="1.0 2.0 0.8"/>
    </geometry>
  </collision>
</link>

<!-- Define Wall Link -->
<link name="wall">
  <visual>
    <origin xyz="0 0 0.5" rpy="0 0 0"/>
    <geometry>
      <box size="0.1 2.0 1.0"/> <!-- Balanced height of 1.0m to allow optimal robot mounting -->
    </geometry>
    <material name="gray">
      <color rgba="0.5 0.5 0.5 1.0"/>
    </material>
  </visual>
  <collision>
    <origin xyz="0 0 0.5" rpy="0 0 0"/>
    <geometry>
      <box size="0.1 2.0 1.0"/>
    </geometry>
  </collision>
</link>

<!-- Fix Table to World -->
<joint name="world_to_table" type="fixed">
  <parent link="world"/>
  <child link="table"/>
  <origin xyz="0 0 0" rpy="0 0 0"/>
</joint>

<!-- Fix Wall to Table -->
<joint name="table_to_wall" type="fixed">
  <parent link="table"/>
  <child link="wall"/>
  <origin xyz="-0.45 0 0.8" rpy="0 0 0"/>
</joint>

<!-- Fix Robot Base to Front surface of the Wall (rotated 90 degrees around Y axis) -->
<joint name="wall_to_robot" type="fixed">
  <parent link="wall"/>
  <child link="${modified_prefix}$(arg robot_type)_link0"/>
  <origin xyz="0.05 0 0.6" rpy="0 ${pi/2} 0"/> <!-- Balanced mounting of 0.6m high from table for clearance and reach -->
</joint>
```

### Method B: Spawning the Robot on top of a Table in the SDF World
Alternatively, you can load a table model inside the Gazebo SDF world file and specify a height offset when spawning the robot.

1. Create a custom world file (e.g., `table_world.sdf`) and add a table model inside it:
```xml
<model name="table">
  <static>true</static>
  <pose>0 0 0 0 0 0</pose>
  <link name="link">
    <collision name="collision">
      <geometry>
        <box>
          <size>1.0 1.0 0.8</size>
        </box>
      </geometry>
    </collision>
    <visual name="visual">
      <geometry>
        <box>
          <size>1.0 1.0 0.8</size>
        </box>
      </geometry>
    </visual>
  </link>
</model>
```
2. Modify your launch file to pass the custom world file to Gazebo Sim.
3. In the spawning node (the `ros_gz_sim` node in the launch file), pass the height offset as arguments to place the base of the arm on top of the table:
```python
spawn = Node(
    package='ros_gz_sim', executable='create',
    arguments=['-topic', '/robot_description', '-z', '0.8'], # Spawn 80cm above ground
    output='screen',
)
```

### Current Active Configuration in the Container
The running container `franka_sim` has already been configured with **Method A**. A `table` and a vertical `wall` have been defined, and the base of the robot arm has been mounted sideways on the wall facing forward ($x=-0.40, y=0.0, z=1.40$, rotated $90^\circ$ around the Y-axis).

* **How to Revert to a Standard (Table-less) Robot Arm:**
  If you ever need to restore the default single-robot configuration, run:
  ```bash
  # Revert the Xacro file modification
  docker exec franka_sim /bin/bash -c "cd /ros2_ws/src/franka_description && git checkout robots/fr3/fr3.urdf.xacro"

  # Restart the container to reload description
  docker stop franka_sim && docker start franka_sim
  ```

