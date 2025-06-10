import json
import pytest
from unittest.mock import MagicMock

def test_check_all_ready_flags(main_controller):
    # Preconditions – nothing ready yet
    main_controller.ptu_controller.ptu_configured = False
    main_controller.robot_controller.robot_configured = False
    main_controller.tdlas_controller.TDLAS_ready    = False

    main_controller.check_all_ready()
    assert not getattr(main_controller.view.home_tab, "_ready", False)

    # Now everything becomes ready
    main_controller.ptu_controller.ptu_configured = True
    main_controller.robot_controller.robot_configured = True
    main_controller.tdlas_controller.TDLAS_ready    = True

    main_controller.check_all_ready()
    assert main_controller.view.home_tab._ready is True  # view updated


def test_check_publish_sends_keyvalue(monkeypatch, main_controller):
    """When all inputs are available, check_publish() emits a KeyValue msg."""
    main_controller.ptu_controller.PTU_position = (42.0, -3.0)
    main_controller.robot_controller.path = [(42.0, -3.0), (42.1, -3.1)]
    main_controller.robot_controller.robot_speed = 0.7

    main_controller.check_publish()

    pub = main_controller.node.publisher_Hunter_initialized
    pub.publish.assert_called_once()
    msg = pub.publish.call_args[0][0]
    assert msg.key == "/initialize_hunter_params"
    body = json.loads(msg.value)
    assert body["vel"] == 0.7
    assert body["points"] == [[42.0, -3.0], [42.1, -3.1]]


def test_pause_test_publishes_toggle(main_controller):
    """pause_test(state) publishes a KeyValue on /start_stop_value with bool payload."""
    pub = main_controller.node.publisher_start_stop_hunter

    main_controller.pause_test(True)

    pub.publish.assert_called_once()
    msg = pub.publish.call_args[0][0]
    assert msg.key == "/start_stop_value"
    assert msg.value == "True"

def test_main_start_test_publishes(main_controller):
    pub = main_controller.node.publisher_start_simulation
    main_controller.test_start()
    pub.publish.assert_called_once()

def test_update_TDLAS_data(main_controller):
    """update_TDLAS_data() updates the TDLAS data in the controller."""
    tdlas_dict = {
                'header': {
                    'stamp': {
                        'sec': 11213,
                        'nanosec': 14132342
                    },
                    'frame_id': 2
                },
                'average_ppmxm': 145,
                'average_reflection_strength':  12,
                'average_absorption_strength': 23,
                'ppmxm': [],  # Si es un array
                'reflection_strength': [],
                'absorption_strength': []
            }
    
    main_controller.ptu_controller.PTU_position = [1.0, 2.0]
    main_controller.robot_controller.robot_position = {"lat": 1.0, "lng": 4.0}

    main_controller.update_TDLAS_data(data=tdlas_dict)

    assert main_controller.tdlas_data_list == [tdlas_dict]
    pub = main_controller.node.publisher_play_simulation
    pub.publish.assert_called_once()

def test_update_TDLAS_dara_none(main_controller):
    """update_TDLAS_data() handles None data gracefully."""
    main_controller.update_TDLAS_data(data=None)
    pub = main_controller.node.publisher_play_simulation
    pub.publish.assert_not_called()
    main_controller.node.get_logger().warn.assert_called_with("Received null TDLAS data")

def test_play_simulation_with_valid_data(main_controller):
    """Test play_simulation with valid data."""
    data = {
        "ptu_position": [12.34567, -98.76543],
        "hunter_position": {"lat": 12.34678, "lng": -98.76432},
        "tdlas_data": {"average_ppmxm": 75.0}
    }

    # Mock the simulation_tab and its methods
    simulation_tab = MagicMock()
    simulation_tab.save_positions = []
    main_controller.view.simulation_tab = simulation_tab

    main_controller.play_simulation(data)

    # Verify map centering and robot position setting
    simulation_tab.map_frame.centerMap.assert_called_once_with(12.34678, -98.76432)
    simulation_tab.set_robot_position.assert_called_once_with((12.34678, -98.76432))
    simulation_tab.map_frame.drawBeam.assert_called_once_with(
        [(12.34567, -98.76543), (12.34678, -98.76432)], 0.55
    )
    simulation_tab.add_data_row.assert_called_once_with({"average_ppmxm": 75.0})
    simulation_tab.set_tdlas_data.assert_called_once_with({"average_ppmxm": 75.0})
    assert simulation_tab.save_positions == [{"lat": 12.34678, "lng": -98.76432}]


def test_play_simulation_with_no_saved_positions(main_controller):
    """Test play_simulation when there are no saved positions."""
    data = {
        "ptu_position": [12.34567, -98.76543],
        "hunter_position": {"lat": 12.34678, "lng": -98.76432},
        "tdlas_data": {"average_ppmxm": 75.0}
    }

    # Mock the simulation_tab and its methods
    simulation_tab = MagicMock()
    simulation_tab.save_positions = []
    main_controller.view.simulation_tab = simulation_tab

    main_controller.play_simulation(data)

    # Verify that the map is centered on the robot position
    simulation_tab.map_frame.centerMap.assert_called_once_with(12.34678, -98.76432)


def test_play_simulation_with_different_ptu_position(main_controller):
    """Test play_simulation when the PTU position changes."""
    data = {
        "ptu_position": [12.34567, -98.76543],
        "hunter_position": {"lat": 12.34678, "lng": -98.76432},
        "tdlas_data": {"average_ppmxm": 75.0}
    }

    # Mock the simulation_tab and its methods
    simulation_tab = MagicMock()
    simulation_tab.save_positions = [{"lat": 12.34678, "lng": -98.76432}]
    main_controller.view.simulation_tab = simulation_tab

    # Mock the PTU controller's last position
    main_controller.ptu_controller.last_ptu_position = [0.0, 0.0]

    main_controller.play_simulation(data)

    # Verify that the PTU marker is updated
    simulation_tab.map_frame.drawPTUMarker.assert_called_once_with(12.34567, -98.76543)
    assert main_controller.ptu_controller.last_ptu_position == (12.34567, -98.76543)


def test_play_simulation_with_null_data(main_controller):
    """Test play_simulation with null data."""
    main_controller.play_simulation(data=None)

    # Verify that a warning is logged
    main_controller.node.get_logger().warn.assert_called_once_with("Received null TDLAS data")


def test_play_simulation_with_missing_ui_components(main_controller):
    """Test play_simulation when UI components are missing."""
    data = {
        "ptu_position": [12.34567, -98.76543],
        "hunter_position": {"lat": 12.34678, "lng": -98.76432},
        "tdlas_data": {"average_ppmxm": 75.0}
    }

    # Mock the view to simulate missing simulation_tab
    main_controller.view.simulation_tab = None

    main_controller.play_simulation(data)

    # Verify that a warning is logged
    main_controller.node.get_logger().warn.assert_called_once_with(
        "Could not update TDLAS data: UI components not available"
    )


def test_play_simulation_handles_exceptions(main_controller):
    """Test play_simulation handles exceptions gracefully."""
    data = {
        "ptu_position": [12.34567, -98.76543],
        "hunter_position": {"lat": 12.34678, "lng": -98.76432},
        "tdlas_data": {"average_ppmxm": 75.0}
    }

    # Mock the simulation_tab and force an exception
    simulation_tab = MagicMock()
    simulation_tab.map_frame.centerMap.side_effect = Exception("Test exception")
    main_controller.view.simulation_tab = simulation_tab

    main_controller.play_simulation(data)

    # Verify that an error is logged
    main_controller.node.get_logger().error.assert_called_with(
        "Error updating TDLAS data: Test exception"
    )


def test_finish_test_with_missing_ui_components(main_controller):
    """Test finish_test when UI components are missing."""
    # Simulate missing simulation_tab
    main_controller.view.simulation_tab = None

    # Call the method
    main_controller.finish_test()

    # Verify that a warning is logged
    main_controller.node.get_logger().warn.assert_called()


def test_finish_test_handles_exceptions(main_controller):
    """Test finish_test handles exceptions gracefully."""
    # Mock the simulation_tab and force an exception
    simulation_tab = MagicMock()
    simulation_tab.set_test_finished.side_effect = Exception("Test exception")
    main_controller.view.simulation_tab = simulation_tab

    # Call the method
    main_controller.finish_test()

    # Verify that an error is logged
    main_controller.node.get_logger().error.assert_called()


def test_connect_events_all_components_available(main_controller):
    """Test _connect_events when all UI components are available."""
    # Mock the view and its components
    view = MagicMock()
    main_controller.view = view

    # Call the method
    main_controller._connect_events()

    # Verify that navigation callbacks are registered
    view.register_ptu_config_callback.assert_called_once_with(main_controller.ptu_controller.show_ptu_config)
    view.register_home_callback.assert_called_once_with(main_controller.show_home)
    view.register_robot_config_callback.assert_called_once_with(main_controller.robot_controller.show_robot_config)
    view.register_select_trajectory_callback.assert_called_once_with(main_controller.robot_controller.show_trajectory_config)

    # Verify that dialog signals are connected
    view.ptu_config_dialog.accepted.connect.assert_called_once_with(main_controller.ptu_controller.on_ptu_dialog_accepted)
    view.ptu_config_dialog.rejected.connect.assert_called_once_with(main_controller.ptu_controller.on_ptu_dialog_rejected)
    view.robot_config_dialog.accepted.connect.assert_called_once_with(main_controller.robot_controller.on_robot_dialog_accepted)
    view.robot_config_dialog.rejected.connect.assert_called_once_with(main_controller.robot_controller.on_robot_dialog_rejected)

    # Verify that widget signals are connected
    view.ptu_config_widget.position_saved.connect.assert_called_once_with(main_controller.ptu_controller.update_ptu_position)
    view.home_tab.path_saved.connect.assert_called_once_with(main_controller.robot_controller._update_path)
    view.home_tab.start_stop_signal.connect.assert_called_once_with(main_controller.pause_test)
    view.home_tab.logger_signal.connect.assert_called_once_with(main_controller._show_info)
    view.simulation_tab.error_signal.connect.assert_called_once_with(main_controller._show_error)
    view.robot_config_widget.speed_saved.connect.assert_called_once_with(main_controller.robot_controller.update_robot_speed)

    # Verify that the widgets_connected flag is set
    assert main_controller.widgets_connected is True


def test_connect_events_missing_view(main_controller):
    """Test _connect_events when the view is missing."""
    main_controller.view = None

    # Call the method
    main_controller._connect_events()

    # Verify that an error is logged
    main_controller.node.get_logger().error.assert_called_with("Cannot connect events: view isW not initialized")


def test_connect_events_missing_dialogs(main_controller):
    """Test _connect_events when some dialogs are missing."""
    # Mock the view with missing dialogs
    view = MagicMock()
    view.ptu_config_dialog = None
    view.robot_config_dialog = None
    main_controller.view = view

    # Call the method
    main_controller._connect_events()

    # Verify that warnings are logged for missing dialogs
    main_controller.node.get_logger().warn.assert_any_call("PTU config dialog not available for event connection")
    main_controller.node.get_logger().warn.assert_any_call("Robot config dialog not available for event connection")


def test_connect_events_missing_widgets(main_controller):
    """Test _connect_events when some widgets are missing."""
    # Mock the view with missing widgets
    view = MagicMock()
    view.ptu_config_widget = None
    view.home_tab = None
    view.robot_config_widget = None
    main_controller.view = view

    # Call the method
    main_controller._connect_events()

    # Verify that warnings are logged for missing widgets
    main_controller.node.get_logger().warn.assert_any_call("PTU config widget not available for event connection")
    main_controller.node.get_logger().warn.assert_any_call("Methane scan tab not available for event connection")
    main_controller.node.get_logger().warn.assert_any_call("Robot config widget not available for event connection")


def test_connect_events_handles_exceptions(main_controller):
    """Test _connect_events handles exceptions gracefully."""
    # Mock the view and force an exception
    view = MagicMock()
    view.register_ptu_config_callback.side_effect = Exception("Test exception")
    main_controller.view = view

    # Call the method
    main_controller._connect_events()

    # Verify that an error is logged
    main_controller.node.get_logger().error.assert_called_with("Error connecting events: Test exception")

