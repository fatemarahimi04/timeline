import json #bibliotek för att konvertera objekt till json text
from pathlib import Path #API, path gör fil och kataloghantering tydligare.
from typing import Any, Dict, List #förklarar för läsare att vi returnerar och hanterar ordböcker med godtyckligt innehåll. 

DATA_DIR = Path("data") #s
DATA_FILE = DATA_DIR / "data.json"

def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_state() -> Dict[str, List[Dict[str, Any]]]:
    _ensure_dir()
    if DATA_FILE.exists():
        try:
            state = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            evs = state.get("events", [])
            for e in evs:
                if "date" not in e:
                    e["date"] = ""
            state["events"] = evs
            return state
        except Exception:
            pass
    return {"characters": [], "places": [], "events": []}

def save_state(state: Dict[str, List[Dict[str, Any]]]) -> None:
    _ensure_dir()
    DATA_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
