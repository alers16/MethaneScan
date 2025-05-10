import traceback
from std_msgs.msg import String as ROSString
from PyQt5.QtCore import pyqtSignal, QObject
import json

from ..views.components.toast import Toast
class _TDLASSignals(QObject):
    tdlasReady = pyqtSignal(bool)

class TDLASController():
    tdlasReadySignal = pyqtSignal(bool)
    def __init__(self, node, view):
        self.node = node
        self.view = view
        self._init_parameters()
        self.signals = _TDLASSignals()
    
    def _init_parameters(self):
        self.TDLAS_ready = False

    def update_TDLAS_ready(self, TDLAS_ready : bool):
        """
        Actualiza el estado de 'TDLAS_ready' con manejo
        de errores.

        Si 'TDLAS_ready' es None, se registra una advertencia y
        se termina la función. En otro caso, se actualiza el
        estado y se llama a 'check_TDLAS_ready' para verificar
        la actualización.

        Parameters:
            TDLAS_ready (bool): Indicador del estado de
            disponibilidad de TDLAS.
        Raises:
            Exception: Se captura y registra cualquier error
            durante la actualización, mostrando la traza.
        """
        try:
            if TDLAS_ready is None:
                self.node.get_logger().warn("Received null TDLAS_ready status")
                return
            
            Toast("¡Confirmación de TDLAS recibida!", self.view, "info", 3000)
            self.node.get_logger().info(f"TDLAS ready status updated: {TDLAS_ready}")
            self.TDLAS_ready = TDLAS_ready
            self.check_TDLAS_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating TDLAS ready status: {str(e)}")
            traceback.print_exc()

    def check_TDLAS_ready(self):
        """
        Verifica la disponibilidad del TDLAS y actualiza el estado del dispositivo en la interfaz de usuario.
        
        Este método realiza las siguientes acciones:
            - Registra el estado actual de TDLAS usando el logger asociado al nodo.
            - Comprueba si la vista ('view') está inicializada; en caso contrario, registra un error.
            - Verifica que exista y esté asignada la pestaña 'home_tab' en la vista.
            - Si TDLAS está listo y la pestaña existe, actualiza el estado del dispositivo TDLAS en la interfaz
              y llama a check_all_ready() para verificar el estado general.

        Manejo de errores:
            - Se capturan y registran todas las excepciones que se puedan generar durante la ejecución del método.
        """
        try:
            self.node.get_logger().info(f"Ha llegado TDLAS: {self.TDLAS_ready}")

            # Check if view and UI components are available
            if self.view is None:
                self.node.get_logger().error("Cannot check TDLAS ready: view is not initialized")
                return
            has_home_tab = (hasattr(self.view, 'home_tab') and
                                    self.view.home_tab is not None)
            
            # Update TDLAS status based on current state
            if self.TDLAS_ready:
                if has_home_tab:
                    self.view.home_tab.set_device_status("TDLAS", True)
                    self.signals.tdlasReady.emit(True)
        except Exception as e:
            self.node.get_logger().error(f"Error checking TDLAS ready: {str(e)}")
            traceback.print_exc()