import time
import numpy as np
import sys
import os
import matplotlib.pyplot as plt

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.audio_engine import Calibrator
from core.measurement import FrequencyResponseMeasurer, DistortionMeasurer

def run_verification(input_idx, output_idx):
    print(f"--- Starting Core Algorithm Verification ---")
    print(f"Devices: Input={input_idx}, Output={output_idx}")
    
    # 1. Test Calibration
    print("\n[Test 1] Automatic Gain Calibration (Target: 94dB SPL)")
    print("NOTE: Using a simulated mic offset of 100dB.")
    print("      This means -6dBFS input will be interpreted as 94dB SPL.")
    
    calibrator = Calibrator(input_idx, output_idx)
    # We pass the offset here. The calibrator will adjust gain until measured SPL = 94.
    success, gain, spl = calibrator.run_calibration(mic_offset_db=100)
    
    print(f"Calibration Result: Success={success}, Final Gain={gain:.4f}, Final SPL={spl:.2f}dB")
    
    # Use the calibrated gain for next tests (or a safe default if failed)
    test_gain = gain if success else 0.1
    
    # 2. Test Frequency Response
    print("\n[Test 2] Frequency Response Sweep (20Hz - 20kHz)")
    fr_measurer = FrequencyResponseMeasurer(input_idx, output_idx)
    result = fr_measurer.measure_sweep(duration=3.0, gain=test_gain)
    
    if result is not None:
        freqs, mag, phase, ir = result
        if freqs is not None and len(freqs) > 0:
            print(f"Sweep completed. Captured {len(freqs)} frequency points.")
            print(f"Average Magnitude: {np.mean(mag):.2f} dB")
            
            # Plot FR
            try:
                plt.figure(figsize=(10, 6))
                plt.subplot(2, 1, 1)
                plt.semilogx(freqs, mag)
                plt.title("Frequency Response")
                plt.ylabel("Magnitude (dB)")
                plt.grid(True, which="both")
                
                plt.subplot(2, 1, 2)
                plt.semilogx(freqs, phase)
                plt.title("Phase Response")
                plt.ylabel("Phase (deg)")
                plt.xlabel("Frequency (Hz)")
                plt.grid(True, which="both")
                
                plt.tight_layout()
                plt.savefig("test_fr_result.png")
                print("Saved FR plot to 'test_fr_result.png'")
            except Exception as e:
                print(f"Plotting failed: {e}")
        else:
            print("Sweep failed: No valid data.")
    
    # 3. Test THD
    print("\n[Test 3] Stepped THD Measurement (100Hz, 1kHz, 5kHz)")
    thd_measurer = DistortionMeasurer(input_idx, output_idx)
    thd_freqs = [100, 1000, 5000]
    thd_results = thd_measurer.measure_thd_stepped(thd_freqs, gain=test_gain)
    
    print("THD Results:")
    for f, thd in thd_results:
        print(f"  {f}Hz: {thd:.4f}%")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        in_idx = int(sys.argv[1])
        out_idx = int(sys.argv[2])
    else:
        # Hardcoded default for non-interactive run if needed, but prefer args
        print("Usage: python verify_core_algos.py <input_idx> <output_idx>")
        print("Using default indices 1 and 6 for testing...")
        in_idx = 1
        out_idx = 6
    
    run_verification(in_idx, out_idx)
