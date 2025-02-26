#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "PyQt6",
# ]
# ///

import sys

from PyQt6.QtCore import Qt, QRect, QRectF, QEvent
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen
from PyQt6.QtWidgets import QApplication, QWidget


class FocusOverlayWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Set window flags: frameless and always on top, and enable attribute for translucent background.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint  # | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Define the focus rectangle (the area that is "cut out") with rounded corners.
        self.focus_rect = QRect(200, 150, 800, 500)
        self.corner_radius = 20  # radius for rounded corners

        # Variables to manage dragging of the corners.
        self.dragging = False
        self.drag_corner = None  # possible values: 'top-left', 'top-right', 'bottom-left', 'bottom-right'
        self.drag_start_pos = None
        self.original_rect = QRect()

        # The size in pixels around a corner that will be sensitive to dragging.
        self.hit_threshold = 10

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill the entire window with a semi-transparent dark overlay.
        overlay_color = QColor(0, 0, 0, 150)
        painter.fillRect(self.rect(), overlay_color)

        # Set the composition mode to clear so that the focus rectangle becomes transparent.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)

        # Create a path with a rounded rectangle for the focus area.
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.focus_rect), self.corner_radius, self.corner_radius)
        painter.fillPath(path, QColor(0, 0, 0, 0))

        # Draw an outline around the focus rectangle.
        # painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        border_pen = QPen(QColor(255, 255, 255), 2)
        painter.setPen(border_pen)
        painter.drawRoundedRect(self.focus_rect, self.corner_radius, self.corner_radius)

    def mousePressEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()

        # Check whether we have pressed near one of the four corners.
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
                return  # Only one corner action

    def mouseMoveEvent(self, event):
        if not self.dragging:
            return

        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        dx = pos.x() - self.drag_start_pos.x()
        dy = pos.y() - self.drag_start_pos.y()
        rect = QRect(self.original_rect)

        # Minimum allowed dimensions for the focus rectangle.
        min_width = 50
        min_height = 50

        # Update the rectangle based on which corner is being dragged.
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

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.drag_corner = None


def main():
    app = QApplication(sys.argv)
    widget = FocusOverlayWidget()
    widget.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()