import sys
import threading
import signal
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
import cv2
import numpy as np
import configparser as cp
import json
from methane_scan.controllers.main_controller import MainController  # type: ignore
from PyQt5 import QtWidgets, QtGui, QtCore
import os


class MethaneScanNode(Node):
    def __init__(self):
        super().__init__('methane_scan_node')

        self.callback_ptu_ready = None
        self.sent_ptu_ready = False
        self.sent_hunter_position = False
        self.callback_hunter_position = None

        self.subscription = self.create_subscription(
            Bool,
            '/PTU_ready',
            self.listener_callback,
            10)
        
        self.subscription_hunter_position = self.create_subscription(
            String,
            '/hunter_position',
            self.listener_hunter_position_callback,
            10
        )

    def listener_callback(self, msg):
        if not self.sent_ptu_ready:
            self.get_logger().info(f'Received message: {msg.data}')
            self.callback_ptu_ready(msg.data)
            self.sent_ptu_ready = True
    
    def listener_hunter_position_callback(self, msg):
        if not self.sent_hunter_position:
            data = json.loads(msg.data)
            self.get_logger().info(f'Received message: {data}')
            self.callback_hunter_position(data)
            self.sent_hunter_position = True


def main(args=None):
    rclpy.init(args=args)
    node = MethaneScanNode()

    # Iniciar el executor en un hilo separado
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()

    # Crear la aplicación PyQt
    app = QtWidgets.QApplication(sys.argv)
    controller = MainController(node=node)
    controller.view.show()

    node.callback_ptu_ready = lambda msg: controller.update_PTU_ready(msg)
    node.callback_hunter_position = lambda msg: controller.update_hunter_position(msg)
    
    # Manejar señales para una salida ordenada
    def signal_handler(sig, frame):
        app.quit()
        
    signal.signal(signal.SIGINT, signal_handler)
    
    ret = 0
    try:
        # Ejecutar la GUI (esto bloquea hasta que se cierra la ventana)
        ret = app.exec()  # Use exec() instead of exec_()
    finally:
        # Al salir, detener el executor y cerrar el nodo
        node.get_logger().info('Shutting down node...')
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()
    
    sys.exit(ret)

if __name__ == '__main__':
    main()
