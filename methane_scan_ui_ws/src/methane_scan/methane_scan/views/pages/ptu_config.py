# ptu_config_widget.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QGridLayout, QSizePolicy, QGroupBox, QLineEdit, QDialog,
    QDialogButtonBox
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from methane_scan import qresources_rc # type: ignore

class PTUConfigWidget(QWidget):
    position_saved = pyqtSignal(tuple)
    accepted = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
        self.PTU_coordinates = None
        self._build_ui()

    def _build_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)  # Balanced margins for better appearance
        layout.setSpacing(8)

        # Configuración de parámetros de la PTU
        config_layout = QVBoxLayout()
        layout.addLayout(config_layout)

        # Título principal
        title_label = QLabel("Configuración de la PTU")
        title_label.setContentsMargins(0, 0, 0, 8)
        title_label.setStyleSheet("font-weight: bold; font-size: 22pt;")
        config_layout.addWidget(title_label)

        # Posición de la PTU
        position_group = QGroupBox("Posición")
        position_group_layout = QGridLayout(position_group)
        position_group_layout.setContentsMargins(6, 6, 6, 6)
        position_group_layout.setHorizontalSpacing(6)
        position_group_layout.setVerticalSpacing(6)
        position_group_layout.setAlignment(Qt.AlignLeft)

        lat_position = self.PTU_coordinates[0] if self.PTU_coordinates else "N/A"
        self.lat_label = QLabel(f"Latitud: {lat_position}")
        self.lat_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lat_label.setStyleSheet("font-size: 12pt;")
        lon_position = self.PTU_coordinates[1] if self.PTU_coordinates else "N/A"
        self.lon_label = QLabel(f"Longitud: {lon_position}")
        self.lon_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lon_label.setStyleSheet("font-size: 12pt;")

        position_group_layout.addWidget(self.lat_label, 0, 0)
        position_group_layout.addWidget(self.lon_label, 1, 0)

        config_layout.addWidget(position_group)

        operative_layout = QHBoxLayout()
        operative_layout.setContentsMargins(4, 4, 4, 4)
        operative_layout.setSpacing(6)
        circle_label = QLabel()
        circle_label.setMinimumSize(30, 30)
        circle_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        circle_label.setAlignment(Qt.AlignCenter)
        icon_pixmap = QIcon(":/icon_State.svg").pixmap(64, 64).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        circle_label.setPixmap(icon_pixmap)
        radio = circle_label.width() / 3
        # Usamos border-radius basado en la mitad del tamaño mínimo (40/2 = 20) para mantener el círculo
        circle_label.setStyleSheet(f"background-color: #f0f0f0; border-radius: 10px;")
        operative_layout.addWidget(circle_label)

        state = "No se encuentra: 'Confirmación', 'Posición'"
        self.state_label = QLabel(f"Estado: {state}")
        self.state_label.setStyleSheet("font-size: 14pt;")
        self.state_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        operative_layout.addWidget(self.state_label)
        config_layout.addLayout(operative_layout)
        
        # Remove fixed constraints that would prevent proper sizing
        self.setMinimumWidth(400)
        self.setMaximumHeight(400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)


    def _create_card(self, title, body, icon):
        """Crea un QFrame estilo 'card' con título y texto."""
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # Remove maximum height constraint to allow content-based sizing
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)

        circle_label = QLabel()
        circle_label.setMinimumSize(40, 40)
        circle_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        circle_label.setAlignment(Qt.AlignCenter)
        icon_pixmap = QIcon(icon).pixmap(64, 64).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        circle_label.setPixmap(icon_pixmap)
        radio = circle_label.width() / 3
        # Usamos border-radius basado en la mitad del tamaño mínimo (40/2 = 20) para mantener el círculo
        circle_label.setStyleSheet(f"background-color: #f0f0f0; border-radius: 10px;")
        card_layout.addWidget(circle_label)

        title_label = QLabel(title)
        title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        title_label.setStyleSheet("font-weight: bold; font-size: 16pt;")
        card_layout.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        body_label.setStyleSheet("font-size: 12pt;")
        card_layout.addWidget(body_label)

        return card
    
    def _on_accept(self):
        """Handle OK button click"""
        self._apply_changes()
        self.accepted.emit()
    
    def _on_reject(self):
        """Handle Cancel button click"""
        self._reset_fields()
        self.rejected.emit()
    
    def _reset_fields(self):
        if not self.PTU_coordinates:
            self.lat_edit.clear()
            self.lon_edit.clear()
            self.save_button.setDisabled(True)
            self.lat_edit.setReadOnly(False)
            self.lon_edit.setReadOnly(False)
        
    def _apply_changes(self):
        #Por ahora asi, luego hay que añadir el guardado de los parametros
        if self.PTU_coordinates:
            self.position_saved.emit(self.PTU_coordinates)
    
    def sizeHint(self):
        # Calculate a better size based on content
        return QSize(550, 650)
    
    def set_position(self, lat, lng):
        """Set the PTU position and update the UI."""
        self.PTU_coordinates = (lat, lng)
        self.lat_label.setText(f"Latitud: {lat}")
        self.lon_label.setText(f"Longitud: {lng}")
    
    def _save_position(self):
        try:
            lat = float(self.lat_edit.text())
            lng = float(self.lon_edit.text())
            self.PTU_coordinates = (lat, lng)

            self.lat_edit.setReadOnly(True)
            self.lon_edit.setReadOnly(True)
            self.save_button.setText("Cambiar Posición")
            self.save_button.clicked.connect(self._activate_edit)
        except ValueError:
            # Si la conversión falla, puedes mostrar un error o ignorar
            print("Error: Las coordenadas no son válidas")
    
    def _activate_edit(self):
        self.lat_edit.setReadOnly(False)
        self.lon_edit.setReadOnly(False)
        self.save_button.setText("Guardar Posición")
        self.save_button.clicked.connect(self._save_position)
    
    def _check_fields(self):
        # Habilita el botón si ambos campos tienen texto
        if self.lat_edit.text().strip() and self.lon_edit.text().strip():
            self.save_button.setDisabled(False)
        else:
            self.save_button.setDisabled(True)

    def set_state(self, state):
        self.state_label.setText(f"Estado: {state}")
    