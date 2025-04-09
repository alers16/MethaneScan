import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
import json
import math
import random
import time

class PTUReadyPublisher(Node):
    def __init__(self):
        super().__init__('ptu_ready_publisher')
        # Creamos el publisher para el tópico /PTU_ready
        self.publisher_ = self.create_publisher(Bool, '/PTU_ready', 10)
        # Timer para publicar a 1 Hz (cada segundo)
        self.timer = self.create_timer(10.0, self.publish_status)

        self.publisher_hunter = self.create_publisher(String, '/hunter_position', 10)
        self.timer_hunter = self.create_timer(10.0, self.publish_hunter)

        self.publisher_TDLAS_ready = self.create_publisher(Bool, '/TDLAS_ready', 10)
        self.timer_TDLAS = self.create_timer(5.0, self.publish_TDLAS_status)

        self.publisher_TDLAS_data = self.create_publisher(String, '/TDLAS_data', 10)

        self.subscriber_start = self.create_subscription(String, '/start_simulation', 
                                                         self.start_simulation, 10)
        
        self.publisher_end_simulation = self.create_publisher(Bool, '/end_simulation', 10)
        
        # Flag to track if cleanup has been performed
        self._cleanup_done = False

        self._hunter_position_sent = False
        

    def start_simulation(self, msg):
        """
        Inicia la simulación con una lista de posiciones, haciendo que el robot se mueva
        gradualmente a lo largo de la trayectoria completa.
        positions: lista de diccionarios, por ejemplo:
           [{"latitude": 0.0, "longitude": 0.0},
            {"latitude": 5.0, "longitude": 0.0},
            {"latitude": 5.0, "longitude": 5.0},
            {"latitude": 0.0, "longitude": 5.0},
            {"latitude": 0.0, "longitude": 0.0}]
        """
        try:
            data = json.loads(msg.data)
            positions = data['path']
            speed = data['speed']
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Error al decodificar el JSON: {str(e)}")
            return
        
        if not positions or len(positions) < 2:
            self.get_logger().error("Se requieren al menos 2 posiciones para la simulación.")
            return

        self.get_logger().info(f"Recibida lista de posiciones: {positions}")
        self.hunter_positions = positions
        self.current_index = 0          # Índice del punto de inicio actual
        self.current_target_index = 1   # Índice del siguiente destino
        self.interp_progress = 0.0      # Progreso de interpolación (0.0 a 1.0)

        # Definir velocidad (unidades por segundo)
        self.speed = speed # Modifica este valor según se requiera

        # Calcular la duración del primer segmento en función de la distancia y la velocidad
        start_pos = self.hunter_positions[self.current_index]
        end_pos = self.hunter_positions[self.current_target_index]
        try:
            lat_start = float(start_pos['latitude'])
            lng_start = float(start_pos['longitude'])
            lat_end = float(end_pos['latitude'])
            lng_end = float(end_pos['longitude'])
        except (KeyError, ValueError) as e:
            self.get_logger().error(f"Error al obtener coordenadas: {str(e)}")
            return

        # Calcular distancia Euclidiana
        distance = math.hypot(lat_end - lat_start, lng_end - lng_start)
        self.segment_duration = distance / self.speed if self.speed > 0 else 1.0
        if self.segment_duration <= 0:
            self.segment_duration = 0.1

        # Si ya había un timer, lo detenemos
        if self.timer is not None:
            self.timer.cancel()
        # Creamos un timer con intervalo de 0.1 segundos para una interpolación suave
        self.timer = self.create_timer(0.1, self.publish_next_position)

    def publish_next_position(self):
        # Revisar si existe un siguiente punto destino
        if self.current_target_index < len(self.hunter_positions):
            start_pos = self.hunter_positions[self.current_index]
            end_pos = self.hunter_positions[self.current_target_index]
            
            # Se asume un tick de 0.1 segundos
            dt = 0.1
            self.interp_progress += dt / self.segment_duration
            t = self.interp_progress
            if t > 1.0:
                t = 1.0

            try:
                lat_start = float(start_pos['latitude'])
                lng_start = float(start_pos['longitude'])
                lat_end = float(end_pos['latitude'])
                lng_end = float(end_pos['longitude'])
            except (KeyError, ValueError) as e:
                self.get_logger().error(f"Error al obtener coordenadas: {str(e)}")
                self.timer.cancel()
                return

            # Interpolar entre la posición de inicio y destino
            lat = (1 - t) * lat_start + t * lat_end
            lng = (1 - t) * lng_start + t * lng_end

            msg = String()
            msg.data = json.dumps({"lat": lat, "lng": lng})
            self.publisher_hunter.publish(msg)
            self.get_logger().info(f'Posición interpolada: {msg.data}')

            msg_TDLAS =  String()
            probability = random.randint(0, 10)
            current_time = time.time()
            sec = int(current_time)
            nanosec = int((current_time - sec) * 1e9)
            tdlas_dict = {
                'header': {
                    'stamp': {
                        'sec': sec,
                        'nanosec': nanosec
                    },
                    'frame_id': 2
                },
                'average_ppmxm': random.randint(0, 100),
                'average_reflection_strength':  random.randint(0, 100),
                'average_absorption_strength': random.randint(0, 100),
                'ppmxm': [],  # Si es un array
                'reflection_strength': [],
                'absorption_strength': []
            }
            if probability < 7:
                tdlas_dict['average_ppmxm'] = random.randint(0, 20)
                msg_TDLAS.data = json.dumps(tdlas_dict)
            else:
                tdlas_dict['average_ppmxm'] = random.randint(76, 150)
                msg_TDLAS.data = json.dumps(tdlas_dict)
                
            self.publisher_TDLAS_data.publish(msg_TDLAS)
            self.get_logger().info(f'Publicado /TDLAS_data: {msg_TDLAS.data}')
            
            # Si la interpolación completó el segmento, se pasa al siguiente
            if self.interp_progress >= 1.0:
                self.current_index = self.current_target_index
                self.current_target_index += 1
                self.interp_progress = 0.0
                # Calcular duración del siguiente segmento si existe
                if self.current_target_index < len(self.hunter_positions):
                    start_pos = self.hunter_positions[self.current_index]
                    end_pos = self.hunter_positions[self.current_target_index]
                    try:
                        lat_start = float(start_pos['latitude'])
                        lng_start = float(start_pos['longitude'])
                        lat_end = float(end_pos['latitude'])
                        lng_end = float(end_pos['longitude'])
                    except (KeyError, ValueError) as e:
                        self.get_logger().error(f"Error al obtener coordenadas: {str(e)}")
                        self.timer.cancel()
                        return
                    distance = math.hypot(lat_end - lat_start, lng_end - lng_start)
                    self.segment_duration = distance / self.speed if self.speed > 0 else 1.0
                    if self.segment_duration <= 0:
                        self.segment_duration = 0.1
        else:
            self.get_logger().info("Simulación completada")
            msg_end = Bool()
            msg_end.data = True
            self.publisher_end_simulation.publish(msg_end)
            self.timer.cancel()
            self.timer = None

    def publish_status(self):
        msg = Bool()
        # Aquí defines el valor booleano que quieres publicar
        msg.data = True  # Puedes cambiarlo a False según tus necesidades
        self.publisher_.publish(msg)
        self.get_logger().info(f'Publicado /PTU_ready: {msg.data}')

    def publish_TDLAS_status(self):
        msg = Bool()
        msg.data = True 
        self.publisher_TDLAS_ready.publish(msg)
        self.get_logger().info(f'Publicado /TDLAS_ready: {msg.data}')

    def publish_hunter(self):
        msg = String()
        data = {"lat": 36.71593, "lng": -4.478058}
        msg.data = json.dumps(data)
        if not self._hunter_position_sent:
            self.publisher_hunter.publish(msg)
            self._hunter_position_sent = True
            self.get_logger().info(f'Publicado /hunter_position: {msg.data}')
    
    def cleanup(self):
        """Safely clean up node resources"""
        if self._cleanup_done:
            self.get_logger().debug('Cleanup already performed, skipping')
            return

        try:
            # Cancel timers first
            if hasattr(self, 'timer') and self.timer:
                self.get_logger().debug('Canceling status timer')
                self.timer.cancel()
                self.timer = None
                
            if hasattr(self, 'timer_hunter') and self.timer_hunter:
                self.get_logger().debug('Canceling hunter timer')
                self.timer_hunter.cancel()
                self.timer_hunter = None
                
            # Mark cleanup as done
            self._cleanup_done = True
            self.get_logger().info('Node resources cleaned up successfully')
        except Exception as e:
            self.get_logger().error(f'Error during cleanup: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = PTUReadyPublisher()
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node:
            node.get_logger().info("Interrupción por teclado, cerrando nodo...")
    except Exception as e:
        if node:
            node.get_logger().error(f"Error inesperado: {str(e)}")
    finally:
        # Perform orderly shutdown
        shutdown_ros(node)

def shutdown_ros(node):
    """Perform a clean and orderly ROS shutdown sequence"""
    if node is None:
        return
        
    try:
        # First clean up the node's resources
        node.cleanup()
            
        # Then destroy the node
        node.get_logger().info("Destroying node...")
        node.destroy_node()
    except Exception as e:
        print(f"Error during node cleanup: {str(e)}")
    
    try:
        # Finally shut down rclpy
        print("Shutting down ROS client...")
        rclpy.shutdown()
    except Exception as e:
        print(f"Error during ROS shutdown: {str(e)}")

if __name__ == '__main__':
    main()
