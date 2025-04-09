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
        self._build_ui()
        self.PTU_coordinates = None

    def _build_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)  # Balanced margins for better appearance
        layout.setSpacing(15)  # Increased spacing for better visual separation

        # Configuración de parámetros de la PTU
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(0, 0, 0, 20)  # Márgenes inferiores mayores
        layout.addLayout(config_layout)

        # Título principal
        title_label = QLabel("Configuración de la PTU")
        title_label.setContentsMargins(0, 0, 0, 10)
        title_label.setStyleSheet("font-weight: bold; font-size: 22pt;")
        title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        config_layout.addWidget(title_label)

        cards_layout = QHBoxLayout()
        cards_layout.setAlignment(Qt.AlignLeft)
        config_layout.addLayout(cards_layout)
        

        # ------------------ Card 1: Parámetros de Percepción ------------------
        card1 = self._create_card(
            title="Parámetros de Percepción",
            body="Greyhound decisively hello cordingly wonderfully marginally for upon excluding.",
            icon=":/icon_Perception.svg"
        )
        cards_layout.addWidget(card1, 1)

        # ------------------ Card 2: Parámetros de Detección ------------------
        card2 = self._create_card(
            title="Parámetros de Detección",
            body="Greyhound decisively hello cordingly wonderfully marginally for upon excluding.",
            icon=":/icon_Detection.svg"
        )
        cards_layout.addWidget(card2, 1)

        # ------------------  Estado de la PTU ------------------
        state_layout = QVBoxLayout()
        layout.addLayout(state_layout)
        state_layout.setContentsMargins(0, 0, 0, 40)

        state_title = QLabel("Estado de la PTU")
        state_title.setStyleSheet("font-weight: bold; font-size: 22pt;")
        state_title.setContentsMargins(0, 0, 0, 10)
        state_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        state_layout.addWidget(state_title)

        position_group = QGroupBox("Posición")
        position_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        position_group_layout = QGridLayout(position_group)
        position_group_layout.setContentsMargins(10, 10, 10, 10)
        position_group_layout.setHorizontalSpacing(10)
        position_group_layout.setVerticalSpacing(10)
        position_group_layout.setAlignment(Qt.AlignLeft)

        lat_label = QLabel("Latitud:")
        lat_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        lon_label = QLabel("Longitud:")
        lon_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.lat_edit = QLineEdit()
        self.lat_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lon_edit = QLineEdit()
        self.lat_edit.setText("36.71579")
        self.lon_edit.setText("-4.478165")
        self.lon_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.save_button = QPushButton("Guardar Posición")
        self.save_button.setStyleSheet("margin-top: 10px;")
        self.save_button.setDisabled(True)

        self.save_button.clicked.connect(self._save_position)
        self.lat_edit.textChanged.connect(self._check_fields)
        self.lon_edit.textChanged.connect(self._check_fields)    

        position_group_layout.addWidget(lat_label, 0, 0)
        position_group_layout.addWidget(self.lat_edit, 0, 1, alignment=Qt.AlignLeft)
        position_group_layout.addWidget(lon_label, 1, 0)
        position_group_layout.addWidget(self.lon_edit, 1, 1, alignment=Qt.AlignLeft)
        position_group_layout.addWidget(self.save_button, 2, 0, 1, 2, alignment= Qt.AlignLeft)

        state_layout.addWidget(position_group)

        operative_layout = QHBoxLayout()
        operative_layout.setContentsMargins(5, 20, 0, 0)
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

        state = "No se encuentra: 'Confirmación', 'Posición'"
        self.state_label = QLabel(f"Estado: {state}")
        self.state_label.setStyleSheet("font-size: 14pt;")
        self.state_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        operative_layout.addWidget(self.state_label)

        state_layout.addLayout(operative_layout)

        # ------------------ Dialog buttons ------------------
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self._on_reject)
        layout.addWidget(self.button_box)
        
        # Set size policies for the main widget to expand properly
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Remove fixed constraints that would prevent proper sizing
        self.setMinimumWidth(500)
        self.adjustSize()


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
    