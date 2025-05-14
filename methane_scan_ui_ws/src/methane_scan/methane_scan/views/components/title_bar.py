from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication, QToolButton, QButtonGroup
import platform

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(36)
        self._restore_ratio = 0.5

        # Fondo tipo VSCode Dark
        self.setStyleSheet("""
            TitleBar { background: #252526; }
        """)
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # — Texto de la app
        self.appTitle = QLabel("MethaneScan", self)
        self.appTitle.setStyleSheet("""
            color: #CCCCCC;
            font: bold 12pt "Segoe UI";
        """)
        layout.addWidget(self.appTitle)

        # — Botones de navegación en grupo exclusivo
        self.navGroup = QButtonGroup(self)
        self.navGroup.setExclusive(True)

        def makeNav(name, slot):
            btn = QToolButton(self)
            btn.setText(name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QToolButton {
                    background: transparent;
                    color: #CCCCCC;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                QToolButton:hover, QToolButton:focus {
                    background: #3E3E42;
                    color: #FFFFFF;
                }
                QToolButton:checked {
                    background: #094771;
                    color: #FFFFFF;
                }
            """)
            btn.clicked.connect(slot)
            self.navGroup.addButton(btn)
            layout.addWidget(btn)
            return btn

        # Creamos y guardamos referencias
        self.btnInicio    = makeNav("Inicio",     self.parent.switch_to_home_tab)
        self.btnSimulacion= makeNav("Simulación", self.parent.switch_to_simulation_tab)

        # Seleccionamos Inicio por defecto
        self.btnInicio.setChecked(True)

        layout.addStretch()

        self.mqtt_status_label = QLabel("MQTT Connection: 🟢", self)
        layout.addWidget(self.mqtt_status_label)
        layout.addSpacing(10)
        self.mqtt_bridge_label = QLabel("MQTT Bridge: 🟢", self)
        layout.addWidget(self.mqtt_bridge_label)
        layout.addSpacing(10)

        # — Botones de ventana (min, max/rest, close)
        for sym, name, slot in (
            ("–", "Minimize", self.parent.showMinimized),
            ("□", "MaxRestore", self.maximize_restore),
            ("✕", "Close",      self.parent.close),
        ):
            tb = QToolButton(self)
            tb.setText(sym)
            tb.setObjectName(name)
            tb.setFixedSize(36, 28)
            tb.setFocusPolicy(Qt.StrongFocus)
            tb.setStyleSheet(f"""
                QToolButton#{name} {{
                    background: transparent;
                    color: #CCCCCC;
                    border-radius: 2px;
                }}
                QToolButton#{name}:hover {{
                    background: #3E3E42;
                }}
                QToolButton#{name}:pressed {{
                    background: {"#E81123" if name=="Close" else "#094771"};
                }}
                QToolButton#{name}:focus {{
                    outline: 1px solid #007ACC;
                }}
            """)
            tb.clicked.connect(slot)
            layout.addWidget(tb)

        # Guardamos para cualquier uso futuro
        count = layout.count()
        self.btnMin, self.btnMax, self.btnClose = (
            layout.itemAt(count-3).widget(),
            layout.itemAt(count-2).widget(),
            layout.itemAt(count-1).widget()
        )


    def maximize_restore(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.btnMax.setText("□")
        else:
            self.parent.showMaximized()
            self.btnMax.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Comprobar si el widget en la posición del clic es un botón.
            child = self.childAt(event.pos())
            if child is not None and child.inherits("QPushButton"):
                # Si se pulsa sobre un botón, no iniciamos el movimiento.
                return
            # Si la ventana está maximizada, se restaura y calculamos el offset horizontal.
            if self.parent.isMaximized():
                self._restore_ratio = event.pos().x() / self.parent.width()
                self.parent.showNormal()
                self.btnMax.setText("□")
            self.moving = True
            # Forzamos el offset vertical a 0 para que el cursor quede justo en el borde superior
            self.offset = QPoint(event.pos().x(), 0)

    def mouseMoveEvent(self, event):
        if self.moving:
            # Mover la ventana de modo que el borde superior se alinee con el cursor
            self.parent.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        # Comprobamos si el widget en la posición del evento es un botón
        child = self.childAt(event.pos())
        if child is not None and child.inherits("QPushButton"):
            self.moving = False
            return
        self.moving = False
        # Si la ventana se acerca al borde superior, maximizarla (snap)
        screen = QApplication.primaryScreen().availableGeometry()
        so = platform.system()
        if so == "Windows":
            if self.parent.y() <= 10:
                self.maximize_restore()
        elif so == "Linux":
            if self.parent.y() <= 56:
                self.maximize_restore()

    def set_active_tab(self, tab_name):
        """Set the active tab based on the name."""
        if tab_name == "Inicio":
            self.btnInicio.setChecked(True)
        elif tab_name == "Simulación":
            self.btnSimulacion.setChecked(True)

    def set_mqtt_status(self, status):
        """Set the MQTT connection status."""
        if status:
            self.mqtt_status_label.setText("MQTT Connection: 🟢")
        else:
            self.mqtt_status_label.setText("MQTT Connection: 🔴")
    
    def set_mqtt_bridge_status(self, status):
        """Set the MQTT bridge status."""
        if status:
            self.mqtt_bridge_label.setText("MQTT Bridge: 🟢")
        else:
            self.mqtt_bridge_label.setText("MQTT Bridge: 🔴")