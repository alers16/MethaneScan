from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication
import platform

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.initUI()
        self.start = QPoint(0, 0)
        self.moving = False
        self._restore_ratio = 0.5  # Valor por defecto para posicionar al restaurar

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        # Izquierda: Título y botones de navegación
        self.appTitle = QLabel("MethaneScan", self)
        self.appTitle.setStyleSheet("color: #ECECEC; font-size: 14pt;")
        layout.addWidget(self.appTitle)

        self.navMethane = QPushButton("Inicio", self)
        self.navMethane.setStyleSheet("background: transparent; color: #ECECEC; border: none; font-size: 10pt;")
        self.navDatos = QPushButton("Datos", self)
        self.navDatos.setStyleSheet("background: transparent; color: #ECECEC; border: none; font-size: 10pt;")
        layout.addWidget(self.navMethane)
        layout.addWidget(self.navDatos)
        layout.addStretch()

        # Derecha: Botones de control de ventana
        self.btnMin = QPushButton("—", self)
        self.btnMin.setFixedSize(40, 30)
        self.btnMin.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ECECEC;
                border: none;
            }
            QPushButton:hover {
                background-color: #3A3A3A;
            }
        """)
        self.btnMax = QPushButton("□", self)
        self.btnMax.setFixedSize(40, 30)
        self.btnMax.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ECECEC;
                border: none;
            }
            QPushButton:hover {
                background-color: #3A3A3A;
            }
        """)
        self.btnClose = QPushButton("X", self)
        self.btnClose.setFixedSize(40, 30)
        self.btnClose.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #ECECEC;
                border: none;
            }
            QPushButton:hover {
                background-color: #E81123;
            }
        """)
        layout.addWidget(self.btnMin)
        layout.addWidget(self.btnMax)
        layout.addWidget(self.btnClose)

        # Conexiones de botones
        self.btnMin.clicked.connect(self.parent.showMinimized)
        self.btnMax.clicked.connect(self.maximize_restore)
        self.btnClose.clicked.connect(self.parent.close)


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
    
    def register_home_callback(self, callback):
        self.navMethane.clicked.connect(callback)