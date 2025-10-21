from __future__ import annotations
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QDateEdit, QCheckBox, QSplitter
)
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPixmap, QPainterPath, QPainter
from PySide6.QtCore import Qt, QRectF, QDate, QSignalBlocker, QSize

from ..models import Event, Character, Place

# ---- styling / layout ----
ROW_H           = 100
LEFT_MARGIN     = 180
TOP_MARGIN      = 100
EVENT_RADIUS    = 12
EVENT_PADDING   = 12
X_STEP_MIN      = 210

BG_COLOR        = QColor("#F7F8FB")
PANEL_COLOR     = QColor("#FFFFFF")
PANEL_BORDER    = QColor(220, 224, 236)
AXIS_COLOR      = QColor(190, 195, 210)
TIMELINE_COLOR  = QColor(120, 150, 210)

TITLE_COLOR     = QColor("#1F2937")
DATE_COLOR      = QColor("#0F766E")
DESC_COLOR      = QColor("#374151")
CARD_BORDER     = QColor(90, 70, 50, 180)
SHADOW_COLOR    = QColor(0, 0, 0, 55)
CHIP_TEXT       = QColor(35, 35, 35)

PLACE_PILL_BG   = QColor(255, 255, 255, 210)
PLACE_PILL_STROKE = QColor(210, 210, 220)

# ---- helpers ----
def _add_rounded_rect(scene: QGraphicsScene, rect: QRectF, radius: float, pen: QPen, brush: QBrush):
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return scene.addPath(path, pen, brush)

def _parse_date(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None

def _elide(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"

def _elide_to_width(text: str, px_width: int, approx_char_px: int = 7) -> str:
    if px_width <= 0:
        return ""
    max_chars = max(1, px_width // approx_char_px)
    return _elide(text, max_chars)

def _first_existing_image(paths: List[str]) -> Optional[str]:
    for p in paths or []:
        if not os.path.isabs(p):
            p = os.path.join(os.getcwd(), p)
        if os.path.exists(p):
            return p
    return None

# ---- view ----
class PrettyTimelineView(QGraphicsView):
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn, parent=None):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(BG_COLOR))
        self.scale_factor = 1.0

        self._font = QFont("Segoe UI")
        self._font.setPointSize(10)
        self.setMouseTracking(True); self.viewport().setMouseTracking(True)

    def minimumSizeHint(self) -> QSize:
        return QSize(400, 300)

    def _lod(self):
        z = self.scale_factor
        if z < 0.95:
            return {
                "tick_days": 28,
                "date_fmt": "%Y-%m",
                "show_image": True,
                "thumb": 44,
                "title_mode": "none",
                "show_date": False,
                "show_desc": False,
                "wrap_desc": False,
                "max_chips": 0,
                "event_w": 220,
                "event_h": 72,
            }
        elif z < 1.20:
            return {
                "tick_days": 7,
                "date_fmt": "%Y-%m-%d",
                "show_image": True,
                "thumb": 52,
                "title_mode": "abbr3",
                "show_date": True,
                "show_desc": False,
                "wrap_desc": False,
                "max_chips": 2,
                "event_w": 250,
                "event_h": 86,
            }
        else:
            return {
                "tick_days": 3,
                "date_fmt": "%Y-%m-%d",
                "show_image": True,
                "thumb": 68,
                "title_mode": "full",
                "show_date": True,
                "show_desc": True,
                "wrap_desc": True,
                "max_chips": 4,
                "event_w": 310,
                "event_h": 108,
            }

    def refresh(self):
        self.scene.clear()
        events: List[Event] = self.get_events_fn()
        characters: List[Character] = self.get_characters_fn()
        places: List[Place] = self.get_places_fn()

        L = self._lod()
        EVENT_W_LOCAL = L["event_w"]
        EVENT_H_LOCAL = L["event_h"]
        TICK_DAYS = L["tick_days"]

        char_by_name: Dict[str, Character] = {c.name: c for c in characters}
        dates = sorted({_parse_date(e.start_date) for e in events if e.start_date})
        dates = [d for d in dates if d]

        vp_w = max(1000, self.viewport().width())
        vp_h = max(600,  self.viewport().height())

        if not places or not dates:
            self.scene.setSceneRect(0, 0, vp_w, vp_h)
            panel_rect = QRectF(20, 20, vp_w - 40, vp_h - 40)
            _add_rounded_rect(self.scene, panel_rect, 16, QPen(PANEL_BORDER), QBrush(PANEL_COLOR))
            self.scene.addText("No data to display").setPos(LEFT_MARGIN, TOP_MARGIN)
            return

        dmin, dmax = min(dates), max(dates)
        dmin = dmin - timedelta(days=1)
        dmax = dmax + timedelta(days=1)

        step_px = max(X_STEP_MIN, 140)

        def x_for(dt: datetime) -> float:
            days = (dt - dmin).days
            return LEFT_MARGIN + days * step_px / TICK_DAYS

        content_w = x_for(dmax) + 220
        content_h = TOP_MARGIN + len(places) * ROW_H + 140
        scene_w = max(content_w + 40, vp_w)
        scene_h = max(content_h + 40, vp_h)
        self.scene.setSceneRect(0, 0, scene_w, scene_h)

        # panel
        panel_rect = QRectF(20, 20, scene_w - 40, scene_h - 40)
        _add_rounded_rect(self.scene, panel_rect, 16, QPen(PANEL_BORDER), QBrush(PANEL_COLOR))

        # platsrader + pill + place-avatar
        for i, p in enumerate(places):
            y = TOP_MARGIN + i * ROW_H
            line_y = y + ROW_H / 2
            self.scene.addLine(LEFT_MARGIN - 10, line_y, scene_w - 60, line_y, QPen(TIMELINE_COLOR, 3))

            pill_rect = QRectF(20, line_y - 16, LEFT_MARGIN - 40, 28)
            _add_rounded_rect(self.scene, pill_rect, 12, QPen(PLACE_PILL_STROKE), QBrush(PLACE_PILL_BG))

            p_img = _first_existing_image(getattr(p, "images", []))
            name_x = pill_rect.left() + 10
            if p_img:
                avatar_rect = QRectF(pill_rect.left() + 8, pill_rect.top() + 4, 20, 20)
                _add_rounded_rect(self.scene, avatar_rect, 10, QPen(QColor(0,0,0,30)), QBrush(Qt.white))
                pm = QPixmap(p_img)
                if not pm.isNull():
                    inner = avatar_rect.adjusted(2, 2, -2, -2)
                    pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    pm_item = self.scene.addPixmap(pm)
                    pm_item.setPos(inner.left(), inner.top())
                name_x = avatar_rect.right() + 6

            name_item = self.scene.addText(_elide(p.name, 18), self._font)
            name_item.setDefaultTextColor(Qt.black)
            name_item.setPos(name_x, pill_rect.top() + 4)

        # datumtick
        tick = dmin - timedelta(days=(dmin.weekday() % 7))
        while tick <= dmax:
            x = x_for(tick)
            if x >= LEFT_MARGIN - 5:
                self.scene.addLine(x, TOP_MARGIN - 30, x, scene_h - 60, QPen(AXIS_COLOR, 1, Qt.DashLine))
                txt = self.scene.addText(tick.strftime(L["date_fmt"]), self._font)
                txt.setDefaultTextColor(QColor(120, 120, 130))
                txt.setPos(x - 40, TOP_MARGIN - 55)
            tick += timedelta(days=TICK_DAYS)

        # events
        for ev in events:
            sdt = _parse_date(ev.start_date)
            if not sdt:
                continue
            for place_name in getattr(ev, "places", []) or [""]:
                row_idx = next((i for i, pl in enumerate(places) if pl.name == place_name), None)
                if row_idx is None:
                    continue

                x = x_for(sdt)
                y_center = TOP_MARGIN + row_idx * ROW_H + ROW_H / 2

                raw_left = x - L["event_w"] / 2 if (L := self._lod()) else x - EVENT_W_LOCAL / 2
                # fallback values
                L = L if isinstance(L, dict) else self._lod()
                raw_left = x - L["event_w"] / 2
                min_left = LEFT_MARGIN
                max_left = scene_w - 60 - L["event_w"]
                rect_left = max(min_left, min(raw_left, max_left))
                rect = QRectF(rect_left, y_center - L["event_h"] / 2, L["event_w"], L["event_h"])

                shadow = QRectF(rect); shadow.translate(0, 4)
                _add_rounded_rect(self.scene, shadow, EVENT_RADIUS, QPen(Qt.NoPen), QBrush(SHADOW_COLOR))

                if ev.characters:
                    base_col = QColor(char_by_name.get(ev.characters[0], Character(name="", color="#9aa")).color)
                    bg = QColor(base_col); bg.setAlpha(255)
                    border = QColor(base_col.darker(140))
                else:
                    bg = QColor("#EFE7DE"); border = CARD_BORDER
                _add_rounded_rect(self.scene, rect, EVENT_RADIUS, QPen(border, 1.6), QBrush(bg))

                padding   = EVENT_PADDING
                text_left = rect.left() + padding

                # event-thumbnail (LOD)
                imgp = _first_existing_image(ev.images) if (L["show_image"] and ev.images) else None
                if imgp and L["thumb"] > 0:
                    frame = QRectF(rect.left() + padding,
                                   rect.top()  + (L["event_h"] - L["thumb"]) / 2,
                                   L["thumb"], L["thumb"])
                    _add_rounded_rect(self.scene, frame, 8, QPen(QColor(0,0,0,30)), QBrush(Qt.white))
                    pix = QPixmap(imgp)
                    if not pix.isNull():
                        inner = frame.adjusted(4, 4, -4, -4)
                        pix = pix.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        pm_item = self.scene.addPixmap(pix)
                        pm_item.setPos(inner.left(), inner.top())
                    text_left = frame.right() + 10

                text_right = rect.right() - (padding + 12)
                text_width = max(10, int(text_right - text_left))

                base_y   = rect.top() + 10
                next_y   = base_y

                # Title (LOD)
                title_mode = L.get("title_mode", "full")
                if title_mode != "none":
                    title_font = QFont(self._font); title_font.setPointSize(12); title_font.setBold(True)
                    if title_mode == "abbr3":
                        title_str = (ev.title or "").strip()[:3].upper()
                        t_item = self.scene.addText(_elide_to_width(title_str, text_width), title_font)
                        t_item.setDefaultTextColor(TITLE_COLOR)
                        t_item.setPos(text_left, base_y)
                        next_y = base_y + 22
                    else:  # full
                        t_item = self.scene.addText("")
                        t_item.setDefaultTextColor(TITLE_COLOR)
                        t_item.setFont(title_font)
                        # if QGraphicsSimpleTextItem / QGraphicsTextItem behavior differs, fallback to addText
                        t_item.setPlainText(ev.title or "")
                        t_item.setPos(text_left, base_y)
                        next_y = base_y + 24

                # Date (LOD)
                if L.get("show_date", False):
                    d_font = QFont(self._font); d_font.setPointSize(10)
                    date_text = f"{ev.start_date} – {ev.end_date}" if ev.end_date else (ev.start_date or "")
                    d_item = self.scene.addText(_elide_to_width(date_text, text_width), d_font)
                    d_item.setDefaultTextColor(DATE_COLOR)
                    d_item.setPos(text_left, next_y)
                    next_y += 20

                # Description (LOD)
                if L.get("show_desc", False):
                    desc_font = QFont(self._font); desc_font.setPointSize(10)
                    if L.get("wrap_desc", False):
                        desc = self.scene.addText("")
                        desc.setDefaultTextColor(DESC_COLOR)
                        desc.setFont(desc_font)
                        desc.setPlainText(ev.description or "")
                        desc.setPos(text_left, next_y)
                    else:
                        desc_text = _elide_to_width(ev.description or "", text_width)
                        desc = self.scene.addText(desc_text, desc_font)
                        desc.setDefaultTextColor(DESC_COLOR)
                        desc.setPos(text_left, next_y)

                # Character chips — show color swatch + name (not just initials)
                cx = rect.right() - padding - 12
                cy = rect.top() + padding + 10
                # We'll place chips from right to left. For each chip render swatch + name.
                for name in (ev.characters or [])[: L["max_chips"]]:
                    ch = char_by_name.get(name, Character(name=name, color="#888"))
                    col = QColor(ch.color)
                    # draw swatch (circle)
                    sw_size = 14
                    sw_rect = QRectF(cx - sw_size, cy - sw_size/2, sw_size, sw_size)
                    _add_rounded_rect(self.scene, sw_rect, sw_size/2, QPen(QColor(0,0,0,30)), QBrush(col)).setZValue(16)
                    # draw name to left of swatch
                    name_font = QFont(self._font.family(), 9)
                    # approximate width allowed for the name
                    max_name_px = 100
                    display = _elide_to_width(name, max_name_px)
                    name_item = self.scene.addText(display, name_font)
                    name_item.setDefaultTextColor(CHIP_TEXT)
                    # place name left of swatch, small padding
                    name_item_w = min(max_name_px, len(display) * 7)
                    name_item.setPos(sw_rect.left() - 6 - name_item_w, sw_rect.top() - 6)
                    name_item.setZValue(16)
                    # move cx left for next chip: include name width + swatch + spacing
                    cx = sw_rect.left() - 8 - name_item_w

    def zoom_in(self):
        step = 1.25
        self.scale(step, step)
        self.scale_factor *= step
        self.refresh()

    def zoom_out(self):
        step = 1.25
        self.scale(1/step, 1/step)
        self.scale_factor /= step
        self.refresh()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)

# ---- Tab with filters + splitter ----
class TimelineTab(QWidget):
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn):
        super().__init__()

        self.char_filter = QListWidget(); self.char_filter.setSelectionMode(QListWidget.MultiSelection)
        self.place_filter = QListWidget(); self.place_filter.setSelectionMode(QListWidget.MultiSelection)
        self.date_from = QDateEdit(); self.date_from.setCalendarPopup(True); self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_to   = QDateEdit(); self.date_to.setCalendarPopup(True);   self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.auto_dates = QCheckBox("Auto dates"); self.auto_dates.setChecked(True)

        self.apply_btn = QPushButton("Apply")
        self.clear_btn = QPushButton("Clear")
        self.zoomin_btn = QPushButton("+")
        self.zoomout_btn = QPushButton("-")

        self._get_events_raw = get_events_fn
        self._get_characters = get_characters_fn
        self._get_places     = get_places_fn

        self.graph = PrettyTimelineView(self._get_events_filtered, self._get_characters, self._get_places)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        left = QVBoxLayout(); left.addWidget(QLabel("Characters:")); left.addWidget(self.char_filter)
        mid  = QVBoxLayout();  mid.addWidget(QLabel("Places:"));     mid.addWidget(self.place_filter)
        right= QVBoxLayout();  right.addWidget(QLabel("From:"));     right.addWidget(self.date_from)
        right.addWidget(QLabel("To:")); right.addWidget(self.date_to)
        row1 = QHBoxLayout(); row1.addLayout(left, 2); row1.addLayout(mid, 2); row1.addLayout(right, 1)
        controls_layout.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(self.apply_btn); row2.addWidget(self.clear_btn); row2.addWidget(self.auto_dates)
        row2.addStretch(1); row2.addWidget(self.zoomin_btn); row2.addWidget(self.zoomout_btn)
        controls_layout.addLayout(row2)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(controls)
        splitter.addWidget(self.graph)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([220, 600])

        root = QVBoxLayout(self)
        root.addWidget(splitter)

        self._populate_filters()
        self._init_date_defaults()

        self.apply_btn.clicked.connect(self.refresh)
        self.clear_btn.clicked.connect(self._clear_filters)
        self.zoomin_btn.clicked.connect(self.graph.zoom_in)
        self.zoomout_btn.clicked.connect(self.graph.zoom_out)
        self.char_filter.itemSelectionChanged.connect(self._maybe_auto_dates)
        self.place_filter.itemSelectionChanged.connect(self._maybe_auto_dates)

        self.graph.refresh()

    def _populate_filters(self):
        with QSignalBlocker(self.char_filter):
            self.char_filter.clear()
            for c in self._get_characters():
                # add simple text item (keeps filter compact)
                self.char_filter.addItem(QListWidgetItem(c.name))
        with QSignalBlocker(self.place_filter):
            self.place_filter.clear()
            for p in self._get_places():
                self.place_filter.addItem(QListWidgetItem(p.name))

    def _init_date_defaults(self):
        dts = [_parse_date(e.start_date) for e in self._get_events_raw() if e.start_date]
        dts = [d for d in dts if d]
        today = QDate.currentDate()
        with QSignalBlocker(self.date_from), QSignalBlocker(self.date_to):
            if not dts:
                self.date_from.setDate(today); self.date_to.setDate(today)
            else:
                self.date_from.setDate(QDate.fromString(min(dts).strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                self.date_to.setDate(QDate.fromString(max(dts).strftime("%Y-%m-%d"), "yyyy-MM-dd"))

    def _selected_chars(self) -> List[str]:
        return [i.text() for i in self.char_filter.selectedItems()]

    def _selected_places(self) -> List[str]:
        return [i.text() for i in self.place_filter.selectedItems()]

    def _within_dates(self, ev: Event) -> bool:
        if not ev.start_date:
            return False
        s = _parse_date(ev.start_date)
        if not s:
            return False
        f = _parse_date(self.date_from.date().toString("yyyy-MM-dd"))
        t = _parse_date(self.date_to.date().toString("yyyy-MM-dd"))
        if f and s < f:
            return False
        if t and s > t:
            return False
        return True

    def _get_events_filtered(self) -> List[Event]:
        events = self._get_events_raw()
        sel_chars = set(self._selected_chars())
        sel_places = set(self._selected_places())

        def char_ok(e: Event):  return True if not sel_chars else bool(set(e.characters) & sel_chars)
        def place_ok(e: Event): return True if not sel_places else bool(set(e.places) & sel_places)

        return [e for e in events if self._within_dates(e) and char_ok(e) and place_ok(e)]

    def _maybe_auto_dates(self):
        if not self.auto_dates.isChecked():
            return
        events = self._get_events_raw()
        sel_chars = set(self._selected_chars())
        sel_places = set(self._selected_places())
        dts: List[datetime] = []
        for e in events:
            d = _parse_date(e.start_date)
            if not d:
                continue
            if (not sel_chars or set(e.characters) & sel_chars) and (not sel_places or set(e.places) & sel_places):
                dts.append(d)
        with QSignalBlocker(self.date_from), QSignalBlocker(self.date_to):
            if dts:
                self.date_from.setDate(QDate.fromString(min(dts).strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                self.date_to.setDate(QDate.fromString(max(dts).strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            else:
                today = QDate.currentDate()
                self.date_from.setDate(today)
                self.date_to.setDate(today)
        self.graph.refresh()

    def _clear_filters(self):
        self.char_filter.clearSelection()
        self.place_filter.clearSelection()
        self._init_date_defaults()
        self.refresh()

    def refresh(self):
        self._populate_filters()
        self.graph.refresh()