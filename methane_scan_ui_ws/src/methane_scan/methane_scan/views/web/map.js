let map;
let drawingManager;
let lastUserOverlay = null;
let ptuMarker = null;
let hunterMarker = null;
let beams = [];
let hunter_path = [];
let trajectories = [];
let hunterLastPos = null;

let isDrawingEnabled = false;

function initMap() {
  // Obtener configuración desde Python inyectada
  const { lat, lng, zoom } = window.CONFIG;

  // Estilos: ocultar POIs y transporte
  const myStyles = [
    { featureType: "poi", stylers: [{ visibility: "off" }] },
    { featureType: "transit", stylers: [{ visibility: "off" }] },
  ];

  // Inicialización del mapa
  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat, lng },
    zoom,
    mapTypeId: google.maps.MapTypeId.SATELLITE,
    styles: myStyles,
    disableDefaultUI: false,
    mapTypeControl: false,
    rotateControl: false,
    streetViewControl: false,
    fullscreenControl: false,
  });

  map.setTilt(0);
  map.setHeading(0);

  // Configurar DrawingManager
  drawingManager = new google.maps.drawing.DrawingManager({
    drawingControl: false,
    drawingControlOptions: {
      position: google.maps.ControlPosition.TOP_CENTER,
      drawingModes: [
        google.maps.drawing.OverlayType.POLYLINE,
        google.maps.drawing.OverlayType.RECTANGLE,
        google.maps.drawing.OverlayType.POLYGON,
      ],
    },
    markerOptions: {
      icon: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
    },
    circleOptions: {
      fillColor: "#ffff00",
      fillOpacity: 0.5,
      strokeWeight: 1,
      clickable: true,
      editable: true,
    },
  });
  drawingManager.setMap(map);

  // Evento cuando termina de dibujar
  google.maps.event.addListener(
    drawingManager,
    "overlaycomplete",
    function (event) {
      if (lastUserOverlay) {
        lastUserOverlay.setMap(null);
        lastUserOverlay = null;
      }
      lastUserOverlay = event.overlay;
      lastUserOverlay.type = event.type;
      console.log("Overlay complete:", lastUserOverlay.type);
    }
  );
}

// Elimina la figura dibujada por el usuario
function clearUserOverlay() {
  if (lastUserOverlay) {
    lastUserOverlay.setMap(null);
    lastUserOverlay = null;
  }
}

// Habilita el DrawingManager
function enableDrawing() {
  if (!isDrawingEnabled) {
    drawingManager.setMap(map);
    drawingManager.setOptions({ drawingControl: true });
    isDrawingEnabled = true;
  }
}

// Deshabilita el DrawingManager
function disableDrawing() {
  if (isDrawingEnabled) {
    drawingManager.setMap(null);
    drawingManager.setOptions({ drawingControl: false });
    isDrawingEnabled = false;
  }
}

// Obtener esquinas de rectángulo
function getRectCorners() {
  const bounds = lastUserOverlay.getBounds();
  const sw = bounds.getSouthWest();
  const ne = bounds.getNorthEast();
  const nw = { latitude: ne.lat(), longitude: sw.lng() };
  const se = { latitude: sw.lat(), longitude: ne.lng() };
  return [
    { latitude: sw.lat(), longitude: sw.lng() },
    nw,
    { latitude: ne.lat(), longitude: ne.lng() },
    se,
    { latitude: sw.lat(), longitude: ne.lng() }
  ];
}

// Obtener datos de círculo
function getCircleCorners() {
  const center = lastUserOverlay.getCenter();
  const radius = lastUserOverlay.getRadius();
  return {
    center: { latitude: center.lat(), longitude: center.lng() },
    radius,
  };
}

// Obtener coordenadas de polígono
function getPolygonCorners() {
  const path = lastUserOverlay.getPath();
  const coords = [];
  for (let i = 0; i < path.getLength(); i++) {
    const latlng = path.getAt(i);
    coords.push({ latitude: latlng.lat(), longitude: latlng.lng() });
  }
  return coords;
}

// Obtener coordenadas de polilínea
function getPolylineCorners() {
  const path = lastUserOverlay.getPath();
  const coords = [];
  for (let i = 0; i < path.getLength(); i++) {
    const latlng = path.getAt(i);
    coords.push({ latitude: latlng.lat(), longitude: latlng.lng() });
  }
  return coords;
}

// Retorna esquinas según tipo de overlay
function getCorners() {
  if (!lastUserOverlay) return null;
  switch (lastUserOverlay.type) {
    case google.maps.drawing.OverlayType.RECTANGLE:
      return getRectCorners();
    case google.maps.drawing.OverlayType.CIRCLE:
      return getCircleCorners();
    case google.maps.drawing.OverlayType.POLYGON:
      return getPolygonCorners();
    case google.maps.drawing.OverlayType.POLYLINE:
      return getPolylineCorners();
    default:
      return null;
  }
}

// Dibuja una polilínea (beam) en el mapa
function drawBeam(coordList, color = "red") {
  const path = coordList.map((c) => ({ lat: c[0], lng: c[1] }));
  const beam = new google.maps.Polyline({
    path,
    strokeColor: color,
    strokeOpacity: 1,
    strokeWeight: 1,
  });
  beams.push(beam);
  beam.setMap(map);

  beam.addListener("click", () => {
    const idx = beams.indexOf(beam);
    if (window.bridge) window.bridge.onBeamClicked(idx, path[1]);
  });
}

// Dibuja una trayectoria “a mano” usando un array de [lat, lng] o {lat, lng}/{latitude, longitude}
function drawTrajectory(coords) {
  // Verifica que coords sea un array con al menos dos puntos
  if (!Array.isArray(coords) || coords.length < 2) return;

  // Construye el path en formato {lat, lng}
  const path = coords.map(pt => ({
    lat: pt.latitude !== undefined ? pt.latitude : pt.lat,
    lng: pt.longitude !== undefined ? pt.longitude : pt.lng
  }));

  // Crea y dibuja la polilínea
  const trajectory = new google.maps.Polyline({
    path,
    strokeColor: "black",
    strokeOpacity: 1.0,
    strokeWeight: 3,
    clickable: false,
    editable: false,
    geodesic: true
  });

  trajectory.setMap(map);

  // Guarda la trayectoria para poder borrarla luego
  trajectories.push(trajectory);

  return trajectory;
}

// Elimina todas las trayectorias manuales
function clearTrajectories() {
  trajectories.forEach(t => t.setMap(null));
  trajectories = [];
}

// Elimina marcador PTU
function deletePTUMarker() {
  if (ptuMarker) {
    ptuMarker.setMap(null);
    ptuMarker = null;
  }
}

// Elimina marcador Hunter
function deleteHunterMarker() {
  if (hunterMarker) {
    hunterMarker.setMap(null);
    hunterMarker = null;
  }
}

// Limpia todos los beams
function clearBeams() {
  beams.forEach((b) => b.setMap(null));
  beams = [];
}

function clearHunterPath() {
  hunter_path.forEach((b) => b.setMap(null));
  hunter_path = [];
  hunterLastPos = null;
}

// Dibuja marcador PTU
function drawPTUMarker(lat, lng) {
  const marker = new google.maps.Marker({
    position: { lat, lng },
    map,
    title: "PTU",
    icon: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
  });
  ptuMarker = marker;
}

// Dibuja marcador Hunter
function drawHunterMarker(lat, lng, isRunning) {
  // Construye el path del beam usando lat/lng actuales y los previos
  if(isRunning == 1){
    const path = [
      { lat, lng },
      hunterLastPos
        ? { lat: hunterLastPos[0], lng: hunterLastPos[1] }
        : { lat, lng },
    ];
  
    const beam = new google.maps.Polyline({
      path,
      strokeColor: "black",
      strokeOpacity: 1,
      strokeWeight: 2,
    });
  
    hunter_path.push(beam);
    beam.setMap(map);
  }

  const marker = new google.maps.Marker({
    position: { lat, lng },
    map,
    title: "Hunter",
    icon: "http://maps.google.com/mapfiles/ms/icons/red-dot.png",
  });
  hunterLastPos = [lat, lng];
  hunterMarker = marker;
}

function centerMap(lat, lng) {
  map.setCenter({ lat, lng });
  map.setZoom(20);
}
