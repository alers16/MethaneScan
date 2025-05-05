from PyQt5.QtWidgets import (
    QDialog, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QPushButton, QFrame, QSizePolicy, QToolButton,
    QMainWindow, QApplication, QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QEventLoop, QEvent
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtGui import QMouseEvent

import requests
import os
import pickle
from PyQt5.QtWidgets import QMessageBox

DATA_STORE = "map_previews.data"

class TrajectorySelectorDialog(QWidget):
    """
    Diálogo para seleccionar una trayectoria existente o añadir una nueva.
    """
    accepted = pyqtSignal()
    rejected = pyqtSignal()
    select_trajectory_signal = pyqtSignal(list)

    def __init__(self, api_key=None, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.parent = parent
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())

        self.setStyleSheet("""
            *:focus {
                border: 2px solid #009688;  /* teal para buen contraste */
                border-radius: 4px;
           }
        """)
        # Cargar entradas guardadas
        self.trajectories = self.load_all_map_previews()
        self.selected_trajectory = None

        self._build_ui()

        self.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        # Si pulsas Return o Enter
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            w = self.focusWidget()
            if isinstance(w, QPushButton) and w.isEnabled():
                w.click()
                return True    # consumimos el evento
            if isinstance(w, QLineEdit):
                # Si es un QLineEdit, lo ignoramos
                return False
            if isinstance(w, QFrame):
                # dentro de eventFilter, en el caso de una card:
                pos = w.rect().center()
                release_event = QMouseEvent(
                    QEvent.MouseButtonRelease,
                    pos,
                    Qt.LeftButton,
                    Qt.LeftButton,
                    Qt.NoModifier
                )
                w.mouseReleaseEvent(release_event)
                return True
            if isinstance(w, QToolButton):
                w.click()
                return True
        return super().eventFilter(obj, event)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)  # Balanced margins for better appearance
        layout.setSpacing(15)

        title_label = QLabel("Selecciona una trayectoria")
        title_label.setContentsMargins(0, 0, 0, 10)
        title_label.setStyleSheet("font-weight: bold; font-size: 22pt;")
        title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout.addWidget(title_label)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFocusPolicy(Qt.NoFocus)
        scroll.viewport().setFocusPolicy(Qt.NoFocus)
        # Mantener estilo coherente dentro del scroll
        content = QWidget()
        content.setFocusPolicy(Qt.NoFocus)
        content.setStyleSheet("background-color: transparent;")
        self.cards_layout = QVBoxLayout(content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(15)
        self.cards_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.btn_add = QPushButton("Añadir nueva trayectoria")
        self.btn_add.clicked.connect(self.select_area)
        self.btn_select = QPushButton("Seleccionar trayectoria")
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self.select_trajectory)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_select)

        layout.addLayout(btn_layout)

        self.refresh_trajectories()

        self.setMinimumSize(600, 400)

    def _create_card(self, traj):
        """
        Crea un QFrame estilo 'card' para una trayectoria:
        - Solo el borde exterior y esquinas redondeadas en el frame principal.
        - El resto (icono, textos, toggle) sin bordes ni fondos.
        """
        # Subclase de QToolButton para manejar enter/leave y deshabilitar el hover del frame
        class HoverToggleButton(QToolButton):
            def __init__(self, parent_frame, name, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.frame = parent_frame
                self.setObjectName(name)

            def enterEvent(self, event):
                # Desactiva hover del frame
                self.frame.setProperty("hoverEnabled", False)
                self.frame.style().unpolish(self.frame)
                self.frame.style().polish(self.frame)
                super().enterEvent(event)

            def leaveEvent(self, event):
                # Reactiva hover del frame
                self.frame.setProperty("hoverEnabled", True)
                self.frame.style().unpolish(self.frame)
                self.frame.style().polish(self.frame)
                super().leaveEvent(event)

        frame = QFrame()
        frame.setObjectName("cardFrame")
        frame.setProperty("hoverEnabled", True)
        frame.setFrameShape(QFrame.NoFrame)
        frame.setStyleSheet("""
            QFrame#cardFrame {
                background-color: transparent;
                border: 1px solid #555555;
                border-radius: 8px;
            }
            /* Sólo se aplica hover si hoverEnabled == true */
            QFrame#cardFrame[hoverEnabled="true"]:hover {
                background-color: #404040;
                border: 1px solid #888888;
            }

            QFrame#cardFrame[selected="true"] {
                background-color: #606060;
                border: 1px solid #888888;
            }
            /* Cuando el propio frame tenga el foco */
            QFrame#cardFrame:focus {
                border: 2px solid #009688;
                border-radius: 8px;   /* mantén el mismo radio que el normal */
            }
            QToolButton:focus {
                border: 2px solid #009688;
                border-radius: 8px;
            }                        
        """)
        frame.setCursor(Qt.PointingHandCursor)
        frame.setFocusPolicy(Qt.StrongFocus)
        v_layout = QVBoxLayout(frame)
        v_layout.setContentsMargins(12, 12, 12, 12)
        v_layout.setSpacing(8)

        # --------- Header -----------
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)

        # Icono grande blanco
        icon_size = 32
        orig = QIcon(":/icon_Trayectoria.svg").pixmap(icon_size, icon_size)
        white = QPixmap(icon_size, icon_size)
        white.fill(Qt.transparent)
        painter = QPainter(white)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(0, 0, orig)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(white.rect(), QColor("white"))
        painter.end()
        icon_label = QLabel()
        icon_label.setPixmap(white)
        icon_label.setFixedSize(icon_size, icon_size)
        icon_label.setStyleSheet("background: transparent; border: none;")
        h_layout.addWidget(icon_label)

        # Textos
        title = QLabel(traj['nombre'])
        title.setStyleSheet("background: transparent; border: none; font-weight: bold; font-size: 13pt; color: #eeeeee;")
        #subtitle = QLabel(f"PTU: ({traj['ptu']['lat']:.5f}, {traj['ptu']['lng']:.5f})")
        #subtitle.setStyleSheet("background: transparent; border: none; font-size: 10pt; color: #cccccc;")
        text_layout = QHBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.addWidget(title)

        #text_layout.addWidget(subtitle)
        h_layout.addLayout(text_layout)
        h_layout.addStretch()

        delete_btn = HoverToggleButton(frame, "delete_btn")
        delete_icon = QIcon(":/icon_DeteleTraj.svg").pixmap(24, 24)
        white_delete = QPixmap(24, 24)
        white_delete.fill(Qt.transparent)
        painter_delete = QPainter(white_delete)
        painter_delete.setCompositionMode(QPainter.CompositionMode_Source)
        painter_delete.drawPixmap(0, 0, delete_icon)
        painter_delete.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter_delete.fillRect(white_delete.rect(), QColor("white"))
        painter_delete.end()
        delete_btn.setIcon(QIcon(white_delete))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setFocusPolicy(Qt.StrongFocus)
        delete_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
            }
            QToolButton:focus {
                border: 2px solid #009688;
                border-radius: 8px;
            }
        """)
        delete_btn.setCursor(Qt.PointingHandCursor)

        # …

        delete_btn.clicked.connect(
            lambda _, n=traj['nombre']: (
                QMessageBox.question(
                    self,
                    "Confirmar eliminación",
                    f"¿Eliminar trayectoria '{n}'?",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes
            ) and self.delete_map_preview(n)
        )
        h_layout.addWidget(delete_btn)

        rename_btn = HoverToggleButton(self, "rename_btn")
        rename_icon = QIcon(":/icon_RenameTraj.svg").pixmap(24, 24)
        white_rename = QPixmap(24, 24)
        white_rename.fill(Qt.transparent)
        painter_rename = QPainter(white_rename)
        painter_rename.setCompositionMode(QPainter.CompositionMode_Source)
        painter_rename.drawPixmap(0, 0, rename_icon)
        painter_rename.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter_rename.fillRect(white_rename.rect(), QColor("white"))
        painter_rename.end()
        rename_btn.setIcon(QIcon(white_rename))
        rename_btn.setFixedSize(24, 24)
        rename_btn.setFocusPolicy(Qt.StrongFocus)
        rename_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
            }
            QToolButton:focus {
                border: 2px solid #009688;
                border-radius: 8px;
            }
        """)
        rename_btn.setCursor(Qt.PointingHandCursor)

        # …

        rename_btn.clicked.connect(
            lambda _, old=traj['nombre'], lbl=title: self._show_rename_dialog(old, lbl)
        )
        h_layout.addWidget(rename_btn)

        # Toggle especializado
        toggle_btn = HoverToggleButton(frame, "toggle_btn")
        toggle_btn.setArrowType(Qt.DownArrow)
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #eeeeee;
            }
            QToolButton:checked {
                background-color: #606060;
                border-radius: 4px;
            }
            QToolButton:focus {
                border: 2px solid #009688;
                border-radius: 8px;
            }
        """)
        # Alternar flecha según estado
        toggle_btn.toggled.connect(lambda c: toggle_btn.setArrowType(Qt.UpArrow if c else Qt.DownArrow))
        h_layout.addWidget(toggle_btn)


        v_layout.addWidget(header)

        # Preview
        preview = QLabel()
        preview.setVisible(False)
        preview.setScaledContents(True)             
        preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        preview.setStyleSheet("background: transparent; border: none;")
        v_layout.addWidget(preview)

        # Mostrar/ocultar preview
        toggle_btn.toggled.connect(lambda checked, tr=traj: self._toggle_preview(checked, preview, tr))
        

        # Click en frame
        frame.mouseReleaseEvent = lambda event, t=traj['coords']: (
            setattr(self, 'selected_trajectory', t),
            frame.setProperty("selected", True),
            frame.style().unpolish(frame),
            frame.style().polish(frame),
            # Desmarcar otros frames
            [self.cards_layout.itemAt(i).widget().setProperty("selected", False) for i in range(self.cards_layout.count()) if self.cards_layout.itemAt(i).widget() != frame],
            [self.cards_layout.itemAt(i).widget().style().unpolish(self.cards_layout.itemAt(i).widget()) for i in range(self.cards_layout.count()) if self.cards_layout.itemAt(i).widget() != frame],
            [self.cards_layout.itemAt(i).widget().style().polish(self.cards_layout.itemAt(i).widget()) for i in range(self.cards_layout.count()) if self.cards_layout.itemAt(i).widget() != frame],
            # Habilitar botón de selección
            self.btn_select.setEnabled(True)
        )

        
        return frame, delete_btn, rename_btn, toggle_btn

    def _show_rename_dialog(self, old_name: str, title_label: QLabel):
        """Abre un QInputDialog para renombrar la trayectoria y actualiza el store."""
        new_name, ok = QInputDialog.getText(
            self,
            "Renombrar trayectoria",
            "Nuevo nombre:",
            QLineEdit.Normal,
            old_name
        )

        new_name = new_name.strip()
        if not ok or not new_name or new_name == old_name:
            return
        
        # Verificar si el nuevo nombre ya existe

        if not new_name:
            QMessageBox.warning(
            self,
            "Error",
            "El nombre no puede estar vacío.",
            QMessageBox.Ok
            )
            return

        # Cargar store
        if os.path.exists(DATA_STORE):
            with open(DATA_STORE, 'rb') as f:
                store = pickle.load(f)
        else:
            store = {}

        # Verificar si el nuevo nombre ya existe
        if new_name in store:
            QMessageBox.warning(
            self,
            "Error",
            f"Ya existe una trayectoria con el nombre '{new_name}'.",
            QMessageBox.Ok
            )
            return

        # Renombrar clave
        info = store.pop(old_name, None)
        if info is None:
            return
        store[new_name] = info

        # Guardar cambios
        with open(DATA_STORE, 'wb') as f:
            pickle.dump(store, f)

        # Refrescar UI
        title_label.setText(new_name)
    

    def select_trajectory(self):
        """
        Devuelve la trayectoria seleccionada.
        Si no hay ninguna seleccionada, retorna None.
        """
        if self.selected_trajectory:
            # Emitir señal de selección
            self.select_trajectory_signal.emit(self.selected_trajectory)
            # Limpiar la selección
            self.selected_trajectory = None
            # Emitir señal de aceptación
            self.accepted.emit()
        else:
            # Si no hay selección, no hacemos nada
            return None
        
    
    def delete_map_preview(self, nombre):
        """
        Elimina la trayectoria guardada bajo la clave 'nombre' en DATA_STORE.
        Si no existe, no hace nada.
        """
        # Si el archivo no existe, no hay nada que borrar
        if not os.path.exists(DATA_STORE):
            return

        # Cargar el store actual
        try:
            with open(DATA_STORE, 'rb') as f:
                store = pickle.load(f)
        except (EOFError, pickle.UnpicklingError):
            store = {}

        # Eliminar la entrada si existe
        if nombre in store:
            store.pop(nombre)
            # Guardar cambios
            with open(DATA_STORE, 'wb') as f:
                pickle.dump(store, f)

        self.refresh_trajectories()
            

    def _toggle_preview(self, checked, preview_label, traj):
        if checked:
            pix = QPixmap()
            pix.loadFromData(traj['map'])
            # Escalamos al ancho disponible manteniendo ratio
            w = preview_label.width()
            scaled = pix.scaledToWidth(w, Qt.SmoothTransformation)
            preview_label.setPixmap(scaled)
            # Ajustamos la altura del label a la del pixmap
            preview_label.setFixedHeight(scaled.height())
            preview_label.setVisible(True)
        else:
            preview_label.setVisible(False)
            # Opcional: limpiar la altura forzada
            preview_label.setFixedHeight(0)

    def _on_accept(self):
        """Handle OK button click"""
        self.accepted.emit()
    
    def _on_reject(self):
        """Handle Cancel button click"""
        self.rejected.emit()

    def refresh_trajectories(self):
        # 1) Limpiar todo
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

        # 2) Repoblar
        self.card_widgets = []
        self.trajectories = self.load_all_map_previews()

        prev_widget = None
        for traj in self.trajectories:
            frame, delete_btn, rename_btn, toggle_btn = self._create_card(traj)
            # 2.1) Hacerlos focusable
            for w in (frame, delete_btn, rename_btn, toggle_btn):
                w.setFocusPolicy(Qt.StrongFocus)

            self.card_widgets.append((frame, delete_btn, rename_btn, toggle_btn))
            self.cards_layout.addWidget(frame)

            # 2.2) Definir tab order dentro de la card
            self.setTabOrder(frame, delete_btn)
            self.setTabOrder(delete_btn, rename_btn)
            self.setTabOrder(rename_btn, toggle_btn)

            # 2.3) Enlazar la última de la tarjeta anterior con el frame de la siguiente
            if prev_widget:
                self.setTabOrder(prev_widget, frame)

            prev_widget = toggle_btn

        # 3) Después de la última tarjeta, enlazar toggle->btn_add->btn_select
        if prev_widget:
            self.setTabOrder(prev_widget, self.btn_add)
        self.setTabOrder(self.btn_add, self.btn_select)

        # 4) Establecer foco inicial en la primera tarjeta (si existe)
        if self.card_widgets:
            first_frame = self.card_widgets[0][0]
            first_frame.setFocus()

    def load_all_map_previews(self):
        """
        Lee todas las entradas guardadas en DATA_STORE.
        Retorna una lista de objetos con formato:
        { 'nombre': str, 'ptu': {'lat': float, 'lng': float}, 'map': bytes }
        """
        try:
            with open(DATA_STORE, 'rb') as f:
                store = pickle.load(f)
        except (FileNotFoundError, EOFError):
            return []

        result = []
        for nombre, info in store.items():
            result.append({
                'nombre': nombre,
                'map': info['map'],
                'coords': info['coords'],
            })
        return result
    
    def select_area(self):
        self.parent.home_tab.selectArea()
        self.rejected.emit()