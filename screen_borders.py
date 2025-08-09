#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "PyQt6",
# ]
# ///
"""A PyQt6 script to draw a gradient border around the edges of the current screen using cool colors, with a styled notification bar in the middle of the top border. The bar displays custom text plus an interactive countdown timer (default 25 minutes) and Pause/Resume and Reset buttons.
Usage:
./screen_borders.py -h
./screen_borders.py -v  # To log INFO messages.
./screen_borders.py -vv # To log DEBUG messages.
./screen_borders.py "Your custom notification text"  # default 25 min countdown.
./screen_borders.py "Focus time" 1800                # 30 min countdown (in seconds)
"""
import json

# =============================================================================
import logging
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPen,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
)
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QPushButton as DialogButton
from PyQt6.QtWidgets import QSpinBox, QVBoxLayout, QWidget

# =============================================================================
# THEME AND COLOR CONFIGURATION
# =============================================================================
# Default theme configuration
DEFAULT_THEME = {
    # Border gradient colors (RGB + Alpha)
    "border_color_start": (0, 120, 255, 200),  # Blue start
    "border_color_end": (0, 255, 255, 200),  # Cyan end
    "border_width": 10,
    # Notification bar colors (RGB + Alpha)
    "notification_bg_start": (0, 120, 255, 240),  # Blue start (more opaque)
    "notification_bg_end": (0, 255, 255, 240),  # Cyan end (more opaque)
    "notification_text_color": (0, 0, 0),  # Black text
    "notification_corner_radius": 10,
    # Button styling
    "button_bg_normal": "rgba(255,255,255,0)",  # Transparent background
    "button_bg_hover": "rgba(255,255,255,80)",  # Semi-transparent white on hover
    "button_text_color": "black",
    "button_corner_radius": 8,
    "button_width": 32,
    "button_height": 28,
    # Button icons
    "icon_pause": "⏸",
    "icon_play": "▶",
    "icon_reset": "⏮",
    "icon_done": "✓",
    # Fonts
    "main_font_family": "Arial",
    "main_font_size": 14,
    "icon_font_family": "Segoe UI Symbol",
    "icon_font_size": 14,
    # Layout dimensions
    "notification_padding": 20,
    "notification_offset": 5,
    "button_spacing": 6,
    "button_container_padding": 10,
}
# Predefined themes
PREDEFINED_THEMES = {
    "Default (Blue-Cyan)": DEFAULT_THEME,
    "Dark Mode": {
        **DEFAULT_THEME,
        "border_color_start": (50, 50, 50, 200),
        "border_color_end": (100, 100, 100, 200),
        "notification_bg_start": (40, 40, 40, 240),
        "notification_bg_end": (60, 60, 60, 240),
        "notification_text_color": (255, 255, 255),
        "button_text_color": "white",
        "button_bg_hover": "rgba(255,255,255,30)",
    },
    "Warm (Orange-Red)": {
        **DEFAULT_THEME,
        "border_color_start": (255, 140, 0, 200),
        "border_color_end": (255, 69, 0, 200),
        "notification_bg_start": (255, 140, 0, 240),
        "notification_bg_end": (255, 165, 0, 240),
    },
    "Nature (Green)": {
        **DEFAULT_THEME,
        "border_color_start": (0, 255, 0, 200),
        "border_color_end": (34, 139, 34, 200),
        "notification_bg_start": (144, 238, 144, 240),
        "notification_bg_end": (152, 251, 152, 240),
    },
    "Purple Dreams": {
        **DEFAULT_THEME,
        "border_color_start": (138, 43, 226, 200),
        "border_color_end": (75, 0, 130, 200),
        "notification_bg_start": (147, 112, 219, 240),
        "notification_bg_end": (138, 43, 226, 240),
        "notification_text_color": (255, 255, 255),
        "button_text_color": "white",
        "button_bg_hover": "rgba(255,255,255,40)",
    },
    "Ocean Sunset": {
        **DEFAULT_THEME,
        "border_color_start": (255, 94, 77, 200),
        "border_color_end": (255, 154, 0, 200),
        "notification_bg_start": (255, 94, 77, 240),
        "notification_bg_end": (255, 206, 84, 240),
    },
}
# Current active theme
current_theme = DEFAULT_THEME.copy()


# Determine OS-specific config directory
def get_config_dir():
    if sys.platform == "win32":
        config_dir = Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support"
    else:  # Linux and other Unix-like
        config_dir = Path.home() / ".config"
    config_dir = config_dir / "screen_borders"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


CONFIG_FILE = get_config_dir() / "config.json"


def load_config():
    """Load configuration from the OS-standard config location."""
    global current_theme
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                saved_config = json.load(f)
            # Update only the keys that exist in the saved config
            current_theme.update(saved_config)
            logging.info(f"Configuration loaded from {CONFIG_FILE}")
        except Exception as e:
            logging.warning(f"Failed to load config from {CONFIG_FILE}: {e}")


def save_config():
    """Save current configuration to the OS-standard config location."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current_theme, f, indent=2)
        logging.info(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        logging.error(f"Failed to save config to {CONFIG_FILE}: {e}")


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(
        "notification_text",
        nargs="?",
        default="Music give allow letter who none. Those again boy seven their fear argue. Quite field well key vote. Window result get allow source candidate.",
        help="Custom text to display in the notification bar",
    )
    parser.add_argument(
        "countdown_seconds",
        nargs="?",
        type=int,
        default=25 * 60,
        help="Countdown duration in seconds (default: 1500 = 25 minutes)",
    )
    return parser.parse_args()


class ColorButton(QPushButton):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(60, 30)
        self.update_color()
        self.clicked.connect(self.choose_color)

    def update_color(self):
        r, g, b = self.color[:3]
        self.setStyleSheet(f"QPushButton {{ background-color: rgb({r},{g},{b}); border: 2px solid #ccc; }}")

    def choose_color(self):
        color = QColorDialog.getColor(QColor(*self.color[:3]))
        if color.isValid():
            self.color = (color.red(), color.green(), color.blue(), self.color[3] if len(self.color) > 3 else 255)
            self.update_color()


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Screen Border Configuration")
        self.setModal(True)
        self.setFixedSize(500, 600)
        # Store original theme for cancel functionality
        self.original_theme = current_theme.copy()
        # Store original timer for cancel functionality
        self.original_timer_seconds = getattr(parent, "countdown_seconds", 25 * 60)
        self.init_ui()

    def _separator(self):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.HLine)
        frame.setFrameShadow(QFrame.Shadow.Sunken)
        return frame

    def init_ui(self):
        layout = QVBoxLayout()
        # Predefined themes section
        theme_group = QGroupBox("Predefined Themes")
        theme_layout = QVBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(PREDEFINED_THEMES.keys())
        self.theme_combo.currentTextChanged.connect(self.load_predefined_theme)
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Custom settings section
        custom_group = QGroupBox("Custom Settings")
        custom_layout = QFormLayout()

        # Border colors
        border_label = QLabel("Border Colors:")
        custom_layout.addRow(border_label)
        border_layout = QHBoxLayout()
        self.border_start_btn = ColorButton(current_theme["border_color_start"])
        self.border_end_btn = ColorButton(current_theme["border_color_end"])
        border_layout.addWidget(QLabel("Start:"))
        border_layout.addWidget(self.border_start_btn)
        border_layout.addWidget(QLabel("End:"))
        border_layout.addWidget(self.border_end_btn)

        # Border width
        self.border_width_spin = QSpinBox()
        self.border_width_spin.setRange(1, 50)
        self.border_width_spin.setValue(current_theme["border_width"])
        border_layout.addWidget(QLabel("Border Width:"))
        border_layout.addWidget(self.border_width_spin)
        border_layout.addStretch()
        custom_layout.addRow(border_layout)
        custom_layout.addRow(self._separator())

        # Notification background colors
        notif_label = QLabel("Notification Background:")
        custom_layout.addRow(notif_label)
        notif_layout = QHBoxLayout()
        self.notif_start_btn = ColorButton(current_theme["notification_bg_start"])
        self.notif_end_btn = ColorButton(current_theme["notification_bg_end"])
        self.text_color_btn = ColorButton(current_theme["notification_text_color"])
        notif_layout.addWidget(QLabel("Start:"))
        notif_layout.addWidget(self.notif_start_btn)
        notif_layout.addWidget(QLabel("End:"))
        notif_layout.addWidget(self.notif_end_btn)
        notif_layout.addWidget(QLabel("Text Color:"))
        notif_layout.addWidget(self.text_color_btn)
        notif_layout.addStretch()
        custom_layout.addRow(notif_layout)
        custom_layout.addRow(self._separator())

        # Button Icons - Changed to use QFormLayout rows instead of QGridLayout
        self.icon_pause_edit = QLineEdit(current_theme["icon_pause"])
        self.icon_play_edit = QLineEdit(current_theme["icon_play"])
        self.icon_reset_edit = QLineEdit(current_theme["icon_reset"])
        self.icon_done_edit = QLineEdit(current_theme["icon_done"])

        # Create horizontal layouts for each icon pair to maintain alignment
        pause_play_layout = QHBoxLayout()
        pause_play_layout.addWidget(QLabel("Pause:"))
        pause_play_layout.addWidget(self.icon_pause_edit)
        pause_play_layout.addWidget(QLabel("Play:"))
        pause_play_layout.addWidget(self.icon_play_edit)
        pause_play_layout.addStretch()

        reset_done_layout = QHBoxLayout()
        reset_done_layout.addWidget(QLabel("Reset:"))
        reset_done_layout.addWidget(self.icon_reset_edit)
        reset_done_layout.addWidget(QLabel("Done:"))
        reset_done_layout.addWidget(self.icon_done_edit)
        reset_done_layout.addStretch()

        button_icons_label = QLabel("Button Icons:")
        custom_layout.addRow(button_icons_label)
        custom_layout.addRow("", pause_play_layout)
        custom_layout.addRow("", reset_done_layout)
        custom_layout.addRow(self._separator())

        # Font settings - Changed to maintain left alignment
        self.font_family_edit = QLineEdit(current_theme["main_font_family"])
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(current_theme["main_font_size"])
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Family:"))
        font_layout.addWidget(self.font_family_edit)
        font_layout.addWidget(QLabel("Size:"))
        font_layout.addWidget(self.font_size_spin)
        font_layout.addStretch()
        main_font_label = QLabel("Main Font:")
        custom_layout.addRow(main_font_label)
        custom_layout.addRow("", font_layout)
        custom_layout.addRow(self._separator())

        # Timer configuration (minutes)
        self.timer_minutes_spin = QSpinBox()
        self.timer_minutes_spin.setRange(1, 24 * 60)  # 1 minute to 24 hours
        parent_widget = self.parent()
        current_timer = getattr(parent_widget, "countdown_seconds", 25 * 60)
        self.timer_minutes_spin.setValue(max(1, current_timer // 60))
        custom_layout.addRow("Timer (minutes):", self.timer_minutes_spin)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Buttons
        button_layout = QHBoxLayout()
        apply_btn = DialogButton("Apply")
        apply_btn.clicked.connect(self.apply_changes)
        ok_btn = DialogButton("OK")
        ok_btn.clicked.connect(self.accept_changes)
        cancel_btn = DialogButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(apply_btn)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_predefined_theme(self, theme_name):
        if theme_name in PREDEFINED_THEMES:
            theme = PREDEFINED_THEMES[theme_name]
            self.update_ui_from_theme(theme)

    def update_ui_from_theme(self, theme):
        self.border_start_btn.color = theme["border_color_start"]
        self.border_start_btn.update_color()
        self.border_end_btn.color = theme["border_color_end"]
        self.border_end_btn.update_color()
        self.border_width_spin.setValue(theme["border_width"])
        self.notif_start_btn.color = theme["notification_bg_start"]
        self.notif_start_btn.update_color()
        self.notif_end_btn.color = theme["notification_bg_end"]
        self.notif_end_btn.update_color()
        self.text_color_btn.color = theme["notification_text_color"]
        self.text_color_btn.update_color()
        self.icon_pause_edit.setText(theme["icon_pause"])
        self.icon_play_edit.setText(theme["icon_play"])
        self.icon_reset_edit.setText(theme["icon_reset"])
        self.icon_done_edit.setText(theme["icon_done"])
        self.font_family_edit.setText(theme["main_font_family"])
        self.font_size_spin.setValue(theme["main_font_size"])

    def get_current_config(self):
        return {
            "border_color_start": self.border_start_btn.color,
            "border_color_end": self.border_end_btn.color,
            "border_width": self.border_width_spin.value(),
            "notification_bg_start": self.notif_start_btn.color,
            "notification_bg_end": self.notif_end_btn.color,
            "notification_text_color": self.text_color_btn.color,
            "notification_corner_radius": current_theme["notification_corner_radius"],
            "button_bg_normal": current_theme["button_bg_normal"],
            "button_bg_hover": current_theme["button_bg_hover"],
            "button_text_color": current_theme["button_text_color"],
            "button_corner_radius": current_theme["button_corner_radius"],
            "button_width": current_theme["button_width"],
            "button_height": current_theme["button_height"],
            "icon_pause": self.icon_pause_edit.text(),
            "icon_play": self.icon_play_edit.text(),
            "icon_reset": self.icon_reset_edit.text(),
            "icon_done": self.icon_done_edit.text(),
            "main_font_family": self.font_family_edit.text(),
            "main_font_size": self.font_size_spin.value(),
            "icon_font_family": current_theme["icon_font_family"],
            "icon_font_size": current_theme["icon_font_size"],
            "notification_padding": current_theme["notification_padding"],
            "notification_offset": current_theme["notification_offset"],
            "button_spacing": current_theme["button_spacing"],
            "button_container_padding": current_theme["button_container_padding"],
        }

    def apply_changes(self):
        global current_theme
        current_theme.update(self.get_current_config())
        if self.parent():
            # Apply theme
            self.parent().apply_theme()
            # Apply timer value (entered in minutes) and restart timer similar to reset
            new_timer = self.timer_minutes_spin.value() * 60
            self.parent().countdown_seconds = new_timer
            self.parent().remaining = new_timer
            self.parent().running = True
            if hasattr(self.parent(), "timer"):
                self.parent().timer.start(1000)
            # Ensure buttons reflect running state after reset
            if self.parent().pause_resume_btn:
                self.parent().pause_resume_btn.setText(current_theme["icon_pause"])
            self.parent().update()
        # Save config after apply
        save_config()

    def accept_changes(self):
        self.apply_changes()
        self.accept()

    def reject(self):
        global current_theme
        current_theme.clear()
        current_theme.update(self.original_theme)
        if self.parent():
            # Re-apply theme
            self.parent().apply_theme()
            # Restore original timer value
            self.parent().countdown_seconds = self.original_timer_seconds
            self.parent().remaining = self.original_timer_seconds
            if self.parent().pause_resume_btn:
                self.parent().pause_resume_btn.setText(current_theme["icon_pause"])
        super().reject()


class BorderWidget(QWidget):
    def __init__(self, notification_text, countdown_seconds):
        super().__init__()
        self.notification_text = notification_text
        self.countdown_seconds = countdown_seconds
        self.remaining = countdown_seconds
        self.running = True  # auto-start
        self.control_widget = None
        self.pause_resume_btn = None
        self.reset_btn = None
        logging.debug("Initializing BorderWidget")
        self.init_ui()
        self.init_timer()
        self.setup_shortcuts()

    def setup_shortcuts(self):
        # Create Cmd+, shortcut for preferences
        self.config_shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
        self.config_shortcut.activated.connect(self.open_config)
        # Also support Cmd+, on macOS
        self.config_shortcut_mac = QShortcut(QKeySequence("Meta+,"), self)
        self.config_shortcut_mac.activated.connect(self.open_config)

    def open_config(self):
        dialog = ConfigDialog(self)
        dialog.exec()

    def init_ui(self):
        # Get the screen geometry
        screen = QApplication.primaryScreen().geometry()
        logging.info(f"Screen geometry: {screen}")
        self.setGeometry(screen)
        # Make the window frameless and transparent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Set window to stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        logging.debug("Window flags set: Frameless and transparent")
        self.create_buttons()

    def create_buttons(self):
        # Remove existing control widget if it exists
        if self.control_widget is not None:
            self.control_widget.deleteLater()
        # Create new control widget for buttons
        self.control_widget = QWidget(self)
        self.control_widget.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.control_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(current_theme["button_spacing"])

        # Pause/Resume button
        self.pause_resume_btn = QPushButton(current_theme["icon_pause"], self.control_widget)
        self.pause_resume_btn.setFixedSize(current_theme["button_width"], current_theme["button_height"])
        self.pause_resume_btn.setFlat(True)
        icon_font = QFont(current_theme["icon_font_family"], current_theme["icon_font_size"])
        self.pause_resume_btn.setFont(icon_font)
        self.pause_resume_btn.setStyleSheet(
            f"QPushButton {{ background-color: {current_theme['button_bg_normal']}; color: {current_theme['button_text_color']}; border: none; padding: 0px; }}"
            f"QPushButton:hover {{ background-color: {current_theme['button_bg_hover']}; border-radius: {current_theme['button_corner_radius']}px; }}"
        )
        self.pause_resume_btn.clicked.connect(self.toggle_pause_resume)

        # Reset button
        self.reset_btn = QPushButton(current_theme["icon_reset"], self.control_widget)
        self.reset_btn.setFixedSize(current_theme["button_width"], current_theme["button_height"])
        self.reset_btn.setFlat(True)
        self.reset_btn.setFont(icon_font)
        self.reset_btn.setStyleSheet(
            f"QPushButton {{ background-color: {current_theme['button_bg_normal']}; color: {current_theme['button_text_color']}; border: none; padding: 0px; }}"
            f"QPushButton:hover {{ background-color: {current_theme['button_bg_hover']}; border-radius: {current_theme['button_corner_radius']}px; }}"
        )
        self.reset_btn.clicked.connect(self.reset_timer)

        button_layout.addWidget(self.pause_resume_btn)
        button_layout.addWidget(self.reset_btn)
        self.control_widget.setLayout(button_layout)

    def apply_theme(self):
        """Apply the current theme to the widget"""
        self.create_buttons()
        self.update()

    def init_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def toggle_pause_resume(self):
        if self.running:
            self.timer.stop()
            self.pause_resume_btn.setText(current_theme["icon_play"])
            self.running = False
        else:
            self.timer.start(1000)
            self.pause_resume_btn.setText(current_theme["icon_pause"])
            self.running = True
        self.update()

    def reset_timer(self):
        self.remaining = self.countdown_seconds
        self.running = True
        self.timer.start(1000)
        self.pause_resume_btn.setText(current_theme["icon_pause"])
        self.update()

    def tick(self):
        if self.remaining > 0:
            self.remaining -= 1
        else:
            self.timer.stop()
            self.running = False
            self.pause_resume_btn.setText(current_theme["icon_done"])
        self.update()

    def paintEvent(self, event):
        logging.debug("Painting border and notification bar")
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width()
        height = self.height()
        logging.debug(f"Widget dimensions: width={width}, height={height}")

        # Gradient for border
        gradient = QLinearGradient(QPointF(0, 0), QPointF(width, height))
        gradient.setColorAt(0.0, QColor(*current_theme["border_color_start"]))
        gradient.setColorAt(1.0, QColor(*current_theme["border_color_end"]))
        pen = QPen(gradient, current_theme["border_width"])
        painter.setPen(pen)

        # Font settings
        font = QFont(current_theme["main_font_family"], current_theme["main_font_size"])
        painter.setFont(font)
        font_metrics = QFontMetrics(font)

        # Build text string
        mm, ss = divmod(self.remaining, 60)
        timer_str = f"{mm:02}:{ss:02}"
        display_text = f"{self.notification_text}   {timer_str}"
        text_width = font_metrics.horizontalAdvance(display_text)
        text_height = font_metrics.height()

        # Notification bar geometry
        btn_total_width = self.pause_resume_btn.width() + self.reset_btn.width() + current_theme["button_spacing"]
        text_area_width = (
            text_width
            + current_theme["notification_padding"]
            + btn_total_width
            + current_theme["button_container_padding"]
        )
        text_area_height = text_height + current_theme["notification_padding"]
        text_area_x = (width - text_area_width) // 2
        text_area_y = current_theme["notification_offset"]

        # Draw notification bar background
        notification_gradient = QLinearGradient(
            QPointF(text_area_x, text_area_y), QPointF(text_area_x + text_area_width, text_area_y)
        )
        notification_gradient.setColorAt(0.0, QColor(*current_theme["notification_bg_start"]))
        notification_gradient.setColorAt(1.0, QColor(*current_theme["notification_bg_end"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(notification_gradient))
        text_area = QRectF(
            text_area_x, text_area_y + current_theme["notification_offset"], text_area_width, text_area_height
        )
        painter.drawRoundedRect(
            text_area, current_theme["notification_corner_radius"], current_theme["notification_corner_radius"]
        )

        # Draw text
        painter.setPen(QColor(*current_theme["notification_text_color"]))
        text_rect = text_area.adjusted(
            current_theme["notification_padding"] / 2,
            current_theme["notification_padding"] / 2,
            -(current_theme["notification_padding"] / 2 + btn_total_width + current_theme["button_container_padding"]),
            -current_theme["notification_padding"] / 2,
        )
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            display_text,
        )

        # Draw borders
        painter.setPen(pen)
        painter.drawLine(0, height - 1, width - 1, height - 1)  # Bottom
        painter.drawLine(0, 0, 0, height - 1)  # Left
        painter.drawLine(width - 1, 0, width - 1, height - 1)  # Right
        painter.drawLine(
            0, current_theme["notification_offset"], width - 1, current_theme["notification_offset"]
        )  # Top

        # Position controls
        if self.control_widget:
            control_x = int(
                text_area_x + text_area_width - btn_total_width - (current_theme["button_container_padding"] // 2)
            )
            control_y = int(
                text_area_y
                + current_theme["notification_offset"]
                + (text_area_height - self.control_widget.height()) // 2
            )
            self.control_widget.move(control_x, control_y)
            self.control_widget.show()

        logging.info("Gradient border and notification bar drawn successfully")


def main(args):
    logging.debug(f"Starting main with verbosity: {args.verbose}")
    app = QApplication([])
    logging.info("QApplication initialized")
    border_widget = BorderWidget(args.notification_text, args.countdown_seconds)
    border_widget.showMaximized()
    logging.info("BorderWidget shown")
    app.exec()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    load_config()  # Load config at startup
    main(args)
