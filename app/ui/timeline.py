import tkinter as tk
from tkinter import Canvas, Frame, Button
from PIL import Image, ImageTk
import os

class TimelineGraphWidget(Canvas):
    def __init__(self, master, get_events_fn, get_characters_fn, get_places_fn, **kwargs):
        super().__init__(master, bg="#f5f5fa", highlightthickness=0, **kwargs)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn

        self.LEFT_MARGIN = 150
        self.TOP_MARGIN = 70
        self.ROW_HEIGHT = 90
        self.EVENT_SIZE = 36
        self.zoom = 1.0

        self._drag_data = None  # For panning
        self._images = []       # Keep references to Tk images

        self.bind("<Configure>", lambda e: self.refresh())
        self.bind("<ButtonPress-1>", self._start_pan)
        self.bind("<B1-Motion>", self._pan)
        self.bind("<ButtonRelease-1>", self._end_pan)
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Control-MouseWheel>", self._on_zoom)

        # For Linux
        self.bind("<Button-4>", lambda e: self._on_zoom_linux(e, 1))
        self.bind("<Button-5>", lambda e: self._on_zoom_linux(e, -1))

    def _start_pan(self, event):
        self.scan_mark(event.x, event.y)

    def _pan(self, event):
        self.scan_dragto(event.x, event.y, gain=1)

    def _end_pan(self, event):
        pass

    def _on_mousewheel(self, event):
        # Normal scrolling (vertical)
        self.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_zoom(self, event):
        # Zoom with Ctrl+mousewheel
        direction = 1 if event.delta > 0 else -1
        self.zoom += 0.2 * direction
        self.zoom = min(max(self.zoom, 0.5), 4.0)
        self.refresh()

    def _on_zoom_linux(self, event, direction):
        # For Linux scroll events
        if event.state & 0x0004:  # Ctrl key mask
            self.zoom += 0.2 * direction
            self.zoom = min(max(self.zoom, 0.5), 4.0)
            self.refresh()

    def refresh(self, *_):
        self.delete("all")
        self._images = []
        events = self.get_events_fn()
        characters = self.get_characters_fn()
        places = self.get_places_fn()
        char_by_name = {c.name: c for c in characters}
        event_dates = sorted({ev.start_date for ev in events if ev.start_date})
        if not event_dates or not places:
            return

        n_dates = len(event_dates)
        n_places = len(places)
        timeline_width = max(800, n_dates * 180) * self.zoom
        timeline_height = self.TOP_MARGIN + n_places * self.ROW_HEIGHT * self.zoom + 200

        date_x = {date: self.LEFT_MARGIN + i * ((timeline_width - self.LEFT_MARGIN) // max(1, n_dates - 1))
                  for i, date in enumerate(event_dates)}
        place_y = {p.name: self.TOP_MARGIN + i * self.ROW_HEIGHT * self.zoom
                   for i, p in enumerate(places)}

        # White background
        self.create_rectangle(0, 0, timeline_width + self.LEFT_MARGIN, timeline_height, fill="#f5f5fa", width=0)

        # Timeline for each place
        for pname, y in place_y.items():
            line_y = y + 40 * self.zoom
            self.create_line(self.LEFT_MARGIN - 20, line_y, timeline_width + self.LEFT_MARGIN - 20, line_y, fill="#6496c8", width=3)
            self.create_text(10, line_y - 18, text=pname, anchor="w", font=("Arial", int(12 * self.zoom), "bold"), fill="#222")

        # Vertical date lines and labels
        for date, x in date_x.items():
            self.create_line(x, self.TOP_MARGIN - 40, x, timeline_height - 20, fill="#bcc", dash=(2, 2))
            self.create_text(x - 34, self.TOP_MARGIN - 65, text=date, anchor="nw", font=("Arial", int(10 * self.zoom)), fill="#888")

        # Draw events
        for ev in events:
            if not ev.start_date:
                continue
            for place in getattr(ev, 'places', []):
                if place not in place_y or ev.start_date not in date_x:
                    continue
                x = date_x[ev.start_date]
                y = place_y[place] + 40 * self.zoom
                s = self.EVENT_SIZE * self.zoom
                # Line from event to timeline
                self.create_line(x, y, x, y - 24 * self.zoom, fill="#78a078", width=2)
                # Event box
                if ev.characters:
                    n_chars = len(ev.characters)
                    for idx, charname in enumerate(ev.characters):
                        color = char_by_name.get(charname, None)
                        color = color.color if color else "#bbb"
                        self.create_rectangle(x - s/2 + idx*(s/n_chars), y - s/2,
                                             x - s/2 + (idx+1)*(s/n_chars), y + s/2,
                                             fill=color, outline="#333")
                else:
                    self.create_rectangle(x - s/2, y - s/2, x + s/2, y + s/2, fill="#bbb", outline="#333")
                # Title
                self.create_text(x, y - s/2 - 32 * self.zoom, text=ev.title, fill="#33ff66",
                                 font=("Arial", int(13 * self.zoom), "bold"))
                # Date
                datetxt = f"{ev.start_date} - {ev.end_date}" if ev.end_date else ev.start_date
                self.create_text(x, y - s/2 - 10 * self.zoom, text=datetxt, fill="#089",
                                 font=("Arial", int(10 * self.zoom)))
                # Desc
                self.create_text(x, y + s/2 + 8 * self.zoom, text=ev.description, fill="#444",
                                 font=("Arial", int(9 * self.zoom)), anchor="n")
                # Image (if zoomat in och finns)
                if s > 60 and hasattr(ev, "images") and ev.images:
                    img_path = ev.images[0]
                    if not os.path.isabs(img_path):
                        img_path = os.path.join(os.getcwd(), img_path)
                    if os.path.exists(img_path):
                        try:
                            img = Image.open(img_path)
                            img = img.resize((int(s*2), int(s*2)))
                            img_tk = ImageTk.PhotoImage(img)
                            self.create_image(x + s/2 + 18 * self.zoom, y - s/2, anchor="nw", image=img_tk)
                            self._images.append(img_tk)  # Keep reference
                        except Exception as err:
                            print("Kunde inte visa bild:", err)

        self.config(scrollregion=(0, 0, timeline_width + self.LEFT_MARGIN, timeline_height))

class TimelineTab(Frame):
    def __init__(self, master, get_events_fn, get_characters_fn, get_places_fn):
        super().__init__(master)
        # Buttons
        btn_frame = Frame(self)
        btn_frame.pack(fill="x", pady=3)
        Button(btn_frame, text="Refresh", command=self.refresh).pack(side="right")
        Button(btn_frame, text="+", command=self.zoom_in).pack(side="right")
        Button(btn_frame, text="-", command=self.zoom_out).pack(side="right")

        # Timeline canvas
        self.graph = TimelineGraphWidget(self, get_events_fn, get_characters_fn, get_places_fn, width=1100, height=500)
        self.graph.pack(fill="both", expand=True)

    def refresh(self):
        self.graph.refresh()
    def zoom_in(self):
        self.graph.zoom += 0.2
        self.graph.zoom = min(max(self.graph.zoom, 0.5), 4.0)
        self.graph.refresh()
    def zoom_out(self):
        self.graph.zoom -= 0.2
        self.graph.zoom = min(max(self.graph.zoom, 0.5), 4.0)
        self.graph.refresh()