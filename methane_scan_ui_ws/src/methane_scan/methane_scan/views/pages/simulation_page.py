from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QGroupBox, QLineEdit, QGridLayout,
    QSplitter, QHBoxLayout, QVBoxLayout, QTableWidgetItem, QSizePolicy,
    QFileDialog, QFrame, QAbstractItemView, 
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QObject, QEvent

import threading
import pexpect
import os

from methane_scan.views.components.map_view import SatelliteMap # type: ignore
from methane_scan.views.components.toast import Toast # type: ignore

class ResizeListener(QObject):
    def __init__(self, target, threshold):
        super().__init__(target)
        self.threshold = threshold
        self.triggered = False
        self.callback_minus = None
        self.callback_more = None
        target.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            if obj.height() <= self.threshold and not self.triggered:
                self.triggered = True
                if self.callback_minus:
                    self.callback_minus()
            elif obj.height() > self.threshold and self.triggered:
                self.triggered = False
                if self.callback_more:
                    self.callback_more()
        return super().eventFilter(obj, event)
    
    def set_callback_minus(self, callback):
        self.callback_minus = callback
    
    def set_callback_more(self, callback):
        self.callback_more = callback

class SimulationPage(QWidget):
    error_signal = pyqtSignal(str)
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
        self.frecuency = 1.0
        self._build_ui()
        self.file_path = None
        self._is_running = False
        self.child = None
        self.save_positions = []

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
        return super().eventFilter(obj, event)
        

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
        self.map_frame.bridge.beamClicked.connect(self.select_data_row)
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
        self.btn_browse = QPushButton("Examinar...")
        self.btn_browse.setFocusPolicy(Qt.StrongFocus)
        self.btn_browse.clicked.connect(self._on_browse)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.btn_browse)
        control_layout.addLayout(file_layout)

        # --- Bloque de datos (Podemos usar un QFrame "interior") ---
        self.data_frame = QFrame()
        self.data_frame.setObjectName("controlDataFrame")  # Podríamos aplicar estilo propio si deseamos
        data_layout = QVBoxLayout(self.data_frame)
        data_layout.setContentsMargins(5, 0, 5, 20)
        data_layout.setSpacing(20)

        self.data_block = QWidget()
        block_layout = QVBoxLayout(self.data_block)

        # 2) Prepara los labels
        title_label = QLabel("Últimas Datas Obtenidas")
        title_label.setStyleSheet("font-weight: bold; font-size: 14pt; margin-bottom: 6px;")

        self.methane_label    = QLabel("Medición de Metano: N/A")
        self.reflection_label = QLabel("Fuerza de Reflexión: N/A")
        self.absortion_label  = QLabel("Fuerza de Absorción: N/A")

        for w in (title_label,
                self.methane_label,
                self.reflection_label,
                self.absortion_label):
            block_layout.addWidget(w)

        # 3) Súbelo al layout principal
        data_layout.addWidget(self.data_block)

        position_group = QGroupBox("Posición del Robot:")
        position_group.setStyleSheet("font-size: 14pt;")
        position_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        position_group.setStyleSheet("font-size: 14pt; ")
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
        legend_group.setContentsMargins(10, 10, 10, 10)
        legend_group.setStyleSheet("font-size: 14pt;")
        legend_layout = QHBoxLayout(legend_group)
        legend_layout.setContentsMargins(10, 10, 10, 10)

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

        # --- Botones de control ---
        actions_group = QGroupBox("Acciones")
        actions_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        actions_group.setStyleSheet("font-size: 14pt; ")
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setContentsMargins(10, 10, 10, 10)
        actions_layout.setSpacing(10)

        actions_grid = QGridLayout()
        actions_grid.setContentsMargins(10, 10, 10, 10)
        actions_grid.setHorizontalSpacing(10)
        actions_grid.setVerticalSpacing(10)

        self.btn_next_message= QPushButton("Siguiente Msg")
        self.btn_next_message.setFocusPolicy(Qt.StrongFocus)
        self.btn_next_message.setObjectName("btnNextMessage")
        self.btn_next_message.setDisabled(True)
        self.btn_next_message.clicked.connect(self._on_next_message)

        self.btn_increase_rate = QPushButton("Aumentar Frec")
        self.btn_increase_rate.setFocusPolicy(Qt.StrongFocus)
        self.btn_increase_rate.setObjectName("btnIncreaseRate")
        self.btn_increase_rate.setDisabled(True)
        self.btn_increase_rate.clicked.connect(self._increase_rate)

        self.btn_decrease_rate = QPushButton("Disminuir Frec")
        self.btn_decrease_rate.setFocusPolicy(Qt.StrongFocus)
        self.btn_decrease_rate.setObjectName("btnDecreaseRate")
        self.btn_decrease_rate.setDisabled(True)
        self.btn_decrease_rate.clicked.connect(self._decrease_rate)

        self.btn_clean_map = QPushButton("Limpiar Mapa")
        self.btn_clean_map.setFocusPolicy(Qt.StrongFocus)
        self.btn_clean_map.setObjectName("btnCleanMap")
        self.btn_clean_map.setDisabled(True)
        self.btn_clean_map.clicked.connect(self._clear_map)

        self.frecuency_label = QLabel(f"Frecuencia: {self.frecuency:.2f} Hz")
        self.frecuency_label.setStyleSheet("font-size: 10pt;")

        actions_grid.addWidget(self.btn_next_message, 0, 1)
        actions_grid.addWidget(self.btn_increase_rate, 0, 0)
        actions_grid.addWidget(self.btn_decrease_rate, 1, 0)
        actions_grid.addWidget(self.btn_clean_map, 1, 1)
        actions_grid.addWidget(self.frecuency_label, 2, 0)

        actions_layout.addLayout(actions_grid)
        data_layout.addWidget(actions_group)
        
        self.data_frame.setLayout(data_layout)
        control_layout.addWidget(self.data_frame)

        # Un estirador para “empujar” los botones al final
        control_layout.addStretch()

        # -- Botones Iniciar y Abortar --
        buttons_layout = QHBoxLayout()
        
        # -- Boton de inicio de simulasion --
        self.btn_iniciar = QPushButton("Iniciar")
        self.btn_iniciar.setFocusPolicy(Qt.NoFocus)
        self.btn_iniciar.setObjectName("btnIniciar") 
        self.btn_iniciar.setDisabled(True)
        self.btn_iniciar.clicked.connect(self.start_simulation)

        self.btn_pausar = QPushButton("Pausar")
        self.btn_pausar.setFocusPolicy(Qt.NoFocus)
        self.btn_pausar.setObjectName("btnPausar")
        self.btn_pausar.setDisabled(True)
        self.btn_pausar.clicked.connect(self._pause_simulation)

        self.btn_abortar = QPushButton("Abortar")
        self.btn_abortar.setFocusPolicy(Qt.NoFocus)
        self.btn_abortar.setObjectName("btnAbortar")
        self.btn_abortar.setDisabled(True)
        self.btn_abortar.clicked.connect(self.abort_simulation)

        self.not_ready_label = QLabel("Nota: Selecciona un archivo para habilitar iniciar.")
        self.not_ready_label.setStyleSheet("font-size: 10pt; color: red;")
        self.not_ready_label.setAlignment(Qt.AlignCenter)
        self.not_ready_label.setContentsMargins(0, 0, 0, 10)
        control_layout.addWidget(self.not_ready_label)
        
        buttons_layout.addWidget(self.btn_iniciar)
        buttons_layout.addWidget(self.btn_pausar)
        buttons_layout.addWidget(self.btn_abortar)
        control_layout.addLayout(buttons_layout)
        
        # 2) Panel superior: mapa + control
        top_panel = QWidget()
        top_panel.setLayout(center_layout)
        top_panel.setMinimumHeight(650)

        listener = ResizeListener(top_panel, 780)
        listener.set_callback_minus(lambda: self.data_block.hide())
        listener.set_callback_more(lambda: self.data_block.show())

        # 3) Panel inferior: Datos Obtenidos (etiqueta + tabla)
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        lbl_data = QLabel("Datos Obtenidos")
        lbl_data.setStyleSheet("font-weight: bold; font-size: 14pt;")
        bottom_layout.addWidget(lbl_data)

        # Tabla
        self.table = QTableWidget(0, 4)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setHorizontalHeaderLabels(["average_ppmxm", "average_reflection_strength", "average_absorption_strength", "timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.table.cellClicked.connect(self._on_table_cell_clicked)
        self.table.itemClicked.connect(self._on_table_item_clicked)
        self.table.clicked.connect(self._on_table_index_clicked)
        self.table.verticalHeader().sectionClicked.connect(self._on_table_index_clicked)

        #self._populate_sample_rows()
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

        self.setTabOrder(self.btn_browse, self.btn_increase_rate)
        self.setTabOrder(self.btn_increase_rate, self.btn_next_message)
        self.setTabOrder(self.btn_next_message, self.btn_decrease_rate)
        self.setTabOrder(self.btn_decrease_rate, self.btn_clean_map)
        self.setTabOrder(self.btn_clean_map, self.btn_iniciar)
        self.setTabOrder(self.btn_iniciar, self.btn_pausar)
        self.setTabOrder(self.btn_pausar, self.btn_abortar)
        self.setTabOrder(self.btn_abortar, self.file_input)
    
    def set_tdlas_data(self, data):
        self.methane_label.setText(f"Medición de Metano: {data['average_ppmxm']}")
        self.reflection_label.setText(f"Fuerza de Reflexión: {data['average_reflection_strength']}")
        self.absortion_label.setText(f"Fuerza de Absorción: {data['average_absorption_strength']}")
    
    def set_robot_position(self, position, is_running=True):
        lat  = position[0]
        lng  = position[1]
        self.robot_lat_label.setText(f"Latitud: {lat}")
        self.robot_lon_label.setText(f"Longitud: {lng}")
        self.map_frame.drawRobotMarker(lat, lng, is_running)
    
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

    def add_data_row(self, data):
        # Añadir una nueva fila con los datos
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        item = QTableWidgetItem(f"{data['average_ppmxm']}")
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_position, 0, item)
        item = QTableWidgetItem(f"{data['average_reflection_strength']}")
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_position, 1, item)
        item = QTableWidgetItem(f"{data['average_absorption_strength']}")
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_position, 2, item)
        
        stamp = data['header']['stamp']
        sec = stamp.get("sec", 0)
        nanosec = stamp.get("nanosec", 0)
        timestamp = sec + nanosec * 1e-9
        item = QTableWidgetItem(f"{timestamp:.9f}")
        item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_position, 3, item)

        self.table.scrollToBottom()

    def select_data_row(self, row, position):
        # Seleccionar una fila específica
        if 0 <= row < self.table.rowCount():
            self.table.selectRow(row)
            self.table.scrollToItem(self.table.item(row, 0))
            self.set_data_text(row, position)
            
    def set_data_text(self, row, position):
        self.set_tdlas_data({
                "average_ppmxm": self.table.item(row, 0).text(),
                "average_reflection_strength": self.table.item(row, 1).text(),
                "average_absorption_strength": self.table.item(row, 2).text(),
        })
        self.set_robot_position([position["lat"], position["lng"]], is_running=False)

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
            self.btn_iniciar.setDisabled(False)
            self.btn_iniciar.setFocusPolicy(Qt.StrongFocus)
    
    def _pause_simulation(self):
        if self.child and self.child.isalive():
            if not self._is_running:
                position = self.save_positions[self.table.rowCount()-1]
                self.set_robot_position(position=[position["lat"], position["lng"]], is_running=False)
                self.btn_next_message.setDisabled(True)
                self.btn_clean_map.setFocusPolicy(Qt.NoFocus)
            else:
                self.btn_next_message.setDisabled(False)
                self.btn_clean_map.setFocusPolicy(Qt.StrongFocus)
            self.child.send(' ')
            txt = "Reanudar" if self._is_running else "Pausar"
            self.btn_pausar.setText(txt)
            self._is_running = not self._is_running
    
    def _increase_rate(self):
        if self.child and self.child.isalive():
            self.child.send('\x1b[A')
            self.frecuency = self.frecuency * 1.1
            self.frecuency_label.setText(f"Frecuencia: {(self.frecuency):.2f}")

    
    def _decrease_rate(self):
        if self.child and self.child.isalive():
            self.child.send('\x1b[B')
            self.frecuency = self.frecuency * 0.9
            self.frecuency_label.setText(f"Frecuencia: {(self.frecuency):.2f}")
    
    def _on_next_message(self):
        if self.child and self.child.isalive():
            self.child.send('\x1b[C')

    def _clear_map(self):
        self.map_frame.clearBeams()
        self.map_frame.deleteHunterMarker()
        self.map_frame.deletePTUMarker()
        self.save_positions = []
        self.table.setRowCount(0)
        self.btn_clean_map.setDisabled(True)
        self.btn_next_message.setFocusPolicy(Qt.NoFocus)



    def start_simulation(self):
        if not self.file_path:
            Toast("¡No se ha seleccionado una carpeta!", self.parent, "error").show()
            self.error_signal.emit("No se ha seleccionado un archivo .bag")
            return

        # Verificar que exista metadata.yaml y al menos un .db3 en la carpeta seleccionada
        entries = os.listdir(self.file_path)
        has_meta = "metadata.yaml" in entries
        has_db3 = any(name.lower().endswith(".db3") for name in entries)

        if not has_meta or not has_db3:
            Toast(
                "El directorio seleccionado es inválido. ",
                self.parent,
                "error"
            ).show()
            self.error_signal.emit("Falta metadata.yaml o archivo .db3 en el directorio")
            return
        self._start_process()

        # Deshabilitar el botón de iniciar y habilitar el de abortar
        self.btn_iniciar.setDisabled(True)
        self.btn_iniciar.setFocusPolicy(Qt.NoFocus)
        self.btn_pausar.setDisabled(False)
        self.btn_pausar.setFocusPolicy(Qt.StrongFocus)
        self.btn_abortar.setDisabled(False)
        self.btn_abortar.setFocusPolicy(Qt.StrongFocus)
        self.change_button_rosbag(False)
        self.btn_pausar.setText("Pausar")
        self._is_running = True

        # hilo para limpiar cuando acabe
        def _wait_and_finish():
            self.child.wait()    # bloquea hasta que el proceso muera
            self._on_simulation_end()

        threading.Thread(target=_wait_and_finish, daemon=True).start()

    def _on_simulation_end(self):
        # Vuelve todo a como estaba
        self.btn_iniciar.setDisabled(False)
        self.btn_iniciar.setFocusPolicy(Qt.StrongFocus)
        self.btn_pausar.setDisabled(True)
        self.btn_pausar.setFocusPolicy(Qt.NoFocus)
        self.btn_abortar.setDisabled(True)
        self.btn_abortar.setFocusPolicy(Qt.NoFocus)
        self.btn_clean_map.setDisabled(False)
        self.btn_clean_map.setFocusPolicy(Qt.StrongFocus)
        self.change_button_rosbag(True)
        self.btn_next_message.setDisabled(True)
        self.btn_next_message.setFocusPolicy(Qt.NoFocus)
        self._is_running = False
        self.child       = None
        self.frecuency = 1.0
        self.frecuency_label.setText(f"Frecuencia: {(self.frecuency):.2f}")

    def _start_process(self):
        cmd = f"ros2 bag play {self.file_path} --remap /save_simulation:=/data_playback"
        self.child = pexpect.spawn(cmd, encoding='utf-8', echo=True)

    def _on_table_cell_clicked(self, row, col):
        self.set_data_text(row, self.save_positions[row])
    
    def _on_table_item_clicked(self, item):
        row = item.row()
        col = item.column()
        if col == 0:
            self.select_data_row(row, self.save_positions[row])
    
    def _on_table_index_clicked(self, index):
        row = index.row()
        col = index.column()
        if col == 0:
            self.select_data_row(row, self.save_positions[row])

    def change_button_rosbag(self, state):
        self.btn_increase_rate.setDisabled(state)
        self.btn_increase_rate.setFocusPolicy(Qt.NoFocus if state else Qt.StrongFocus)
        self.btn_decrease_rate.setDisabled(state)
        self.btn_decrease_rate.setFocusPolicy(Qt.NoFocus if state else Qt.StrongFocus)


    def abort_simulation(self):
        if self.child and self.child.isalive():
            self.child.terminate(force=False)
            try:
                self.child.wait(2)
            except pexpect.exceptions.TIMEOUT:
                self.child.terminate(force=True)
        self._on_simulation_end()
            

