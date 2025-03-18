import sys
import threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String as ROSString
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

    # Ejecutar la GUI (esto bloquea hasta que se cierra la ventana)
    ret = app.exec_()

    # Al salir, detener el executor y cerrar el nodo
    executor.shutdown()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(ret)

if __name__ == '__main__':
    main()
