This document explains how to install, run and use Timeline — a simple desktop application for keeping track of characters, places and events while writing fiction. The instructions assume a Linux environment and are written so that a user with little technical experience can follow them.

Contents

-Project overview
-Features
-Technical information
-Requirements
-Step‑by‑step: install and run
-Short user guide (common tasks)
 -Create/open projects
 -Add / edit characters
 --Add / edit places
 -Add / edit events
 -Use the timeline
-Where data is stored
-Troubleshooting (common problems and fixes)
-File structure (overview)
-Contact / further instructions
-Project overview Timeline helps authors organise characters, places and events. The program is a native desktop application (Qt via PySide6) and displays a timeline where events can be reviewed and edited. The design is simple and focuses on speeding up the most common workflows (add/delete/edit events).

Features (summary)
-Manage characters: name, description, colour, images.
-Manage places: name, description, images.
-Manage events: title, description, start/end date, images, selectable characters and places.
-Visual timeline with event cards.
-Quick editing via a small “info” icon on each event (edit characters, places or dates).
-Automatic saving when project data changes.


Technical information
-Language: Python (3.10+ recommended; works with 3.8+ in many cases).
-GUI: PySide6 (Qt for Python).
-Runs as a native desktop application (not Electron/web).
-Data is stored locally in the project folder: projects/<project_name>/data.json and images in projects/<project_name>/pictures/.


Requirements (Linux)
-Python 3.8 or later installed.
-pip available to install dependencies.
-A graphical desktop environment (X11 or Wayland). The program requires a display to show the window.


Installation (step‑by‑step)
-Unzip the provided ZIP file into a folder (for example ~/timeline).
-Open a terminal and change to the project folder, for example: cd ~/timeline
-Create and activate a virtual environment (recommended): python3 -m venv venv source venv/bin/activate
-Install dependencies: pip install --upgrade pip pip install PySide6 (If you want to pin dependencies, create a requirements.txt with PySide6 and run pip install -r requirements.txt)
-Done — proceed to “Run the application”.


Run the application: python -m app.main

Common tasks — step‑by‑step

A. Create a project (first run)
-On first start, if no projects exist the application creates a default project named "default". Otherwise a project dialog appears where you can choose an existing project.


B. Add a character
-Go to the "Characters" tab.
-Click "Add".
-Enter a name (required), description, pick a colour from the palette, and add images (optional).
-Click OK — the character is saved to the project.


C. Add a place
-Go to the "Places" tab.
-Click "Add".
-Enter a name, description and images (optional).
-Click OK.


D. Edit an event
-In the "Events" tab: select an event and click "Edit".
-Or in the "Timeline":
-Click the small "i" icon on the event card to quick-edit characters, places or dates.
-Double-click the event card to open the full editor for all fields.


F. Delete items
-Select an item in its tab and click "Delete". Confirm the prompt.


G. Save
-The application attempts to save automatically when changes occur.
-You can press Ctrl+S to force a save.
-You can also use the Apply/Clear buttons in the UI where available.


Where data is stored
-After unzipping, a folder projects/ is created in the project root.
-Each project is stored in projects/<project_name>/.
-Data file: projects/<project_name>/data.json
-Images are copied to: projects/<project_name>/pictures/
-The currently selected project name is written to .current_project in the project root.


Troubleshooting — common problems and fixes
1.No GUI window appears / "Could not connect to display"
-Ensure you are running on a graphical desktop (X11 or Wayland).
Check environment variables:
 -DISPLAY should be set (X11) or WAYLAND_DISPLAY (Wayland).
 -In a terminal: echo $DISPLAY
-If you run over SSH without X forwarding: enable X forwarding or run locally.
-For automated tests or CI: use xvfb-run -a python -m app.main.

2.PySide6 missing or import errors

-Activate your virtualenv and run: pip install PySide6
-Check Python version: python3 --version

3.Menu or dialog opens off-screen (especially when zoomed)
-This can happen at high zoom levels or after scrolling. Move the main window or reset zoom (Ctrl+0).
-If necessary, close and reopen the dialog.

4."Duplicate title" when adding an event
-Event titles must be unique. Choose a different title.

5.Data lost or corrupted
-Inspect projects/<project>/data.json. If it is missing or corrupted, restore from backup.
-The program will recreate data.json if it is missing, but any previous data will be lost.


Quick reference (keyboard & quick tips)

 -Start: python -m app.main
 -Save: Ctrl+S
 -Zoom in: Ctrl++ or Ctrl+=
 -Zoom out: Ctrl+-
 -Reset zoom: Ctrl+0
 -UI structure:
  -Tabs: Characters, Places, Events, Timeline
  -Create new: Add button in each tab
  -Timeline shortcuts: double-click background = add event, double-click card = edit event, "i" icon = quick-edit


Files and structure (overview)
-app/
 -main.py — entry point
 -models.py — data models (Character, Place, Event)
 -storage.py — project and data file handling
 -ui/
  -tabs.py — forms and tabs (Characters/Places/Events)
  -timeline.py — timeline view and interaction
  -project_dialog.py — project selection dialog
-projects/ — contains project data (created at runtime)
-README.md — this document

Final note These are the precise, practical instructions for running and using Timeline locally on a Linux machine. Follow them in order — unzip, create a virtualenv, install PySide6 and start the program with python -m app.main. Everything needed is included in the code inside the ZIP file.