import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
import rclpy
from rclpy.node import Node
from diagnostic_msgs.msg import KeyValue
from std_msgs.msg import Bool, String


class MqttRosBridgeNode(Node):
    is_connected = False
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
        self.create_subscriptions()
        self.get_logger().info("MQTT to ROS bridge node initialized.")
        self.is_connected = True

    def declare_parameters_ros(self):
        self.declare_parameter('TOPICS.hunter_position', '/hunter_position')
        self.declare_parameter('TOPICS.mqtt2ros', '/mqtt2ros')
        self.declare_parameter('TOPICS.ros2mqtt', '/ros2mqtt') 
        self.declare_parameter('TOPICS.initialize_hunter', '/initialize_hunter_params')
        self.declare_parameter('TOPICS.start_stop_hunter', '/start_stop_hunter')

    def create_params_dict(self):
        return {
            'mqtt2ros': self.get_parameter('TOPICS.mqtt2ros').value,
            'ros2mqtt': self.get_parameter('TOPICS.ros2mqtt').value,
            'hunter_position': self.get_parameter('TOPICS.hunter_position').value,
            'initialize_hunter': self.get_parameter('TOPICS.initialize_hunter').value,
            'start_stop_hunter': self.get_parameter('TOPICS.start_stop_hunter').value
        }       
    
    def create_publishers(self):
        self.publisher_hunter_position = self.create_publisher(
            String,
            self.params['hunter_position'],
            10
        )
        self.publisher_connection_status = self.create_publisher(
            Bool,
            '/connection_status',
            10
        )


        self.timer = self.create_timer(1.0, self.publish_connection_status)
    
    def publish_connection_status(self):
        self.publish_connection_status_msg = Bool()
        self.publish_connection_status_msg.data = self.is_connected
        self.publisher_connection_status.publish(self.publish_connection_status_msg)

    def create_subscriptions(self):
        self.subscription_initialize_hunter = self.create_subscription(
            KeyValue,
            self.params['initialize_hunter'],
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
        if key == self.params['hunter_position']:
            self.get_logger().info(f"Posición del hunter recibida: {msg.value}")
            self.publisher_hunter_position.publish(String(data=msg.value))

    def send_command(self, msg: KeyValue):
        self.get_logger().info(f"Comando recibido: {msg.key} - {msg.value}")
        self.pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    app = QApplication(sys.argv)
    node = MqttRosBridgeNode()
    rclpy.spin(node)
    node.get_logger().info("Shutting down MQTT to ROS bridge node.")
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()