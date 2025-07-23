import traceback
from PyQt5.QtCore import pyqtSignal, QObject

import dotenv
import os
import requests
from std_msgs.msg import String as ROSString
from ..views.components.toast import Toast

class _RobotSignals(QObject):
    robotReady = pyqtSignal(bool)
    dialogActive = pyqtSignal(bool)

class RobotController:
    def __init__(self, node, view):
        self.node = node
        self.view = view
        self.signals = _RobotSignals()
        self._init_parameters()
        self.node.get_logger().info("RobotController initialized")

    def _init_parameters(self):
        self.robot_speed = None
        self.robot_position = None
        self.robot_configured = False
        self.path = []

    def update_robot_speed(self, speed : float):
        """
        Actualiza la velocidad del robot.

        Este método asigna el valor de `speed` a la variable
        `robot_speed` y registra la acción. Si ocurre alguna
        excepción durante la actualización, se captura, se
        registra el error y se imprime la traza de la excepción.

        Parameters:
            speed (float): Valor numérico que indica la nueva velocidad del
                   robot.
        """
        """Update robot speed with error handling"""
        try:
            if self.robot_speed is not None and speed == self.robot_speed:
                self.node.get_logger().info("No change in robot speed")
                return
            self.robot_speed = speed
            
            self.node.get_logger().info(f"Robot speed updated: {speed}")
            self.check_Robot_ready()
            Toast(f"¡Posición del robot actualizada a {speed} m/s", self.view, "info", 3000).show()
        except TypeError as e:
            Toast("Error: la velocidad debe ser un número", self.view, "error", 3000).show()
            self.node.get_logger().error(f"TypeError updating robot speed: {e}")
            traceback.print_exc()
        except ValueError as e:
            Toast("Error: valor de velocidad fuera de rango", self.view, "error", 3000).show()
            self.node.get_logger().error(f"ValueError updating robot speed: {e}")
            traceback.print_exc()
        except AttributeError as e:
            Toast("Error interno: componente de UI no disponible", self.view, "error", 3000).show()
            self.node.get_logger().error(f"AttributeError updating robot speed: {e}")
            traceback.print_exc()
        except Exception as e:
            Toast(f"Error al actualizar la velocidad del robot: {e}", self.view, "error", 3000).show()
            self.node.get_logger().error(f"Unexpected error updating robot speed: {e}")
            traceback.print_exc()
    
    def update_hunter_position(self, position : dict):
        """
        Actualiza la posición de Hunter y la interfaz de usuario.

        Esta función recibe un diccionario con la posición del robot y
        actualiza la posición interna. Se comprueba si el diccionario es
        válido y, en caso de serlo, se actualiza la posición del robot.
        Si la interfaz de usuario y sus componentes están disponibles,
        también se actualizan los widgets correspondientes. Además, se
        verifica el estado de configuración del robot.

        Parameters:
            position (dict): Diccionario que contiene la posición del 
            robot. Se esperan los valores necesarios para actualizar la
            ubicación.
        
        Raises:
            Se captura cualquier excepción que se
            produzca durante la actualización, registrando la causa
            y mostrando la traza de error.
        """
        try:
            if not position:
                self.node.get_logger().warn("Received null hunter position")
                return
                
            if position == self.robot_position:
                self.node.get_logger().info("No change in hunter position")
                return
            
            # Check if view and components are available before updating UI
            if (self.view is not None and 
                hasattr(self.view, 'home_tab') and 
                self.view.home_tab is not None and
                hasattr(self.view.home_tab, 'map_frame')):
                if self.robot_position is None:
                    Toast(f"¡Posición de Hunter actualizada!", self.view, "info", 3000).show()
                self.view.home_tab.set_robot_position(position)
                self.view.robot_config_widget.set_position(position)
            else:
                self.node.get_logger().warn("Could not update map: UI components not available")

            self.robot_position = position
            self.node.get_logger().info(f"Posición de Hunter actualizada: {position}")
            
            # Update robot ready status
            if not self.robot_configured:
                self.check_Robot_ready()
        except TypeError as e:
            Toast(
            "Formato de posición inválido.",
            self.view, "error", 3000
            ).show()
            self.node.get_logger().error(f"TypeError updating hunter position: {e}")
            traceback.print_exc()
        except KeyError as e:
            Toast(
            f"Error: falta la clave '{e.args[0]}' en la posición del robot",
            self.view, "error", 3000
            ).show()
            self.node.get_logger().error(f"KeyError updating hunter position: {e}")
            traceback.print_exc()
        except AttributeError as e:
            Toast(
            "Error interno: componente de UI no disponible para actualizar la posición",
            self.view, "error", 3000
            ).show()
            self.node.get_logger().error(f"AttributeError updating hunter position: {e}")
            traceback.print_exc()
        except Exception as e:
            Toast(
            f"Error inesperado al actualizar la posición de Hunter",
            self.view, "error", 3000
            ).show()
            self.node.get_logger().error(f"Unexpected error updating hunter position: {e}")
            traceback.print_exc()

    def _update_path(self, path : list):
        """
        Actualiza la ruta y verifica el estado del robot.

        Si la ruta es None, se emite una advertencia y no se realiza
        ninguna actualización. En caso contrario, se actualiza la
        ruta del objeto y se registra la acción, seguido de la
        verificación del estado del robot.

        Parámetros:
            path (list): Nueva ruta que se debe establecer. Puede ser None.

        Excepciones:
            Captura cualquier excepción durante la actualización, 
            registra el error y muestra el traceback.
        """
        try:
            if path == [None]:
                self.node.get_logger().warn("Received null path")
                self.path = []
                Toast("¡No se ha seleccionado ninguna trayectoria!", self.view, "warning", 3000).show() # pragma: no cover
                self.check_Robot_ready()
                return
            if path == []:
                self.path = []
                self.node.get_logger().warn("empty path")
                self.check_Robot_ready()
                return
                
            self.path = path
            Toast(f"¡Trayectoria actualizada!", self.view, "info", 3000).show() # pragma: no cover
            self.node.get_logger().info(f"Ruta actualizada: {path}")
            self.check_Robot_ready()
        except TypeError as e:
            Toast(
            "Error: formato de trayectoria inválido",
            self.view, "error", 3000
            ).show() # pragma: no cover
            self.node.get_logger().error(f"TypeError updating path: {e}")
            traceback.print_exc()
        except ValueError as e:
            Toast(
            f"Error: valor inválido en la trayectoria ",
            self.view, "error", 3000
            ).show() # pragma: no cover
            self.node.get_logger().error(f"ValueError updating path: {e}")
            traceback.print_exc()
        except AttributeError as e:
            Toast(
            "Error interno: componente de UI no disponible al actualizar la trayectoria",
            self.view, "error", 3000
            ).show() # pragma: no cover
            self.node.get_logger().error(f"AttributeError updating path: {e}")
            traceback.print_exc()
        except Exception as e:
            Toast(
            f"Error inesperado al actualizar la trayectoria",
            self.view, "error", 3000
            ).show() # pragma: no cover
            self.node.get_logger().error(f"Unexpected error updating path: {e}")
            traceback.print_exc()

    def check_Robot_ready(self):
        """
        Verifica que el robot esté listo comprobando la disponibilidad
        de los widgets requeridos y la validez de la configuración del robot,
        incluyendo velocidad, posición y trayectoria.

        Detalles:
            - Registra información básica sobre velocidad, posición y trayectoria.
            - Comprueba que la vista (view) esté inicializada; en caso contrario, registra un error.
            - Verifica la existencia y disponibilidad de 'home_tab' en la vista.
            - Evalúa si 'robot_speed' es válida (mayor a 0).
            - Evalúa que 'robot_position' no sea nula.
            - Evalúa que 'path' contenga datos válidos (lista no vacía).
            - Actualiza el estado de configuración del robot ('robot_configured') basado en la presencia
              de todos los parámetros requeridos.
            - Dependiendo de los parámetros verificados, actualiza el estado del dispositivo en el widget
              'home_tab', indicando si el robot está listo o qué parámetros faltan.
            - Si está disponible, actualiza el widget 'robot_config_widget' mostrando el estado operativo
              o los elementos faltantes necesarios.
            - En caso de cualquier excepción, captura el error e imprime el traceback correspondiente en el log.
        """
        try:
            self.node.get_logger().info(f"Ha llegado: {self.robot_speed} {self.robot_position} {self.path}")
            
            # Check if view is available
            if self.view is None:
                self.node.get_logger().error("Cannot check Robot ready: view is not initialized")
                return
                
            # Check if home_tab is available
            has_home_tab = (hasattr(self.view, 'home_tab') and 
                                   self.view.home_tab is not None)
            if not has_home_tab:
                self.node.get_logger().error("Cannot check Robot ready: home_tab is not available")
                return
                
            missing = []
            
            if not self.robot_speed or self.robot_speed <= 0:
                missing.append("Velocidad")
            
            if self.robot_position is None:
                missing.append("Posición")
            
            if not self.path or len(self.path) == 0:
                missing.append("Trayectoria")
            
            # Update robot configuration status
            self.robot_configured = len(missing) == 0
            
            # Update UI status
            if not missing:
                self.view.home_tab.set_device_status("Robot", True)
                self.signals.robotReady.emit(self.robot_configured)
            else:
                self.view.home_tab.set_device_status("Robot", False, missing)
                
            # Update robot config widget if available
            if (hasattr(self.view, 'robot_config_widget') and 
                self.view.robot_config_widget is not None):
                
                if not missing:
                    self.view.robot_config_widget.set_state("Operativo")
                    return True
                else:
                    missing_str = ", ".join(missing)
                    self.view.robot_config_widget.set_state(f"Falta: {missing_str}")
                    return False
        except Exception as e:
            self.node.get_logger().error(f"Error checking Robot ready: {str(e)}")
            traceback.print_exc()

    def show_robot_config(self):
        """
        Muestra el diálogo de configuración del robot e informa de cada cambio
        en el estado de la vista.

        Si la vista no está inicializada, se registra un error y se retorna sin
        realizar ninguna acción. Durante la ejecución, se activa la bandera
        'dialog_active' para controlar el estado del diálogo. 
        Se registran mensajes de información y de error utilizando el logger del nodo, 
        de forma que se notifique la apertura correcta o la ocurrencia de alguna excepción.

        Excepciones:
            - Captura y registra cualquier excepción que se produzca al intentar
            - cambiar la vista a la configuración del robot.
        """
        if self.view is None:
            self.node.get_logger().error("Cannot show robot config: view is not initialized")
            return
            
        try:
            self.signals.dialogActive.emit(True)
            self.node.get_logger().info("Opening robot configuration dialog")
            self.view.switch_to_robot_config()
            self.node.get_logger().info("Robot configuration dialog opened")
        except Exception as e:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().error(f"Error opening robot config dialog: {str(e)}")
            traceback.print_exc()

    def on_robot_dialog_accepted(self):
        """
        Gestiona la aceptación del diálogo de configuración del robot.

        Desactiva el estado activo del diálogo y registra la aceptación en el
        logger del nodo. 
        
        Si se dispone del widget de configuración del robot,
        se extrae el valor de la velocidad y se actualiza la configuración
        correspondiente. 
        
        En caso de que el widget no esté disponible, se
        registra una advertencia. Si ocurre cualquier excepción durante el
        proceso, se captura y se registra el error, mostrando además la traza
        para facilitar la depuración.
        """
        try:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().info("Robot configuration accepted")
            # Process any final robot configuration data if needed
            if hasattr(self.view, 'robot_config_widget') and self.view.robot_config_widget is not None:
                # Update robot with final configuration values
                speed = self.view.robot_config_widget.speed
                if speed:
                    self.update_robot_speed(speed)
            else:
                self.node.get_logger().warn("Robot config widget not available for final data retrieval")
        except Exception as e:
            self.node.get_logger().error(f"Error handling robot dialog acceptance: {str(e)}")
            traceback.print_exc()

    def on_robot_dialog_rejected(self):
        """
        Maneja el rechazo del diálogo de configuración del robot.

        Esta función marca el diálogo como inactivo y registra un mensaje
        informativo indicando que la configuración del robot ha sido
        cancelada. Adicionalmente, se pueden realizar tareas de limpieza
        si es necesario. En caso de ocurrir alguna excepción, el error se
        registra detalladamente.

        Raises:
            Exception: Captura cualquier excepción que se genere durante
            el manejo del rechazo del diálogo.
        """
        try:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().info("Robot configuration cancelled")
            # Additional cleanup if needed
        except Exception as e:
            self.node.get_logger().error(f"Error handling robot dialog rejection: {str(e)}")
            traceback.print_exc()

    def on_trajectory_dialog_accepted(self):
        """
        Maneja la aceptación del diálogo de selección de trayectoria.

        Desactiva el estado activo del diálogo y registra la aceptación en el
        logger del nodo. Si se dispone del widget de selección de trayectoria,
        se extrae la trayectoria seleccionada y se actualiza la configuración
        correspondiente. En caso de que el widget no esté disponible, se
        registra una advertencia. Si ocurre cualquier excepción durante el
        proceso, se captura y se registra el error, mostrando además la traza
        para facilitar la depuración.
        """
        try:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().info("Trajectory selection accepted")
            # Process any final trajectory data if needed
            if hasattr(self.view, 'select_trajectory_widget') and self.view.select_trajectory_widget is not None:
                # Update robot with final trajectory values
                trajectory = self.view.select_trajectory_widget.selected_trajectory
                if trajectory:
                    self._update_path(trajectory)
            else:
                self.node.get_logger().warn("Trajectory selection widget not available for final data retrieval")
        except Exception as e:
            self.node.get_logger().error(f"Error handling trajectory dialog acceptance: {str(e)}")
            traceback.print_exc()

    def on_trajectory_dialog_rejected(self):
        """
        Maneja el rechazo del diálogo de selección de trayectoria.

        Esta función marca el diálogo como inactivo y registra un mensaje
        informativo indicando que la selección de trayectoria ha sido
        cancelada. Adicionalmente, se pueden realizar tareas de limpieza
        si es necesario. En caso de ocurrir alguna excepción, el error se
        registra detalladamente.

        Raises:
            Exception: Captura cualquier excepción que se genere durante
            el manejo del rechazo del diálogo.
        """
        try:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().info("Trajectory selection cancelled")
            # Additional cleanup if needed
        except Exception as e:
            self.node.get_logger().error(f"Error handling trajectory dialog rejection: {str(e)}")
            traceback.print_exc()

    def show_trajectory_config(self):
        """
        Muestra el diálogo de seleccion de Trayectoria.
        Este método verifica si la vista está inicializada antes de intentar mostrar el diálogo de configuración.
        Si la vista no está inicializada, registra un error y aborta la operación. Durante la ejecución, se actualiza
        el estado de la variable `dialog_active` para evitar conflictos. Se registran mensajes en el log tanto para la
        apertura exitosa del diálogo como para cualquier error que se produzca, en cuyo caso se imprime el traceback.
        Raises:
            Exception: Si ocurre un error inesperado al intentar cambiar al diálogo de configuración del PTU.
        """
        if self.view is None:
            self.node.get_logger().error("Cannot show PTU config: view is not initialized")
            return
            
        try:
            self.signals.dialogActive.emit(True)
            self.node.get_logger().info("Opening path dialog")
            self.view.switch_to_select_trajectory()
            self.node.get_logger().info("Path dialog opened")
        except Exception as e:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().error(f"Error opening Path dialog: {str(e)}")
            traceback.print_exc()


    