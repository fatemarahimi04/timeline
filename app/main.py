import sys
from dataclasses import asdict
from PySide6.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QMessageBox, QDialog
from PySide6.QtGui import QShortcut, QKeySequence


from .models import Character, Place, Event
from .storage import load_state, save_state, set_project, list_projects
from .ui.tabs import CharactersTab, EventsTab, PlacesTab
from .ui.timeline import TimelineTab
from .ui.project_dialog import ProjectDialog

class MainWindow(QWidget):
    def __init__(self, state):
        super().__init__()
        self.setWindowTitle("timeline – Projects")
        self.resize(1000, 680)

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

        self.events_tab.data_changed.connect(self._save_now)
        self.chars_tab.data_changed.connect(self._save_now)
        self.places_tab.data_changed.connect(self._save_now)
        self.events_tab.data_changed.connect(self.timeline_tab.refresh)
        
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
        self.timeline_tab.refresh()

    def _update_events_places(self):
        self.events_tab.set_places([p.name for p in self.places_tab.values()])
        self.timeline_tab.refresh()

    def _save_now(self):
        state = {
            "characters": [asdict(c) for c in self.chars_tab.values()],
            "places": [asdict(p) for p in self.places_tab.values()],
            "events": [asdict(e) for e in self.events_tab.values()],
        }
        try:
            save_state(state)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Could not save data: {e}")


def main():
    app = QApplication(sys.argv)

    dlg = ProjectDialog()
    if dlg.exec() != QDialog.Accepted:
        sys.exit(0)

    name = dlg.selected_name()
    if not name:
        projects = list_projects()
        name = projects[0] if projects else "default"

    set_project(name)

    state = load_state()
    w = MainWindow(state)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
