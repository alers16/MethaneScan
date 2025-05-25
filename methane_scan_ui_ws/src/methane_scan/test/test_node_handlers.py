def test_handle_ptu_ready_invokes_callback():
    from methane_scan.methane_scan_node import MethaneScanNode
    mn = MethaneScanNode()
    flag = {}
    mn.register_callbacks(ptu_ready_callback=lambda v: flag.setdefault("ptu", v),
                          hunter_position_callback=None,
                          TDLAS_ready_callback=None,
                          TDLAS_data_callback=None,
                          end_simulation_callback=None,
                          play_simulation_callback=None,
                          ptu_position_callback=None,
                          mqtt_connection_callback=None,
                          mqtt_bridge_status_callback=None)
    mn._handle_ptu_ready_qt(True)
    assert flag["ptu"] is True