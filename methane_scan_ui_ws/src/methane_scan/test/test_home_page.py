import pytest
from PyQt5.QtWidgets import QApplication
from methane_scan.views.pages.home_page import HomePage
import sys

@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

def test_home_page_signals(app):
    page = HomePage("dummy_key", None)
    # Simula la señal de selección de trayectoria
    called = {}
    def fake_slot():
        called['ok'] = True
    page.selectTrajectory = fake_slot
    if hasattr(page, 'select_trajectory_signal'):
        page.select_trajectory_signal.emit()
        assert called.get('ok')
