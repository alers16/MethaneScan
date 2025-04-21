from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QGraphicsScene, QDialogButtonBox, QGroupBox, QLineEdit, QGridLayout,
    QSplitter, QHBoxLayout, QVBoxLayout, QTableWidgetItem, QSpacerItem, QSizePolicy,
    QFileDialog, QFrame, QToolButton, QStyle, QStyleOption
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal

import subprocess
import threading

from methane_scan.views.components.map_view import SatelliteMap # type: ignore
from methane_scan.views.components.device_card import DeviceCard # type: ignore

class SimulationPage(QWidget):
    def __init__(self, API_KEY):
        super().__init__()
        self.setObjectName("methaneScanTab")
        self._API_KEY = API_KEY
        self._build_ui()
        self.file_path = None

    def _build_ui(self):
        """Construye la interfaz de la primera pestaña (MethaneScan)."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 2) Zona central: Mapa (izq) y Zona de Control (dcha)
        center_layout = QHBoxLayout()
        
        # 1a) Mapa de inspección
        map_layout = QVBoxLayout()
        title_map = QLabel("Mapa de inspección")
        title_map.setStyleSheet("font-weight: bold; font-size: 16pt;")
        map_layout.addWidget(title_map)

        self.map_frame = SatelliteMap(api_key=self._API_KEY)
        self.map_frame.setObjectName("mapFrame")
        self.map_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        map_layout.addWidget(self.map_frame)
        center_layout.addLayout(map_layout, stretch=3)
        
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
        lbl_control = QLabel("Zona de Control")
        lbl_control.setStyleSheet("font-weight: bold; font-size: 16pt; color: #FFFFFF;")
        control_layout.addWidget(lbl_control)
        control_layout.addWidget(self._make_separator())

        # Selector de archivo rosbag
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Selecciona un archivo .bag...")
        self.file_input.setReadOnly(True)
        btn_browse = QPushButton("Examinar...")
        btn_browse.clicked.connect(self._on_browse)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(btn_browse)
        control_layout.addLayout(file_layout)

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

        # Sub-layout para la escala
        tdlas_scale_layout = QHBoxLayout()
        tdlas_scale_layout.setSpacing(5)
        tdlas_scale_layout.setAlignment(Qt.AlignCenter)

        label_0 = QLabel("0")
        label_0.setStyleSheet("font-size: 10pt; color: #DDDDDD;")

        # Barra con gradiente horizontal de blanco a rojo
        color_scale_frame = QFrame()
        color_scale_frame.setFixedSize(100, 15)
        color_scale_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,
                    stop:0 rgba(255,255,255,255),
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

        self.btn_abortar = QPushButton("Abortar")
        self.btn_abortar.setObjectName("btnAbortar")
        self.btn_abortar.setDisabled(True)

        self.not_ready_label = QLabel("Nota: Selecciona un archivo para habilitar iniciar.")
        self.not_ready_label.setStyleSheet("font-size: 10pt; color: red;")
        self.not_ready_label.setAlignment(Qt.AlignCenter)
        self.not_ready_label.setContentsMargins(0, 0, 0, 10)
        control_layout.addWidget(self.not_ready_label)
        
        buttons_layout.addWidget(self.btn_iniciar)
        buttons_layout.addWidget(self.btn_abortar)
        control_layout.addLayout(buttons_layout)
        
        # 2) Panel superior: mapa + control
        top_panel = QWidget()
        top_panel.setLayout(center_layout)
        top_panel.setMinimumHeight(500)

        # 3) Panel inferior: Datos Obtenidos (etiqueta + tabla)
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        lbl_data = QLabel("Datos Obtenidos")
        lbl_data.setStyleSheet("font-weight: bold; font-size: 14pt;")
        bottom_layout.addWidget(lbl_data)
        # Tabla
        self.table = QTableWidget(3, 3)
        self.table.setHorizontalHeaderLabels(["Medidas del láser", "Medidas del viento", "Timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._populate_sample_rows()
        bottom_layout.addWidget(self.table)
        bottom_panel.setMinimumHeight(150)

        # --- 4) Splitter vertical: top + bottom ---
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(top_panel)
        splitter.addWidget(bottom_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        # 5) Añadir splitter al layout principal
        layout.addWidget(splitter)
    
    def enableStartButton(self):
        self.btn_iniciar.setDisabled(False)
        self.btn_iniciar.clicked.connect(self.start_simulation)
    
    def set_tdlas_data(self, data):
        self.methane_label.setText(f"Medición de Metano: {data['average_ppmxm']}")
        self.reflection_label.setText(f"Fuerza de Reflexión: {data['average_reflection_strength']}")
        self.absortion_label.setText(f"Fuerza de Absorción: {data['average_absorption_strength']}")
    
    def set_robot_position(self, position):
        lat  = position.get("lat", 0)
        lng  = position.get("lng", 0)
        self.robot_lat_label.setText(f"Latitud: {lat}")
        self.robot_lon_label.setText(f"Longitud: {lng}")
        self.map_frame.drawRobotMarker(lat, lng)
    
    def set_ready(self, ready):
        if ready:
            self.not_ready_label.setVisible(False)
        else:
            self.not_ready_label.setVisible(True)

    def _populate_sample_rows(self):
        # Ejemplo de filas iniciales
        sample = [
            ("6.2 ppm", "2.3 m/s", "12:00:00"),
            ("6.5 ppm", "2.1 m/s", "12:05:00"),
            ("6.0 ppm", "2.4 m/s", "12:10:00"),
        ]
        for row, (laser, wind, ts) in enumerate(sample):
            self.table.setItem(row, 0, QTableWidgetItem(laser))
            self.table.setItem(row, 1, QTableWidgetItem(wind))
            self.table.setItem(row, 2, QTableWidgetItem(ts))

    def _make_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        return sep

    def _on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecciona la carpeta")
        if folder:
            self.file_input.setText(folder)
            self.file_path = folder
            self.not_ready_label.hide()
            self.enableStartButton()
    
    def start_simulation(self):
        command = ["ros2", "bag", "play", self.file_path]
        self.process = subprocess.Popen(command)

        def _wait_and_kill():
            # Espera a que termine de reproducir todos los mensajes
            self.process.wait()
            # Por si todavía siguiera vivo, lo mata
            try:
                self.process.kill()
            except Exception:
                pass
        # Lanzar la monitorización en un hilo para no bloquear la UI
        threading.Thread(target=_wait_and_kill, daemon=True).start()
            

