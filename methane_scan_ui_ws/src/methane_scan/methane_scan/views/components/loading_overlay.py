from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMovie

class LoadingOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        # 1) Flags: Qt.Tool para que flote sobre el parent, sin decoraciones
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # 2) Transparencia parcial
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 3) Captura todos los eventos para bloquear la UI
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # 4) Fondo gris semitransparente
        self._bg = QWidget(self)
        self._bg.setStyleSheet("background-color: rgba(0,0,0,128);")
        self._bg.setGeometry(self.rect())

        # 5) Spinner
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setAlignment(Qt.AlignCenter)
        spinner = QLabel(self)
        movie = QMovie(":/spinner.gif")
        spinner.setMovie(movie)
        movie.start()
        layout.addWidget(spinner)

        self.hide()

    def resizeEvent(self, e):
        # Actualiza la geometría del fondo gris
        self._bg.setGeometry(self.rect())
        super().resizeEvent(e)

