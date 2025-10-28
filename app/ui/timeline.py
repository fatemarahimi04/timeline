from __future__ import annotations
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QDateEdit, QCheckBox, QSplitter, QDialog,
    QDialogButtonBox, QMessageBox, QMenu, QGraphicsEllipseItem, QGraphicsTextItem
)
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPixmap, QPainterPath, QPainter, QShortcut, QKeySequence, QGuiApplication
from PySide6.QtCore import Qt, QRectF, QDate, QSignalBlocker, QSize, Signal, QPointF, QPoint, QTimer

from ..models import Event, Character, Place

ROW_H = 100
LEFT_MARGIN = 180
TOP_MARGIN = 100
EVENT_RADIUS = 12
EVENT_PADDING = 12
X_STEP_MIN = 210

PLACE_PILL_HEIGHT = 36
PLACE_AVATAR_SIZE = 28
PLACE_PILL_PADDING = 10

DEFAULT_CHAR_AVATAR = 22
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


def _elide(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _first_existing_image(paths: List[str]) -> Optional[str]:
    for p in paths or []:
        if not p:
            continue
        if not os.path.isabs(p):
            p = os.path.join(os.getcwd(), p)
        if os.path.exists(p):
            return p
    return None


class ClickableEllipseItem(QGraphicsEllipseItem):
    """
    Small clickable ellipse used as an 'info' button inside an event card.
    On click it schedules the callback(ev_index, scene_pos: QPointF) to run
    via QTimer.singleShot(0, ...) so the callback runs after the event
    handler has returned (avoids C++ object-deleted-while-in-Python errors).
    """
    def __init__(self, rect: QRectF, ev_index: int, callback: Callable[[int, QPointF], None]):
        super().__init__(rect)
        self.ev_index = ev_index
        self.callback = callback
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        try:
            if callable(self.callback):
                center = self.sceneBoundingRect().center()
                try:
                    event.accept()
                except Exception:
                    pass
                QTimer.singleShot(0, lambda ev_idx=self.ev_index, c=center: self.callback(ev_idx, c))
        except Exception:
            import traceback
            traceback.print_exc()


class PrettyTimelineView(QGraphicsView):
    """
    Non-interactive timeline renderer. Call refresh() to re-draw.
    Provides zoom_in/zoom_out/reset_zoom for TimelineTab controls.

    Added: small clickable 'info' icon on each event (bottom-left).
    When clicked, a menu allows editing characters, places or dates.
    After edit the provided on_event_edited() callback is called (if any) to allow saving.
    """
    def __init__(
        self,
        get_events_fn,
        get_characters_fn,
        get_places_fn,
        get_selected_chars_fn=None,
        on_event_edited: Optional[Callable[[], None]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.get_events_fn = get_events_fn
        self.get_characters_fn = get_characters_fn
        self.get_places_fn = get_places_fn
        self.get_selected_chars_fn = get_selected_chars_fn
        self.on_event_edited = on_event_edited

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(BG_COLOR))
        self.scale_factor = 1.0

        self._font = QFont("Segoe UI", 10)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def minimumSizeHint(self) -> QSize:
        return QSize(400, 300)

    def _lod(self):
        z = self.scale_factor
        if z < 0.95:
            return {"tick_days": 28, "date_fmt": "%Y-%m", "thumb": 44, "title_mode": "none", "show_date": False, "show_desc": False, "max_chips": 0, "event_w": 220, "event_h": 72}
        elif z < 1.20:
            return {"tick_days": 7, "date_fmt": "%Y-%m-%d", "thumb": 52, "title_mode": "abbr3", "show_date": True, "show_desc": False, "max_chips": 2, "event_w": 260, "event_h": 86}
        else:
            return {"tick_days": 3, "date_fmt": "%Y-%m-%d", "thumb": 68, "title_mode": "full", "show_date": True, "show_desc": True, "max_chips": 4, "event_w": 320, "event_h": 108}

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
            _add_rounded_rect(self.scene, panel_rect, 12, QPen(PANEL_BORDER), QBrush(PANEL_COLOR))
            self.scene.addText("No data to display").setPos(LEFT_MARGIN, TOP_MARGIN)
            return

        dmin, dmax = min(dates), max(dates)
        dmin = dmin - timedelta(days=1)
        dmax = dmax + timedelta(days=1)

        step_px = max(X_STEP_MIN, 140)

        def x_for(dt: datetime) -> float:
            days = (dt - dmin).total_seconds() / 86400.0
            return LEFT_MARGIN + days * step_px / L["tick_days"]

        content_w = x_for(dmax) + 220
        content_h = TOP_MARGIN + len(places) * ROW_H + 140
        scene_w = max(content_w + 40, vp_w)
        scene_h = max(content_h + 40, vp_h)
        self.scene.setSceneRect(0, 0, scene_w, scene_h)

        panel_rect = QRectF(20, 20, scene_w - 40, scene_h - 40)
        _add_rounded_rect(self.scene, panel_rect, 12, QPen(PANEL_BORDER), QBrush(PANEL_COLOR))

        today_dt = datetime.today().date()
        if dmin.date() <= today_dt <= dmax.date():
            x_today = x_for(datetime(today_dt.year, today_dt.month, today_dt.day))
            self.scene.addLine(x_today, TOP_MARGIN - 30, x_today, scene_h - 60, QPen(QColor(255, 80, 80, 160), 2))
            t = self.scene.addText("Today", QFont(self._font.family(), 9))
            t.setDefaultTextColor(QColor(200, 60, 60))
            t.setPos(x_today + 6, TOP_MARGIN - 70)

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
                avatar_rect = QRectF(pill_rect.left() + PLACE_PILL_PADDING, pill_rect.top() + (pill_rect.height() - avatar_size) / 2, avatar_size, avatar_size)
                _add_rounded_rect(self.scene, avatar_rect, avatar_size / 2, QPen(QColor(0,0,0,20)), QBrush(Qt.white))
                pm = QPixmap(p_img)
                if not pm.isNull():
                    inner = avatar_rect.adjusted(3, 3, -3, -3)
                    pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    pm_item = self.scene.addPixmap(pm)
                    pm_item.setPos(inner.left() + (inner.width() - pm.width())/2, inner.top() + (inner.height() - pm.height())/2)
                    pm_item.setZValue(12)
                name_x = avatar_rect.right() + 8

            name_item = self.scene.addText(_elide(p.name, 24), QFont(self._font.family(), 11))
            name_item.setDefaultTextColor(Qt.black)
            name_item.setPos(name_x, pill_rect.top() + (pill_rect.height() - 14) / 2)

        tick = dmin - timedelta(days=(dmin.weekday() % 7))
        while tick <= dmax:
            x = x_for(tick)
            if x >= LEFT_MARGIN - 5:
                self.scene.addLine(x, TOP_MARGIN - 30, x, scene_h - 60, QPen(AXIS_COLOR, 1, Qt.DashLine))
                txt = self.scene.addText(tick.strftime(L["date_fmt"]), self._font)
                txt.setDefaultTextColor(QColor(120,120,130))
                txt.setPos(x - 35, TOP_MARGIN - 55)
            tick += timedelta(days=L["tick_days"])

        selected_chars = set(self.get_selected_chars_fn() or []) if self.get_selected_chars_fn else set()

        stack_map: Dict[tuple, int] = {}

        for ev_idx, ev in enumerate(events):
            sdt = _parse_date(getattr(ev, "start_date", "") or "")
            edt = _parse_date(getattr(ev, "end_date", "") or "") or sdt
            if not sdt:
                continue
            if edt < sdt:
                edt = sdt

            x = x_for(sdt)

            for place_name in getattr(ev, "places", []) or [""]:
                row_idx = next((i for i, pl in enumerate(places) if pl.name == place_name), None)
                if row_idx is None:
                    continue

                Lcur = L
                y_center = TOP_MARGIN + row_idx * ROW_H + ROW_H / 2

                x_start = x_for(sdt)
                x_end   = x_for(edt) if edt else x_start

                if edt and edt > sdt:
                    band_left  = max(LEFT_MARGIN + 6, x_start)
                    band_right = max(band_left, x_end)
                    band_rect  = QRectF(band_left, y_center - 6, band_right - band_left, 12)
                    self.scene.addRect(band_rect, QPen(Qt.NoPen), QBrush(QColor(60, 100, 160, 80)))

                min_left   = LEFT_MARGIN + 6
                min_width  = Lcur["event_w"]
                rect_left  = max(min_left, x_start)

                if edt and edt > sdt:
                    span_w = max(min_width, (x_end - rect_left))
                    rect_w = span_w
                else:
                    rect_w = min_width

                rect_h   = Lcur["event_h"]
                rect     = QRectF(rect_left, y_center - rect_h/2, rect_w, rect_h)
                day_slot = (row_idx, sdt.date())
                idx = stack_map.get(day_slot, 0)
                if idx:
                    rect.translate(0, (-1)**idx * (min(idx, 3) * 16))
                stack_map[day_slot] = idx + 1

                shadow = QRectF(rect); shadow.translate(0, 4)
                _add_rounded_rect(self.scene, shadow, EVENT_RADIUS, QPen(Qt.NoPen), QBrush(SHADOW_COLOR))

                has_sel = bool(selected_chars & set(ev.characters or []))
                if ev.characters:
                    try:
                        base_col = QColor(char_by_name.get(ev.characters[0], Character(name="", color="#9aa")).color)
                    except Exception:
                        base_col = QColor("#9aa")
                    bg = QColor(base_col); bg.setAlpha(200 if (not selected_chars or has_sel) else 90)
                    border = QColor(base_col.darker(140)) if (not selected_chars or has_sel) else QColor(180,180,185)
                else:
                    bg = QColor("#EFE7DE")
                    border = CARD_BORDER if (not selected_chars) else QColor(200,200,205)

                _add_rounded_rect(self.scene, rect, EVENT_RADIUS, QPen(border, 1.6), QBrush(bg))

                padding   = EVENT_PADDING
                chip_zone = min(int(rect.width() * 0.35), 140)
                text_left = rect.left() + padding
                text_right = rect.right() - (padding + 8 + chip_zone)
                text_width = max(10, int(text_right - text_left))

                base_y   = rect.top() + 10
                next_y   = base_y

                thumb_path = _first_existing_image(getattr(ev, "images", []))
                if thumb_path and L.get("thumb", 0) > 0:
                    frame = QRectF(rect.left() + padding, rect.top() + (L["event_h"] - L["thumb"]) / 2, L["thumb"], L["thumb"])
                    _add_rounded_rect(self.scene, frame, 8, QPen(QColor(0,0,0,30)), QBrush(Qt.white))
                    pm = QPixmap(thumb_path)
                    if not pm.isNull():
                        inner = frame.adjusted(4,4,-4,-4)
                        pm = pm.scaled(int(inner.width()), int(inner.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        pmi = self.scene.addPixmap(pm)
                        pmi.setPos(inner.left() + (inner.width() - pm.width())/2, inner.top() + (inner.height() - pm.height())/2)
                    text_left = frame.right() + 10
                    text_width = max(10, int(text_right - text_left))

                title_font = QFont(self._font); title_font.setPointSize(12); title_font.setBold(True)
                t_item = self.scene.addText(_elide(ev.title or "", 40), title_font)
                t_item.setDefaultTextColor(TITLE_COLOR)
                t_item.setPos(text_left, next_y)
                next_y += 22

                if Lcur.get("show_date", False):
                    date_font = QFont(self._font); date_font.setPointSize(10)
                    date_text = f"{ev.start_date} – {ev.end_date}" if ev.end_date else (ev.start_date or "")
                    d_item = self.scene.addText(_elide(date_text, 40), date_font)
                    d_item.setDefaultTextColor(DATE_COLOR)
                    d_item.setPos(text_left, next_y)
                    next_y += 18

                if Lcur.get("show_desc", False):
                    desc_font = QFont(self._font); desc_font.setPointSize(10)
                    desc_item = self.scene.addText(_elide(ev.description or "", 120), desc_font)
                    desc_item.setDefaultTextColor(DESC_COLOR)
                    desc_item.setPos(text_left, next_y)
                    next_y += 18

                cx = rect.right() - padding - DEFAULT_CHAR_AVATAR
                cy = rect.top() + 10
                for name in (ev.characters or [])[:Lcur.get("max_chips", 3)]:
                    ch = char_by_name.get(name, None)
                    col = QColor("#888")
                    if ch:
                        try:
                            col = QColor(ch.color)
                        except Exception:
                            pass
                    if selected_chars and name not in selected_chars:
                        col = QColor(150,150,155)
                    circ = self.scene.addEllipse(cx - DEFAULT_CHAR_AVATAR, cy, DEFAULT_CHAR_AVATAR, DEFAULT_CHAR_AVATAR, QPen(Qt.NoPen), QBrush(col))
                    circ.setZValue(40)
                    cx -= (DEFAULT_CHAR_AVATAR + AVATAR_SPACING)

                info_size = 16
                info_x = rect.left() + 8
                info_y = rect.bottom() - info_size - 8
                info_rect = QRectF(info_x, info_y, info_size, info_size)
                info_item = ClickableEllipseItem(info_rect, ev_idx, self._on_info_clicked)
                info_item.setZValue(80)
                info_item.setBrush(QBrush(QColor(255, 255, 255, 220)))
                info_item.setPen(QPen(QColor(120, 120, 130), 1.0))
                self.scene.addItem(info_item)
                i_text = QGraphicsTextItem("i")
                font_i = QFont(self._font)
                font_i.setPointSize(10)
                font_i.setBold(True)
                i_text.setFont(font_i)
                i_text.setDefaultTextColor(QColor(80, 80, 90))
                i_text.setPos(info_x + 4, info_y - 1)
                i_text.setZValue(81)
                self.scene.addItem(i_text)

    def _on_info_clicked(self, ev_index: int, scene_pos: QPointF):
        """
        Called when the small info icon on an event is clicked.
        Shows a menu with choices to edit characters, places or dates.
        The menu position is clamped to the current screen's available geometry so it won't open off-screen.
        """
        view_pos = self.mapFromScene(scene_pos)

        if isinstance(view_pos, QPointF):
            vp = QPoint(int(view_pos.x()), int(view_pos.y()))
        elif isinstance(view_pos, QPoint):
            vp = view_pos
        else:
            try:
                vp = QPoint(int(view_pos.x()), int(view_pos.y()))
            except Exception:
                vp = QPoint(0, 0)

        global_pos = self.mapToGlobal(vp)

        menu = QMenu()
        act_chars = menu.addAction("Edit characters")
        act_places = menu.addAction("Edit places")
        act_dates = menu.addAction("Edit dates")

        try:
            menu_size = menu.sizeHint()
            screen = QGuiApplication.screenAt(global_pos) if hasattr(QGuiApplication, "screenAt") else QGuiApplication.primaryScreen()
            if screen is None:
                screen = QGuiApplication.primaryScreen()
            screen_geom = screen.availableGeometry()
            px = global_pos.x()
            py = global_pos.y()
            if px + menu_size.width() > screen_geom.right():
                px = max(screen_geom.left(), screen_geom.right() - menu_size.width() - 8)
            if px < screen_geom.left():
                px = screen_geom.left() + 8
            if py + menu_size.height() > screen_geom.bottom():
                py = max(screen_geom.top(), screen_geom.bottom() - menu_size.height() - 8)
            if py < screen_geom.top():
                py = screen_geom.top() + 8
            global_pos = QPoint(px, py)
        except Exception:
            pass

        chosen = menu.exec(global_pos)
        if chosen is None:
            return

        if chosen == act_chars:
            self._edit_characters(ev_index)
        elif chosen == act_places:
            self._edit_places(ev_index)
        elif chosen == act_dates:
            self._edit_dates(ev_index)

    def _edit_characters(self, ev_index: int):
        events = self.get_events_fn()
        if ev_index < 0 or ev_index >= len(events):
            return
        ev = events[ev_index]

        dlg = QDialog(self.window())
        dlg.setWindowTitle(f"Edit characters — {ev.title}")
        layout = QVBoxLayout(dlg)
        listw = QListWidget()
        listw.setSelectionMode(QListWidget.MultiSelection)
        chars = [c.name for c in self.get_characters_fn()]
        for name in chars:
            item = QListWidgetItem(name)
            listw.addItem(item)
            if name in (ev.characters or []):
                item.setSelected(True)
        layout.addWidget(QLabel("Select characters:"))
        layout.addWidget(listw)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if dlg.exec() == QDialog.Accepted:
            ev.characters = [i.text() for i in listw.selectedItems()]
            # refresh and notify
            self.refresh()
            if callable(self.on_event_edited):
                try:
                    self.on_event_edited()
                except Exception:
                    pass

    def _edit_places(self, ev_index: int):
        events = self.get_events_fn()
        if ev_index < 0 or ev_index >= len(events):
            return
        ev = events[ev_index]

        dlg = QDialog(self.window())
        dlg.setWindowTitle(f"Edit places — {ev.title}")
        layout = QVBoxLayout(dlg)
        listw = QListWidget()
        listw.setSelectionMode(QListWidget.MultiSelection)
        places = [p.name for p in self.get_places_fn()]
        for name in places:
            item = QListWidgetItem(name)
            listw.addItem(item)
            if name in (ev.places or []):
                item.setSelected(True)
        layout.addWidget(QLabel("Select places:"))
        layout.addWidget(listw)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        if dlg.exec() == QDialog.Accepted:
            ev.places = [i.text() for i in listw.selectedItems()]
            self.refresh()
            if callable(self.on_event_edited):
                try:
                    self.on_event_edited()
                except Exception:
                    pass

    def _edit_dates(self, ev_index: int):
        events = self.get_events_fn()
        if ev_index < 0 or ev_index >= len(events):
            return
        ev = events[ev_index]

        dlg = QDialog(self.window())
        dlg.setWindowTitle(f"Edit dates — {ev.title}")
        layout = QVBoxLayout(dlg)
        start_edit = QDateEdit(); start_edit.setCalendarPopup(True); start_edit.setDisplayFormat("yyyy-MM-dd")
        end_edit = QDateEdit(); end_edit.setCalendarPopup(True); end_edit.setDisplayFormat("yyyy-MM-dd")
        today = QDate.currentDate()
        if ev.start_date:
            d = _parse_date(ev.start_date)
            if d:
                start_edit.setDate(QDate.fromString(d.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            else:
                start_edit.setDate(today)
        else:
            start_edit.setDate(today)
        if ev.end_date:
            d2 = _parse_date(ev.end_date)
            if d2:
                end_edit.setDate(QDate.fromString(d2.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
            else:
                end_edit.setDate(start_edit.date())
        else:
            end_edit.setDate(start_edit.date())

        layout.addWidget(QLabel("Start date:")); layout.addWidget(start_edit)
        layout.addWidget(QLabel("End date:")); layout.addWidget(end_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec() == QDialog.Accepted:
            s = start_edit.date()
            t = end_edit.date()
            if t < s:
                QMessageBox.warning(self.window(), "Ogiltiga datum", "Slutdatum kan inte vara tidigare än startdatum.")
                return
            ev.start_date = s.toString("yyyy-MM-dd")
            ev.end_date = t.toString("yyyy-MM-dd")
            self.refresh()
            if callable(self.on_event_edited):
                try:
                    self.on_event_edited()
                except Exception:
                    pass

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

        self._get_events_raw = get_events_fn
        self._get_characters = get_characters_fn
        self._get_places = get_places_fn

        self.char_filter = QListWidget(); self.char_filter.setSelectionMode(QListWidget.MultiSelection)
        self.place_filter = QListWidget(); self.place_filter.setSelectionMode(QListWidget.MultiSelection)
        self.date_from = QDateEdit(); self.date_from.setCalendarPopup(True); self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_to = QDateEdit(); self.date_to.setCalendarPopup(True); self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.auto_dates = QCheckBox("Auto dates"); self.auto_dates.setChecked(True)

        self.apply_btn = QPushButton("Apply")
        self.clear_btn = QPushButton("Clear")
        self.zoomin_btn = QPushButton("+")
        self.zoomout_btn = QPushButton("-")

        self.graph = PrettyTimelineView(
            self._get_events_filtered,
            self._get_characters,
            self._get_places,
            get_selected_chars_fn=self._selected_chars,
            on_event_edited=self._on_event_edited
        )

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        left = QVBoxLayout(); left.addWidget(QLabel("Characters:")); left.addWidget(self.char_filter)
        mid = QVBoxLayout(); mid.addWidget(QLabel("Places:")); mid.addWidget(self.place_filter)
        right = QVBoxLayout(); right.addWidget(QLabel("From:")); right.addWidget(self.date_from)
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

    def _on_event_edited(self):
        """
        Called by the PrettyTimelineView when an event has been edited.
        Emit data_changed so MainWindow (or whoever listens) can save the state.
        Also refresh the timeline to reflect changes.
        """
        try:
            self.refresh()
        finally:
            try:
                self.data_changed.emit()
            except Exception:
                pass