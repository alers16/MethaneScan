import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
import json

class PTUReadyPublisher(Node):
    def __init__(self):
        super().__init__('ptu_ready_publisher')
        # Creamos el publisher para el tópico /PTU_ready
        self.publisher_ = self.create_publisher(Bool, '/PTU_ready', 10)
        # Timer para publicar a 1 Hz (cada segundo)
        self.timer = self.create_timer(20.0, self.publish_status)

        self.publisher_hunter = self.create_publisher(String, '/hunter_position', 10)
        self.timer_hunter = self.create_timer(20.0, self.publish_hunter)

    def publish_status(self):
        msg = Bool()
        # Aquí defines el valor booleano que quieres publicar
        msg.data = True  # Puedes cambiarlo a False según tus necesidades
        self.publisher_.publish(msg)
        self.get_logger().info(f'Publicado /PTU_ready: {msg.data}')

    def publish_hunter(self):
        msg = String()
        data = {"lat": 36.71593, "lng": -4.478058}
        msg.data = json.dumps(data)
        self.publisher_hunter.publish(msg)
        self.get_logger().info(f'Publicado /hunter_position: {msg.data}')

def main(args=None):
    rclpy.init(args=args)
    node = PTUReadyPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Interrupción por teclado, cerrando nodo...")
    except Exception as e:
        node.get_logger().error(f"Error inesperado: {str(e)}")
    finally:
        # Clean up timer resources
        if hasattr(node, 'timer') and node.timer:
            node.timer.cancel()
        if hasattr(node, 'timer_hunter') and node.timer_hunter:
            node.timer_hunter.cancel()
        
        # First destroy the node
        node.destroy_node()
        
        # Then shutdown rclpy
        rclpy.shutdown()

if __name__ == '__main__':
    main()
