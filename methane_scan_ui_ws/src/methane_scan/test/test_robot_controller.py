import unittest
from unittest.mock import MagicMock
from methane_scan.controllers.robot_controller import RobotController

class TestRobotController(unittest.TestCase):
    def setUp(self):
        self.mock_node = MagicMock()
        self.mock_view = MagicMock()
        self.controller = RobotController(self.mock_node, self.mock_view)

    def test_init_parameters(self):
        self.controller._init_parameters()
        self.assertIsNone(self.controller.robot_speed)
        self.assertIsNone(self.controller.robot_position)
        self.assertFalse(self.controller.robot_configured)
        self.assertEqual(self.controller.path, [])

    def test_update_robot_speed_no_change(self):
        self.controller.robot_speed = 1.0
        with unittest.mock.patch.object(self.controller, 'check_Robot_ready') as mock_check_ready:
            self.controller.update_robot_speed(1.0)
            mock_check_ready.assert_not_called()
            self.mock_node.get_logger().info.assert_called_with("No change in robot speed")

if __name__ == "__main__":
    unittest.main()
