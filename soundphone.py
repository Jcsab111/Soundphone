import sys
import os
import shutil
import json
import random
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox,
    QToolBar, QAction, QLabel, QWidget, QVBoxLayout,
    QTreeView, QInputDialog, QListWidget, QMenu,
    QSlider, QHBoxLayout, QPushButton, QComboBox, QListWidgetItem
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileSystemModel


APP_NAME = "Soundphone"
AUDIO_FOLDER = os.path.join(os.getenv("LOCALAPPDATA"), "Soundphone Audios")
URL_HISTORY_FILE = os.path.join(AUDIO_FOLDER, "url_history.json")
CONFIG_FILE = os.path.join(AUDIO_FOLDER, "config.json")


# ---------------- URL HISTORY WINDOW ----------------
class URLHistoryWindow(QWidget):
    def __init__(self, parent, urls):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("URL Audio History")
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.addItems(urls)
        self.list_widget.itemDoubleClicked.connect(self.play_url)
        layout.addWidget(self.list_widget)

    def play_url(self, item):
        url = item.text()
        self.parent.player.stop()
        self.parent.player.setMedia(QMediaContent(QUrl(url)))
        self.parent.player.play()
        self.parent.info.setText(f"Streaming:\n{url}")


# ---------------- VOLUME WINDOW ----------------
class VolumeWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("Set Volume")
        self.resize(300, 80)

        layout = QVBoxLayout(self)
        slider_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(self.parent.player.volume())
        self.slider.valueChanged.connect(self.set_volume)
        slider_layout.addWidget(QLabel("Volume:"))
        slider_layout.addWidget(self.slider)
        layout.addLayout(slider_layout)

    def set_volume(self, value):
        self.parent.player.setVolume(value)
        if hasattr(self.parent, "volume_label"):
            self.parent.volume_label.setText(f"{value}%")


# ---------------- THEME WINDOW ----------------
class ThemeWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("Select Theme")
        self.resize(350, 150)

        layout = QVBoxLayout(self)

        self.combo = QComboBox()
        self.combo.addItems(["Fusion", "Windows", "WindowsVista", "Macintosh"])
        layout.addWidget(QLabel("Choose default theme:"))
        layout.addWidget(self.combo)

        apply_btn = QPushButton("Apply Theme")
        apply_btn.clicked.connect(self.apply_theme)
        layout.addWidget(apply_btn)

        custom_btn = QPushButton("Custom Theme (Select .qss file)")
        custom_btn.clicked.connect(self.apply_custom_theme)
        layout.addWidget(custom_btn)

        reset_btn = QPushButton("Reset Theme")
        reset_btn.clicked.connect(self.reset_theme)
        layout.addWidget(reset_btn)

    def apply_theme(self):
        style_name = self.combo.currentText()
        QApplication.setStyle(style_name)
        QApplication.instance().setStyleSheet("")
        self.save_config({"type": "default", "style": style_name})

    def apply_custom_theme(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Custom Theme", "", "Stylesheet Files (*.qss)")
        if file:
            with open(file, "r") as f:
                qss = f.read()
            QApplication.instance().setStyleSheet(qss)
            self.save_config({"type": "custom", "file": file})

    def reset_theme(self):
        QApplication.setStyle("Fusion")
        QApplication.instance().setStyleSheet("")
        self.save_config({"type": "default", "style": "Fusion"})

    def save_config(self, theme_data):
        os.makedirs(AUDIO_FOLDER, exist_ok=True)
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        config["theme"] = theme_data
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)


# ---------------- TOOLBAR CUSTOMIZATION WINDOW ----------------
class ToolbarCustomizationWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setWindowTitle("Customize Toolbar")
        self.resize(300, 400)

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Check buttons to show in toolbar:"))
        layout.addWidget(self.list_widget)

        # populate toolbar buttons
        for key, btn in parent.toolbar_buttons.items():
            item = QListWidgetItem(key)
            item.setCheckState(Qt.Checked if btn["enabled"] else Qt.Unchecked)
            self.list_widget.addItem(item)

        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_changes)
        layout.addWidget(save_btn)

    def save_changes(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            name = item.text()
            self.parent.toolbar_buttons[name]["enabled"] = item.checkState() == Qt.Checked
        self.parent.update_toolbar()
        self.save_config()
        self.close()

    def save_config(self):
        os.makedirs(AUDIO_FOLDER, exist_ok=True)
        config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        toolbar_config = {name: btn["enabled"] for name, btn in self.parent.toolbar_buttons.items()}
        config["toolbar"] = toolbar_config
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)


# ---------------- MAIN APP ----------------
class Soundphone(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Soundphone")
        self.setWindowIcon(QIcon("icon1.png"))
        self.resize(950, 600)

        self.player = QMediaPlayer()
        self.history_window = None
        self.volume_window = None
        self.theme_window = None
        self.toolbar_window = None
        self.current_index = None
        self.shuffle_enabled = False

        # toolbar buttons definitions
        self.toolbar_buttons = {
            "Open": {"action": None, "enabled": True},
            "Play": {"action": None, "enabled": True},
            "Pause": {"action": None, "enabled": True},
            "Next": {"action": None, "enabled": True},
        }

        self.init_ui()
        self.init_menu()
        self.init_toolbar()
        self.load_config()
        self.load_theme_on_startup()

    # ---------------- UI ----------------
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.model = QFileSystemModel()
        self.model.setRootPath(AUDIO_FOLDER)
        self.model.setNameFilters(["*.mp3", "*.wav", "*.ogg"])
        self.model.setNameFilterDisables(False)

        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setRootIndex(self.model.index(AUDIO_FOLDER))
        self.view.doubleClicked.connect(self.play_from_library)
        self.view.setHeaderHidden(True)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.library_menu)

        layout.addWidget(self.view)

        self.info = QLabel("No audio loaded")
        self.info.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info)

    # ---------------- MENU ----------------
    def init_menu(self):
        bar = self.menuBar()

        file_menu = bar.addMenu("File")
        open_file = QAction("Open File", self)
        open_file.triggered.connect(self.open_file)
        file_menu.addAction(open_file)

        open_url = QAction("Open URL", self)
        open_url.triggered.connect(self.open_url)
        file_menu.addAction(open_url)

        file_menu.addSeparator()
        exit_app = QAction("Exit", self)
        exit_app.triggered.connect(self.close)
        file_menu.addAction(exit_app)

        history_menu = bar.addMenu("History")
        url_history = QAction("URL Audio History", self)
        url_history.triggered.connect(self.show_url_history)
        history_menu.addAction(url_history)

        volume_menu = bar.addMenu("Volume")
        set_volume = QAction("Set Volume", self)
        set_volume.triggered.connect(self.open_volume_window)
        volume_menu.addAction(set_volume)

        settings_menu = bar.addMenu("Settings")
        audio_menu = settings_menu.addMenu("Audio")
        self.shuffle_action = QAction("Enable Shuffle", self, checkable=True)
        self.shuffle_action.triggered.connect(self.toggle_shuffle)
        audio_menu.addAction(self.shuffle_action)

        theme_menu = settings_menu.addMenu("Theme")
        select_theme_action = QAction("Select Theme", self)
        select_theme_action.triggered.connect(self.open_theme_window)
        theme_menu.addAction(select_theme_action)

        toolbar_menu = settings_menu.addMenu("Toolbar")
        customize_toolbar_action = QAction("Customize Toolbar", self)
        customize_toolbar_action.triggered.connect(self.open_toolbar_window)
        toolbar_menu.addAction(customize_toolbar_action)

        help_menu = bar.addMenu("Help")
        about = QAction("About", self)
        about.triggered.connect(self.about)
        help_menu.addAction(about)

        repo = QAction("Repo", self)
        repo.triggered.connect(lambda: webbrowser.open("https://github.com/Jcsab111/Soundphone"))
        help_menu.addAction(repo)

    # ---------------- TOOLBAR ----------------
    def init_toolbar(self):
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        style = self.style()
        icons = {
            "Open": style.standardIcon(style.SP_DialogOpenButton),
            "Play": style.standardIcon(style.SP_MediaPlay),
            "Pause": style.standardIcon(style.SP_MediaPause),
            "Next": style.standardIcon(style.SP_MediaSkipForward),
        }

        # create actions
        self.toolbar_buttons["Open"]["action"] = QAction(icons["Open"], "Open", self)
        self.toolbar_buttons["Open"]["action"].triggered.connect(self.open_file)

        self.toolbar_buttons["Play"]["action"] = QAction(icons["Play"], "Play", self)
        self.toolbar_buttons["Play"]["action"].triggered.connect(self.play_selected_or_current)

        self.toolbar_buttons["Pause"]["action"] = QAction(icons["Pause"], "Pause", self)
        self.toolbar_buttons["Pause"]["action"].triggered.connect(self.player.pause)

        self.toolbar_buttons["Next"]["action"] = QAction(icons["Next"], "Next", self)
        self.toolbar_buttons["Next"]["action"].triggered.connect(self.play_next)

        self.update_toolbar()

    def update_toolbar(self):
        self.toolbar.clear()
        for key, btn in self.toolbar_buttons.items():
            if btn["enabled"]:
                self.toolbar.addAction(btn["action"])

        # volume label
        self.volume_label = QLabel(f"{self.player.volume()}%")
        self.volume_label.setAlignment(Qt.AlignCenter)
        self.toolbar.addWidget(self.volume_label)

    # ---------------- TOOLBAR WINDOW ----------------
    def open_toolbar_window(self):
        if not self.toolbar_window:
            self.toolbar_window = ToolbarCustomizationWindow(self)
        self.toolbar_window.show()
        self.toolbar_window.raise_()
        self.toolbar_window.activateWindow()

    # ---------------- SHUFFLE ----------------
    def toggle_shuffle(self):
        self.shuffle_enabled = self.shuffle_action.isChecked()

    # ---------------- VOLUME ----------------
    def open_volume_window(self):
        if not self.volume_window:
            self.volume_window = VolumeWindow(self)
        self.volume_window.show()
        self.volume_window.raise_()
        self.volume_window.activateWindow()

    # ---------------- THEME ----------------
    def open_theme_window(self):
        if not self.theme_window:
            self.theme_window = ThemeWindow(self)
        self.theme_window.show()
        self.theme_window.raise_()
        self.theme_window.activateWindow()

    def load_theme_on_startup(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                theme = config.get("theme")
                if theme:
                    if theme["type"] == "default":
                        QApplication.setStyle(theme.get("style", "Fusion"))
                        QApplication.instance().setStyleSheet("")
                    elif theme["type"] == "custom":
                        file = theme.get("file")
                        if file and os.path.exists(file):
                            with open(file, "r") as f2:
                                QApplication.instance().setStyleSheet(f2.read())

    # ---------------- LOAD TOOLBAR CONFIG ----------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                toolbar_config = config.get("toolbar", {})
                for key, enabled in toolbar_config.items():
                    if key in self.toolbar_buttons:
                        self.toolbar_buttons[key]["enabled"] = enabled

    # ---------------- CORE LOGIC ----------------
    def ensure_audio_folder(self):
        if not os.path.exists(AUDIO_FOLDER):
            os.makedirs(AUDIO_FOLDER)

    def open_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Open Audio", "", "Audio Files (*.mp3 *.wav *.ogg)"
        )
        if not file:
            return
        self.ensure_audio_folder()
        dest = os.path.join(AUDIO_FOLDER, os.path.basename(file))
        if not os.path.exists(dest):
            shutil.copy(file, dest)
        self.refresh_library()
        self.play_file(dest)

    def play_file(self, path):
        self.player.stop()
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self.player.play()
        self.info.setText(f"Playing:\n{os.path.basename(path)}")
        self.current_index = self.model.index(path)

    def play_from_library(self, index):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            self.play_file(path)

    def play_selected_or_current(self):
        index = self.view.currentIndex()
        if index.isValid():
            path = self.model.filePath(index)
            if os.path.isfile(path):
                if index != self.current_index:
                    self.play_file(path)
                    return
        self.player.play()

    def play_next(self):
        if not self.current_index:
            return

        if self.shuffle_enabled:
            all_files = []
            for row in range(self.model.rowCount(self.model.index(AUDIO_FOLDER))):
                index = self.model.index(row, 0, self.model.index(AUDIO_FOLDER))
                path = self.model.filePath(index)
                if os.path.isfile(path):
                    all_files.append(index)
            if all_files:
                next_index = random.choice(all_files)
                self.view.setCurrentIndex(next_index)
                self.play_from_library(next_index)
                return

        next_index = self.view.indexBelow(self.current_index)
        if next_index.isValid():
            self.view.setCurrentIndex(next_index)
            self.play_from_library(next_index)

    def refresh_library(self):
        self.model.setRootPath(AUDIO_FOLDER)
        self.view.setRootIndex(self.model.index(AUDIO_FOLDER))

    # ---------------- REMOVE FROM LIBRARY ----------------
    def library_menu(self, position):
        index = self.view.indexAt(position)
        if not index.isValid():
            return
        path = self.model.filePath(index)
        if not os.path.isfile(path):
            return
        menu = QMenu()
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self.remove_file(path))
        menu.addAction(remove_action)
        menu.exec_(self.view.viewport().mapToGlobal(position))

    def remove_file(self, path):
        reply = QMessageBox.question(
            self, "Remove Audio", "Remove this audio from the library?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.current_index and self.model.filePath(self.current_index) == path:
                self.player.stop()
            os.remove(path)
            self.refresh_library()
            self.info.setText("Audio removed")

    # ---------------- URL AUDIO ----------------
    def open_url(self):
        url, ok = QInputDialog.getText(self, "Open URL", "Audio URL:")
        if not ok or not url:
            return
        self.player.stop()
        self.player.setMedia(QMediaContent(QUrl(url)))
        self.player.play()
        self.info.setText(f"Streaming:\n{url}")
        self.save_url_history(url)

    def save_url_history(self, url):
        self.ensure_audio_folder()
        history = []
        if os.path.exists(URL_HISTORY_FILE):
            with open(URL_HISTORY_FILE, "r") as f:
                history = json.load(f)
        if url not in history:
            history.append(url)
        with open(URL_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)

    def show_url_history(self):
        if not os.path.exists(URL_HISTORY_FILE):
            QMessageBox.information(self, "History", "No URL audio history.")
            return
        with open(URL_HISTORY_FILE, "r") as f:
            urls = json.load(f)
        if not urls:
            QMessageBox.information(self, "History", "No URL audio history.")
            return
        self.history_window = URLHistoryWindow(self, urls)
        self.history_window.show()

    # ---------------- ABOUT ----------------
    def about(self):
        QMessageBox.about(
            self, "About Soundphone",
            "Soundphone\n\nPyQt5 Music & Audio Player\n\nMade by:\nZohan Haque"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Soundphone()
    window.show()
    sys.exit(app.exec_())
