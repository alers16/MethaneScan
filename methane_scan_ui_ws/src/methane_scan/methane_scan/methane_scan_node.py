import sys
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from sensor_msgs.msg import NavSatFix # type: ignore
from olfaction_msgs.msg import TDLAS
import cv2
import numpy as np
import configparser as cp
import json
from methane_scan.controllers.main_controller import MainController  # type: ignore
from PyQt5 import QtWidgets, QtGui, QtCore
from diagnostic_msgs.msg import KeyValue
import os
import time
import traceback
from typing import Optional, Dict, Any, Callable
from PyQt5 import QtCore
from rcl_interfaces.msg import Log
from rclpy.duration import Duration
import rclpy
from .views.splash_screen import SplashScreen  # type: ignore
import methane_scan.qresources_rc  # type: ignore # Tu archivo de recursos compilado


class RosQtSignals(QtCore.QObject):
    ptu_ready_signal = QtCore.pyqtSignal(bool)
    hunter_position_signal = QtCore.pyqtSignal(dict)
    TDLAS_ready_signal = QtCore.pyqtSignal(bool)
    TDLAS_data_signal = QtCore.pyqtSignal(dict)
    log_message_signal = QtCore.pyqtSignal(str, str)  # level, message
    end_simulation_signal = QtCore.pyqtSignal(bool)
    play_simulation_signal = QtCore.pyqtSignal(dict)
    ptu_position_signal = QtCore.pyqtSignal(dict)
    mqtt_connection_signal = QtCore.pyqtSignal(bool)
    mqtt_bridge_status_signal = QtCore.pyqtSignal(bool)

class NodeChecker(QtCore.QThread):
    nodeReady = QtCore.pyqtSignal(str)  # emite nombre del nodo cuando su topic reporta
    allReady  = QtCore.pyqtSignal()     # emite cuando todos los nodos han reportado
    nodeError = QtCore.pyqtSignal(str)  # emite si un nodo no reporta en el tiempo esperado

    def __init__(self, wait_for: dict, parent=None):
        """
        wait_for = {
          'mqtt_ros_bridge_node': {
             'status_topic': '/mqtt_bridge/status',
             'status_type': String
          },
          'otro_nodo': {
             'status_topic': '/otro_nodo/status',
             'status_type': String
          }
        }
        """
        super().__init__(parent)
        self.wait_for = wait_for
        self._ready = set()
        self._error = set()  # nodos que no reportaron en el tiempo esperado

    def run(self):
        checker = rclpy.create_node('splash_node_checker')

        for node_name, cfg in self.wait_for.items():
            topic = cfg['status_topic']
            typ   = cfg['status_type']

            def make_cb(name):
                def cb(msg):
                    if name not in self._ready and msg.data:
                        self._ready.add(name)
                        self.nodeReady.emit(name)
                return cb

            checker.create_subscription(
                typ,
                topic,
                make_cb(node_name),
                10
            )

        start_time = time.time()
        timeout = 10
        while rclpy.ok() and self._ready != set(self.wait_for.keys()):
            if time.time() - start_time > timeout:
                missing_nodes = set(self.wait_for.keys()) - self._ready
                for missed in missing_nodes:
                    self.nodeError.emit(f"{missed}")
                    self._error.add(missed)

                break
            rclpy.spin_once(checker, timeout_sec=0.2)

        time.sleep(1)
        self.allReady.emit()
        checker.destroy_node()

class MethaneScanNode(Node):
    """ROS2 node with thread-safety and proper resource management for MethaneScan."""
    
    def __init__(self):
        super().__init__('methane_scan_node')

        # Declare parameters and initialize state
        self.declare_parameters_ros()
        
        # Thread synchronization
        self._lock = threading.RLock()
        self.signals = RosQtSignals()
        self.now = self.get_clock().now()
        
        # State tracking
        self._node_running = True
        self._initialized = False
        self._subscriptions_active = True
        self._callbacks_registered = False
        
        # Message tracking
        self._last_ptu_ready = None
        self._last_hunter_position = None
        self._ptu_ready_received = False
        self._hunter_position_received = False
        self._TDLAS_ready_received = False
        self._last_TDLAS_ready = None
        self._last_TDLAS_data = None
        self._last_ptu_position = None
        self._mqtt_conn_timed_out   = False
        self._mqtt_bridge_timed_out = False
        self._last_mqtt_conn    = self.now
        self._last_mqtt_bridge  = self.now
        
        
        # Initialize callbacks with safe no-op functions
        self._callback_ptu_ready: Optional[Callable[[bool], None]] = None
        self._callback_hunter_position: Optional[Callable[[Dict[str, Any]], None]] = None
        self._callback_TDLAS_ready: Optional[Callable[[bool], None]] = None
        self._callback_TDLAS_data: Optional[Callable[[Dict[str, Any]], None]] = None
        self._callback_end_simulation: Optional[Callable[[bool], None]] = None
        self._callback_play_simulation: Optional[Callable[[bool], None]] = None
        self._callback_ptu_position: Optional[Callable[[Dict[str, Any]], None]] = None
        self._callback_mqtt_connection: Optional[Callable[[bool], None]] = None
        self._callback_mqtt_bridge_status: Optional[Callable[[bool], None]] = None
        
        # Connect Qt signals to thread-safe handler methods
        self.signals.ptu_ready_signal.connect(self._handle_ptu_ready_qt)
        self.signals.hunter_position_signal.connect(self._handle_hunter_position_qt)
        self.signals.TDLAS_ready_signal.connect(self._handle_TDLAS_ready_qt)
        self.signals.log_message_signal.connect(self._handle_log_message_qt)
        self.signals.TDLAS_data_signal.connect(self._handle_TDLAS_data_qt)
        self.signals.end_simulation_signal.connect(self._handle_end_simulation_qt)
        self.signals.play_simulation_signal.connect(self._handle_play_simulation_qt)
        self.signals.ptu_position_signal.connect(self._handle_ptu_position_qt)
        self.signals.mqtt_connection_signal.connect(self._handle_mqtt_connection_qt)
        self.signals.mqtt_bridge_status_signal.connect(self._handle_mqtt_bridge_status_qt)
        
        # Create subscriptions and publishers with proper error handling
        try:
            self.subscription = self.create_subscription(
                Bool,
                self.get_parameter('TOPICS.ptu_ready').value,
                self._listener_callback_safe,
                10)
            
            self.subscription_hunter_position = self.create_subscription(
                String,
                self.get_parameter('TOPICS.hunter_position').value,
                self._listener_hunter_position_callback_safe,
                10
            )

            self.subscription_TDLAS_ready = self.create_subscription(
                Bool,
                self.get_parameter('TOPICS.tdlas_ready').value,
                self._listener_TDLAS_ready_callback_safe,
                10
            )

            self.subscription_TDLAS_data = self.create_subscription(
                TDLAS,
                self.get_parameter('TOPICS.tdlas_data').value,
                self._listener_TDLAS_data_callback_safe,
                10
            )

            self.subscription_end_simulation = self.create_subscription(
                Bool,
                self.get_parameter('TOPICS.end_simulation').value,
                self._listener_end_simulation_callback_safe,
                10
            )

            self.subscription_simulation = self.create_subscription(
                String,
                self.get_parameter('TOPICS.play_simulation').value,
                self._listener_play_simulation_callback_safe,
                10
            )

            self.subscription_ptu_position = self.create_subscription(
                NavSatFix,
                self.get_parameter('TOPICS.ptu_position').value,
                self._listener_ptu_position_callback_safe,
                10
            )

            # MQTT connection status subscription + timeout timer
            self.subscription_mqtt_connection = self.create_subscription(
                Bool,
                self.get_parameter('TOPICS.mqtt_connection_status').value,
                self._listener_mqtt_connection_callback_safe,
                10
            )

            # MQTT bridge status subscription + timeout timer
            self.subscription_mqtt_bridge_status = self.create_subscription(
                Bool,
                self.get_parameter('TOPICS.mqtt_bridge_status').value,
                self._listener_mqtt_bridge_status_callback_safe,
                10
            )

            self.publisher_Hunter_initialized = self.create_publisher(KeyValue, 
                                                                      self.get_parameter('TOPICS.initialize_hunter').value,
                                                                      10)
            self.publisher_start_simulation = self.create_publisher(KeyValue,
                                                                    self.get_parameter('TOPICS.start_hunter').value,
                                                                    10)
            
            self.publisher_play_simulation = self.create_publisher(String,
                                                                    self.get_parameter('TOPICS.save_simulation').value,
                                                                    10)
            self.publisher_start_stop_hunter = self.create_publisher(KeyValue,
                                                                      self.get_parameter('TOPICS.start_stop_hunter').value,
                                                                      10)

            self.create_timer(0.5, self._check_for_timeouts)

            self._initialized = True
            self.get_logger().info('MethaneScanNode initialized successfully')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize MethaneScanNode: {str(e)}')
            traceback.print_exc()
            self._initialized = False
    
    def _check_for_timeouts(self):
        now = self.get_clock().now()
        timeout = Duration(seconds=3)

        # MQTT connection status timeout
        if not self._mqtt_conn_timed_out and now - self._last_mqtt_conn > timeout:
            self._mqtt_conn_timed_out = True
            self._on_mqtt_connection_timeout()

        # MQTT bridge status timeout
        if not self._mqtt_bridge_timed_out and now - self._last_mqtt_bridge > timeout:
            self._mqtt_bridge_timed_out = True
            self._on_mqtt_bridge_timeout()
    

    def declare_parameters_ros(self):
        self.declare_parameter('TOPICS.ptu_ready', "/PTU_ready") # pragma: no cover
        self.declare_parameter('TOPICS.hunter_position', "/hunter_position") # pragma: no cover
        self.declare_parameter('TOPICS.tdlas_ready', "/TDLAS_ready")# pragma: no cover
        self.declare_parameter('TOPICS.tdlas_data', "/falcon/reading")  # pragma: no cover
        self.declare_parameter('TOPICS.initialize_hunter', "/initialize_hunter_params") # pragma: no cover
        self.declare_parameter('TOPICS.start_hunter', "/start_simulation") # pragma: no cover
        self.declare_parameter('TOPICS.end_simulation', "/end_simulation") # pragma: no cover
        self.declare_parameter('TOPICS.play_simulation', "/data_playback") # pragma: no cover
        self.declare_parameter('TOPICS.save_simulation', "/save_simulation") # pragma: no cover
        self.declare_parameter('TOPICS.start_stop_hunter', "/start_stop_hunter")# pragma: no cover
        self.declare_parameter('TOPICS.ptu_position', "/fix") # pragma: no cover
        self.declare_parameter('TOPICS.mqtt_connection_status', "/connection_status") # pragma: no cover
        self.declare_parameter('TOPICS.mqtt_bridge_status', "/mqtt_status") # pragma: no cover
    
    def register_callbacks(self, ptu_ready_callback, hunter_position_callback, TDLAS_ready_callback, TDLAS_data_callback,
                           end_simulation_callback, play_simulation_callback, ptu_position_callback, 
                           mqtt_connection_callback, mqtt_bridge_status_callback):
        """Register callbacks with thread-safe protection."""
        with self._lock:
            self._callback_ptu_ready = ptu_ready_callback
            self._callback_hunter_position = hunter_position_callback
            self._callback_TDLAS_ready = TDLAS_ready_callback
            self._callback_TDLAS_data = TDLAS_data_callback
            self._callback_end_simulation = end_simulation_callback
            self._callback_play_simulation = play_simulation_callback
            self._callback_ptu_position = ptu_position_callback
            self._callback_mqtt_connection = mqtt_connection_callback
            self._callback_mqtt_bridge_status = mqtt_bridge_status_callback
            self._callbacks_registered = True
            self.get_logger().info('Callbacks registered successfully')
            
            # If messages were received before callbacks were registered, process them now
            if self._ptu_ready_received and self._last_ptu_ready is not None:
                self.signals.ptu_ready_signal.emit(self._last_ptu_ready)
            
            if self._hunter_position_received and self._last_hunter_position is not None:
                self.signals.hunter_position_signal.emit(self._last_hunter_position)

            if self._TDLAS_ready_received and self._last_TDLAS_ready is not None:
                self.signals.TDLAS_ready_signal.emit(self._last_TDLAS_ready)
    
    def _listener_callback_safe(self, msg):
        """Thread-safe wrapper for PTU ready message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            with self._lock:
                self._last_ptu_ready = msg.data
                self._ptu_ready_received = True
            
            self.signals.log_message_signal.emit('info', f'Received PTU ready message: {msg.data}')
            self.signals.ptu_ready_signal.emit(msg.data)
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in PTU ready callback: {str(e)}')
            traceback.print_exc()

    def _listener_TDLAS_ready_callback_safe(self, msg):
        """Thread-safe wrapper for PTU ready message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            with self._lock:
                self._last_TDLAS_ready = msg.data
                self._TDLAS_ready_received = True
            
            self.signals.log_message_signal.emit('info', f'Received TDLAS ready message: {msg.data}')
            self.signals.TDLAS_ready_signal.emit(msg.data)
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in TDLAS ready callback: {str(e)}')
            traceback.print_exc()
    
    def _listener_hunter_position_callback_safe(self, msg):
        """Thread-safe wrapper for hunter position message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            data = json.loads(msg.data)
            
            with self._lock:
                self._last_hunter_position = data
                self._hunter_position_received = True
            
            self.signals.log_message_signal.emit('info', f'Received hunter position message: {data}')
            self.signals.hunter_position_signal.emit(data)
        except json.JSONDecodeError:
            self.signals.log_message_signal.emit('error', f'Invalid JSON in hunter position message: {msg.data}')
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in hunter position callback: {str(e)}')
            traceback.print_exc()
    
    def _listener_TDLAS_data_callback_safe(self, msg):
        """Thread-safe wrapper for TDLAS data message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            data = {
                'average_ppmxm': msg.average_ppmxm,
                'average_absorption_strength': msg.average_absorption_strength,
                'average_reflection_strength': msg.average_reflection_strength, 
            }
            
            with self._lock:
                self._last_TDLAS_data = data
            
            self.signals.log_message_signal.emit('info', f'Received TDLAS data message: {data}')
            self.signals.TDLAS_data_signal.emit(data)
        except json.JSONDecodeError:
            self.signals.log_message_signal.emit('error', f'Invalid JSON in TDLAS data message: {msg.data}')
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in TDLAS data callback: {str(e)}')
            traceback.print_exc()
    
    def _listener_end_simulation_callback_safe(self, msg):
        """Thread-safe wrapper for end simulation message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            with self._lock:
                end_simulation = msg.data
            
            self.signals.log_message_signal.emit('info', f'Received end simulation message: {end_simulation}')
            if end_simulation:
                self.signals.end_simulation_signal.emit(True)
                # Handle end simulation logic here
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in end simulation callback: {str(e)}')
            traceback.print_exc()

    def _listener_play_simulation_callback_safe(self, msg):
        """Thread-safe wrapper for play simulation message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            data = json.loads(msg.data)
            
            with self._lock:
                self._last_play_simulation = data
            
            #self.signals.log_message_signal.emit('info', f'Received play simulation message: {data}')
            self.signals.play_simulation_signal.emit(data)
        except json.JSONDecodeError:
            self.signals.log_message_signal.emit('error', f'Invalid JSON in play simulation message: {msg.data}')
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in play simulation callback: {str(e)}')
            traceback.print_exc()

    def _listener_ptu_position_callback_safe(self, msg):
        """Thread-safe wrapper for PTU position message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            data = {
                'lat': msg.latitude,
                'lng': msg.longitude,
            }
            
            with self._lock:
                self._last_ptu_position = data
            
            self.signals.log_message_signal.emit('info', f'Received PTU position message: {data}')
            self.signals.ptu_position_signal.emit(data)
        except json.JSONDecodeError:
            self.signals.log_message_signal.emit('error', f'Invalid JSON in PTU position message: {msg.data}')
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in PTU position callback: {str(e)}')
            traceback.print_exc()
        
    def _listener_mqtt_connection_callback_safe(self, msg):
        """Thread-safe wrapper for MQTT connection status message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            with self._lock:
                mqtt_connection = msg.data
                self._last_mqtt_conn = self.get_clock().now()
                self._mqtt_conn_timed_out = False
            
            #self.signals.log_message_signal.emit('info', f'Received MQTT connection status message: {mqtt_connection}')
            self.signals.mqtt_connection_signal.emit(mqtt_connection)
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in MQTT connection callback: {str(e)}')
            traceback.print_exc()
    
    def _listener_mqtt_bridge_status_callback_safe(self, msg):
        """Thread-safe wrapper for MQTT bridge status message callback."""
        if not self._node_running or not self._subscriptions_active:
            return
        
        try:
            with self._lock:
                mqtt_bridge_status = msg.data
                self._last_mqtt_bridge = self.get_clock().now()
                self._mqtt_bridge_timed_out = False
            
            #self.signals.log_message_signal.emit('info', f'Received MQTT bridge status message: {mqtt_bridge_status}')
            self.signals.mqtt_bridge_status_signal.emit(mqtt_bridge_status)
        except Exception as e:
            self.signals.log_message_signal.emit('error', f'Error in MQTT bridge status callback: {str(e)}')
            traceback.print_exc()

    def _handle_ptu_ready_qt(self, ptu_ready):
        """Qt thread handler for PTU ready signal."""
        try:
            if self._callbacks_registered and self._callback_ptu_ready:
                self._callback_ptu_ready(ptu_ready)
            self.get_logger().info(f'PTU ready: {ptu_ready}')
        except Exception as e:
            self.get_logger().error(f'Error handling PTU ready in Qt thread: {str(e)}')
            traceback.print_exc()
        
    def _handle_TDLAS_ready_qt(self, TDLAS_ready):
        """Qt thread handler for TDLAS ready signal."""
        try:
            if self._callbacks_registered and self._callback_TDLAS_ready:
                self._callback_TDLAS_ready(TDLAS_ready)
            self.get_logger().info(f'TDLAS ready: {TDLAS_ready}')
        except Exception as e:
            self.get_logger().error(f'Error handling TDLAS ready in Qt thread: {str(e)}')
            traceback.print_exc()
    
    def _handle_hunter_position_qt(self, position):
        """Qt thread handler for hunter position signal."""
        try:
            if self._callbacks_registered and self._callback_hunter_position:
                self._callback_hunter_position(position)
            self.get_logger().info(f'Hunter position updated: {position}')
        except Exception as e:
            self.get_logger().error(f'Error handling hunter position in Qt thread: {str(e)}')
            traceback.print_exc()
    
    def _handle_log_message_qt(self, level, message):
        """Qt thread handler for log messages."""
        try:
            if level == 'info':
                self.get_logger().info(message)
            elif level == 'warn':
                self.get_logger().warn(message)
            elif level == 'error':
                self.get_logger().error(message)
            elif level == 'debug':
                self.get_logger().debug(message)
        except Exception as e:
            # Last resort error handling
            print(f"Error in logging: {str(e)} - Original message: {message}")
    
    def _handle_TDLAS_data_qt(self, data):
        """Qt thread handler for TDLAS data signal."""
        try:
            if self._callbacks_registered and self._callback_TDLAS_data:
                self._callback_TDLAS_data(data)
            self.get_logger().info(f'TDLAS data received: {data}')
        except Exception as e:
            self.get_logger().error(f'Error handling TDLAS data in Qt thread: {str(e)}')
            traceback.print_exc
    
    def _handle_end_simulation_qt(self, end_simulation):
        """Qt thread handler for end simulation signal."""
        try:
            if self._callbacks_registered and self._callback_end_simulation:
                self._callback_end_simulation()
            self.get_logger().info(f'End simulation signal received: {end_simulation}')
        except Exception as e:
            self.get_logger().error(f'Error handling end simulation in Qt thread: {str(e)}')
            traceback.print_exc()

    def _handle_play_simulation_qt(self, data):
        """Qt thread handler for play simulation signal."""
        try:
            if self._callbacks_registered and self._callback_play_simulation:
                self._callback_play_simulation(data)
            #self.get_logger().info(f'Play simulation signal received: {data}')
        except Exception as e:
            self.get_logger().error(f'Error handling play simulation in Qt thread: {str(e)}')
            traceback.print_exc()
    
    def _handle_ptu_position_qt(self, data):
        """Qt thread handler for PTU position signal."""
        try:
            if self._callbacks_registered and self._callback_ptu_position:
                self._callback_ptu_position(data)
            self.get_logger().info(f'PTU position received: {data}')
        except Exception as e:
            self.get_logger().error(f'Error handling PTU position in Qt thread: {str(e)}')
            traceback.print_exc()
    
    def _handle_mqtt_connection_qt(self, mqtt_connection):
        """Qt thread handler for MQTT connection status signal."""
        try:
            if self._callbacks_registered and self._callback_mqtt_connection:
                #self.get_logger().info(f'MQTT connection status: {mqtt_connection}')
                self._callback_mqtt_connection(mqtt_connection)
        except Exception as e:
            self.get_logger().error(f'Error handling MQTT connection in Qt thread: {str(e)}')
            traceback.print_exc()
    
    def _handle_mqtt_bridge_status_qt(self, mqtt_bridge_status):
        """Qt thread handler for MQTT bridge status signal."""
        try:
            if self._callbacks_registered and self._callback_mqtt_bridge_status:
                self._callback_mqtt_bridge_status(mqtt_bridge_status)
        except Exception as e:
            self.get_logger().error(f'Error handling MQTT bridge status in Qt thread: {str(e)}')
            traceback.print_exc()

    def pause_subscriptions(self):
        """Pause processing of incoming messages."""
        with self._lock:
            self._subscriptions_active = False
            self.get_logger().info('Subscriptions paused')
    
    def resume_subscriptions(self):
        """Resume processing of incoming messages."""
        with self._lock:
            self._subscriptions_active = True
            self.get_logger().info('Subscriptions resumed')
    
    def shutdown(self):
        """Clean shutdown of the node."""
        with self._lock:
            self._node_running = False
            self._subscriptions_active = False
        
        # Allow time for threads to notice the shutdown flag
        time.sleep(0.1)
        self.get_logger().info('Node marked for shutdown')
        
        # Resources will be cleaned up in main function's finally block

    def _on_mqtt_connection_timeout(self):
        self.get_logger().warn('MQTT connection status timeout')
        self.signals.mqtt_connection_signal.emit(False)
    
    def _on_mqtt_bridge_timeout(self):
        self.get_logger().warn('MQTT bridge status timeout')
        self.signals.mqtt_bridge_status_signal.emit(False)


def main(args=None): # pragma: no cover
    """Main function with proper resource management and error handling."""
    executor = None
    node = None
    ros_thread = None
    app = None
    controller = None
    timer = None

    nodos = [
        "mqtt_bridge",
        "mqtt_ros_bridge_node"]
    
    try:
        # Initialize ROS
        rclpy.init(args=args)
        node = MethaneScanNode()
        
        if not node._initialized:
            print("Failed to initialize MethaneScanNode, exiting")
            return 1
        
        # Initialize executor in a separate thread with proper error handling
        executor = rclpy.executors.MultiThreadedExecutor()
        executor.add_node(node)
        
        # Use daemon=True to ensure thread exits when main program exits
        ros_thread = threading.Thread(target=executor.spin, daemon=True)
        ros_thread.start()
        
        # Create PyQt application with error handling
        app = QtWidgets.QApplication(sys.argv)
        
        # Set up application-level exception handling
        sys._excepthook = sys.excepthook
        def exception_hook(exctype, value, traceback_obj):
            print(f"Uncaught exception: {exctype}, {value}")
            if node:
                node.get_logger().error(f"Uncaught exception: {exctype.__name__}: {value}")
            sys._excepthook(exctype, value, traceback_obj)
        sys.excepthook = exception_hook
        
        # Initialize controller
        controller = MainController(node=node)
        if controller.view is None or not controller.initialized:
            node.get_logger().error("Failed to initialize controller, exiting")
            return 1
        
        splash = SplashScreen(":Logo", nodos)
        splash.show()

        wait_for = {
            'mqtt_ros_bridge_node': {
                'status_topic': '/connection_status',
                'status_type': Bool
            },
            'mqtt_bridge': {
                'status_topic': '/mqtt_status',
                'status_type': Bool
            }
        }
        
        checker = NodeChecker(wait_for=wait_for)
        checker.nodeReady.connect(lambda n: (splash.mark_node_ready(n),
                                  node.get_logger().info(f"{n} está listo ✅"),
                                ))
        checker.allReady.connect(lambda: (splash.close(), controller.view.show(), 
                                          controller.view.raise_(), controller.view.activateWindow()))
        
        checker.nodeError.connect(lambda n: (splash.mark_node_error(n),))
        checker.start()
        
        # Register callbacks in a thread-safe way
        node.register_callbacks(
            ptu_ready_callback=controller.ptu_controller.update_PTU_ready,
            hunter_position_callback=controller.robot_controller.update_hunter_position,
            TDLAS_ready_callback=controller.tdlas_controller.update_TDLAS_ready,
            TDLAS_data_callback=controller.update_TDLAS_data,
            end_simulation_callback=controller.finish_test,
            play_simulation_callback=controller.play_simulation,
            ptu_position_callback=controller.ptu_controller.update_ptu_position,
            mqtt_connection_callback=controller.set_mqtt_connection_status,
            mqtt_bridge_status_callback=controller.set_mqtt_bridge_status
        )
        
        # Set up Qt heartbeat timer for clean shutdown and responsive UI
        timer = QtCore.QTimer()
        timer.start(100)  # More responsive timer
        
        # Use Qt event processing to ensure UI remains responsive
        def process_events():
            app.processEvents()
            # Check if ROS is still running
            if not rclpy.ok():
                app.quit()
        
        # Connect timer to process_events to ensure UI responsiveness
        timer.timeout.connect(process_events)
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            node.get_logger().info(f"Signal {sig} received, initiating shutdown")
            if app:
                app.quit()
        
        # Execute the Qt application - will block until app.quit() is called
        node.get_logger().info("Starting Qt application event loop")
        exit_code = app.exec_()
        node.get_logger().info(f"Qt application exited with code {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        node.get_logger().info("KeyboardInterrupt received, shutting down")
        if app:
            app.quit()
        return 1
    except Exception as e:
        print(f"Unhandled exception in main: {str(e)}")
        traceback.print_exc()
        if node:
            node.get_logger().error(f"Unhandled exception in main: {str(e)}")
        return 1
    finally:
        # Proper resource cleanup sequence
        node.get_logger().info("Cleaning up resources")
        
        # Clean up Qt resources
        if timer:
            timer.stop()
            timer.timeout.disconnect()
            timer.deleteLater()
        
        if controller:
            try:
                controller.cleanup()
            except Exception as e:
                print(f"Error during controller cleanup: {str(e)}")
                if node:
                    node.get_logger().error(f"Error during controller cleanup: {str(e)}")
        
        # Clean up ROS resources
        if node:
            try:
                controller.shutdown()
                node.shutdown()
            except Exception as e:
                print(f"Error during node shutdown: {str(e)}")
        
        # Shutdown ROS
        if rclpy.ok():
            try:
                rclpy.shutdown()
                node.get_logger().info("ROS shutdown complete")
            except Exception as e:
                print(f"Error during ROS shutdown: {str(e)}")
        
        # Wait for ROS thread to complete
        if ros_thread and ros_thread.is_alive():
            try:
                # Give it a reasonable timeout
                ros_thread.join(timeout=2.0)
                if ros_thread.is_alive():
                    print("Warning: ROS thread did not exit cleanly")
            except Exception as e:
                print(f"Error waiting for ROS thread: {str(e)}")
        
        # Final cleanup for Qt
        if app:
            try:
                # Process any pending events before final exit
                app.processEvents()
                # Force cleanup of remaining Qt objects
                app = None
            except Exception as e:
                print(f"Error during final Qt cleanup: {str(e)}")
        
        node.get_logger().info("Cleanup complete, exiting")

if __name__ == '__main__': # pragma: no cover
    sys.exit(main())
