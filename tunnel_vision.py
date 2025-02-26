#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "PyQt6",
# ]
# ///

import sys

from PyQt6.QtCore import QRect, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QApplication, QWidget

# Color constants
OVERLAY_COLOR = QColor(0, 0, 0, 150)  # Semi-transparent dark overlay
BORDER_COLOR = QColor(255, 255, 255)  # White border for the focus rectangle
FOCUS_RECT_FILL_COLOR = QColor(0, 0, 0, 30)  # Fully transparent fill for focus area


class FocusOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Remove window decorations and set the widget to be transparent.
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Initialize the focus rectangle in the center of the available screen.
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            available_rect = QRect(100, 100, 800, 600)
        else:
            available_rect = screen.availableGeometry()
        init_width = available_rect.width() // 3
        init_height = available_rect.height() // 3
        init_x = (available_rect.width() - init_width) // 2
        init_y = (available_rect.height() - init_height) // 2
        self.focusRect = QRect(init_x, init_y, init_width, init_height)
        self.cornerRadius = 20  # Rounded corner radius

        # Variables for resizing only.
        self._dragMode = None  # "resize"
        self._resizeCorner = None  # "top_left", "top_right", "bottom_left", or "bottom_right"
        self.setMouseTracking(True)  # Allow cursor changes even when not pressing buttons

    def paintEvent(self, event):
        """Paints the translucent overlay with a cleared (transparent) focus hole and a border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill the whole widget with the overlay color.
        painter.fillRect(self.rect(), OVERLAY_COLOR)

        # Clear the focus rectangle area so it remains fully transparent.
        # (Using CompositionMode_Clear ensures that no extra brush–color gets blended in.)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        rounded_rect_path = QPainterPath()
        rounded_rect_path.addRoundedRect(QRectF(self.focusRect), self.cornerRadius, self.cornerRadius)
        painter.fillPath(rounded_rect_path, FOCUS_RECT_FILL_COLOR)

        # Restore composition mode for normal painting.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Draw a white border around the focus rectangle.
        border_pen = QPen(BORDER_COLOR, 2)
        painter.setPen(border_pen)
        painter.drawRoundedRect(QRectF(self.focusRect), self.cornerRadius, self.cornerRadius)
        print(f"Focus Rect is {self.focusRect}")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        handle_size = 10  # Tolerance for detecting corner handles
        self._dragMode = None

        # Check if we are near any of the four corners for resizing.
        if abs(pos.x() - self.focusRect.left()) <= handle_size and abs(pos.y() - self.focusRect.top()) <= handle_size:
            self._dragMode = "resize"
            self._resizeCorner = "top_left"
        elif (
                abs(pos.x() - self.focusRect.right()) <= handle_size and abs(
            pos.y() - self.focusRect.top()) <= handle_size
        ):
            self._dragMode = "resize"
            self._resizeCorner = "top_right"
        elif (
                abs(pos.x() - self.focusRect.left()) <= handle_size
                and abs(pos.y() - self.focusRect.bottom()) <= handle_size
        ):
            self._dragMode = "resize"
            self._resizeCorner = "bottom_left"
        elif (
                abs(pos.x() - self.focusRect.right()) <= handle_size
                and abs(pos.y() - self.focusRect.bottom()) <= handle_size
        ):
            self._dragMode = "resize"
            self._resizeCorner = "bottom_right"

        self._lastMousePos = pos

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        handle_size = 10

        # Update the cursor shape when near the resize handles.
        if abs(pos.x() - self.focusRect.left()) <= handle_size and abs(pos.y() - self.focusRect.top()) <= handle_size:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (
                abs(pos.x() - self.focusRect.right()) <= handle_size and abs(
            pos.y() - self.focusRect.top()) <= handle_size
        ):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif (
                abs(pos.x() - self.focusRect.left()) <= handle_size
                and abs(pos.y() - self.focusRect.bottom()) <= handle_size
        ):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif (
                abs(pos.x() - self.focusRect.right()) <= handle_size
                and abs(pos.y() - self.focusRect.bottom()) <= handle_size
        ):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.unsetCursor()

        # Handle resizing of the rectangle.
        if self._dragMode == "resize":
            min_width = 50
            min_height = 50
            new_rect = QRect(self.focusRect)  # copy current focusRect
            if self._resizeCorner == "top_left":
                new_left = min(pos.x(), self.focusRect.right() - min_width)
                new_top = min(pos.y(), self.focusRect.bottom() - min_height)
                new_rect.setLeft(new_left)
                new_rect.setTop(new_top)
            elif self._resizeCorner == "top_right":
                new_right = max(pos.x(), self.focusRect.left() + min_width)
                new_top = min(pos.y(), self.focusRect.bottom() - min_height)
                new_rect.setRight(new_right)
                new_rect.setTop(new_top)
            elif self._resizeCorner == "bottom_left":
                new_left = min(pos.x(), self.focusRect.right() - min_width)
                new_bottom = max(pos.y(), self.focusRect.top() + min_height)
                new_rect.setLeft(new_left)
                new_rect.setBottom(new_bottom)
            elif self._resizeCorner == "bottom_right":
                new_right = max(pos.x(), self.focusRect.left() + min_width)
                new_bottom = max(pos.y(), self.focusRect.top() + min_height)
                new_rect.setRight(new_right)
                new_rect.setBottom(new_bottom)
            self.focusRect = new_rect
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragMode = None
        self._resizeCorner = None
        self.update()

    def keyPressEvent(self, event: QKeyEvent):
        # Press Escape to exit the application.
        if event.key() == Qt.Key.Key_Escape:
            QApplication.quit()


def main():
    app = QApplication(sys.argv)
    overlay = FocusOverlay()
    overlay.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
