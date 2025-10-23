# Modern, clean timeline (bands start→end inclusive)
# + Shows event description and character avatars (with image if available)
from __future__ import annotations
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QDateEdit, QCheckBox, QSplitter
)
from PySide6.QtGui import (
    QColor, QPen, QBrush, QFont, QPixmap, QPainterPath, QPainter,
    QShortcut, QKeySequence
)
from PySide6.QtCore import Qt, QRectF, QDate, QSignalBlocker, QSize, Signal

from ..models import Event, Character, Place

# ---- layout / styling ----
ROW_H              = 84
LEFT_MARGIN        = 190
TOP_MARGIN         = 110
X_STEP_MIN         = 220

PLACE_PILL_H       = 36
PLACE_AVATAR       = 26
PLACE_PILL_PAD_X   = 10

BAND_RADIUS        = 14
BAND_STROKE        = 2.0
TITLE_SIZE         = 14
DATE_SIZE          = 12
DESC_SIZE          = 11

BG_COLOR        = QColor("#F7F8FB")
PANEL_COLOR     = QColor("#FFFFFF")
PANEL_BORDER    = QColor(225, 229, 240)
AXIS_COLOR      = QColor(196, 200, 214)
LINE_COLOR      = QColor(130, 150, 210, 200)

TEXT_PRIMARY    = QColor("#111827")
TEXT_SUBTLE     = QColor("#0F766E")
TEXT_DESC       = QColor("#374151")

PILL_BG         = QColor(255, 255, 255, 235)
PILL_STROKE     = QColor(215, 218, 230)

CHIP_SIZE       = 18
CHIP_GAP        = 6


# ---- helpers ---------------------------------------------------------------
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
    except Exception:
        return None

def _first_img(paths: List[str]) -> Optional[str]:
    for p in paths or []:
        if not p:
            continue
        if not os.path.isabs(p):
            p = os.path.join(os.getcwd(), p)
        if os.path.exists(p):
            return p
    return None

def _alpha(color: QColor, a: int) -> QColor:
    c = QColor(color)
    c.setAlpha(a)
    return c

def _mix(c: QColor, w: QColor, p: float) -> QColor:
    return QColor(
        int(c.red()   * (1-p) + w.red()   * p),
        int(c.green() * (1-p) + w.green() * p),
        int(c.blue()  * (1-p) + w.blue()  * p),
    )


# ---- view ------------------------------------------------------------------
class PrettyTimelineView(QGraphicsView):
    def __init__(
        self,
        get_events_fn: Callable[[], List[Event]],
        get_characters_fn: Callable[[], List[Character]],
        get_places_fn: Callable[[], List[Place]],
        get_selected_chars_fn: Callable[[], List[str]] | None = None,
        parent=None
    ):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn
        self.get_selected_chars_fn = get_selected_chars_fn or (lambda: [])

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setBackgroundBrush(QBrush(BG_COLOR))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.scale_factor = 1.0

        self._font = QFont("Segoe UI", 10)

    def minimumSizeHint(self) -> QSize:
        return QSize(420, 320)

    def _lod(self):
        z = self.scale_factor
        if z < 0.95:
            return {
                "tick_days": 28, "date_fmt": "%Y-%m",
                "band_h": 26, "thumb": 40,
                "show_desc": False, "max_chips": 0,
            }
        elif z < 1.25:
            return {
                "tick_days": 7, "date_fmt": "%Y-%m-%d",
                "band_h": 30, "thumb": 48,
                "show_desc": True,  # visa beskrivning i normal zoom
                "max_chips": 2,
            }
        else:
            return {
                "tick_days": 3, "date_fmt": "%Y-%m-%d",
                "band_h": 34, "thumb": 56,
                "show_desc": True,  # visa beskrivning i hög zoom
                "max_chips": 3,
            }

    def refresh(self):
        self.scene.clear()

        events: List[Event] = self.get_events_fn()
        characters: List[Character] = self.get_characters_fn()
        places: List[Place] = self.get_places_fn()
        selected_chars = set(self.get_selected_chars_fn() or [])

        L = self._lod()
        char_by_name: Dict[str, Character] = {c.name: c for c in characters}

        # samla datum
        dates: List[datetime] = []
        for e in events:
            s = _parse_date(getattr(e, "start_date", "") or "")
            if s:
                dates.append(s)
            t = _parse_date(getattr(e, "end_date", "") or "")
            if t:
                dates.append(t)
        dates = sorted(dates)

        vp_w = max(1000, self.viewport().width())
        vp_h = max(600, self.viewport().height())

        if not places or not dates:
            self.scene.setSceneRect(0, 0, vp_w, vp_h)
            _add_rounded_rect(self.scene, QRectF(20, 20, vp_w-40, vp_h-40), 14, QPen(PANEL_BORDER), QBrush(PANEL_COLOR))
            self.scene.addText("No data to display").setPos(LEFT_MARGIN, TOP_MARGIN)
            return

        dmin, dmax = min(dates), max(dates)
        dmin = dmin - timedelta(days=1)
        dmax = dmax + timedelta(days=1)

        step_px = max(X_STEP_MIN, 140)

        def day_width() -> float:
            return step_px / L["tick_days"]

        def x_for(dt: datetime) -> float:
            days = (dt - dmin).total_seconds() / 86400.0
            return LEFT_MARGIN + days * step_px / L["tick_days"]

        def band_span(s: datetime, e: Optional[datetime]) -> tuple[float, float]:
            xs = x_for(s)
            if e and e >= s:
                xe = x_for(e + timedelta(days=1))  # end inclusive
            else:
                xe = xs + max(day_width() * 0.75, 36.0)
            return xs, xe

        content_w = x_for(dmax) + 240
        content_h = TOP_MARGIN + len(places) * ROW_H + 140
        scene_w = max(content_w + 40, vp_w)
        scene_h = max(content_h + 40, vp_h)
        self.scene.setSceneRect(0, 0, scene_w, scene_h)

        # panel
        _add_rounded_rect(self.scene, QRectF(20, 20, scene_w-40, scene_h-40), 14, QPen(PANEL_BORDER), QBrush(PANEL_COLOR))

        # platsrader
        for i, p in enumerate(places):
            y = TOP_MARGIN + i * ROW_H
            y_mid = y + ROW_H/2
            self.scene.addLine(LEFT_MARGIN - 8, y_mid, scene_w - 60, y_mid, QPen(LINE_COLOR, 3.0))

            pill = QRectF(20, y_mid - PLACE_PILL_H/2, LEFT_MARGIN - 40, PLACE_PILL_H)
            _add_rounded_rect(self.scene, pill, PLACE_PILL_H/2, QPen(PILL_STROKE), QBrush(PILL_BG))
            name_x = pill.left() + PLACE_PILL_PAD_X

            imgp = _first_img(getattr(p, "images", []))
            if imgp:
                a_size = min(PLACE_AVATAR, pill.height() - 8)
                a_rect = QRectF(pill.left() + PLACE_PILL_PAD_X, pill.top() + (pill.height()-a_size)/2, a_size, a_size)
                _add_rounded_rect(self.scene, a_rect, a_size/2, QPen(QColor(0,0,0,20)), QBrush(Qt.white))
                pm = QPixmap(imgp)
                if not pm.isNull():
                    inner = a_rect.adjusted(3,3,-3,-3)
                    pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    pm_item = self.scene.addPixmap(pm)
                    pm_item.setPos(inner.left() + (inner.width()-pm.width())/2,
                                   inner.top() + (inner.height()-pm.height())/2)
                name_x = a_rect.right() + 8

            nm = self.scene.addText(p.name, QFont(self._font.family(), 11))
            nm.setDefaultTextColor(TEXT_PRIMARY)
            nm.setPos(name_x, pill.top() + (pill.height()-14)/2)

        # datum-ticks
        tick = dmin - timedelta(days=(dmin.weekday() % 7))
        while tick <= dmax:
            x = x_for(tick)
            if x >= LEFT_MARGIN - 5:
                self.scene.addLine(x, TOP_MARGIN - 32, x, scene_h - 60, QPen(AXIS_COLOR, 1, Qt.DashLine))
                txt = self.scene.addText(tick.strftime(L["date_fmt"]), QFont(self._font.family(), 12))
                txt.setDefaultTextColor(QColor(120, 120, 130))
                txt.setPos(x - 40, TOP_MARGIN - 56)
            tick += timedelta(days=L["tick_days"])

        # event-band
        for ev in events:
            sdt = _parse_date(getattr(ev, "start_date", "") or "")
            edt = _parse_date(getattr(ev, "end_date", "") or "")
            if not sdt:
                continue

            for place_name in getattr(ev, "places", []) or [""]:
                row_idx = next((i for i, pl in enumerate(places) if pl.name == place_name), None)
                if row_idx is None:
                    continue

                xs, xe = band_span(sdt, edt if edt and edt >= sdt else None)
                width = max(16.0, xe - xs)
                y_mid = TOP_MARGIN + row_idx * ROW_H + ROW_H/2
                band_h = L["band_h"]

                # färg från första karaktär
                base = QColor("#94A3B8")
                if ev.characters:
                    first = char_by_name.get(ev.characters[0])
                    if first:
                        try: base = QColor(first.color)
                        except Exception: pass
                fill  = _mix(base, QColor("#FFFFFF"), 0.65)
                edge  = QColor(base.darker(135))

                dim = 1.0
                selected_chars = set(self.get_selected_chars_fn() or [])
                if selected_chars and not (set(ev.characters or []) & selected_chars):
                    dim = 0.35
                fill = _alpha(fill, int(220*dim))
                edge = _alpha(edge, int(200*dim))

                band_rect = QRectF(xs, y_mid - band_h/2, width, band_h)

                glow = QRectF(band_rect); glow.translate(0, 3)
                _add_rounded_rect(self.scene, glow, BAND_RADIUS, QPen(Qt.NoPen), QBrush(_alpha(QColor(0,0,0), int(40*dim))))
                _add_rounded_rect(self.scene, band_rect, BAND_RADIUS, QPen(edge, BAND_STROKE), QBrush(fill))

                # event thumbnail (vänster i bandet)
                left_pad = 10.0
                ev_img = _first_img(getattr(ev, "images", []))
                if ev_img and band_h > 20:
                    a = min(band_h - 8, L["thumb"])
                    frame = QRectF(band_rect.left() + 8, band_rect.top() + (band_h - a)/2, a, a)
                    _add_rounded_rect(self.scene, frame, 6, QPen(QColor(0,0,0,25)), QBrush(Qt.white))
                    pm = QPixmap(ev_img)
                    if not pm.isNull():
                        inner = frame.adjusted(3,3,-3,-3)
                        pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        pm_item = self.scene.addPixmap(pm)
                        pm_item.setPos(inner.left() + (inner.width()-pm.width())/2,
                                       inner.top() + (inner.height()-pm.height())/2)
                    left_pad = frame.width() + 14

                # textblock
                title_font = QFont(self._font); title_font.setPointSize(TITLE_SIZE); title_font.setBold(True)
                date_font  = QFont(self._font);  date_font.setPointSize(DATE_SIZE)
                desc_font  = QFont(self._font);  desc_font.setPointSize(DESC_SIZE)

                tx_left = band_rect.left() + left_pad + 4
                tx_right = band_rect.right() - 8 - max(0, (L["max_chips"])*(CHIP_SIZE+CHIP_GAP)) - 6
                tx_w = max(20.0, tx_right - tx_left)

                # Build strings
                title_txt = ev.title or ""
                date_txt  = f"{ev.start_date}" + (f" – {ev.end_date}" if ev.end_date else "")
                desc_txt  = (ev.description or "").strip()

                # Title
                t_item = self.scene.addText(title_txt, title_font)
                t_item.setDefaultTextColor(_alpha(TEXT_PRIMARY, int(255*dim)))
                t_item.setTextWidth(tx_w)  # gör att Qt eliderar när smalt
                # Date
                d_item = self.scene.addText(date_txt, date_font)
                d_item.setDefaultTextColor(_alpha(TEXT_SUBTLE, int(255*dim)))
                d_item.setTextWidth(tx_w)
                # Description (en rad)
                if L["show_desc"] and desc_txt:
                    desc_item = self.scene.addText(desc_txt, desc_font)
                    desc_item.setDefaultTextColor(_alpha(TEXT_DESC, int(240*dim)))
                    desc_item.setTextWidth(tx_w)
                else:
                    desc_item = None

                # placera blocket centrerat vertikalt
                block_h = t_item.boundingRect().height() + d_item.boundingRect().height()
                if desc_item:
                    block_h += desc_item.boundingRect().height()
                cy = band_rect.top() + (band_h - block_h)/2
                t_item.setPos(tx_left, cy - 1)
                d_item.setPos(tx_left, t_item.pos().y() + t_item.boundingRect().height() - 2)
                if desc_item:
                    desc_item.setPos(tx_left, d_item.pos().y() + d_item.boundingRect().height() - 2)

                # character avatars (höger)
                cx_chip = band_rect.right() - 8 - CHIP_SIZE
                cy_chip = band_rect.top() + (band_h - CHIP_SIZE)/2
                for name in (ev.characters or [])[: L["max_chips"]]:
                    ch = char_by_name.get(name)
                    col = QColor("#A3A3A3")
                    imgp = None
                    if ch:
                        try: col = QColor(ch.color)
                        except Exception: pass
                        imgp = _first_img(getattr(ch, "images", []))

                    # bakgrundscirkel
                    circ = self.scene.addEllipse(cx_chip, cy_chip, CHIP_SIZE, CHIP_SIZE, QPen(Qt.NoPen), QBrush(_alpha(col, int(255*dim))))
                    circ.setZValue(20)
                    # bild om finns
                    if imgp:
                        pm = QPixmap(imgp)
                        if not pm.isNull():
                            inner = QRectF(cx_chip+2, cy_chip+2, CHIP_SIZE-4, CHIP_SIZE-4)
                            _add_rounded_rect(self.scene, inner, (CHIP_SIZE-4)/2, QPen(Qt.NoPen), QBrush(Qt.white))
                            pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                            pm_item = self.scene.addPixmap(pm)
                            pm_item.setPos(inner.left() + (inner.width()-pm.width())/2,
                                           inner.top() + (inner.height()-pm.height())/2)
                            pm_item.setZValue(21)
                    cx_chip -= (CHIP_SIZE + CHIP_GAP)

                # tooltip
                tips = [ev.title or "", date_txt]
                if desc_txt:
                    tips.append(desc_txt)
                if ev.characters:
                    tips.append("Characters: " + ", ".join(ev.characters))
                if ev.places:
                    tips.append("Places: " + ", ".join(ev.places))
                cover = self.scene.addRect(band_rect, QPen(Qt.NoPen), QBrush(Qt.transparent))
                cover.setToolTip("\n".join(tips))
                cover.setZValue(25)

    # --- zoom helpers --------------------------------------------------------
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

    def reset_zoom(self):
        self.resetTransform()
        self.scale_factor = 1.0
        self.refresh()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0: self.zoom_in()
            else: self.zoom_out()
            return
        super().wheelEvent(event)


# ---- Tab med filter & kontroller ------------------------------------------
class TimelineTab(QWidget):
    data_changed = Signal()

    def __init__(self, get_events_fn, get_characters_fn, get_places_fn):
        super().__init__()

        self._get_events_raw = get_events_fn
        self._get_characters = get_characters_fn
        self._get_places     = get_places_fn

        self.char_filter = QListWidget(); self.char_filter.setSelectionMode(QListWidget.MultiSelection)
        self.place_filter = QListWidget(); self.place_filter.setSelectionMode(QListWidget.MultiSelection)
        self.date_from = QDateEdit(); self.date_from.setCalendarPopup(True); self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_to   = QDateEdit(); self.date_to.setCalendarPopup(True);   self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.auto_dates = QCheckBox("Auto dates"); self.auto_dates.setChecked(True)

        self.apply_btn = QPushButton("Apply")
        self.clear_btn = QPushButton("Clear")
        self.zoomin_btn = QPushButton("+")
        self.zoomout_btn = QPushButton("-")

        self.graph = PrettyTimelineView(
            self._get_events_filtered,
            self._get_characters,
            self._get_places,
            get_selected_chars_fn=self._selected_chars
        )

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        left = QVBoxLayout(); left.addWidget(QLabel("Characters:")); left.addWidget(self.char_filter)
        mid  = QVBoxLayout(); mid.addWidget(QLabel("Places:"));     mid.addWidget(self.place_filter)
        right= QVBoxLayout(); right.addWidget(QLabel("From:"));     right.addWidget(self.date_from)
        right.addWidget(QLabel("To:")); right.addWidget(self.date_to)
        row1 = QHBoxLayout(); row1.addLayout(left,2); row1.addLayout(mid,2); row1.addLayout(right,1)
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

        # shortcuts
        QShortcut(QKeySequence("Ctrl++"), self, activated=self.graph.zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self, activated=self.graph.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self.graph.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.graph.reset_zoom)

        self._populate_filters()
        self._init_date_defaults()

        self.apply_btn.clicked.connect(self.refresh)
        self.clear_btn.clicked.connect(self._clear_filters)
        self.zoomin_btn.clicked.connect(self.graph.zoom_in)
        self.zoomout_btn.clicked.connect(self.graph.zoom_out)
        self.char_filter.itemSelectionChanged.connect(self._maybe_auto_dates)
        self.place_filter.itemSelectionChanged.connect(self._maybe_auto_dates)

        self.graph.refresh()

    # --- helpers -------------------------------------------------------------
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
        if f and s < f: return False
        if t and s > t: return False
        return True

    def _get_events_filtered(self) -> List[Event]:
        events = self._get_events_raw()
        sel_places = set(self._selected_places())
        def place_ok(e: Event): return True if not sel_places else bool(set(e.places) & sel_places)
        return [e for e in events if self._within_dates(e) and place_ok(e)]

    def _maybe_auto_dates(self):
        if not self.auto_dates.isChecked():
            return
        events = self._get_events_raw()
        sel_chars = set(self._selected_chars())
        sel_places = set(self._selected_places())
        dts: List[datetime] = []
        for e in events:
            d = _parse_date(e.start_date)
            if not d: continue
            if (not sel_chars or set(e.characters) & sel_chars) and (not sel_places or set(e.places) & sel_places):
                dts.append(d)
        with QSignalBlocker(self.date_from), QSignalBlocker(self.date_to):
            if dts:
                self.date_from.setDate(QDate.fromString(min(dts).strftime("%Y-%m-%d"), "yyyy-MM-dd"))
                self.date_to.setDate(QDate.fromString(max(dts).strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            else:
                today = QDate.currentDate()
                self.date_from.setDate(today); self.date_to.setDate(today)
        self.graph.refresh()

    def _clear_filters(self):
        self.char_filter.clearSelection()
        self.place_filter.clearSelection()
        self._init_date_defaults()
        self.refresh()

    def refresh(self):
        self._populate_filters()
        self.graph.refresh()
