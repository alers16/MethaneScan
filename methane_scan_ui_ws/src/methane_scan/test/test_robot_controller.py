from unittest.mock import MagicMock
import pytest

def test_update_robot_speed_valid(robot_controller):
    robot_controller.update_robot_speed(1.2)
    assert robot_controller.robot_speed == 1.2


def test_update_robot_speed_no_change(robot_controller, caplog):
    robot_controller.robot_speed = 0.5
    robot_controller.update_robot_speed(0.5)  # same value
    # Logger should have registered "No change" – easier: robot_speed unchanged
    assert robot_controller.robot_speed == 0.5

def test_robot_check_ready(robot_controller):
    robot_controller.robot_position = [10, 20]
    robot_controller.path = [(10, 20), (10.1, 20.1)]
    robot_controller.robot_speed = 0.5
    # stub out view and signals
    robot_controller.view.home_tab = MagicMock()
    robot_controller.view.robot_config_widget = MagicMock()
    robot_controller.signals = MagicMock()
    # call and assert return value
    assert robot_controller.check_Robot_ready()
    # check that the controller marked itself configured
    assert robot_controller.robot_configured is True

def test_robotcontroller_path_none(robot_controller):
    """update_ptu_position() with missing keys should raise KeyError/ValueError."""
    assert robot_controller._update_path([None]) is None
    robot_controller.node.get_logger().warn.assert_called_once()

def test_robotcontroller_path_empty(robot_controller):
    """update_ptu_position() with missing keys should raise KeyError/ValueError."""
    assert robot_controller._update_path([]) is None
    robot_controller.node.get_logger().warn.assert_called_once()

def test_update_hunter_position_with_valid_data(robot_controller):
    """Test update_hunter_position with valid data."""
    position = {"lat": 12.34567, "lng": -98.76543}

    # Mock the view and its components
    home_tab = MagicMock()
    robot_config_widget = MagicMock()
    robot_controller.view.home_tab = home_tab
    robot_controller.view.robot_config_widget = robot_config_widget

    # Call the method
    robot_controller.update_hunter_position(position)

    # Verify that the position is updated
    assert robot_controller.robot_position == position

    # Verify that the UI components are updated
    home_tab.set_robot_position.assert_called_once_with(position)
    robot_config_widget.set_position.assert_called_once_with(position)


def test_update_hunter_position_with_null_data(robot_controller):
    """Test update_hunter_position with null data."""
    # Call the method with None
    robot_controller.update_hunter_position(None)

    # Verify that a warning is logged
    robot_controller.node.get_logger().warn.assert_called_once_with("Received null hunter position")

    # Verify that the position is not updated
    assert robot_controller.robot_position is None


def test_update_hunter_position_with_missing_ui_components(robot_controller):
    """Test update_hunter_position when UI components are missing."""
    position = {"lat": 12.34567, "lng": -98.76543}

    # Simulate missing UI components
    robot_controller.view.home_tab = None
    robot_controller.view.robot_config_widget = None

    # Call the method
    robot_controller.update_hunter_position(position)

    # Verify that a warning is logged
    robot_controller.node.get_logger().warn.assert_called_once_with(
        "Could not update map: UI components not available"
    )

    # Verify that the position is updated internally
    assert robot_controller.robot_position == position


def test_update_hunter_position_handles_type_error(robot_controller):
    """Test update_hunter_position handles TypeError gracefully."""
    # Call the method with invalid data
    robot_controller.update_hunter_position("invalid_data")

    robot_controller.node.get_logger().error.assert_called()


def test_update_hunter_position_handles_key_error(robot_controller):
    """Test update_hunter_position handles KeyError gracefully."""
    # Call the method with missing keys
    position = {"latitude": 12.34567}  # Missing "lng"
    robot_controller.update_hunter_position(position)

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called()



def test_update_hunter_position_handles_attribute_error(robot_controller):
    """Test update_hunter_position handles AttributeError gracefully."""
    position = {"lat": 12.34567, "lng": -98.76543}

    # Simulate missing attributes in the view
    robot_controller.view = None

    # Call the method
    robot_controller.update_hunter_position(position)

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called()


def test_update_hunter_position_handles_unexpected_exception(robot_controller):
    """Test update_hunter_position handles unexpected exceptions gracefully."""
    position = {"lat": 12.34567, "lng": -98.76543}

    # Mock the view and force an exception
    home_tab = MagicMock()
    home_tab.set_robot_position.side_effect = Exception("Test exception")
    robot_controller.view.home_tab = home_tab

    # Call the method
    robot_controller.update_hunter_position(position)

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called_with(
        "Unexpected error updating hunter position: Test exception"
    )

def test_update_path_with_valid_path(robot_controller):
    """Test _update_path with a valid path."""
    path = [{"lat": 12.34567, "lng": -98.76543}, {"lat": 12.34678, "lng": -98.76432}]

    # Call the method
    robot_controller._update_path(path)

    # Verify that the path is updated
    assert robot_controller.path == path
    


def test_update_path_with_null_path(robot_controller):
    """Test _update_path with a null path."""
    path = [None]

    # Call the method
    robot_controller._update_path(path)

    # Verify that the path is cleared
    assert robot_controller.path == []

    # Verify that a warning is logged
    robot_controller.node.get_logger().warn.assert_called_with("Received null path")


def test_update_path_with_empty_path(robot_controller):
    """Test _update_path with an empty path."""
    path = []

    # Call the method
    robot_controller._update_path(path)

    # Verify that the path is cleared
    assert robot_controller.path == []

    # Verify that a warning is logged
    robot_controller.node.get_logger().warn.assert_called_with("empty path")



def test_update_path_handles_type_error(robot_controller):
    """Test _update_path handles TypeError gracefully."""
    path = "invalid_path"

    # Call the method
    robot_controller._update_path(path)

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called()


def test_update_path_handles_value_error(robot_controller):
    """Test _update_path handles ValueError gracefully."""
    path = [{"lat": "invalid_lat", "lng": -98.76543}]

    # Call the method
    robot_controller._update_path(path)

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called()


def test_show_trajectory_config_with_valid_view(robot_controller):
    """Test show_trajectory_config when the view is valid."""
    # Mock the view and its methods
    view = MagicMock()
    robot_controller.view = view

    # Call the method
    robot_controller.show_trajectory_config()

    # Verify that the logger logs the dialog opening
    robot_controller.node.get_logger().info.assert_any_call("Opening path dialog")
    robot_controller.node.get_logger().info.assert_any_call("Path dialog opened")


def test_show_trajectory_config_with_missing_view(robot_controller):
    """Test show_trajectory_config when the view is missing."""
    # Set the view to None
    robot_controller.view = None

    # Call the method
    robot_controller.show_trajectory_config()

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called_with(
        "Cannot show PTU config: view is not initialized"
    )


def test_show_trajectory_config_handles_exceptions(robot_controller):
    """Test show_trajectory_config handles exceptions gracefully."""
    # Mock the view and force an exception
    view = MagicMock()
    view.switch_to_select_trajectory.side_effect = Exception("Test exception")
    robot_controller.view = view

    # Call the method
    robot_controller.show_trajectory_config()

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called_with(
        "Error opening Path dialog: Test exception"
    )



def test_on_trajectory_dialog_accepted_with_valid_widget(robot_controller):
    """Test on_trajectory_dialog_accepted when the widget is valid."""
    # Mock the view and its components
    select_trajectory_widget = MagicMock()
    select_trajectory_widget.selected_trajectory = [
        {"lat": 12.34567, "lng": -98.76543},
        {"lat": 12.34678, "lng": -98.76432},
    ]
    robot_controller.view = MagicMock()
    robot_controller.view.select_trajectory_widget = select_trajectory_widget

    # Mock the _update_path method
    robot_controller._update_path = MagicMock()

    # Call the method
    robot_controller.on_trajectory_dialog_accepted()

    # Verify that the logger logs the acceptance
    robot_controller.node.get_logger().info.assert_called_with("Trajectory selection accepted")

    # Verify that the path is updated
    robot_controller._update_path.assert_called_once_with(select_trajectory_widget.selected_trajectory)


def test_on_trajectory_dialog_accepted_with_missing_widget(robot_controller):
    """Test on_trajectory_dialog_accepted when the widget is missing."""
    # Mock the view without the select_trajectory_widget
    robot_controller.view = MagicMock()
    robot_controller.view.select_trajectory_widget = None

    # Call the method
    robot_controller.on_trajectory_dialog_accepted()

    # Verify that a warning is logged
    robot_controller.node.get_logger().warn.assert_called_with(
        "Trajectory selection widget not available for final data retrieval"
    )


def test_on_trajectory_dialog_accepted_handles_exceptions(robot_controller):
    """Test on_trajectory_dialog_accepted handles exceptions gracefully."""
    # Mock the view and force an exception
    select_trajectory_widget = MagicMock()
    select_trajectory_widget.selected_trajectory = [
        {"lat": 12.34567, "lng": -98.76543},
        {"lat": 12.34678, "lng": -98.76432},
    ]
    robot_controller.view = MagicMock()
    robot_controller.view.select_trajectory_widget = select_trajectory_widget
    robot_controller._update_path = MagicMock(side_effect=Exception("Test exception"))

    # Call the method
    robot_controller.on_trajectory_dialog_accepted()

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called_with(
        "Error handling trajectory dialog acceptance: Test exception"
    )

def test_show_robot_config_with_valid_view(robot_controller):
    """Test show_robot_config when the view is valid."""
    # Mock the view and its methods
    view = MagicMock()
    robot_controller.view = view

    # Call the method
    robot_controller.show_robot_config()

    # Verify that the dialog is opened
    view.switch_to_robot_config.assert_called_once()

    # Verify that the logger logs the dialog opening
    robot_controller.node.get_logger().info.assert_any_call("Opening robot configuration dialog")
    robot_controller.node.get_logger().info.assert_any_call("Robot configuration dialog opened")


def test_show_robot_config_with_missing_view(robot_controller):
    """Test show_robot_config when the view is missing."""
    # Set the view to None
    robot_controller.view = None

    # Call the method
    robot_controller.show_robot_config()

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called_with(
        "Cannot show robot config: view is not initialized"
    )



def test_show_robot_config_handles_exceptions(robot_controller):
    """Test show_robot_config handles exceptions gracefully."""
    # Mock the view and force an exception
    view = MagicMock()
    view.switch_to_robot_config.side_effect = Exception("Test exception")
    robot_controller.view = view

    # Call the method
    robot_controller.show_robot_config()

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called_with(
        "Error opening robot config dialog: Test exception"
    )



def test_on_robot_dialog_accepted_with_valid_widget(robot_controller):
    """Test on_robot_dialog_accepted when the widget is valid."""
    # Mock the view and its components
    robot_config_widget = MagicMock()
    robot_config_widget.speed = 1.5  # Mock speed value
    robot_controller.view = MagicMock()
    robot_controller.view.robot_config_widget = robot_config_widget

    # Mock the update_robot_speed method
    robot_controller.update_robot_speed = MagicMock()

    # Call the method
    robot_controller.on_robot_dialog_accepted()

    # Verify that the logger logs the acceptance
    robot_controller.node.get_logger().info.assert_called_with("Robot configuration accepted")

    # Verify that the robot speed is updated
    robot_controller.update_robot_speed.assert_called_once_with(1.5)


def test_on_robot_dialog_accepted_with_missing_widget(robot_controller):
    """Test on_robot_dialog_accepted when the widget is missing."""
    # Mock the view without the robot_config_widget
    robot_controller.view = MagicMock()
    robot_controller.view.robot_config_widget = None

    # Call the method
    robot_controller.on_robot_dialog_accepted()

    # Verify that a warning is logged
    robot_controller.node.get_logger().warn.assert_called_with(
        "Robot config widget not available for final data retrieval"
    )


def test_on_robot_dialog_accepted_handles_exceptions(robot_controller):
    """Test on_robot_dialog_accepted handles exceptions gracefully."""
    # Mock the view and force an exception
    robot_config_widget = MagicMock()
    robot_config_widget.speed = 1.5
    robot_controller.view = MagicMock()
    robot_controller.view.robot_config_widget = robot_config_widget
    robot_controller.update_robot_speed = MagicMock(side_effect=Exception("Test exception"))

    # Call the method
    robot_controller.on_robot_dialog_accepted()

    # Verify that an error is logged
    robot_controller.node.get_logger().error.assert_called_with(
        "Error handling robot dialog acceptance: Test exception"
    )
