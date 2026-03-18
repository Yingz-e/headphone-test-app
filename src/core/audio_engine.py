import numpy as np
import scipy.signal as signal
import sounddevice as sd
import time
import math

class SignalGenerator:
    """Generates test signals for audio measurements."""
    
    @staticmethod
    def sine_wave(frequency, duration, sample_rate=44100, amplitude=1.0):
        """Generates a stereo sine wave."""
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        wave = amplitude * np.sin(2 * np.pi * frequency * t)
        return np.column_stack((wave, wave))

    @staticmethod
    def logarithmic_sweep(start_freq, end_freq, duration, sample_rate=44100, amplitude=1.0):
        """Generates a logarithmic sine sweep."""
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Logarithmic chirp
        wave = amplitude * signal.chirp(t, f0=start_freq, f1=end_freq, t1=duration, method='logarithmic')
        # Apply fade in/out to avoid clicks
        fade_len = int(0.01 * sample_rate) # 10ms fade
        if len(wave) > 2 * fade_len:
            fade_in = np.linspace(0, 1, fade_len)
            fade_out = np.linspace(1, 0, fade_len)
            wave[:fade_len] *= fade_in
            wave[-fade_len:] *= fade_out
            
        return np.column_stack((wave, wave))

class AudioAnalyzer:
    """Analyzes audio signals for SPL, Frequency Response, etc."""
    
    @staticmethod
    def calculate_rms(audio_data):
        """Calculates RMS value of the signal."""
        return np.sqrt(np.mean(audio_data**2))

    @staticmethod
    def calculate_spl(audio_data, mic_sensitivity_offset=0):
        """
        Calculates SPL (Sound Pressure Level) in dB based on RMS.
        
        mic_sensitivity_offset: The calibration factor to convert dBFS to SPL.
        SPL = 20*log10(RMS) + Offset
        
        Example: If -20 dBFS corresponds to 94 dB SPL, Offset = 114 dB.
        """
        rms = AudioAnalyzer.calculate_rms(audio_data)
        if rms < 1e-9: # Avoid log(0)
            return -100.0
            
        dbfs = 20 * np.log10(rms)
        return dbfs + mic_sensitivity_offset

    @staticmethod
    def calculate_thd(audio_data, sample_rate, fundamental_freq):
        """
        Calculates Total Harmonic Distortion (THD).
        THD = sqrt(sum(harmonics^2)) / fundamental
        """
        # Windowing
        window = np.blackman(len(audio_data))
        audio_windowed = audio_data * window
        
        # FFT
        fft_spectrum = np.fft.rfft(audio_windowed)
        freqs = np.fft.rfftfreq(len(audio_windowed), 1/sample_rate)
        magnitude = np.abs(fft_spectrum)
        
        # Find fundamental peak index
        bin_width = freqs[1] - freqs[0]
        fund_idx = int(fundamental_freq / bin_width)
        search_radius = int(50 / bin_width) # +/- 50Hz search window
        
        start = max(0, fund_idx - search_radius)
        end = min(len(magnitude), fund_idx + search_radius)
        if end <= start: return 0.0
        
        peak_local_idx = np.argmax(magnitude[start:end])
        peak_idx = start + peak_local_idx
        fundamental_mag = magnitude[peak_idx]
        
        if fundamental_mag < 1e-9: return 0.0

        # Sum harmonics (2nd, 3rd, ... 10th)
        harmonics_sum_sq = 0
        for n in range(2, 11):
            harmonic_freq = n * freqs[peak_idx]
            if harmonic_freq > sample_rate / 2:
                break
                
            h_idx = int(harmonic_freq / bin_width)
            # Search nearby for harmonic peak
            h_start = max(0, h_idx - search_radius)
            h_end = min(len(magnitude), h_idx + search_radius)
            
            if h_end > h_start:
                h_peak_mag = np.max(magnitude[h_start:h_end])
                harmonics_sum_sq += h_peak_mag**2
        
        thd = np.sqrt(harmonics_sum_sq) / fundamental_mag
        return thd * 100 # Percentage

class Calibrator:
    """Handles the automatic volume calibration process."""
    
    def __init__(self, input_device, output_device, sample_rate=44100, target_spl=94.0):
        self.input_device = input_device
        self.output_device = output_device
        self.sample_rate = sample_rate
        self.target_spl = target_spl
        self.tolerance = 0.5
        self.max_attempts = 10
        
    def run_calibration(self, mic_offset_db=0):
        """
        Adjusts output gain to reach 94dB SPL.
        
        Args:
            mic_offset_db: The calibration constant. 
                           If 0, it assumes 0 dBFS = 0 dB SPL (uncalibrated).
                           If e.g. 100, then -6 dBFS = 94 dB SPL.
        
        Returns:
            (success, final_gain, final_spl)
        """
        current_gain = 0.1 # Start low
        frequency = 1000.0
        duration = 1.0 # 1 second measurement per step
        
        print(f"Starting Calibration... Target: {self.target_spl}dB ±{self.tolerance}")
        
        for attempt in range(self.max_attempts):
            print(f"--- Attempt {attempt+1} (Gain: {current_gain:.4f}) ---")
            
            # Generate signal with current gain
            signal_wave = SignalGenerator.sine_wave(frequency, duration, self.sample_rate, amplitude=current_gain)
            
            # Play and Record
            try:
                recording = sd.playrec(signal_wave, samplerate=self.sample_rate, channels=2, 
                                       device=(self.input_device, self.output_device), dtype='float32')
                sd.wait()
            except Exception as e:
                print(f"Error during playback/recording: {e}")
                return False, current_gain, 0.0
            
            # Analyze (Use Left channel for now)
            audio_data = recording[:, 0]
            measured_spl = AudioAnalyzer.calculate_spl(audio_data, mic_offset_db)
            
            print(f"Measured SPL: {measured_spl:.2f} dB (Offset: {mic_offset_db})")
            
            if abs(measured_spl - self.target_spl) <= self.tolerance:
                print("Calibration Successful!")
                return True, current_gain, measured_spl
            
            # Adjust gain logic
            # If SPL is too low, increase gain.
            # Delta dB = Target - Measured
            # Gain_new = Gain_old * 10^(Delta_dB / 20)
            
            error_db = self.target_spl - measured_spl
            
            # Limit the step size to avoid huge jumps
            max_step_db = 10.0
            if error_db > max_step_db: error_db = max_step_db
            if error_db < -max_step_db: error_db = -max_step_db
            
            gain_factor = 10**(error_db / 20)
            
            # Apply damping
            new_gain = current_gain * gain_factor
            
            # Safety limits
            if new_gain > 1.0:
                print("Warning: Max gain reached (1.0). Clipping may occur.")
                new_gain = 1.0
                if current_gain == 1.0: # Already at max, can't go higher
                    print("Calibration Failed: Hardware gain insufficient.")
                    return False, 1.0, measured_spl
            elif new_gain < 0.0001:
                new_gain = 0.0001
            
            current_gain = new_gain
            time.sleep(0.2) # Short pause between attempts
                
        print("Calibration Failed: Could not converge after max attempts.")
        return False, current_gain, measured_spl
