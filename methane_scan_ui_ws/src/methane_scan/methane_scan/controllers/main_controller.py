
import json
from methane_scan.views.main_window import MainWindow # type: ignore
from methane_scan.views.pages.ptu_config import PTUConfigWidget # type: ignore

from PyQt5.QtCore import QMetaObject, Qt, QTimer
from std_msgs.msg import String as ROSString
import traceback

class MainController():
    def __init__(self, node):
        self.node = node
        self.initialized = False
        self.widgets_connected = False
        self.dialog_active = False
        
        self._init_parameters()
        
        try:
            self.view = MainWindow()
            # Connect signals and callbacks
            self._connect_events()
            self.initialized = True
            self.node.get_logger().info("MainController initialized successfully")
        except Exception as e:
            self.node.get_logger().error(f"Error initializing MainController: {str(e)}")
            traceback.print_exc()
            self.view = None

    def _init_parameters(self):
        self.PTU_position = None
        self.path = []  
        self.PTU_ready = False
        self.robot_speed = None
        self.robot_position = None
        self.TDLAS_ready = False
    
        self.ptu_configured = False
        self.robot_configured = False

    def _connect_events(self):
        if self.view is None:
            self.node.get_logger().error("Cannot connect events: view is not initialized")
            return
        
        try:
            # Navigation callbacks
            self.view.register_ptu_config_callback(self.show_ptu_config)
            self.view.register_home_callback(self.show_home)
            self.view.register_robot_config_callback(self.show_robot_config)
            
            # Connect dialog results
            if hasattr(self.view, 'ptu_config_dialog') and self.view.ptu_config_dialog is not None:
                self.view.ptu_config_dialog.accepted.connect(self.on_ptu_dialog_accepted)
                self.view.ptu_config_dialog.rejected.connect(self.on_ptu_dialog_rejected)
            else:
                self.node.get_logger().warn("PTU config dialog not available for event connection")
            
            if hasattr(self.view, 'robot_config_dialog') and self.view.robot_config_dialog is not None:
                self.view.robot_config_dialog.accepted.connect(self.on_robot_dialog_accepted)
                self.view.robot_config_dialog.rejected.connect(self.on_robot_dialog_rejected)
            else:
                self.node.get_logger().warn("Robot config dialog not available for event connection")
                
            # Connect widget signals if available
            if hasattr(self.view, 'ptu_config_widget') and self.view.ptu_config_widget is not None:
                self.view.ptu_config_widget.position_saved.connect(self._update_ptu_position)
            else:
                self.node.get_logger().warn("PTU config widget not available for event connection")
                
            if hasattr(self.view, 'methane_scan_tab') and self.view.methane_scan_tab is not None:
                self.view.methane_scan_tab.path_saved.connect(self._update_path)
            else:
                self.node.get_logger().warn("Methane scan tab not available for event connection")
                
            if hasattr(self.view, 'robot_config_widget') and self.view.robot_config_widget is not None:
                self.view.robot_config_widget.speed_saved.connect(self._update_robot_speed)
            else:
                self.node.get_logger().warn("Robot config widget not available for event connection")
                
            self.widgets_connected = True
            self.node.get_logger().info("All UI events connected successfully")
        except Exception as e:
            self.node.get_logger().error(f"Error connecting events: {str(e)}")
            traceback.print_exc()
        

    def show_ptu_config(self):
        """Show PTU configuration dialog with error handling"""
        if self.view is None:
            self.node.get_logger().error("Cannot show PTU config: view is not initialized")
            return
            
        try:
            self.dialog_active = True
            self.node.get_logger().info("Opening PTU configuration dialog")
            self.view.switch_to_ptu_config()
            self.node.get_logger().info("PTU configuration dialog opened")
        except Exception as e:
            self.dialog_active = False
            self.node.get_logger().error(f"Error opening PTU config dialog: {str(e)}")
            traceback.print_exc()

    def show_home(self):
        """Return to home screen by closing any open dialogs"""
        if self.view is None:
            self.node.get_logger().error("Cannot show home: view is not initialized")
            return
            
        try:
            self.view.switch_to_home()
            self.dialog_active = False
            self.node.get_logger().info("Returned to home screen")
        except Exception as e:
            self.node.get_logger().error(f"Error returning to home: {str(e)}")
            traceback.print_exc()

    def show_robot_config(self):
        """Show robot configuration dialog with error handling"""
        if self.view is None:
            self.node.get_logger().error("Cannot show robot config: view is not initialized")
            return
            
        try:
            self.dialog_active = True
            self.node.get_logger().info("Opening robot configuration dialog")
            self.view.switch_to_robot_config()
            self.node.get_logger().info("Robot configuration dialog opened")
        except Exception as e:
            self.dialog_active = False
            self.node.get_logger().error(f"Error opening robot config dialog: {str(e)}")
            traceback.print_exc()
            
    def on_dialog_accepted(self):
        """General handler for dialog acceptance"""
        try:
            self.dialog_active = False
            self.node.get_logger().info("Dialog accepted, returning to home")
            self.show_home()
        except Exception as e:
            self.node.get_logger().error(f"Error handling dialog acceptance: {str(e)}")
            traceback.print_exc()
            
    def on_ptu_dialog_accepted(self):
        """Handle PTU configuration dialog acceptance"""
        try:
            self.dialog_active = False
            self.node.get_logger().info("PTU configuration accepted")
            # Process any final PTU configuration data if needed
            if hasattr(self.view, 'ptu_config_widget') and self.view.ptu_config_widget is not None:
                position = self.view.ptu_config_widget.PTU_coordinates
                if position:
                    self._update_ptu_position(position)
            else:
                self.node.get_logger().warn("PTU config widget not available for final data retrieval")
        except Exception as e:
            self.node.get_logger().error(f"Error handling PTU dialog acceptance: {str(e)}")
            traceback.print_exc()
            
    def on_ptu_dialog_rejected(self):
        """Handle PTU configuration dialog rejection"""
        try:
            self.dialog_active = False
            self.node.get_logger().info("PTU configuration cancelled")
            # Additional cleanup if needed
        except Exception as e:
            self.node.get_logger().error(f"Error handling PTU dialog rejection: {str(e)}")
            traceback.print_exc()
            
    def on_robot_dialog_accepted(self):
        """Handle robot configuration dialog acceptance"""
        try:
            self.dialog_active = False
            self.node.get_logger().info("Robot configuration accepted")
            # Process any final robot configuration data if needed
            if hasattr(self.view, 'robot_config_widget') and self.view.robot_config_widget is not None:
                # Update robot with final configuration values
                speed = self.view.robot_config_widget.speed
                if speed:
                    self._update_robot_speed(speed)
            else:
                self.node.get_logger().warn("Robot config widget not available for final data retrieval")
        except Exception as e:
            self.node.get_logger().error(f"Error handling robot dialog acceptance: {str(e)}")
            traceback.print_exc()
            
    def on_robot_dialog_rejected(self):
        """Handle robot configuration dialog rejection"""
        try:
            self.dialog_active = False
            self.node.get_logger().info("Robot configuration cancelled")
            # Additional cleanup if needed
        except Exception as e:
            self.node.get_logger().error(f"Error handling robot dialog rejection: {str(e)}")
            traceback.print_exc()

    def _update_ptu_position(self, position):
        """Update PTU position with error handling"""
        if position is None:
            self.node.get_logger().warn("Received null position for PTU")
            return
            
        try:
            self.PTU_position = position
            self.node.get_logger().info(f"PTU position updated: {position}")
            
            # Check if view and components are available
            if (self.view is not None and 
                hasattr(self.view, 'methane_scan_tab') and 
                self.view.methane_scan_tab is not None and
                hasattr(self.view.methane_scan_tab, 'map_frame')):
                
                self.view.methane_scan_tab.map_frame.drawPTUMarker(position[0], position[1])
            else:
                self.node.get_logger().warn("Could not update map: UI components not available")

            self.check_publish()    
            self.check_PTU_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating PTU position: {str(e)}")
            traceback.print_exc()

    def _update_robot_speed(self, speed):
        """Update robot speed with error handling"""
        try:
            self.robot_speed = speed
            self.node.get_logger().info(f"Robot speed updated: {speed}")
            self.check_Robot_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating robot speed: {str(e)}")
            traceback.print_exc()

    def update_PTU_ready(self, PTU_ready):
        """Update PTU ready status with error handling"""
        try:
            if PTU_ready is None:
                self.node.get_logger().warn("Received null PTU_ready status")
                return
            
            self.node.get_logger().info(f"PTU ready status updated: {PTU_ready}")
            self.PTU_ready = PTU_ready
            self.check_PTU_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating PTU ready status: {str(e)}")
            traceback.print_exc()

    def update_TDLAS_ready(self, TDLAS_ready):
        """Update TDLAS ready status with error handling"""
        try:
            if TDLAS_ready is None:
                self.node.get_logger().warn("Received null TDLAS_ready status")
                return
            
            self.node.get_logger().info(f"PTU ready status updated: {TDLAS_ready}")
            self.TDLAS_ready = TDLAS_ready
            self.check_TDLAS_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating PTU ready status: {str(e)}")
            traceback.print_exc()

    def update_hunter_position(self, position):
        """Update hunter position with error handling and null checks"""
        try:
            if not position:
                self.node.get_logger().warn("Received null hunter position")
                return
                
            self.robot_position = position
            self.node.get_logger().info(f"Posición de Hunter actualizada: {position}")
            
            # Check if view and components are available before updating UI
            if (self.view is not None and 
                hasattr(self.view, 'methane_scan_tab') and 
                self.view.methane_scan_tab is not None and
                hasattr(self.view.methane_scan_tab, 'map_frame')):
                
                # Update map with hunter position
                self.view.methane_scan_tab.map_frame.drawRobotMarker(
                    position.get('lat', 0), 
                    position.get('lng', 0)
                )

                self.view.robot_config_widget.set_position(position)
            else:
                self.node.get_logger().warn("Could not update map: UI components not available")
            
            # Update robot ready status
            if not self.robot_configured:
                self.check_Robot_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating hunter position: {str(e)}")
            traceback.print_exc()

    def _update_path(self, path):
        """Update path with error handling"""
        try:
            if path is None:
                self.node.get_logger().warn("Received null path")
                return
                
            self.path = path
            self.node.get_logger().info(f"Ruta actualizada: {path}")
            self.check_Robot_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating path: {str(e)}")
            traceback.print_exc()
    
    def update_TDLAS_data(self, data):
        """Update TDLAS data with error handling"""
        try:
            if data is None:
                self.node.get_logger().warn("Received null TDLAS data")
                return
                
            self.node.get_logger().info(f"Datos de TDLAS actualizados: {data}")
            # Update TDLAS data in UI if available
            if (self.view is not None and 
                hasattr(self.view, 'methane_scan_tab') and 
                self.view.methane_scan_tab is not None):

                positions = [(self.PTU_position[0], self.PTU_position[1]), (self.robot_position['lat'], self.robot_position['lng'])]
                opacity = 0.9 * (data.get('average_ppmxm', 0) / 150.0) + 0.1
                
                self.view.methane_scan_tab.map_frame.drawBeam(positions, opacity)
            else:
                self.node.get_logger().warn("Could not update TDLAS data: UI components not available")
        except Exception as e:
            self.node.get_logger().error(f"Error updating TDLAS data: {str(e)}")
            traceback.print_exc

    def check_TDLAS_ready(self):
        """Check TDLAS readiness with proper widget availability checks"""
        try:
            self.node.get_logger().info(f"Ha llegado: {self.TDLAS_ready}")

            # Check if view and UI components are available
            if self.view is None:
                self.node.get_logger().error("Cannot check TDLAS ready: view is not initialized")
                return
            has_methane_scan_tab = (hasattr(self.view, 'methane_scan_tab') and
                                    self.view.methane_scan_tab is not None)
            
            # Update TDLAS status based on current state
            if self.TDLAS_ready:
                if has_methane_scan_tab:
                    self.view.methane_scan_tab.set_device_status("TDLAS", True)
                    self.check_all_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error checking TDLAS ready: {str(e)}")
            traceback.print_exc()
        

    def check_PTU_ready(self):
        """Check PTU readiness with proper widget availability checks"""
        try:
            self.node.get_logger().info(f"Ha llegado: {self.PTU_ready} {self.PTU_position}")
            
            # Check if view and UI components are available
            if self.view is None:
                self.node.get_logger().error("Cannot check PTU ready: view is not initialized")
                return
                
            has_methane_scan_tab = (hasattr(self.view, 'methane_scan_tab') and 
                                   self.view.methane_scan_tab is not None)
            has_ptu_config_widget = (hasattr(self.view, 'ptu_config_widget') and 
                                    self.view.ptu_config_widget is not None)
            
            # Update PTU status based on current state
            if(self.PTU_position is not None and self.PTU_ready):
                self.node.get_logger().info(f"Posición de PTU actualizada: {self.PTU_position}")
                self.ptu_configured = True
                
                if has_methane_scan_tab:
                    self.view.methane_scan_tab.set_device_status("PTU", True)
                    self.check_all_ready()
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("Operativo")
            elif (self.PTU_position is not None):
                self.ptu_configured = False
                
                if has_methane_scan_tab:
                    self.view.methane_scan_tab.set_device_status("PTU", False, ["Confirmación"])
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("No se ha confirmado la posición")
                
            else:
                self.node.get_logger().info("PTU no configurado")
                self.ptu_configured = False
                
                if has_methane_scan_tab:
                    self.view.methane_scan_tab.set_device_status("PTU", False, ["Posición"])
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("No se ha configurado la posición")
        except Exception as e:
            self.node.get_logger().error(f"Error checking PTU ready: {str(e)}")
            traceback.print_exc()

    def check_Robot_ready(self):
        """Check Robot readiness with proper widget availability checks"""
        try:
            self.node.get_logger().info(f"Ha llegado: {self.robot_speed} {self.robot_position} {self.path}")
            
            # Check if view is available
            if self.view is None:
                self.node.get_logger().error("Cannot check Robot ready: view is not initialized")
                return
                
            # Check if methane_scan_tab is available
            has_methane_scan_tab = (hasattr(self.view, 'methane_scan_tab') and 
                                   self.view.methane_scan_tab is not None)
            if not has_methane_scan_tab:
                self.node.get_logger().error("Cannot check Robot ready: methane_scan_tab is not available")
                return
                
            missing = []
            
            if self.robot_speed <= 0:
                missing.append("Velocidad")
            
            if self.robot_position is None:
                missing.append("Posición")
            
            if not self.path or len(self.path) == 0:
                missing.append("Trayectoria")
            
            # Update robot configuration status
            self.robot_configured = len(missing) == 0
            
            # Update UI status
            if not missing:
                self.view.methane_scan_tab.set_device_status("Robot", True)
                self.check_publish()
                self.check_all_ready()
            else:
                self.view.methane_scan_tab.set_device_status("Robot", False, missing)
                
            # Update robot config widget if available
            if (hasattr(self.view, 'robot_config_widget') and 
                self.view.robot_config_widget is not None):
                
                if not missing:
                    self.view.robot_config_widget.set_state("Operativo")
                else:
                    missing_str = ", ".join(missing)
                    self.view.robot_config_widget.set_state(f"Falta: {missing_str}")
        except Exception as e:
            self.node.get_logger().error(f"Error checking Robot ready: {str(e)}")
            traceback.print_exc()

    def check_all_ready(self):
        """Check all devices readiness"""
        ready = (self.ptu_configured and self.robot_configured and self.TDLAS_ready)
        try:
            self.node.get_logger().info(f"Todo listo: {ready}")
            if ready:
                # Check if view is available
                if self.view is None:
                    self.node.get_logger().error("Cannot check Robot ready: view is not initialized")
                    return
                    
                # Check if methane_scan_tab is available
                has_methane_scan_tab = (hasattr(self.view, 'methane_scan_tab') and 
                                    self.view.methane_scan_tab is not None)
                
                # Update UI status
                if has_methane_scan_tab:
                    self.view.methane_scan_tab.enableStartButton(self.test_start)
        except Exception as e:
            self.node.get_logger().error(f"Error checking all ready: {str(e)}")
            traceback.print_exc()
        
    def check_publish(self):
        """Check if all data is ready to publish"""
        try:
            if self.PTU_position and len(self.path) > 0 and self.robot_speed > 0:
                self.node.get_logger().info("Listo para publicar")

                # Publish /initialize_hunter_params
                info = {
                    "vel": self.robot_speed, 
                    "point_ptu": {"latitude_ptu": self.PTU_position[0], 
                                  "longitude_ptu": self.PTU_position[1]},
                    "points": self.path
                }
                json_info = json.dumps(info)
                msg = ROSString()
                msg.data = json_info
                self.node.publisher_Hunter_initialized.publish(msg)
                self.node.get_logger().info(f"Publicado /initialize_hunter_params: {json_info}")
        except Exception as e:
            self.node.get_logger().error(f"Error checking publish readiness: {str(e)}")
            traceback.print_exc()

    def test_start(self):
        """Test start button callback"""
        self.node.get_logger().info("Botón de inicio presionado")
        msg = ROSString()
        msg.data = json.dumps({"path": self.path, "speed": self.robot_speed})
        self.node.publisher_start_simulation.publish(msg)

