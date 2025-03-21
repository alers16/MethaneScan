# ptu_config_widget.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QGridLayout, QSizePolicy, QGroupBox, QLineEdit, QDialog
)
from PyQt5.QtGui import QIcon, QPixmap, QPalette, QColor
from PyQt5.QtCore import Qt, pyqtSignal
from methane_scan import qresources_rc # type: ignore

class RobotConfigWidget(QDialog):
    position_saved = pyqtSignal(tuple)
    speed_saved = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__()
        self.position = None
        self.speed = None
        self.parent = parent
        self.setStyleSheet(parent.styleSheet())
        self.closeEvent = lambda event: (self.parent.methane_scan_tab.setEnabled(True), self._reset_fields())
        self._build_ui()

    def _build_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)  # Márgenes algo mayores
        layout.setAlignment(Qt.AlignTop)

        # Configuración de parámetros del Robot
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(0, 0, 0, 20)  # Márgenes inferiores mayores
        config_layout.setSpacing(20)
        layout.addLayout(config_layout)

        # Título principal
        title_label = QLabel("Configuración del Robot")
        title_label.setContentsMargins(0, 0, 0, 20)
        title_label.setMaximumHeight(60)
        title_label.setStyleSheet("font-weight: bold; font-size: 22pt;")
        config_layout.addWidget(title_label)

        # Posición del Robot
        position_group = QGroupBox("Posición")
        position_group.setMaximumHeight(200)
        position_group.setMaximumWidth(300)
        position_group_layout = QGridLayout(position_group)
        position_group_layout.setContentsMargins(10, 10, 10, 10)
        position_group_layout.setHorizontalSpacing(10)
        position_group_layout.setVerticalSpacing(10)
        position_group_layout.setAlignment(Qt.AlignLeft)

        lat_position = self.position[0] if self.position else "N/A"
        self.lat_label = QLabel(f"Latitud: {lat_position}")
        self.lat_label.setMaximumHeight(40)
        lon_position = self.position[1] if self.position else "N/A"
        self.lon_label = QLabel(f"Longitud: {lon_position}")
        self.lon_label.setMaximumHeight(40)

        position_group_layout.addWidget(self.lat_label, 0, 0)
        position_group_layout.addWidget(self.lon_label, 1, 0)

        config_layout.addWidget(position_group)

        # Velocidad del Robot
        speed_group = QGroupBox("Velocidad")
        speed_group.setMaximumHeight(200)
        speed_group.setMaximumWidth(300)
        speed_group_layout = QGridLayout(speed_group)
        speed_group_layout.setContentsMargins(10, 10, 10, 10)
        speed_group_layout.setHorizontalSpacing(10)
        speed_group_layout.setVerticalSpacing(10)
        speed_group_layout.setAlignment(Qt.AlignLeft)

        speed_label = QLabel("Velocidad:")
        speed_label.setMaximumHeight(40)
        self.speed_edit = QLineEdit()
        self.speed_edit.setMaximumHeight(40)
        self.save_velocity = QPushButton("Guardar Velocidad")
        self.save_velocity.setDisabled(True)

        self.save_velocity.clicked.connect(self._save_speed)
        self.speed_edit.textChanged.connect(self._check_fields)

        speed_group_layout.addWidget(speed_label, 0, 0)
        speed_group_layout.addWidget(self.speed_edit, 0, 1)
        speed_group_layout.addWidget(self.save_velocity, 1, 0, 1, 2)
        config_layout.addWidget(speed_group)

        operative_layout = QHBoxLayout()
        operative_layout.setContentsMargins(5, 0, 0, 0)
        operative_layout.setSpacing(10)
        circle_label = QLabel()
        circle_label.setMinimumSize(40, 40)
        circle_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        circle_label.setAlignment(Qt.AlignCenter)
        icon_pixmap = QIcon(":/icon_State.svg").pixmap(64, 64).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        circle_label.setPixmap(icon_pixmap)
        radio = circle_label.width() / 3
        # Usamos border-radius basado en la mitad del tamaño mínimo (40/2 = 20) para mantener el círculo
        circle_label.setStyleSheet(f"background-color: #f0f0f0; border-radius: 10px;")
        operative_layout.addWidget(circle_label)

        state = "Operativo"
        self.state_label = QLabel(f"Estado: {state}")
        self.state_label.setStyleSheet("font-size: 14pt;")
        self.state_label.setMaximumHeight(40)
        operative_layout.addWidget(self.state_label)

        config_layout.addLayout(operative_layout)

        # ------------------ Card 4: Acciones ------------------
        actions_layout = QVBoxLayout()
        actions_layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(actions_layout)
        action_label = QLabel("Acciones")
        action_label.setStyleSheet("font-weight: bold; font-size: 18pt;")
        actions_layout.addWidget(action_label)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 20, 0, 0)
        buttons_layout.setSpacing(10)

        self.apply_btn = QPushButton("Aplicar Alarmas")
        self.discard_btn = QPushButton("Descartar y volver")

        buttons_layout.addWidget(self.apply_btn)
        buttons_layout.addWidget(self.discard_btn)
        actions_layout.addLayout(buttons_layout)
    
    def register_home_callback(self, callback):
        """Permite registrar un callback para volver a la pantalla Home."""
        self.discard_btn.clicked.connect(lambda: (callback(), self._reset_fields()))
    
    def register_apply_callback(self, callback):
        """Permite registrar un callback para aplicar los cambios."""
        self.apply_btn.clicked.connect(lambda: (self._apply_changes(), callback()))
    
    def _reset_fields(self):
        if not self.speed:
            self.speed_edit.clear()
            self.save_velocity.setDisabled(True)
    
    def _apply_changes(self):
        if self.speed:
            self.speed_saved.emit(self.speed)
    
    def _save_speed(self):
        try:
            self.speed = float(self.speed_edit.text())
            self.speed_edit.setReadOnly(True)
            self.save_velocity.setText("Cambiar Velocidad")
            self.save_velocity.clicked.connect(self._activate_edit)
        except ValueError:
            # Si la conversión falla, puedes mostrar un error o ignorar
            print("Error: Las coordenadas no son válidas")

    def _check_fields(self):
        # Habilita el botón si ambos campos tienen texto
        if self.speed_edit.text().strip():
            self.save_velocity.setDisabled(False)
        else:
            self.save_velocity.setDisabled(True)
    
    def _activate_edit(self):
        self.speed_edit.setReadOnly(False)
        self.save_velocity.setText("Guardar Posición")
        self.save_velocity.clicked.connect(self._save_speed)

    def set_position(self, position):
        self.position = position
        self.lat_label.setText(f"Latitud: {position['lat']}")
        self.lon_label.setText(f"Longitud: {position['lng']}")

    def set_state(self, state):
        self.state_label.setText(f"Estado: {state}")
    