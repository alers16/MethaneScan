import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import KeyValue
from std_msgs.msg import Bool, String


class MqttRosBridgeNode(Node):
    def __init__(self):
        super().__init__('mqtt_ros_bridge_node')
        self.declare_parameters_ros()
        self.params = self.create_params_dict()

        self.sub = self.create_subscription(
            KeyValue,
            self.params['mqtt2ros'],
            self.on_mqtt_msg,
            10
        )

        self.pub = self.create_publisher(
            KeyValue,
            self.params['ros2mqtt'],
            10
        )

        self.create_publishers()

    def declare_parameters_ros(self):
        self.declare_parameter('TOPICS.ptu_ready', '/PTU_ready')
        self.declare_parameter('TOPICS.hunter_position', '/hunter_position')
        self.declare_parameter('TOPICS.tdlas_ready', '/TDLAS_ready')
        self.declare_parameter('TOPICS.tdlas_data', '/TDLAS_data')
        self.declare_parameter('TOPICS.end_simulation', '/end_simulation')
        self.declare_parameter('TOPICS.ptu_position', '/PTU_position')
        self.declare_parameter('TOPICS.mqtt2ros', '/mqtt2ros')
        self.declare_parameter('TOPICS.ros2mqtt', '/ros2mqtt') 
        self.declare_parameter('TOPICS.initialize_hunter', '/initialize_hunter')
        self.declare_parameter('TOPICS.start_hunter', '/start_simulation')
        self.declare_parameter('TOPICS.start_stop_hunter', '/start_stop_value')

    def create_params_dict(self):
        return {
            'mqtt2ros': self.get_parameter('TOPICS.mqtt2ros').value,
            'ros2mqtt': self.get_parameter('TOPICS.ros2mqtt').value,
            'ptu_ready': self.get_parameter('TOPICS.ptu_ready').value,
            'hunter_position': self.get_parameter('TOPICS.hunter_position').value,
            'tdlas_ready': self.get_parameter('TOPICS.tdlas_ready').value,
            'tdlas_data': self.get_parameter('TOPICS.tdlas_data').value,
            'end_simulation': self.get_parameter('TOPICS.end_simulation').value,
            'ptu_position': self.get_parameter('TOPICS.ptu_position').value
        }       
    
    def create_publishers(self):
        self.publisher_ptu_ready = self.create_publisher(
            Bool,
            self.params['ptu_ready'],
            10
        )
        self.publisher_hunter_position = self.create_publisher(
            String,
            self.params['hunter_position'],
            10
        )
        self.publisher_tdlas_ready = self.create_publisher(
            Bool,
            self.params['tdlas_ready'],
            10
        )
        self.publisher_tdlas_data = self.create_publisher(
            String,
            self.params['tdlas_data'],
            10
        )
        self.publisher_end_simulation = self.create_publisher(
            Bool,
            self.params['end_simulation'],
            10
        )
        self.publisher_ptu_position = self.create_publisher(
            String,
            self.params['ptu_position'],
            10
        )
    
    def creater_subscriptions(self):
        self.subscription_initialize_hunter = self.create_subscription(
            KeyValue,
            self.params['initialize_hunter'],
            self.send_command,
            10
        )
        self.subscription_start_hunter = self.create_subscription(
            KeyValue,
            self.params['start_hunter'],
            self.send_command,
            10
        )
        self.subscription_start_stop_hunter = self.create_subscription(
            KeyValue,
            self.params['start_stop_hunter'],
            self.send_command,
            10
        )

    def on_mqtt_msg(self, msg: KeyValue):
        key = msg.key
        if key == self.params['ptu_ready']:
            self.get_logger().info(f"PTU ready recibido: {msg.value}")
            self.publisher_tdlas_ready.publish(Bool(data=msg.value == 'True'))
        elif key == self.params['hunter_position']:
            self.get_logger().info(f"Posición del hunter recibida: {msg.value}")
            self.publisher_hunter_position.publish(String(data=msg.value))
        elif key == self.params['tdlas_ready']:
            self.get_logger().info(f"TDLAS ready recibido: {msg.value}")
            self.publisher_tdlas_ready.publish(Bool(data=msg.value == 'True'))
        elif key == self.params['tdlas_data']:
            self.get_logger().info(f"Datos de TDLAS recibidos: {msg.value}")
            self.publisher_tdlas_data.publish(String(data=msg.value))
        elif key == self.params['end_simulation']:
            self.get_logger().info(f"Fin de simulación recibido: {msg.value}")
            self.publisher_end_simulation.publish(Bool(data=msg.value == 'True'))
        elif key == self.params['ptu_position']:
            self.get_logger().info(f"Posición de PTU recibida: {msg.value}")
            self.publisher_ptu_position.publish(String(data=msg.value))

    def send_command(self, msg: KeyValue):
        self.get_logger().info(f"Comando recibido: {msg.key} - {msg.value}")
        self.pub.publish(msg)