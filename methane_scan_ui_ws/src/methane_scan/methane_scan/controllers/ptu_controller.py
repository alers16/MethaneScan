
from typing import Tuple
import traceback
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QLabel

from ..views.components.toast import Toast
from ..views.main_window import MainWindow

class _PTUSignals(QObject):
    dialogActive = pyqtSignal(bool)
    ptuReady      = pyqtSignal(bool)
    ptuPosition   = pyqtSignal(bool)


class PTUController():
    def __init__(self, node, view: MainWindow):
        self.node = node
        self.view = view
        self.signals = _PTUSignals()
        self._init_parameters()

    def _init_parameters(self):
        self.PTU_position = None 
        self.PTU_ready = False
        self.ptu_configured = False
        self.last_ptu_position = None
        self.first_update = True

    def update_ptu_position(self, position: dict):
        """
        Actualiza la posición del PTU y la interfaz de usuario asociada.

        Parameters:
            position (Tuple[int,int]): Coordenadas (x, y) de la posición del PTU. Se espera
                que sea una tupla o lista con dos elementos. Si es None, se emite
                una advertencia y no se realiza la actualización.
                
        Proceso:
            1. Valida que position no sea None.
            2. Actualiza la posición interna del PTU y registra la operación.
            3. Verifica la disponibilidad de los componentes de la interfaz:
               a. Si la vista y el mapa están disponibles, dibuja el marcador del
                  PTU en el mapa.
               b. De lo contrario, registra una advertencia.
            4. Ejecuta comprobaciones adicionales mediante check_publish y
               check_PTU_ready.
            5. Captura y registra cualquier excepción que se produzca durante el
               proceso, imprimiendo la traza del error.
        """
        if position is None:
            self.node.get_logger().warn("Received null position for PTU")
            return
        
            
        try:
            self.PTU_position = [position['lat'], position['lng']]
            self.node.get_logger().info(f"PTU position updated: {position}")
            
            # Check if view and components are available
            if (self.view is not None and 
                hasattr(self.view, 'home_tab') and 
                self.view.home_tab is not None and
                hasattr(self.view.home_tab, 'map_frame')):
                
                toast = Toast("¡Posición de la PTU Actualizada!", self.view, toast_type=Toast.INFO)
                if self.PTU_position is None:
                    toast.show()
                self.view.ptu_config_widget.set_position(self.PTU_position[0], self.PTU_position[1])
                self.view.home_tab.map_frame.drawPTUMarker(self.PTU_position[0], self.PTU_position[1])
                if self.first_update:
                    self.view.home_tab.map_frame.centerMap(self.PTU_position[0], self.PTU_position[1])
                    self.first_update = False
                
            else:
                self.node.get_logger().warn("Could not update map: UI components not available")

            self.signals.ptuPosition.emit(True)    
            self.check_PTU_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating PTU position: {str(e)}")
            traceback.print_exc()

    def update_PTU_ready(self, PTU_ready : bool):
        """
        Actualiza el estado de disponibilidad del PTU.
        Este método realiza lo siguiente:
            - Verifica si el valor de PTU_ready es nulo; en ese caso, registra una advertencia
              y detiene la actualización.
            - Si PTU_ready tiene un valor válido, actualiza el estado y registra la
              actualización.
            - Llama al método check_PTU_ready para continuar con la verificación de
              la disponibilidad.
            - Si ocurre cualquier excepción durante la actualización, se registra un
              error y se imprime el traceback para facilitar el debug.
        Parameters:
            PTU_ready (bool): Estado que indica si el PTU está listo.
        """
        try:
            if PTU_ready is None:
                self.node.get_logger().warn("Received null PTU_ready status")
                return
            
            self.PTU_ready = PTU_ready
            self.node.get_logger().info(f"PTU ready status updated: {PTU_ready}")
            # dentro de update_PTU_ready, justo después de node.get_logger().info(...)
            # create a frameless, transient label as toast
            toast = Toast("¡Confirmación de la PTU Recibida!", self.view, toast_type=Toast.INFO)
            toast.show()
            self.check_PTU_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating PTU ready status: {str(e)}")
            traceback.print_exc()

    def check_PTU_ready(self):
        """
        Verifica el estado de preparación del PTU (Unidad de Pan-Tilt) mediante la comprobación
        de la disponibilidad de los componentes de la interfaz de usuario y actualiza el estado
        del dispositivo según la información obtenida.
        
        Pasos del método:
            1. Registra información preliminar sobre el estado actual del PTU y su posición.
            2. Verifica que la vista (UI) esté inicializada. Si no lo está, registra un error y
               termina el proceso.
            3. Comprueba si existen los componentes:
                 - La pestaña 'home_tab' destinada a mostrar el inicio.
                 - El widget 'ptu_config_widget' encargado de representar la configuración
                   de la PTU.
            4. Actualiza el estado del PTU en función de la disponibilidad de su posición
               y del valor de PTU_ready:
                 - Si la posición está definida y PTU está listo:
                     a. Registra la nueva posición.
                     b. Marca el PTU como configurado.
                     c. Actualiza el estado en la pestaña y elimina cualquier aviso de error.
                     d. Invoca 'check_all_ready' para verificar la preparación global.
                 - Si sólo la posición está disponible pero PTU aún no está listo:
                     a. Marca el PTU como no configurado.
                     b. Actualiza la pestaña para indicar que falta la confirmación.
                     c. Notifica a través del widget que la posición no ha sido confirmada.
                 - Si la posición no está disponible:
                     a. Registra que el PTU no se encuentra configurado.
                     b. Actualiza la pestaña y el widget para señalar la ausencia de la posición.
            5. Captura y registra cualquier excepción que ocurra durante la ejecución.

        Este método no retorna ningún valor, pero actualiza
        el estado interno del controlador y la interfaz de usuario según las condiciones evaluadas.
        """
        try:
            self.node.get_logger().info(f"Ha llegado en PTU: {self.PTU_ready} {self.PTU_position}")
            
            # Check if view and UI components are available
            if self.view is None:
                self.node.get_logger().error("Cannot check PTU ready: view is not initialized")
                return
                
            has_home_tab = (hasattr(self.view, 'home_tab') and 
                                   self.view.home_tab is not None)
            has_ptu_config_widget = (hasattr(self.view, 'ptu_config_widget') and 
                                    self.view.ptu_config_widget is not None)
            
            # Update PTU status based on current state
            if(self.PTU_position is not None and self.PTU_ready):
                self.node.get_logger().info(f"Posición de PTU actualizada: {self.PTU_position}")
                self.ptu_configured = True
                
                if has_home_tab:
                    self.view.home_tab.set_device_status("PTU", True)
                    self.signals.ptuReady.emit(True)
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("Operativo")
                
                return True  # PTU is ready and configured
            elif (self.PTU_position is not None):
                self.ptu_configured = False
                self.node.get_logger().info("PTU solo tiene posición")
                
                if has_home_tab:
                    self.view.home_tab.set_device_status("PTU", False, ["Confirmación"])
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("No se ha confirmado la detección del patrón")
                
                return False  # PTU is not ready, but has position
                
            else:
                self.node.get_logger().info("PTU no configurado")
                self.ptu_configured = False
                
                if has_home_tab:
                    self.view.home_tab.set_device_status("PTU", False, ["Posición"])
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("No se ha configurado la posición")

                return False  # PTU is not configured
        except Exception as e:
            self.node.get_logger().error(f"Error checking PTU ready: {str(e)}")
            traceback.print_exc()

    def show_ptu_config(self):
        """
        Muestra el diálogo de configuración del PTU.
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
            self.node.get_logger().info("Opening PTU configuration dialog")
            self.view.switch_to_ptu_config()
            self.node.get_logger().info("PTU configuration dialog opened")
        except Exception as e:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().error(f"Error opening PTU config dialog: {str(e)}")
            traceback.print_exc()
        
    def on_ptu_dialog_accepted(self):
        """
        Maneja la aceptación del diálogo de configuración PTU.

        Este método realiza las siguientes acciones:
            - Desactiva el indicador de actividad del diálogo.
            - Informa mediante el logger que se ha aceptado la configuración PTU.
            - Si existe el widget de configuración PTU y contiene una posición, actualiza la posición del PTU.
            - Emite una advertencia si el widget de configuración PTU no está disponible para recuperar los datos finales.

        En caso de ocurrir una excepción, se captura y se registra el error,
        imprimiendo además la traza para facilitar la depuración.
        """
        try:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().info("PTU configuration accepted")
            # Process any final PTU configuration data if needed
            if hasattr(self.view, 'ptu_config_widget') and self.view.ptu_config_widget is not None:
                position = self.view.ptu_config_widget.PTU_coordinates
                if position:
                    self.update_ptu_position(position)
            else:
                self.node.get_logger().warn("PTU config widget not available for final data retrieval")
        except Exception as e:
            self.node.get_logger().error(f"Error handling PTU dialog acceptance: {str(e)}")
            traceback.print_exc()

    def on_ptu_dialog_rejected(self):
        """
        Gestiona el rechazo del diálogo de configuración PTU.

        Realiza las siguientes acciones:
            - Marca el diálogo como inactivo.
            - Registra la cancelación en el logger del nodo.
            - En caso de error, captura la excepción, registra el fallo
              y muestra la traza del error.

        No retorna ningún valor.
        """
        try:
            self.signals.dialogActive.emit(False)
            self.node.get_logger().info("PTU configuration cancelled")
            # Additional cleanup if needed
        except Exception as e:
            self.node.get_logger().error(f"Error handling PTU dialog rejection: {str(e)}")
            traceback.print_exc()