import sys
from dataclasses import asdict
from PySide6.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QMessageBox

from .models import Character, Place, Event
from .storage import load_state, save_state
from .ui.tabs import CharactersTab, EventsTab, PlacesTab
from .ui.timeline import TimelineTab

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("timeline – MVP with Timeline")
        self.resize(900, 600)

        state = load_state()
        characters = [Character(**c) for c in state.get("characters", [])]
        places = [Place(**p) if not isinstance(p, Place) else p for p in state.get("places", [])]
        events = [Event(**e) for e in state.get("events", [])]

        self.tabs = QTabWidget()
        self.chars_tab = CharactersTab(characters)
        self.places_tab = PlacesTab(places)
        self.events_tab = EventsTab(events, characters=characters, places=places)
        self.timeline_tab = TimelineTab(self.events_tab.values, self.chars_tab.values, self.places_tab.values)

        self.chars_tab.data_changed.connect(self._update_events_characters)
        self.places_tab.data_changed.connect(self._update_events_places)

        self.tabs.addTab(self.chars_tab, "Characters")
        self.tabs.addTab(self.places_tab, "Places")
        self.tabs.addTab(self.events_tab, "Events")
        self.tabs.addTab(self.timeline_tab, "Timeline")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def closeEvent(self, event):
        state = {
            "characters": [asdict(c) for c in self.chars_tab.values()],
            "places": [asdict(p) for p in self.places_tab.values()],
            "events": [asdict(e) for e in self.events_tab.values()],
        }
        try:
            save_state(state)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Could not save data: {e}")
        event.accept()
    def _update_events_characters(self):
        self.events_tab.set_characters([c.name for c in self.chars_tab.values()])

    def _update_events_places(self):
        self.events_tab.set_places([p.name for p in self.places_tab.values()])
def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()