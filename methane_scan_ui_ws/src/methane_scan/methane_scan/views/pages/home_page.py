from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QGraphicsScene, QDialogButtonBox, QGroupBox, QLineEdit, QGridLayout,
    QApplication, QStyle, QProxyStyle
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent, QPointF, QRectF, QUrl

import pickle
import time
import requests
import os
from PyQt5.QtGui import QMouseEvent

from methane_scan.views.components.map_view import SatelliteMap # type: ignore
from methane_scan.views.components.device_card import DeviceCard # type: ignore
from ..components.toast import Toast # type: ignore

DATA_STORE = "map_previews.data"

class HomePage(QWidget):
    path_saved = pyqtSignal(list)
    start_stop_signal = pyqtSignal(bool)
    logger_signal = pyqtSignal(str)

    def __init__(self, API_KEY, parent=None):
        super().__init__()
        self.parent = parent
        self.setObjectName("methaneScanTab")
        self.setStyleSheet("""
          *:focus {
                border: 2px solid #009688;  /* teal para buen contraste */
                border-radius: 4px;
           }
          QPushButton:focus {
                           border: 2px solid #009688;  /* teal para buen contraste */
                border-radius: 4px;
           }
        """)
        self._API_KEY = API_KEY
        self.start_callback = None
        self.simulation_running = True
        self._build_ui()

        self.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        # Si pulsas Return o Enter
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            w = self.focusWidget()
            if isinstance(w, QPushButton) and w.isEnabled():
                w.click()
                return True    # consumimos el evento
            if isinstance(w, QLineEdit):
                # Si es un QLineEdit, lo ignoramos
                return False
            if isinstance(w, DeviceCard):
                # dentro de eventFilter, en el caso DeviceCard:
                pos = w.rect().center()
                click_event = QMouseEvent(
                    QEvent.MouseButtonPress,
                    pos,
                    Qt.LeftButton,
                    Qt.LeftButton,
                    Qt.NoModifier
                )
                w.mousePressEvent(click_event)
                return True
        return super().eventFilter(obj, event)

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
        map_label.setStyleSheet("font-weight: bold; font-size: 16pt;")
        map_title_layout.addWidget(map_label)
        map_title_layout.addStretch()
        
        # Marco donde irá el mapa
        scene = QGraphicsScene()
        scene.setSceneRect(0, 0, 1000, 1000)
        self.map_frame = SatelliteMap(api_key=self._API_KEY)
        self.map_frame.setObjectName("mapFrame")
        self.map_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Botones de zoom, seleccionar área e importar datos
        self.btn_select_area = QPushButton("Seleccionar Área")
        self.btn_clean_area= QPushButton("Limpiar Área")
        self.btn_clean_area.setDisabled(True)
        self.btn_clean_area.clicked.connect(lambda: self.cleanSelection(refresh=True))
        self.btn_huntertrail = QPushButton("+")
        btn_zoom_out = QPushButton("-")

        map_buttons_layout = QHBoxLayout()
        map_buttons_layout.addWidget(self.btn_select_area)
        map_buttons_layout.addWidget(self.btn_clean_area)
        map_buttons_layout.addWidget(self.btn_huntertrail)
        map_buttons_layout.addWidget(btn_zoom_out)
        map_layout.addLayout(map_buttons_layout)

        map_layout.addWidget(self.map_frame)
        
        # 2b) Zona de Control
        control_frame = QFrame()
        control_frame.setObjectName("controlZone")  # Usamos el mismo estilo "card" que tus DeviceCards
        control_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        control_frame.setMaximumWidth(400)  # Ancho máximo para la zona de control
        center_layout.addWidget(control_frame, stretch=1)

        control_layout = QVBoxLayout(control_frame)
        # Márgenes algo más amplios para dar sensación de "aire":
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(12)

        # --- Encabezado con icono y título ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        header_title = QLabel("Zona de Control")
        header_title.setStyleSheet("""
            font-weight: bold; 
            font-size: 16pt; 
            color: #FFFFFF;
        """)
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        control_layout.addLayout(header_layout)

        # Separador horizontal sutil
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        control_layout.addWidget(separator)

        # --- Bloque de datos (Podemos usar un QFrame "interior") ---
        data_frame = QFrame()
        data_frame.setObjectName("controlDataFrame")  # Podríamos aplicar estilo propio si deseamos
        data_layout = QVBoxLayout(data_frame)
        data_layout.setContentsMargins(5, 5, 5, 5)
        data_layout.setSpacing(6)

        # Título pequeño (sub-sección)
        recent_data_title = QLabel("Últimas Datas Obtenidas")
        recent_data_title.setStyleSheet("font-weight: bold; font-size: 14pt; margin-bottom: 6px;")
        data_layout.addWidget(recent_data_title)

        self.methane_label = QLabel("Medición de Metano: N/A")
        self.reflection_label = QLabel("Fuerza de Reflexión: N/A")
        self.absortion_label = QLabel("Fuerza de Absorción: N/A")
        self.absortion_label.setContentsMargins(0, 0, 0, 20)

        # Añadimos los labels al layout interno
        data_layout.addWidget(self.methane_label)
        data_layout.addWidget(self.reflection_label)
        data_layout.addWidget(self.absortion_label)

        position_group = QGroupBox("Posición del Robot:")
        position_group.setStyleSheet("font-size: 14pt;")
        position_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        position_group.setContentsMargins(0, 0, 0, 70)
        position_group_layout = QGridLayout(position_group)
        position_group_layout.setContentsMargins(10, 10, 10, 10)
        position_group_layout.setHorizontalSpacing(10)
        position_group_layout.setVerticalSpacing(10)
        position_group_layout.setAlignment(Qt.AlignLeft)

        self.robot_lat_label = QLabel("Latitud: N/A")
        self.robot_lat_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.robot_lon_label = QLabel("Longitud: N/A")
        self.robot_lon_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        position_group_layout.addWidget(self.robot_lat_label, 0, 0)
        position_group_layout.addWidget(self.robot_lon_label, 1, 0)

        for lbl in [self.methane_label, self.reflection_label, self.absortion_label, self.robot_lat_label, self.robot_lon_label]:
            # Ajustamos un estilo unificado
            lbl.setStyleSheet("font-size: 12pt; color: #DDDDDD; margin-bottom: 2px;")


        data_layout.addWidget(position_group)

        legend_group = QGroupBox("Leyenda")
        legend_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        legend_group.setStyleSheet("font-size: 14pt;")
        legend_layout = QHBoxLayout(legend_group)
        legend_layout.setContentsMargins(10, 10, 10, 10)
        legend_layout.setSpacing(10)

        #
        # 1) Leyenda de PTU
        #
        ptu_layout = QVBoxLayout()
        ptu_layout.setSpacing(8)
        ptu_layout.setAlignment(Qt.AlignCenter)

        ptu_color_label = QLabel()
        ptu_color_label.setFixedSize(20, 20)
        # Ejemplo: un verde para el PTU
        ptu_color_label.setStyleSheet("""
            background-color: #2196F3; /* Verde PTU */
            border: 1px solid #444444;
            border-radius: 10px; 
        """)

        ptu_text_label = QLabel("PTU")
        ptu_text_label.setStyleSheet("font-size: 10pt; color: #DDDDDD;")

        ptu_layout.addWidget(ptu_color_label, 0, Qt.AlignCenter)
        ptu_layout.addWidget(ptu_text_label, 0, Qt.AlignCenter)
        legend_layout.addLayout(ptu_layout)

        #
        # 2) Leyenda de “Hunter” o Robot
        #
        robot_layout = QVBoxLayout()
        robot_layout.setSpacing(4)
        robot_layout.setAlignment(Qt.AlignCenter)

        robot_color_label = QLabel()
        robot_color_label.setFixedSize(20, 20)
        # Ejemplo: un azul para el Robot/Hunter
        robot_color_label.setStyleSheet("""
            background-color: #fd7567; /* Azul Robot */
            border: 1px solid #444444;
            border-radius: 10px;
        """)

        robot_text_label = QLabel("Robot")
        robot_text_label.setStyleSheet("font-size: 10pt; color: #DDDDDD;")

        robot_layout.addWidget(robot_color_label, 0, Qt.AlignCenter)
        robot_layout.addWidget(robot_text_label, 0, Qt.AlignCenter)
        legend_layout.addLayout(robot_layout)

        #
        # 3) Barra de gradiente TDLAS (0 - 150 ppm·m)
        #   En horizontal
        #
        tdlas_layout = QVBoxLayout()
        tdlas_layout.setSpacing(4)
        tdlas_layout.setAlignment(Qt.AlignCenter)

        tdlas_scale_layout = QHBoxLayout()
        tdlas_scale_layout.setSpacing(5)
        tdlas_scale_layout.setAlignment(Qt.AlignCenter)

        label_0 = QLabel("0")
        label_0.setStyleSheet("font-size: 10pt; color: #DDDDDD;")

        color_scale_frame = QFrame()
        color_scale_frame.setFixedSize(100, 15)
        color_scale_frame.setStyleSheet("""
            QFrame {
            background: qlineargradient(
                spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,
                stop:0 rgba(0,255,0,255),
                stop:0.33 rgba(255,255,0,255),
                stop:0.66 rgba(255,165,0,255),
                stop:1 rgba(255,0,0,255)
            );
            border: 1px solid #444444;
            border-radius: 4px;
            }
        """)

        label_150 = QLabel("150")
        label_150.setStyleSheet("font-size: 10pt; color: #DDDDDD;")

        tdlas_scale_layout.addWidget(label_0)
        tdlas_scale_layout.addWidget(color_scale_frame)
        tdlas_scale_layout.addWidget(label_150)

        tdlas_layout.addLayout(tdlas_scale_layout)
        tdlas_label = QLabel("ppm·m")
        tdlas_label.setStyleSheet("font-size: 10pt; color: #DDDDDD;")
        tdlas_layout.addWidget(tdlas_label, 0, Qt.AlignCenter)

        tdlas_label = QLabel("ppm·m")
        tdlas_label.setStyleSheet("font-size: 10pt; color: #DDDDDD;")

        tdlas_layout.addLayout(tdlas_scale_layout)
        tdlas_layout.addWidget(tdlas_label, 0, Qt.AlignCenter)

        legend_layout.addLayout(tdlas_layout)

        data_layout.addWidget(legend_group)

        data_frame.setLayout(data_layout)
        control_layout.addWidget(data_frame)


        # Un estirador para “empujar” los botones al final
        control_layout.addStretch()

        # -- Botones Iniciar y Abortar --
        buttons_layout = QHBoxLayout()
        
        self.btn_iniciar = QPushButton("Iniciar")
        self.btn_iniciar.setObjectName("btnIniciar") 
        self.btn_iniciar.setDisabled(True)

        self.btn_pausar = QPushButton("Pausar")
        self.btn_pausar.setObjectName("btnPausar")
        self.btn_pausar.setDisabled(True)
        self.btn_pausar.clicked.connect(self._on_pause_clicked)

        self.btn_abortar = QPushButton("Abortar")
        self.btn_abortar.setObjectName("btnAbortar")
        self.btn_abortar.setDisabled(True)

        self.not_ready_label = QLabel("Nota: Todos los dispositivos deben estar listos para iniciar.")
        self.not_ready_label.setStyleSheet("font-size: 10pt; color: red;")
        self.not_ready_label.setAlignment(Qt.AlignCenter)
        self.not_ready_label.setContentsMargins(0, 0, 0, 10)
        control_layout.addWidget(self.not_ready_label)
        
        buttons_layout.addWidget(self.btn_iniciar)
        buttons_layout.addWidget(self.btn_pausar)
        buttons_layout.addWidget(self.btn_abortar)
        control_layout.addLayout(buttons_layout)

        for w in (
            self.card_ptu, self.card_tdlas, self.card_robot,
            self.btn_select_area, self.btn_clean_area,
            self.btn_huntertrail, btn_zoom_out, self.btn_iniciar,
            self.btn_pausar, self.btn_abortar
        ):
            w.setFocusPolicy(Qt.StrongFocus)

        # 2) Definimos el orden de tabulación
        self.setTabOrder(self.card_ptu,       self.card_tdlas)
        self.setTabOrder(self.card_tdlas,     self.card_robot)
        self.setTabOrder(self.card_robot,     self.btn_select_area)
        self.setTabOrder(self.btn_select_area,self.btn_clean_area)
        self.setTabOrder(self.btn_clean_area, self.btn_huntertrail)
        self.setTabOrder(self.btn_huntertrail,btn_zoom_out)
        self.setTabOrder(self.btn_iniciar,    self.btn_pausar)
        self.setTabOrder(self.btn_pausar,     self.btn_abortar)
   
    def register_ptu_config_callback(self, callback):
        """Permite registrar un callback que se ejecutará al hacer clic en la card PTU."""
        # Usamos una lambda para ignorar el argumento 'event' y llamar al callback inyectado
        self.card_ptu.mousePressEvent = lambda event: callback()
    
    def register_robot_config_callback(self, callback):
        """Permite registrar un callback que se ejecutará al hacer clic en la card Robot."""
        # Usamos una lambda para ignorar el argumento 'event' y llamar al callback inyectado
        self.card_robot.mousePressEvent = lambda event: callback()

    def register_trajectory_callback(self, callback):
        self.trajectory_callback = callback
        self.btn_select_area.clicked.connect(lambda event: callback())

    def onGetRectCorners(self):
        # Llamamos a getRectangleCorners y definimos un callback
        self.map_frame.getCorners(self.handleRectCorners)
    
    def selectArea(self):
        self.map_frame.enableDrawing()
        self.cleanSelection()
        self.btn_clean_area.setDisabled(False)
        self.btn_select_area.setText("Guardar Selección")
        try:
            self.btn_select_area.clicked.disconnect()
        except TypeError:
            pass
        self.btn_select_area.clicked.connect(self.saveSelection)


    def selectTrajectory(self, coords):
        self.map_frame.drawTrajectory(coords)
        self.btn_select_area.setText("Seleccionar Area")
        self.map_frame.disableDrawing()
        try:
            self.btn_select_area.clicked.disconnect()
        except TypeError:
            pass
        self.btn_select_area.clicked.connect(self.trajectory_callback)
        self.btn_clean_area.setDisabled(False)
        if coords:
            self.path_saved.emit(coords)



    def saveSelection(self):
        Toast("Guardando selección...", self.parent, "info", 3000).show()
        self.btn_select_area.setText("Seleccionar Area")
        self.map_frame.disableDrawing()
        try:
            self.btn_select_area.clicked.disconnect()
        except TypeError:
            pass
        self.btn_select_area.clicked.connect(self.trajectory_callback)
        self.map_frame.getCorners(self.handleCorners)
        

    def get_map_preview(self, coords,
                    width=600, height=300, zoom=18):
        """
        Captura una vista previa de toda la trayectoria en modo satélite usando Google Static Maps API.
        - Dibuja líneas entre todos los puntos en 'coords' en un solo mapa.
        - Marcador verde en el inicio y rojo en el final.
        - Retorna los bytes de la imagen.
        """

        if not coords or len(coords) < 2:
            raise ValueError("Se requieren al menos dos puntos para generar la ruta.")

        path_points = "|".join(f"{coord['latitude']},{coord['longitude']}" for coord in coords)
        path = f"path=color:0x000000FF|weight:5|{path_points}"

        params = {
            "size": f"{width}x{height}",
            "zoom": str(zoom),
            "maptype": "satellite",
            "scale": "2",
            "key": self._API_KEY,
        }
        base_url = "https://maps.googleapis.com/maps/api/staticmap"
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{base_url}?{query}&{path}"

        response = requests.get(url)
        response.raise_for_status()
        return response.content
    
    def save_map_preview(self, nombre, coords):
        """
        Genera la imagen de la trayectoria con coords y almacena bajo 'nombre'.
        - nombre: clave bajo la que se guardará la vista previa.
        - coords: lista de tuplas (lat, lng) para trazar la ruta.
        Guarda en DATA_STORE un dict con 'map'.
        Si el archivo no existe, lo crea.
        """
        # 1) Obtener bytes de la imagen
        data = self.get_map_preview(coords)

        # 2) Asegurarse de que la carpeta (si la hay) exista
        directory = os.path.dirname(DATA_STORE)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)

        # 3) Si el archivo no existe, inicializarlo con un dict vacío
        if not os.path.exists(DATA_STORE):
            with open(DATA_STORE, 'wb') as f:
                pickle.dump({}, f)

        # 4) Cargar el store existente
        try:
            with open(DATA_STORE, 'rb') as f:
                store = pickle.load(f)
        except (EOFError, pickle.UnpicklingError):
            store = {}

        # 5) Actualizar y guardar
        store[nombre] = {
            'map': data,
            'coords': coords
        }
        with open(DATA_STORE, 'wb') as f:
            pickle.dump(store, f)

    def cleanSelection(self, refresh=False):
        self.map_frame.clearSelection()
        self.btn_clean_area.setDisabled(True)
        if refresh:
            self.path_saved.emit([])

    def handleCorners(self, corners):
        """
        corners es la lista [SW, NW, NE, SE] o None si no hay rectángulo.
        Cada esquina es un dict con lat, lng.
        """
        if corners == [] or corners is None:
            self.btn_clean_area.setDisabled(True)
            self.path_saved.emit([None])
            return

        if corners is not None:
            self.path_saved.emit(corners)
            self.save_map_preview(time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime()), corners)
            self.btn_clean_area.setDisabled(False)

            self.parent.select_trajectory_widget.refresh_trajectories()
        

    
    def enableStartButtonCallback(self, callback, callback_end):
        if self.start_callback is None:
            self.btn_iniciar.setDisabled(False)
            self.btn_iniciar.setFocusPolicy(Qt.StrongFocus)
            self.start_callback = callback
            self.btn_iniciar.clicked.connect(callback)

        if callback_end is not None:
            self.btn_abortar.clicked.connect(callback_end)

    def enableStartButton(self):
        self.btn_iniciar.setDisabled(False)
        self.btn_iniciar.setFocusPolicy(Qt.StrongFocus)
        self.btn_abortar.setDisabled(True)
        self.btn_abortar.setFocusPolicy(Qt.NoFocus)
        self.btn_pausar.setDisabled(True)
        self.btn_pausar.setFocusPolicy(Qt.NoFocus)

    def disableStartButton(self):
        self.btn_iniciar.setDisabled(True)
        self.btn_iniciar.setFocusPolicy(Qt.NoFocus)
        self.btn_pausar.setDisabled(False)
        self.btn_pausar.setFocusPolicy(Qt.StrongFocus)
        self.btn_abortar.setDisabled(False)
        self.btn_abortar.setFocusPolicy(Qt.StrongFocus)

    def tooglePauseButton(self):
        if self.simulation_running:
            self.btn_pausar.setText("Reanudar")
        else:
            self.btn_pausar.setText("Pausar")

    
    
    def set_device_status(self, device, status, errors = []):
        if device == "PTU":
            self.card_ptu.set_status(status, errors)
        elif device == "Robot":
            self.card_robot.set_status(status, errors)
        elif device == "TDLAS":
            self.card_tdlas.set_status(status, errors)
        else:
            raise ValueError("Dispositivo no reconocido")
    
    def set_tdlas_data(self, data):
        self.methane_label.setText(f"Medición de Metano: {data['average_ppmxm']}")
        self.reflection_label.setText(f"Fuerza de Reflexión: {data['average_reflection_strength']}")
        self.absortion_label.setText(f"Fuerza de Absorción: {data['average_absorption_strength']}")
    
    def set_robot_position(self, position):
        lat  = position.get("Latitude", 0)
        lng  = position.get("Longitude", 0)
        self.robot_lat_label.setText(f"Latitud: {lat}")
        self.robot_lon_label.setText(f"Longitud: {lng}")
        self.map_frame.drawRobotMarker(lat, lng, False)
    

    def set_ready(self, ready):
        if ready:
            self.not_ready_label.setVisible(False)
        else:
            self.not_ready_label.setVisible(True)

    def _on_pause_clicked(self):
        self.tooglePauseButton()
        self.start_stop_signal.emit(self.simulation_running)
        self.simulation_running = not self.simulation_running
        
