import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECTS_DIR = Path("projects")
CURRENT_PROJECT_NAME: Optional[str] = None

DEFAULT_CHARACTER = {
    "description": "",
    "color": "#3dc2da",
    "texts": [],
    "images": [],
}
DEFAULT_PLACE = {
    "description": "",
    "texts": [],
    "images": [],
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

def _project_dir(name: Optional[str] = None) -> Path:
    n = name or CURRENT_PROJECT_NAME or "default"
    return PROJECTS_DIR / n

def _data_dir() -> Path:
    return _project_dir()

def _data_file() -> Path:
    return _data_dir() / "data.json"

def get_project_dir() -> Path:
    """Publik: nuvarande projektmapp."""
    return _project_dir()

def get_pictures_dir() -> Path:
    """Publik: nuvarande projektets pictures/ (skapas vid behov)."""
    p = _project_dir() / "pictures"
    p.mkdir(parents=True, exist_ok=True)
    return p

def set_project(name: str) -> None:
    """Välj aktivt projekt (skapar mappen om den saknas)."""
    global CURRENT_PROJECT_NAME
    CURRENT_PROJECT_NAME = name
    d = _project_dir()
    d.mkdir(parents=True, exist_ok=True)
    if not _data_file().exists():
        save_state({"characters": [], "places": [], "events": []})

def list_projects() -> List[str]:
    """Lista alla projekt (mappar i projects/)."""
    if not PROJECTS_DIR.exists():
        return []
    return sorted([p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()])

def create_project(name: str) -> None:
    """Skapa ett nytt projekt med tomt state."""
    d = _project_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    f = d / "data.json"
    if not f.exists():
        f.write_text(json.dumps({"characters": [], "places": [], "events": []}, indent=2, ensure_ascii=False), encoding="utf-8")
    (d / "pictures").mkdir(exist_ok=True)

def delete_project(name: str) -> None:
    """Radera ett projekt (hela mappen)."""
    d = _project_dir(name)
    if d.exists():
        shutil.rmtree(d)

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
    dfile = _data_file()
    if dfile.exists():
        try:
            state = json.loads(dfile.read_text(encoding="utf-8"))
            state["characters"] = [_patch_character(c) for c in state.get("characters", [])]
            state["places"]     = [_patch_place(p)      for p in state.get("places", [])]
            state["events"]     = [_patch_event(e)      for e in state.get("events", [])]
            return state
        except Exception:
            pass
    return {"characters": [], "places": [], "events": []}

def save_state(state: Dict[str, List[Dict[str, Any]]]) -> None:
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    _data_file().write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
