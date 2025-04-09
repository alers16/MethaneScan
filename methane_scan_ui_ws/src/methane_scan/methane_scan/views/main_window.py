import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QToolBar, QAction, QDialog,
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
from methane_scan.views.pages.robot_config import RobotConfigWidget # type: ignore
import methane_scan.qresources_rc  # type: ignore # Tu archivo de recursos compilado

config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.abspath(os.path.join(config_dir, ".env"))
if os.path.isfile(env_path):
    load_dotenv(env_path)
    print("Archivo .env cargado correctamente.")
else:
    print("No se encontró el archivo .env.")

# Add error handling for API_KEY initialization
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if API_KEY is None:
    print("WARNING: GOOGLE_MAPS_API_KEY not found in environment variables")
    print("Maps functionality may be limited or unavailable")
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

        # Construimos la pantalla principal (pestaña MethaneScan)
        self.methane_scan_tab = HomePage(API_KEY)
        main_layout.addWidget(self.methane_scan_tab)
        
        # Creamos los diálogos de configuración como QDialog
        self.ptu_config_dialog = QDialog(self)
        self.ptu_config_dialog.setWindowTitle("Configuración PTU")
        ptu_dialog_layout = QVBoxLayout(self.ptu_config_dialog)
        ptu_dialog_layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        self.ptu_config_widget = PTUConfigWidget(self)
        self.ptu_config_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        ptu_dialog_layout.addWidget(self.ptu_config_widget)
        self.ptu_config_dialog.setModal(True)
        
        # Connect dialog signals
        self.ptu_config_widget.accepted.connect(self.ptu_config_dialog.accept)
        self.ptu_config_widget.rejected.connect(self.ptu_config_dialog.reject)
        
        # Diálogo de configuración del robot
        self.robot_config_dialog = QDialog(self)
        self.robot_config_dialog.setWindowTitle("Configuración Robot")
        robot_dialog_layout = QVBoxLayout(self.robot_config_dialog)
        robot_dialog_layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        self.robot_config_widget = RobotConfigWidget(self)
        self.robot_config_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        robot_dialog_layout.addWidget(self.robot_config_widget)
        self.robot_config_dialog.setModal(True)
        
        # Connect dialog signals
        self.robot_config_widget.accepted.connect(self.robot_config_dialog.accept)
        self.robot_config_widget.rejected.connect(self.robot_config_dialog.reject)
    
    def resizeEvent(self, event):
        """Callback que se activa cada vez que la ventana cambia de tamaño."""
        super().resizeEvent(event)
        screen_rect = QApplication.primaryScreen().availableGeometry()
        
        new_width = int(screen_rect.width() * 0.5)
        new_height = int(screen_rect.height() * 0.5)
        # Set the size of the map in the main tab
        self.methane_scan_tab.map_frame.setMinimumSize(new_width, new_height)
        
        # Let dialogs size themselves based on their content
        # No fixed sizing for dialogs to allow them to adapt to their content
    
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
    
    def register_ptu_config_callback(self, callback):
        self.methane_scan_tab.register_ptu_config_callback(callback)

    def register_robot_config_callback(self, callback):
        self.methane_scan_tab.register_robot_config_callback(callback)

    def register_home_callback(self, callback):
        self.titleBar.register_home_callback(callback)
        
        # Connect dialog close events to home callback
        self.ptu_config_dialog.rejected.connect(callback)
        self.robot_config_dialog.rejected.connect(callback)

    def switch_to_ptu_config(self):
        # Show PTU configuration dialog
        # Ensure the dialog adjusts to content before showing
        self.ptu_config_dialog.adjustSize()
        self.ptu_config_dialog.exec_()
        
    def switch_to_robot_config(self):
        # Show Robot configuration dialog
        # Ensure the dialog adjusts to content before showing
        self.robot_config_dialog.adjustSize()
        self.robot_config_dialog.exec_()
        
    def switch_to_home(self):
        # Close any open dialogs
        if self.ptu_config_dialog.isVisible():
            self.ptu_config_dialog.reject()
        if self.robot_config_dialog.isVisible():
            self.robot_config_dialog.reject()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()



