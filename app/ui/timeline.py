from __future__ import annotations
from typing import List, Dict, Callable, Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QDateEdit, QCheckBox
)
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPixmap, QPainter
from PySide6.QtCore import Qt, QRectF, QDate, QUrl, QPointF, QSignalBlocker
import os

from ..models import Event, Character, Place


def _parse_date(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None

def _date_str(d: QDate) -> str:
    if not d.isValid():
        return ""
    return d.toString("yyyy-MM-dd")



class TimelineGraphWidget(QGraphicsView):
    def __init__(self, get_events_fn: Callable[[], List[Event]], get_characters_fn, get_places_fn, parent=None):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.ROW_HEIGHT = 90
        self.LEFT_MARGIN = 120
        self.TOP_MARGIN = 80
        self.TIMELINE_Y_OFFSET = 40
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
            self.setSceneRect(0, 0, 800, 400)
            return

        n_dates = len(event_dates)
        n_places = len(places)
        timeline_width = max(800, n_dates * 190)
        timeline_height = self.TOP_MARGIN + n_places * self.ROW_HEIGHT + 120

        date_x: Dict[str, float] = {
            date: self.LEFT_MARGIN + i * ((timeline_width - self.LEFT_MARGIN) // max(1, n_dates - 1))
            for i, date in enumerate(event_dates)
        }
        place_y: Dict[str, float] = {
            p.name: self.TOP_MARGIN + i * self.ROW_HEIGHT
            for i, p in enumerate(places)
        }

        self.scene.addRect(
            0, 0, timeline_width + self.LEFT_MARGIN, timeline_height,
            QPen(Qt.NoPen), QBrush(QColor(245, 245, 250))
        )

        for pname, y in place_y.items():
            line_y = y + self.TIMELINE_Y_OFFSET
            self.scene.addLine(
                self.LEFT_MARGIN - 20, line_y,
                timeline_width + self.LEFT_MARGIN - 20, line_y,
                QPen(QColor(100, 140, 200), 3)
            )
            label = self.scene.addText(pname, self._font)
            label.setDefaultTextColor(Qt.black)
            label.setPos(10, line_y - 18)

        for date, x in date_x.items():
            self.scene.addLine(x, self.TOP_MARGIN - 40, x, timeline_height - 20, QPen(QColor(190, 190, 210), 1, Qt.DashLine))
            txt = self.scene.addText(date, self._font)
            txt.setDefaultTextColor(QColor(120, 120, 120))
            txt.setPos(x - 34, self.TOP_MARGIN - 65)

        for ev in events:
            if not ev.start_date:
                continue
            for place in getattr(ev, 'places', []):
                if place not in place_y or ev.start_date not in date_x:
                    continue
                x = date_x[ev.start_date]
                y = place_y[place] + self.TIMELINE_Y_OFFSET
                rect = QRectF(x - self.EVENT_SIZE / 2, y - self.EVENT_SIZE / 2, self.EVENT_SIZE, self.EVENT_SIZE)

                self.scene.addLine(x, y, x, y - 24, QPen(QColor(120, 160, 120, 180), 2))

                if ev.characters:
                    n_chars = len(ev.characters)
                    for idx, charname in enumerate(ev.characters):
                        color_hex = char_by_name.get(charname, Character(name="", color="#aaa")).color
                        color = QColor(color_hex)
                        color.setAlpha(120)
                        part_rect = QRectF(
                            rect.left() + idx * rect.width() / n_chars,
                            rect.top(),
                            rect.width() / n_chars,
                            rect.height()
                        )
                        self.scene.addRect(part_rect, QPen(Qt.black, 1), QBrush(color))
                else:
                    gray = QColor("#bbb")
                    gray.setAlpha(120)
                    self.scene.addRect(rect, QPen(Qt.black, 1), QBrush(gray))

                font_name = QFont(self._font); font_name.setPointSize(13)
                event_name = self.scene.addText(ev.title, font_name)
                event_name.setDefaultTextColor(QColor("#cc7894"))
                event_name.setPos(x - self.EVENT_SIZE / 2, y - self.EVENT_SIZE / 2 - 32)

                font_date = QFont(self._font); font_date.setPointSize(10)
                datetxt = f"{ev.start_date} - {ev.end_date}" if ev.end_date else ev.start_date
                date_item = self.scene.addText(datetxt, font_date)
                date_item.setDefaultTextColor(Qt.darkCyan)
                date_item.setPos(x - self.EVENT_SIZE / 2, y - self.EVENT_SIZE / 2 - 10)

                font_desc = QFont(self._font); font_desc.setPointSize(9)
                desc = ev.description if hasattr(ev, "description") else ""
                desc_item = self.scene.addText(desc, font_desc)
                desc_item.setDefaultTextColor(Qt.darkGray)
                desc_item.setPos(x - self.EVENT_SIZE / 2, y + self.EVENT_SIZE / 2 + 8)

                if self.scale_factor >= 2.0 and getattr(ev, "images", None):
                    img_path = ev.images[0]
                    if not os.path.isabs(img_path):
                        img_path = os.path.join(os.getcwd(), img_path)
                    if os.path.exists(img_path):
                        pix = QPixmap(img_path)
                        if not pix.isNull():
                            pix = pix.scaled(int(self.EVENT_SIZE * 2), int(self.EVENT_SIZE * 2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            img_item = self.scene.addPixmap(pix)
                            img_item.setPos(x + self.EVENT_SIZE / 2 + 18, y - self.EVENT_SIZE / 2)

        self.setSceneRect(0, 0, timeline_width + self.LEFT_MARGIN, timeline_height)

    def zoom_in(self):
        self.scale(1.2, 1.2); self.scale_factor *= 1.2

    def zoom_out(self):
        self.scale(1/1.2, 1/1.2); self.scale_factor /= 1.2

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            self.zoom_in() if event.angleDelta().y() > 0 else self.zoom_out()
        else:
            super().wheelEvent(event)



class TimelineTab(QWidget):
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn):
        super().__init__()

        self.char_filter = QListWidget()
        self.char_filter.setSelectionMode(QListWidget.MultiSelection)

        self.place_filter = QListWidget()
        self.place_filter.setSelectionMode(QListWidget.MultiSelection)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")

        self.apply_btn = QPushButton("Apply")
        self.clear_btn = QPushButton("Clear")
        self.zoomin_btn = QPushButton("+")
        self.zoomout_btn = QPushButton("-")
        self.auto_dates = QCheckBox("Auto dates")
        self.auto_dates.setChecked(True)


        self._get_events_raw = get_events_fn
        self._get_characters = get_characters_fn
        self._get_places = get_places_fn
        self.graph = TimelineGraphWidget(self._get_events_filtered, self._get_characters, self._get_places)

        self._populate_filters()

        filt_row1 = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Characters (multi-select):"))
        left.addWidget(self.char_filter)
        mid = QVBoxLayout()
        mid.addWidget(QLabel("Places (multi-select):"))
        mid.addWidget(self.place_filter)
        right = QVBoxLayout()
        right.addWidget(QLabel("Date from:"))
        right.addWidget(self.date_from)
        right.addWidget(QLabel("Date to:"))
        right.addWidget(self.date_to)
        btns = QHBoxLayout()
        btns.addWidget(self.apply_btn)
        btns.addWidget(self.clear_btn)
        btns.addWidget(self.auto_dates)
        btns.addStretch(1)
        btns.addWidget(self.zoomin_btn)
        btns.addWidget(self.zoomout_btn)

        top = QHBoxLayout()
        top.addLayout(left, 2)
        top.addLayout(mid, 2)
        top.addLayout(right, 1)

        self.apply_btn.clicked.connect(self.refresh)
        self.clear_btn.clicked.connect(self._clear_filters)
        self.zoomin_btn.clicked.connect(self.graph.zoom_in)
        self.zoomout_btn.clicked.connect(self.graph.zoom_out)
        self.char_filter.itemSelectionChanged.connect(self._maybe_auto_dates)
        self.place_filter.itemSelectionChanged.connect(self._maybe_auto_dates)
        

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(btns)
        layout.addWidget(self.graph)

        self._init_date_defaults()
        self.graph.refresh()


    def _populate_filters(self):
        with QSignalBlocker(self.char_filter):
            self.char_filter.clear()
            for c in self._get_characters():
                self.char_filter.addItem(QListWidgetItem(c.name))

        with QSignalBlocker(self.place_filter):
            self.place_filter.clear()
            for p in self._get_places():
                self.place_filter.addItem(QListWidgetItem(p.name))


    def _init_date_defaults(self):
        dates = [_parse_date(e.start_date) for e in self._get_events_raw() if e.start_date]
        dates = [d for d in dates if d]
        if not dates:
            today = QDate.currentDate()
            with QSignalBlocker(self.date_from), QSignalBlocker(self.date_to):
                self.date_from.setDate(today)
                self.date_to.setDate(today)
            return
        dmin, dmax = min(dates), max(dates)
        with QSignalBlocker(self.date_from), QSignalBlocker(self.date_to):
            self.date_from.setDate(QDate.fromString(dmin.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            self.date_to.setDate(QDate.fromString(dmax.strftime("%Y-%m-%d"), "yyyy-MM-dd"))

    def _maybe_auto_dates(self):
        if not self.auto_dates.isChecked():
            return

        events = self._get_events_raw()
        sel_chars = set(self._selected_chars())
        sel_places = set(self._selected_places())

        def char_ok(ev: Event) -> bool:
            return True if not sel_chars else bool(set(ev.characters) & sel_chars)

        def place_ok(ev: Event) -> bool:
            return True if not sel_places else bool(set(ev.places) & sel_places)

        from datetime import datetime
        dates: list[datetime] = []
        for ev in events:
            if not ev.start_date:
                continue
            if char_ok(ev) and place_ok(ev):
                d = _parse_date(ev.start_date)
                if d:
                    dates.append(d)

        if not dates:
            today = QDate.currentDate()
            with QSignalBlocker(self.date_from), QSignalBlocker(self.date_to):
                self.date_from.setDate(today)
                self.date_to.setDate(today)
            self.graph.refresh()
            return

        dmin, dmax = min(dates), max(dates)
        with QSignalBlocker(self.date_from), QSignalBlocker(self.date_to):
            self.date_from.setDate(QDate.fromString(dmin.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            self.date_to.setDate(QDate.fromString(dmax.strftime("%Y-%m-%d"), "yyyy-MM-dd"))

        self.graph.refresh()



    def _selected_chars(self) -> List[str]:
        return [it.text() for it in self.char_filter.selectedItems()]

    def _selected_places(self) -> List[str]:
        return [it.text() for it in self.place_filter.selectedItems()]

    def _within_dates(self, ev: Event) -> bool:
        if not ev.start_date:
            return False
        s = _parse_date(ev.start_date)
        if not s:
            return False
        f = _parse_date(_date_str(self.date_from.date()))
        t = _parse_date(_date_str(self.date_to.date()))
        if f and s < f:
            return False
        if t and s > t:
            return False
        return True

    def _get_events_filtered(self) -> List[Event]:
        events = self._get_events_raw()
        sel_chars = set(self._selected_chars())
        sel_places = set(self._selected_places())

        def char_ok(ev: Event) -> bool:
            if not sel_chars:
                return True
            return bool(set(ev.characters) & sel_chars)

        def place_ok(ev: Event) -> bool:
            if not sel_places:
                return True
            return bool(set(ev.places) & sel_places)

        return [
            ev for ev in events
            if self._within_dates(ev) and char_ok(ev) and place_ok(ev)
        ]

    def _clear_filters(self):
        self.char_filter.clearSelection()
        self.place_filter.clearSelection()
        if self.auto_dates.isChecked():
            self._init_date_defaults()
        else:
            self._init_date_defaults()
        self.refresh()

    def refresh(self):
        self._populate_filters()
        self.graph.refresh()
