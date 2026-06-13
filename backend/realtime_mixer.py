import sounddevice as sd
import soundfile as sf
import numpy as np

# 1. Load the track into memory
data, fs = sf.read("test.mp3", dtype='float32')

# We need to keep track of where we are in the audio file
current_frame = 0

# This is our real-time volume multiplier. 1.0 is 100%, 0.5 is 50%, 0.0 is mute.
current_volume = 1.0 

def audio_callback(outdata, frames, time, status):
    """
    This function is called by the sound card dozens of times a second.
    'outdata' is the empty array the sound card wants us to fill with audio.
    'frames' is how many samples it needs right now.
    """
    global current_frame, current_volume
    
    # Calculate how much audio is left
    chunk_size = min(len(data) - current_frame, frames)
    
    # If the track is over, fill the rest with silence and stop
    if chunk_size == 0:
        outdata.fill(0)
        raise sd.CallbackStop()

    # 2. Grab the next tiny chunk of audio from our file
    audio_chunk = data[current_frame : current_frame + chunk_size]
    
    # 3. THE MAGIC: Multiply the chunk by our volume variable
    processed_audio = audio_chunk * current_volume
    
    # 4. Give the processed audio to the sound card
    outdata[:chunk_size] = processed_audio
    
    # If we are at the end of the file, pad the rest of the buffer with zeros (silence)
    if chunk_size < frames:
        outdata[chunk_size:] = 0
        raise sd.CallbackStop()

    # Move our position forward
    current_frame += chunk_size

# Start the stream in the background
stream = sd.OutputStream(samplerate=fs, channels=data.shape[1], callback=audio_callback)

with stream:
    print("Playing! Type a number between 0.0 and 1.0 to change volume.")
    print("Type 'q' to quit.")
    
    while True:
        # The audio is playing in the background. 
        # We can use the main thread to take user input!
        user_input = input("New volume: ")
        
        if user_input.lower() == 'q':
            break
        
        try:
            # Update the global volume variable instantly
            current_volume = float(user_input)
            print(f"Volume set to {current_volume}")
        except ValueError:
            print("Please enter a valid number.")