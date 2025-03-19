
from methane_scan.views.main_window import MainWindow # type: ignore
from methane_scan.views.pages.ptu_config import PTUConfigWidget # type: ignore

class MainController:
    def __init__(self, node):
        self.node = node
        # Instanciar la vista principal
        self.view = MainWindow()
        # Conectar señales o callbacks para delegar la navegación
        self._connect_events()

    def _init_parameters(self):
        self.PTU_position = None

    def _connect_events(self):
        # Cuando se requiera cambiar a la pantalla de PTU, invocar al método del controlador
        self.view.register_ptu_config_callback(self.show_ptu_config)

        # Conectar el botón de "volver a home" de la pantalla de PTU
        self.view.register_home_callback(self.show_home)

        # Conectar la señal que emite la posición en PTUConfigWidget
        self.view.ptu_config_widget.position_saved.connect(self._update_ptu_position)

    def show_ptu_config(self):
        self.view.switch_to_ptu_config()

    def show_home(self):
        self.view.switch_to_home()

    def _update_ptu_position(self, position):
        self.PTU_position = position
        self.node.get_logger().info(f"Posición de PTU actualizada: {position}")
