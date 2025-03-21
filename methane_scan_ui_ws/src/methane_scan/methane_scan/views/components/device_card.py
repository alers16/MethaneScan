from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy
from PyQt5.QtGui import QIcon

class DeviceCard(QFrame):
    def __init__(self, device, status_text, icon):
        super().__init__()
        self.device = device
        self._create_device_card(device, status_text, icon)

    def _create_device_card(self, device_name, status_text, icon):
        """Crea una 'card' para mostrar el estado de un dispositivo de forma responsive."""
        self.setObjectName("deviceCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setCursor(Qt.PointingHandCursor)
        
        v_layout = QVBoxLayout(self)
        v_layout.setContentsMargins(10, 10, 10, 10)
        v_layout.setSpacing(5)
        
        # Círculo con ícono
        circle_label = QLabel()
        circle_label.setMinimumSize(40, 40)
        circle_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        circle_label.setAlignment(Qt.AlignCenter)
        icon_pixmap = QIcon(icon).pixmap(64, 64).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        circle_label.setPixmap(icon_pixmap)
        circle_label.setStyleSheet("background-color: #f0f0f0; border-radius: 10px;")
        
        status_title = QLabel("Estado del dispositivo")
        status_title.setStyleSheet("color: #666666; font-size: 10pt; font-weight: bold;")
        
        label_device = QLabel(device_name)
        label_device.setStyleSheet("font-weight: bold; font-size: 13pt;")

        self.label_status = QLabel(status_text)
        self.label_status.setStyleSheet("color: #666666; font-size: 10pt;")
        
        v_layout.addWidget(circle_label)
        v_layout.addWidget(status_title)
        v_layout.addWidget(label_device)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        status_layout.addWidget(self.label_status)

        # Creamos el LED o icono
        self.led_label = QLabel()
        self.led_label.setMaximumSize(24, 24)
        self.led_label.setStyleSheet("background-color: #dc3545; border-radius: 9px;")  # border-radius ajustado para un círculo perfecto
        self.led_label.setToolTip(f"{device_name} no listo")
        
        status_layout.addWidget(self.led_label)
        v_layout.addLayout(status_layout)

    def set_status(self, status, errors = []):
        """Actualiza el estado del dispositivo y muestra el texto correspondiente."""
        if status == True:
            self.led_label.setStyleSheet("background-color: #28a745; border-radius: 9px;")
            self.led_label.setToolTip(f"{self.device} listo")
            self.label_status.setText("Conectado y listo para funcionar")
        else:
            self.led_label.setStyleSheet("background-color: #dc3545; border-radius: 9px;")
            self.led_label.setToolTip(f"{self.device} no listo")
            self.label_status.setText(f"No se encuentran: {errors}")
