import sounddevice as sd
import soundfile as sf
import numpy as np

# Load two different tracks (or the same ones, but they will move independently now)
data_a, fs_a = sf.read("track_a.mp3", dtype='float32')
data_b, fs_b = sf.read("track_b.mp3", dtype='float32')

# 1. STATE MANAGEMENT: Track each deck's status independently
deck_a = {
    "data": data_a,
    "current_frame": 0,
    "is_playing": True,
    "volume": 1.0
}

deck_b = {
    "data": data_b,
    "current_frame": 0,
    "is_playing": False, # Start Deck B paused!
    "volume": 1.0
}

crossfader = 0.5



def audio_callback(outdata, frames, time, status):
    global crossfader
    
    # Initialize empty buffers for this specific audio chunk
    chunk_a = np.zeros((frames, data_a.shape[1]), dtype='float32')
    chunk_b = np.zeros((frames, data_b.shape[1]), dtype='float32')
    
    # --- PROCESS DECK A ---
    if deck_a["is_playing"]:
        pos = deck_a["current_frame"]
        size = min(len(deck_a["data"]) - pos, frames)
        if size > 0:
            chunk_a[:size] = deck_a["data"][pos : pos + size]
            deck_a["current_frame"] += size

    # --- PROCESS DECK B ---
    if deck_b["is_playing"]:
        pos = deck_b["current_frame"]
        size = min(len(deck_b["data"]) - pos, frames)
        if size > 0:
            chunk_b[:size] = deck_b["data"][pos : pos + size]
            deck_b["current_frame"] += size

    # --- APPLY MIXING MATH ---
    vol_a = (1.0 - crossfader) * deck_a["volume"]
    vol_b = crossfader * deck_b["volume"]
    
    # Combined mixed audio sent to speakers
    outdata[:] = (chunk_a * vol_a) + (chunk_b * vol_b)

# Start the audio stream
stream = sd.OutputStream(samplerate=fs_a, channels=data_a.shape[1], callback=audio_callback)

with stream:
    print("Dual Decks Ready!")
    print("Commands: 'play a', 'pause a', 'play b', 'pause b', 'fader [0-1]', 'q' to quit")
    
    while True:
        user_input = input("\nEnter command: ").strip().lower()
        
        if user_input == 'q':
            break
        elif user_input == 'play a':
            deck_a["is_playing"] = True
            print("Deck A playing")
        elif user_input == 'pause a':
            deck_a["is_playing"] = False
            print("Deck A paused")
        elif user_input == 'play b':
            deck_b["is_playing"] = True
            print("Deck B playing")
        elif user_input == 'pause b':
            deck_b["is_playing"] = False
            print("Deck B paused")
        elif user_input.startswith('fader'):
            try:
                val = float(user_input.split()[1])
                if 0.0 <= val <= 1.0:
                    crossfader = val
                    print(f"Crossfader: {crossfader}")
            except (ValueError, IndexError):
                print("Usage: fader 0.5")