from PyQt5.QtGui import QDoubleValidator

class PositiveDoubleValidator(QDoubleValidator):
    def __init__(self, parent=None):
        # Set a wide range and 6 decimals precision
        super().__init__(0.0, 1e10, 6, parent)
        self.setNotation(QDoubleValidator.StandardNotation)
    
    def validate(self, input_str, pos):
        state, input_str, pos = super().validate(input_str, pos)
        try:
            value = float(input_str)
        except ValueError:
            # If conversion fails, delegate to the base validator state
            return state, input_str, pos
        # Enforce strictly greater than 0
        if value <= 0:
            return QDoubleValidator.Invalid, input_str, pos
        return state, input_str, pos
