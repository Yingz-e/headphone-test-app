import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QMessageBox, QLineEdit)
from PyQt6.QtCore import pyqtSignal

# Import AudioManager
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils.audio_manager import AudioManager

class AudioSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio Configuration")
        self.resize(400, 250)
        
        self.input_device_idx = None
        self.output_device_idx = None
        self.target_spl = 94.0 # Default
        
        self.init_ui()
        self.load_devices()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Input Device Selection
        layout.addWidget(QLabel("Input Device (Microphone):"))
        self.combo_input = QComboBox()
        layout.addWidget(self.combo_input)
        
        # Output Device Selection
        layout.addWidget(QLabel("Output Device (Headphone/DAC):"))
        self.combo_output = QComboBox()
        layout.addWidget(self.combo_output)
        
        # Target SPL Input
        layout.addWidget(QLabel("Target Calibration SPL (dB):"))
        self.txt_target_spl = QLineEdit()
        self.txt_target_spl.setText(str(self.target_spl))
        layout.addWidget(self.txt_target_spl)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh Devices")
        self.btn_refresh.clicked.connect(self.load_devices)
        
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.accept_settings)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_devices(self):
        self.combo_input.clear()
        self.combo_output.clear()
        
        devices = AudioManager.get_all_devices()
        # Filter logic if needed (e.g. show ASIO first)
        # For now, list all and show index
        
        for i, dev in enumerate(devices):
            name = dev['name']
            hostapi = dev['hostapi']
            hostapi_name = AudioManager.get_hostapi_name(hostapi)
            
            display_text = f"[{i}] {name} [{hostapi_name}] (In: {dev['max_input_channels']}, Out: {dev['max_output_channels']})"
            
            # Add to input if it has input channels
            if dev['max_input_channels'] > 0:
                self.combo_input.addItem(display_text, i)
                
            # Add to output if it has output channels
            if dev['max_output_channels'] > 0:
                self.combo_output.addItem(display_text, i)
                
    def accept_settings(self):
        if self.combo_input.currentIndex() == -1 or self.combo_output.currentIndex() == -1:
            QMessageBox.warning(self, "Warning", "Please select both input and output devices.")
            return

        try:
            target = float(self.txt_target_spl.text())
            if target < 50 or target > 120:
                QMessageBox.warning(self, "Warning", "Target SPL should be between 50 and 120 dB.")
                return
            self.target_spl = target
        except ValueError:
            QMessageBox.warning(self, "Warning", "Invalid Target SPL.")
            return

        self.input_device_idx = self.combo_input.currentData()
        self.output_device_idx = self.combo_output.currentData()
        self.accept()

    def get_selected_devices(self):
        return self.input_device_idx, self.output_device_idx
