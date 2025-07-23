
import json
import time
from typing import Tuple
from methane_scan.controllers.robot_controller import RobotController
from methane_scan.controllers.tdlas_controller import TDLASController
from methane_scan.controllers.ptu_controller import PTUController
from methane_scan.views.main_window import MainWindow # type: ignore
from methane_scan.views.components.toast import Toast # type: ignore

from rclpy.node import Node

from std_msgs.msg import String as ROSString
from std_msgs.msg import Bool as ROSBool
from diagnostic_msgs.msg import KeyValue
import traceback
from PyQt5.QtCore import pyqtSlot
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
            self.robot_controller = RobotController(node, self.view)
            self.tdlas_controller = TDLASController(node, self.view)
            self.ptu_controller = PTUController(node, self.view)

            # Connect signals and callbacks
            self._connect_events()
            self._connect_signals()

            self.initialized = True
            self.node.get_logger().info("MainController initialized successfully")
        except Exception as e:
            self.node.get_logger().error(f"Error initializing MainController: {str(e)}")
            traceback.print_exc()
            self.view = None

    def _connect_signals(self):
        """
        Conecta las señales de la vista a los slots del controlador.

        Este método se encarga de conectar las señales emitidas por los
        componentes de los sub-controladores a los métodos correspondientes en el
        controlador.

        No retorna ningún valor.
        """
        try:
            # Connect signals from RobotController
            self.robot_controller.signals.robotReady.connect(self.check_publish)
            self.robot_controller.signals.robotReady.connect(self.check_all_ready)
            self.robot_controller.signals.dialogActive.connect(self._on_dialog_active)

            # Connect signals from TDLASController
            self.tdlas_controller.signals.tdlasReady.connect(self.check_all_ready)

            # Connect signals from PTUController
            self.ptu_controller.signals.ptuReady.connect(self.check_all_ready)
            self.ptu_controller.signals.ptuPosition.connect(self.check_publish)
            self.ptu_controller.signals.dialogActive.connect(self._on_dialog_active)

        except Exception as e:
            self.node.get_logger().error(f"Error connecting signals: {str(e)}")
            traceback.print_exc()

    def _on_dialog_active(self, active: bool):
        """Slot que actualiza self.dialog_active cuando el PTU o el robot abre/cierra su diálogo."""
        self.dialog_active = active

    def _init_parameters(self):
        """
            Inicializa los parámetros necesarios para el controlador.

            Atributos:
                - tdlas_data_list (list): Lista vacía para almacenar los datos del TDLAS.
                - process (None): Proceso de escritura del rosbag, inicialmente sin asignar.
                - child (None): Proceso hijo para la escritura del rosbag, inicialmente sin asignar.
        """
        self.tdlas_data_list = []
        self.process = None
        self.child = None
        self.simulation_running = False
        self.hunter_initialized = False
        self.mqtt_bridge_connected = True
        self.mqtt_connection_connected = True


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
            self.node.get_logger().error("Cannot connect events: view isW not initialized")
            return

        try:
            # Ensure self.view is not None before accessing its attributes
            if self.view is None:
                raise AttributeError("View is not initialized")
            
            # Navigation callbacks
            self.view.register_ptu_config_callback(self.ptu_controller.show_ptu_config)
            self.view.register_home_callback(self.show_home)
            self.view.register_robot_config_callback(self.robot_controller.show_robot_config)
            self.view.register_select_trajectory_callback(self.robot_controller.show_trajectory_config)

            # Connect dialog results
            if hasattr(self.view, 'ptu_config_dialog') and self.view.ptu_config_dialog is not None:
                self.view.ptu_config_dialog.accepted.connect(self.ptu_controller.on_ptu_dialog_accepted)
                self.view.ptu_config_dialog.rejected.connect(self.ptu_controller.on_ptu_dialog_rejected)
            else:
                self.node.get_logger().warn("PTU config dialog not available for event connection")
            
            if hasattr(self.view, 'robot_config_dialog') and self.view.robot_config_dialog is not None:
                self.view.robot_config_dialog.accepted.connect(self.robot_controller.on_robot_dialog_accepted)
                self.view.robot_config_dialog.rejected.connect(self.robot_controller.on_robot_dialog_rejected)
            else:
                self.node.get_logger().warn("Robot config dialog not available for event connection")

            if hasattr(self.view, 'select_trajectory_dialog') and self.view.select_trajectory_dialog is not None:
                self.view.select_trajectory_dialog.accepted.connect(self.robot_controller.on_trajectory_dialog_accepted)
                self.view.select_trajectory_dialog.rejected.connect(self.robot_controller.on_trajectory_dialog_rejected)
                
            # Connect widget signals if available
            if hasattr(self.view, 'ptu_config_widget') and self.view.ptu_config_widget is not None:
                self.view.ptu_config_widget.position_saved.connect(self.ptu_controller.update_ptu_position)
            else:
                self.node.get_logger().warn("PTU config widget not available for event connection")
                
            if hasattr(self.view, 'home_tab') and self.view.home_tab is not None:
                self.view.home_tab.path_saved.connect(self.robot_controller._update_path)
                self.view.home_tab.start_stop_signal.connect(self.pause_test)
                self.view.home_tab.map_frame.javaScriptConsoleMessage.connect(self._show_error)
                self.view.home_tab.logger_signal.connect(self._show_info)
            else:
                self.node.get_logger().warn("Methane scan tab not available for event connection")
                
            if hasattr(self.view, 'robot_config_widget') and self.view.robot_config_widget is not None:
                self.view.robot_config_widget.speed_saved.connect(self.robot_controller.update_robot_speed)
            else:
                self.node.get_logger().warn("Robot config widget not available for event connection")
            
            if hasattr(self.view, 'simulation_tab') and self.view.simulation_tab is not None:
                self.view.simulation_tab.error_signal.connect(self._show_error)
                
            self.widgets_connected = True
            self.node.get_logger().info("All UI events connected successfully")
        except Exception as e:
            self.node.get_logger().error(f"Error connecting events: {str(e)}")
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
        if not self.simulation_running:
            self.node.get_logger().warn("Simulation is not running, cannot update TDLAS data")
            return
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
                "ptu_position": self.ptu_controller.PTU_position,
                "hunter_position": self.robot_controller.robot_position
            })
            self.node.publisher_play_simulation.publish(msg)
                
            # Update TDLAS data in UI if available
            if (self.view is not None and 
                hasattr(self.view, 'home_tab') and 
                self.view.home_tab is not None):

                positions = [(self.ptu_controller.PTU_position[0], self.ptu_controller.PTU_position[1]), (self.robot_controller.robot_position['Latitude'], self.robot_controller.robot_position['Longitude'])]
                avg_ppm = data.get('average_ppmxm', 0)
                fraction = max(0.0, min(avg_ppm / 150.0, 1.0))

                if fraction < 0.33:
                    color = "#00FF00"  # Green
                elif fraction < 0.66:
                    color = "#FFFF00"  # Yellow
                elif fraction < 1.0:
                    color = "#FFA500"  # Orange
                else:
                    color = "#FF0000"  # Red

                self.view.home_tab.map_frame.drawBeam(positions, color)
                self.view.home_tab.set_tdlas_data(data)
                self.view.home_tab.set_robot_position(self.robot_controller.robot_position)

            else:
                self.node.get_logger().warn("Could not update TDLAS data: UI components not available")
        except Exception as e:
            self.node.get_logger().error(f"Error updating TDLAS data: {str(e)}")
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
        ready = (self.ptu_controller.ptu_configured and self.robot_controller.robot_configured and self.tdlas_controller.TDLAS_ready)
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
                    self.view.home_tab.enableStartButtonCallback(self.test_start, self.finish_test)
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
            if not self.hunter_initialized and self.ptu_controller.PTU_position and len(self.robot_controller.path) > 0 and self.robot_controller.robot_speed > 0:
                self.node.get_logger().info("Listo para publicar")

                # Publish /initialize_hunter_params
                info = {
                    "vel": self.robot_controller.robot_speed, 
                    "point_ptu": {"latitude_ptu": self.ptu_controller.PTU_position[0], 
                                  "longitude_ptu": self.ptu_controller.PTU_position[1]},
                    "points": self.robot_controller.path
                }
                json_info = json.dumps(info)
                msg = KeyValue()
                msg.key = self.node.get_parameter("TOPICS.initialize_hunter").value
                msg.value = json_info
                self.node.publisher_Hunter_initialized.publish(msg)
                self.node.get_logger().info(f"Publicado /initialize_hunter_params: {json_info}")
                self.hunter_initialized = True
        except Exception as e:
            self.node.get_logger().error(f"Error checking publish readiness: {str(e)}")
            traceback.print_exc()

    def test_start(self):
        """Test start button callback"""
        self.node.get_logger().info("Botón de inicio presionado")
        self.process, _ = self._record_ros2_bag(self.node.get_parameter("TOPICS.save_simulation").
                                                value)
        self.simulation_running = True
        self.view.home_tab.disableStartButton()
        msg = KeyValue()
        msg.key = self.node.get_parameter("TOPICS.start_stop_hunter").value
        msg.value = "True"
        self.node.publisher_start_stop_hunter.publish(msg)

    def _record_ros2_bag(self, topic="/TDLAS_data"):
        bag_name = "experiments/tdlas_data_bag_" + time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        command = ["ros2", "bag", "record", "-o", bag_name, topic]
        process = subprocess.Popen(command)
        return process, bag_name
    
    def pause_test(self, state: bool):
        """
        Pausa el test y cierra el proceso de grabación del bag.

        Este método se encarga de pausar el proceso de grabación del bag
        y de eliminar el bag asociado al proceso. Se utiliza el logger del
        nodo para registrar un mensaje informativo en caso de pausa exitosa,
        o un mensaje de error junto con el trazo de la excepción si ocurre
        algún problema durante el proceso.
        """
        self.node.get_logger().info("Test paused")
        
        msg = KeyValue()
        msg.key = self.node.get_parameter("TOPICS.start_stop_hunter").value
        msg.value = f"{state}"
        self.node.publisher_start_stop_hunter.publish(msg)
    
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
                self.simulation_running = False
                self.node.get_logger().info("Test finished successfully")
                self.view.home_tab.enableStartButton()
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
                avg_ppm = data.get('tdlas_data').get('average_ppmxm', 0) 
                fraction = max(0.0, min(avg_ppm / 150.0, 1.0))

                if fraction < 0.33:
                    color = "#00FF00"  # Green
                elif fraction < 0.66:
                    color = "#FFFF00"  # Yellow
                elif fraction < 1.0:
                    color = "#FFA500"  # Orange
                else:
                    color = "#FF0000"  # Red
                robot_pos = positions[1]

                if len(self.view.simulation_tab.save_positions) <= 0:
                    self.node.get_logger().info("No hay posiciones guardadas")
                    self.view.simulation_tab.map_frame.centerMap(robot_pos[0], robot_pos[1])
                
                self.view.simulation_tab.set_robot_position(robot_pos)
                self.view.simulation_tab.map_frame.drawBeam(positions, color)
                self.view.simulation_tab.add_data_row(data.get('tdlas_data'))
                self.view.simulation_tab.set_tdlas_data(data.get('tdlas_data'))
                self.view.simulation_tab.save_positions.append({"lat": positions[1][0], "lng": positions[1][1]})

                current_ptu = positions[0]
                if current_ptu != self.ptu_controller.last_ptu_position:
                    self.view.simulation_tab.map_frame.drawPTUMarker(current_ptu[0], current_ptu[1])
                    self.ptu_controller.last_ptu_position = current_ptu
            else:
                self.node.get_logger().warn("Could not update TDLAS data: UI components not available")
        except Exception as e:
            self.node.get_logger().error(f"Error updating TDLAS data: {str(e)}")
            traceback.print_exc
    
    def _show_error(self, message: str):
        self.node.get_logger().error(message)

    def _show_info(self, message: str):
        self.node.get_logger().info(message)

    def set_mqtt_connection_status(self, status: bool):
        """
        Actualiza el estado de conexión MQTT en la interfaz gráfica.

        Este método se encarga de actualizar el estado de conexión MQTT
        en la interfaz gráfica, utilizando el logger del nodo para registrar
        un mensaje informativo o de error según corresponda.

        Parámetros:
            status (bool): Estado de conexión MQTT (True si está conectado,
                           False si no lo está).
        """
        self.node.get_logger().info(f"MQTT connection status in MainController: {status}")
        if self.view is not None and hasattr(self.view, 'titleBar') and self.view.home_tab is not None:
            self.view.titleBar.set_mqtt_bridge_status(status)
            if not status and self.mqtt_connection_connected:
                Toast("MQTT Bridge está desconectado", self.view, "error").show()
                self.mqtt_connection_connected = False
            elif status and not self.mqtt_connection_connected: 
                Toast("MQTT Bridge está conectado", self.view, "info").show()
                self.mqtt_connection_connected = True
        else:
            self.node.get_logger().warn("Cannot update MQTT connection status: view is not initialized")

    def set_mqtt_bridge_status(self, status: bool):
        """
        Actualiza el estado del puente MQTT en la interfaz gráfica.

        Este método se encarga de actualizar el estado del puente MQTT
        en la interfaz gráfica, utilizando el logger del nodo para registrar
        un mensaje informativo o de error según corresponda.

        Parámetros:
            status (bool): Estado del puente MQTT (True si está conectado,
                           False si no lo está).
        """
        if self.view is not None and hasattr(self.view, 'titleBar') and self.view.home_tab is not None:
            self.view.titleBar.set_mqtt_status(status)
            if not status and self.mqtt_bridge_connected:
                self.mqtt_bridge_connected = False
                Toast("El cliente MQTT ha perdido la conexión. Reconectando...", self.view, "error").show()
            elif status and not self.mqtt_bridge_connected:
                Toast("Cliente MQTT conectado", self.view, "info").show()
                self.mqtt_bridge_connected = True
        else:
            self.node.get_logger().warn("Cannot update MQTT bridge status: view is not initialized")
    
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

