import sys
from dataclasses import asdict
from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QMessageBox, QDialog,
    QMenuBar, QMenu, QInputDialog
)
from PySide6.QtGui import QShortcut, QKeySequence, QDesktopServices, QAction
from PySide6.QtCore import QUrl

from .models import Character, Place, Event
from .storage import (
    load_state, save_state, set_project, list_projects,
    create_project, delete_project, rename_project,
    get_current_project_name, get_project_dir
)
from .ui.tabs import CharactersTab, EventsTab, PlacesTab
from .ui.timeline import TimelineTab
from .ui.project_dialog import ProjectDialog


class MainWindow(QWidget):
    def __init__(self, state):
        super().__init__()
        self.setWindowTitle(f"timeline – {get_current_project_name()}")
        self.resize(1000, 680)

        self.menu_bar = QMenuBar(self)
        self._build_menu()

        self.tabs = QTabWidget()
        self._load_state_into_ui(state)

        layout = QVBoxLayout(self)
        layout.setMenuBar(self.menu_bar)
        layout.addWidget(self.tabs)

        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save_now)

    def _load_state_into_ui(self, state):
        """
        Load data into tabs and wire signals.
        This version is robust to timeline API changes and avoids duplicate signal hookups.
        """
        print("🟢 _load_state_into_ui start")
        self.tabs.clear()

        characters = [Character(**c) for c in state.get("characters", [])]
        places = [Place(**p) if not isinstance(p, Place) else p for p in state.get("places", [])]
        events = [Event(**e) for e in state.get("events", [])]

        print(f"Characters: {len(characters)}, Places: {len(places)}, Events: {len(events)}")

        # Create tabs
        self.chars_tab = CharactersTab(characters)
        self.places_tab = PlacesTab(places)
        self.events_tab = EventsTab(events, characters=characters, places=places)

        # Timeline expects callables that return up-to-date lists
        self.timeline_tab = TimelineTab(
            self.events_tab.values,
            self.chars_tab.values,
            self.places_tab.values
        )

        # Wire up signals
        # Keep connections minimal and idempotent (avoid duplicate connections)
        try:
            # When characters change, update events' character lists and refresh timeline
            self.chars_tab.data_changed.connect(self._update_events_characters)
            self.chars_tab.data_changed.connect(self._save_now)

            # When places change, update events' place lists and refresh timeline
            self.places_tab.data_changed.connect(self._update_events_places)
            self.places_tab.data_changed.connect(self._save_now)

            # When events change, refresh timeline and save
            self.events_tab.data_changed.connect(self.timeline_tab.refresh)
            self.events_tab.data_changed.connect(self._save_now)

            # Timeline can emit data_changed (e.g. when interaction modifies placement)
            # Connect it to save. Use hasattr to be defensive if timeline implementation changes.
            if hasattr(self.timeline_tab, "data_changed"):
                try:
                    self.timeline_tab.data_changed.connect(self._save_now)
                except Exception:
                    # If the timeline signal signature changed, ignore and proceed
                    pass

        except Exception as e:
            # If wiring fails, show message but continue (so UI still opens)
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Signal wiring failed", f"Could not wire signals:\n{e}")

        # Add tabs to UI
        self.tabs.addTab(self.chars_tab, "Characters")
        self.tabs.addTab(self.places_tab, "Places")
        self.tabs.addTab(self.events_tab, "Events")
        self.tabs.addTab(self.timeline_tab, "Timeline")

        # Ensure timeline reflects current state
        try:
            self.timeline_tab.refresh()
        except Exception:
            # fallback: ignore refresh errors to avoid crash during startup
            pass

        print("🟢 _load_state_into_ui done")

    def _update_events_characters(self):
        # keep events' character lists in sync with characters tab
        try:
            self.events_tab.set_characters([c.name for c in self.chars_tab.values()])
            self.timeline_tab.refresh()
            self._save_now()
        except Exception:
            # don't crash UI; log instead
            import traceback
            traceback.print_exc()

    def _update_events_places(self):
        try:
            self.events_tab.set_places([p.name for p in self.places_tab.values()])
            self.timeline_tab.refresh()
            self._save_now()
        except Exception:
            import traceback
            traceback.print_exc()

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

    def closeEvent(self, event):
        # save on close
        self._save_now()
        event.accept()

    def _build_menu(self):
        m_project = QMenu("&Project", self)

        act_new = QAction("New…", self)
        act_open = QAction("Open…", self)
        act_rename = QAction("Rename…", self)
        act_delete = QAction("Delete…", self)
        act_open_folder = QAction("Open Project Folder", self)

        act_new.triggered.connect(self._project_new)
        act_open.triggered.connect(self._project_open)
        act_rename.triggered.connect(self._project_rename)
        act_delete.triggered.connect(self._project_delete)
        act_open_folder.triggered.connect(self._project_open_folder)

        m_project.addAction(act_new)
        m_project.addAction(act_open)
        m_project.addSeparator()
        m_project.addAction(act_rename)
        m_project.addAction(act_delete)
        m_project.addSeparator()
        m_project.addAction(act_open_folder)

        self.menu_bar.addMenu(m_project)

    def _project_new(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Invalid name", "Please enter a project name.")
            return
        try:
            create_project(name)
            set_project(name)
            self.setWindowTitle(f"timeline – {name}")
            self._load_state_into_ui(load_state())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Couldn't create project:\n{e}")

    def _project_open(self):
        dlg = ProjectDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.selected_name()
        if not name:
            avail = list_projects()
            if not avail:
                QMessageBox.information(self, "No projects", "No projects available.")
                return
            name = avail[0]
        set_project(name)
        self.setWindowTitle(f"timeline – {name}")
        self._load_state_into_ui(load_state())

    def _project_rename(self):
        current = get_current_project_name()
        new_name, ok = QInputDialog.getText(self, "Rename Project", "New name:", text=current)
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == current:
            return
        try:
            rename_project(current, new_name)
            set_project(new_name)
            self.setWindowTitle(f"timeline – {new_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Couldn't rename project:\n{e}")

    def _project_delete(self):
        from PySide6.QtWidgets import QMessageBox
        name = get_current_project_name()
        if QMessageBox.question(
            self, "Delete Project",
            f"Delete '{name}'?\nThis will remove the entire project folder including pictures.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            delete_project(name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Couldn't delete:\n{e}")
            return

        avail = list_projects()
        if not avail:
            create_project("default")
            set_project("default")
            self.setWindowTitle(f"timeline – default")
            self._load_state_into_ui(load_state())
            return

        dlg = ProjectDialog(self)
        if dlg.exec() != QDialog.Accepted:
            set_project(avail[0])
            self.setWindowTitle(f"timeline – {avail[0]}")
            self._load_state_into_ui(load_state())
            return

        name = dlg.selected_name() or avail[0]
        set_project(name)
        self.setWindowTitle(f"timeline – {name}")
        self._load_state_into_ui(load_state())

    def _project_open_folder(self):
        folder = get_project_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


def main():
    app = QApplication(sys.argv)

    projects = list_projects()
    if not projects:
        create_project("default")
        set_project("default")
        state = load_state()
        w = MainWindow(state)
        w.setWindowTitle("timeline – default")
        w.show()
        sys.exit(app.exec())

    dlg = ProjectDialog()
    try:
        dlg.raise_()
        dlg.activateWindow()
    except Exception:
        pass

    result = dlg.exec()

    if result == QDialog.Accepted and dlg.selected_name():
        name = dlg.selected_name()
    else:
        name = projects[0]

    set_project(name)

    state = load_state()
    w = MainWindow(state)
    w.setWindowTitle(f"timeline – {name}")
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()