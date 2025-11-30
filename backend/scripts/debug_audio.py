import sounddevice as sd
import sys

print("Python executable:", sys.executable)
print("SoundDevice version:", sd.__version__)
print("\nSearching for devices...")

try:
    devices = sd.query_devices()
    print(f"\nFound {len(devices)} devices:\n")
    print(devices)
    
    print("\nDefault devices:", sd.default.device)
    
    print("\nAnalyzing Input Candidates:")
    targets = {'blackhole', 'vb-cable', 'loopback'}
    
    found_loopback = False
    
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            name = dev['name'].lower()
            is_loopback = any(t in name for t in targets)
            marker = " [LOOPBACK CANDIDATE]" if is_loopback else ""
            if is_loopback: found_loopback = True
            
            print(f"  Index {i}: {dev['name']} (In: {dev['max_input_channels']}){marker}")

    if not found_loopback:
        print("\nWARNING: No virtual audio device (BlackHole, VB-Cable, Loopback) found.")
        print("Only microphone audio will be captured.")

except Exception as e:
    print(f"\nERROR querying devices: {e}")

