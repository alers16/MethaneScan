from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QGraphicsScene
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal

from methane_scan.views.components.map_view import SatelliteMap # type: ignore
from methane_scan.views.components.device_card import DeviceCard # type: ignore

class HomePage(QWidget):
    path_saved = pyqtSignal(list)

    def __init__(self, API_KEY):
        super().__init__()
        self.setObjectName("methaneScanTab")
        self._API_KEY = API_KEY
        self._build_ui()

    def _build_ui(self):
        """Construye la interfaz de la primera pestaña (MethaneScan)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 1) Fila superior con cards de estado de dispositivos
        devices_layout = QHBoxLayout()
        layout.addLayout(devices_layout)
        
        # Crear las tres "cards" de dispositivos
        self.card_ptu = DeviceCard("PTU", "No se encuentran: ('Posición', 'Confirmación')", ":/icon_PTU.svg")
        self.card_tdlas = DeviceCard("TDLAS", "No se encuentra Confirmación", ":/icon_TDLAS.svg")
        self.card_robot = DeviceCard("Robot", "No se encuentran: ('Posición', 'Trayectoria', 'Velocidad')", ":/icon_Robot.svg")
        
        # Añadir las cards al layout con 'stretch factor' para que tengan igual ancho
        devices_layout.addWidget(self.card_ptu, 1)
        devices_layout.addWidget(self.card_tdlas, 1)
        devices_layout.addWidget(self.card_robot, 1)
        
        # 2) Zona central: Mapa (izq) y Zona de Control (dcha)
        center_layout = QHBoxLayout()
        layout.addLayout(center_layout, stretch=1)
        
        # 2a) Mapa de inspección
        map_layout = QVBoxLayout()
        center_layout.addLayout(map_layout, stretch=3)
        
        # Título "Mapa de inspección"
        map_title_layout = QHBoxLayout()
        map_layout.addLayout(map_title_layout)
        
        map_label = QLabel("Mapa de inspección")
        map_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        map_title_layout.addWidget(map_label)
        map_title_layout.addStretch()
        
        # Botones de zoom, seleccionar área e importar datos
        self.btn_select_area = QPushButton("Seleccionar Área")
        self.btn_select_area.clicked.connect(self.selectArea)
        self.btn_clean_area= QPushButton("Limpiar Área")
        self.btn_clean_area.setDisabled(True)
        self.btn_clean_area.clicked.connect(self.cleanSelection)
        btn_zoom_in = QPushButton("+")
        btn_zoom_out = QPushButton("-")
        
        map_buttons_layout = QHBoxLayout()
        map_buttons_layout.addWidget(self.btn_select_area)
        map_buttons_layout.addWidget(self.btn_clean_area)
        map_buttons_layout.addWidget(btn_zoom_in)
        map_buttons_layout.addWidget(btn_zoom_out)
        map_layout.addLayout(map_buttons_layout)
        
        # Marco donde irá el mapa
        scene = QGraphicsScene()
        scene.setSceneRect(0, 0, 1000, 1000)
        self.map_frame = SatelliteMap(api_key=self._API_KEY)
        self.map_frame.setObjectName("mapFrame")
        self.map_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        map_layout.addWidget(self.map_frame)
        
        # 2b) Zona de Control
        control_frame = QFrame()
        control_frame.setObjectName("controlZone")
        control_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        center_layout.addWidget(control_frame, stretch=1)
        
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 10, 10, 10)
        
        control_title = QLabel("Zona de Control")
        control_title.setStyleSheet("font-weight: bold; font-size: 14pt;")
        control_layout.addWidget(control_title)
        
        # Últimas datas obtenidas
        recent_data_label = QLabel("Últimas Datas Obtenidas")
        recent_data_label.setStyleSheet("font-weight: bold; margin-top: 10px; font-size: 8pt;")
        control_layout.addWidget(recent_data_label)
        
        laser_label = QLabel("Laser: 6.2 ppm")
        wind_label = QLabel("Medidor de viento: 2.3 m/s")
        error_label = QLabel("Porcentaje de error: 2.5%")
        
        control_layout.addWidget(laser_label)
        control_layout.addWidget(wind_label)
        control_layout.addWidget(error_label)
        control_layout.addStretch()

        # -- Botones Iniciar y Abortar --
        buttons_layout = QHBoxLayout()
        
        self.btn_iniciar = QPushButton("Iniciar")
        self.btn_iniciar.setObjectName("btnIniciar") 
        self.btn_iniciar.setDisabled(True)

        self.btn_abortar = QPushButton("Abortar")
        self.btn_abortar.setObjectName("btnAbortar")
        self.btn_abortar.setDisabled(True)

        buttons_layout.addWidget(self.btn_iniciar)
        buttons_layout.addWidget(self.btn_abortar)
        control_layout.addLayout(buttons_layout)
        
        # 3) Tabla de "Datos Obtenidos"
        #data_obtenidos_label = QLabel("Datos Obtenidos")
        #data_obtenidos_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        #layout.addWidget(data_obtenidos_label)
        #
        #table = QTableWidget()
        #table.setRowCount(3)
        #table.setColumnCount(3)
        #table.setHorizontalHeaderLabels(["Medidas del láser", "Medidas del viento", "Timestamp"])
        #table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        #table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #
        #table.setItem(0, 0, QTableWidgetItem("6.2 ppm"))
        #table.setItem(0, 1, QTableWidgetItem("2.3 m/s"))
        #table.setItem(0, 2, QTableWidgetItem("12:00:00"))
        #
        #table.setItem(1, 0, QTableWidgetItem("6.5 ppm"))
        #table.setItem(1, 1, QTableWidgetItem("2.1 m/s"))
        #table.setItem(1, 2, QTableWidgetItem("12:05:00"))
        #
        #table.setItem(2, 0, QTableWidgetItem("6.0 ppm"))
        #table.setItem(2, 1, QTableWidgetItem("2.4 m/s"))
        #table.setItem(2, 2, QTableWidgetItem("12:10:00"))
        #
        #layout.addWidget(table, stretch=1)

    
    def register_ptu_config_callback(self, callback):
        """Permite registrar un callback que se ejecutará al hacer clic en la card PTU."""
        # Usamos una lambda para ignorar el argumento 'event' y llamar al callback inyectado
        self.card_ptu.mousePressEvent = lambda event: callback()
    
    def register_robot_config_callback(self, callback):
        """Permite registrar un callback que se ejecutará al hacer clic en la card Robot."""
        # Usamos una lambda para ignorar el argumento 'event' y llamar al callback inyectado
        self.card_robot.mousePressEvent = lambda event: callback()

    def onGetRectCorners(self):
        # Llamamos a getRectangleCorners y definimos un callback
        self.map_frame.getCorners(self.handleRectCorners)
    
    def selectArea(self):
        self.map_frame.enableDrawing()
        self.btn_select_area.setText("Guardar Selección")
        self.btn_select_area.clicked.connect(self.saveSelection)

    def saveSelection(self):
        self.btn_select_area.setText("Seleccionar Area")
        self.map_frame.disableDrawing()
        self.btn_select_area.clicked.connect(self.selectArea)
        self.map_frame.getCorners(self.handleCorners)
        self.btn_clean_area.setDisabled(False)

    def cleanSelection(self):
        self.map_frame.clearSelection()
        self.btn_clean_area.setDisabled(True)
        self.path_saved.emit([])

    def handleCorners(self, corners):
        """
        corners es la lista [SW, NW, NE, SE] o None si no hay rectángulo.
        Cada esquina es un dict con lat, lng.
        """
        if corners is not None:
            self.path_saved.emit(corners)
    
    def enableStartButton(self, callback):
        self.btn_iniciar.setDisabled(False)
        self.btn_iniciar.clicked.connect(callback)
    
    def set_device_status(self, device, status, errors = []):
        if device == "PTU":
            self.card_ptu.set_status(status, errors)
        elif device == "Robot":
            self.card_robot.set_status(status, errors)
        elif device == "TDLAS":
            self.card_tdlas.set_status(status, errors)
        else:
            raise ValueError("Dispositivo no reconocido")
    
    

