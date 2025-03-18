
from methane_scan.views.main_window import MainWindow # type: ignore
from methane_scan.views.pages.ptu_config import PTUConfigWidget # type: ignore

class MainController:
    def __init__(self, node):
        self.node = node
        # Instanciar la vista principal
        self.view = MainWindow()
        # Conectar señales o callbacks para delegar la navegación
        self._connect_events()

    def _connect_events(self):
        # Cuando se requiera cambiar a la pantalla de PTU, invocar al método del controlador
        self.view.register_ptu_config_callback(self.show_ptu_config)

        # Conectar el botón de "volver a home" de la pantalla de PTU
        self.view.register_home_callback(self.show_home)

    def show_ptu_config(self):
        self.view.switch_to_ptu_config()

    def show_home(self):
        self.view.switch_to_home()
