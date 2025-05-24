import unittest
from unittest.mock import MagicMock
from methane_scan.controllers.ptu_controller import PTUController

class TestPTUController(unittest.TestCase):
    def setUp(self):
        self.mock_node = MagicMock()
        self.mock_view = MagicMock()
        self.controller = PTUController(self.mock_node, self.mock_view)

    def test_init_parameters(self):
        self.controller._init_parameters()
        self.assertIsNone(self.controller.PTU_position)
        self.assertFalse(self.controller.PTU_ready)
        self.assertFalse(self.controller.ptu_configured)
        self.assertIsNone(self.controller.last_ptu_position)

    def test_update_ptu_position_none(self):
        # Si la posición es None, no debe actualizar nada
        with unittest.mock.patch.object(self.controller, 'check_publish') as mock_check_publish:
            with unittest.mock.patch.object(self.controller, 'check_PTU_ready') as mock_check_ready:
                self.controller.update_ptu_position(None)
                mock_check_publish.assert_not_called()
                mock_check_ready.assert_not_called()

if __name__ == "__main__":
    unittest.main()
