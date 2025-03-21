
from methane_scan.views.main_window import MainWindow # type: ignore
from methane_scan.views.pages.ptu_config import PTUConfigWidget # type: ignore

class MainController():
    def __init__(self, node):

        self.node = node
        # Instanciar la vista principal
        self.view = MainWindow()
        # Conectar señales o callbacks para delegar la navegación
        self._connect_events()
        self._init_parameters()

    def _init_parameters(self):
        self.PTU_position = None
        self.path = []  
        self.PTU_ready = False
        self.robot_speed = None
        self.robot_position = None

    def _connect_events(self):
        # Cuando se requiera cambiar a la pantalla de PTU, invocar al método del controlador
        self.view.register_ptu_config_callback(self.show_ptu_config)

        # Conectar el botón de "volver a home" de la pantalla de PTU
        self.view.register_home_callback(self.show_home)

        # Conectar la señal que emite la posición en PTUConfigWidget
        self.view.ptu_config_widget.position_saved.connect(self._update_ptu_position)

        # Conectar el botón de "aplicar cambios"
        self.view.register_apply_callback(self.show_home)
        
        # Conectar la señal que emite la ruta en MethaneScanTab
        self.view.methane_scan_tab.path_saved.connect(self._update_path)

        # Cuando se requiera cambiar a la pantalla del Robot, invocar al método del controlador
        self.view.register_robot_config_callback(self.show_robot_config)

        # Conectar la señal que emite la velocidad en RobotConfigWidget
        self.view.robot_config_widget.speed_saved.connect(self._update_robot_speed)

    def show_ptu_config(self):
        self.view.switch_to_ptu_config()

    def show_home(self):
        self.view.switch_to_home()

    def show_robot_config(self):
        self.view.switch_to_robot_config()

    def _update_ptu_position(self, position):
        self.PTU_position = position
        self.view.methane_scan_tab.map_frame.drawPTUMarker(position[0], position[1])
        self.check_PTU_ready()

    def _update_robot_speed(self, speed):
        self.robot_speed = speed
        self.node.get_logger().info(f"Velocidad actualizada: {speed}")
        self.check_Robot_ready()

    def update_PTU_ready(self, PTU_ready):
        self.node.get_logger().info(f"PTU listo: {PTU_ready}")
        self.PTU_ready = PTU_ready
        self.check_PTU_ready()

    def update_hunter_position(self, position):
        self.robot_position = (float(position['lat']), float(position['lng']))
        self.node.get_logger().info(f"Posición de Hunter actualizada: {position}")
        #self.view.methane_scan_tab.map_frame.drawRobotMarker(float(position['lat']), float(position['lng']))
        self.view.robot_config_widget.set_position(position)
        self.check_Robot_ready()

    def _update_path(self, path):
        self.path = path
        self.node.get_logger().info(f"Ruta actualizada: {path}")
        self.check_Robot_ready()

    def check_PTU_ready(self):
        self.node.get_logger().info(f"Ha llegado: {self.PTU_ready} {self.PTU_position}")
        if(self.PTU_position is not None and self.PTU_ready):
            self.node.get_logger().info(f"Posición de PTU actualizada: {self.PTU_position}")
            self.view.methane_scan_tab.set_device_status("PTU", True)
            self.view.ptu_config_widget.set_state("Operativo")
        elif (self.PTU_position is not None):
            self.view.methane_scan_tab.set_device_status("PTU", False, ["Confirmación"])
            self.view.ptu_config_widget.set_state("No se ha confirmado la posición")
        else:
            self.node.get_logger().info("PTU no configurado")
            self.view.methane_scan_tab.set_device_status("PTU", False, ["Posición"])
            self.view.ptu_config_widget.set_state("No se ha configurado la posición")

    def check_Robot_ready(self):
        self.node.get_logger().info(f"Ha llegado: {self.robot_speed} {self.robot_position} {self.path}")
        if (self.robot_speed is not None and self.robot_position is not None and self.path.__len__() > 0):
            self.view.methane_scan_tab.set_device_status("Robot", True)
        elif (self.robot_speed is not None and self.robot_position is not None):
            self.view.methane_scan_tab.set_device_status("Robot", False, ["Trayectoria"])
        elif (self.robot_speed is not None):
            self.view.methane_scan_tab.set_device_status("Robot", False, ["Posición"])
        else:
            self.view.methane_scan_tab.set_device_status("Robot", False, ["Velocidad"])