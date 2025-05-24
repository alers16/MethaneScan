import unittest
from unittest.mock import MagicMock
from methane_scan.controllers.main_controller import MainController

class TestMainController(unittest.TestCase):
    def setUp(self):
        # Mock ROS2 node
        self.mock_node = MagicMock()
        # Patch MainWindow to avoid GUI instantiation
        patcher = unittest.mock.patch('methane_scan.views.main_window.MainWindow', autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_mainwindow = patcher.start()
        # Patch controllers to avoid their side effects
        rc_patcher = unittest.mock.patch('methane_scan.controllers.robot_controller.RobotController', autospec=True)
        self.addCleanup(rc_patcher.stop)
        rc_patcher.start()
        tc_patcher = unittest.mock.patch('methane_scan.controllers.tdlas_controller.TDLASController', autospec=True)
        self.addCleanup(tc_patcher.stop)
        tc_patcher.start()
        pc_patcher = unittest.mock.patch('methane_scan.controllers.ptu_controller.PTUController', autospec=True)
        self.addCleanup(pc_patcher.stop)
        pc_patcher.start()

    def test_initialization_success(self):
        controller = MainController(self.mock_node)
        self.assertTrue(controller.initialized)
        self.mock_node.get_logger().info.assert_called_with("MainController initialized successfully")

    def test_initialization_failure(self):
        # Simula excepción en MainWindow
        with unittest.mock.patch('methane_scan.views.main_window.MainWindow', side_effect=Exception("fail")):
            controller = MainController(self.mock_node)
            self.assertFalse(controller.initialized)
            self.mock_node.get_logger().error.assert_called()

if __name__ == "__main__":
    unittest.main()
