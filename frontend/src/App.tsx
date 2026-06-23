import { useState, useEffect } from "react";

type EQBand = "low" | "mid" | "high";

function App() {
  const BACKEND_URL = "http://127.0.0.1:8000";
  const [faderValue, setFaderValue] = useState<number>(0.5);
  const [deckAPlaying, setDeckAPlaying] = useState<boolean>(false);
  const [deckBPlaying, setDeckBPlaying] = useState<boolean>(false);
  const [deckAEQ, setDeckAEQ] = useState({ low: 1.0, mid: 1.0, high: 1.0 });
  const [deckBEQ, setDeckBEQ] = useState({ low: 1.0, mid: 1.0, high: 1.0 });

  // Waveform structural numerical arrays
  const [waveA, setWaveA] = useState<number[]>([]);
  const [waveB, setWaveB] = useState<number[]>([]);

  // Current track progress percentage (0.0 to 100.0)
  const [progressA, setProgressA] = useState<number>(0);
  const [progressB, setProgressB] = useState<number>(0);

  // 1. Fetch Waveform Data points once on application launch
  useEffect(() => {
    fetch(`${BACKEND_URL}/waveform/a`).then((res) => res.json()).then((data) => setWaveA(data));
    fetch(`${BACKEND_URL}/waveform/b`).then((res) => res.json()).then((data) => setWaveB(data));
  }, []);

  // 2. Poll the server status 10 times a second (every 100ms) for smooth real-time playhead tracking
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/state`);
        const state = await res.json();
        
        setDeckAPlaying(state.deck_a.is_playing);
        setDeckBPlaying(state.deck_b.is_playing);
        
        if (state.deck_a.total_frames > 0) {
          setProgressA((state.deck_a.current_frame / state.deck_a.total_frames) * 100);
        }
        if (state.deck_b.total_frames > 0) {
          setProgressB((state.deck_b.current_frame / state.deck_b.total_frames) * 100);
        }
      } catch (err) {
        console.error("Poller engine sync failed:", err);
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

  const triggerDeckAction = async (action: "play" | "pause", deck: "a" | "b") => {
    await fetch(`${BACKEND_URL}/${action}/${deck}`, { method: "POST" });
  };

  const handleFaderChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setFaderValue(val);
    await fetch(`${BACKEND_URL}/fader?value=${val}`, { method: "POST" });
  };

  const handleEQChange = async (deck: "a" | "b", band: EQBand, value: number) => {
    // 1. Update the UI sliders instantly
    if (deck === "a") setDeckAEQ((prev) => ({ ...prev, [band]: value }));
    if (deck === "b") setDeckBEQ((prev) => ({ ...prev, [band]: value }));
    
    // 2. Safely send the decimal value to the backend as a JSON body
    try {
      await fetch(`${BACKEND_URL}/eq/${deck}/${band}`, { 
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ value: value })
      });
    } catch (err) {
      console.error("EQ dispatch failed:", err);
    }
  };

  // 3. Handle interactive clicking/seeking directly on the visual waveform
const handleWaveformClick = async (deck: "a" | "b", e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickPct = (e.clientX - rect.left) / rect.width;
    
    await fetch(`${BACKEND_URL}/seek/${deck}`, { 
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ pct: clickPct }) // Sending as secure JSON
    });
  };

  const renderWaveform = (deck: "a" | "b", waveData: number[], currentProgress: number) => {
    return (
      <div 
        onClick={(e) => handleWaveformClick(deck, e)}
        className="relative h-20 w-full bg-slate-950 rounded-xl flex items-center justify-between px-2 gap-[2px] cursor-pointer overflow-hidden border border-slate-800"
      >
        {waveData.map((peak, idx) => {
          const barPct = (idx / waveData.length) * 100;
          const isPlayed = barPct <= currentProgress;
          return (
            <div
              key={idx}
              className={`w-full rounded-sm transition-colors ${isPlayed ? 'bg-blue-500' : 'bg-slate-700'}`}
              style={{ height: `${Math.max(10, peak * 100)}%` }}
            />
          );
        })}
        {/* Real-time Playhead Vertical Slicer Line */}
        <div 
          className="absolute top-0 bottom-0 w-[2px] bg-white shadow-[0_0_8px_white] pointer-events-none transition-all duration-100"
          style={{ left: `${currentProgress}%` }}
        />
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-6">
      <h1 className="text-2xl font-black tracking-widest mb-8 text-blue-500">
        PRO DIGITAL DJ STATION
      </h1>

      <div className="grid grid-cols-2 gap-8 w-full max-w-4xl mb-8">
        {/* DECK A */}
        <div className={`p-6 rounded-2xl border-2 bg-slate-900 transition-all ${deckAPlaying ? 'border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-slate-800'}`}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-slate-400">DECK A</h2>
            <span className={`px-2 py-0.5 text-xs rounded font-mono ${deckAPlaying ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-800 text-slate-500'}`}>
              {deckAPlaying ? "LIVE" : "PAUSED"}
            </span>
          </div>

          {/* Interactive Waveform Container */}
          <div className="mb-4">
            {renderWaveform("a", waveA, progressA)}
          </div>

          <div className="flex justify-around bg-slate-950 p-4 rounded-xl mb-4">
            {(["high", "mid", "low"] as EQBand[]).map((band) => (
              <div key={band} className="flex flex-col items-center gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-500">{band[0]}</span>
                <input
                  type="range" min="0" max="2" step="0.05" value={deckAEQ[band]}
                  onChange={(e) => handleEQChange("a", band, parseFloat(e.target.value))}
                  className="h-20 appearance-none bg-slate-800 rounded-lg w-1.5 cursor-pointer accent-blue-500"
                  style={{ transform: "rotate(-90deg)", transformOrigin: "center", WebkitAppearance: "slider-vertical" }}
                />
                <span className="text-[9px] font-mono text-slate-400 mt-1">{deckAEQ[band].toFixed(1)}x</span>
              </div>
            ))}
          </div>

          <button
            onClick={() => triggerDeckAction(deckAPlaying ? "pause" : "play", "a")}
            className={`w-full py-2.5 rounded-xl font-bold transition-all ${deckAPlaying ? 'bg-red-600' : 'bg-blue-600'}`}
          >
            {deckAPlaying ? "PAUSE" : "PLAY"}
          </button>
        </div>

        {/* DECK B */}
        <div className={`p-6 rounded-2xl border-2 bg-slate-900 transition-all ${deckBPlaying ? 'border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.15)]' : 'border-slate-800'}`}>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-bold text-slate-400">DECK B</h2>
            <span className={`px-2 py-0.5 text-xs rounded font-mono ${deckBPlaying ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-800 text-slate-500'}`}>
              {deckBPlaying ? "LIVE" : "PAUSED"}
            </span>
          </div>

          {/* Interactive Waveform Container */}
          <div className="mb-4">
            {renderWaveform("b", waveB, progressB)}
          </div>

          <div className="flex justify-around bg-slate-950 p-4 rounded-xl mb-4">
            {(["high", "mid", "low"] as EQBand[]).map((band) => (
              <div key={band} className="flex flex-col items-center gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-500">{band[0]}</span>
                <input
                  type="range" min="0" max="2" step="0.05" value={deckBEQ[band]}
                  onChange={(e) => handleEQChange("b", band, parseFloat(e.target.value))}
                  className="h-20 appearance-none bg-slate-800 rounded-lg w-1.5 cursor-pointer accent-blue-500"
                  style={{ transform: "rotate(-90deg)", transformOrigin: "center", WebkitAppearance: "slider-vertical" }}
                />
                <span className="text-[9px] font-mono text-slate-400 mt-1">{deckBEQ[band].toFixed(1)}x</span>
              </div>
            ))}
          </div>

          <button
            onClick={() => triggerDeckAction(deckBPlaying ? "pause" : "play", "b")}
            className={`w-full py-2.5 rounded-xl font-bold transition-all ${deckBPlaying ? 'bg-red-600' : 'bg-blue-600'}`}
          >
            {deckBPlaying ? "PAUSE" : "PLAY"}
          </button>
        </div>
      </div>

      {/* CROSSFADER BLOCK */}
      <div className="w-full max-w-4xl bg-slate-900 border border-slate-800 p-5 rounded-2xl flex flex-col items-center">
        <label className="text-[10px] font-bold tracking-widest text-slate-400 mb-2 uppercase">Crossfader</label>
        <div className="flex justify-between w-full text-[10px] font-mono text-slate-500 px-1 mb-1">
          <span>DECK A ({(100 - faderValue * 100).toFixed(0)}%)</span>
          <span>DECK B ({(faderValue * 100).toFixed(0)}%)</span>
        </div>
        <input
          type="range" min="0" max="1" step="0.01" value={faderValue} onChange={handleFaderChange}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
      </div>
    </div>
  );
}

export default App;