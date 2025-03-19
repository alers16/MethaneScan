import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QToolBar, QAction, QStackedWidget, 
    QGraphicsScene
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon, QPixmap
from methane_scan.views.pages.ptu_config import PTUConfigWidget # type: ignore
import platform
from methane_scan.views.components.map_view import SatelliteMap, MyWebEnginePage # type: ignore
import os
from dotenv import load_dotenv
from methane_scan.views.components.title_bar import TitleBar # type: ignore
from methane_scan.views.pages.home_page import HomePage # type: ignore
import methane_scan.qresources_rc  # type: ignore # Tu archivo de recursos compilado

config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.abspath(os.path.join(config_dir, ".env"))
if os.path.isfile(env_path):
    load_dotenv(env_path)
    print("Archivo .env cargado correctamente.")
else:
    print("No se encontró el archivo .env.")

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MethaneScan")
        self.resize(600, 400)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Cargar hojas de estilo desde archivos qss en el mismo nivel
        current_dir = os.path.dirname(__file__)
        light_qss_path = os.path.join(current_dir, "light_style.qss")
        dark_qss_path = os.path.join(current_dir, "dark_style.qss")
        try:
            with open(light_qss_path, "r") as file:
                self.light_style = file.read()
        except Exception as e:
            print("No se pudo cargar light_style.qss:", e)
            self.light_style = ""
        try:
            with open(dark_qss_path, "r") as file:
                self.dark_style = file.read()
        except Exception as e:
            print("No se pudo cargar dark_style.qss:", e)
            self.dark_style = ""

        # Aplicamos inicialmente la hoja de estilo (modo oscuro, por ejemplo)
        self.setStyleSheet(self.dark_style)
        self.current_theme = "dark"

        # Crear widget central y layout principal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Añadimos la custom title bar (siempre visible)
        self.titleBar = TitleBar(self)
        self.titleBar.setStyleSheet("background-color: #1C1C1C;")
        main_layout.addWidget(self.titleBar)

        # Creamos el QStackedWidget para cambiar el contenido
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Construimos la pantalla principal (pestaña MethaneScan)
        self.methane_scan_tab = HomePage(API_KEY)

        # Creamos la pantalla de configuración (por ejemplo, PTU Config)
        self.ptu_config_widget = PTUConfigWidget()

        # Añadimos ambas pantallas al stacked widget
        self.stacked_widget.addWidget(self.methane_scan_tab)        # Índice 0: Pantalla principal
        self.stacked_widget.addWidget(self.ptu_config_widget)         # Índice 1: Pantalla de configuración

        # Inicia mostrando la pantalla principal
        self.stacked_widget.setCurrentIndex(0)
    
    def resizeEvent(self, event):
        """Callback que se activa cada vez que la ventana cambia de tamaño."""
        super().resizeEvent(event)
        screen_rect = QApplication.primaryScreen().availableGeometry()
        
        new_width = int(screen_rect.width() * 0.8)
        new_height = int(screen_rect.height() * 0.8)
        self.methane_scan_tab.map_frame.setMinimumSize(new_width, new_height)
    
    def toggle_theme(self):
        """Cambia entre modo claro y oscuro."""
        if self.toggle_theme_action.isChecked():
            self.setStyleSheet(self.dark_style)
            self.current_theme = "dark"
            self.toggle_theme_action.setText("Modo Claro")
        else:
            self.setStyleSheet(self.light_style)
            self.current_theme = "light"
            self.toggle_theme_action.setText("Modo Oscuro")
    
    # Métodos para registrar callbacks (desde el controlador)
    def register_ptu_config_callback(self, callback):
        self.methane_scan_tab.register_ptu_config_callback(callback)

    def register_home_callback(self, callback):
        self.ptu_config_widget.register_home_callback(callback)
        self.titleBar.register_home_callback(callback)

    # Métodos para cambiar la pantalla
    def switch_to_ptu_config(self):
        self.stacked_widget.setCurrentWidget(self.ptu_config_widget)

    def switch_to_home(self):
        self.stacked_widget.setCurrentWidget(self.methane_scan_tab)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()



