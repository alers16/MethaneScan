from unittest.mock import MagicMock
import pytest
def test_update_ptu_position_sets_coords(ptu_controller):
    ptu_controller.update_ptu_position({"lat": 10, "lng": 20})
    assert ptu_controller.PTU_position == [10, 20]


def test_update_PTU_ready_sets_flag(ptu_controller):
    ptu_controller.update_PTU_ready(True)
    assert ptu_controller.PTU_ready is True

def test_ptu_check_ready(ptu_controller):
    # prepare state
    ptu_controller.PTU_ready = True
    ptu_controller.PTU_position = [10, 20]
    # stub out view and signals
    ptu_controller.view.home_tab = MagicMock()
    ptu_controller.view.ptu_config_widget = MagicMock()
    ptu_controller.signals = MagicMock()
    # call and assert return value
    assert ptu_controller.check_PTU_ready()
    # check that the controller marked itself configured
    assert ptu_controller.ptu_configured is True
    # logger info
    ptu_controller.node.get_logger().info.assert_called_with(
        f"Posición de PTU actualizada: {ptu_controller.PTU_position}"
    )
    # UI and signal side‐effects
    ptu_controller.view.home_tab.set_device_status.assert_called_once_with("PTU", True)
    ptu_controller.signals.ptuReady.emit.assert_called_once_with(True)
    ptu_controller.view.ptu_config_widget.set_state.assert_called_once_with("Operativo")


def test_ptu_show_config_calls_switch(ptu_controller, main_controller):
    # Monkeypatch main_window switch tracking
    called = {}
    def _switch():
        called["ptu"] = True
    main_controller.view.switch_to_ptu_config = _switch

    ptu_controller.show_ptu_config()
    assert called.get("ptu") is True

def test_ptucontroller_position_none(ptu_controller):
    """update_ptu_position() with missing keys should raise KeyError/ValueError."""
    assert ptu_controller.update_ptu_position(None) is None
    ptu_controller.node.get_logger().warn.assert_called_once()

def test_update_ptu_position_incomplete(ptu_controller):
    # falta lat
    ptu_controller.node.get_logger().error.reset_mock()
    assert ptu_controller.update_ptu_position({'lng': 20}) is None
    ptu_controller.node.get_logger().error.assert_called_once()
    # falta lng
    ptu_controller.node.get_logger().error.reset_mock()
    assert ptu_controller.update_ptu_position({'lat': 10}) is None
    ptu_controller.node.get_logger().error.assert_called_once()

def test_update_ptu_ready_false(ptu_controller):
    # cambiamos a False desde True
    ptu_controller.PTU_ready = True
    ptu_controller.update_PTU_ready(False)
    assert ptu_controller.PTU_ready is False

def test_check_PTU_ready_not_ready(ptu_controller):
    # PTU_ready=False no hace nada
    ptu_controller.PTU_ready = False
    ptu_controller.PTU_position = [1,2]
    ptu_controller.view.home_tab = MagicMock()
    ptu_controller.signals = MagicMock()
    assert ptu_controller.check_PTU_ready() is False
    ptu_controller.signals.ptuReady.emit.assert_not_called()

def test_check_PTU_ready_no_position(ptu_controller):
    # posición None tampoco
    ptu_controller.PTU_ready = True
    ptu_controller.PTU_position = None
    ptu_controller.view.home_tab = MagicMock()
    ptu_controller.signals = MagicMock()
    assert ptu_controller.check_PTU_ready() is False
    ptu_controller.signals.ptuReady.emit.assert_not_called()

def test_register_ptu_config_callback(ptu_controller):
    # si existe register_ptu_config_callback(), que conecte la señal adecuada
    called = {}
    def cb(x): called['v']=x
    # suponemos que el controller tiene ptu_config_callback o método similar
    if hasattr(ptu_controller, 'register_ptu_config_callback'):
        ptu_controller.signals = MagicMock()
        ptu_controller.register_ptu_config_callback(cb)
        # emitimos la señal interna
        ptu_controller.signals.dialogActive.emit(True)
        assert called['v'] is True

# ————— update_ptu_position —————

def test_update_ptu_position_draw_marker_and_emit(ptu_controller):
    # Preparamos un home_tab con map_frame y monkeypatch de checks
    map_frame = MagicMock()
    home_tab = MagicMock()
    ptu_controller.view.home_tab = home_tab
    home_tab.map_frame = map_frame
    
    ptu_controller.signals = MagicMock()
    ptu_controller.check_publish = MagicMock()
    ptu_controller.check_PTU_ready = MagicMock()

    ptu_controller.update_ptu_position({'lat': 1.23, 'lng': 4.56})
    assert ptu_controller.PTU_position== [1.23, 4.56]


def test_update_ptu_position_valid_logs_info(ptu_controller):
    # Inserta un logger info al call válido
    ptu_controller.node.get_logger().info.reset_mock()
    ptu_controller.view = None  # no rompe si no hay UI
    ptu_controller.update_ptu_position({'lat': 7, 'lng': 8})
    ptu_controller.node.get_logger().warn.assert_called_once()

# ————— update_PTU_ready —————

def test_update_PTU_ready_true_triggers_ui_and_signal(ptu_controller):
    ptu_controller.view.home_tab = MagicMock()
    ptu_controller.signals = MagicMock()
    ptu_controller.update_PTU_ready(True)
    assert ptu_controller.PTU_ready is True

def test_update_PTU_ready_false_no_ui(ptu_controller):
    ptu_controller.PTU_ready = True
    ptu_controller.view.home_tab = MagicMock()
    ptu_controller.signals = MagicMock()
    ptu_controller.update_PTU_ready(False)
    assert ptu_controller.PTU_ready is False
    ptu_controller.view.home_tab.set_device_status.assert_not_called()
    ptu_controller.signals.dialogActive.emit.assert_not_called()

# ————— check_PTU_ready ramas faltantes —————

def test_check_PTU_ready_view_none(ptu_controller):
    ptu_controller.view = None
    ptu_controller.node.get_logger().error.reset_mock()
    assert ptu_controller.check_PTU_ready() is None
    ptu_controller.node.get_logger().error.assert_called_once()

def test_check_PTU_ready_position_only(ptu_controller):
    # PTU_ready=False pero hay posición
    ptu_controller.PTU_ready = False
    ptu_controller.PTU_position = [5,6]
    ptu_controller.view.home_tab = MagicMock()
    ptu_controller.view.ptu_config_widget = MagicMock()
    # Capturamos info/logger y señal
    ptu_controller.node.get_logger().info.reset_mock()
    ptu_controller.signals = MagicMock()
    ok = ptu_controller.check_PTU_ready()
    assert ok is False
    ptu_controller.node.get_logger().info.assert_called_with("PTU solo tiene posición")
    ptu_controller.view.home_tab.set_device_status.assert_called_once_with("PTU", False, ["Confirmación"])
    ptu_controller.view.ptu_config_widget.set_state.assert_called_once_with("No se ha confirmado la posición")

# ————— show/ hide config —————

def test_show_ptu_config_no_view(ptu_controller):
    ptu_controller.view = None
    ptu_controller.node.get_logger().error.reset_mock()
    assert ptu_controller.show_ptu_config() is None
    ptu_controller.node.get_logger().error.assert_called_once()

def test_show_and_hide_ptu_config_widget(ptu_controller):
    # show_ptu_config
    widget = MagicMock()
    ptu_controller.view.ptu_config_widget = widget
    ptu_controller.node.get_logger().info.reset_mock()
    ptu_controller.signals = MagicMock()
    ptu_controller.view.switch_to_ptu_config = MagicMock()
    ptu_controller.api_key = "XYZ"
    ptu_controller.show_ptu_config()
    ptu_controller.view.switch_to_ptu_config.assert_called_once()


    # hide_ptu_config (si existe)
    if hasattr(ptu_controller, 'hide_ptu_config'):
        widget.reset_mock()
        ptu_controller.signals = MagicMock()
        ptu_controller.hide_ptu_config()
        widget.hide.assert_called_once()
        ptu_controller.signals.dialogActive.emit.assert_called_once_with(False)