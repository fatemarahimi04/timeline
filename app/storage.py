import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil

ROOT_DIR = Path.cwd()
PROJECTS_DIR = ROOT_DIR / "projects"
CURRENT_FILE = ROOT_DIR / ".current_project"

DEFAULT_CHARACTER = {
    "description": "",
    "color": "",
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

def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def get_current_project_name() -> str:
    if CURRENT_FILE.exists():
        return CURRENT_FILE.read_text(encoding="utf-8").strip() or "default"
    return "default"

def set_project(name: str) -> None:
    name = name.strip() or "default"
    _ensure_dir(PROJECTS_DIR)
    CURRENT_FILE.write_text(name, encoding="utf-8")
    _ensure_dir(get_project_dir())
    _ensure_dir(get_pictures_dir())
    # Se till att data.json finns
    df = get_data_file()
    if not df.exists():
        df.write_text(json.dumps({"characters": [], "places": [], "events": []}, indent=2, ensure_ascii=False), encoding="utf-8")

def get_project_dir(name: Optional[str] = None) -> Path:
    if name is None:
        name = get_current_project_name()
    return PROJECTS_DIR / name

def get_pictures_dir(name: Optional[str] = None) -> Path:
    return get_project_dir(name) / "pictures"

def get_data_file(name: Optional[str] = None) -> Path:
    return get_project_dir(name) / "data.json"

def list_projects() -> List[str]:
    _ensure_dir(PROJECTS_DIR)
    return sorted([p.name for p in PROJECTS_DIR.iterdir() if p.is_dir()])

def create_project(name: str) -> None:
    pd = get_project_dir(name)
    _ensure_dir(pd)
    _ensure_dir(pd / "pictures")
    df = pd / "data.json"
    if not df.exists():
        df.write_text(json.dumps({"characters": [], "places": [], "events": []}, indent=2, ensure_ascii=False), encoding="utf-8")

def delete_project(name: str) -> None:
    pd = get_project_dir(name)
    if pd.exists():
        shutil.rmtree(pd)

def rename_project(old: str, new: str) -> None:
    op = get_project_dir(old)
    np = get_project_dir(new)
    if not op.exists():
        raise FileNotFoundError(f"Project '{old}' not found")
    if np.exists():
        raise FileExistsError(f"Project '{new}' already exists")
    op.rename(np)

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
    _ensure_dir(PROJECTS_DIR)
    pd = get_project_dir()
    _ensure_dir(pd)
    df = get_data_file()
    if df.exists():
        try:
            state = json.loads(df.read_text(encoding="utf-8"))
            state["characters"] = [_patch_character(c) for c in state.get("characters", [])]
            state["places"]     = [_patch_place(p) for p in state.get("places", [])]
            state["events"]     = [_patch_event(e) for e in state.get("events", [])]
            return state
        except Exception:
            pass
    return {"characters": [], "places": [], "events": []}

def save_state(state: Dict[str, List[Dict[str, Any]]]) -> None:
    pd = get_project_dir()
    _ensure_dir(pd)
    (pd / "data.json").write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
