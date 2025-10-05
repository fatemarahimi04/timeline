from __future__ import annotations
from typing import List, Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainter
from PySide6.QtCore import Qt, QRectF
from ..models import Event, Character, Place

class TimelineGraphWidget(QGraphicsView):
    """
    Shows a graphical timeline with y=place, x=time.
    Each event is a square in the matrix, filled with the selected characters' colors.
    """
    ROW_HEIGHT = 60
    LEFT_MARGIN = 120
    TOP_MARGIN = 60
    EVENT_SIZE = 30
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn, parent=None):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumHeight(350)
        self.setMinimumWidth(900)
        self._font = QFont()
        self._font.setPointSize(10)

    def refresh(self):
        events: List[Event] = self.get_events_fn()
        characters: List[Character] = self.get_characters_fn()
        places: List[Place] = self.get_places_fn()

        char_by_name: Dict[str, Character] = {c.name: c for c in characters}
        place_by_name: Dict[str, Place] = {p.name: p for p in places}

        event_dates = sorted(set(ev.start_date for ev in events if ev.start_date))
        if not event_dates or not places:
            self.scene().clear()
            return

        n_dates = len(event_dates)
        n_places = len(places)
        timeline_width = max(600, n_dates * 90)
        timeline_height = self.TOP_MARGIN + n_places * self.ROW_HEIGHT + 40

        date_x: Dict[str, float] = {
            date: self.LEFT_MARGIN + i * (timeline_width // max(1, n_dates-1))
            for i, date in enumerate(event_dates)
        }
        place_y: Dict[str, float] = {
            p.name: self.TOP_MARGIN + i * self.ROW_HEIGHT
            for i, p in enumerate(places)
        }

        self.scene().clear()
        for date, x in date_x.items():
            self.scene().addLine(x, self.TOP_MARGIN-30, x, timeline_height-20, QPen(Qt.gray, 1, Qt.DashLine))
            txt = self.scene().addText(date, self._font)
            txt.setPos(x-24, self.TOP_MARGIN-50)
        for pname, y in place_y.items():
            self.scene().addLine(self.LEFT_MARGIN-10, y, timeline_width+self.LEFT_MARGIN-30, y, QPen(Qt.gray, 1))
            label = self.scene().addText(pname, self._font)
            label.setDefaultTextColor(Qt.darkBlue)
            label.setPos(10, y - self.EVENT_SIZE // 2)

        for ev in events:
            if not ev.start_date:
                continue
            for place in getattr(ev, 'places', []):
                if place not in place_y or ev.start_date not in date_x:
                    continue
                x = date_x[ev.start_date]
                y = place_y[place]
                rect = QRectF(x - self.EVENT_SIZE/2, y - self.EVENT_SIZE/2, self.EVENT_SIZE, self.EVENT_SIZE)
                if ev.characters:
                    n_chars = len(ev.characters)
                    for idx, charname in enumerate(ev.characters):
                        color = QColor(char_by_name[charname].color) if charname in char_by_name else QColor("#aaa")
                        part_rect = QRectF(
                            rect.left() + idx*rect.width()/n_chars,
                            rect.top(),
                            rect.width()/n_chars,
                            rect.height()
                        )
                        self.scene().addRect(part_rect, QPen(Qt.black, 1), QBrush(color))
                else:
                    self.scene().addRect(rect, QPen(Qt.black, 1), QBrush(QColor("#bbb")))
                txt = self.scene().addText(ev.title, self._font)
                txt.setDefaultTextColor(Qt.black)
                txt.setPos(x - self.EVENT_SIZE/2, y + self.EVENT_SIZE/2 + 2)

class TimelineTab(QWidget):
    """
    Tab containing the graphical timeline and a refresh button.
    """
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn):
        super().__init__()
        self.graph = TimelineGraphWidget(get_events_fn, get_characters_fn, get_places_fn)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.graph.refresh)

        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(self.refresh_btn)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.graph)

    def refresh(self):
        self.graph.refresh()