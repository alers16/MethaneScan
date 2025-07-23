import os
from PyQt5.QtCore import QUrl, QObject, pyqtSignal, pyqtSlot, QVariant
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel

class MapBridge(QObject):
    beamClicked = pyqtSignal(int, dict)

    @pyqtSlot(int, QVariant)
    def onBeamClicked(self, index, position):
        data = position
        if isinstance(data, QVariant):
            try:
                data = data.toPyObject()
            except Exception:
                data = dict(data)
        self.beamClicked.emit(index, data)

class MyWebEnginePage(QWebEnginePage):
    def __init__(self, signal : pyqtSignal , parent=None):
        self.signal = signal
        super().__init__(parent)
        self.last_message = None
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        self.last_message = (f"JS Console - Level: {level}, Message: {message}, Line: {lineNumber}, Source: {sourceID}")
        self.signal.emit(self.last_message)
    
class SatelliteMap(QWebEngineView):
    javaScriptConsoleMessage = pyqtSignal(str)
    def __init__(self, lat=36.71579, lng=-4.478165, zoom=19, api_key="YOUR_API_KEY", parent=None):
        super().__init__(parent)
        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessRemoteUrls, True
        )

        self.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls, True
        )
        self.setPage(MyWebEnginePage(parent=self, signal=self.javaScriptConsoleMessage))
        

        # instalar QWebChannel
        self.bridge = MapBridge()
        channel = QWebChannel(self.page())
        channel.registerObject('bridge', self.bridge)
        self.page().setWebChannel(channel)
        
        # Control de carga
        self._isLoaded = False
        self._pendingBeams = []  
        self._pendingMarkers = []
        
        # Conectamos la señal que indica que la página ha terminado de cargar
        self.loadFinished.connect(self._handleLoadFinished)

        self.PTU_coordinates = None
        self.robot_coordinates = None
        
        # 1) Ruta absoluta de este archivo (map_view.py)
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 2) Sube dos niveles: de components → views → methane_scan
        project_pkg_dir = os.path.abspath(os.path.join(current_dir, '..'))

        # 3) Apunta al folder web dentro de methane_scan
        base_dir = os.path.join(project_pkg_dir, 'web')
        html_path = os.path.join(base_dir, 'index.html')

        with open(html_path, 'r', encoding='utf-8') as f:
            html = (f.read()
                    .replace('__API_KEY__', api_key)
                    .replace('__LAT__', str(lat))
                    .replace('__LNG__', str(lng))
                    .replace('__ZOOM__', str(zoom))
                   )

        base_url = QUrl.fromLocalFile(base_dir + os.sep)
        self.setHtml(html, base_url)

    def _handleLoadFinished(self, ok):
        """Se llama cuando el HTML ha cargado."""
        self._isLoaded = ok
        if not ok:
            print("Error: la página no se cargó correctamente.")
            return
        # Si había beams pendientes, dibujarlos ahora
        for coords in self._pendingBeams:
            self._execDrawBeam(coords)
        self._pendingBeams.clear()

        # Si había markers pendientes, dibujarlos ahora
        for lat, lng in self._pendingMarkers:
            self.drawPTUMarker(lat, lng)
        self._pendingMarkers.clear()

    def getCorners(self, callback):
        """Invoca getCorners() en JS y llama a 'callback' con la lista de esquinas."""
        code = "getCorners();"
        self.page().runJavaScript(code, callback)
        

    def drawBeam(self, coords, color):
        """
        coords: lista de tuplas (lat, lng), ej: [(lat1, lng1), (lat2, lng2), ...]
        """
        if not self._isLoaded:
            # Todavía no ha cargado, encolamos
            self._pendingBeams.append(coords)
        else:
            # Ya está cargado, dibujamos directamente
            self._execDrawBeam(coords, color)
    
    def drawTrajectory(self, coords, opacity=1.0):
        """
        coords: lista de tuplas (lat, lng), ej: [(lat1, lng1), (lat2, lng2), ...]
        """
        if not self._isLoaded:
            # Todavía no ha cargado, encolamos
            self._pendingBeams.append(coords)
        else:
            # Ya está cargado, dibujamos directamente
            command = f"drawTrajectory({coords});"
            self.page().runJavaScript(command)
    
    def drawPTUMarker(self, lat, lng):
        """Dibuja un marcador en la posición especificada."""
        if not self._isLoaded:
            # Todavía no ha cargado, encolamos
            self._pendingMarkers.append((lat, lng))
        else:
          if self.PTU_coordinates:
            self.deletePTUMarker()
          code = f"drawPTUMarker({lat}, {lng});"
          self.page().runJavaScript(code)
          self.PTU_coordinates = (lat, lng)

    def drawRobotMarker(self, lat, lng, is_running):
        """Dibuja un marcador en la posición especificada."""
        if not self._isLoaded:
            # Todavía no ha cargado, encolamos
            self._pendingMarkers.append((lat, lng))
        else:
          if self.robot_coordinates:
            self.deleteHunterMarker()
          code = f"drawHunterMarker({lat}, {lng}, {1 if is_running else 0});"
          self.page().runJavaScript(code)
          self.robot_coordinates = (lat, lng)
      
    def clearSelection(self):
        """Elimina la figura dibujada por el usuario (si existe)"""
        code = "clearUserOverlay(); clearBeams(); clearTrajectories();"
        self.page().runJavaScript(code)
      
    def clearBeams(self):
        """Elimina todos los beams dibujados (si existen)"""
        code = "clearBeams(); clearHunterPath(); "
        self.page().runJavaScript(code)

    def _execDrawBeam(self, coords, color):
        # Llama a la función JS drawBeam(coordList)
        js_array = str([[c[0], c[1]] for c in coords])  # [[lat, lng], [lat, lng], ...]
        code = f'drawBeam({js_array}, "{color}");'
        self.page().runJavaScript(code)

    def enableDrawing(self):
        """Habilita la DrawingManager."""
        code = "enableDrawing();"
        self.page().runJavaScript(code)
      
    def disableDrawing(self):
        """Deshabilita la DrawingManager."""
        code = "disableDrawing();"
        self.page().runJavaScript(code)
    
    def clearUserOverlay(self):
        """Elimina la figura dibujada por el usuario (si existe)"""
        self.page().runJavaScript("clearUserOverlay();")

    def deletePTUMarker(self):
        """Elimina el marcador PTU (si existe)"""
        self.page().runJavaScript("deletePTUMarker();")
    
    def deleteHunterMarker(self):
        """Elimina el marcador Hunter (si existe)"""
        self.page().runJavaScript("deleteHunterMarker();")

    def centerMap(self, lat, lng):
        """Centra el mapa en la posición especificada."""
        code = f"centerMap({lat}, {lng});"
        self.page().runJavaScript(code)