from __future__ import annotations
from typing import List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton
)
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPixmap, QPainter
from PySide6.QtCore import Qt, QRectF
import os
from ..models import Event, Character, Place

class TimelineGraphWidget(QGraphicsView):
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn, parent=None):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)  # <--- FIXED HERE

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        self.ROW_HEIGHT = 80
        self.LEFT_MARGIN = 150
        self.TOP_MARGIN = 80
        self.EVENT_SIZE = 36

        self.scale_factor = 1.0
        self._font = QFont()
        self._font.setPointSize(10)

    def refresh(self):
        self.scene.clear()
        events: List[Event] = self.get_events_fn()
        characters: List[Character] = self.get_characters_fn()
        places: List[Place] = self.get_places_fn()
        char_by_name: Dict[str, Character] = {c.name: c for c in characters}
        event_dates = sorted(set(ev.start_date for ev in events if ev.start_date))
        if not event_dates or not places:
            return

        n_dates = len(event_dates)
        n_places = len(places)
        timeline_width = max(800, n_dates * 180)
        timeline_height = self.TOP_MARGIN + n_places * self.ROW_HEIGHT + 200

        date_x: Dict[str, float] = {
            date: self.LEFT_MARGIN + i * ((timeline_width - self.LEFT_MARGIN) // max(1, n_dates-1))
            for i, date in enumerate(event_dates)
        }
        place_y: Dict[str, float] = {
            p.name: self.TOP_MARGIN + i * self.ROW_HEIGHT
            for i, p in enumerate(places)
        }

        for i, (pname, y) in enumerate(place_y.items()):
            rect = QRectF(0, y - self.ROW_HEIGHT//2, timeline_width + self.LEFT_MARGIN, self.ROW_HEIGHT)
            self.scene.addRect(rect, QPen(Qt.NoPen), QBrush(Qt.white))

        for date, x in date_x.items():
            self.scene.addLine(x, self.TOP_MARGIN-40, x, timeline_height-20, QPen(Qt.gray, 1, Qt.DashLine))
            txt = self.scene.addText(date, self._font)
            txt.setPos(x-32, self.TOP_MARGIN-60)
        for pname, y in place_y.items():
            label = self.scene.addText(pname, self._font)
            label.setDefaultTextColor(Qt.black)
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
                        color = QColor(char_by_name.get(charname, Character(name="", color="#aaa")).color)
                        color.setAlpha(120)
                        part_rect = QRectF(
                            rect.left() + idx*rect.width()/n_chars,
                            rect.top(),
                            rect.width()/n_chars,
                            rect.height()
                        )
                        self.scene.addRect(part_rect, QPen(Qt.black, 1), QBrush(color))
                else:
                    gray = QColor("#bbb")
                    gray.setAlpha(120)
                    self.scene.addRect(rect, QPen(Qt.black, 1), QBrush(gray))

                font_name = QFont(self._font)
                font_name.setPointSize(13)
                event_name = self.scene.addText(ev.title, font_name)
                event_name.setDefaultTextColor(QColor("#33ff66"))
                event_name.setPos(x - self.EVENT_SIZE/2, y + self.EVENT_SIZE/2 + 8)

                font_date = QFont(self._font)
                font_date.setPointSize(10)
                datetxt = f"{ev.start_date} - {ev.end_date}" if ev.end_date else ev.start_date
                date_item = self.scene.addText(datetxt, font_date)
                date_item.setDefaultTextColor(Qt.darkCyan)
                date_item.setPos(x - self.EVENT_SIZE/2, y + self.EVENT_SIZE/2 + 32)

                font_desc = QFont(self._font)
                font_desc.setPointSize(9)
                desc = ev.description if hasattr(ev, "description") else ""
                desc_item = self.scene.addText(desc, font_desc)
                desc_item.setDefaultTextColor(Qt.darkGray)
                desc_item.setPos(x - self.EVENT_SIZE/2, y + self.EVENT_SIZE/2 + 54)

                if self.scale_factor >= 2.0 and hasattr(ev, "images") and ev.images:
                    img_path = ev.images[0]
                    if not os.path.isabs(img_path):
                        img_path = os.path.join(os.getcwd(), img_path)
                    if os.path.exists(img_path):
                        pix = QPixmap(img_path)
                        if not pix.isNull():
                            pix = pix.scaled(int(self.EVENT_SIZE*2), int(self.EVENT_SIZE*2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            img_item = self.scene.addPixmap(pix)
                            img_item.setPos(x + self.EVENT_SIZE/2 + 18, y - self.EVENT_SIZE/2)

        self.setSceneRect(0, 0, timeline_width + self.LEFT_MARGIN, timeline_height)

    def zoom_in(self):
        self.scale(1.2, 1.2)
        self.scale_factor *= 1.2

    def zoom_out(self):
        self.scale(1/1.2, 1/1.2)
        self.scale_factor /= 1.2

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