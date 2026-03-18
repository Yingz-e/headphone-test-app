import sounddevice as sd
import platform

class AudioManager:
    @staticmethod
    def get_all_devices():
        """Returns the full list of devices from sounddevice."""
        return sd.query_devices()

    @staticmethod
    def get_preferred_hostapi_name():
        """Returns the preferred host API name based on the OS."""
        system = platform.system()
        if system == 'Windows':
            return 'ASIO'
        elif system == 'Darwin': # macOS
            return 'Core Audio'
        else:
            return None

    @staticmethod
    def get_preferred_hostapi_index():
        """Finds the index of the preferred host API (ASIO on Windows, Core Audio on macOS)."""
        preferred_api = AudioManager.get_preferred_hostapi_name()
        if not preferred_api:
            return -1
            
        for i, api in enumerate(sd.query_hostapis()):
            if preferred_api in api['name']:
                return i
        return -1

    @staticmethod
    def get_hostapi_name(index):
        """Returns the name of the host API given its index."""
        try:
            return sd.query_hostapis()[index]['name']
        except:
            return "Unknown"

    @staticmethod
    def list_preferred_devices():
        """Returns a list of tuples (index, device_info) for preferred devices."""
        api_index = AudioManager.get_preferred_hostapi_index()
        if api_index == -1:
            return []
        
        devices = sd.query_devices()
        preferred_devices = []
        for i, dev in enumerate(devices):
            if dev['hostapi'] == api_index:
                preferred_devices.append((i, dev))
        return preferred_devices

    @staticmethod
    def print_device_info():
        """Prints detailed information about audio devices."""
        print(f"PortAudio version: {sd.get_portaudio_version()}")
        print(f"System: {platform.system()}")
        
        api_index = AudioManager.get_preferred_hostapi_index()
        api_name = AudioManager.get_preferred_hostapi_name() or "None"
        
        if api_index == -1:
            print(f"WARNING: Preferred Host API ({api_name}) not found in PortAudio.")
        else:
            print(f"Preferred Host API: {api_name} (Index: {api_index})")

        print("\n--- All Devices ---")
        print(sd.query_devices())

        print(f"\n--- {api_name} Devices ---")
        pref_devs = AudioManager.list_preferred_devices()
        if not pref_devs:
            print(f"No {api_name} devices found.")
        else:
            for idx, dev in pref_devs:
                print(f"Index {idx}: {dev['name']}")
                print(f"  Max Input Channels: {dev['max_input_channels']}")
                print(f"  Max Output Channels: {dev['max_output_channels']}")
                print(f"  Default Sample Rate: {dev['default_samplerate']}")
