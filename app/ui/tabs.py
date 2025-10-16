from __future__ import annotations
from dataclasses import asdict
from typing import List
import os
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox, QColorDialog,
    QFileDialog, QDateEdit, QDialog, QDialogButtonBox, QComboBox
)
from ..models import Character, Place, Event

class CharacterForm(QDialog):
    def __init__(self, character: Character = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Character")
        self.setModal(True)
        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self._pick_color)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.desc_edit)
        layout.addWidget(QLabel("Color:"))
        layout.addWidget(self.color_btn)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.character = character
        if character:
            self.name_edit.setText(character.name)
            self.desc_edit.setPlainText(character.description)
            self.color_btn.setStyleSheet(f"background:{character.color}")
            self.color_btn.setText(character.color)
        else:
            self.color_btn.setText("#eedada")

    def _pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_btn.setStyleSheet(f"background:{color.name()}")
            self.color_btn.setText(color.name())

    def get_result(self):
        name = self.name_edit.text().strip()
        if not name:
            return None
        desc = self.desc_edit.toPlainText()
        color = self.color_btn.text()
        return Character(name=name, description=desc, color=color)

class PlaceForm(QDialog):
    def __init__(self, place: Place = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Place")
        self.setModal(True)
        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.desc_edit)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.place = place
        if place:
            self.name_edit.setText(place.name)
            self.desc_edit.setPlainText(place.description)

    def get_result(self):
        name = self.name_edit.text().strip()
        if not name:
            return None
        desc = self.desc_edit.toPlainText()
        return Place(name=name, description=desc)

class EventForm(QDialog):
    def __init__(self, event: Event = None, characters: List[Character] = None, places: List[Place] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Event")
        self.setModal(True)
        self.title_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.images_list = QListWidget()
        self.add_img_btn = QPushButton("Add Image")
        self.add_img_btn.clicked.connect(self._add_img)
        self.del_img_btn = QPushButton("Delete Image")
        self.del_img_btn.clicked.connect(self._del_img)
        self.char_combo = QListWidget()
        self.char_combo.setSelectionMode(QListWidget.MultiSelection)
        for c in (characters or []):
            self.char_combo.addItem(c.name)
        self.place_combo = QListWidget()
        self.place_combo.setSelectionMode(QListWidget.MultiSelection)
        for p in (places or []):
            self.place_combo.addItem(p.name)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Title:"))
        layout.addWidget(self.title_edit)
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.desc_edit)
        layout.addWidget(QLabel("Start date:"))
        layout.addWidget(self.start_date_edit)
        layout.addWidget(QLabel("End date:"))
        layout.addWidget(self.end_date_edit)
        layout.addWidget(QLabel("Images:"))
        layout.addWidget(self.images_list)
        hl = QHBoxLayout()
        hl.addWidget(self.add_img_btn)
        hl.addWidget(self.del_img_btn)
        layout.addLayout(hl)
        layout.addWidget(QLabel("Characters:"))
        layout.addWidget(self.char_combo)
        layout.addWidget(QLabel("Places:"))
        layout.addWidget(self.place_combo)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
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
            for i in range(self.char_combo.count()):
                if event.characters and self.char_combo.item(i).text() in event.characters:
                    self.char_combo.item(i).setSelected(True)
            for i in range(self.place_combo.count()):
                if event.places and self.place_combo.item(i).text() in event.places:
                    self.place_combo.item(i).setSelected(True)
        self.selected_images = list(event.images) if event else []

    def _add_img(self):
        from ..storage import get_pictures_dir, get_project_dir
        folder = str(get_pictures_dir())
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Image", folder,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        )
        if file:
            rel = os.path.relpath(file, str(get_project_dir()))
            if not rel.startswith("pictures/") and not rel.startswith("pictures\\"):
                QMessageBox.warning(self, "Not in pictures/", "Please only add images from the 'pictures/' folder.")
                return
            self.images_list.addItem(rel)

    def _del_img(self):
        for item in self.images_list.selectedItems():
            self.images_list.takeItem(self.images_list.row(item))

    def get_result(self):
        title = self.title_edit.text().strip()
        if not title:
            return None
        desc = self.desc_edit.toPlainText()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        images = [self.images_list.item(i).text() for i in range(self.images_list.count())]
        characters = [self.char_combo.item(i).text() for i in range(self.char_combo.count()) if self.char_combo.item(i).isSelected()]
        places = [self.place_combo.item(i).text() for i in range(self.place_combo.count()) if self.place_combo.item(i).isSelected()]
        return Event(
            title=title,
            description=desc,
            start_date=start_date,
            end_date=end_date,
            images=images,
            characters=characters,
            places=places
        )

class CharactersTab(QWidget):
    data_changed = Signal()
    def __init__(self, initial_chars: List[Character]):
        super().__init__()
        self.chars: List[Character] = [Character(**asdict(c)) if not isinstance(c, Character) else c for c in initial_chars]
        self.list = QListWidget()
        self._refresh_list()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        del_btn = QPushButton("Delete")
        add_btn.clicked.connect(self._add)
        edit_btn.clicked.connect(self._edit)
        del_btn.clicked.connect(self._delete)
        btnrow = QHBoxLayout()
        btnrow.addWidget(add_btn)
        btnrow.addWidget(edit_btn)
        btnrow.addWidget(del_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Characters:"))
        layout.addWidget(self.list)
        layout.addLayout(btnrow)

    def _refresh_list(self):
        self.list.clear()
        for c in self.chars:
            self.list.addItem(c.name)

    def _add(self):
        dlg = CharacterForm(parent=self)
        if dlg.exec() == QDialog.Accepted:
            char = dlg.get_result()
            if char and not any(c.name == char.name for c in self.chars):
                self.chars.append(char)
                self._refresh_list()
                self.data_changed.emit()

    def _edit(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.chars):
            return
        dlg = CharacterForm(self.chars[idx], parent=self)
        if dlg.exec() == QDialog.Accepted:
            char = dlg.get_result()
            if char:
                self.chars[idx] = char
                self._refresh_list()
                self.data_changed.emit()

    def _delete(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.chars):
            return
        self.chars.pop(idx)
        self._refresh_list()
        self.data_changed.emit()

    def values(self) -> List[Character]:
        return self.chars

class PlacesTab(QWidget):
    data_changed = Signal()
    def __init__(self, initial_places: List[Place]):
        super().__init__()
        self.places: List[Place] = [Place(**asdict(p)) if not isinstance(p, Place) else p for p in initial_places]
        self.list = QListWidget()
        self._refresh_list()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        del_btn = QPushButton("Delete")
        add_btn.clicked.connect(self._add)
        edit_btn.clicked.connect(self._edit)
        del_btn.clicked.connect(self._delete)
        btnrow = QHBoxLayout()
        btnrow.addWidget(add_btn)
        btnrow.addWidget(edit_btn)
        btnrow.addWidget(del_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Places:"))
        layout.addWidget(self.list)
        layout.addLayout(btnrow)

    def _refresh_list(self):
        self.list.clear()
        for p in self.places:
            self.list.addItem(p.name)

    def _add(self):
        dlg = PlaceForm(parent=self)
        if dlg.exec() == QDialog.Accepted:
            place = dlg.get_result()
            if place and not any(p.name == place.name for p in self.places):
                self.places.append(place)
                self._refresh_list()
                self.data_changed.emit()

    def _edit(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.places):
            return
        dlg = PlaceForm(self.places[idx], parent=self)
        if dlg.exec() == QDialog.Accepted:
            place = dlg.get_result()
            if place:
                self.places[idx] = place
                self._refresh_list()
                self.data_changed.emit()

    def _delete(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.places):
            return
        self.places.pop(idx)
        self._refresh_list()
        self.data_changed.emit()

    def values(self) -> List[Place]:
        return self.places

class EventsTab(QWidget):
    data_changed = Signal()
    def __init__(self, initial_events: List[Event], characters: List[Character]=None, places: List[Place]=None):
        super().__init__()
        self.events: List[Event] = [Event(**asdict(e)) if not isinstance(e, Event) else e for e in initial_events]
        self.characters: List[Character] = characters or []
        self.places: List[Place] = places or []
        self.list = QListWidget()
        self._refresh_list()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        del_btn = QPushButton("Delete")
        add_btn.clicked.connect(self._add)
        edit_btn.clicked.connect(self._edit)
        del_btn.clicked.connect(self._delete)
        btnrow = QHBoxLayout()
        btnrow.addWidget(add_btn)
        btnrow.addWidget(edit_btn)
        btnrow.addWidget(del_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Events:"))
        layout.addWidget(self.list)
        layout.addLayout(btnrow)

    def _refresh_list(self):
        self.list.clear()
        for e in self.events:
            self.list.addItem(e.title)

    def set_characters(self, characters: List[str]):
        self.characters = [Character(name=n) for n in characters]

    def set_places(self, places: List[str]):
        self.places = [Place(name=n) for n in places]

    def _add(self):
        dlg = EventForm(characters=self.characters, places=self.places, parent=self)
        if dlg.exec() == QDialog.Accepted:
            event = dlg.get_result()
            if event and not any(e.title == event.title for e in self.events):
                self.events.append(event)
                self._refresh_list()
                self.data_changed.emit()

    def _edit(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.events):
            return
        dlg = EventForm(self.events[idx], characters=self.characters, places=self.places, parent=self)
        if dlg.exec() == QDialog.Accepted:
            event = dlg.get_result()
            if event:
                self.events[idx] = event
                self._refresh_list()
                self.data_changed.emit()

    def _delete(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.events):
            return
        self.events.pop(idx)
        self._refresh_list()
        self.data_changed.emit()

    def values(self) -> List[Event]:
        return self.events