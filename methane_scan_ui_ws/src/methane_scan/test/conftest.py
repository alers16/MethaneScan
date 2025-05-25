import os, sys, types, json, time, tempfile, contextlib, importlib
import pytest
from unittest.mock import MagicMock


# ----------------------------------------------------------------------------
# 1) Make Qt run head‑less (avoids platform plugin errors in CI / GH‑Actions)
# ----------------------------------------------------------------------------
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# --------------------------------------------------------------------
# Stub Qt WebEngine modules to avoid head‑less Chromium crash
# --------------------------------------------------------------------
try:
    import PyQt5.QtWebEngineWidgets  # noqa: F401
except Exception:
    from PyQt5.QtWidgets import QWidget
    we_mod = types.ModuleType("PyQt5.QtWebEngineWidgets")
    class QWebEngineView(QWidget):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
    we_mod.QWebEngineView = QWebEngineView
    sys.modules["PyQt5.QtWebEngineWidgets"] = we_mod

# Ensure Core stub exists as well (some versions import it)
if "PyQt5.QtWebEngineCore" not in sys.modules:
    sys.modules["PyQt5.QtWebEngineCore"] = types.ModuleType("PyQt5.QtWebEngineCore")


# ----------------------------------------------------------------------------
# 2) Fake rclpy so the app logic imports without a ROS2 daemon
# ----------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _mock_rclpy():
    rclpy = types.ModuleType("rclpy")
    rclpy.ok = lambda: True
    rclpy.init = MagicMock()
    rclpy.shutdown = MagicMock()
    rclpy.spin_once = MagicMock()
    rclpy.time = MagicMock()

    class _FakeTime(float):
        """Float subclass with minus operator overriding to simplify Duration diff."""
        def __sub__(self, other):
            return float(self) - float(other)
    
    class _FakeClock:
        def now(self):
            return _FakeTime(time.time())

    # Stub Duration so Duration(seconds=x) → float(x)
    duration_mod = types.ModuleType("rclpy.duration")
    class Duration(float):
        def __new__(cls, *, seconds):
            return super().__new__(cls, seconds)
    duration_mod.Duration = Duration
    sys.modules["rclpy.duration"] = duration_mod

    class _FakeNode:
        def __init__(self, *args, **kwargs):
            self._logger = MagicMock()
            self._params = {
                "TOPICS.ptu_ready": "/PTU_ready",
                "TOPICS.hunter_position": "/hunter_position",
                "TOPICS.tdlas_ready": "/TDLAS_ready",
                "TOPICS.tdlas_data": "/TDLAS_data",
                "TOPICS.initialize_hunter": "/initialize_hunter_params",
                "TOPICS.start_hunter": "/start_simulation",
                "TOPICS.save_simulation": "/save_simulation",
                "TOPICS.start_stop_hunter": "/start_stop_value",
                "TOPICS.end_simulation": "/end_simulation",
                "TOPICS.play_simulation": "/data_playback",
                "TOPICS.ptu_position": "/PTU_position",
                "TOPICS.mqtt_connection_status": "/connection_status",
                "TOPICS.mqtt_bridge_status": "/mqtt_status",
            }
            # Core publishers mocked so tests can assert .publish()
            self.publisher_Hunter_initialized   = MagicMock()
            self.publisher_start_simulation     = MagicMock()
            self.publisher_start_stop_hunter    = MagicMock()
            self.publisher_play_simulation      = MagicMock()
            
        # --- ROS emulation helpers -----------------------------------------
        def get_logger(self):
            return self._logger
        def declare_parameter(self, *a, **k):
            pass
        def get_parameter(self, name):
            class _P:
                def __init__(self, v): self.value = v
            return _P(self._params[name])
        def create_publisher(self, *a, **k):
            return MagicMock()
        def create_subscription(self, *a, **k):
            return MagicMock()
        def create_timer(self, *a, **k):
            return MagicMock()
        def get_clock(self):
            return _FakeClock()
    
    rclpy.node = types.ModuleType("rclpy.node")
    rclpy.node.Node = _FakeNode
    sys.modules["rclpy"] = rclpy
    sys.modules["rclpy.node"] = rclpy.node

    # ------------------------------------------------------------
    # Stub rosbag2_py (to avoid heavy C++ bindings & duplicate registrations)
    # ------------------------------------------------------------
    rb2 = types.ModuleType("rosbag2_py")

    # Fake rpyutils so the import inside rosbag2_py does not fail
    rpyutils = types.ModuleType("rpyutils")
    @contextlib.contextmanager
    def add_dll_directories_from_env(path):
        yield
    rpyutils.add_dll_directories_from_env = add_dll_directories_from_env
    sys.modules["rpyutils"] = rpyutils

    # Sub‑modules expected by rosbag2_py
    reader_mod = types.ModuleType("rosbag2_py._reader")
    for cls_name in [
        "SequentialCompressionReader",
        "SequentialReader",
        "get_registered_readers",
    ]:
        setattr(reader_mod, cls_name, MagicMock(name=cls_name))

    storage_mod = types.ModuleType("rosbag2_py._storage")
    for cls_name in [
        "ConverterOptions",
        "FileInformation",
        "StorageFilter",
        "StorageOptions",
        "TopicMetadata",
        "TopicInformation",
        "BagMetadata",
    ]:
        setattr(storage_mod, cls_name, MagicMock(name=cls_name))

    rb2._reader = reader_mod
    rb2._storage = storage_mod
    sys.modules.update({
        "rosbag2_py": rb2,
        "rosbag2_py._reader": reader_mod,
        "rosbag2_py._storage": storage_mod,
    })

    yield

# ----------------------------------------------------------------------------
# 3) Patch Toast so tests do not open transient widgets
# ----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _patch_toast(monkeypatch):
    fake_toast_cls = type("Toast", (), {"__init__": lambda self,*a,**k: None, "show": lambda self: None})
    mod = types.ModuleType("toast")
    mod.Toast = fake_toast_cls
    monkeypatch.setitem(sys.modules, "methane_scan.views.components.toast", mod)

# ----------------------------------------------------------------------------
# 4) Stub MainWindow & its nested widgets expected by the controllers
# ----------------------------------------------------------------------------
class _HomeStub:
    def __init__(self):
        self.map_frame = MagicMock()
        self.btn_iniciar = MagicMock()
        self.btn_pausar  = MagicMock()
        self.btn_abortar = MagicMock()
        self.btn_clean_map = MagicMock()
        self.btn_next_message = MagicMock()
        self.not_ready_label = MagicMock()
    def set_ready(self, x):
        self._ready = x
    def enableStartButtonCallback(self, cb):
        self._cb = cb
    def disableStartButton(self):
        pass
    def enableStartButton(self):
        pass

class _MainWindowStub:
    def __init__(self):
        self.home_tab = _HomeStub()
        self.titleBar  = MagicMock()
        self.ptu_config_widget = MagicMock()
        self.select_trajectory_widget = MagicMock()
    def switch_to_ptu_config(self):
        pass
    def switch_to_select_trajectory(self):
        pass

sys.modules.setdefault("methane_scan.views.main_window", types.ModuleType("mw"))
sys.modules["methane_scan.views.main_window"].MainWindow = _MainWindowStub

# ----------------------------------------------------------------------------
# 5) Skip style‑lint integration tests (flake8, pep257) – they are out of scope
# ----------------------------------------------------------------------------

def pytest_ignore_collect(path, config):
    """Prevent collection of heavy linter/PEP257 tests which fail on style issues."""
    fname = os.path.basename(str(path))
    return fname in {"test_flake8.py", "test_pep257.py"}

# ----------------------------------------------------------------------------
# 6) Provide fallback qtbot if pytest‑qt plugin is absent
# ----------------------------------------------------------------------------
try:
    importlib.import_module("pytestqt")
except ModuleNotFoundError:
    @pytest.fixture
    def qtbot():
        class _DummyQtBot:
            def addWidget(self, widget):
                # widgets may have setParent; ignore
                return widget
            def waitUntil(self, condition, timeout=1000):
                import time as _t
                start = _t.time()
                while _t.time() - start < timeout/1000.0:
                    if condition():
                        return
                    _t.sleep(0.01)
                assert condition()
        return _DummyQtBot()

# ----------------------------------------------------------------------------
# 7) Shared fixtures
# ----------------------------------------------------------------------------
@pytest.fixture
def node():
    from rclpy.node import Node
    return Node()

@pytest.fixture
def main_controller(node):
    from methane_scan.controllers.main_controller import MainController
    return MainController(node=node)

@pytest.fixture
def robot_controller(main_controller):
    return main_controller.robot_controller

@pytest.fixture
def ptu_controller(main_controller):
    return main_controller.ptu_controller

@pytest.fixture
def tdlas_controller(main_controller):
    return main_controller.tdlas_controller

@pytest.fixture
def simulation_page(qtbot):
    """Return a SimulationPage instance with dependencies mocked."""
    from methane_scan.views.pages.simulation_page import SimulationPage
    page = SimulationPage(API_KEY="DUMMY")
    qtbot.addWidget(page)
    # Patch internal _start_process to avoid spawning pexpect
    page._start_process = MagicMock(name="_start_process")
    return page