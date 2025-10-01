from __future__ import annotations
from dataclasses import asdict
from typing import List
import os
from PySide6.QtCore import Qt,QDate, Signal
from PySide6.QtGui import QColor, QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QTextEdit, QPushButton, QLabel, QMessageBox, QColorDialog,
    QFileDialog, QListView, QInputDialog, QDialog, QDialogButtonBox, QGridLayout,
    QDateEdit
)
from ..models import Character, Place, Event

def _shorten(text: str, max_len: int = 60) -> str:
    text = (text or "").replace("\n", " ")
    return text if len(text) <= max_len else text[: max_len - 1] + "…"

def _add_image_item(images_list, img_path):
    full_path = os.path.join(os.getcwd(), img_path)
    item = QListWidgetItem(os.path.basename(img_path))
    if os.path.exists(full_path):
        icon = QIcon(full_path)
        item.setIcon(icon)
    item.setToolTip(img_path)
    images_list.addItem(item)

class CharactersTab(QWidget):
    """
    A full-featured characters tab: select a character and edit all fields.
    """
    data_changed = Signal()

    def __init__(self, initial_chars: List[Character]):
        super().__init__()
        self.chars: List[Character] = [Character(**asdict(c)) if not isinstance(c, Character) else c for c in initial_chars]
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SingleSelection)
        for c in self.chars:
            self.list.addItem(QListWidgetItem(c.name))
        self.list.currentRowChanged.connect(self._on_select)

        add_btn = QPushButton("Add Character")
        del_btn = QPushButton("Delete selected")
        add_btn.clicked.connect(self._add_char)
        del_btn.clicked.connect(self._delete_selected)

        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self._pick_color)
        self.texts_list = QListWidget()
        self.add_text_btn = QPushButton("Add Note")
        self.del_text_btn = QPushButton("Delete Note")
        self.add_text_btn.clicked.connect(self._add_text)
        self.del_text_btn.clicked.connect(self._del_text)
        self.images_list = QListWidget()
        self.add_img_btn = QPushButton("Add Image")
        self.del_img_btn = QPushButton("Delete Image")
        self.add_img_btn.clicked.connect(self._add_img)
        self.del_img_btn.clicked.connect(self._del_img)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current)

        form = QGridLayout()
        form.addWidget(QLabel("Name"), 0, 0)
        form.addWidget(self.name_edit, 0, 1)
        form.addWidget(QLabel("Description"), 1, 0)
        form.addWidget(self.desc_edit, 1, 1)
        form.addWidget(QLabel("Color"), 2, 0)
        form.addWidget(self.color_btn, 2, 1)
        form.addWidget(QLabel("Texts/Notes"), 3, 0)
        form.addWidget(self.texts_list, 3, 1)
        form.addWidget(self.add_text_btn, 4, 1)
        form.addWidget(self.del_text_btn, 5, 1)
        form.addWidget(QLabel("Images"), 6, 0)
        form.addWidget(self.images_list, 6, 1)
        form.addWidget(self.add_img_btn, 7, 1)
        form.addWidget(self.del_img_btn, 8, 1)
        form.addWidget(self.save_btn, 9, 0, 1, 2)

        left = QVBoxLayout()
        left.addWidget(self.list)
        left.addWidget(add_btn)
        left.addWidget(del_btn)

        main = QHBoxLayout(self)
        main.addLayout(left, 1)
        main.addLayout(form, 2)

        self.list.setCurrentRow(0)

    def _on_select(self, row):
        if row < 0 or row >= len(self.chars):
            self._clear_details()
            return
        c = self.chars[row]
        self.name_edit.setText(c.name)
        self.desc_edit.setPlainText(c.description)
        self.color_btn.setStyleSheet(f"background:{c.color}")
        self.color_btn.setText(c.color)
        self.texts_list.clear()
        for t in c.texts:
            self.texts_list.addItem(QListWidgetItem(t))
        self.images_list.clear()
        for img in c.images:
            _add_image_item(self.images_list, img)

    def _save_current(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.chars):
            return
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Name cannot be empty.")
            return
        for i, cc in enumerate(self.chars):
            if i != row and cc.name.lower() == name.lower():
                QMessageBox.warning(self, "Duplicate", "Another character has this name.")
                return
        c = self.chars[row]
        c.name = name
        c.description = self.desc_edit.toPlainText()
        c.color = self.color_btn.text()
        c.texts = [self.texts_list.item(i).text() for i in range(self.texts_list.count())]
        c.images = [self.images_list.item(i).toolTip() for i in range(self.images_list.count())]
        self.list.item(row).setText(c.name)
        self.data_changed.emit()

    def _clear_details(self):
        self.name_edit.clear()
        self.desc_edit.clear()
        self.color_btn.setStyleSheet("")
        self.color_btn.setText("")
        self.texts_list.clear()
        self.images_list.clear()

    def _add_char(self):
        name, ok = QInputDialog.getText(self, "Add Character", "Character name?")
        if not ok or not name.strip():
            return
        if any(c.name.lower() == name.strip().lower() for c in self.chars):
            QMessageBox.warning(self, "Duplicate", "Character already exists.")
            return
        c = Character(name=name.strip())
        self.chars.append(c)
        self.list.addItem(QListWidgetItem(c.name))
        self.list.setCurrentRow(self.list.count() - 1)
        self.data_changed.emit()

    def _delete_selected(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.chars):
            return
        self.chars.pop(row)
        self.list.takeItem(row)
        self.list.setCurrentRow(0 if self.chars else -1)
        self.data_changed.emit()

    def _pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_btn.setStyleSheet(f"background:{color.name()}")
            self.color_btn.setText(color.name())

    def _add_text(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Note", "Text:")
        if ok and text.strip():
            self.texts_list.addItem(QListWidgetItem(text.strip()))

    def _del_text(self):
        for item in self.texts_list.selectedItems():
            self.texts_list.takeItem(self.texts_list.row(item))

    def _add_img(self):
        folder = os.path.join(os.getcwd(), "pictures")
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        file, _ = QFileDialog.getOpenFileName(self, "Select Image", folder, "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)")
        if file:
            rel = os.path.relpath(file, os.getcwd())
            if not rel.startswith("pictures/") and not rel.startswith("pictures\\"):
                QMessageBox.warning(self, "Not in pictures/", "Please only add images from the 'pictures/' folder.")
                return
            _add_image_item(self.images_list, rel)
            self.data_changed.emit()

    def _del_img(self):
        for item in self.images_list.selectedItems():
            self.images_list.takeItem(self.images_list.row(item))
        self.data_changed.emit()

    def values(self) -> List[Character]:
        self._save_current()
        return self.chars

class PlacesTab(QWidget):
    """
    A full-featured places tab: select a place and edit all fields.
    """
    data_changed = Signal()

    def __init__(self, initial_places: List[Place]):
        super().__init__()
        self.places: List[Place] = [Place(**asdict(p)) if not isinstance(p, Place) else p for p in initial_places]
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SingleSelection)
        for p in self.places:
            self.list.addItem(QListWidgetItem(p.name))
        self.list.currentRowChanged.connect(self._on_select)

        add_btn = QPushButton("Add Place")
        del_btn = QPushButton("Delete selected")
        add_btn.clicked.connect(self._add_place)
        del_btn.clicked.connect(self._delete_selected)

        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.texts_list = QListWidget()
        self.add_text_btn = QPushButton("Add Note")
        self.del_text_btn = QPushButton("Delete Note")
        self.add_text_btn.clicked.connect(self._add_text)
        self.del_text_btn.clicked.connect(self._del_text)
        self.images_list = QListWidget()
        self.add_img_btn = QPushButton("Add Image")
        self.del_img_btn = QPushButton("Delete Image")
        self.add_img_btn.clicked.connect(self._add_img)
        self.del_img_btn.clicked.connect(self._del_img)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current)

        form = QGridLayout()
        form.addWidget(QLabel("Name"), 0, 0)
        form.addWidget(self.name_edit, 0, 1)
        form.addWidget(QLabel("Description"), 1, 0)
        form.addWidget(self.desc_edit, 1, 1)
        form.addWidget(QLabel("Texts/Notes"), 2, 0)
        form.addWidget(self.texts_list, 2, 1)
        form.addWidget(self.add_text_btn, 3, 1)
        form.addWidget(self.del_text_btn, 4, 1)
        form.addWidget(QLabel("Images"), 5, 0)
        form.addWidget(self.images_list, 5, 1)
        form.addWidget(self.add_img_btn, 6, 1)
        form.addWidget(self.del_img_btn, 7, 1)
        form.addWidget(self.save_btn, 8, 0, 1, 2)

        left = QVBoxLayout()
        left.addWidget(self.list)
        left.addWidget(add_btn)
        left.addWidget(del_btn)

        main = QHBoxLayout(self)
        main.addLayout(left, 1)
        main.addLayout(form, 2)

        self.list.setCurrentRow(0)

    def _on_select(self, row):
        if row < 0 or row >= len(self.places):
            self._clear_details()
            return
        p = self.places[row]
        self.name_edit.setText(p.name)
        self.desc_edit.setPlainText(p.description)
        self.texts_list.clear()
        for t in p.texts:
            self.texts_list.addItem(QListWidgetItem(t))
        self.images_list.clear()
        for img in p.images:
            _add_image_item(self.images_list, img)

    def _save_current(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.places):
            return
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Name cannot be empty.")
            return
        for i, pp in enumerate(self.places):
            if i != row and pp.name.lower() == name.lower():
                QMessageBox.warning(self, "Duplicate", "Another place has this name.")
                return
        p = self.places[row]
        p.name = name
        p.description = self.desc_edit.toPlainText()
        p.texts = [self.texts_list.item(i).text() for i in range(self.texts_list.count())]
        p.images = [self.images_list.item(i).toolTip() for i in range(self.images_list.count())]
        self.list.item(row).setText(p.name)
        self.data_changed.emit()

    def _clear_details(self):
        self.name_edit.clear()
        self.desc_edit.clear()
        self.texts_list.clear()
        self.images_list.clear()

    def _add_place(self):
        name, ok = QInputDialog.getText(self, "Add Place", "Place name?")
        if not ok or not name.strip():
            return
        if any(p.name.lower() == name.strip().lower() for p in self.places):
            QMessageBox.warning(self, "Duplicate", "Place already exists.")
            return
        p = Place(name=name.strip())
        self.places.append(p)
        self.list.addItem(QListWidgetItem(p.name))
        self.list.setCurrentRow(self.list.count() - 1)
        self.data_changed.emit()

    def _delete_selected(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.places):
            return
        self.places.pop(row)
        self.list.takeItem(row)
        self.list.setCurrentRow(0 if self.places else -1)
        self.data_changed.emit()

    def _add_text(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Note", "Text:")
        if ok and text.strip():
            self.texts_list.addItem(QListWidgetItem(text.strip()))

    def _del_text(self):
        for item in self.texts_list.selectedItems():
            self.texts_list.takeItem(self.texts_list.row(item))

    def _add_img(self):
        folder = os.path.join(os.getcwd(), "pictures")
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        file, _ = QFileDialog.getOpenFileName(self, "Select Image", folder, "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)")
        if file:
            rel = os.path.relpath(file, os.getcwd())
            if not rel.startswith("pictures/") and not rel.startswith("pictures\\"):
                QMessageBox.warning(self, "Not in pictures/", "Please only add images from the 'pictures/' folder.")
                return
            _add_image_item(self.images_list, rel)
            self.data_changed.emit()

    def _del_img(self):
        for item in self.images_list.selectedItems():
            self.images_list.takeItem(self.images_list.row(item))
        self.data_changed.emit()

    def values(self) -> List[Place]:
        self._save_current()
        return self.places


class ListTab(QWidget):
    """Generic list tab for Characters and Places."""
    def __init__(self, label_singular: str, initial_items: List[str]):
        super().__init__()
        self.label_singular = label_singular

        self.list = QListWidget()
        for name in initial_items:
            self.list.addItem(QListWidgetItem(name))

        self.input = QLineEdit()
        self.input.setPlaceholderText(f"Add {label_singular.lower()}…")

        add_btn = QPushButton(f"Add {label_singular}")
        del_btn = QPushButton("Delete selected")

        add_btn.clicked.connect(self.add_item)
        del_btn.clicked.connect(self.delete_selected)

        top = QHBoxLayout()
        top.addWidget(self.input)
        top.addWidget(add_btn)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(del_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.list)
        layout.addLayout(bottom)

    def add_item(self):
        text = self.input.text().strip()
        if not text:
            return
        existing = [self.list.item(i).text().lower() for i in range(self.list.count())]
        if text.lower() in existing:
            QMessageBox.information(self, "Already exists", f"{self.label_singular} '{text}' already exists.")
            return
        self.list.addItem(QListWidgetItem(text))
        self.input.clear()

    def delete_selected(self):
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))

    def values(self) -> List[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]


class EventsTab(QWidget):
    """
    Full-featured Events tab: add/edit all fields, associate characters/places, texts, images.
    """
    def __init__(self, initial_events: List[Event], characters: List[Character]=None, places: List[Place]=None):
        super().__init__()
        self.events: List[Event] = [Event(**asdict(e)) if not isinstance(e, Event) else e for e in initial_events]
        self.characters: List[str] = [c.name for c in (characters or [])]
        self.places: List[str] = [p.name for p in (places or [])]

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SingleSelection)
        for e in self.events:
            self.list.addItem(QListWidgetItem(e.title))
        self.list.currentRowChanged.connect(self._on_select)

        add_btn = QPushButton("Add Event")
        del_btn = QPushButton("Delete selected")
        add_btn.clicked.connect(self._add_event)
        del_btn.clicked.connect(self._delete_selected)

        self.title_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setSpecialValueText("")

        self.texts_list = QListWidget()
        self.add_text_btn = QPushButton("Add Note")
        self.del_text_btn = QPushButton("Delete Note")
        self.add_text_btn.clicked.connect(self._add_text)
        self.del_text_btn.clicked.connect(self._del_text)

        self.images_list = QListWidget()
        self.add_img_btn = QPushButton("Add Image")
        self.del_img_btn = QPushButton("Delete Image")
        self.add_img_btn.clicked.connect(self._add_img)
        self.del_img_btn.clicked.connect(self._del_img)

        self.char_list = QListWidget()
        self.char_list.setSelectionMode(QListWidget.MultiSelection)
        self.place_list = QListWidget()
        self.place_list.setSelectionMode(QListWidget.MultiSelection)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current)

        form = QGridLayout()
        form.addWidget(QLabel("Title"), 0, 0)
        form.addWidget(self.title_edit, 0, 1)
        form.addWidget(QLabel("Description"), 1, 0)
        form.addWidget(self.desc_edit, 1, 1)
        form.addWidget(QLabel("Start date"), 2, 0)
        form.addWidget(self.start_date, 2, 1)
        form.addWidget(QLabel("End date"), 3, 0)
        form.addWidget(self.end_date, 3, 1)
        form.addWidget(QLabel("Texts/Notes"), 4, 0)
        form.addWidget(self.texts_list, 4, 1)
        form.addWidget(self.add_text_btn, 5, 1)
        form.addWidget(self.del_text_btn, 6, 1)
        form.addWidget(QLabel("Images"), 7, 0)
        form.addWidget(self.images_list, 7, 1)
        form.addWidget(self.add_img_btn, 8, 1)
        form.addWidget(self.del_img_btn, 9, 1)
        form.addWidget(QLabel("Characters"), 10, 0)
        form.addWidget(self.char_list, 10, 1)
        form.addWidget(QLabel("Places"), 11, 0)
        form.addWidget(self.place_list, 11, 1)
        form.addWidget(self.save_btn, 12, 0, 1, 2)

        left = QVBoxLayout()
        left.addWidget(self.list)
        left.addWidget(add_btn)
        left.addWidget(del_btn)

        main = QHBoxLayout(self)
        main.addLayout(left, 1)
        main.addLayout(form, 2)

        self._refresh_char_place_lists()
        self.list.setCurrentRow(0)

    def _refresh_char_place_lists(self):
        self.char_list.clear()
        for name in self.characters:
            item = QListWidgetItem(name)
            self.char_list.addItem(item)
        self.place_list.clear()
        for name in self.places:
            item = QListWidgetItem(name)
            self.place_list.addItem(item)

    def set_characters(self, characters: List[str]):
        self.characters = characters
        self._refresh_char_place_lists()

    def set_places(self, places: List[str]):
        self.places = places
        self._refresh_char_place_lists()

    def _on_select(self, row):
        if row < 0 or row >= len(self.events):
            self._clear_details()
            return
        e = self.events[row]
        self.title_edit.setText(e.title)
        self.desc_edit.setPlainText(e.description)
        try:
            if e.start_date:
                self.start_date.setDate(QDate.fromString(e.start_date, "yyyy-MM-dd"))
            else:
                self.start_date.setDate(QDate.currentDate())
            if e.end_date:
                self.end_date.setDate(QDate.fromString(e.end_date, "yyyy-MM-dd"))
            else:
                self.end_date.setDate(QDate.currentDate())
        except Exception:
            self.start_date.setDate(QDate.currentDate())
            self.end_date.setDate(QDate.currentDate())
        self.texts_list.clear()
        for t in e.texts:
            self.texts_list.addItem(QListWidgetItem(t))
        self.images_list.clear()
        for img in e.images:
            self.images_list.addItem(QListWidgetItem(img))
        self._refresh_char_place_lists()
        for i in range(self.char_list.count()):
            item = self.char_list.item(i)
            item.setSelected(item.text() in e.characters)
        for i in range(self.place_list.count()):
            item = self.place_list.item(i)
            item.setSelected(item.text() in e.places)

    def _save_current(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.events):
            return
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing title", "Title cannot be empty.")
            return
        for i, ee in enumerate(self.events):
            if i != row and ee.title.lower() == title.lower():
                QMessageBox.warning(self, "Duplicate", "Another event has this title.")
                return
        e = self.events[row]
        e.title = title
        e.description = self.desc_edit.toPlainText()
        e.start_date = self.start_date.date().toString("yyyy-MM-dd")
        e.end_date = self.end_date.date().toString("yyyy-MM-dd") if self.end_date.date() != self.start_date.date() else ""
        e.texts = [self.texts_list.item(i).text() for i in range(self.texts_list.count())]
        e.images = [self.images_list.item(i).text() for i in range(self.images_list.count())]
        e.characters = [self.char_list.item(i).text() for i in range(self.char_list.count()) if self.char_list.item(i).isSelected()]
        e.places = [self.place_list.item(i).text() for i in range(self.place_list.count()) if self.place_list.item(i).isSelected()]
        self.list.item(row).setText(e.title)

    def _clear_details(self):
        self.title_edit.clear()
        self.desc_edit.clear()
        self.start_date.setDate(QDate.currentDate())
        self.end_date.setDate(QDate.currentDate())
        self.texts_list.clear()
        self.images_list.clear()
        self._refresh_char_place_lists()

    def _add_event(self):
        title, ok = QInputDialog.getText(self, "Add Event", "Event title?")
        if not ok or not title.strip():
            return
        if any(e.title.lower() == title.strip().lower() for e in self.events):
            QMessageBox.warning(self, "Duplicate", "Event already exists.")
            return
        e = Event(title=title.strip())
        self.events.append(e)
        self.list.addItem(QListWidgetItem(e.title))
        self.list.setCurrentRow(self.list.count() - 1)

    def _delete_selected(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.events):
            return
        self.events.pop(row)
        self.list.takeItem(row)
        self.list.setCurrentRow(0 if self.events else -1)

    def _add_text(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Note", "Text:")
        if ok and text.strip():
            self.texts_list.addItem(QListWidgetItem(text.strip()))

    def _del_text(self):
        for item in self.texts_list.selectedItems():
            self.texts_list.takeItem(self.texts_list.row(item))

    def _add_img(self):
        folder = os.path.join(os.getcwd(), "pictures")
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        file, _ = QFileDialog.getOpenFileName(self, "Select Image", folder, "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)")
        if file:
            rel = os.path.relpath(file, os.getcwd())
            if not rel.startswith("pictures/") and not rel.startswith("pictures\\"):
                QMessageBox.warning(self, "Not in pictures/", "Please only add images from the 'pictures/' folder.")
                return
            self.images_list.addItem(QListWidgetItem(rel))

    def _del_img(self):
        for item in self.images_list.selectedItems():
            self.images_list.takeItem(self.images_list.row(item))

    def values(self) -> List[Event]:
        self._save_current()
        return self.events