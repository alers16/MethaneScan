import unittest
from unittest.mock import MagicMock
from methane_scan.mqtt_ros_bridge_node import MQTTROSBridgeNode

class TestMQTTROSBridgeNode(unittest.TestCase):
    def setUp(self):
        # Mock ROS2 node base
        self.mock_node = MagicMock()
        with unittest.mock.patch('rclpy.node.Node.__init__', return_value=None):
            self.node = MQTTROSBridgeNode()

    def test_signal_emission(self):
        if hasattr(self.node, 'publisher'):
            self.node.publisher.publish = MagicMock()
            self.node.emit_signal('test')
            self.node.publisher.publish.assert_called()

    def test_subscription_callback(self):
        if hasattr(self.node, 'callback'):
            msg = MagicMock()
            self.node.callback(msg)
            # Aquí podrías comprobar efectos secundarios

if __name__ == "__main__":
    unittest.main()
