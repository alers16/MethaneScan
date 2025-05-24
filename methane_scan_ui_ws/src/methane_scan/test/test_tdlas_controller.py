import unittest
from unittest.mock import MagicMock
from methane_scan.controllers.tdlas_controller import TDLASController

class TestTDLASController(unittest.TestCase):
    def setUp(self):
        self.mock_node = MagicMock()
        self.mock_view = MagicMock()
        self.controller = TDLASController(self.mock_node, self.mock_view)

    def test_init_parameters(self):
        self.controller._init_parameters()
        self.assertFalse(self.controller.TDLAS_ready)

    def test_update_TDLAS_ready_none(self):
        with unittest.mock.patch.object(self.controller, 'check_TDLAS_ready') as mock_check_ready:
            self.controller.update_TDLAS_ready(None)
            mock_check_ready.assert_not_called()
            self.mock_node.get_logger().warn.assert_called_with("Received null TDLAS_ready status")

if __name__ == "__main__":
    unittest.main()
