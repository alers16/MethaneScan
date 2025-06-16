# 🚀 MethaneScan: Plataforma de Monitorización Remota de Metano

![ROS2](https://img.shields.io/badge/ROS2-Humble-blue)
![PyQt](https://img.shields.io/badge/PyQt5-Interface-green)
![MQTT](https://img.shields.io/badge/MQTT-Integration-purple)

## 📌 Descripción del Proyecto

MethaneScan es una aplicación integral diseñada para la detección, monitorización y análisis remoto de emisiones de metano mediante la tecnología TDLAS (Tunable Diode Laser Absorption Spectroscopy). Construida sobre ROS 2 y PyQt, esta plataforma automatiza completamente el proceso desde la configuración inicial hasta la visualización y análisis de datos en tiempo real.

## 🌟 Características Clave

- 🔧 **Automatización completa** del flujo de trabajo, simplificando el proceso operativo.
- 🛰️ **Visualización satelital interactiva** para seguimiento preciso del robot y mediciones.
- 📊 **Análisis en tiempo real** con sincronización y trazabilidad de los datos.
- 🖥️ **Interfaz intuitiva y amigable** diseñada para reducir la carga operativa en campo.
- 🌐 **Integración de ROS2 y MQTT**, ampliando capacidades hacia sistemas IoT externos.
- 🚦 **Nodo simulador personalizado**, permitiendo validación previa al despliegue en terreno.

## 🛠️ Tecnologías Utilizadas

- **Lenguaje Principal:** Python 🐍
- **Framework Robótico:** ROS 2 Humble 🤖
- **Interfaz Gráfica:** PyQt5 🎨
- **Comunicación IoT:** MQTT 📡
- **Base de datos y almacenamiento:** ROSbag, JSON, Pickle 🗃️

## 📁 Estructura del Repositorio

```
MethaneScan/
├── controllers/       # Lógica de control (PTU, Robot, TDLAS)
├── views/             # Componentes gráficos de PyQt
├── config/            # Configuración del sistema
├── simulations/       # Nodo simulador
├── data/              # Datos y trayectorias
├── docs/              # Documentación técnica
└── README.md          # Información del proyecto
```

## ⚙️ Instalación y Configuración

### Requisitos Previos

ROS2 Humble incluye muchas bibliotecas básicas necesarias, pero deberás instalar otras dependencias específicas del proyecto usando un archivo `requirements.txt`. A continuación se listan los requisitos esenciales:
- ROS2 Humble
- Python 3.8+
- PyQt5

### Instalación

```bash
git clone https://github.com/tu-usuario/MethaneScan.git
cd MethaneScan
pip install -r requirements.txt

# Asegúrate de que todas las dependencias adicionales estén correctamente especificadas en el archivo requirements.txt
```

### Ejecución

1. Construir workspace y entorno:
```bash
cd methane_scan_ui_ws
colcon build
source install/setup.bash
```

2. Iniciar el sistema:
```bash
ros2 launch methane_scan launch.py
```

## 🖥️ Interfaz de Usuario

La interfaz principal está dividida en:
- 🔖 **Tarjetas de dispositivos:** Monitorizan el estado operativo.
- 🌍 **Mapa interactivo:** Muestra posiciones, trayectorias y áreas de medición.
- 🎛️ **Panel de control:** Permite iniciar, pausar y abortar experimentos.

## 🔮 Próximas Mejoras

- Validación completa con hardware real.
- Optimización de rendimiento mediante técnicas avanzadas de procesamiento.
- Análisis predictivo usando machine learning.
- Gestión multiusuario con control remoto seguro.

## 🤝 Contribuciones

Cualquier mejora o sugerencia es bienvenida. Para contribuir, realiza un fork del proyecto y envía un pull request o abre una issue para discutir mejoras.

## 📃 Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.


¡Gracias por visitar MethaneScan! 🌱✨
