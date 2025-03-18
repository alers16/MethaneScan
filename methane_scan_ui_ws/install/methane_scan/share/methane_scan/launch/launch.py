import os
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='methane_scan',
            executable='methane_scan_node',
            name='methane_scan_node'
        )
    ])
