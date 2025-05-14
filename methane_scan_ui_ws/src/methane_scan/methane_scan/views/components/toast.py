from PyQt5.QtWidgets import QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore    import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve

class Toast(QLabel):
    INFO    = 'info'
    WARNING = 'warning'
    ERROR   = 'error'

    STYLE_TEMPLATES = {
        INFO:    {'icon': 'ℹ️', 'border': '#2196F3'},
        WARNING: {'icon': '⚠️', 'border': '#FBC02D'},
        ERROR:   {'icon': '❌', 'border': '#D32F2F'},
    }

    _active_toasts = []
    _spacing       = 10
    _animations    = []  # guardamos refs a animaciones para que no mueran

    def __init__(self, msg: str, parent, toast_type: str = INFO, duration: int = 3000):
        super().__init__(parent)
        self.duration    = duration
        self._fading_out = False

        # — Estilo básico
        style      = self.STYLE_TEMPLATES.get(toast_type, self.STYLE_TEMPLATES[self.INFO])
        icon       = style['icon']
        border_col = style['border']
        self.setText(f"{icon}   {msg}")
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setStyleSheet(f"""
            padding: 10px 14px;
            border-left: 5px solid {border_col};
            border-radius: 1px;
            font-weight: bold;
        """)

        # — Sombra (único GraphicEffect)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        # — Ventana sin marco y transparente fuera del CSS
        flags = Qt.ToolTip | Qt.FramelessWindowHint
        self.setWindowFlags(flags)

        self.adjustSize()
        # Empieza invisible para poder animar windowOpacity
        self.setWindowOpacity(0)

    def show(self):
        # 1) Registro y reposición
        Toast._active_toasts.append(self)
        QTimer.singleShot(0, lambda: self._reposition_toasts(animated=True, animate_new=False))

        # 2) Muestro y arranco fade-in
        super().show()
        fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        fade_in.setDuration(300)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        fade_in.setEasingCurve(QEasingCurve.OutCubic)
        fade_in.start()
        Toast._animations.append(fade_in)

        # 3) Auto‐cierre
        QTimer.singleShot(self.duration, self.close)

    def close(self):
        if not self._fading_out:
            self._fading_out = True
            fade_out = QPropertyAnimation(self, b"windowOpacity", self)
            fade_out.setDuration(300)
            fade_out.setStartValue(self.windowOpacity())
            fade_out.setEndValue(0)
            fade_out.setEasingCurve(QEasingCurve.InCubic)
            fade_out.finished.connect(super().close)
            fade_out.start()
            Toast._animations.append(fade_out)
        else:
            super().close()

    def closeEvent(self, event):
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)
            QTimer.singleShot(0, lambda: self._reposition_toasts(animated=True, animate_new=True))
        super().closeEvent(event)

    @classmethod
    def _reposition_toasts(cls, animated: bool, animate_new: bool = True):
        if not cls._active_toasts:
            return
        cls._animations.clear()

        parent   = cls._active_toasts[0].parentWidget()
        rect     = parent.rect()
        mid_x    = rect.width() // 2
        bottom_y = rect.height()
        global_mid = parent.mapToGlobal(QPoint(mid_x, bottom_y))

        max_w   = max(t.width() for t in cls._active_toasts)
        fixed_x = global_mid.x() - max_w // 2
        base_y  = global_mid.y() - cls._active_toasts[-1].height() - 20

        for idx, toast in enumerate(reversed(cls._active_toasts)):
            tx = fixed_x
            ty = base_y - idx * (toast.height() + cls._spacing)
            if animated and (animate_new or idx > 0):
                anim = QPropertyAnimation(toast, b"pos", toast)
                anim.setDuration(300)
                anim.setEasingCurve(QEasingCurve.OutCubic)
                anim.setStartValue(toast.pos())
                anim.setEndValue(QPoint(tx, ty))
                anim.start()
                cls._animations.append(anim)
            else:
                toast.move(tx, ty)
