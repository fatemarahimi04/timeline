from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QHBoxLayout, QPushButton, QInputDialog, QMessageBox
)
from ...  import __init__ 
from ..storage import list_projects, create_project, delete_project

class ProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Project")
        self.setModal(True)

        self.list = QListWidget()
        self._reload()

        self.btn_new = QPushButton("New")
        self.btn_open = QPushButton("Open")
        self.btn_delete = QPushButton("Delete")
        self.btn_cancel = QPushButton("Cancel")

        self.btn_new.clicked.connect(self._new)
        self.btn_open.clicked.connect(self.accept)
        self.btn_delete.clicked.connect(self._delete)
        self.btn_cancel.clicked.connect(self.reject)

        top = QVBoxLayout(self)
        top.addWidget(QLabel("Choose a project:"))
        top.addWidget(self.list)

        row = QHBoxLayout()
        row.addWidget(self.btn_new)
        row.addWidget(self.btn_delete)
        row.addStretch(1)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_open)
        top.addLayout(row)

        self.list.itemDoubleClicked.connect(lambda *_: self.accept())

    def _reload(self):
        self.list.clear()
        for name in list_projects():
            self.list.addItem(QListWidgetItem(name))

    def selected_name(self) -> Optional[str]:
        it = self.list.currentItem()
        return it.text() if it else None

    def _new(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if ok:
            name = name.strip()
            if not name:
                QMessageBox.warning(self, "Invalid", "Please enter a project name.")
                return
            try:
                create_project(name)
                self._reload()
                matches = self.list.findItems(name, Qt.MatchExactly)
                if matches:
                    self.list.setCurrentItem(matches[0])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Couldn't create project:\n{e}")

    def _delete(self):
        name = self.selected_name()
        if not name:
            QMessageBox.information(self, "No selection", "Select a project to delete.")
            return
        if QMessageBox.question(self, "Delete Project", f"Delete '{name}'? This cannot be undone.") == QMessageBox.Yes:
            try:
                delete_project(name)
                self._reload()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Couldn't delete project:\n{e}")
