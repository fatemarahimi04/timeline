import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import asdict

from .models import Character, Place, Event
from .storage import load_state, save_state
from .ui.timeline import TimelineTab

# Placeholder Tkinter tabs – byt ut mot dina riktiga!
class CharactersTab(tk.Frame):
    def __init__(self, master, characters):
        super().__init__(master)
        self.characters = characters
        tk.Label(self, text="Characters tab (implementera själv)", font=("Arial", 16)).pack(pady=50)

class PlacesTab(tk.Frame):
    def __init__(self, master, places):
        super().__init__(master)
        self.places = places
        tk.Label(self, text="Places tab (implementera själv)", font=("Arial", 16)).pack(pady=50)

class EventsTab(tk.Frame):
    def __init__(self, master, events, characters=None, places=None):
        super().__init__(master)
        self.events = events
        tk.Label(self, text="Events tab (implementera själv)", font=("Arial", 16)).pack(pady=50)

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("timeline – MVP with Timeline")
        self.geometry("1200x700")

        state = load_state()
        self.characters = [Character(**c) for c in state.get("characters", [])]
        self.places = [Place(**p) if not isinstance(p, Place) else p for p in state.get("places", [])]
        self.events = [Event(**e) for e in state.get("events", [])]

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.chars_tab = CharactersTab(self, self.characters)
        self.places_tab = PlacesTab(self, self.places)
        self.events_tab = EventsTab(self, self.events, characters=self.characters, places=self.places)
        self.timeline_tab = TimelineTab(self, lambda: self.events, lambda: self.characters, lambda: self.places)

        self.notebook.add(self.chars_tab, text="Characters")
        self.notebook.add(self.places_tab, text="Places")
        self.notebook.add(self.events_tab, text="Events")
        self.notebook.add(self.timeline_tab, text="Timeline")

    def on_close(self):
        state = {
            "characters": [asdict(c) for c in self.characters],
            "places": [asdict(p) for p in self.places],
            "events": [asdict(e) for e in self.events],
        }
        try:
            save_state(state)
        except Exception as e:
            messagebox.showerror("Save failed", f"Could not save data: {e}")
        self.destroy()

if __name__ == "__main__":
    app = MainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()