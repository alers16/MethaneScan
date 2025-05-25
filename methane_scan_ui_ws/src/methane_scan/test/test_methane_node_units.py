import json, time, types
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from std_msgs.msg import Bool


def _make_bool(data):
    from std_msgs.msg import Bool
    msg = Bool()
    msg.data = data
    return msg


def _make_string(payload):
    from std_msgs.msg import String
    msg = String()
    msg.data = payload
    return msg

@pytest.fixture
def node_instance(monkeypatch):
    """Return MethaneScanNode with timer disabled for deterministic tests."""
    from methane_scan.methane_scan_node import MethaneScanNode
    # Patch create_timer to store callback without starting threads
    timer_cb = {}
    def fake_create_timer(period, cb):
        timer_cb["cb"] = cb
        return SimpleNamespace(start=lambda: None, stop=lambda: None, timeout=None)
    monkeypatch.setattr(MethaneScanNode, "create_timer", fake_create_timer, raising=True)

    n = MethaneScanNode()
    # ensure not running real ROS clock
    n.get_clock().now = lambda: 0.0
    return n


def test_hunter_position_invalid_json_does_not_raise(node_instance, caplog):
    bad_msg = _make_string("not_json")
    # should just log error, not raise
    node_instance._listener_hunter_position_callback_safe(bad_msg)
    assert any("Invalid JSON" in rec.message for rec in caplog.records) is False


def test_previous_messages_emitted_on_register(node_instance):
    # Pre‑receive a PTU ready message
    node_instance._listener_callback_safe(_make_bool(True))
    emitted = {}
    node_instance.register_callbacks(ptu_ready_callback=lambda v: emitted.setdefault("ptu", v),
                                     hunter_position_callback=None,
                                     TDLAS_ready_callback=None,
                                     TDLAS_data_callback=None,
                                     end_simulation_callback=None,
                                     play_simulation_callback=None,
                                     ptu_position_callback=None,
                                     mqtt_connection_callback=None,
                                     mqtt_bridge_status_callback=None)
    assert emitted["ptu"] is True


def test_mqtt_timeouts_trigger_signals(node_instance):
    triggered = {}
    node_instance.signals.mqtt_connection_signal.connect(lambda v: triggered.setdefault("conn", v))
    node_instance.signals.mqtt_bridge_status_signal.connect(lambda v: triggered.setdefault("bridge", v))

    # set last timestamps in the past so difference > 3s
    node_instance._last_mqtt_conn = 0.0
    node_instance._last_mqtt_bridge = 0.0
    node_instance.get_clock().now = lambda: 5.0  # seconds

    node_instance._check_for_timeouts()
    assert triggered["conn"] is False and triggered["bridge"] is False


def test_listener_callbacks_update_state(node_instance):
    # MQTT connection resets timeout flag
    msg = _make_bool(True)
    node_instance._mqtt_conn_timed_out = True
    node_instance._listener_mqtt_connection_callback_safe(msg)
    assert node_instance._mqtt_conn_timed_out is False


@pytest.fixture
def registered_node(node_instance):
    """Node with all callbacks registered to simple collectors."""
    bag = {}
    def _make(name):
        return lambda v=None: bag.setdefault(name, v)

    node_instance.register_callbacks(
        ptu_ready_callback     = _make("ptu"),
        hunter_position_callback=_make("hunter"),
        TDLAS_ready_callback   = _make("tdlas"),
        TDLAS_data_callback    = _make("tdlas_data"),
        end_simulation_callback= _make("end_sim"),
        play_simulation_callback=lambda d: bag.setdefault("play", d),
        ptu_position_callback  = _make("ptu_pos"),
        mqtt_connection_callback=lambda b: bag.setdefault("mqtt_conn", b),
        mqtt_bridge_status_callback=lambda b: bag.setdefault("mqtt_bridge", b),
    )
    return node_instance, bag


def test_signal_to_callback_bridge(registered_node):
    node, bag = registered_node
    # Emit every Qt signal once
    node.signals.ptu_ready_signal.emit(True)
    node.signals.hunter_position_signal.emit({"x":1})
    node.signals.TDLAS_ready_signal.emit(True)
    node.signals.TDLAS_data_signal.emit({"ppm":0.2})
    node.signals.end_simulation_signal.emit(True)
    node.signals.play_simulation_signal.emit({"path":"/tmp"})
    node.signals.ptu_position_signal.emit({"lat":0,"lng":0})
    node.signals.mqtt_connection_signal.emit(False)
    node.signals.mqtt_bridge_status_signal.emit(False)

    assert bag == {
        "ptu": True,
        "hunter": {"x":1},
        "tdlas": True,
        "tdlas_data": {"ppm":0.2},
        "end_sim": None,
        "play": {"path":"/tmp"},
        "ptu_pos": {"lat":0,"lng":0},
        "mqtt_conn": False,
        "mqtt_bridge": False,
    }


def test_pause_resume_subscriptions(node_instance):
    node_instance.pause_subscriptions()
    assert node_instance._subscriptions_active is False

    # Try to send message while paused – state shouldn't change
    node_instance._listener_callback_safe(_make_bool(True))
    assert node_instance._ptu_ready_received is False

    node_instance.resume_subscriptions()
    assert node_instance._subscriptions_active is True

    node_instance._listener_callback_safe(_make_bool(True))
    assert node_instance._ptu_ready_received is True


def test_tdlas_data_invalid_json(node_instance, caplog):
    bad_json = _make_string("{bad json}")
    node_instance._listener_TDLAS_data_callback_safe(bad_json)
    assert any("Invalid JSON" in rec.message for rec in caplog.records) is False


def test_shutdown_flags(node_instance):
    node_instance.shutdown()
    assert node_instance._node_running is False and node_instance._subscriptions_active is False

def test_all_qt_handlers_call_callbacks(registered_node):
    node, bag = registered_node

    # End simulation
    node._handle_end_simulation_qt(True)
    assert bag["end_sim"] is None

    # Play simulation
    node._handle_play_simulation_qt({"file": "X"})
    assert bag["play"] == {"file": "X"}

    # PTU position
    node._handle_ptu_position_qt({"lat": 1, "lng": 2})
    assert bag["ptu_pos"] == {"lat": 1, "lng": 2}

    # Log handler covers info / warn / error / debug branches
    for lvl in ("info", "warn", "error", "debug"):
        node._handle_log_message_qt(lvl, "msg")

def test_listeners_good_json(node_instance):
    node_instance.resume_subscriptions()

    pos = _make_string(json.dumps({"x": 0}))
    node_instance._listener_hunter_position_callback_safe(pos)
    assert node_instance._hunter_position_received

    tdlas = _make_string(json.dumps({"ppm": 1.2}))
    node_instance._listener_TDLAS_data_callback_safe(tdlas)
    assert node_instance._last_TDLAS_data == {"ppm": 1.2}

    ptu_pos = _make_string(json.dumps({"lat": 3, "lng": 4}))
    node_instance._listener_ptu_position_callback_safe(ptu_pos)
    assert node_instance._last_ptu_position == {"lat": 3, "lng": 4}



def test_subscription_and_publisher_calls(monkeypatch):
    """Ensure create_subscription, create_publisher, and create_timer are called with correct args."""
    from methane_scan.methane_scan_node import MethaneScanNode
    call_log = {"subs": [], "pubs": [], "timers": []}

    def fake_create_subscription(self, msg_type, topic, callback, qos):
        call_log["subs"].append((msg_type.__name__, topic, callback.__name__, qos))
        return f"sub:{topic}"
    def fake_create_publisher(self, msg_type, topic, qos):
        call_log["pubs"].append((msg_type.__name__, topic, qos))
        return f"pub:{topic}"
    def fake_create_timer(self, period, cb):
        call_log["timers"].append((period, cb.__name__))
        return None

    monkeypatch.setattr(MethaneScanNode, 'create_subscription', fake_create_subscription)
    monkeypatch.setattr(MethaneScanNode, 'create_publisher', fake_create_publisher)
    monkeypatch.setattr(MethaneScanNode, 'create_timer', fake_create_timer)

    node = MethaneScanNode()
    # Nine subscriptions expected
    expected_subs = [
        ('Bool', '/PTU_ready', '_listener_callback_safe', 10),
        ('String', '/hunter_position', '_listener_hunter_position_callback_safe', 10),
        ('Bool', '/TDLAS_ready', '_listener_TDLAS_ready_callback_safe', 10),
        ('String', '/TDLAS_data', '_listener_TDLAS_data_callback_safe', 10),
        ('Bool', '/end_simulation', '_listener_end_simulation_callback_safe', 10),
        ('String', '/data_playback', '_listener_play_simulation_callback_safe', 10),
        ('String', '/PTU_position', '_listener_ptu_position_callback_safe', 10),
        ('Bool', '/connection_status', '_listener_mqtt_connection_callback_safe', 10),
        ('Bool', '/mqtt_status', '_listener_mqtt_bridge_status_callback_safe', 10),
    ]
    assert call_log['subs'] == expected_subs

    # Three publishers expected
    expected_pubs = [
        ('KeyValue', '/initialize_hunter_params', 10),
        ('KeyValue', '/start_simulation', 10),
        ('String', '/save_simulation', 10),
        ('KeyValue', '/start_stop_value', 10),
    ]
    assert call_log['pubs'] == expected_pubs

    # One timer expected
    assert call_log['timers'] == [(0.5, '_check_for_timeouts')]

def test_listener_TDLAS_ready_callback_safe_with_valid_data(node_instance):
    """Test _listener_TDLAS_ready_callback_safe with valid data."""
    msg = Bool(data=True)

    # Call the method
    node_instance._listener_TDLAS_ready_callback_safe(msg)

    # Verify that the TDLAS ready state is updated
    assert node_instance._last_TDLAS_ready is True
    assert node_instance._TDLAS_ready_received is True



def test_listener_TDLAS_ready_callback_safe_handles_exceptions(node_instance):
    """Test _listener_TDLAS_ready_callback_safe handles exceptions gracefully."""
    # Force an exception
    node_instance._lock = None  # This will cause an AttributeError
    msg = Bool(data=True)

    # Call the method
    node_instance._listener_TDLAS_ready_callback_safe(msg)

  

def test_listener_end_simulation_callback_safe_handles_exceptions(node_instance):
    """Test _listener_end_simulation_callback_safe handles exceptions gracefully."""

    # Force an exception
    node_instance._lock = None  # This will cause an AttributeError
    msg = Bool(data=True)

    # Call the method
    node_instance._listener_end_simulation_callback_safe(msg)


def test_listener_mqtt_bridge_status_callback_safe_with_valid_data(node_instance):
    """Test _listener_mqtt_bridge_status_callback_safe with valid data."""
    msg = Bool(data=True)

    # Call the method
    node_instance._listener_mqtt_bridge_status_callback_safe(msg)

    # Verify that the MQTT bridge status is updated
    assert node_instance._mqtt_bridge_timed_out is False


def test_listener_mqtt_bridge_status_callback_safe_handles_exceptions(node_instance):
    """Test _listener_mqtt_bridge_status_callback_safe handles exceptions gracefully."""
    # Force an exception
    node_instance._lock = None  # This will cause an AttributeError
    msg = Bool(data=True)

    # Call the method
    node_instance._listener_mqtt_bridge_status_callback_safe(msg)
