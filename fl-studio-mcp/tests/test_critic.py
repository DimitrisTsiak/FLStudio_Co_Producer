"""Unit tests for the Critic-Generator loop music validation and auto-correction."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src folder to python path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fl_studio_mcp.utils.critic import parse_key_signature, validate_notes, correct_notes

def test_parse_key_signature():
    # Test valid keys
    assert parse_key_signature("D Phrygian") == (2, [0, 1, 3, 5, 7, 8, 10], "phrygian")
    assert parse_key_signature("F minor") == (5, [0, 2, 3, 5, 7, 8, 10], "minor")
    assert parse_key_signature("C Major") == (0, [0, 2, 4, 5, 7, 9, 11], "major")
    
    # Test flats and case sensitivity
    assert parse_key_signature("Bb Phrygian") == (10, [0, 1, 3, 5, 7, 8, 10], "phrygian")
    assert parse_key_signature("g# natural_minor") == (8, [0, 2, 3, 5, 7, 8, 10], "natural_minor")

    # Test invalid key
    assert parse_key_signature("invalid key") is None

def test_validate_notes_scale():
    # D Phrygian scale notes: D(62), Eb(63), F(65), G(67), A(69), Bb(70), C(72)
    valid_notes = [
        {"midi": 62, "duration": 1.0, "time": 0.0}, # D (Tonic)
        {"midi": 63, "duration": 1.0, "time": 1.0}, # Eb (in-scale)
        {"midi": 65, "duration": 1.0, "time": 2.0}, # F (in-scale)
    ]
    is_valid, errors, warnings = validate_notes(valid_notes, "low_piano", "D Phrygian")
    assert is_valid
    assert len(errors) == 0

    # Off-scale note: E (64) is not in D Phrygian
    invalid_notes = [
        {"midi": 62, "duration": 1.0, "time": 0.0},
        {"midi": 64, "duration": 1.0, "time": 1.0}, # E (off-scale)
    ]
    is_valid, errors, warnings = validate_notes(invalid_notes, "low_piano", "D Phrygian")
    assert not is_valid
    assert len(errors) == 1
    assert "out of the scale" in errors[0]

def test_validate_notes_range():
    # Kick must be exactly MIDI 60 (C4)
    invalid_kick = [{"midi": 61, "duration": 0.5, "time": 0.0}]
    is_valid, errors, warnings = validate_notes(invalid_kick, "kick")
    assert not is_valid
    assert any("must be strictly C4" in e for e in errors)

    # High piano should be high (e.g. 72-96), warning for low values
    low_high_piano = [{"midi": 50, "duration": 1.0, "time": 0.0}]
    is_valid, errors, warnings = validate_notes(low_high_piano, "high_piano")
    assert is_valid  # Warnings don't make it invalid
    assert any("outside typical high range" in w for w in warnings)

def test_validate_notes_timing():
    # Kick landing on 2nd 16th note step (0.25)
    invalid_kick_time = [{"midi": 60, "duration": 0.5, "time": 0.25}]
    is_valid, errors, warnings = validate_notes(invalid_kick_time, "kick")
    assert not is_valid
    assert any("lands on a 2nd or 4th 16th-note step" in e for e in errors)

    # Kick landing on beat 1 (0.0) or offbeat 8th note (0.5) is valid
    valid_kick_time = [
        {"midi": 60, "duration": 0.5, "time": 0.0},
        {"midi": 60, "duration": 0.5, "time": 0.5}
    ]
    is_valid, errors, warnings = validate_notes(valid_kick_time, "kick")
    assert is_valid
    assert len(errors) == 0

def test_validate_notes_overlap():
    # Overlapping notes on monophonic track (bass)
    overlapping_notes = [
        {"midi": 62, "duration": 1.0, "time": 0.0},
        {"midi": 65, "duration": 1.0, "time": 0.5}, # Overlaps since previous note ends at 1.0
    ]
    is_valid, errors, warnings = validate_notes(overlapping_notes, "bass")
    assert not is_valid
    assert any("Overlapping notes detected" in e for e in errors)

def test_correct_notes():
    # 1. Scale correction (D Phrygian scale notes. Root = D=62)
    # G# (68) is not in D Phrygian, closest should shift to A (69) or G (67)
    notes = [{"midi": 68, "duration": 1.0, "time": 0.0}]
    corrected = correct_notes(notes, "high_piano", "D Phrygian")
    assert corrected[0]["midi"] in (67, 69)

    # 2. Range correction (Kick forced to 60)
    kick_notes = [{"midi": 72, "duration": 0.5, "time": 0.0}]
    corrected_kick = correct_notes(kick_notes, "kick")
    assert corrected_kick[0]["midi"] == 60

    # 3. Timing correction (Kick at 0.25 quantized to nearest 8th note: 0.0 or 0.5)
    kick_timing = [{"midi": 60, "duration": 0.5, "time": 0.25}]
    corrected_timing = correct_notes(kick_timing, "kick")
    assert corrected_timing[0]["time"] in (0.0, 0.5)

    # 4. Overlap correction (Shortens previous note)
    overlapping = [
        {"midi": 62, "duration": 1.0, "time": 0.0},
        {"midi": 62, "duration": 1.0, "time": 0.5},
    ]
    corrected_overlap = correct_notes(overlapping, "bass")
    assert corrected_overlap[0]["duration"] == 0.5
    assert corrected_overlap[1]["time"] == 0.5
