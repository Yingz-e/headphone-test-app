import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from core.audio_engine import Calibrator

def diagnose_residual(input_idx, output_idx):
    print("--- Residual Signal Diagnostic ---")
    
    # 1. Run Calibration (Simulated)
    print("1. Playing Calibration Tone (1kHz)...")
    calibrator = Calibrator(input_idx, output_idx)
    # Use a high gain to make residual obvious if present
    # But wait, run_calibration adjusts gain.
    # Let's manually play a tone to mimic calibration ending
    fs = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(fs*duration), endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * 1000 * t)
    signal = np.column_stack((tone, tone))
    
    sd.play(signal, samplerate=fs, device=output_idx, blocking=True)
    print("   Tone finished playing (according to sd.play).")
    
    # 2. Immediately Record Silence
    print("2. Immediately recording 'Silence' for 2 seconds...")
    rec_duration = 2.0
    rec = sd.rec(int(rec_duration * fs), samplerate=fs, channels=2, device=input_idx, dtype='float32')
    sd.wait()
    
    # 3. Analyze Recording
    # Plot the first 0.5s to see if there's bleed
    print("3. Analyzing recording...")
    chunk = rec[:int(0.5 * fs), 0]
    time_axis = np.linspace(0, 0.5, len(chunk))
    
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.plot(time_axis, chunk)
    plt.title("Recorded Signal Immediately After Tone (First 0.5s)")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.grid(True)
    
    # Check RMS of "silence"
    rms = np.sqrt(np.mean(chunk**2))
    db = 20 * np.log10(rms + 1e-9)
    print(f"RMS of first 0.5s: {rms:.6f} ({db:.2f} dBFS)")
    
    if db > -60:
        print("DETECTED RESIDUAL SIGNAL! The input buffer is dirty.")
    else:
        print("Buffer seems clean.")
        
    plt.tight_layout()
    plt.savefig("diagnose_residual.png")
    print("Saved plot to diagnose_residual.png")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        in_idx = 1
        out_idx = 6
    else:
        in_idx = int(sys.argv[1])
        out_idx = int(sys.argv[2])
    
    diagnose_residual(in_idx, out_idx)
