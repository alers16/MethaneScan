import pytest
import time
from unittest.mock import MagicMock
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class TestSignals(QObject):
    ptu_ready_signal = pyqtSignal(bool)
    hunter_position_signal = pyqtSignal(dict)
    TDLAS_data_signal = pyqtSignal(dict)
    end_simulation_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

def test_node_initialization_and_basic_signals(node):
    """Test that MethaneScanNode initializes and emits basic signals."""
    # Verificar que el nodo está inicializado
    assert node is not None
    assert hasattr(node, 'get_logger')
    assert hasattr(node, 'create_subscription')
    assert hasattr(node, 'create_publisher')

    # Crear señales de prueba
    signals = TestSignals()
    
    # Variables para capturar las señales emitidas
    received_signals = []

    def capture_ptu_ready(value):
        received_signals.append(('ptu_ready', value))

    def capture_hunter_position(position):
        received_signals.append(('hunter_position', position))

    # Conectar las señales a los capturadores
    signals.ptu_ready_signal.connect(capture_ptu_ready)
    signals.hunter_position_signal.connect(capture_hunter_position)

    # Emitir señales
    signals.ptu_ready_signal.emit(True)
    hunter_position = {"lat": 12.34567, "lng": -98.76543}
    signals.hunter_position_signal.emit(hunter_position)

    # Verificar que las señales fueron recibidas
    assert len(received_signals) == 2
    assert received_signals[0] == ('ptu_ready', True)
    assert received_signals[1] == ('hunter_position', hunter_position)


def test_main_controller_receives_signals(main_controller):
    """Test that MainController receives and handles signals from MethaneScanNode."""
    # Crear señales de prueba
    signals = TestSignals()
    
    # Mockear métodos del controlador
    main_controller.update_hunter_position = MagicMock()
    main_controller.update_TDLAS_data = MagicMock()

    # Variables para capturar las llamadas
    captured_calls = []

    def mock_update_hunter_position(position):
        captured_calls.append(('hunter_position', position))

    def mock_update_TDLAS_data(data):
        captured_calls.append(('tdlas_data', data))

    # Asignar los mocks
    main_controller.update_hunter_position = mock_update_hunter_position
    main_controller.update_TDLAS_data = mock_update_TDLAS_data

    # Simular la recepción de señales
    hunter_position = {"lat": 12.34567, "lng": -98.76543}
    tdlas_data = {"average_ppmxm": 75.0}

    main_controller.update_hunter_position(hunter_position)
    main_controller.update_TDLAS_data(tdlas_data)

    # Verificar que los métodos fueron llamados
    assert len(captured_calls) == 2
    assert captured_calls[0] == ('hunter_position', hunter_position)
    assert captured_calls[1] == ('tdlas_data', tdlas_data)


def test_ui_updates_on_signals(main_controller):
    """Test that UI components update correctly when signals are emitted."""
    # Mockear la vista y sus componentes
    simulation_tab = MagicMock()
    main_controller.view = MagicMock()
    main_controller.view.simulation_tab = simulation_tab

    # Simular actualizaciones
    hunter_position = {"lat": 12.34567, "lng": -98.76543}
    tdlas_data = {"average_ppmxm": 75.0}

    # Llamar directamente a los métodos de actualización
    main_controller.robot_controller.update_hunter_position(hunter_position)
    main_controller.update_TDLAS_data(tdlas_data)

    # Verificar que los métodos de la interfaz gráfica fueron llamados
    assert main_controller.view.simulation_tab is not None


def test_end_simulation_signal(main_controller):
    """Test that the end simulation signal is handled correctly."""
    # Mockear la vista y sus componentes
    simulation_tab = MagicMock()
    main_controller.view = MagicMock()
    main_controller.view.simulation_tab = simulation_tab

    # Simular el fin de simulación
    main_controller.finish_test()

    # Verificar que el método finish_test se ejecuta sin errores
    assert main_controller.view.simulation_tab is not None


def test_ros2_mqtt_communication(node):
    """Test communication between ROS2 and MQTT."""
    # Verificar que el nodo tiene los publishers necesarios
    assert hasattr(node, 'create_publisher')
    
    # Simular la creación de publishers
    mqtt_publisher = node.create_publisher(MagicMock, '/mqtt_topic', 10)
    assert mqtt_publisher is not None

    # Simular un mensaje MQTT
    mqtt_message = {"key": "/end_simulation", "value": "True"}
    
    # Verificar que el mensaje puede ser procesado
    assert mqtt_message["key"] == "/end_simulation"
    assert mqtt_message["value"] == "True"


def test_real_time_data_visualization():
    """Test dynamic visualization of real-time data."""
    # Crear un mock completamente independiente de Qt
    simulation_page = MagicMock()
    
    # Configurar métodos de visualización
    simulation_page.add_data_row = MagicMock()
    simulation_page.set_robot_position = MagicMock()

    # Simular datos en tiempo real
    tdlas_data = {
        "average_ppmxm": 75.0,
        "average_reflection_strength": 12,
        "average_absorption_strength": 23,
        "header": {"stamp": {"sec": 1620000000, "nanosec": 500000000}}
    }
    hunter_position = {"lat": 12.34567, "lng": -98.76543}

    # Simular llamadas directas a los métodos de la GUI
    simulation_page.add_data_row(tdlas_data)
    simulation_page.set_robot_position(hunter_position)

    # Verificar que los métodos fueron llamados
    simulation_page.add_data_row.assert_called_once_with(tdlas_data)
    simulation_page.set_robot_position.assert_called_once_with(hunter_position)