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
        
        # Flag to track if cleanup has been performed
        self._cleanup_done = False

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
    
    def cleanup(self):
        """Safely clean up node resources"""
        if self._cleanup_done:
            self.get_logger().debug('Cleanup already performed, skipping')
            return

        try:
            # Cancel timers first
            if hasattr(self, 'timer') and self.timer:
                self.get_logger().debug('Canceling status timer')
                self.timer.cancel()
                self.timer = None
                
            if hasattr(self, 'timer_hunter') and self.timer_hunter:
                self.get_logger().debug('Canceling hunter timer')
                self.timer_hunter.cancel()
                self.timer_hunter = None
                
            # Mark cleanup as done
            self._cleanup_done = True
            self.get_logger().info('Node resources cleaned up successfully')
        except Exception as e:
            self.get_logger().error(f'Error during cleanup: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = PTUReadyPublisher()
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node:
            node.get_logger().info("Interrupción por teclado, cerrando nodo...")
    except Exception as e:
        if node:
            node.get_logger().error(f"Error inesperado: {str(e)}")
    finally:
        # Perform orderly shutdown
        shutdown_ros(node)

def shutdown_ros(node):
    """Perform a clean and orderly ROS shutdown sequence"""
    if node is None:
        return
        
    try:
        # First clean up the node's resources
        node.cleanup()
            
        # Then destroy the node
        node.get_logger().info("Destroying node...")
        node.destroy_node()
    except Exception as e:
        print(f"Error during node cleanup: {str(e)}")
    
    try:
        # Finally shut down rclpy
        print("Shutting down ROS client...")
        rclpy.shutdown()
    except Exception as e:
        print(f"Error during ROS shutdown: {str(e)}")

if __name__ == '__main__':
    main()
