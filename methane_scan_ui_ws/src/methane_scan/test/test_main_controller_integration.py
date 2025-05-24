import unittest
from unittest.mock import MagicMock
from methane_scan.controllers.main_controller import MainController

class TestMainControllerIntegration(unittest.TestCase):
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
        self.mock_robot = rc_patcher.start().return_value
        tc_patcher = unittest.mock.patch('methane_scan.controllers.tdlas_controller.TDLASController', autospec=True)
        self.addCleanup(tc_patcher.stop)
        self.mock_tdlas = tc_patcher.start().return_value
        pc_patcher = unittest.mock.patch('methane_scan.controllers.ptu_controller.PTUController', autospec=True)
        self.addCleanup(pc_patcher.stop)
        self.mock_ptu = pc_patcher.start().return_value

    def test_check_all_ready(self):
        controller = MainController(self.mock_node)
        # Simula todos los controladores listos
        self.mock_robot.check_Robot_ready.return_value = True
        self.mock_tdlas.check_TDLAS_ready.return_value = True
        self.mock_ptu.check_PTU_ready.return_value = True
        # Si existe el método check_all_ready, se puede probar aquí
        if hasattr(controller, 'check_all_ready'):
            result = controller.check_all_ready()
            self.assertTrue(result)

    def test_start_and_pause_test(self):
        controller = MainController(self.mock_node)
        # Si existen los métodos start_test y pause_test
        if hasattr(controller, 'start_test') and hasattr(controller, 'pause_test'):
            controller.start_test()
            controller.pause_test()
            # Aquí podrías comprobar efectos secundarios, logs, etc.

if __name__ == "__main__":
    unittest.main()
