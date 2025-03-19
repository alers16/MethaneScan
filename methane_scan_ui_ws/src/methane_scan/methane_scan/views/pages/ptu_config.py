# ptu_config_widget.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QGridLayout, QSizePolicy, QGroupBox
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from methane_scan import qresources_rc # type: ignore

class PTUConfigWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.PTU_coordinates = None

    def _build_ui(self):
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)  # Márgenes algo mayores

        # Configuración de parámetros de la PTU
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(0, 0, 0, 20)  # Márgenes inferiores mayores
        layout.addLayout(config_layout)

        # Título principal
        title_label = QLabel("Configuración de la PTU")
        title_label.setContentsMargins(0, 0, 0, 20)
        title_label.setMaximumHeight(60)
        title_label.setStyleSheet("font-weight: bold; font-size: 18pt;")
        config_layout.addWidget(title_label)

        cards_layout = QHBoxLayout()
        cards_layout.setAlignment(Qt.AlignLeft)
        config_layout.addLayout(cards_layout)

        #Mirar ChatGPT para hacerlo más bonito
        

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

        state_title = QLabel("Estado de la PTU")
        state_title.setStyleSheet("font-weight: bold; font-size: 18pt;")
        state_title.setMaximumHeight(60)
        state_layout.addWidget(state_title)

        position_group = QGroupBox("Posición")
        position_group_layout = QGridLayout()
        position_group.setLayout(position_group_layout)
        state_layout.addWidget(position_group)



        # ------------------ Card 4: Acciones ------------------
        card4 = QFrame()
        card4.setObjectName("cardFrame")
        card4_layout = QHBoxLayout(card4)
        card4_layout.setContentsMargins(15, 15, 15, 15)
        card4_layout.setSpacing(10)

        action_label = QLabel("Acciones")
        action_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        card4_layout.addWidget(action_label)

        card4_layout.addStretch()

        self.apply_btn = QPushButton("Aplicar Alarmas")
        self.discard_btn = QPushButton("Descartar y volver")

        card4_layout.addWidget(self.apply_btn)
        card4_layout.addWidget(self.discard_btn)

        layout.addWidget(card4)

    def _create_card(self, title, body, icon):
        """Crea un QFrame estilo 'card' con título y texto."""
        card = QFrame()
        card.setObjectName("deviceCard")
        card.setMaximumHeight(160)
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
        title_label.setMaximumHeight(40)
        title_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        card_layout.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setMaximumHeight(40) 
        body_label.setStyleSheet("font-size: 12pt;")
        card_layout.addWidget(body_label)

        return card
    
    def register_home_callback(self, callback):
        """Permite registrar un callback para volver a la pantalla Home."""
        self.discard_btn.clicked.connect(callback)
    