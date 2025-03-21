        self.stacked_widget.addWidget(self.methane_scan_tab)        # Índice 0: Pantalla principal
        self.stacked_widget.addWidget(self.ptu_config_widget)       # Índice 1: Pantalla de configuración PTU
        self.stacked_widget.addWidget(self.robot_config_widget)     # Índice 2: Pantalla de configuración Robot
    def switch_to_ptu_config(self):
        # Use stacked widget to switch to PTU config page
        self.stacked_widget.setCurrentIndex(1)
    def switch_to_robot_config(self):
        # Use stacked widget to switch to Robot config page
        self.stacked_widget.setCurrentIndex(2)
    def switch_to_home(self):
        # Use stacked widget to switch to home page
        self.stacked_widget.setCurrentIndex(0)
    sys.exit(app.exec())  # Updated to newer PyQt5 method
