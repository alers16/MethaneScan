import pytest
from PyQt5.QtWidgets import QApplication
from methane_scan.views.main_window import MainWindow
import sys

@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

@pytest.mark.parametrize("theme", ["dark", "light"])
def test_toggle_theme(app, theme):
    window = MainWindow()
    # Simula el toggle
    window.toggle_theme_action = type("obj", (), {"isChecked": lambda self: theme == "dark", "setText": lambda self, x: None})()
    window.toggle_theme()
    assert window.current_theme == theme

# Test de interacción de pestañas
def test_switch_tabs(app):
    window = MainWindow()
    window.switch_to_simulation_tab()
    assert window.tab_widget.currentWidget() == window.simulation_tab
    window.switch_to_home_tab()
    assert window.tab_widget.currentWidget() == window.home_tab
