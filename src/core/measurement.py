import numpy as np
import scipy.signal as signal
import sounddevice as sd
import time
from .audio_engine import SignalGenerator, AudioAnalyzer

class FrequencyResponseMeasurer:
    """Handles frequency response measurement."""
    
    def __init__(self, input_device, output_device, sample_rate=44100):
        self.input_device = input_device
        self.output_device = output_device
        self.sample_rate = sample_rate
        
    def flush_input_buffer(self, duration=1.0):
        """
        Reads from the input device to clear any residual audio.
        This is crucial for high-latency systems (like VoiceMeeter)
        where the input buffer might still contain the previous signal.
        """
        print(f"Flushing input buffer for {duration}s...")
        try:
            # Just record and discard
            sd.rec(int(duration * self.sample_rate), samplerate=self.sample_rate, 
                   channels=2, device=self.input_device, dtype='float32')
            sd.wait()
            print("Input buffer flushed.")
        except Exception as e:
            print(f"Warning: Failed to flush input buffer: {e}")

    def measure_sweep(self, start_freq=20, end_freq=20000, duration=2.0, gain=0.1):
        """
        Performs a sine sweep measurement.
        
        Returns:
            (freqs, magnitude_db, phase_deg, impulse_response, thd_data)
        """
        # Ensure clean state
        self.flush_input_buffer(duration=1.5) # Flush for 1.5s to be safe
        
        print(f"Starting Sweep: {start_freq}-{end_freq}Hz, {duration}s, Gain={gain}")
        
        # 1. Generate Sweep Signal
        sweep_signal = SignalGenerator.logarithmic_sweep(start_freq, end_freq, duration, self.sample_rate, amplitude=gain)
        
        # Add silence padding to capture reverb tail/latency and ensure clean start
        pre_padding_duration = 0.5
        post_padding_duration = 0.5
        
        pre_padding_samples = int(pre_padding_duration * self.sample_rate)
        post_padding_samples = int(post_padding_duration * self.sample_rate)
        
        pre_padding = np.zeros((pre_padding_samples, 2))
        post_padding = np.zeros((post_padding_samples, 2))
        
        full_signal = np.vstack((pre_padding, sweep_signal, post_padding))
        
        # 2. Play and Record
        try:
            recording = sd.playrec(full_signal, samplerate=self.sample_rate, channels=2, 
                                   device=(self.input_device, self.output_device), dtype='float32')
            sd.wait()
        except Exception as e:
            print(f"Error during sweep: {e}")
            return None, None, None, None, None
            
        # 3. Analyze Impulse Response (IR)
        # We need the original mono sweep for deconvolution
        # The sweep generator returns stereo, take one channel
        original_sweep = sweep_signal[:, 0]
        
        # Extract the relevant part of the recording (remove pre-padding)
        # The recording includes pre-padding, so the response should start around pre_padding_samples
        # But due to latency, it might be later. Deconvolution handles the time shift naturally,
        # but we should be careful not to include the silence BEFORE the sweep in the analysis if possible,
        # or just use the full recording and let the math work it out.
        # Ideally, we deconvolving the FULL recording against the ORIGINAL SWEEP (padded to match).
        
        recorded_response = recording[:, 0] # Use Left channel
        
        # Construct the full excitation signal as it was played (mono)
        full_excitation_mono = np.concatenate((
            np.zeros(pre_padding_samples), 
            original_sweep, 
            np.zeros(post_padding_samples)
        ))
        
        # Ensure lengths match exactly
        if len(recorded_response) != len(full_excitation_mono):
             min_len = min(len(recorded_response), len(full_excitation_mono))
             recorded_response = recorded_response[:min_len]
             full_excitation_mono = full_excitation_mono[:min_len]

        # Use Cross-Correlation to find the actual start of the sweep
        # This handles the latency issue
        # We correlate recording with the raw sweep (no padding) to find the peak lag
        
        # Performance optimization: Use FFT convolution for correlation if signals are long
        # But standard numpy correlate is fine for short signals. 
        # Note: signal.correlate(in1, in2) corresponds to sum(in1[k+m] * in2[k])
        
        # Calculate lag: where does 'original_sweep' best fit inside 'recorded_response'?
        correlation = signal.correlate(recorded_response, original_sweep, mode='full')
        lags = signal.correlation_lags(len(recorded_response), len(original_sweep), mode='full')
        lag_idx = np.argmax(np.abs(correlation))
        best_lag = lags[lag_idx]
        
        # best_lag is the shift of original_sweep relative to recorded_response.
        # If best_lag is positive X, it means original_sweep starts at index X in recorded_response.
        
        print(f"Detected Latency Lag: {best_lag} samples ({best_lag/self.sample_rate*1000:.2f} ms)")
        
        # Calculate shift amount needed to align recording with expected timing
        # In our theoretical model (full_excitation_mono), the sweep starts at 'pre_padding_samples'
        # In reality (recorded_response), it starts at 'best_lag'
        
        actual_start = best_lag
        expected_start = pre_padding_samples
        shift_needed = expected_start - actual_start # Shift recording RIGHT by this amount (or LEFT if negative)
        
        # If actual start is later (larger index), shift_needed is negative (shift left)
        # Shift recorded signal to align with theoretical excitation
        recorded_aligned = np.roll(recorded_response, shift_needed)
        
        # Zero out the parts that wrapped around due to roll?
        # Yes, rolling moves the end to the start. For impulse response analysis, this circular convolution is actually okay
        # if we consider DFT properties, but strictly we should probably zero pad or handle edges.
        # Given we have padding, the wrap-around should be silence anyway.
        
        # Now deconvolve
        fft_resp = np.fft.rfft(recorded_aligned)
        fft_exc = np.fft.rfft(full_excitation_mono)
        
        # Regularization to avoid division by zero
        epsilon = 1e-10
        # Calculate Transfer Function (H = Y / X)
        h_spectrum = fft_resp / (fft_exc + epsilon)
        
        # Inverse FFT to get Impulse Response
        impulse_response = np.fft.irfft(h_spectrum)
        
        # --- THD Calculation (Farina Method) ---
        # In a log sweep, harmonic distortion components appear as pre-echoes in the IR.
        # 2nd harmonic is shifted by T_shift(2) = T * log(2) / log(f2/f1)
        # 3rd harmonic is shifted by T_shift(3) = T * log(3) / log(f2/f1)
        # etc.
        # We can window these harmonic IRs and FFT them to get harmonic magnitude.
        
        # Calculate T_shift factor
        # T_sweep = duration
        # f1 = start_freq
        # f2 = end_freq
        L = np.log(end_freq / start_freq)
        
        def get_harmonic_ir(order, ir_full, ir_len):
            # Time shift for n-th harmonic
            # T_shift = duration * log(order) / L
            t_shift = duration * np.log(order) / L
            shift_samples = int(t_shift * self.sample_rate)
            
            # The harmonic IR is located at t = -t_shift relative to the fundamental.
            # Fundamental is at t=0 (or wherever peak is).
            # So harmonic is at index = peak_idx - shift_samples.
            # But due to circular convolution, negative index wraps around to end.
            
            # Find peak of fundamental IR (already centered or at 0?)
            # IR is raw from IFFT. Peak should be at 0 if aligned perfectly.
            # But let's find it.
            peak_idx = np.argmax(np.abs(ir_full))
            
            harmonic_peak_idx = peak_idx - shift_samples
            
            # Window the harmonic IR
            # Window size: enough to capture the impulse but not overlap with adjacent harmonics
            # Distance to next harmonic (order+1) or previous (order-1)?
            # T_shift(n) - T_shift(n-1) gets smaller as n increases.
            # For 2nd harmonic, distance to fundamental is large.
            # For 10th harmonic, distance to 9th is small.
            
            # Simple fixed window for now, or dynamic?
            # Let's use a conservative window.
            # E.g. 50ms window centered at harmonic peak.
            win_half = int(0.02 * self.sample_rate) # 20ms radius
            
            start = harmonic_peak_idx - win_half
            end = harmonic_peak_idx + win_half
            
            # Extract and handle wrap-around
            if start < 0:
                # Wrap around
                chunk = np.concatenate((ir_full[start:], ir_full[:end]))
            elif end > ir_len:
                chunk = np.concatenate((ir_full[start:], ir_full[:end-ir_len]))
            else:
                chunk = ir_full[start:end]
                
            # Pad to full length for FFT resolution matching
            padded_chunk = np.zeros(ir_len)
            if len(chunk) <= ir_len:
                padded_chunk[:len(chunk)] = chunk * np.blackman(len(chunk))
            
            return padded_chunk

        # Calculate Fundamental (Linear) Response
        # Peak at 0 (or close). Window it as before.
        peak_ir_idx = np.argmax(np.abs(impulse_response))
        center_idx = len(impulse_response) // 2
        roll_amount = center_idx - peak_ir_idx
        impulse_response_centered = np.roll(impulse_response, roll_amount)
        window_len = len(impulse_response_centered)
        window_func = signal.windows.tukey(window_len, alpha=0.1)
        impulse_response_windowed = impulse_response_centered * window_func
        impulse_response_final = np.roll(impulse_response_windowed, -roll_amount)
        
        h_fundamental = np.fft.rfft(impulse_response_final)
        mag_fundamental = np.abs(h_fundamental)
        
        # Calculate Harmonics (2nd, 3rd)
        thd_accum = np.zeros_like(mag_fundamental)
        
        # Sum of squares of harmonics
        # Only up to 5th harmonic usually relevant
        for order in range(2, 6):
            h_ir = get_harmonic_ir(order, impulse_response, len(impulse_response))
            h_fft = np.fft.rfft(h_ir)
            mag_h = np.abs(h_fft)
            thd_accum += mag_h**2
            
        thd_percent = np.sqrt(thd_accum) / (mag_fundamental + 1e-12) * 100
        
        # 4. Calculate Frequency Response from Windowed IR
        h_spectrum_windowed = h_fundamental # Use windowed fundamental for FR
        
        # Frequency vector
        freqs = np.fft.rfftfreq(len(impulse_response), 1/self.sample_rate)
        
        mag_response = np.abs(h_spectrum_windowed)
        phase_response = np.angle(h_spectrum_windowed)
        
        # Convert to dB
        mag_db = 20 * np.log10(mag_response + 1e-12)
        
        # Unwrap phase
        phase_unwrapped = np.unwrap(phase_response)
        phase_deg = np.degrees(phase_unwrapped)
        
        # Filter range (20Hz - 20kHz) and positive frequencies only
        mask = (freqs >= start_freq) & (freqs <= end_freq)
        
        return freqs[mask], mag_db[mask], phase_deg[mask], impulse_response, thd_percent[mask]

class LinearityMeasurer:
    """Handles Dynamic Linearity Deviation test."""
    
    def __init__(self, input_device, output_device, sample_rate=44100):
        self.fr_measurer = FrequencyResponseMeasurer(input_device, output_device, sample_rate)
        
    def measure_linearity(self, base_gain, gain_step_db=10.0):
        """
        Performs linearity test at Base, High (+10dB), and Low (-10dB) levels.
        
        Returns:
            dict containing FR curves for High, Mid, Low and Deviation curve.
        """
        # Calculate gains
        factor = 10**(gain_step_db / 20.0)
        gain_high = base_gain * factor
        gain_low = base_gain / factor
        
        print(f"Linearity Test: Base={base_gain:.4f}, High={gain_high:.4f}, Low={gain_low:.4f}")
        
        # Measure Base
        print("Measuring Base Level...")
        res_mid = self.fr_measurer.measure_sweep(gain=base_gain)
        if not res_mid[0].any(): return None
        
        # Measure High
        print("Measuring High Level...")
        if gain_high > 1.0:
            print("Warning: High gain > 1.0, clipping to 1.0")
            gain_high = 1.0
        res_high = self.fr_measurer.measure_sweep(gain=gain_high)
        
        # Measure Low
        print("Measuring Low Level...")
        res_low = self.fr_measurer.measure_sweep(gain=gain_low)
        
        freqs = res_mid[0]
        mag_high = res_high[1]
        mag_low = res_low[1]
        mag_mid = res_mid[1]
        
        # Deviation = High_dB - Low_dB
        deviation = mag_high - mag_low
        
        return {
            "freqs": freqs,
            "mag_mid": mag_mid,
            "mag_high": mag_high,
            "mag_low": mag_low,
            "deviation": deviation
        }

class DistortionMeasurer:
    """Handles THD measurement using stepped sine or sweep analysis."""
    
    def __init__(self, input_device, output_device, sample_rate=44100):
        self.input_device = input_device
        self.output_device = output_device
        self.sample_rate = sample_rate

    def measure_thd_stepped(self, frequencies, gain=0.1):
        """
        Measures THD at specific frequency points using Stepped Sine.
        """
        thd_results = []
        print("Starting Stepped THD Measurement...")
        
        for f in frequencies:
            # Play tone
            duration = 0.5
            signal_wave = SignalGenerator.sine_wave(f, duration, self.sample_rate, amplitude=gain)
            
            # Record
            try:
                rec = sd.playrec(signal_wave, samplerate=self.sample_rate, channels=2, 
                                 device=(self.input_device, self.output_device), dtype='float32')
                sd.wait()
            except Exception as e:
                print(f"Error measuring {f}Hz: {e}")
                continue
                
            # Analyze middle part to avoid transient
            # Wait 100ms for settling
            start_idx = int(0.1 * self.sample_rate)
            # Use 200ms window
            end_idx = start_idx + int(0.2 * self.sample_rate)
            
            if end_idx > len(rec): end_idx = len(rec)
            
            chunk = rec[start_idx:end_idx, 0]
            
            thd = AudioAnalyzer.calculate_thd(chunk, self.sample_rate, f)
            thd_results.append((f, thd))
            print(f"Freq: {f}Hz -> THD: {thd:.2f}%")
            
        return thd_results
