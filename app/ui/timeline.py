from __future__ import annotations
from typing import List, Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainter, QPixmap
from PySide6.QtCore import Qt, QRectF
import os
from ..models import Event, Character, Place

class TimelineGraphWidget(QGraphicsView):
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn, parent=None):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.base_event_size = 30
        self.event_size = 30
        self.zoom_factor = 1.0
        self.ROW_HEIGHT = 60
        self.LEFT_MARGIN = 120
        self.TOP_MARGIN = 60
        self._font = QFont()
        self._font.setPointSize(10)

    def refresh(self):
        self.scene().clear()
        events: List[Event] = self.get_events_fn()
        characters: List[Character] = self.get_characters_fn()
        places: List[Place] = self.get_places_fn()
        char_by_name: Dict[str, Character] = {c.name: c for c in characters}
        event_dates = sorted(set(ev.start_date for ev in events if ev.start_date))
        if not event_dates or not places:
            return

        n_dates = len(event_dates)
        n_places = len(places)
        timeline_width = max(600, n_dates * 90 * self.zoom_factor)
        timeline_height = self.TOP_MARGIN + n_places * self.ROW_HEIGHT * self.zoom_factor + 40

        date_x: Dict[str, float] = {
            date: self.LEFT_MARGIN + i * (timeline_width // max(1, n_dates-1))
            for i, date in enumerate(event_dates)
        }
        place_y: Dict[str, float] = {
            p.name: self.TOP_MARGIN + i * self.ROW_HEIGHT * self.zoom_factor
            for i, p in enumerate(places)
        }

        for date, x in date_x.items():
            self.scene().addLine(x, self.TOP_MARGIN-30, x, timeline_height-20, QPen(Qt.gray, 1, Qt.DashLine))
            txt = self.scene().addText(date, self._font)
            txt.setPos(x-24, self.TOP_MARGIN-50)
        for pname, y in place_y.items():
            self.scene().addLine(self.LEFT_MARGIN-10, y, timeline_width+self.LEFT_MARGIN-30, y, QPen(Qt.gray, 1))
            label = self.scene().addText(pname, self._font)
            label.setDefaultTextColor(Qt.darkBlue)
            label.setPos(10, y - self.event_size // 2)

        for ev in events:
            if not ev.start_date:
                continue
            for place in getattr(ev, 'places', []):
                if place not in place_y or ev.start_date not in date_x:
                    continue
                x = date_x[ev.start_date]
                y = place_y[place]
                event_size = self.event_size * self.zoom_factor
                rect = QRectF(x - event_size/2, y - event_size/2, event_size, event_size)
                if ev.characters:
                    n_chars = len(ev.characters)
                    for idx, charname in enumerate(ev.characters):
                        color = QColor(char_by_name.get(charname, Character(name="", color="#aaa")).color)
                        color.setAlpha(130)
                        part_rect = QRectF(
                            rect.left() + idx*rect.width()/n_chars,
                            rect.top(),
                            rect.width()/n_chars,
                            rect.height()
                        )
                        self.scene().addRect(part_rect, QPen(Qt.black, 1), QBrush(color))
                else:
                    gray = QColor("#bbb")
                    gray.setAlpha(130)
                    self.scene().addRect(rect, QPen(Qt.black, 1), QBrush(gray))

                font = QFont(self._font)
                font.setPointSize(int(10*self.zoom_factor))
                txt = self.scene().addText(ev.title, font)
                txt.setDefaultTextColor(Qt.black)
                txt.setPos(x - event_size/2, y + event_size/2 + 2)
                if self.zoom_factor >= 2.0:
                    desc = ev.description if hasattr(ev, "description") else ""
                    datetxt = f"{ev.start_date} - {ev.end_date}" if ev.end_date else ev.start_date
                    desc_item = self.scene().addText(desc, font)
                    desc_item.setDefaultTextColor(Qt.darkGray)
                    desc_item.setPos(x - event_size/2, y + event_size/2 + 18)
                    date_item = self.scene().addText(datetxt, font)
                    date_item.setDefaultTextColor(Qt.darkCyan)
                    date_item.setPos(x - event_size/2, y + event_size/2 + 36)
                    if hasattr(ev, "images") and ev.images:
                        img_path = ev.images[0]
                        if not os.path.isabs(img_path):
                            img_path = os.path.join(os.getcwd(), img_path)
                        if os.path.exists(img_path):
                            pix = QPixmap(img_path)
                            if not pix.isNull():
                                pix = pix.scaled(int(event_size), int(event_size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                img_item = self.scene().addPixmap(pix)
                                img_item.setPos(x - event_size/2, y - event_size/2)
        self.setSceneRect(0, 0, timeline_width+self.LEFT_MARGIN, timeline_height)

    def zoom_in(self):
        self.zoom_factor = min(self.zoom_factor * 1.5, 6.0)
        self.refresh()

    def zoom_out(self):
        self.zoom_factor = max(self.zoom_factor / 1.5, 0.5)
        self.refresh()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

class TimelineTab(QWidget):
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn):
        super().__init__()
        self.graph = TimelineGraphWidget(get_events_fn, get_characters_fn, get_places_fn)
        self.refresh_btn = QPushButton("Refresh")
        self.zoomin_btn = QPushButton("+")
        self.zoomout_btn = QPushButton("-")
        self.refresh_btn.clicked.connect(self.graph.refresh)
        self.zoomin_btn.clicked.connect(self.graph.zoom_in)
        self.zoomout_btn.clicked.connect(self.graph.zoom_out)
        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(self.refresh_btn)
        top.addWidget(self.zoomin_btn)
        top.addWidget(self.zoomout_btn)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.graph)
        self.graph.refresh()
    def refresh(self):
        self.graph.refresh()