import os
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config_file = os.path.join(os.path.dirname(__file__), 'parameters.yaml')
    return LaunchDescription([
        Node(
            package='methane_scan',
            executable='methane_scan_node',
            name='methane_scan_node',
            parameters=[config_file]
        ),
        Node(
            package='methane_scan',
            executable='mqtt_ros_bridge_node',
            name='mqtt_ros_bridge_node',
            parameters=[config_file],
        )
    ])
