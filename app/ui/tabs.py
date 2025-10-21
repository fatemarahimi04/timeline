from __future__ import annotations
from dataclasses import asdict
from typing import List
import os

from PySide6.QtCore import Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox,
    QFileDialog, QDialog, QDialogButtonBox, QComboBox
)
from PySide6.QtGui import QColor, QPixmap, QIcon

from ..models import Character, Place, Event

# Förvalda färger (exakt sju som du önskade)
PALETTE = [
    ("Baby rosa", "#F8C8DC"),
    ("Ljust blå", "#A7C7E7"),
    ("Ljus grön", "#BEE5B0"),
    ("Röd", "#EF4444"),
    ("Turkos", "#40E0D0"),
    ("Smör gul", "#FFE08A"),
    ("Ljus brun", "#C8A27E"),
]

# ---------- Character ----------
class CharacterForm(QDialog):
    def __init__(self, character: Character = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Character")
        self.setModal(True)

        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()

        # Förvald färg via ComboBox (visar en färgruta som ikon)
        self.color_combo = QComboBox()
        # ikonstorlek så färgrutan syns i dropdown och i vald rad
        self.color_combo.setIconSize(QSize(16, 16))
        for label, hexcode in PALETTE:
            # skapa liten pixmap fylld med färg för att använda som ikon
            pix = QPixmap(16, 16)
            pix.fill(QColor(hexcode))
            icon = QIcon(pix)
            # lägg till item med icon, textrubrik och userData = hexkod
            self.color_combo.addItem(icon, label, hexcode)

        # Images
        self.images_list = QListWidget()
        self.add_img_btn = QPushButton("Add Image")
        self.del_img_btn = QPushButton("Delete Image")
        self.add_img_btn.clicked.connect(self._add_img)
        self.del_img_btn.clicked.connect(self._del_img)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Name:")); layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Description:")); layout.addWidget(self.desc_edit)
        layout.addWidget(QLabel("Color:")); layout.addWidget(self.color_combo)
        layout.addWidget(QLabel("Images:")); layout.addWidget(self.images_list)
        imgrow = QHBoxLayout(); imgrow.addWidget(self.add_img_btn); imgrow.addWidget(self.del_img_btn)
        layout.addLayout(imgrow)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.character = character
        if character:
            self.name_edit.setText(character.name)
            self.desc_edit.setPlainText(character.description)
            # välj rätt färg i listan (sök på userData = hexkod)
            idx = self.color_combo.findData(character.color)
            if idx == -1:
                idx = 0
            self.color_combo.setCurrentIndex(idx)
            for img in getattr(character, "images", []):
                self.images_list.addItem(img)

    def _add_img(self):
        from ..storage import get_pictures_dir, get_project_dir
        import shutil

        file, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if not file:
            return
        pictures_dir = get_pictures_dir()
        pictures_dir.mkdir(parents=True, exist_ok=True)
        filename = os.path.basename(file)
        dest = pictures_dir / filename
        try:
            shutil.copy(file, dest)
        except Exception as e:
            QMessageBox.warning(self, "Copy failed", f"Could not copy image:\n{e}")
            return
        rel = os.path.relpath(dest, get_project_dir())
        self.images_list.addItem(rel)

    def _del_img(self):
        for item in self.images_list.selectedItems():
            self.images_list.takeItem(self.images_list.row(item))

    def get_result(self):
        name = self.name_edit.text().strip()
        if not name:
            return None
        desc = self.desc_edit.toPlainText()
        color = self.color_combo.currentData()
        images = [self.images_list.item(i).text() for i in range(self.images_list.count())]
        return Character(name=name, description=desc, color=color, images=images)


# ---------- Place ----------
class PlaceForm(QDialog):
    def __init__(self, place: Place = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Place")
        self.setModal(True)

        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()

        self.images_list = QListWidget()
        self.add_img_btn = QPushButton("Add Image")
        self.del_img_btn = QPushButton("Delete Image")
        self.add_img_btn.clicked.connect(self._add_img)
        self.del_img_btn.clicked.connect(self._del_img)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Name:")); layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Description:")); layout.addWidget(self.desc_edit)
        layout.addWidget(QLabel("Images:")); layout.addWidget(self.images_list)
        imgrow = QHBoxLayout(); imgrow.addWidget(self.add_img_btn); imgrow.addWidget(self.del_img_btn)
        layout.addLayout(imgrow)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.place = place
        if place:
            self.name_edit.setText(place.name)
            self.desc_edit.setPlainText(place.description)
            for img in getattr(place, "images", []):
                self.images_list.addItem(img)

    def _add_img(self):
        from ..storage import get_pictures_dir, get_project_dir
        import shutil

        file, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if not file:
            return
        pictures_dir = get_pictures_dir()
        pictures_dir.mkdir(parents=True, exist_ok=True)
        filename = os.path.basename(file)
        dest = pictures_dir / filename
        try:
            shutil.copy(file, dest)
        except Exception as e:
            QMessageBox.warning(self, "Copy failed", f"Could not copy image:\n{e}")
            return
        rel = os.path.relpath(dest, get_project_dir())
        self.images_list.addItem(rel)

    def _del_img(self):
        for item in self.images_list.selectedItems():
            self.images_list.takeItem(self.images_list.row(item))

    def get_result(self):
        name = self.name_edit.text().strip()
        if not name:
            return None
        desc = self.desc_edit.toPlainText()
        images = [self.images_list.item(i).text() for i in range(self.images_list.count())]
        return Place(name=name, description=desc, images=images)


# ---------- Event ----------
class EventForm(QDialog):
    def __init__(self, event: Event = None, characters: List[Character] = None, places: List[Place] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Event")
        self.setModal(True)

        from PySide6.QtCore import QDate
        self.title_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.start_date_edit = QLineEdit()
        self.end_date_edit = QLineEdit()

        # Byt till QDateEdit för datum (default: idag)
        from PySide6.QtWidgets import QDateEdit
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setDate(QDate.currentDate())
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDate(QDate.currentDate())

        # sync: när start ändras → end = start
        self.start_date_edit.dateChanged.connect(lambda d: self.end_date_edit.setDate(d))

        # Bilder
        self.images_list = QListWidget()
        self.add_img_btn = QPushButton("Add Image"); self.del_img_btn = QPushButton("Delete Image")
        self.add_img_btn.clicked.connect(self._add_img); self.del_img_btn.clicked.connect(self._del_img)

        # Multi-select Characters/Places
        self.char_list = QListWidget(); self.char_list.setSelectionMode(QListWidget.MultiSelection)
        for c in (characters or []):
            self.char_list.addItem(c.name)
        self.place_list = QListWidget(); self.place_list.setSelectionMode(QListWidget.MultiSelection)
        for p in (places or []):
            self.place_list.addItem(p.name)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Title:")); layout.addWidget(self.title_edit)
        layout.addWidget(QLabel("Description:")); layout.addWidget(self.desc_edit)
        layout.addWidget(QLabel("Start date:")); layout.addWidget(self.start_date_edit)
        layout.addWidget(QLabel("End date:")); layout.addWidget(self.end_date_edit)

        layout.addWidget(QLabel("Images:")); layout.addWidget(self.images_list)
        r = QHBoxLayout(); r.addWidget(self.add_img_btn); r.addWidget(self.del_img_btn)
        layout.addLayout(r)

        layout.addWidget(QLabel("Characters:")); layout.addWidget(self.char_list)
        layout.addWidget(QLabel("Places:")); layout.addWidget(self.place_list)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        if event:
            self.title_edit.setText(event.title)
            self.desc_edit.setPlainText(event.description)
            if event.start_date:
                self.start_date_edit.setDate(QDate.fromString(event.start_date, "yyyy-MM-dd"))
            if event.end_date:
                self.end_date_edit.setDate(QDate.fromString(event.end_date, "yyyy-MM-dd"))
            for img in event.images:
                self.images_list.addItem(img)
            for i in range(self.char_list.count()):
                if event.characters and self.char_list.item(i).text() in event.characters:
                    self.char_list.item(i).setSelected(True)
            for i in range(self.place_list.count()):
                if event.places and self.place_list.item(i).text() in event.places:
                    self.place_list.item(i).setSelected(True)

    def _add_img(self):
        from ..storage import get_pictures_dir, get_project_dir
        import shutil

        file, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if not file:
            return
        pictures_dir = get_pictures_dir()
        pictures_dir.mkdir(parents=True, exist_ok=True)
        filename = os.path.basename(file)
        dest = pictures_dir / filename
        try:
            shutil.copy(file, dest)
        except Exception as e:
            QMessageBox.warning(self, "Copy failed", f"Could not copy image:\n{e}")
            return
        rel = os.path.relpath(dest, get_project_dir())
        self.images_list.addItem(rel)

    def _del_img(self):
        for item in self.images_list.selectedItems():
            self.images_list.takeItem(self.images_list.row(item))

    def get_result(self):
        from PySide6.QtCore import QDate
        title = self.title_edit.text().strip()
        if not title:
            return None
        desc = self.desc_edit.toPlainText()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        images = [self.images_list.item(i).text() for i in range(self.images_list.count())]
        characters = [self.char_list.item(i).text() for i in range(self.char_list.count()) if self.char_list.item(i).isSelected()]
        places = [self.place_list.item(i).text() for i in range(self.place_list.count()) if self.place_list.item(i).isSelected()]
        return Event(title=title, description=desc, start_date=start_date, end_date=end_date, images=images, characters=characters, places=places)


# ---------- Tabs (listor & CRUD) ----------
class CharactersTab(QWidget):
    data_changed = Signal()
    def __init__(self, initial_chars: List[Character]):
        super().__init__()
        self.chars: List[Character] = [Character(**asdict(c)) if not isinstance(c, Character) else c for c in initial_chars]
        self.list = QListWidget(); self._refresh_list()
        add_btn = QPushButton("Add"); edit_btn = QPushButton("Edit"); del_btn = QPushButton("Delete")
        add_btn.clicked.connect(self._add); edit_btn.clicked.connect(self._edit); del_btn.clicked.connect(self._delete)
        row = QHBoxLayout(); row.addWidget(add_btn); row.addWidget(edit_btn); row.addWidget(del_btn)
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Characters:")); layout.addWidget(self.list); layout.addLayout(row)

    def _refresh_list(self):
        self.list.clear()
        for c in self.chars: self.list.addItem(c.name)

    def _add(self):
        dlg = CharacterForm(parent=self)
        if dlg.exec():
            ch = dlg.get_result()
            if ch and not any(c.name == ch.name for c in self.chars):
                self.chars.append(ch); self._refresh_list(); self.data_changed.emit()

    def _edit(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.chars): return
        dlg = CharacterForm(self.chars[idx], parent=self)
        if dlg.exec():
            ch = dlg.get_result()
            if ch: self.chars[idx] = ch; self._refresh_list(); self.data_changed.emit()

    def _delete(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.chars): return
        self.chars.pop(idx); self._refresh_list(); self.data_changed.emit()

    def values(self) -> List[Character]:
        return self.chars


class PlacesTab(QWidget):
    data_changed = Signal()
    def __init__(self, initial_places: List[Place]):
        super().__init__()
        self.places: List[Place] = [Place(**asdict(p)) if not isinstance(p, Place) else p for p in initial_places]
        self.list = QListWidget(); self._refresh_list()
        add_btn = QPushButton("Add"); edit_btn = QPushButton("Edit"); del_btn = QPushButton("Delete")
        add_btn.clicked.connect(self._add); edit_btn.clicked.connect(self._edit); del_btn.clicked.connect(self._delete)
        row = QHBoxLayout(); row.addWidget(add_btn); row.addWidget(edit_btn); row.addWidget(del_btn)
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Places:")); layout.addWidget(self.list); layout.addLayout(row)

    def _refresh_list(self):
        self.list.clear()
        for p in self.places: self.list.addItem(p.name)

    def _add(self):
        dlg = PlaceForm(parent=self)
        if dlg.exec():
            pl = dlg.get_result()
            if pl and not any(p.name == pl.name for p in self.places):
                self.places.append(pl); self._refresh_list(); self.data_changed.emit()

    def _edit(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.places): return
        dlg = PlaceForm(self.places[idx], parent=self)
        if dlg.exec():
            pl = dlg.get_result()
            if pl: self.places[idx] = pl; self._refresh_list(); self.data_changed.emit()

    def _delete(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.places): return
        self.places.pop(idx); self._refresh_list(); self.data_changed.emit()

    def values(self) -> List[Place]:
        return self.places


class EventsTab(QWidget):
    data_changed = Signal()
    def __init__(self, initial_events: List[Event], characters: List[Character] = None, places: List[Place] = None):
        super().__init__()
        self.events: List[Event] = [Event(**asdict(e)) if not isinstance(e, Event) else e for e in initial_events]
        self.characters: List[Character] = characters or []
        self.places: List[Place] = places or []
        self.list = QListWidget(); self._refresh_list()
        add_btn = QPushButton("Add"); edit_btn = QPushButton("Edit"); del_btn = QPushButton("Delete")
        add_btn.clicked.connect(self._add); edit_btn.clicked.connect(self._edit); del_btn.clicked.connect(self._delete)
        row = QHBoxLayout(); row.addWidget(add_btn); row.addWidget(edit_btn); row.addWidget(del_btn)
        layout = QVBoxLayout(self); layout.addWidget(QLabel("Events:")); layout.addWidget(self.list); layout.addLayout(row)

    def _refresh_list(self):
        self.list.clear()
        for e in self.events: self.list.addItem(e.title)

    def set_characters(self, characters: List[str]):
        self.characters = [Character(name=n) for n in characters]

    def set_places(self, places: List[str]):
        self.places = [Place(name=n) for n in places]

    def _add(self):
        dlg = EventForm(characters=self.characters, places=self.places, parent=self)
        if dlg.exec():
            ev = dlg.get_result()
            if ev and not any(e.title == ev.title for e in self.events):
                self.events.append(ev); self._refresh_list(); self.data_changed.emit()

    def _edit(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.events): return
        dlg = EventForm(self.events[idx], characters=self.characters, places=self.places, parent=self)
        if dlg.exec():
            ev = dlg.get_result()
            if ev: self.events[idx] = ev; self._refresh_list(); self.data_changed.emit()

    def _delete(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.events): return
        self.events.pop(idx); self._refresh_list(); self.data_changed.emit()

    def values(self) -> List[Event]:
        return self.events