import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.actions import TimerAction

def generate_launch_description():
    # Paths a ficheros de parámetros
    config_file      = os.path.join(os.path.dirname(__file__), 'parameters.yaml')
    mqtt_config_file = os.path.join(os.path.dirname(__file__), 'mqtt_parameters.yaml')
    bridge_params    = os.path.join(
        get_package_share_directory('mqtt_bridge'),
        'launch',
        'mqtt_basic_robot.yaml'
    )

    # 1) Nodo que queremos que arranque primero
    methane_node = Node(
        package='methane_scan',
        executable='methane_scan_node',
        name='methane_scan_node',
        output='screen',
        parameters=[config_file]
    )

    # 2) Los nodos que esperamos lanzar tras methane_scan_node
    mqtt_bridge_node = Node(
        package='mqtt_bridge',
        executable='mqtt_bridge_node',
        name='mqtt_bridge',
        output='screen',
        prefix='xterm -e',
        parameters=[bridge_params]
    )
    mqtt_ros_bridge_node = Node(
        package='methane_scan',
        executable='mqtt_ros_bridge_node',
        name='mqtt_ros_bridge_node',
        output='screen',
        prefix='xterm -e',
        parameters=[mqtt_config_file],
    )

    # 3) Event handler: cuando methane_node realice OnProcessStart, lanza los otros tras 2 segundos
    delayed_launch = RegisterEventHandler(
        OnProcessStart(
            target_action=methane_node,
            on_start=[
                TimerAction(
                    period=2.0,
                    actions=[mqtt_bridge_node, mqtt_ros_bridge_node]
                )
            ]
        )
    )

    return LaunchDescription([
        # Para que los logs salgan inmediatamente
        SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1'),

        DeclareLaunchArgument(
            "log_level",
            default_value=["info"],  #debug, info
            description="Logging level",
        ),

        # 1) methane_scan_node
        methane_node,

        # 2) el handler que lanza los demás tras arrancar el anterior
        delayed_launch,
    ])
