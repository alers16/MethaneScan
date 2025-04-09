import sys
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import cv2
import numpy as np
import configparser as cp
import json
from methane_scan.controllers.main_controller import MainController  # type: ignore
from PyQt5 import QtWidgets, QtGui, QtCore
import os
import time
import traceback
from typing import Optional, Dict, Any, Callable

# Signal class for thread-safe communication between ROS and Qt
class RosQtSignals(QtCore.QObject):
    ptu_ready_signal = QtCore.pyqtSignal(bool)
    hunter_position_signal = QtCore.pyqtSignal(dict)
    TDLAS_ready_signal = QtCore.pyqtSignal(bool)
    TDLAS_data_signal = QtCore.pyqtSignal(dict)
    log_message_signal = QtCore.pyqtSignal(str, str)  # level, message
    end_simulation_signal = QtCore.pyqtSignal(bool)

class MethaneScanNode(Node):
    """ROS2 node with thread-safety and proper resource management for MethaneScan."""
    
    def __init__(self):
        super().__init__('methane_scan_node')

        # Declare parameters and initialize state
        self.declare_parameters_ros()
        
        # Thread synchronization
        self._lock = threading.RLock()
        self.signals = RosQtSignals()
        
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
        
        
        # Initialize callbacks with safe no-op functions
        self._callback_ptu_ready: Optional[Callable[[bool], None]] = None
        self._callback_hunter_position: Optional[Callable[[Dict[str, Any]], None]] = None
        self._callback_TDLAS_ready: Optional[Callable[[bool], None]] = None
        self._callback_TDLAS_data: Optional[Callable[[Dict[str, Any]], None]] = None
        self._callback_end_simulation: Optional[Callable[[bool], None]] = None
        
        # Connect Qt signals to thread-safe handler methods
        self.signals.ptu_ready_signal.connect(self._handle_ptu_ready_qt)
        self.signals.hunter_position_signal.connect(self._handle_hunter_position_qt)
        self.signals.TDLAS_ready_signal.connect(self._handle_TDLAS_ready_qt)
        self.signals.log_message_signal.connect(self._handle_log_message_qt)
        self.signals.TDLAS_data_signal.connect(self._handle_TDLAS_data_qt)
        self.signals.end_simulation_signal.connect(self._handle_end_simulation_qt)
        
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
                String,
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

            self.publisher_Hunter_initialized = self.create_publisher(String, 
                                                                      self.get_parameter('TOPICS.initialize_hunter').value,
                                                                      10)
            self.publisher_start_simulation = self.create_publisher(String,
                                                                    self.get_parameter('TOPICS.start_hunter').value,
                                                                    10)

            self._initialized = True
            self.get_logger().info('MethaneScanNode initialized successfully')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize MethaneScanNode: {str(e)}')
            traceback.print_exc()
            self._initialized = False

    def declare_parameters_ros(self):
        self.declare_parameter('TOPICS.ptu_ready', "/PTU_ready")
        self.declare_parameter('TOPICS.hunter_position', "/hunter_position")
        self.declare_parameter('TOPICS.tdlas_ready', "/TDLAS_ready")
        self.declare_parameter('TOPICS.tdlas_data', "/TDLAS_data")
        self.declare_parameter('TOPICS.initialize_hunter', "/initialize_hunter_params")
        self.declare_parameter('TOPICS.start_hunter', "/start_simulation")
        self.declare_parameter('TOPICS.end_simulation', "/end_simulation")
    
    def register_callbacks(self, ptu_ready_callback, hunter_position_callback, TDLAS_ready_callback, TDLAS_data_callback,
                           end_simulation_callback):
        """Register callbacks with thread-safe protection."""
        with self._lock:
            self._callback_ptu_ready = ptu_ready_callback
            self._callback_hunter_position = hunter_position_callback
            self._callback_TDLAS_ready = TDLAS_ready_callback
            self._callback_TDLAS_data = TDLAS_data_callback
            self._callback_end_simulation = end_simulation_callback
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
            data = json.loads(msg.data)
            
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


def main(args=None):
    """Main function with proper resource management and error handling."""
    executor = None
    node = None
    ros_thread = None
    app = None
    controller = None
    timer = None
    
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
            
        controller.view.show()
        
        # Register callbacks in a thread-safe way
        node.register_callbacks(
            ptu_ready_callback=controller.update_PTU_ready,
            hunter_position_callback=controller.update_hunter_position,
            TDLAS_ready_callback=controller.update_TDLAS_ready,
            TDLAS_data_callback=controller.update_TDLAS_data,
            end_simulation_callback=controller.finish_test
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

if __name__ == '__main__':
    sys.exit(main())
