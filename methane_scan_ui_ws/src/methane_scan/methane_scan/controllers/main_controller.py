
import json
import time
from typing import Tuple
from methane_scan.views.main_window import MainWindow # type: ignore

from std_msgs.msg import String as ROSString
import traceback
import rosbag2_py
import subprocess
import pexpect
import threading


class MainController():
    def __init__(self, node):
        self.node = node
        self.initialized = False
        self.widgets_connected = False
        self.dialog_active = False
        
        self._init_parameters()
        #self.init_bag()
        
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
        """
            Inicializa los parámetros necesarios para el controlador.

            Atributos:
                - PTU_position (None): Posición del PTU, inicialmente sin asignar.
                - path (list): Lista vacía para almacenar la trayectoria.
                - PTU_ready (bool): Indicador de si el PTU está listo para operar.
                - robot_speed (None): Velocidad del robot, inicialmente sin asignar.
                - robot_position (None): Posición del robot, inicialmente sin asignar.
                - TDLAS_ready (bool): Indicador de si el sistema TDLAS está listo para operar.
                - ptu_configured (bool): Indicador de si el PTU ha sido configurado.
                - robot_configured (bool): Indicador de si el robot ha sido configurado.
                - tdlas_data_list (list): Lista vacía para almacenar los datos del TDLAS.
                - process (None): Proceso de escritura del rosbag, inicialmente sin asignar.
                - child (None): Proceso hijo para la escritura del rosbag, inicialmente sin asignar.
        """
        self.PTU_position = None
        self.path = []  
        self.PTU_ready = False
        self.robot_speed = None
        self.robot_position = None
        self.TDLAS_ready = False
        self.ptu_configured = False
        self.robot_configured = False
        self.last_ptu_position = None

        self.tdlas_data_list = []
        self.process = None
        self.child = None

    def init_bag(self):
        """
        Inicializa la escritura de un rosbag para registrar datos de TDLAS.

        Esta función realiza los siguientes pasos:
        1. Genera un nombre único para el bag basado en la fecha y hora actuales.
        2. Configura el escritor del rosbag utilizando almacenamiento SQLite y el formato de serialización 'cdr'.
        3. Abre el escritor con las opciones de almacenamiento y conversión definidas.
        4. Crea el topic '/tdlas_data' con la metadata correspondiente, especificando el tipo de mensaje "std_msgs/String" y el formato de serialización "cdr".
        5. Registra en el logger la inicialización exitosa del bag, o bien captura y registra errores en caso de que la creación del topic falle.

        No retorna ningún valor.
        """
        start_time = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        bag_name = f"tdlas_data_bag_{start_time}"
        self.writer = rosbag2_py.SequentialWriter()
        storage_options = rosbag2_py.StorageOptions(uri=bag_name, storage_id='sqlite3')
        converter_options = rosbag2_py.ConverterOptions(
            input_serialization_format='cdr',
            output_serialization_format='cdr'
        )
        self.writer.open(storage_options, converter_options)

        try:
            tdlas_topic = "/tdlas_data"
            tdlas_topic_methadata = rosbag2_py.TopicMetadata(
                name=tdlas_topic,
                type="std_msgs/String",
                serialization_format="cdr",
            )

            self.writer.create_topic(tdlas_topic_methadata)
        except Exception as e:
            self.node.get_logger().error(f"Error creating topic metadata: {str(e)}")
            traceback.print_exc()
        self.node.get_logger().info(f"Bag writer initialized: {bag_name}")

    def _connect_events(self):
        """
        Conecta los eventos de la interfaz de usuario con las funciones correspondientes.
        Este método realiza las siguientes acciones:
        - Verifica si la vista (self.view) está inicializada. Si no lo está, registra un error y retorna.
            - Registra callbacks para la navegación:
                - Configuración del PTU.
                - Página de inicio.
                - Configuración del robot.
        - Conecta los resultados de diálogo para la configuración del PTU y del robot, si dichos diálogos existen.
        - Conecta señales de widgets específicos:
            - Widget de configuración del PTU para actualizar la posición.
            - Pestaña de escaneo de metano para guardar la ruta.
            - Widget de configuración del robot para actualizar la velocidad.
        - Si algún componente no está disponible, se registra una advertencia.
        - Si todos los eventos se conectan exitosamente, se marca self.widgets_connected como True y se registra un mensaje informativo.
        - En caso de producirse alguna excepción durante la conexión de eventos, se captura, registra el error y se imprime la traza.
        
        No se devuelve ningún valor.
        """
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
                
            if hasattr(self.view, 'home_tab') and self.view.home_tab is not None:
                self.view.home_tab.path_saved.connect(self._update_path)
            else:
                self.node.get_logger().warn("Methane scan tab not available for event connection")
                
            if hasattr(self.view, 'robot_config_widget') and self.view.robot_config_widget is not None:
                self.view.robot_config_widget.speed_saved.connect(self._update_robot_speed)
            else:
                self.node.get_logger().warn("Robot config widget not available for event connection")
            
            if hasattr(self.view, 'simulation_tab') and self.view.simulation_tab is not None:
                self.view.simulation_tab.error_signal.connect(self._show_error)

            
                
            self.widgets_connected = True
            self.node.get_logger().info("All UI events connected successfully")
        except Exception as e:
            self.node.get_logger().error(f"Error connecting events: {str(e)}")
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
            self.dialog_active = True
            self.node.get_logger().info("Opening PTU configuration dialog")
            self.view.switch_to_ptu_config()
            self.node.get_logger().info("PTU configuration dialog opened")
        except Exception as e:
            self.dialog_active = False
            self.node.get_logger().error(f"Error opening PTU config dialog: {str(e)}")
            traceback.print_exc()

    def show_home(self):
        """
        Regresa a la pantalla principal cerrando cualquier diálogo abierto.

        Este método verifica que la vista esté inicializada y, en caso afirmativo, 
        cambia la interfaz a la pantalla inicial utilizando el método 'switch_to_home'. 

        También actualiza el estado interno 'dialog_active' a False y registra el cambio de estado.

        Si ocurre algún error durante el proceso, se captura la excepción, se registra un mensaje 
        de error y se imprime la traza del error para facilitar la depuración.
        """
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
            self.dialog_active = True
            self.node.get_logger().info("Opening robot configuration dialog")
            self.view.switch_to_robot_config()
            self.node.get_logger().info("Robot configuration dialog opened")
        except Exception as e:
            self.dialog_active = False
            self.node.get_logger().error(f"Error opening robot config dialog: {str(e)}")
            traceback.print_exc()
            
    def on_dialog_accepted(self):
        """Manejador general para la aceptación del diálogo.

        Este método desactiva el estado activo del diálogo, muestra el área
        principal de la aplicación y registra la acción en el logger. En caso
        de producirse una excepción durante el proceso, se captura la excepción,
        se registra el error y se imprime el traceback correspondiente.

        Raises:
            Exception: Si ocurre un error durante la ejecución del proceso de
                aceptación del diálogo.
        """
        try:
            self.dialog_active = False
            self.node.get_logger().info("Dialog accepted, returning to home")
            self.show_home()
        except Exception as e:
            self.node.get_logger().error(f"Error handling dialog acceptance: {str(e)}")
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
            self.dialog_active = False
            self.node.get_logger().info("PTU configuration cancelled")
            # Additional cleanup if needed
        except Exception as e:
            self.node.get_logger().error(f"Error handling PTU dialog rejection: {str(e)}")
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
            self.dialog_active = False
            self.node.get_logger().info("Robot configuration cancelled")
            # Additional cleanup if needed
        except Exception as e:
            self.node.get_logger().error(f"Error handling robot dialog rejection: {str(e)}")
            traceback.print_exc()
    
    def _update_ptu_position(self, position: Tuple[int, int]):
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
            self.PTU_position = position
            self.node.get_logger().info(f"PTU position updated: {position}")
            
            # Check if view and components are available
            if (self.view is not None and 
                hasattr(self.view, 'home_tab') and 
                self.view.home_tab is not None and
                hasattr(self.view.home_tab, 'map_frame')):
                
                self.view.home_tab.map_frame.drawPTUMarker(position[0], position[1])
                if self.robot_position is None:
                    self.view.home_tab.map_frame.centerMap(position[0], position[1])
            else:
                self.node.get_logger().warn("Could not update map: UI components not available")

            self.check_publish()    
            self.check_PTU_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating PTU position: {str(e)}")
            traceback.print_exc()

    def _update_robot_speed(self, speed : float):
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
            self.robot_speed = speed
            self.node.get_logger().info(f"Robot speed updated: {speed}")
            self.check_Robot_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating robot speed: {str(e)}")
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
            
            self.node.get_logger().info(f"PTU ready status updated: {PTU_ready}")
            self.PTU_ready = PTU_ready
            self.check_PTU_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating PTU ready status: {str(e)}")
            traceback.print_exc()

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
            
            self.node.get_logger().info(f"PTU ready status updated: {TDLAS_ready}")
            self.TDLAS_ready = TDLAS_ready
            self.check_TDLAS_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating PTU ready status: {str(e)}")
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
                
            self.robot_position = position
            self.node.get_logger().info(f"Posición de Hunter actualizada: {position}")
            
            # Check if view and components are available before updating UI
            if (self.view is not None and 
                hasattr(self.view, 'home_tab') and 
                self.view.home_tab is not None and
                hasattr(self.view.home_tab, 'map_frame')):
                
                self.view.home_tab.set_robot_position(position)
                if self.PTU_position is None:
                    self.view.home_tab.map_frame.centerMap(position["lat"], position["lng"])
                self.view.robot_config_widget.set_position(position)
            else:
                self.node.get_logger().warn("Could not update map: UI components not available")
            
            # Update robot ready status
            if not self.robot_configured:
                self.check_Robot_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating hunter position: {str(e)}")
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
            if path is None:
                self.node.get_logger().warn("Received null path")
                return
                
            self.path = path
            self.node.get_logger().info(f"Ruta actualizada: {path}")
            self.check_Robot_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error updating path: {str(e)}")
            traceback.print_exc()
    
    def update_TDLAS_data(self, data : dict):
        """
        Actualiza los datos TDLAS con manejo de errores.

        Recoge el diccionario recibido, valida su contenido y lo procesa para:
            - Almacenar los datos en una lista interna.
            - Actualizar la interfaz gráfica (pestaña de Methane Scan).
            - Extraer y calcular el timestamp utilizando los campos 'sec' y
                'nanosec' del encabezado.
            - Serializar y escribir los datos en el bag de mensajes.
            - Dibujar en el mapa un beam con posiciones y opacidad
                calculada a partir de 'average_ppmxm'.

        Si el dato recibido es None o si algún componente de la interfaz
        no está disponible, se registra una advertencia. En caso de producirse
        alguna excepción durante el proceso, se captura el error, se registra
        y se imprime el traceback.

        Parámetros:
            data (dict): Diccionario con los datos TDLAS, que debe incluir
                         un 'header' con 'stamp', 'sec' y 'nanosec', y la llave
                         'average_ppmxm' para determinar la opacidad.
        """
  
        try:
            if data is None:
                self.node.get_logger().warn("Received null TDLAS data")
                return

            # Store TDLAS data
            self.tdlas_data_list.append(data)

            # Send data to save it
            msg = ROSString()
            msg.data = json.dumps({
                "tdlas_data": data,
                "ptu_position": self.PTU_position,
                "hunter_position": self.robot_position
            })
            self.node.publisher_play_simulation.publish(msg)
                
            # Update TDLAS data in UI if available
            if (self.view is not None and 
                hasattr(self.view, 'home_tab') and 
                self.view.home_tab is not None):

                positions = [(self.PTU_position[0], self.PTU_position[1]), (self.robot_position['lat'], self.robot_position['lng'])]
                opacity = 0.9 * (data.get('average_ppmxm', 0) / 150.0) + 0.1
                
                self.view.home_tab.map_frame.drawBeam(positions, opacity)
            else:
                self.node.get_logger().warn("Could not update TDLAS data: UI components not available")
        except Exception as e:
            self.node.get_logger().error(f"Error updating TDLAS data: {str(e)}")
            traceback.print_exc

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
            self.node.get_logger().info(f"Ha llegado: {self.TDLAS_ready}")

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
                    self.check_all_ready()
        except Exception as e:
            self.node.get_logger().error(f"Error checking TDLAS ready: {str(e)}")
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
            self.node.get_logger().info(f"Ha llegado: {self.PTU_ready} {self.PTU_position}")
            
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
                    self.check_all_ready()
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("Operativo")
            elif (self.PTU_position is not None):
                self.ptu_configured = False
                
                if has_home_tab:
                    self.view.home_tab.set_device_status("PTU", False, ["Confirmación"])
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("No se ha confirmado la posición")
                
            else:
                self.node.get_logger().info("PTU no configurado")
                self.ptu_configured = False
                
                if has_home_tab:
                    self.view.home_tab.set_device_status("PTU", False, ["Posición"])
                if has_ptu_config_widget:
                    self.view.ptu_config_widget.set_state("No se ha configurado la posición")
        except Exception as e:
            self.node.get_logger().error(f"Error checking PTU ready: {str(e)}")
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
                self.check_publish()
                self.check_all_ready()
            else:
                self.view.home_tab.set_device_status("Robot", False, missing)
                
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
        """
        Verifica que todos los dispositivos y componentes necesarios estén listos.

        Esta función comprueba que:
            - La configuración del PTU esté establecida.
            - La configuración del robot se haya realizado.
            - El componente TDLAS esté listo.

        Si se cumplen todas estas condiciones, se registra en el logger que todo está listo y, 
        adicionalmente, se procede a actualizar la interfaz de usuario verificando que:
            - La vista (view) esté inicializada.
            - La pestaña 'home_tab' exista y no sea nula.

        De cumplirse, se indica en la pestaña que el sistema está listo y se habilita el botón de inicio.
        En caso de cualquier excepción durante el proceso, se registra el error y se imprime el traceback.
        """
        ready = (self.ptu_configured and self.robot_configured and self.TDLAS_ready)
        try:
            self.node.get_logger().info(f"Todo listo: {ready}")
            if ready:
                # Check if view is available
                if self.view is None:
                    self.node.get_logger().error("Cannot check Robot ready: view is not initialized")
                    return
                    
                # Check if home_tab is available
                has_home_tab = (hasattr(self.view, 'home_tab') and 
                                    self.view.home_tab is not None)
                
                # Update UI status
                if has_home_tab:
                    self.view.home_tab.set_ready(True)
                    self.view.home_tab.enableStartButton(self.test_start)
        except Exception as e:
            self.node.get_logger().error(f"Error checking all ready: {str(e)}")
            traceback.print_exc()
        
    def check_publish(self):
        """
        Verifica que todos los datos necesarios estén configurados adecuadamente
        para proceder con la publicación de los parámetros del cazador.

        La función realiza las siguientes acciones:
            - Comprueba que la posición del PTU esté definida, que la lista de puntos
              que representa el camino no esté vacía y que la velocidad del robot sea
              mayor que cero.
            - Si se cumplen las condiciones, construye un diccionario con la información
              requerida, lo codifica en formato JSON y publica el mensaje en el tópico
              /initialize_hunter_params.
            - Registra en el log un mensaje informativo indicando que está listo para publicar
              o, en caso de producirse algún error, captura la excepción y registra el error
              en el log, mostrando además la traza de la excepción.
        """
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
        self.process, _ = self._record_ros2_bag(self.node.get_parameter("TOPICS.save_simulation").
                                                value)
        msg = ROSString()
        msg.data = json.dumps({"path": self.path, "speed": self.robot_speed})
        self.node.publisher_start_simulation.publish(msg)

    def _record_ros2_bag(self, topic="/TDLAS_data"):
        bag_name = "tdlas_data_bag_" + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        command = ["ros2", "bag", "record", "-o", bag_name, topic]
        process = subprocess.Popen(command)
        return process, bag_name
    
    def finish_test(self):
        """
        Finaliza el test y cierra el proceso de grabación del bag.

        Este método se encarga de cerrar el proceso de grabación del bag
        y de eliminar el bag asociado al proceso. Se utiliza el logger del
        nodo para registrar un mensaje informativo en caso de cierre exitoso,
        o un mensaje de error junto con el trazo de la excepción si ocurre
        algún problema durante el proceso.
        """
        try:
            if self.process:
                self.process.terminate()
                self.process.wait()
                self.node.get_logger().info("Test finished successfully")
            else:
                self.node.get_logger().warn("No process to terminate")
        except Exception as e:
            self.node.get_logger().error(f"Error finishing test: {str(e)}")
            traceback.print_exc()  
    
    def play_simulation(self, data : dict):
        try:
            if data is None:
                self.node.get_logger().warn("Received null TDLAS data")
                return
            
            # Update TDLAS data in UI if available
            if (self.view is not None and 
                hasattr(self.view, 'simulation_tab') and 
                self.view.simulation_tab is not None):

                positions = [(data.get('ptu_position')[0], data.get('ptu_position')[1]),
                              (data.get('hunter_position')['lat'], data.get('hunter_position')['lng'])]
                opacity = 0.9 * (data.get('tdlas_data').get('average_ppmxm', 0) / 150.0) + 0.1
                robot_pos = positions[1]

                if len(self.view.simulation_tab.save_positions) <= 0:
                    self.node.get_logger().info("No hay posiciones guardadas")
                    self.view.simulation_tab.map_frame.centerMap(robot_pos[0], robot_pos[1])
                
                self.view.simulation_tab.set_robot_position(robot_pos)
                self.view.simulation_tab.map_frame.drawBeam(positions, opacity)
                self.view.simulation_tab.add_data_row(data.get('tdlas_data'))
                self.view.simulation_tab.set_tdlas_data(data.get('tdlas_data'))
                self.view.simulation_tab.save_positions.append({"lat": positions[1][0], "lng": positions[1][1]})

                current_ptu = positions[0]
                if current_ptu != self.last_ptu_position:
                    self.view.simulation_tab.map_frame.drawPTUMarker(current_ptu[0], current_ptu[1])
                    self.last_ptu_position = current_ptu
            else:
                self.node.get_logger().warn("Could not update TDLAS data: UI components not available")
        except Exception as e:
            self.node.get_logger().error(f"Error updating TDLAS data: {str(e)}")
            traceback.print_exc
    
    def _show_error(self, message: str):
        self.node.get_logger().error(message)
    
    def shutdown(self):
        """
        Método shutdown para cerrar el escritor de bag.

        Este método se encarga de cerrar el escritor asignándolo a None, indicando que ya no se utilizará para guardar datos.
        Se utiliza el logger del nodo para registrar un mensaje informativo en caso de cierre exitoso, o un mensaje de error
        junto con el trazo de la excepción si ocurre algún problema durante el proceso.

        """
        try:
            self.writer = None
            self.node.get_logger().info("Bag writer closed successfully")
        except Exception as e:
            self.node.get_logger().error(f"Error closing bag writer: {str(e)}")
            traceback.print_exc()

