from __future__ import annotations
from typing import List, Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainter, QPixmap, QMouseEvent, QWheelEvent
from PySide6.QtCore import Qt, QRectF, QPointF
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
        self.ROW_HEIGHT = 80
        self.LEFT_MARGIN = 150
        self.TOP_MARGIN = 80
        self._font = QFont()
        self._font.setPointSize(10)

        self._last_pan_point = None
        self.setDragMode(QGraphicsView.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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
        timeline_width = max(800, n_dates * 150 * self.zoom_factor)
        timeline_height = self.TOP_MARGIN + n_places * self.ROW_HEIGHT * self.zoom_factor + 120

        date_x: Dict[str, float] = {
            date: self.LEFT_MARGIN + i * (timeline_width // max(1, n_dates-1))
            for i, date in enumerate(event_dates)
        }
        place_y: Dict[str, float] = {
            p.name: self.TOP_MARGIN + i * self.ROW_HEIGHT * self.zoom_factor
            for i, p in enumerate(places)
        }

        for i, (pname, y) in enumerate(place_y.items()):
            rect = QRectF(0, y - self.ROW_HEIGHT // 2 * self.zoom_factor, timeline_width + self.LEFT_MARGIN, self.ROW_HEIGHT * self.zoom_factor)
            self.scene().addRect(rect, QPen(Qt.NoPen), QBrush(Qt.white))

        for date, x in date_x.items():
            self.scene().addLine(x, self.TOP_MARGIN-40, x, timeline_height-20, QPen(Qt.gray, 1, Qt.DashLine))
            txt = self.scene().addText(date, self._font)
            txt.setPos(x-32, self.TOP_MARGIN-60)
        for pname, y in place_y.items():
            label = self.scene().addText(pname, self._font)
            label.setDefaultTextColor(Qt.black)
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
                        color.setAlpha(120)
                        part_rect = QRectF(
                            rect.left() + idx*rect.width()/n_chars,
                            rect.top(),
                            rect.width()/n_chars,
                            rect.height()
                        )
                        self.scene().addRect(part_rect, QPen(Qt.black, 1), QBrush(color))
                else:
                    gray = QColor("#bbb")
                    gray.setAlpha(120)
                    self.scene().addRect(rect, QPen(Qt.black, 1), QBrush(gray))

                font_name = QFont(self._font)
                font_name.setPointSize(max(int(13*self.zoom_factor), 12))
                event_name = self.scene().addText(ev.title, font_name)
                event_name.setDefaultTextColor(QColor("#5dc677"))
                event_name.setPos(x - event_size/2, y + event_size/2 + 8)

                font_date = QFont(self._font)
                font_date.setPointSize(max(int(10*self.zoom_factor), 9))
                datetxt = f"{ev.start_date} - {ev.end_date}" if ev.end_date else ev.start_date
                date_item = self.scene().addText(datetxt, font_date)
                date_item.setDefaultTextColor(Qt.darkCyan)
                date_item.setPos(x - event_size/2, y + event_size/2 + 32)

                if self.zoom_factor >= 1.0:
                    font_desc = QFont(self._font)
                    font_desc.setPointSize(max(int(9*self.zoom_factor), 8))
                    desc = ev.description if hasattr(ev, "description") else ""
                    desc_item = self.scene().addText(desc, font_desc)
                    desc_item.setDefaultTextColor(Qt.darkGray)
                    desc_item.setPos(x - event_size/2, y + event_size/2 + 54)

                if self.zoom_factor >= 2.0 and hasattr(ev, "images") and ev.images:
                    img_path = ev.images[0]
                    if not os.path.isabs(img_path):
                        img_path = os.path.join(os.getcwd(), img_path)
                    if os.path.exists(img_path):
                        pix = QPixmap(img_path)
                        if not pix.isNull():
                            pix = pix.scaled(int(event_size*2), int(event_size*2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            img_item = self.scene().addPixmap(pix)
                            img_item.setPos(x + event_size/2 + 18, y - event_size/2)

        self.setSceneRect(0, 0, timeline_width+self.LEFT_MARGIN, timeline_height)

    def zoom_in(self):
        self.zoom_factor = min(self.zoom_factor * 1.5, 6.0)
        self.refresh()

    def zoom_out(self):
        self.zoom_factor = max(self.zoom_factor / 1.5, 0.5)
        self.refresh()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._last_pan_point = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._last_pan_point is not None:
            delta = event.pos() - self._last_pan_point
            self._last_pan_point = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._last_pan_point = None
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

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