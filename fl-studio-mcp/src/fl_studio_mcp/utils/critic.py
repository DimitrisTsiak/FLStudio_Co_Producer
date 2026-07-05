"""Critic validation and auto-correction engine for music theory and track constraints."""

from __future__ import annotations

import math

# Note values to pitch class (0-11)
SEMITONES = {
    "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11,
    "DB": 1, "EB": 3, "GB": 6, "AB": 8, "BB": 10
}

# Scale intervals relative to tonic root (0)
SCALES = {
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "ionian": [0, 2, 4, 5, 7, 9, 11],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
}

def parse_key_signature(key: str) -> tuple[int, list[int], str] | None:
    """Parse key signature string (e.g. 'D Phrygian', 'F minor') into root pitch class and intervals.
    
    Returns:
        (root_pitch_class, scale_intervals, scale_name) or None if parsing fails
    """
    key = key.strip()
    parts = key.split()
    if not parts:
        return None
        
    root_name = parts[0].upper()
    # Normalize flats and sharps
    if len(root_name) > 1 and root_name[1] in ("#", "B"):
        # e.g., F# or Bb -> flat is represented as 'B' or 'b'
        root_name = root_name[0] + root_name[1]
    
    root_pc = SEMITONES.get(root_name)
    if root_pc is None:
        return None
        
    scale_name = "minor"
    if len(parts) > 1:
        scale_name = parts[1].lower()
        
    intervals = SCALES.get(scale_name, SCALES["minor"])
    return root_pc, intervals, scale_name

def get_nearest_in_scale(midi: int, root_pc: int, intervals: list[int]) -> int:
    """Find the nearest MIDI note that fits within the target scale."""
    for shift in [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6]:
        candidate = midi + shift
        candidate_pc = (candidate - root_pc) % 12
        if candidate_pc in intervals:
            return candidate
    return midi

def get_nearest_step_quantized(time: float, grid_ppq: int = 4) -> float:
    """Quantize time to the nearest grid step (e.g., 16th notes)."""
    return round(time * grid_ppq) / grid_ppq

def validate_notes(
    notes: list[dict], 
    track_type: str, 
    key_signature: str = "D Phrygian"
) -> tuple[bool, list[str], list[str]]:
    """Validate a list of notes against scale, range, timing, and overlap constraints.
    
    Returns:
        (is_valid, list_of_errors, list_of_warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []
    
    if not notes:
        return True, [], ["No notes provided for validation."]
        
    # Sort notes by start time
    sorted_notes = sorted(notes, key=lambda x: x.get("time", 0))
    
    # Parse key signature
    parsed = parse_key_signature(key_signature)
    if parsed is None:
        warnings.append(f"Could not parse key signature '{key_signature}'. Defaulting to D Phrygian scale checks.")
        root_pc, intervals, scale_name = 2, SCALES["phrygian"], "phrygian"
    else:
        root_pc, intervals, scale_name = parsed

    # 1. Scale Checks (only for melodic tracks: low_piano, high_piano, bass)
    if track_type in ("low_piano", "high_piano", "bass"):
        # For bass and low_piano, the scale is Phrygian
        # For high_piano, it should be in the corresponding minor scale (relative or parallel minor)
        target_intervals = intervals
        if track_type == "high_piano" and scale_name == "phrygian":
            # high piano should be in minor scale of the root note
            target_intervals = SCALES["minor"]
            
        for i, n in enumerate(sorted_notes):
            midi = n.get("midi")
            if midi is not None:
                pc = (midi - root_pc) % 12
                if pc not in target_intervals:
                    errors.append(
                        f"Note index {i} (MIDI {midi}, time {n.get('time')}) is out of the scale "
                        f"'{key_signature}' (Pitch Class {pc} not in {target_intervals})."
                    )

    # 2. Range Checks
    for i, n in enumerate(sorted_notes):
        midi = n.get("midi")
        if midi is None:
            continue
            
        if track_type == "kick":
            if midi != 60:
                errors.append(f"Kick note {i} is MIDI {midi}, but must be strictly C4 (60).")
                
        elif track_type == "snare":
            if midi != 60:
                errors.append(f"Snare note {i} is MIDI {midi}, but must be strictly C4 (60).")
                
        elif track_type == "hihat":
            # Reference is C5 (72)
            if abs(midi - 72) > 12:
                errors.append(f"Hi-hat note {i} (MIDI {midi}) is more than 1 octave away from standard C5 (72).")
                
        elif track_type == "low_piano":
            # Low range: 36 to 64
            if midi < 36 or midi > 64:
                warnings.append(f"Low piano note {i} (MIDI {midi}) is outside typical low range (36-64).")
                
        elif track_type == "bass":
            # Bass range: 48 to 72 (standard range, allow filler notes up to 84)
            if midi < 48 or midi > 84:
                warnings.append(f"Bass note {i} (MIDI {midi}) is outside typical bass range (48-84).")
                
        elif track_type == "high_piano":
            # High range: 68 to 96
            if midi < 68 or midi > 100:
                warnings.append(f"High piano note {i} (MIDI {midi}) is outside typical high range (68-100).")

    # 3. Timing and Rhythm Checks
    if track_type == "kick":
        for i, n in enumerate(sorted_notes):
            t = n.get("time", 0)
            # Check if kick hits on 2nd or 4th 16th note
            # 16th notes: 0.0, 0.25, 0.5, 0.75...
            step = int(round(t * 4))
            if step % 2 == 1:
                errors.append(f"Kick note {i} at time {t} lands on a 2nd or 4th 16th-note step, which reduces bounce.")

    elif track_type == "snare":
        # Check that snare primary hits are on the 3rd beat of each bar (beat_in_bar = 2.0)
        offbeats = 0
        for i, n in enumerate(sorted_notes):
            t = n.get("time", 0)
            beat_in_bar = t % 4.0
            if not math.isclose(beat_in_bar, 2.0, abs_tol=0.01):
                if t < 30.0: # not in the final bar fill zone
                    offbeats += 1
                    
        if offbeats > 2:
            warnings.append(f"Found {offbeats} snare note(s) on off-beats (excluding final bar fill), Memphis beats prefer snare on beat 3.")

    elif track_type == "low_piano":
        # Max 3 distinct pitches
        pitches = {n.get("midi") for n in sorted_notes if n.get("midi") is not None}
        if len(pitches) > 3:
            errors.append(f"Low piano pattern uses {len(pitches)} distinct notes, but must use maximum 3 to stay spaced out.")
            
        # First note must be tonic
        if sorted_notes:
            first_note = sorted_notes[0].get("midi")
            if first_note is not None and (first_note - root_pc) % 12 != 0:
                warnings.append(f"First note of low piano (MIDI {first_note}) is not the tonic root note.")
                
        # Tonic must be the most common note
        if sorted_notes:
            pitch_counts = {}
            for n in sorted_notes:
                p = n.get("midi")
                if p is not None:
                    pitch_counts[p] = pitch_counts.get(p, 0) + 1
            most_common = max(pitch_counts, key=pitch_counts.get)
            if (most_common - root_pc) % 12 != 0:
                warnings.append("The tonic root note is not the most frequent pitch in the low piano track.")

    # 4. Overlap / Polyphony Checks (Monophonic tracks: kick, bass)
    if track_type in ("kick", "bass"):
        for i in range(len(sorted_notes) - 1):
            curr_n = sorted_notes[i]
            next_n = sorted_notes[i + 1]
            curr_time = curr_n.get("time", 0)
            curr_dur = curr_n.get("duration", 0)
            next_time = next_n.get("time", 0)
            
            # Check overlap
            if curr_time + curr_dur > next_time + 0.001:
                errors.append(
                    f"Overlapping notes detected on monophonic track '{track_type}': "
                    f"Note {i} (time {curr_time}, duration {curr_dur}) overlaps with Note {i+1} (time {next_time})."
                )

    is_valid = len(errors) == 0
    return is_valid, errors, warnings

def correct_notes(
    notes: list[dict],
    track_type: str,
    key_signature: str = "D Phrygian"
) -> list[dict]:
    """Auto-correct a list of notes to conform to scale, range, timing, and overlap rules.
    
    Returns:
        A list of new corrected note dictionaries.
    """
    if not notes:
        return []
        
    corrected = [dict(n) for n in notes]
    
    # Parse key signature
    parsed = parse_key_signature(key_signature)
    if parsed is None:
        root_pc, intervals, scale_name = 2, SCALES["phrygian"], "phrygian"
    else:
        root_pc, intervals, scale_name = parsed

    # 1. Scale correction (melodic tracks)
    if track_type in ("low_piano", "high_piano", "bass"):
        target_intervals = intervals
        if track_type == "high_piano" and scale_name == "phrygian":
            target_intervals = SCALES["minor"]
            
        for n in corrected:
            midi = n.get("midi")
            if midi is not None:
                pc = (midi - root_pc) % 12
                if pc not in target_intervals:
                    n["midi"] = get_nearest_in_scale(midi, root_pc, target_intervals)

    # 2. Range correction (shift octaves ±12)
    for n in corrected:
        midi = n.get("midi")
        if midi is None:
            continue
            
        if track_type == "kick":
            n["midi"] = 60
            
        elif track_type == "snare":
            n["midi"] = 60
            
        elif track_type == "hihat":
            duration = n.get("duration", 0.25)
            if duration >= 0.25:
                n["midi"] = 72
            else:
                while n["midi"] < 60:
                    n["midi"] += 12
                while n["midi"] > 84:
                    n["midi"] -= 12
                    
        elif track_type == "low_piano":
            while n["midi"] < 36:
                n["midi"] += 12
            while n["midi"] > 64:
                n["midi"] -= 12
                
        elif track_type == "bass":
            max_r = 84 if n.get("velocity", 0.8) < 0.8 else 72
            while n["midi"] < 48:
                n["midi"] += 12
            while n["midi"] > max_r:
                n["midi"] -= 12
                
        elif track_type == "high_piano":
            while n["midi"] < 68:
                n["midi"] += 12
            while n["midi"] > 96:
                n["midi"] -= 12

    # 3. Timing and Rhythm corrections
    if track_type == "kick":
        for n in corrected:
            t = n.get("time", 0)
            step = int(round(t * 4))
            if step % 2 == 1:
                new_step = round(step / 2) * 2
                n["time"] = float(new_step / 4)

    # Sort corrected notes by time to handle overlaps
    corrected = sorted(corrected, key=lambda x: x.get("time", 0))

    # 4. Overlap corrections (kick, bass)
    if track_type in ("kick", "bass"):
        for i in range(len(corrected) - 1):
            curr_n = corrected[i]
            next_n = corrected[i + 1]
            curr_time = curr_n.get("time", 0)
            curr_dur = curr_n.get("duration", 0)
            next_time = next_n.get("time", 0)
            
            if curr_time + curr_dur > next_time:
                new_dur = max(0.125, next_time - curr_time)
                curr_n["duration"] = new_dur

    return corrected
