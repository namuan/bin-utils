#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "PyQt6",
#   "pyobjc",
# ]
# ///

import logging
import sys

from PyQt6.QtCore import Qt, QRect, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen
from PyQt6.QtWidgets import QApplication, QWidget

# Set up logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TunnelVision')

# Import macOS-specific modules
try:
    # Import CoreGraphics for events
    from Quartz.CoreGraphics import (
        CGEventCreateScrollWheelEvent,
        CGEventPost,
        kCGHIDEventTap,
        kCGScrollEventUnitLine
    )

    # Import AppKit for application info
    from AppKit import (
        NSWorkspace
    )

    MACOS_MODULES_AVAILABLE = True
except ImportError as e:
    MACOS_MODULES_AVAILABLE = False
    print(f"Failed to import macOS modules: {e}. Try: pip install pyobjc")


class FocusAreaWidget(QWidget):
    """A separate widget just for the transparent focus area"""
    clicked = pyqtSignal()

    def __init__(self, rect, parent=None):
        super().__init__(parent)
        self.focus_rect = rect
        self.setGeometry(rect)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: transparent;")

    def mousePressEvent(self, event):
        self.clicked.emit()
        event.accept()  # Prevent event propagation


class FocusOverlayWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Define the focus rectangle with rounded corners
        self.focus_rect = QRect(200, 150, 800, 500)
        self.corner_radius = 20  # radius for rounded corners

        # Variables to manage dragging of the corners
        self.dragging = False
        self.drag_corner = None
        self.drag_start_pos = None
        self.original_rect = QRect()

        # The size in pixels around a corner that will be sensitive to dragging
        self.hit_threshold = 14
        self.handle_size = 10  # Size of the visible corner handles

        # Auto-scroll variables
        self.auto_scrolling = False
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.perform_scroll)
        self.scroll_speed = -1  # default lines per scroll
        self.scroll_interval = 500  # milliseconds

        # Status display
        self.last_action = "Ready"

        # Create a separate widget for the focus area
        self.focus_area = FocusAreaWidget(self.focus_rect, self)

        # Set cursor for corners
        self.setMouseTracking(True)  # Enable mouse tracking for cursor changes

    def update_focus_area_geometry(self):
        """Update the focus area widget to match the focus rectangle"""
        self.focus_area.setGeometry(self.focus_rect)
        self.focus_area.focus_rect = self.focus_rect

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill the entire window with a semi-transparent dark overlay
        overlay_color = QColor(0, 0, 0, 200)
        painter.fillRect(self.rect(), overlay_color)

        # Set the composition mode to clear so that the focus rectangle becomes transparent
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)

        # Create a path with a rounded rectangle for the focus area
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.focus_rect), self.corner_radius, self.corner_radius)
        painter.fillPath(path, QColor(0, 0, 0, 0))

        # Draw an outline around the focus rectangle
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Use different colors based on state
        if self.auto_scrolling:
            border_pen = QPen(QColor(155, 206, 223), 3)
        else:
            border_pen = QPen(QColor(170, 170, 190), 2)  # Muted blue-gray for normal

        painter.setPen(border_pen)
        painter.drawRoundedRect(self.focus_rect, self.corner_radius, self.corner_radius)

        # Draw corner handles
        handle_color = QColor(255, 255, 255)
        if self.auto_scrolling:
            handle_color = QColor(155, 206, 223)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(handle_color)

        # Draw the corner handles
        corners = {
            'top-left': self.focus_rect.topLeft(),
            'top-right': self.focus_rect.topRight(),
            'bottom-left': self.focus_rect.bottomLeft(),
            'bottom-right': self.focus_rect.bottomRight(),
        }

        for corner, point in corners.items():
            # Draw circular handle centered on corner
            handle_rect = QRectF(
                point.x() - self.handle_size / 2,
                point.y() - self.handle_size / 2,
                self.handle_size,
                self.handle_size
            )
            painter.drawEllipse(handle_rect)

        # Display keyboard shortcut info
        key_help = [
            "ESC: Exit",
            "SPACE: Toggle scroll direction",
            "+/-: Adjust scroll speed",
            "S: Toggle scrolling",
        ]

        debug_y = self.height() - 140
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        for help_text in key_help:
            painter.drawText(10, debug_y, help_text)
            debug_y += 20

    def mouseMoveEvent(self, event):
        """Handle mouse movement for corner dragging and cursor changing"""
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()

        # If currently dragging, handle corner movement
        if self.dragging:
            dx = pos.x() - self.drag_start_pos.x()
            dy = pos.y() - self.drag_start_pos.y()
            rect = QRect(self.original_rect)

            # Minimum allowed dimensions for the focus rectangle
            min_width = 100
            min_height = 100

            # Update the rectangle based on which corner is being dragged
            if self.drag_corner == 'top-left':
                new_x = rect.x() + dx
                new_y = rect.y() + dy
                new_width = rect.width() - dx
                new_height = rect.height() - dy
                if new_width < min_width:
                    new_x = rect.x() + (rect.width() - min_width)
                    new_width = min_width
                if new_height < min_height:
                    new_y = rect.y() + (rect.height() - min_height)
                    new_height = min_height
                self.focus_rect = QRect(new_x, new_y, new_width, new_height)

            elif self.drag_corner == 'top-right':
                new_y = rect.y() + dy
                new_width = rect.width() + dx
                new_height = rect.height() - dy
                if new_width < min_width:
                    new_width = min_width
                if new_height < min_height:
                    new_y = rect.y() + (rect.height() - min_height)
                    new_height = min_height
                self.focus_rect = QRect(rect.x(), new_y, new_width, new_height)

            elif self.drag_corner == 'bottom-left':
                new_x = rect.x() + dx
                new_width = rect.width() - dx
                new_height = rect.height() + dy
                if new_width < min_width:
                    new_x = rect.x() + (rect.width() - min_width)
                    new_width = min_width
                if new_height < min_height:
                    new_height = min_height
                self.focus_rect = QRect(new_x, rect.y(), new_width, new_height)

            elif self.drag_corner == 'bottom-right':
                new_width = rect.width() + dx
                new_height = rect.height() + dy
                if new_width < min_width:
                    new_width = min_width
                if new_height < min_height:
                    new_height = min_height
                self.focus_rect = QRect(rect.x(), rect.y(), new_width, new_height)

            self.update()
        else:
            # Change cursor based on mouse position
            corners = {
                'top-left': self.focus_rect.topLeft(),
                'top-right': self.focus_rect.topRight(),
                'bottom-left': self.focus_rect.bottomLeft(),
                'bottom-right': self.focus_rect.bottomRight(),
            }

            corner_detected = False
            for corner, point in corners.items():
                if abs(point.x() - pos.x()) <= self.hit_threshold and abs(point.y() - pos.y()) <= self.hit_threshold:
                    # Set appropriate diagonal resize cursor based on corner
                    if corner == 'top-left' or corner == 'bottom-right':
                        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                    else:
                        self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                    corner_detected = True
                    break

            if not corner_detected:
                # Reset to default cursor when not over a corner
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        """Handle mouse press events for corner dragging only"""
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()

        # Check if near corner for dragging
        corners = {
            'top-left': self.focus_rect.topLeft(),
            'top-right': self.focus_rect.topRight(),
            'bottom-left': self.focus_rect.bottomLeft(),
            'bottom-right': self.focus_rect.bottomRight(),
        }

        for corner, point in corners.items():
            if abs(point.x() - pos.x()) <= self.hit_threshold and abs(point.y() - pos.y()) <= self.hit_threshold:
                self.dragging = True
                self.drag_corner = corner
                self.drag_start_pos = pos
                self.original_rect = QRect(self.focus_rect)
                self.last_action = f"Dragging {corner}"

                # Hide the focus area widget during dragging
                self.focus_area.hide()
                return

    def toggle_auto_scroll(self):
        """Toggle auto-scrolling state"""
        self.auto_scrolling = not self.auto_scrolling

        if self.auto_scrolling:
            self.last_action = "Started auto-scrolling"

            # Make the focus area widget transparent to mouse events
            # This allows clicks to pass through to underlying applications
            self.focus_area.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

            # Start the timer for scroll events
            self.scroll_timer.start(self.scroll_interval)

            # Execute an immediate scroll
            QTimer.singleShot(100, self.perform_scroll)
        else:
            self.last_action = "Stopped auto-scrolling"
            self.scroll_timer.stop()

            # Make the focus area widget non-transparent to capture clicks again
            self.focus_area.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self.update()

    def perform_scroll(self):
        """Send scroll events to the window under the focus rectangle"""
        if not self.auto_scrolling:
            return

        # Check if macOS modules are available
        if not MACOS_MODULES_AVAILABLE:
            return

        try:
            # Create a scroll wheel event
            scroll_event = CGEventCreateScrollWheelEvent(
                None,  # No source
                kCGScrollEventUnitLine,  # Use line units
                1,  # Number of wheels (1 for vertical only)
                self.scroll_speed  # Number of lines
            )

            # Post the event
            CGEventPost(kCGHIDEventTap, scroll_event)

        except Exception:
            pass

    def mouseReleaseEvent(self, event):
        """Handle mouse release events for corner dragging"""
        if self.dragging:
            self.dragging = False
            self.drag_corner = None
            self.last_action = "Ready"

            # Update and show the focus area widget
            self.update_focus_area_geometry()
            self.focus_area.show()

            self.update()

    def keyPressEvent(self, event):
        """Handle key press events"""
        # Exit on Escape key
        if event.key() == Qt.Key.Key_Escape:
            self.close()

        # Toggle scroll direction with space
        elif event.key() == Qt.Key.Key_Space:
            self.scroll_speed = -self.scroll_speed
            direction = "DOWN" if self.scroll_speed < 0 else "UP"
            self.last_action = f"Changed scroll direction to {direction}"
            self.update()

        # Toggle scrolling with S key
        elif event.key() == Qt.Key.Key_S:
            self.toggle_auto_scroll()

        # Adjust scroll speed with + and - keys
        elif event.key() == Qt.Key.Key_Plus or event.key() == Qt.Key.Key_Equal:
            if self.scroll_speed > 0:
                self.scroll_speed += 1
            else:
                self.scroll_speed -= 1
            self.update()

        elif event.key() == Qt.Key.Key_Minus:
            if self.scroll_speed > 0:
                self.scroll_speed = max(1, self.scroll_speed - 1)
            else:
                self.scroll_speed = min(-1, self.scroll_speed + 1)
            self.update()


def main():
    # Check for macOS
    if sys.platform != 'darwin':
        print("This application is designed to run only on macOS.")
        sys.exit(1)

    app = QApplication(sys.argv)

    # Create main overlay
    widget = FocusOverlayWidget()
    widget.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()