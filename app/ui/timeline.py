# app/ui/timeline.py
# Fixed: defer on_change to avoid deleting items during mouseReleaseEvent (use QTimer.singleShot)
from __future__ import annotations
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsObject, QGraphicsItem,
    QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QLabel, QDateEdit, QCheckBox, QSplitter
)
from PySide6.QtGui import (
    QColor, QPen, QBrush, QFont, QPixmap, QPainterPath, QPainter, QKeySequence, QShortcut, QMouseEvent
)
from PySide6.QtCore import Qt, QRectF, QDate, QSignalBlocker, QSize, Signal, QTimer

from ..models import Event, Character, Place

# ---- styling / layout ----
ROW_H = 100
LEFT_MARGIN = 180
TOP_MARGIN = 100
EVENT_RADIUS = 12
EVENT_PADDING = 12
X_STEP_MIN = 210

PLACE_PILL_HEIGHT = 36
PLACE_AVATAR_SIZE = 28
PLACE_PILL_PADDING = 10

DEFAULT_CHAR_AVATAR = 26
AVATAR_SPACING = 8

BG_COLOR = QColor("#F7F8FB")
PANEL_COLOR = QColor("#FFFFFF")
PANEL_BORDER = QColor(220, 224, 236)
AXIS_COLOR = QColor(190, 195, 210)
TIMELINE_COLOR = QColor(120, 150, 210)

TITLE_COLOR = QColor("#1F2937")
DATE_COLOR = QColor("#0F766E")
DESC_COLOR = QColor("#374151")
CARD_BORDER = QColor(90, 70, 50, 180)
SHADOW_COLOR = QColor(0, 0, 0, 55)
CHIP_TEXT = QColor(35, 35, 35)

PLACE_PILL_BG = QColor(255, 255, 255, 230)
PLACE_PILL_STROKE = QColor(210, 210, 220)


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


def _format_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


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
        if not p:
            continue
        if not os.path.isabs(p):
            p = os.path.join(os.getcwd(), p)
        if os.path.exists(p):
            return p
    return None


class EventItem(QGraphicsObject):
    """
    Interactive graphics object for an Event. Movable horizontally; on release it updates the Event dates
    via provided conversion callbacks and calls on_change (deferred with QTimer.singleShot).
    """
    def __init__(
        self,
        ev: Event,
        characters: Dict[str, Character],
        x_to_date: Callable[[float], datetime],
        date_to_x: Callable[[datetime], float],
        on_change: Callable[[Event], None],
        lod_getter: Callable[[], dict],
        parent=None
    ):
        super().__init__(parent)
        self.ev = ev
        self.characters = characters
        self.x_to_date = x_to_date
        self.date_to_x = date_to_x
        self.on_change = on_change
        self._lod_getter = lod_getter

        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        self._drag_start_pos = None
        self._initial_x = 0.0
        self._rect = QRectF(0, 0, 120, 80)

    def boundingRect(self) -> QRectF:
        return self._rect.adjusted(-6, -6, 6, 6)

    def paint(self, painter: QPainter, option, widget=None):
        L = self._lod_getter()
        # shadow
        shadow = QRectF(self._rect)
        shadow.translate(0, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(SHADOW_COLOR))
        painter.drawRoundedRect(shadow, EVENT_RADIUS, EVENT_RADIUS)

        # background color / border
        if self.ev.characters:
            col = "#EFE7DE"
            try:
                ch0 = self.ev.characters[0]
                col = self.characters.get(ch0, Character(name="", color="#EFE7DE")).color
            except Exception:
                col = "#EFE7DE"
            bg = QColor(col)
        else:
            bg = QColor("#EFE7DE")
        bg.setAlpha(255)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(bg.darker(140), 1.6))
        painter.drawRoundedRect(self._rect, EVENT_RADIUS, EVENT_RADIUS)

        # content
        padding = EVENT_PADDING
        text_left = self._rect.left() + padding

        width = int(self._rect.width())
        show_thumb = width >= 120 and L.get("thumb", 44) > 0
        if show_thumb and self.ev.images:
            imgp = _first_existing_image(self.ev.images)
            if imgp:
                thumb_w = min(L.get("thumb", 44), max(40, int(self._rect.width() * 0.28)))
                frame = QRectF(self._rect.left() + padding,
                               self._rect.top() + (self._rect.height() - thumb_w) / 2,
                               thumb_w, thumb_w)
                painter.setBrush(QBrush(Qt.white))
                painter.setPen(QPen(QColor(0, 0, 0, 30)))
                painter.drawRoundedRect(frame, 8, 8)
                pm = QPixmap(imgp)
                if not pm.isNull():
                    pm = pm.scaled(int(thumb_w - 8), int(thumb_w - 8), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    px = frame.left() + (frame.width() - pm.width()) / 2 + 4
                    py = frame.top() + (frame.height() - pm.height()) / 2 + 4
                    painter.drawPixmap(int(px), int(py), pm)
                text_left = frame.right() + 12

        text_right = self._rect.right() - (padding + 12)
        text_width = max(10, int(text_right - text_left))

        # Title
        y = self._rect.top() + 12
        painter.setPen(TITLE_COLOR)
        title_font = QFont("Segoe UI", 12)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(QRectF(text_left, y, text_width, 20), Qt.AlignLeft | Qt.AlignTop, self.ev.title or "")

        # Date
        y += 22
        painter.setPen(DATE_COLOR)
        date_font = QFont("Segoe UI", 10)
        painter.setFont(date_font)
        date_text = f"{self.ev.start_date} – {self.ev.end_date}" if self.ev.end_date else (self.ev.start_date or "")
        painter.drawText(QRectF(text_left, y, text_width, 18), Qt.AlignLeft | Qt.AlignTop, date_text)

        # Description
        y += 20
        painter.setPen(DESC_COLOR)
        desc_font = QFont("Segoe UI", 10)
        painter.setFont(desc_font)
        painter.drawText(QRectF(text_left, y, text_width, 36), Qt.TextWordWrap, self.ev.description or "")

        # avatars (overlap)
        max_chips = L.get("max_chips", 3)
        raw_chars = [c for c in (self.ev.characters or []) if isinstance(c, str) and c.strip()]
        seen = set()
        unique = []
        for c in raw_chars:
            if c in seen:
                continue
            seen.add(c)
            unique.append(c)
        avatar_count = len(unique)
        shown = min(avatar_count, max_chips)
        cx = self._rect.right() - padding - DEFAULT_CHAR_AVATAR
        cy = self._rect.top() + 8
        overlap = int(DEFAULT_CHAR_AVATAR * 0.40)
        for name in unique[:shown]:
            ch = self.characters.get(name, None)
            avatar_rect = QRectF(cx, cy, DEFAULT_CHAR_AVATAR, DEFAULT_CHAR_AVATAR)
            painter.setBrush(QBrush(Qt.white))
            painter.setPen(QPen(QColor(0, 0, 0, 12)))
            painter.drawEllipse(avatar_rect)
            drew = False
            if ch and getattr(ch, "images", None):
                img = _first_existing_image(ch.images)
                if img:
                    pm = QPixmap(img)
                    if not pm.isNull():
                        inner = avatar_rect.adjusted(2, 2, -2, -2)
                        pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        px = inner.left() + (inner.width() - pm.width()) / 2
                        py = inner.top() + (inner.height() - pm.height()) / 2
                        painter.drawPixmap(int(px), int(py), pm)
                        drew = True
            if not drew:
                fill_col = QColor("#cccccc")
                if ch:
                    try:
                        fill_col = QColor(ch.color)
                    except Exception:
                        pass
                painter.setBrush(QBrush(fill_col))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(avatar_rect.adjusted(3, 3, -3, -3))
            ring_col = QColor("#888")
            if ch:
                try:
                    ring_col = QColor(ch.color)
                except Exception:
                    pass
            painter.setPen(QPen(ring_col, 1.6))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(avatar_rect)
            cx -= (DEFAULT_CHAR_AVATAR - overlap)

        if avatar_count > shown:
            more = avatar_count - shown
            badge_rect = QRectF(cx + overlap, cy, 26, DEFAULT_CHAR_AVATAR)
            painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
            painter.setPen(QPen(QColor(0, 0, 0, 10)))
            painter.drawRoundedRect(badge_rect, badge_rect.height() / 2, badge_rect.height() / 2)
            painter.setPen(CHIP_TEXT)
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(badge_rect, Qt.AlignCenter, f"+{more}")

    # Mouse handling: horizontal move only
    def mousePressEvent(self, event: QMouseEvent):
        self._drag_start_pos = event.pos()
        self._initial_x = self.x()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start_pos is None:
            super().mouseMoveEvent(event)
            return
        dx = event.pos().x() - self._drag_start_pos.x()
        new_x = self._initial_x + dx
        scene = self.scene()
        if scene:
            scene_rect = scene.sceneRect()
            min_x = LEFT_MARGIN
            max_x = scene_rect.width() - 60 - self._rect.width()
            new_x = max(min_x, min(new_x, max_x))
        self.setX(new_x)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        # compute left edge in scene coords
        left_x = self.scenePos().x()
        # Convert x -> date using provided x_to_date (should be a snapping wrapper)
        start_dt = self.x_to_date(left_x)
        # preserve original duration (in whole days)
        s_old = _parse_date(self.ev.start_date) or start_dt
        e_old = _parse_date(self.ev.end_date) or s_old
        delta_days = max(0, (e_old - s_old).days)
        new_start = start_dt
        new_end = new_start + timedelta(days=delta_days)
        # write back to model
        self.ev.start_date = _format_date(new_start)
        self.ev.end_date = _format_date(new_end) if delta_days > 0 else ""
        # defer calling on_change so the item is not removed while still in release handler
        if callable(self.on_change):
            QTimer.singleShot(0, lambda ev=self.ev: self.on_change(ev))
        # do NOT call super().mouseReleaseEvent(event) after this — avoids C++-deleted wrapper issues
        self._drag_start_pos = None
        return


class PrettyTimelineView(QGraphicsView):
    def __init__(self, get_events_fn, get_characters_fn, get_places_fn, on_event_changed: Optional[Callable[[Event], None]] = None, parent=None):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn
        self.on_event_changed = on_event_changed

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(BG_COLOR))
        self.scale_factor = 1.0

        self._font = QFont("Segoe UI")
        self._font.setPointSize(10)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def minimumSizeHint(self) -> QSize:
        return QSize(400, 300)

    def _lod(self):
        z = self.scale_factor
        if z < 0.95:
            return {"tick_days": 28, "date_fmt": "%Y-%m", "thumb": 44, "title_mode": "none", "show_date": False, "show_desc": False, "max_chips": 0, "event_h": 72}
        elif z < 1.20:
            return {"tick_days": 7, "date_fmt": "%Y-%m-%d", "thumb": 52, "title_mode": "abbr3", "show_date": True, "show_desc": False, "max_chips": 2, "event_h": 86}
        else:
            return {"tick_days": 3, "date_fmt": "%Y-%m-%d", "thumb": 68, "title_mode": "full", "show_date": True, "show_desc": True, "max_chips": 4, "event_h": 108}

    def date_to_x(self, dt: datetime, dmin: datetime, lod: dict) -> float:
        days = (dt - dmin).total_seconds() / 86400.0
        return LEFT_MARGIN + days * max(X_STEP_MIN, 140) / lod["tick_days"]

    def x_to_date(self, x: float, dmin: datetime, lod: dict) -> datetime:
        # returns FLOAT-day date (not snapped)
        days = (x - LEFT_MARGIN) * lod["tick_days"] / max(X_STEP_MIN, 140)
        return dmin + timedelta(days=days)

    # wrapper for EventItem: returns snapped date (nearest whole day)
    def _current_x_to_date(self, x: float) -> datetime:
        events = self.get_events_fn()
        dates = []
        for e in events:
            s = _parse_date(getattr(e, "start_date", "") or "")
            if s:
                dates.append(s)
            t = _parse_date(getattr(e, "end_date", "") or "")
            if t:
                dates.append(t)
        if not dates:
            return datetime.now()
        dmin = min(dates) - timedelta(days=0.5)
        lod = self._lod()
        step_px = max(X_STEP_MIN, 140)
        days_float = (x - LEFT_MARGIN) * lod["tick_days"] / step_px
        days_rounded = int(round(days_float))
        return dmin + timedelta(days=days_rounded)

    def _current_date_to_x(self, dt: datetime) -> float:
        events = self.get_events_fn()
        dates = []
        for e in events:
            s = _parse_date(getattr(e, "start_date", "") or "")
            if s:
                dates.append(s)
            t = _parse_date(getattr(e, "end_date", "") or "")
            if t:
                dates.append(t)
        if not dates:
            return LEFT_MARGIN
        dmin = min(dates) - timedelta(days=0.5)
        lod = self._lod()
        return self.date_to_x(dt, dmin, lod)

    def refresh(self):
        self.scene.clear()
        events: List[Event] = self.get_events_fn()
        characters: List[Character] = self.get_characters_fn()
        places: List[Place] = self.get_places_fn()

        L = self._lod()
        char_by_name: Dict[str, Character] = {c.name: c for c in characters}

        dates = []
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
            panel_rect = QRectF(20, 20, vp_w - 40, vp_h - 40)
            _add_rounded_rect(self.scene, panel_rect, 16, QPen(PANEL_BORDER), QBrush(PANEL_COLOR))
            self.scene.addText("No data to display").setPos(LEFT_MARGIN, TOP_MARGIN)
            return

        dmin, dmax = min(dates), max(dates)
        dmin = dmin - timedelta(days=0.5)
        dmax = dmax + timedelta(days=0.5)
        lod = L

        step_px = max(X_STEP_MIN, 140)

        def x_for(dt: datetime) -> float:
            days = (dt - dmin).total_seconds() / 86400.0
            return LEFT_MARGIN + days * step_px / lod["tick_days"]

        content_w = x_for(dmax) + 220
        content_h = TOP_MARGIN + len(places) * ROW_H + 140
        scene_w = max(content_w + 40, vp_w)
        scene_h = max(content_h + 40, vp_h)
        self.scene.setSceneRect(0, 0, scene_w, scene_h)

        # panel
        panel_rect = QRectF(20, 20, scene_w - 40, scene_h - 40)
        _add_rounded_rect(self.scene, panel_rect, 16, QPen(PANEL_BORDER), QBrush(PANEL_COLOR))

        # places
        for i, p in enumerate(places):
            y = TOP_MARGIN + i * ROW_H
            line_y = y + ROW_H / 2
            self.scene.addLine(LEFT_MARGIN - 10, line_y, scene_w - 60, line_y, QPen(TIMELINE_COLOR, 3))
            pill_rect = QRectF(20, line_y - (PLACE_PILL_HEIGHT / 2), LEFT_MARGIN - 40, PLACE_PILL_HEIGHT)
            _add_rounded_rect(self.scene, pill_rect, PLACE_PILL_HEIGHT / 2, QPen(PLACE_PILL_STROKE), QBrush(PLACE_PILL_BG))
            p_img = _first_existing_image(getattr(p, "images", []))
            name_x = pill_rect.left() + PLACE_PILL_PADDING
            if p_img:
                avatar_size = min(PLACE_AVATAR_SIZE, pill_rect.height() - 6)
                avatar_rect = QRectF(pill_rect.left() + PLACE_PILL_PADDING,
                                     pill_rect.top() + (pill_rect.height() - avatar_size) / 2,
                                     avatar_size, avatar_size)
                _add_rounded_rect(self.scene, avatar_rect, avatar_size / 2, QPen(QColor(0, 0, 0, 20)), QBrush(Qt.white))
                pm = QPixmap(p_img)
                if not pm.isNull():
                    inner = avatar_rect.adjusted(3, 3, -3, -3)
                    pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    px = inner.left() + (inner.width() - pm.width()) / 2
                    py = inner.top() + (inner.height() - pm.height()) / 2
                    self.scene.addPixmap(pm).setPos(px, py)
                name_x = avatar_rect.right() + 8
            name_font = QFont(self._font.family(), 11)
            name_item = self.scene.addText(_elide(p.name, 24), name_font)
            name_item.setDefaultTextColor(Qt.black)
            name_item.setPos(name_x, pill_rect.top() + (pill_rect.height() - 14) / 2)

        # ticks
        tick = dmin - timedelta(days=(dmin.weekday() % 7))
        while tick <= dmax:
            x = x_for(tick)
            if x >= LEFT_MARGIN - 5:
                self.scene.addLine(x, TOP_MARGIN - 30, x, scene_h - 60, QPen(AXIS_COLOR, 1, Qt.DashLine))
                txt = self.scene.addText(tick.strftime(lod["date_fmt"]), self._font)
                txt.setDefaultTextColor(QColor(120, 120, 130))
                txt.setPos(x - 35, TOP_MARGIN - 55)
            tick += timedelta(days=lod["tick_days"])

        # add EventItems
        for ev in events:
            sdt = _parse_date(getattr(ev, "start_date", "") or "")
            edt = _parse_date(getattr(ev, "end_date", "") or "") or sdt
            if not sdt:
                continue
            if edt < sdt:
                edt = sdt
            x_start = x_for(sdt)
            x_end = x_for(edt)
            day_px = (step_px / lod["tick_days"])
            min_width = max(36, int(day_px * 0.6))
            raw_width = max(min_width, int(round(x_end - x_start)))
            rect_left = max(LEFT_MARGIN, min(x_start, scene_w - 60 - raw_width))
            rect_width = raw_width

            for place_name in getattr(ev, "places", []) or [""]:
                row_idx = next((i for i, pl in enumerate(places) if pl.name == place_name), None)
                if row_idx is None:
                    continue
                ev_h = lod["event_h"]
                y_center = TOP_MARGIN + row_idx * ROW_H + ROW_H / 2
                rect = QRectF(rect_left, y_center - ev_h / 2, rect_width, ev_h)

                item = EventItem(
                    ev=ev,
                    characters=char_by_name,
                    x_to_date=lambda xx, dmin=dmin, lod=lod, step_px=step_px: self._snap_x_to_date(xx, dmin, lod, step_px),
                    date_to_x=lambda dt, dmin=dmin, lod=lod: self.date_to_x(dt, dmin, lod),
                    on_change=self._on_event_changed,
                    lod_getter=self._lod_getter
                )
                item._rect = rect
                item.setPos(rect.left(), rect.top())
                self.scene.addItem(item)

    def _lod_getter(self):
        return self._lod()

    def _snap_x_to_date(self, x: float, dmin: datetime, lod: dict, step_px: int) -> datetime:
        days_float = (x - LEFT_MARGIN) * lod["tick_days"] / step_px
        days_rounded = int(round(days_float))
        return dmin + timedelta(days=days_rounded)

    def _on_event_changed(self, ev: Event):
        # defer propagation to avoid deleting items mid-event
        if callable(self.on_event_changed):
            QTimer.singleShot(0, lambda e=ev: self.on_event_changed(e))

    # zoom helpers
    def zoom_in(self):
        step = 1.25
        self.scale(step, step)
        self.scale_factor *= step
        self.refresh()

    def zoom_out(self):
        step = 1.25
        self.scale(1 / step, 1 / step)
        self.scale_factor /= step
        self.refresh()

    def reset_zoom(self):
        self.resetTransform()
        self.scale_factor = 1.0
        self.refresh()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            return
        super().wheelEvent(event)


class TimelineTab(QWidget):
    data_changed = Signal()

    def __init__(self, get_events_fn, get_characters_fn, get_places_fn):
        super().__init__()

        self.char_filter = QListWidget(); self.char_filter.setSelectionMode(QListWidget.MultiSelection)
        self.place_filter = QListWidget(); self.place_filter.setSelectionMode(QListWidget.MultiSelection)
        self.date_from = QDateEdit(); self.date_from.setCalendarPopup(True); self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_to = QDateEdit(); self.date_to.setCalendarPopup(True); self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.auto_dates = QCheckBox("Auto dates"); self.auto_dates.setChecked(True)

        self.apply_btn = QPushButton("Apply")
        self.clear_btn = QPushButton("Clear")
        self.zoomin_btn = QPushButton("+")
        self.zoomout_btn = QPushButton("-")

        self._get_events_raw = get_events_fn
        self._get_characters = get_characters_fn
        self._get_places = get_places_fn

        # pass on_event_changed callback so tab can emit data_changed/save
        self.graph = PrettyTimelineView(self._get_events_filtered, self._get_characters, self._get_places, on_event_changed=self._on_item_changed)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        left = QVBoxLayout(); left.addWidget(QLabel("Characters:")); left.addWidget(self.char_filter)
        mid = QVBoxLayout(); mid.addWidget(QLabel("Places:")); mid.addWidget(self.place_filter)
        right = QVBoxLayout(); right.addWidget(QLabel("From:")); right.addWidget(self.date_from)
        right.addWidget(QLabel("To:")); right.addWidget(self.date_to)
        row1 = QHBoxLayout(); row1.addLayout(left, 2); row1.addLayout(mid, 2); row1.addLayout(right, 1)
        controls_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.apply_btn.clicked.connect(self.graph.refresh)
        self.clear_btn.clicked.connect(self._clear_filters)
        self.zoomin_btn.clicked.connect(self.graph.zoom_in)
        self.zoomout_btn.clicked.connect(self.graph.zoom_out)

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

        # keyboard shortcuts using QShortcut
        QShortcut(QKeySequence("Ctrl++"), self, activated=self.graph.zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self, activated=self.graph.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self.graph.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.graph.reset_zoom)

        self._populate_filters()
        self._init_date_defaults()

        self.char_filter.itemSelectionChanged.connect(self._maybe_auto_dates)
        self.place_filter.itemSelectionChanged.connect(self._maybe_auto_dates)

        self.graph.refresh()

    def _on_item_changed(self, ev: Event):
        # defer refresh + emit so it doesn't run inside release handler
        QTimer.singleShot(0, self._deferred_item_changed)

    def _deferred_item_changed(self):
        # emit and refresh in next loop cycle (safe)
        try:
            self.data_changed.emit()
        except Exception:
            pass
        try:
            self.graph.refresh()
        except Exception:
            pass

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

        def char_ok(e: Event): return True if not sel_chars else bool(set(e.characters) & sel_chars)
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
                ed = _parse_date(e.end_date)
                if ed:
                    dts.append(ed)
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
        self.graph.refresh()

    def refresh(self):
        self._populate_filters()
        self.graph.refresh()