import sounddevice as sd
import soundfile as sf

def list_devices():
    print("--- AVAILABLE AUDIO DEVICES ---")
    print(sd.query_devices())

def play_test_file(filename):
    print(f"\nPlaying {filename}...")
    # Read the data and the sample rate (usually 44100Hz)
    data, fs = sf.read(filename)
    # Play it on your default output device
    sd.play(data, fs)
    sd.wait() # Wait until the file finishes playing
    print("Playback finished!")

if __name__ == "__main__":
    list_devices()
    # Uncomment the line below once you put a real file in the folder
    play_test_file("test.mp3")