import sys, time
import rclpy
from PyQt5.QtCore    import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui     import QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)

from PyQt5.QtGui import QGuiApplication

class SplashScreen(QWidget):
    def __init__(self, image_path: str, nodes: list):
        """
        :param image_path: Ruta a la imagen de fondo (tu splash .png)
        :param nodes: lista de nombres de nodos a esperar
        """
        super().__init__(flags=Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #1F2933;")

        # 1) Imagen de fondo
        pix = QPixmap(image_path)
        self._bg_label = QLabel(self)
        self._bg_label.setFixedSize(400, 400)
        scaled_pix = pix.scaled(
            self._bg_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self._bg_label.setPixmap(scaled_pix)

        # 2) Layout principal vertical
        self._main = QVBoxLayout(self)
        self._main.addSpacerItem(
            QSpacerItem(0, -100, QSizePolicy.Minimum, QSizePolicy.Fixed)
        )
        self._main.addWidget(self._bg_label, alignment=Qt.AlignHCenter)

        # 3) Texto “MethaneScan”
        self._title = QLabel("MethaneScan", self)
        self._title.setStyleSheet("color: #FFFFFF;")
        self._title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self._main.addWidget(self._title, alignment=Qt.AlignHCenter)
        self._main.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # 4) Contenedor de estado de nodos
        self._node_labels = {}
        for name in nodes:
            lbl = QLabel(f"• {name}:  ⏳", self)
            lbl.setStyleSheet("color: #BBBBBB; font: 10pt 'Segoe UI';")
            self._main.addWidget(lbl, alignment=Qt.AlignHCenter)
            self._node_labels[name] = lbl

        self.adjustSize()
        # 5) Centrar en pantalla
        screens = QGuiApplication.screens()
        target = screens[0] if len(screens) > 1 else screens[0]

        geo   = target.geometry()
        x     = geo.x() + (geo.width()  - self.width())  // 2
        y     = geo.y() + (geo.height() - self.height()) // 2
        self.move(x, y)

    def mark_node_ready(self, name: str):
        """Cambia el nodo a estado listo."""
        lbl = self._node_labels.get(name)
        if lbl:
            lbl.setText(f"• {name}:  ✔️")
            lbl.setStyleSheet("color: #00C853; font: 10pt 'Segoe UI';")
    
    def mark_node_error(self, name: str):
        """Cambia el nodo a estado de error."""
        lbl = self._node_labels.get(name)
        if lbl:
            lbl.setText(f"• {name}:  ❌")
            lbl.setStyleSheet("color: #D32F2F; font: 10pt 'Segoe UI';")
