import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QGroupBox, 
                             QFormLayout, QTextEdit, QStatusBar, QMessageBox,
                             QTabWidget, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# Import Core Logic
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.core.audio_engine import Calibrator
from src.core.measurement import FrequencyResponseMeasurer, DistortionMeasurer, LinearityMeasurer
from src.ui.audio_settings import AudioSettingsDialog
import scipy.io.wavfile as wavfile
import datetime

class TestWorker(QThread):
    """Background worker for running audio tests."""
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(object) # (test_type, data)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(self, input_idx, output_idx, target_spl=94.0):
        super().__init__()
        self.input_idx = input_idx
        self.output_idx = output_idx
        self.target_spl = target_spl
        self.is_running = True
        self.phase_data = [] # Store phase for plotting

    def run(self):
        try:
            # 1. Calibration
            self.progress_signal.emit(f"Step 1/5: Calibrating (Target {self.target_spl}dB)...")
            calibrator = Calibrator(self.input_idx, self.output_idx, target_spl=self.target_spl)
            # Simulate offset for loopback testing
            success, gain, spl = calibrator.run_calibration(mic_offset_db=100)
            
            if not success:
                self.error_signal.emit(f"Calibration Failed! Gain={gain:.4f}, SPL={spl:.2f}dB")
                return
            
            self.progress_signal.emit(f"Calibration OK! Gain={gain:.4f}, SPL={spl:.2f}dB")
            
            # Wait for signal to clear (prevent bleed-over)
            self.progress_signal.emit("Waiting 2s for signal to clear...")
            import time
            time.sleep(2.0)
            
            # 2. Frequency Response & THD (Continuous)
            self.progress_signal.emit("Step 2/5: Measuring FR, Phase & THD (Sweep)...")
            fr_measurer = FrequencyResponseMeasurer(self.input_idx, self.output_idx)
            # Use calibrated gain
            result = fr_measurer.measure_sweep(duration=3.0, gain=gain)
            
            if result is None:
                 self.error_signal.emit("Frequency Response Measurement Failed.")
                 return

            freqs, mag, phase, ir, thd = result
            self.phase_data = phase # Store for THD plot secondary axis if needed
            self.result_signal.emit(("FR", (freqs, mag, phase, thd)))
            
            # 3. Impulse Response Saving
            self.progress_signal.emit("Step 3/5: Saving Impulse Response...")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ir_filename = f"ir_{timestamp}.wav"
            # Normalize IR to -1..1
            ir_norm = ir / np.max(np.abs(ir))
            wavfile.write(ir_filename, 44100, ir_norm.astype(np.float32))
            self.progress_signal.emit(f"Impulse Response saved to {ir_filename}")
            
            # 4. Dynamic Linearity Deviation
            self.progress_signal.emit("Step 4/5: Measuring Dynamic Linearity...")
            lin_measurer = LinearityMeasurer(self.input_idx, self.output_idx)
            lin_result = lin_measurer.measure_linearity(base_gain=gain, gain_step_db=10.0)
            
            if lin_result:
                self.result_signal.emit(("LINEARITY", lin_result))
            
            # 5. Stepped THD (Optional Verification)
            self.progress_signal.emit("Step 5/5: Verifying THD (Stepped)...")
            # Only test 3 points to save time
            thd_measurer = DistortionMeasurer(self.input_idx, self.output_idx)
            freqs_thd = [100, 1000, 5000] 
            thd_results = thd_measurer.measure_thd_stepped(freqs_thd, gain=gain)
            self.result_signal.emit(("THD_STEPPED", thd_results))
            
            self.progress_signal.emit("Test Completed Successfully!")
            self.finished_signal.emit()

        except Exception as e:
            self.error_signal.emit(f"Unexpected Error: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Headphone Auto-Test Suite (v0.6)")
        self.resize(1200, 800)
        
        self.input_device_idx = None
        self.output_device_idx = None
        self.target_spl = 94.0 # Default
        
        self.init_ui()
        
    def init_ui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left Panel: Controls & Info
        left_panel = QGroupBox("Control Panel")
        left_layout = QVBoxLayout()
        
        # 1. Device Info
        self.lbl_device_status = QLabel("No Audio Device Selected")
        self.lbl_device_status.setStyleSheet("color: red; font-weight: bold;")
        left_layout.addWidget(self.lbl_device_status)
        
        self.btn_settings = QPushButton("Audio Settings")
        self.btn_settings.clicked.connect(self.open_settings)
        left_layout.addWidget(self.btn_settings)
        
        # 2. Product Info Form
        form_group = QGroupBox("Product Information")
        form_layout = QFormLayout()
        self.txt_brand = QLineEdit()
        self.txt_model = QLineEdit()
        self.txt_serial = QLineEdit()
        form_layout.addRow("Brand:", self.txt_brand)
        form_layout.addRow("Model:", self.txt_model)
        form_layout.addRow("Serial No:", self.txt_serial)
        form_group.setLayout(form_layout)
        left_layout.addWidget(form_group)
        
        # 3. Actions
        self.btn_start = QPushButton("Start Test")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; padding: 10px;")
        self.btn_start.clicked.connect(self.start_test)
        self.btn_start.setEnabled(False) # Disabled until device selected
        left_layout.addWidget(self.btn_start)
        
        # 4. Logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        left_layout.addWidget(QLabel("Logs:"))
        left_layout.addWidget(self.log_text)
        
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(300)
        
        # Right Panel: Plots
        right_panel = QTabWidget()
        
        # FR Plot Tab
        self.fr_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        right_panel.addTab(self.fr_canvas, "Frequency Response")
        
        # THD Plot Tab (Placeholder for now)
        self.thd_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        right_panel.addTab(self.thd_canvas, "THD & Phase")
        
        # Add to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
    def log(self, message):
        self.log_text.append(message)
        self.status_bar.showMessage(message)

    def open_settings(self):
        dialog = AudioSettingsDialog(self)
        if dialog.exec():
            # Get selection
            # We need to implement get_selected_devices in dialog
            # Or access public members if simple
            # Let's assume dialog sets self.input_device_idx etc.
            # But wait, dialog is modal.
            
            # Accessing from dialog instance
            # The dialog implementation I wrote has `input_device_idx` attribute
            in_idx = dialog.input_device_idx
            out_idx = dialog.output_device_idx
            target = dialog.target_spl
            
            if in_idx is not None and out_idx is not None:
                self.input_device_idx = in_idx
                self.output_device_idx = out_idx
                self.target_spl = target
                
                self.lbl_device_status.setText(f"In: {in_idx} | Out: {out_idx} | Target: {target}dB")
                self.lbl_device_status.setStyleSheet("color: green; font-weight: bold;")
                self.btn_start.setEnabled(True)
                self.log(f"Selected Devices: Input {in_idx}, Output {out_idx}, Target SPL: {target}dB")

    def start_test(self):
        if self.input_device_idx is None:
            QMessageBox.critical(self, "Error", "Select audio devices first!")
            return
            
        self.btn_start.setEnabled(False)
        self.log("Starting Test Sequence...")
        
        # Start Worker Thread
        self.worker = TestWorker(self.input_device_idx, self.output_device_idx, target_spl=self.target_spl)
        self.worker.progress_signal.connect(self.log)
        self.worker.result_signal.connect(self.handle_results)
        self.worker.error_signal.connect(self.handle_error)
        self.worker.finished_signal.connect(self.test_finished)
        self.worker.start()

    def handle_results(self, data):
        test_type, result_data = data
        if test_type == "FR":
            freqs, mag, phase, thd = result_data
            self.plot_fr(freqs, mag, phase)
            self.plot_thd(freqs, thd)
        elif test_type == "LINEARITY":
            # result_data is a dict with freqs, mag_mid, deviation, etc.
            deviation = result_data['deviation']
            max_dev = np.max(np.abs(deviation))
            mean_dev = np.mean(np.abs(deviation))
            self.log(f"Dynamic Linearity Deviation: Max={max_dev:.4f}dB, Mean={mean_dev:.4f}dB")
            
            # Plot Deviation on FR tab (secondary line?) or just log it
            # Let's add it to the FR plot as a dashed line (scaled?) or just log for now.
            # Plotting deviation on its own scale is better.
            # For now, just logging is sufficient for verification.
            
        elif test_type == "THD_STEPPED":
            self.log(f"Stepped THD Verification: {result_data}")

    def plot_fr(self, freqs, mag, phase):
        self.fr_canvas.axes.clear()
        self.fr_canvas.axes.semilogx(freqs, mag, label='Magnitude (dB)')
        self.fr_canvas.axes.set_title("Frequency Response")
        self.fr_canvas.axes.set_xlabel("Frequency (Hz)")
        self.fr_canvas.axes.set_ylabel("Amplitude (dB)")
        self.fr_canvas.axes.grid(True, which="both")
        self.fr_canvas.axes.legend()
        self.fr_canvas.draw()
        
        # Plot Phase on the other tab (or secondary axis?)
        # Current logic puts Phase on THD tab, but THD tab should be for THD
        # Let's create a Phase tab or put Phase on secondary axis of FR?
        # The UI has "THD & Phase" tab.
        # Let's plot Phase there for now along with THD.

    def plot_thd(self, freqs, thd):
        self.thd_canvas.axes.clear()
        # Plot THD
        self.thd_canvas.axes.semilogx(freqs, thd, color='red', label='THD (%)')
        self.thd_canvas.axes.set_ylabel("THD (%)")
        self.thd_canvas.axes.set_xlabel("Frequency (Hz)")
        
        # Plot Phase on secondary axis
        ax2 = self.thd_canvas.axes.twinx()
        ax2.semilogx(freqs, self.worker.phase_data if hasattr(self.worker, 'phase_data') else [], color='orange', alpha=0.5, label='Phase')
        # Wait, I don't have phase data here easily unless passed.
        # `handle_results` passes `phase` to `plot_fr`.
        # Let's just plot THD here.
        
        self.thd_canvas.axes.set_title("THD (Continuous Sweep)")
        self.thd_canvas.axes.grid(True, which="both")
        self.thd_canvas.axes.legend(loc='upper left')
        self.thd_canvas.draw()

    def handle_error(self, msg):
        QMessageBox.critical(self, "Test Error", msg)
        self.log(f"Error: {msg}")
        self.btn_start.setEnabled(True)

    def test_finished(self):
        self.log("Test Finished.")
        self.btn_start.setEnabled(True)
        QMessageBox.information(self, "Done", "Test Sequence Completed!")

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
