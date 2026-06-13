from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy import signal
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Audio Files
data_a, fs_a = sf.read("track_a.mp3", dtype='float32')
data_b, fs_b = sf.read("track_b.mp3", dtype='float32')
num_channels = data_a.shape[1]

# DSP Filters setup
sos_low = signal.butter(2, 250, btype='lowpass', fs=fs_a, output='sos')
sos_high = signal.butter(2, 4000, btype='highpass', fs=fs_a, output='sos')
sos_mid = signal.butter(2, [250, 4000], btype='bandpass', fs=fs_a, output='sos')

zi_init_low = signal.sosfilt_zi(sos_low)
zi_init_mid = signal.sosfilt_zi(sos_mid)
zi_init_high = signal.sosfilt_zi(sos_high)

state = {
    "crossfader": 0.5,
    "deck_a": {
        "data": data_a, "current_frame": 0, "is_playing": False,
        "eq_low": 1.0, "eq_mid": 1.0, "eq_high": 1.0,
        "zi_low": np.repeat(zi_init_low[:, :, np.newaxis], num_channels, axis=2),
        "zi_mid": np.repeat(zi_init_mid[:, :, np.newaxis], num_channels, axis=2),
        "zi_high": np.repeat(zi_init_high[:, :, np.newaxis], num_channels, axis=2),
    },
    "deck_b": {
        "data": data_b, "current_frame": 0, "is_playing": False,
        "eq_low": 1.0, "eq_mid": 1.0, "eq_high": 1.0,
        "zi_low": np.repeat(zi_init_low[:, :, np.newaxis], num_channels, axis=2),
        "zi_mid": np.repeat(zi_init_mid[:, :, np.newaxis], num_channels, axis=2),
        "zi_high": np.repeat(zi_init_high[:, :, np.newaxis], num_channels, axis=2),
    }
}

def process_eq(audio_chunk, deck_state):
    if len(audio_chunk) == 0: return audio_chunk
    low_band, deck_state["zi_low"] = signal.sosfilt(sos_low, audio_chunk, axis=0, zi=deck_state["zi_low"])
    mid_band, deck_state["zi_mid"] = signal.sosfilt(sos_mid, audio_chunk, axis=0, zi=deck_state["zi_mid"])
    high_band, deck_state["zi_high"] = signal.sosfilt(sos_high, audio_chunk, axis=0, zi=deck_state["zi_high"])
    return (low_band * deck_state["eq_low"]) + (mid_band * deck_state["eq_mid"]) + (high_band * deck_state["eq_high"])

def audio_callback(outdata, frames, time, status):
    chunk_a = np.zeros((frames, num_channels), dtype='float32')
    chunk_b = np.zeros((frames, num_channels), dtype='float32')
    
    if state["deck_a"]["is_playing"]:
        pos = state["deck_a"]["current_frame"]
        size = min(len(state["deck_a"]["data"]) - pos, frames)
        if size > 0:
            chunk_a[:size] = process_eq(state["deck_a"]["data"][pos : pos + size], state["deck_a"])
            state["deck_a"]["current_frame"] += size
        else:
            state["deck_a"]["current_frame"] = 0

    if state["deck_b"]["is_playing"]:
        pos = state["deck_b"]["current_frame"]
        size = min(len(state["deck_b"]["data"]) - pos, frames)
        if size > 0:
            chunk_b[:size] = process_eq(state["deck_b"]["data"][pos : pos + size], state["deck_b"])
            state["deck_b"]["current_frame"] += size
        else:
            state["deck_b"]["current_frame"] = 0

    outdata[:] = (chunk_a * (1.0 - state["crossfader"])) + (chunk_b * state["crossfader"])

stream = sd.OutputStream(samplerate=fs_a, channels=num_channels, callback=audio_callback)
stream.start()

# --- WAVEFORM & POSITION ENDPOINTS ---

@app.get("/waveform/{deck_name}")
def get_waveform(deck_name: str, points: int = 150):
    """Downsamples audio data into specific number of peak points for clean UI drawing"""
    deck_key = f"deck_{deck_name}"
    if deck_key not in state: return {"error": "Invalid deck"}
    
    # Analyze only the left channel (column 0) to save CPU power
    raw_data = state[deck_key]["data"][:, 0]
    total_samples = len(raw_data)
    
    step = max(1, total_samples // points)
    waveform_peaks = []
    
    for i in range(0, total_samples, step):
        block = raw_data[i : i + step]
        if len(block) > 0:
            # Grab the maximum absolute volume structural peak in this section
            peak = float(np.max(np.abs(block)))
            waveform_peaks.append(peak)
            
    return waveform_peaks[:points]

# Create a payload model just like we did for Seek
class EQRequest(BaseModel):
    value: float

@app.post("/eq/{deck_name}/{band}")
def set_eq(deck_name: str, band: str, payload: EQRequest):
    """Safely receives EQ values via JSON body to avoid URL path float errors"""
    deck_key = f"deck_{deck_name}"
    
    if deck_key in state:
        # Save the value to our state dictionary
        state[deck_key][f"eq_{band}"] = payload.value
        
        # Print confirmation
        print(f"-> SUCCESS: Deck {deck_name.upper()} {band.upper()} EQ set to {payload.value}x")
        return {"status": "success", "value": payload.value}
        
    return {"error": "Invalid deck"}

@app.get("/state")
def get_state():
    """Polled by frontend to accurately calculate playhead percentages in real time"""
    return {
        "crossfader": state["crossfader"],
        "deck_a": {
            "is_playing": state["deck_a"]["is_playing"],
            "current_frame": state["deck_a"]["current_frame"],
            "total_frames": len(state["deck_a"]["data"])
        },
        "deck_b": {
            "is_playing": state["deck_b"]["is_playing"],
            "current_frame": state["deck_b"]["current_frame"],
            "total_frames": len(state["deck_b"]["data"])
        }
    }

# Core structural endpoints preserved
@app.post("/play/{deck_name}")
def play_deck(deck_name: str):
    if f"deck_{deck_name}" in state: state[f"deck_{deck_name}"]["is_playing"] = True
@app.post("/pause/{deck_name}")
def pause_deck(deck_name: str):
    if f"deck_{deck_name}" in state: state[f"deck_{deck_name}"]["is_playing"] = False

@app.post("/eq/{deck_name}/{band}/{value}")
def set_eq(deck_name: str, band: str, value: float):
    """Forces the EQ update into the state dictionary"""
    deck_key = f"deck_{deck_name}"
    
    if deck_key in state:
        state[deck_key][f"eq_{band}"] = value
        print(f"-> SUCCESS: Deck {deck_name.upper()} {band.upper()} EQ set to {value}x")
        return {"status": "success", "value": value}
        
    print(f"-> FAILED: Deck {deck_key} not found in state.")
    return {"error": "Invalid deck"}

@app.post("/fader")
def set_fader(value: float):
    state["crossfader"] = value

@app.post("/eq/{deck_name}/{band}/{value}")
def set_eq(deck_name: str, band: str, value: float):
    """Forces the EQ update into the state dictionary, creating the keys if missing."""
    deck_key = f"deck_{deck_name}"
    
    if deck_key in state:
        # Force the key into existence and assign the value
        state[deck_key][f"eq_{band}"] = value
        
        # This print MUST show up in your terminal when you move the slider
        print(f"-> SUCCESS: Deck {deck_name.upper()} {band.upper()} EQ set to {value}x")
        return {"status": "success", "value": value}
        
    print(f"-> FAILED: Deck {deck_key} not found in state.")
    return {"error": "Invalid deck"}