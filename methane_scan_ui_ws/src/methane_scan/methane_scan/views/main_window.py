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
from PyQt5.QtWidgets import QStackedWidget
from methane_scan.views.components.title_bar import TitleBar # type: ignore
from methane_scan.views.pages.home_page import HomePage # type: ignore
from methane_scan.views.pages.simulation_page import SimulationPage # type: ignore
from methane_scan.views.pages.robot_config import RobotConfigWidget # type: ignore
from methane_scan.views.pages.select_location_dialog import TrajectorySelectorDialog # type: ignore
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

        # Construimos un QTabWidget para manejar el cambio de pantalla según lo indique la title bar
        self.tab_widget = QStackedWidget()
        # Agregamos la pantalla principal (HomePage) como la primera pestaña
        self.home_tab = HomePage(API_KEY, self)
        self.tab_widget.addWidget(self.home_tab)
        # Agregamos la pestaña de simulación (SimulationPage) como la segunda pestaña
        self.simulation_tab = SimulationPage(API_KEY)
        self.tab_widget.addWidget(self.simulation_tab)
        self.tab_widget.setCurrentWidget(self.home_tab)
        # Se pueden agregar más pestañas y cambiar entre ellas mediante callbacks de la title bar
        main_layout.addWidget(self.tab_widget)
        
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

        #Creamos los diálogos de selección de trayectoria como QDialog
        self.select_trajectory_dialog = QDialog(self)
        self.select_trajectory_dialog.setWindowTitle("Seleccionar trayectoria")
        select_trajectory_layout = QVBoxLayout(self.select_trajectory_dialog)
        select_trajectory_layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        self.select_trajectory_widget = TrajectorySelectorDialog(parent=self)
        self.select_trajectory_widget.setMinimumSize(800, 500)
        select_trajectory_layout.addWidget(self.select_trajectory_widget)
        self.select_trajectory_dialog.setModal(True)

        # Connect dialog signals
        self.select_trajectory_widget.accepted.connect(self.select_trajectory_dialog.accept)
        self.select_trajectory_widget.rejected.connect(self.select_trajectory_dialog.reject)
        self.select_trajectory_widget.select_trajectory_signal.connect(self.home_tab.selectTrajectory)
        
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
        self.home_tab.map_frame.setMinimumSize(new_width, new_height)
        self.simulation_tab.map_frame.setMinimumSize(new_width, new_height)
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
        self.home_tab.register_ptu_config_callback(callback)

    def register_robot_config_callback(self, callback):
        self.home_tab.register_robot_config_callback(callback)

    def register_select_trajectory_callback(self, callback):
        self.home_tab.register_trajectory_callback(callback)

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

    def switch_to_select_trajectory(self):
        # Show Select trajectory dialog
        # Ensure the dialog adjusts to content before showing
        self.select_trajectory_dialog.adjustSize()
        self.select_trajectory_dialog.exec_()
        
    def switch_to_home(self):
        # Close any open dialogs
        if self.ptu_config_dialog.isVisible():
            self.ptu_config_dialog.reject()
        if self.robot_config_dialog.isVisible():
            self.robot_config_dialog.reject()
    
    # Switch to home tab
    def switch_to_home_tab(self):
        self.tab_widget.setCurrentWidget(self.home_tab)

    def switch_to_simulation_tab(self):
        self.tab_widget.setCurrentWidget(self.simulation_tab)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()



