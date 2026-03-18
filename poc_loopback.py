import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import time
import sys
import os

# Add src to path to import utils
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from utils.audio_manager import AudioManager

def generate_sine_wave(frequency, duration, sample_rate=44100, amplitude=0.5):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Generate stereo signal (2 channels)
    wave = amplitude * np.sin(2 * np.pi * frequency * t)
    return np.column_stack((wave, wave)) # Stereo

def run_loopback_test():
    print("--- Audio Loopback Test ---")
    
    # List devices
    print("\n--- Available Devices ---")
    print(sd.query_devices())
    
    print("\n--- Device Selection ---")
    input_idx_str = input("Enter Input Device Index (default system input): ")
    output_idx_str = input("Enter Output Device Index (default system output): ")
    
    input_idx = None
    output_idx = None
    
    if input_idx_str.strip():
        try:
            input_idx = int(input_idx_str)
        except ValueError:
            print("Invalid input index.")
            
    if output_idx_str.strip():
        try:
            output_idx = int(output_idx_str)
        except ValueError:
            print("Invalid output index.")
            
    device = (input_idx, output_idx) # Tuple for (input, output)
    if input_idx is None and output_idx is None:
        device = None # Use defaults
    elif input_idx is None:
        device = (sd.default.device[0], output_idx)
    elif output_idx is None:
        device = (input_idx, sd.default.device[1])

    # 2. Configuration
    fs = 44100  # Sample rate
    duration = 3.0  # Seconds
    freq = 1000.0 # Hz
    amplitude = 0.5
    
    # Generate signal
    print(f"\nGenerating {duration}s of {freq}Hz sine wave...")
    # Create the signal array
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    wave = amplitude * np.sin(2 * np.pi * freq * t)
    signal = np.column_stack((wave, wave)) # Stereo signal to play
    
    print(f"Starting playback on device {device}...")
    try:
        # Play and Record simultaneously
        # blocking=True means it waits until finished
        # sd.playrec returns the recorded data
        recording = sd.playrec(signal, samplerate=fs, channels=2, device=device, dtype='float32')
        sd.wait() # Wait for playback to finish
        print("Recording finished.")
        
        # 3. Analysis
        if recording is None or len(recording) == 0:
            print("Error: No data recorded.")
            return

        # Calculate RMS of the recorded signal
        rms_l = np.sqrt(np.mean(recording[:, 0]**2))
        rms_r = np.sqrt(np.mean(recording[:, 1]**2))
        
        # Calculate dBFS (Full Scale is 1.0)
        db_l = 20 * np.log10(rms_l + 1e-9)
        db_r = 20 * np.log10(rms_r + 1e-9)
        
        print(f"\n--- Results ---")
        print(f"Left Channel RMS: {rms_l:.4f} ({db_l:.2f} dBFS)")
        print(f"Right Channel RMS: {rms_r:.4f} ({db_r:.2f} dBFS)")
        
        # 4. Save to file
        filename = "loopback_test.wav"
        # Scale float32 (-1.0 to 1.0) to int16
        recording_int16 = (recording * 32767).astype(np.int16)
        wav.write(filename, fs, recording_int16)
        print(f"Saved recording to '{filename}'")
        
        if rms_l > 0.001 or rms_r > 0.001:
            print("\nSUCCESS: Signal detected!")
        else:
            print("\nWARNING: No signal detected (Silence). Check your loopback routing.")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_loopback_test()
