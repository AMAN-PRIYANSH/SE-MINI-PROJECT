"""Best-model summary (Phase 3): the model that won the six-model comparison.

training/select_best_model.py writes training/best_model.json; the Web Server
reads it (cached for the process lifetime) and shows it as the headline result
next to every completed analysis. Returns None until the selection script has
run once, so a missing file is a normal state, not an error.
"""
import json
from pathlib import Path

BEST_MODEL_FILE = Path(__file__).resolve().parent.parent / "training" / "best_model.json"

_cache = None


def load_best_model():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(BEST_MODEL_FILE.read_text())
        except (FileNotFoundError, ValueError):
            _cache = False
    return _cache or None
