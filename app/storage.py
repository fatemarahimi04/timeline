import json
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "data.json"

DEFAULT_CHARACTER = {
    "description": "",
    "color": "#3dc2da",
    "texts": [],
    "images": []
}
DEFAULT_PLACE = {
    "description": "",
    "texts": [],
    "images": []
}
DEFAULT_EVENT = {
    "start_date": "",
    "end_date": "",
    "images": [],
    "characters": [],
    "places": [],
    "description": "",
    "title": "",
}

def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _patch_character(c: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in DEFAULT_CHARACTER.items():
        if k not in c:
            c[k] = v
    return c

def _patch_place(p: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in DEFAULT_PLACE.items():
        if k not in p:
            p[k] = v
    return p

def _patch_event(e: Dict[str, Any]) -> Dict[str, Any]:
    if "start_date" not in e and "date" in e:
        e["start_date"] = e["date"]
        del e["date"]
    for k, v in DEFAULT_EVENT.items():
        if k not in e:
            e[k] = v
    return e

def load_state() -> Dict[str, List[Dict[str, Any]]]:
    _ensure_dir()
    if DATA_FILE.exists():
        try:
            state = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            state["characters"] = [_patch_character(c) for c in state.get("characters", [])]
            state["places"] = [_patch_place(p) for p in state.get("places", [])]
            state["events"] = [_patch_event(e) for e in state.get("events", [])]
            return state
        except Exception:
            pass
    return {
        "characters": [],
        "places": [],
        "events": []
    }

def save_state(state: Dict[str, List[Dict[str, Any]]]) -> None:
    _ensure_dir()
    DATA_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )