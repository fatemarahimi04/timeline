from __future__ import annotations
# Uppdaterad timeline: undvik att streckgubbar täcker datum — reservera chip-zon till höger
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QDateEdit, QCheckBox, QSplitter
)
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPixmap, QPainterPath, QPainter
from PySide6.QtCore import Qt, QRectF, QDate, QSignalBlocker, QSize, QPointF, QByteArray, QDataStream, Signal
from PySide6.QtWidgets import QGraphicsItem
from ..models import Event, Character, Place

# ---- styling / layout ----
ROW_H           = 100
LEFT_MARGIN     = 180
TOP_MARGIN      = 100
EVENT_RADIUS    = 12
EVENT_PADDING   = 12
X_STEP_MIN      = 210

# Place pill specifics
PLACE_PILL_HEIGHT = 36
PLACE_AVATAR_SIZE = 28
PLACE_PILL_PADDING = 10

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

PLACE_PILL_BG   = QColor(255, 255, 255, 230)
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

def _decode_qabstractitemmodeldatalist(mime) -> Optional[str]:
    fmt = "application/x-qabstractitemmodeldatalist"
    if not mime or not mime.hasFormat(fmt):
        return mime.text() if hasattr(mime, "text") else None
    data = mime.data(fmt)
    if not isinstance(data, QByteArray):
        return None
    ds = QDataStream(data)
    if ds.atEnd():
        return None
    ds.readInt32()  # row
    ds.readInt32()  # col
    items = {}
    while not ds.atEnd():
        role = ds.readInt32()
        value = ds.readQVariant()
        items[role] = value
    # DisplayRole = 0
    return str(items.get(0, "")).strip() or None


# ---- view ----
class PrettyTimelineView(QGraphicsView):
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn, on_event_changed=None, on_character_dropped=None, parent=None):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn
        self.on_event_changed = on_event_changed
        self.on_character_dropped = on_character_dropped

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
            return LEFT_MARGIN + days * step_px / L["tick_days"]
        
        def date_for_x(x: float) -> datetime:
            dayf = (x - LEFT_MARGIN) * L["tick_days"] / step_px
            return dmin + timedelta(days=int(round(dayf)))

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

            pill_rect = QRectF(20, line_y - (PLACE_PILL_HEIGHT / 2), LEFT_MARGIN - 40, PLACE_PILL_HEIGHT)
            _add_rounded_rect(self.scene, pill_rect, PLACE_PILL_HEIGHT/2, QPen(PLACE_PILL_STROKE), QBrush(PLACE_PILL_BG))

            p_img = _first_existing_image(getattr(p, "images", []))
            name_x = pill_rect.left() + PLACE_PILL_PADDING
            if p_img:
                avatar_size = min(PLACE_AVATAR_SIZE, pill_rect.height() - 6)
                avatar_rect = QRectF(pill_rect.left() + PLACE_PILL_PADDING,
                                     pill_rect.top() + (pill_rect.height() - avatar_size) / 2,
                                     avatar_size, avatar_size)
                _add_rounded_rect(self.scene, avatar_rect, avatar_size / 2, QPen(QColor(0,0,0,20)), QBrush(Qt.white))
                pm = QPixmap(p_img)
                if not pm.isNull():
                    inner = avatar_rect.adjusted(3, 3, -3, -3)
                    pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    px = inner.left() + (inner.width() - pm.width()) / 2
                    py = inner.top() + (inner.height() - pm.height()) / 2
                    pm_item = self.scene.addPixmap(pm)
                    pm_item.setPos(px, py)
                    pm_item.setZValue(12)
                name_x = avatar_rect.right() + 8

            name_font = QFont(self._font.family(), 11)
            name_item = self.scene.addText(_elide(p.name, 24), name_font)
            name_item.setDefaultTextColor(Qt.black)
            name_item.setPos(name_x, pill_rect.top() + (pill_rect.height() - 14) / 2)

        # datumtick
        tick = dmin - timedelta(days=(dmin.weekday() % 7))
        while tick <= dmax:
            x = x_for(tick)
            if x >= LEFT_MARGIN - 5:
                self.scene.addLine(x, TOP_MARGIN - 30, x, scene_h - 60, QPen(AXIS_COLOR, 1, Qt.DashLine))
                txt = self.scene.addText(tick.strftime(L["date_fmt"]), self._font)
                txt.setDefaultTextColor(QColor(120, 120, 130))
                txt.setPos(x - 40, TOP_MARGIN - 55)
            tick += timedelta(days=L["tick_days"])
        class EventCardItem(QGraphicsItem):
            def __init__(self, rect: QRectF, ev: Event, place_idx: int, parent_view: 'PrettyTimelineView'):
                super().__init__()
                self.rect = QRectF(rect)
                self.ev = ev
                self.place_idx = place_idx
                self.parent_view = parent_view
                self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsScenePositionChanges)
                self.setAcceptDrops(True)
                self.setZValue(30)

            def boundingRect(self) -> QRectF:
                return QRectF(self.rect)

            def paint(self, painter, option, widget=None):
                # Transparent overlay – själva kortet är redan ritat i scenen
                pass

            def itemChange(self, change, value):
                if change == QGraphicsItem.ItemPositionChange:
                    new_pos: QPointF = value
                    new_pos.setY(self.rect.top())  # lås Y till raden
                    return new_pos
                if change == QGraphicsItem.ItemPositionHasChanged:
                    try:
                        cx = self.pos().x() + self.rect.width()/2
                        new_dt = date_for_x(cx)
                        old_start = _parse_date(self.ev.start_date) or new_dt
                        dur = 0
                        if getattr(self.ev, "end_date", ""):
                            end = _parse_date(self.ev.end_date)
                            if end and old_start:
                                dur = (end - old_start).days
                        self.ev.start_date = new_dt.strftime("%Y-%m-%d")
                        if dur > 0:
                            self.ev.end_date = (new_dt + timedelta(days=dur)).strftime("%Y-%m-%d")
                        if callable(self.parent_view.on_event_changed):
                            self.parent_view.on_event_changed()
                    except Exception:
                        pass
                return super().itemChange(change, value)

            # --- drop av karaktär ---
            def dragEnterEvent(self, e):
                e.acceptProposedAction()

            def dragMoveEvent(self, e):
                e.acceptProposedAction()

            def dropEvent(self, e):
                name = _decode_qabstractitemmodeldatalist(e.mimeData())
                if name and name not in self.ev.characters:
                    self.ev.characters.append(name)
                    if callable(self.parent_view.on_character_dropped):
                        self.parent_view.on_character_dropped()
                e.acceptProposedAction()

        # events (cards)
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

                Lcur = L
                raw_left = x - Lcur["event_w"] / 2
                min_left = LEFT_MARGIN
                max_left = scene_w - 60 - Lcur["event_w"]
                rect_left = max(min_left, min(raw_left, max_left))
                rect = QRectF(rect_left, y_center - Lcur["event_h"] / 2, Lcur["event_w"], Lcur["event_h"])

                # shadow
                shadow = QRectF(rect); shadow.translate(0, 4)
                _add_rounded_rect(self.scene, shadow, EVENT_RADIUS, QPen(Qt.NoPen), QBrush(SHADOW_COLOR))

                # background color based on first character
                if ev.characters:
                    try:
                        base_col = QColor(char_by_name.get(ev.characters[0], Character(name="", color="#9aa")).color)
                    except Exception:
                        base_col = QColor("#9aa")
                    bg = QColor(base_col); bg.setAlpha(255)
                    border = QColor(base_col.darker(140))
                else:
                    bg = QColor("#EFE7DE"); border = CARD_BORDER
                _add_rounded_rect(self.scene, rect, EVENT_RADIUS, QPen(border, 1.6), QBrush(bg))

                padding   = EVENT_PADDING
                text_left = rect.left() + padding

                # Reserve a right-side chip area so text (title/date/desc) never overlaps chips/stickfigs
                n_chars = len(ev.characters or [])
                n_chips = min(n_chars, Lcur.get("max_chips", 4))
                # avatar size default for chips/stickfigures
                default_avatar = 18
                # approximate per-character width in chip area (avatar + spacing + optional name area)
                approx_per_char = int(default_avatar + 8 + 40)  # avatar + spacing + room for small name (if shown)
                # chip area limited to max fraction of card width
                max_chip_zone = int(rect.width() * 0.45)
                chip_area_width = min(max_chip_zone, max( (n_chips * approx_per_char), 0 ))
                # ensure a minimum chip area
                chip_area_width = max(chip_area_width, 48)

                # adjust text_right so text does not draw under chips
                text_right = rect.right() - (padding + 12 + chip_area_width)
                text_width = max(10, int(text_right - text_left))

                # event-thumbnail (left)
                imgp = _first_existing_image(ev.images) if (Lcur["show_image"] and ev.images) else None
                if imgp and Lcur["thumb"] > 0:
                    frame = QRectF(rect.left() + padding,
                                   rect.top()  + (Lcur["event_h"] - Lcur["thumb"]) / 2,
                                   Lcur["thumb"], Lcur["thumb"])
                    _add_rounded_rect(self.scene, frame, 8, QPen(QColor(0,0,0,30)), QBrush(Qt.white))
                    pix = QPixmap(imgp)
                    if not pix.isNull():
                        inner = frame.adjusted(4, 4, -4, -4)
                        pix = pix.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        pm_item = self.scene.addPixmap(pix)
                        px = inner.left() + (inner.width() - pix.width()) / 2
                        py = inner.top() + (inner.height() - pix.height()) / 2
                        pm_item.setPos(px, py)
                    text_left = frame.right() + 10

                base_y   = rect.top() + 10
                next_y   = base_y

                # title (elided in view) — full shown in tooltip
                title_mode = Lcur.get("title_mode", "full")
                if title_mode != "none":
                    title_font = QFont(self._font); title_font.setPointSize(12); title_font.setBold(True)
                    if title_mode == "abbr3":
                        t_item = self.scene.addText(_elide_to_width((ev.title or "").strip()[:3].upper(), text_width), title_font)
                        t_item.setDefaultTextColor(TITLE_COLOR)
                        t_item.setPos(text_left, base_y)
                        t_item.setZValue(20)  # ensure title is on top
                        next_y = base_y + 22
                    else:
                        t_item = self.scene.addText(_elide_to_width(ev.title or "", text_width), title_font)
                        t_item.setDefaultTextColor(TITLE_COLOR)
                        t_item.setPos(text_left, base_y)
                        t_item.setZValue(20)
                        next_y = base_y + 24

                # date
                if Lcur.get("show_date", False):
                    d_font = QFont(self._font); d_font.setPointSize(10)
                    date_text = f"{ev.start_date} – {ev.end_date}" if ev.end_date else (ev.start_date or "")
                    d_item = self.scene.addText(_elide_to_width(date_text, text_width), d_font)
                    d_item.setDefaultTextColor(DATE_COLOR)
                    d_item.setPos(text_left, next_y)
                    d_item.setZValue(20)  # make date clearly readable on top
                    next_y += 20

                # description
                if Lcur.get("show_desc", False):
                    desc_font = QFont(self._font); desc_font.setPointSize(10)
                    if Lcur.get("wrap_desc", False):
                        desc = self.scene.addText(_elide_to_width(ev.description or "", text_width))
                        desc.setDefaultTextColor(DESC_COLOR)
                        desc.setPos(text_left, next_y)
                        desc.setZValue(20)
                    else:
                        desc_text = _elide_to_width(ev.description or "", text_width)
                        desc = self.scene.addText(desc_text, desc_font)
                        desc.setDefaultTextColor(DESC_COLOR)
                        desc.setPos(text_left, next_y)
                        desc.setZValue(20)

                # draw chips / stickgubbar INTO the reserved chip zone at rightmost side
                chip_right_x = rect.right() - (padding + 6)  # starting x for chips (right edge)
                cx = chip_right_x
                cy = rect.top() + padding + 8

                # We'll draw from right to left inside chip_area_width
                sw_size = 12
                # If stickfigures (with names) are used, use a slightly larger avatar
                avatar_size = 18

                chars_to_draw = (ev.characters or [])[:Lcur.get("max_chips", 4)]
                # iterate and draw into reserved zone
                for name in chars_to_draw[::-1]:  # draw right-to-left so order matches left-to-right visually
                    ch = char_by_name.get(name, None)
                    # compute if we draw full stick figure (with name) or only small swatch; keep it compact
                    # here we draw compact swatch; if you want stickfigs with names, adjust widths accordingly
                    col = QColor("#888")
                    if ch:
                        try:
                            col = QColor(ch.color)
                        except Exception:
                            col = QColor("#888")
                    # small circular swatch
                    circ = self.scene.addEllipse(cx - sw_size, cy - sw_size/2, sw_size, sw_size, QPen(Qt.NoPen), QBrush(col))
                    circ.setZValue(12)
                    cx -= (sw_size + 6)

                # If you want stick figures (larger with names) instead of swatches, we can place them
                # in a dedicated row under or above the card instead — but for clarity and to avoid
                # covering text we keep the compact swatches in the chip zone.

                # tooltip: show full title, date and full list of characters & places
                tooltip_lines = []
                tooltip_lines.append(f"{ev.title or ''}")
                if ev.start_date:
                    if ev.end_date:
                        tooltip_lines.append(f"{ev.start_date} – {ev.end_date}")
                    else:
                        tooltip_lines.append(ev.start_date)
                if ev.characters:
                    tooltip_lines.append("Characters: " + ", ".join(ev.characters))
                if ev.places:
                    tooltip_lines.append("Places: " + ", ".join(ev.places))
                capture = self.scene.addRect(rect, QPen(Qt.NoPen), QBrush(Qt.transparent))
                capture.setToolTip("\n".join(tooltip_lines))
                capture.setZValue(19)

                mover = EventCardItem(rect, ev, row_idx, self)
                self.scene.addItem(mover)
                mover.setPos(rect.left(), rect.top())


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
    data_changed = Signal()

    def _on_event_changed(self):
        self.data_changed.emit()
        self.graph.refresh()

    def _on_character_dropped(self):
        self.data_changed.emit()
        self.graph.refresh()


    def __init__(self, get_events_fn, get_characters_fn, get_places_fn):
        super().__init__()

        self.char_filter = QListWidget(); self.char_filter.setSelectionMode(QListWidget.MultiSelection)
        self.char_filter.setDragEnabled(True)
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

        self.graph = PrettyTimelineView(
            self._get_events_filtered,
            self._get_characters,
            self._get_places,
            on_event_changed=self._on_event_changed,
            on_character_dropped=self._on_character_dropped
        )

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
        try:
            self._populate_filters()
            self.graph.refresh()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Timeline error", str(e))


    def _on_event_changed(self):
        self.data_changed.emit()
        self.graph.refresh()

    def _on_character_dropped(self):
        self.data_changed.emit()
        self.graph.refresh()


