import sys
import json
import os
import random
from pathlib import Path
from datetime import datetime

# Add the src folder to Python path
sys.path.insert(0, str(Path("C:/programming/fl_mcp/fl-studio-mcp/src")))

from fl_studio_mcp.utils.connection import get_connection
from fl_studio_mcp.utils.fl_trigger import get_trigger

def _get_fl_scripts_dir() -> Path:
    """Get FL Studio Piano roll scripts directory."""
    if sys.platform == "darwin":
        base = Path.home() / "Documents" / "Image-Line" / "FL Studio" / "Settings"
    else:
        userprofile = os.environ.get("USERPROFILE", "~")
        base = Path(userprofile) / "Documents" / "Image-Line" / "FL Studio" / "Settings"
    return base / "Piano roll scripts"

def _write_request(request: dict | list) -> None:
    """Write request to the request JSON file."""
    request_file = _get_fl_scripts_dir() / "mcp_request.json"
    request_file.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if isinstance(request, list):
        existing.extend(request)
    else:
        existing.append(request)
    with open(request_file, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"Request written to {request_file}")

def _get_projects_dir() -> Path:
    """Get the projects directory in the workspace."""
    workspace_dir = Path("c:/programming/fl_mcp/fl-studio-mcp")
    projects_dir = workspace_dir / "projects" / "dark-memphis-beats"
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir

def transpose_to_range(note: int, min_val: int, max_val: int) -> int:
    """Transpose a note to fit within a specific MIDI range."""
    while note < min_val:
        note += 12
    while note > max_val:
        note -= 12
    return note

def get_fl_channels(conn) -> list[dict]:
    """Retrieve all active channels from FL Studio."""
    result = conn.send_command("channels.getAll")
    return result.get("channels", [])

# --- GEN MODULE ---

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def get_key_name(root_pitch: int) -> str:
    """Get the key name (e.g., 'F Phrygian') based on root MIDI pitch."""
    note_name = NOTE_NAMES[root_pitch % 12]
    return f"{note_name} Phrygian"

def generate_beat(root_pitch: int = 50) -> dict:
    """Generate all MIDI patterns for a Dark Memphis Beat (8 bars / 32 beats)."""
    # root_pitch (octave 3): 50 = D3, 53 = F3, etc.
    
    # 1. Hi-Hats: 8-bar loop, 8th notes, C5 (72) root, rolls using 16th and 32nd notes.
    # On-beat velocity > off-beat velocity
    hat_notes = []
    for beat in range(32):
        hat_notes.append({"midi": 72, "duration": 0.25, "time": float(beat), "velocity": 0.90})
        hat_notes.append({"midi": 72, "duration": 0.25, "time": beat + 0.5, "velocity": 0.60})
        
    # Remove standard hits at roll positions and insert rolls
    # Roll at bar endings: beats 7.5, 15.5, 23.5, 31.5
    roll_beats = [7.0, 15.0, 23.0, 31.0]
    hat_notes = [h for h in hat_notes if h["time"] not in [r + 0.5 for r in roll_beats]]
    
    for r_beat in roll_beats:
        start = r_beat + 0.5
        # Alternating 16th note rolls and 32nd note pitch-ramping rolls
        if r_beat in (7.0, 23.0):
            # 16th roll (4 notes, duration 0.125 beats)
            for i in range(4):
                hat_notes.append({"midi": 72, "duration": 0.125, "time": start + (i * 0.125), "velocity": 0.75})
        else:
            # 32nd roll (8 notes, duration 0.0625 beats) with pitch ramp (C5 to G5)
            for i in range(8):
                pitch = 72 + i
                hat_notes.append({"midi": pitch, "duration": 0.0625, "time": start + (i * 0.0625), "velocity": 0.80})

    # 2. Kick: 8-bar loop, C4 (60) root. Hits on beat 1 of every 2 bars (0.0, 8.0, 16.0, 24.0).
    # Rest of hits at 4th and 6th beats, avoids 2nd/4th 16th notes (which are .25, .75).
    kick_beats = [
        # Bar 1 & 2
        0.0, 3.0, 5.5, 10.0, 13.0,
        # Bar 3 & 4
        16.0, 19.0, 21.5, 26.0, 29.0
    ]
    # Ensure beat 1 of every 2 bars is hit
    extra_bounces = [8.0, 24.0]
    all_kicks = sorted(list(set(kick_beats + extra_bounces)))
    kick_notes = [{"midi": 60, "duration": 0.5, "time": float(k), "velocity": 0.95} for k in all_kicks]

    # 3. Snare: 8-bar loop, C4 (60) root. Hits on the 3rd beat of each bar.
    # Has a fill at the end of the 8 bars.
    snare_notes = []
    for bar in range(8):
        beat_pos = (bar * 4.0) + 2.0
        snare_notes.append({"midi": 60, "duration": 0.5, "time": beat_pos, "velocity": 0.90})
        
    # Snare fill at the end of the 8th bar (beats 31.0 - 32.0)
    # 16th note roll
    fill_start = 31.0
    for i in range(4):
        snare_notes.append({"midi": 60, "duration": 0.25, "time": fill_start + (i * 0.25), "velocity": 0.80})

    # 4. Low Piano: 8-bar loop, max 3 notes, low range, Phrygian mode. Tonic is most common.
    # Semitone interval spacing: root_pitch, root_pitch + 1, root_pitch + 3
    tonic = root_pitch
    m2 = root_pitch + 1
    m3 = root_pitch + 3
    
    low_piano_notes = [
        # Bar 1-2
        {"midi": tonic, "duration": 4.0, "time": 0.0, "velocity": 0.75},
        {"midi": m2, "duration": 2.0, "time": 6.0, "velocity": 0.75},
        # Bar 3-4
        {"midi": tonic, "duration": 4.0, "time": 8.0, "velocity": 0.75},
        {"midi": m3, "duration": 2.0, "time": 12.0, "velocity": 0.75},
        {"midi": tonic, "duration": 2.0, "time": 14.0, "velocity": 0.75},
        # Bar 5-6
        {"midi": tonic, "duration": 4.0, "time": 16.0, "velocity": 0.75},
        {"midi": m2, "duration": 2.0, "time": 22.0, "velocity": 0.75},
        # Bar 7-8
        {"midi": tonic, "duration": 4.0, "time": 24.0, "velocity": 0.75},
        {"midi": m3, "duration": 2.0, "time": 28.0, "velocity": 0.75},
        {"midi": m2, "duration": 2.0, "time": 30.0, "velocity": 0.75},
    ]

    # 5. Bassline: 8-bar loop, follows Low Piano roots transposed to C4-C5 range, follows Kick rhythm.
    bass_notes = []
    # Key mapping
    for k in all_kicks:
        if k < 6.0:
            pitch = tonic
        elif k < 8.0:
            pitch = m2
        elif k < 12.0:
            pitch = tonic
        elif k < 14.0:
            pitch = m3
        elif k < 22.0:
            pitch = tonic
        elif k < 24.0:
            pitch = m2
        elif k < 28.0:
            pitch = tonic
        else:
            pitch = m2
            
        bass_pitch = transpose_to_range(pitch, 60, 72)
        bass_notes.append({"midi": bass_pitch, "duration": 0.75, "time": float(k), "velocity": 0.85})
        
        # Add filler note in the second 4 bars
        if k >= 16.0 and (k == 19.0 or k == 29.0):
            bass_notes.append({"midi": bass_pitch + 12, "duration": 0.5, "time": float(k) + 0.5, "velocity": 0.70})

    # 6. High Piano: 8-bar loop, high range, minor scale, repetitive/memorable, half-step interval.
    # F minor lead motif: 5th degree (root + 7), 6th degree (root + 8), 3rd degree (root + 3)
    deg5 = transpose_to_range(root_pitch + 7, 72, 88)
    deg6 = deg5 + 1 # half-step interval
    deg3 = transpose_to_range(root_pitch + 3, 72, 88)
    deg4 = transpose_to_range(root_pitch + 5, 72, 88)
    
    motif = [
        {"midi": deg5, "duration": 0.5, "time": 0.0, "velocity": 0.80},
        {"midi": deg6, "duration": 0.5, "time": 0.5, "velocity": 0.80},
        {"midi": deg5, "duration": 1.0, "time": 1.0, "velocity": 0.85},
        {"midi": deg3, "duration": 2.0, "time": 2.0, "velocity": 0.75},
        
        {"midi": deg5, "duration": 0.5, "time": 4.0, "velocity": 0.80},
        {"midi": deg6, "duration": 0.5, "time": 4.5, "velocity": 0.80},
        {"midi": deg5, "duration": 1.0, "time": 5.0, "velocity": 0.85},
        {"midi": deg4, "duration": 2.0, "time": 6.0, "velocity": 0.75},
    ]
    
    high_piano_notes = []
    for loop in range(4):
        offset = loop * 8.0
        for n in motif:
            high_piano_notes.append({
                "midi": n["midi"],
                "duration": n["duration"],
                "time": n["time"] + offset,
                "velocity": n["velocity"]
            })
            
    return {
        "bpm": 150,
        "key": get_key_name(root_pitch),
        "tracks": {
            "hihat": hat_notes,
            "kick": kick_notes,
            "snare": snare_notes,
            "low_piano": low_piano_notes,
            "bass": bass_notes,
            "high_piano": high_piano_notes
        }
    }

# --- FUZZY MATCHING MODULE ---

def fuzzy_match_channels(fl_channels: list[dict]) -> dict:
    """Match generic beat components to actual FL Studio channel indices."""
    mappings = {
        "hihat": {"keywords": ["hat", "hihat", "hi-hat", "hh", "shaker"], "index": None, "name": None},
        "kick": {"keywords": ["kick", "bd", "bass drum", "kickdrum"], "index": None, "name": None},
        "snare": {"keywords": ["snare", "sd"], "index": None, "name": None},
        "low_piano": {"keywords": ["keys", "piano", "rhodes", "epiano", "inst"], "index": None, "name": None},
        "bass": {"keywords": ["bass", "sub", "808", "bassline", "boobass", "flex"], "index": None, "name": None},
        "high_piano": {"keywords": ["lead", "high", "synth", "pluck", "melody"], "index": None, "name": None}
    }
    
    # Track used channel indices to avoid double matching
    matched_indices = set()
    
    # 1. Match specific drums and bass
    for part, data in mappings.items():
        best_score = -1
        best_ch = None
        for ch in fl_channels:
            idx = ch.get("index")
            if idx in matched_indices:
                continue
            name = ch.get("name", "").lower()
            for kw in data["keywords"]:
                if kw in name:
                    # Score based on how closely it matches keyword length
                    score = len(kw) / len(name)
                    if score > best_score:
                        best_score = score
                        best_ch = ch
                        
        if best_ch:
            data["index"] = best_ch["index"]
            data["name"] = best_ch["name"]
            matched_indices.add(best_ch["index"])

    # 2. Match pianos if not already matched
    # If we have multiple keys/pianos, assign the first one (lower index) to low_piano
    # and the second one (higher index) to high_piano.
    available_keys = []
    for ch in fl_channels:
        name = ch.get("name", "").lower()
        if "keys" in name or "piano" in name:
            available_keys.append(ch)
            
    if len(available_keys) >= 2:
        # Sort by name/index
        available_keys = sorted(available_keys, key=lambda x: x.get("index"))
        if mappings["low_piano"]["index"] is None:
            mappings["low_piano"]["index"] = available_keys[0]["index"]
            mappings["low_piano"]["name"] = available_keys[0]["name"]
        if mappings["high_piano"]["index"] is None:
            mappings["high_piano"]["index"] = available_keys[1]["index"]
            mappings["high_piano"]["name"] = available_keys[1]["name"]
    elif len(available_keys) == 1:
        if mappings["low_piano"]["index"] is None:
            mappings["low_piano"]["index"] = available_keys[0]["index"]
            mappings["low_piano"]["name"] = available_keys[0]["name"]

    # 3. Clean format return
    return {part: {"index": data["index"], "name": data["name"]} for part, data in mappings.items()}

# --- ACTION RUNNERS ---

def run_generation() -> str:
    """Generate the full project structure and save it to workspace."""
    # Find next beat index
    projects_dir = _get_projects_dir()
    existing_dirs = [d for d in projects_dir.iterdir() if d.is_dir() and d.name.startswith("beat_")]
    
    next_idx = 1
    if existing_dirs:
        try:
            indices = [int(d.name.split("_")[1]) for d in existing_dirs]
            next_idx = max(indices) + 1
        except:
            pass
            
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    beat_dir = projects_dir / f"beat_{next_idx}_{timestamp}"
    beat_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate notes in a dark key: D Phrygian / D minor (root 50)
    beat_data = generate_beat(root_pitch=50)
    
    # Save project file
    project_file = beat_dir / "beat.json"
    with open(project_file, "w") as f:
        json.dump(beat_data, f, indent=2)
        
    print(f"SUCCESS: Generated beat #{next_idx} structure.")
    print(f"DIRECTORY: {beat_dir}")
    print(f"FILE: {project_file}")
    
    # Query channels and match
    conn = get_connection()
    try:
        conn.ensure_connected()
        channels = get_fl_channels(conn)
        matches = fuzzy_match_channels(channels)
        print("MATCHES:", json.dumps(matches))
    except Exception as e:
        print("MATCH_ERROR:", str(e))
        
    return str(beat_dir)

def run_import(project_dir: str, track_type: str, match_index: int) -> None:
    """Select the target channel via MIDI, and write notes to request JSON or program step sequencer."""
    project_path = Path(project_dir)
    project_file = project_path / "beat.json"
    
    if not project_file.exists():
        print(f"Error: Project file not found at {project_file}")
        return
        
    with open(project_file) as f:
        beat_data = json.load(f)
        
    track_notes = beat_data.get("tracks", {}).get(track_type)
    if not track_notes:
        print(f"Error: Track type '{track_type}' not found in project.")
        return
        
    conn = get_connection()
    try:
        conn.ensure_connected()
        # Select target channel in FL Studio
        print(f"Selecting FL Studio channel index {match_index}...")
        conn.send_command("channels.selectOne", {"index": match_index})
    except Exception as e:
        print(f"Warning: Could not select channel via MIDI: {e}")

    # Direct Step Sequencer path for Kick and Snare
    if track_type in ["kick", "snare"]:
        print(f"Programming '{track_type}' directly into the FL Studio Step Sequencer...")
        # 8 bars = 32 beats = 128 steps (16th notes)
        pattern = [False] * 128
        for note in track_notes:
            step_idx = int(round(note["time"] * 4))
            if 0 <= step_idx < 128:
                pattern[step_idx] = True
        
        try:
            res = conn.send_command("channels.setStepSequence", {"channel": match_index, "pattern": pattern})
            if res.get("success", False):
                print(f"SUCCESS: Programmed step sequence for '{track_type}' directly!")
                return
            else:
                print(f"MIDI step sequence command failed: {res.get('error')}. Falling back to Piano Roll script.")
        except Exception as e:
            print(f"Error sending step sequence: {e}. Falling back to Piano Roll script.")
        
    # Write notes request
    requests = [
        {"action": "clear"},
        {"action": "add_notes", "notes": track_notes}
    ]
    _write_request(requests)
    
    # Trigger key simulation
    trigger = get_trigger()
    trigger.trigger(delay=0) # run trigger
    print(f"SUCCESS: Sent '{track_type}' note request to FL Studio.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        run_generation()
    elif len(sys.argv) > 3 and sys.argv[1] == "--import":
        # python beat_maker.py --import <project_dir> <track_type> <match_index>
        run_import(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else:
        print("Usage:")
        print("  python beat_maker.py --generate")
        print("  python beat_maker.py --import <project_dir> <track_type> <match_index>")
