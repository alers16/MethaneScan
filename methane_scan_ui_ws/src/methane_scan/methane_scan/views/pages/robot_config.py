# ptu_config_widget.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QGridLayout, QSizePolicy, QGroupBox, QLineEdit, QDialog,
    QDialogButtonBox
)
from PyQt5.QtGui import QIcon, QPixmap, QPalette, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QDoubleValidator
from methane_scan import qresources_rc # type: ignore

class RobotConfigWidget(QWidget):
    position_saved = pyqtSignal(tuple)
    speed_saved = pyqtSignal(float)
    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.position = None
        self.speed = None
        self.parent = parent
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())

        self.setStyleSheet("""
            *:focus {
                border: 2px solid #009688;  /* teal para buen contraste */
                border-radius: 4px;
           }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._build_ui()

    def _build_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)  # Margins balanced
        layout.setSpacing(12)

        # Configuración de parámetros del Robot
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(0, 0, 0, 10)  # Balanced margins
        config_layout.setSpacing(15)
        layout.addLayout(config_layout)

        # Título principal
        title_label = QLabel("Configuración del Robot")
        title_label.setContentsMargins(0, 0, 0, 10)
        title_label.setStyleSheet("font-weight: bold; font-size: 22pt;")
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        config_layout.addWidget(title_label)

        # Posición del Robot
        position_group = QGroupBox("Posición")
        position_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        position_group_layout = QGridLayout(position_group)
        position_group_layout.setContentsMargins(12, 12, 12, 12)
        position_group_layout.setHorizontalSpacing(10)
        position_group_layout.setVerticalSpacing(10)
        position_group_layout.setAlignment(Qt.AlignLeft)

        lat_position = self.position[0] if self.position else "N/A"
        self.lat_label = QLabel(f"Latitud: {lat_position}")
        self.lat_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lon_position = self.position[1] if self.position else "N/A"
        self.lon_label = QLabel(f"Longitud: {lon_position}")
        self.lon_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        position_group_layout.addWidget(self.lat_label, 0, 0)
        position_group_layout.addWidget(self.lon_label, 1, 0)

        config_layout.addWidget(position_group)

        # Velocidad del Robot
        speed_group = QGroupBox("Velocidad")
        speed_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        speed_group_layout = QGridLayout(speed_group)
        speed_group_layout.setContentsMargins(12, 12, 12, 12)
        speed_group_layout.setHorizontalSpacing(10)
        speed_group_layout.setVerticalSpacing(10)
        speed_group_layout.setAlignment(Qt.AlignLeft)
        speed_label = QLabel("Velocidad:")
        speed_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.speed_edit = QLineEdit()
        self.speed_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.save_speed = QPushButton("Guardar Velocidad")
        self.save_speed.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.save_speed.setDisabled(True)

        self.save_speed.clicked.connect(self._save_speed)
        self.speed_edit.textChanged.connect(self._check_fields)

        self.error_label = QLabel("La velocidad debe ser mayor que 0")
        self.error_label.setStyleSheet("color: red; font-size: 10pt;")
        self.error_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.error_label.hide()

        speed_group_layout.addWidget(speed_label, 0, 0)
        speed_group_layout.addWidget(self.speed_edit, 0, 1)
        speed_group_layout.addWidget(self.save_speed, 2, 0, 1, 2)
        speed_group_layout.addWidget(self.error_label, 1, 0, 1, 2)
        config_layout.addWidget(speed_group)

        operative_layout = QHBoxLayout()
        operative_layout.setContentsMargins(5, 10, 5, 5)
        operative_layout.setSpacing(10)
        circle_label = QLabel()
        circle_label.setFixedSize(30, 30)
        circle_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        circle_label.setAlignment(Qt.AlignCenter)
        icon_pixmap = QIcon(":/icon_State.svg").pixmap(64, 64).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        circle_label.setPixmap(icon_pixmap)
        radio = circle_label.width() / 3
        # Usamos border-radius basado en la mitad del tamaño mínimo (40/2 = 20) para mantener el círculo
        circle_label.setStyleSheet(f"background-color: #f0f0f0; border-radius: 10px;")
        operative_layout.addWidget(circle_label)

        state = "No se encuentra: 'Velocidad', 'Posición', 'Trayectoria'"
        self.state_label = QLabel(f"Estado: {state}")
        self.state_label.setStyleSheet("font-size: 14pt;")
        self.state_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        operative_layout.addWidget(self.state_label)
        config_layout.addLayout(operative_layout)

        # ------------------ Dialog buttons ------------------
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self._on_reject)
        self.button_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.button_box)
    
    def _on_accept(self):
        """Handle OK button click"""
        self._apply_changes()
        self.accepted.emit()
    
    def _on_reject(self):
        """Handle Cancel button click"""
        self._reset_fields()
        self.rejected.emit()
    
    def _reset_fields(self):
        if not self.speed:
            self.speed_edit.clear()
            self.save_speed.setDisabled(True)
    
    def _apply_changes(self):
        if self.speed:
            if not self.speed_edit.text().strip():
                self.speed_edit.setText(str(self.speed))
                self.speed_edit.setReadOnly(True)
                self.save_speed.setText("Cambiar Velocidad")
                self.save_speed.clicked.connect(self._activate_edit)
            self.speed_saved.emit(self.speed)
        else:
            self.speed_saved.emit(0.0)
    
    def _save_speed(self):
        try:
            self.speed = float(self.speed_edit.text()) if self.speed_edit.text() != "" else 0.0
            self.speed_edit.setReadOnly(True)
            self.save_speed.setText("Cambiar Velocidad")
            self.save_speed.clicked.connect(self._activate_edit)
        except ValueError:
            # Si la conversión falla, puedes mostrar un error o ignorar
            print("Error: Las coordenadas no son válidas")

    def _check_fields(self):
        # Habilita el botón si ambos campos tienen texto
        if self.speed_edit.text().strip():
            if float(self.speed_edit.text()) <= 0:
                self.error_label.show()
                self.save_speed.setDisabled(True)
            else:
                self.error_label.hide()
                self.save_speed.setDisabled(False)
        else:
            self.save_speed.setDisabled(True)
    
    def _activate_edit(self):
        self.speed_edit.setReadOnly(False)
        self.save_speed.setText("Guardar Posición")
        self.save_speed.clicked.connect(self._save_speed)

    def set_position(self, position):
        self.position = position
        self.lat_label.setText(f"Latitud: {position['Latitude']}")
        self.lon_label.setText(f"Longitud: {position['Longitude']}")

    def set_state(self, state):
        self.state_label.setText(f"Estado: {state}")
        
    def sizeHint(self):
        """Return a size based on content"""
        return QSize(450, 550)
    