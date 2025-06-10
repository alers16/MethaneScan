import pytest

def test_update_TDLAS_ready_sets_flag(tdlas_controller):
    tdlas_controller.update_TDLAS_ready(True)
    assert tdlas_controller.TDLAS_ready is True


def test_tdlascontroller_none_flag(tdlas_controller):
    """update_TDLAS_ready() with None should log a warning."""
    tdlas_controller.update_TDLAS_ready(None)
    tdlas_controller.node.get_logger().warn.assert_called_once_with("Received null TDLAS_ready status")
    assert tdlas_controller.TDLAS_ready is False  # Should not change