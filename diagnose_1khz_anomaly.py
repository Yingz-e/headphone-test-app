import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
import sys
import os
import json
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from core.audio_engine import SignalGenerator, AudioAnalyzer

def analyze_signal(recording, fs, title="Signal"):
    """Plot Time and Frequency domain."""
    t = np.linspace(0, len(recording)/fs, len(recording))
    
    # FFT
    window = np.blackman(len(recording))
    fft_spec = np.fft.rfft(recording * window)
    freqs = np.fft.rfftfreq(len(recording), 1/fs)
    mag_db = 20 * np.log10(np.abs(fft_spec) + 1e-12)
    
    # Peak
    peak_idx = np.argmax(mag_db)
    peak_freq = freqs[peak_idx]
    peak_amp = mag_db[peak_idx]
    
    print(f"[{title}] Peak: {peak_amp:.2f}dB at {peak_freq:.2f}Hz")
    
    return freqs, mag_db

def diagnose(input_idx, output_idx):
    fs = 44100
    duration = 2.0
    gain = 0.5
    
    print(f"--- Audio Diagnostic (In:{input_idx}, Out:{output_idx}) ---")
    
    # Test 1: Silence (Noise Floor)
    print("\n[Test 1] Noise Floor Check (Playing Silence)")
    silence = np.zeros((int(duration * fs), 2))
    rec_silence = sd.playrec(silence, samplerate=fs, channels=2, device=(input_idx, output_idx), dtype='float32')
    sd.wait()
    rms_silence = np.sqrt(np.mean(rec_silence[:, 0]**2))
    db_silence = 20 * np.log10(rms_silence + 1e-9)
    print(f"Noise Floor RMS: {rms_silence:.6f} ({db_silence:.2f} dBFS)")
    
    if db_silence > -60:
        print("WARNING: High noise floor! Check loopback routing or background apps.")
    
    # Test 2: 1kHz Sine Purity
    print("\n[Test 2] 1kHz Sine Wave Purity")
    sine_1k = SignalGenerator.sine_wave(1000, duration, fs, gain)
    rec_1k = sd.playrec(sine_1k, samplerate=fs, channels=2, device=(input_idx, output_idx), dtype='float32')
    sd.wait()
    
    # Analyze 1k
    # Skip start/end transients
    start = int(0.2 * fs)
    end = int(1.8 * fs)
    chunk_1k = rec_1k[start:end, 0]
    
    freqs, mag = analyze_signal(chunk_1k, fs, "1kHz Sine")
    
    # Check Harmonics (2k, 3k)
    f_idx = np.argmax(mag)
    f_fund = freqs[f_idx]
    amp_fund = mag[f_idx]
    
    # Find harmonic peaks
    thd_sum = 0
    print("Harmonics:")
    for h in range(2, 10):
        h_freq = h * f_fund
        # Find closest bin
        idx = np.argmin(np.abs(freqs - h_freq))
        h_amp = mag[idx]
        delta = h_amp - amp_fund
        print(f"  {h}x ({freqs[idx]:.1f}Hz): {h_amp:.2f}dB (Delta: {delta:.2f}dB)")
        
    # Test 3: Latency / Buffer check
    print("\n[Test 3] Latency Check (Impulse)")
    impulse = np.zeros((int(1.0 * fs), 2))
    impulse[100, :] = 0.8 # Impulse at sample 100
    
    rec_imp = sd.playrec(impulse, samplerate=fs, channels=2, device=(input_idx, output_idx), dtype='float32')
    sd.wait()
    
    # Find peak in recording
    rec_peak_idx = np.argmax(np.abs(rec_imp[:, 0]))
    latency_samples = rec_peak_idx - 100
    latency_ms = latency_samples / fs * 1000
    print(f"Measured Loopback Latency: {latency_samples} samples ({latency_ms:.2f} ms)")
    
    if latency_ms > 200:
         print("WARNING: High latency! Verify buffer size.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python diagnose_1khz_anomaly.py <in_idx> <out_idx>")
        # Default
        in_idx = 1
        out_idx = 6
    else:
        in_idx = int(sys.argv[1])
        out_idx = int(sys.argv[2])
        
    diagnose(in_idx, out_idx)
