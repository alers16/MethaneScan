
def test_mqtt_timeout_handlers_emit_signals(qtbot):
    from methane_scan.methane_scan_node import MethaneScanNode

    node = MethaneScanNode()

    mqtt_conn_values   = []
    mqtt_bridge_values = []
    node.signals.mqtt_connection_signal.connect(lambda v: mqtt_conn_values.append(v))
    node.signals.mqtt_bridge_status_signal.connect(lambda v: mqtt_bridge_values.append(v))

    # Trigger the handlers directly
    node._on_mqtt_connection_timeout()
    node._on_mqtt_bridge_timeout()

    # Both should have sent a False boolean
    assert mqtt_conn_values and mqtt_conn_values[-1] is False
    assert mqtt_bridge_values and mqtt_bridge_values[-1] is False