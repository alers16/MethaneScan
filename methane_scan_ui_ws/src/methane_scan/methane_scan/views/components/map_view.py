import os
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

class MyWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_message = None
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        self.last_message = (f"JS Console - Level: {level}, Message: {message}, Line: {lineNumber}, Source: {sourceID}")
        print(f"JS Console - Level: {level}, Message: {message}, Line: {lineNumber}, Source: {sourceID}")
    
class SatelliteMap(QWebEngineView):
    def __init__(self, lat=36.71579, lng=-4.478165, zoom=19, api_key="YOUR_API_KEY", parent=None):
        super().__init__(parent)

        self.setPage(MyWebEnginePage(self))
        
        # Control de carga
        self._isLoaded = False
        self._pendingBeams = []  
        
        # Conectamos la señal que indica que la página ha terminado de cargar
        self.loadFinished.connect(self._handleLoadFinished)
        
        # HTML con librería 'drawing' + ocultar POIs/transit
        html = f"""
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8" />
            <title>Mapa Satelital con Rectángulo</title>
            <style>
              html, body, #map {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
              }}
            </style>
            <!-- Google Maps + librería drawing -->
            <script src="https://maps.googleapis.com/maps/api/js?key={api_key}&libraries=drawing"></script>
            <script>
              let map;
              let drawingManager;
              let lastUserOverlay = null;

              let isDrawingEnabled = false;
              
              function initMap() {{
                const myStyles = [
                  {{
                    featureType: "poi",
                    stylers: [{{ visibility: "off" }}]
                  }},
                  {{
                    featureType: "transit",
                    stylers: [{{ visibility: "off" }}]
                  }},
                  
                ];

                map = new google.maps.Map(document.getElementById('map'), {{
                  center: {{ lat: {lat}, lng: {lng} }},
                  zoom: {zoom},
                  mapTypeId: google.maps.MapTypeId.SATELLITE,
                  styles: myStyles,
                  disableDefaultUI: false, 
                  mapTypeControl: false,
                  rotateControl: false,
                  streetViewControl: false,
                  fullscreenControl: false
                }});

                map.setTilt(0);
                map.setHeading(0);

                drawingManager = new google.maps.drawing.DrawingManager({{
                  drawingControl: false,
                  drawingControlOptions: {{
                    position: google.maps.ControlPosition.TOP_CENTER,
                    drawingModes: [
                      google.maps.drawing.OverlayType.MARKER,
                      google.maps.drawing.OverlayType.POLYLINE,
                      google.maps.drawing.OverlayType.RECTANGLE,
                      google.maps.drawing.OverlayType.CIRCLE,
                      google.maps.drawing.OverlayType.POLYGON
                    ]
                  }},
                  markerOptions: {{
                    icon: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"
                  }},
                  circleOptions: {{
                    fillColor: "#ffff00",
                    fillOpacity: 0.5,
                    strokeWeight: 1,
                    clickable: true,
                    editable: true
                  }}
                }});
                drawingManager.setMap(map);

                // overlaycomplete: cuando se termina de dibujar algo
                google.maps.event.addListener(drawingManager, 'overlaycomplete', function(event) {{
                  
                  // Eliminar la figura anterior si existe
                  if (lastUserOverlay) {{
                    lastUserOverlay.setMap(null);
                    lastUserOverlay = null;
                  }}
                  // Guardar la nueva figura
                  lastUserOverlay = event.overlay;
                  lastUserOverlay.type = event.type;
                  console.log(lastUserOverlay.type);
                  
                }});
              }}

              // Eliminar la figura dibujada por el usuario
              function clearUserOverlay() {{
                if (lastUserOverlay) {{
                  lastUserOverlay.setMap(null);
                  lastUserOverlay = null;
                }}
              }}

              // Función para habilitar la DrawingManager
              function enableDrawing() {{
                if (!isDrawingEnabled) {{
                  drawingManager.setMap(map);
                  drawingManager.setOptions({{ drawingControl: true }});
                  isDrawingEnabled = true;
                }}
              }}


              // Función para deshabilitar la DrawingManager
              function disableDrawing() {{
                if (isDrawingEnabled) {{
                  drawingManager.setMap(null);
                  drawingManager.setOptions({{ drawingControl: false }});
                  isDrawingEnabled = false;
                }}
              }}

              // Retorna las 4 esquinas del último rectángulo
              function getRectCorners() {{
                const bounds = lastUserOverlay.getBounds();
                const sw = bounds.getSouthWest();
                const ne = bounds.getNorthEast();
                const nw = {{ lat: ne.lat(), lng: sw.lng() }};
                const se = {{ lat: sw.lat(), lng: ne.lng() }};
                return [
                  {{ lat: sw.lat(), lng: sw.lng() }},
                  nw,
                  {{ lat: ne.lat(), lng: ne.lng() }},
                  se
                ];
              }}

              // Retorna las 4 esquinas del último círculo
              function getCircleCorners() {{
                const center = lastUserOverlay.getCenter();
                const radius = lastUserOverlay.getRadius();
                return {{ center: {{ lat: center.lat(), lng: center.lng() }}, radius: radius }};
              }}

              // Retorna las esquinas de un polígono
              function getPolygonCorners() {{
                let path = lastUserOverlay.getPath();
                let coords = [];
                for (let i = 0; i < path.getLength(); i++) {{
                  let latlng = path.getAt(i);
                  coords.push({{ lat: latlng.lat(), lng: latlng.lng() }});
                }}
                return coords;  
              }}

              // Retorna las esquinas de una polilínea
              function getPolylineCorners() {{
                let path = lastUserOverlay.getPath();
                let coords = [];
                for (let i = 0; i < path.getLength(); i++) {{
                  let latlng = path.getAt(i);
                  coords.push({{ lat: latlng.lat(), lng: latlng.lng() }});
                }}
                return coords;
              }}

              function getCorners() {{
                if(!lastUserOverlay) {{
                  return null;
                }}
                if(lastUserOverlay.type === google.maps.drawing.OverlayType.RECTANGLE) {{
                  return getRectCorners();
                }} else if(lastUserOverlay.type === google.maps.drawing.OverlayType.CIRCLE) {{
                  return getCircleCorners();
                }} else if(lastUserOverlay.type === google.maps.drawing.OverlayType.POLYGON) {{
                  return getPolygonCorners();
                }} else if(lastUserOverlay.type === google.maps.drawing.OverlayType.POLYLINE) {{
                  return getPolylineCorners();
                }}

                return null;
              }}

              // Dibuja una polilínea "haz" en color rojo
              function drawBeam(coordList) {{
                let path = coordList.map(function(c) {{
                  return {{ lat: c[0], lng: c[1] }};
                }});
                let beam = new google.maps.Polyline({{
                  path: path,
                  strokeColor: "red",
                  strokeOpacity: 0.7,
                  strokeWeight: 2
                }});
                beam.setMap(map);
              }}

              function drawPTUMarker(lat, lng) {{
                var marker = new google.maps.Marker({{
                  position: {{ lat: lat, lng: lng }},
                  map: map,
                  title: "PTU",
                  // Opcional: Puedes definir un icono personalizado
                  icon: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"
                }});
              }}
            </script>
          </head>
          <body onload="initMap()">
            <div id="map"></div>
          </body>
        </html>
        """
        self.setHtml(html)

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

    def getCorners(self, callback):
        """Invoca getCorners() en JS y llama a 'callback' con la lista de esquinas."""
        code = "getCorners();"
        self.page().runJavaScript(code, callback)

    def drawBeam(self, coords):
        """
        coords: lista de tuplas (lat, lng), ej: [(lat1, lng1), (lat2, lng2), ...]
        """
        if not self._isLoaded:
            # Todavía no ha cargado, encolamos
            self._pendingBeams.append(coords)
        else:
            # Ya está cargado, dibujamos directamente
            self._execDrawBeam(coords)
    
    def drawPTUMarker(self, lat, lng):
        """Dibuja un marcador en la posición especificada."""
        code = f"drawPTUMarker({lat}, {lng});"
        self.page().runJavaScript(code)

    def _execDrawBeam(self, coords):
        # Llama a la función JS drawBeam(coordList)
        js_array = str([[c[0], c[1]] for c in coords])  # [[lat, lng], [lat, lng], ...]
        code = f"drawBeam({js_array});"
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
