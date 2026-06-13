import sounddevice as sd
import soundfile as sf
import numpy as np

# 1. Load BOTH tracks into memory
data_a, fs_a = sf.read("track_a.mp3", dtype='float32')
data_b, fs_b = sf.read("track_b.mp3", dtype='float32')

current_frame = 0

# The crossfader goes from 0.0 (Deck A only) to 1.0 (Deck B only)
# 0.5 means both are playing equally
crossfader = 0.5 

def audio_callback(outdata, frames, time, status):
    global current_frame, crossfader
    
    # Calculate how much audio is left
    chunk_size = min(len(data_a) - current_frame, frames)
    
    if chunk_size == 0:
        outdata.fill(0)
        raise sd.CallbackStop()

    # 2. Grab chunks for BOTH tracks
    chunk_a = data_a[current_frame : current_frame + chunk_size]
    chunk_b = data_b[current_frame : current_frame + chunk_size]
    
    # 3. Calculate volumes based on crossfader position
    vol_a = 1.0 - crossfader
    vol_b = crossfader
    
    # 4. Multiply chunks by their volumes
    processed_a = chunk_a * vol_a
    processed_b = chunk_b * vol_b
    
    # 5. THE MIX: Add the two arrays together! This is literally what "mixing" audio means.
    mixed_audio = processed_a + processed_b
    
    outdata[:chunk_size] = mixed_audio
    
    if chunk_size < frames:
        outdata[chunk_size:] = 0
        raise sd.CallbackStop()

    current_frame += chunk_size

stream = sd.OutputStream(samplerate=fs_a, channels=data_a.shape[1], callback=audio_callback)

with stream:
    print("Crossfader active! 0.0 = Track A | 0.5 = Both | 1.0 = Track B")
    print("Type 'q' to quit.")
    
    while True:
        user_input = input("Move crossfader (0.0 to 1.0): ")
        
        if user_input.lower() == 'q':
            break
        
        try:
            val = float(user_input)
            # Make sure they don't enter a number outside the fader limits
            if 0.0 <= val <= 1.0:
                crossfader = val
                print(f"Crossfader set to {crossfader}")
            else:
                print("Must be between 0.0 and 1.0!")
        except ValueError:
            print("Please enter a valid number.")