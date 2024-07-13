import random
import sys

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsLinearLayout,
    QGraphicsLineItem,
    QGraphicsProxyWidget,
    QGraphicsScene,
    QGraphicsView,
    QGraphicsWidget,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
)


class LinkLine(QGraphicsLineItem):
    def __init__(self, parent, child):
        super().__init__()
        self.parent = parent
        self.child = child
        self.setPen(QPen(QColor(100, 100, 100), 2, Qt.PenStyle.DashLine))
        self.setZValue(-1)  # Ensure the line is drawn behind the forms
        self.updatePosition()

    def updatePosition(self):
        parent_center = self.parent.mapToScene(self.parent.boundingRect().center())
        child_center = self.child.mapToScene(self.child.boundingRect().center())
        self.setLine(parent_center.x(), parent_center.y(), child_center.x(), child_center.y())


class HeaderWidget(QGraphicsWidget):
    cloneRequested = pyqtSignal()
    deleteRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(30)
        self.setMaximumHeight(30)

    def paint(self, painter, option, widget):
        # Draw the main header background
        painter.fillRect(self.boundingRect(), QBrush(QColor(200, 200, 200)))

        # Draw the draggable area with a bright color
        drag_rect = QRectF(0, 0, self.boundingRect().width() - 120, self.boundingRect().height())
        painter.fillRect(drag_rect, QBrush(QColor(100, 200, 255)))  # Bright blue color

        # Draw "Drag Here" text
        painter.setPen(QColor(0, 0, 0))  # Set text color to black for better visibility
        painter.drawText(drag_rect, Qt.AlignmentFlag.AlignCenter, "Drag Here")

        # Draw "Clone" button
        clone_rect = QRectF(self.boundingRect().width() - 120, 0, 60, self.boundingRect().height())
        painter.fillRect(clone_rect, QBrush(QColor(180, 180, 180)))
        painter.drawText(clone_rect, Qt.AlignmentFlag.AlignCenter, "Clone")

        # Draw "Delete" button
        delete_rect = QRectF(self.boundingRect().width() - 60, 0, 60, self.boundingRect().height())
        painter.fillRect(delete_rect, QBrush(QColor(255, 100, 100)))
        painter.drawText(delete_rect, Qt.AlignmentFlag.AlignCenter, "Delete")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            clone_rect = QRectF(self.boundingRect().width() - 120, 0, 60, self.boundingRect().height())
            delete_rect = QRectF(self.boundingRect().width() - 60, 0, 60, self.boundingRect().height())
            if clone_rect.contains(event.pos()):
                self.cloneRequested.emit()
            elif delete_rect.contains(event.pos()):
                self.deleteRequested.emit()
            else:
                super().mousePressEvent(event)


class FormWidget(QGraphicsWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.parent_form = parent
        self.child_forms = []
        self.link_line = None

        # Create main layout
        main_layout = QGraphicsLinearLayout(Qt.Orientation.Vertical)

        # Create and add header
        self.header = HeaderWidget()
        self.header.cloneRequested.connect(self.cloneForm)
        self.header.deleteRequested.connect(self.deleteForm)
        main_layout.addItem(self.header)

        # Create form layout
        form_layout = QGraphicsLinearLayout(Qt.Orientation.Vertical)

        # Create form elements and their proxies
        name_label = QGraphicsProxyWidget()
        name_label.setWidget(QLabel("Name:"))

        self.name_input = QGraphicsProxyWidget()
        self.name_input.setWidget(QLineEdit())

        email_label = QGraphicsProxyWidget()
        email_label.setWidget(QLabel("Email:"))

        self.email_input = QGraphicsProxyWidget()
        self.email_input.setWidget(QLineEdit())

        submit_button = QGraphicsProxyWidget()
        submit_button_widget = QPushButton("Submit")
        submit_button_widget.clicked.connect(self.submitForm)
        submit_button.setWidget(submit_button_widget)

        # Add form elements to form layout
        form_layout.addItem(name_label)
        form_layout.addItem(self.name_input)
        form_layout.addItem(email_label)
        form_layout.addItem(self.email_input)
        form_layout.addItem(submit_button)

        # Add form layout to main layout
        main_layout.addItem(form_layout)

        # Set the layout for this widget
        self.setLayout(main_layout)

    def paint(self, painter, option, widget):
        # Draw a background for the entire form
        painter.fillRect(self.boundingRect(), QBrush(QColor(240, 240, 240)))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.header.boundingRect().contains(event.pos()):
            # Only start dragging if the mouse is pressed in the header area
            super().mousePressEvent(event)
        else:
            # For clicks outside the header, pass the event to children
            event.ignore()

    def mouseMoveEvent(self, event):
        if self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable:
            super().mouseMoveEvent(event)
            self.updateLinkLines()
        else:
            event.ignore()

    def cloneForm(self):
        # Calculate the size of the current form
        form_width = self.boundingRect().width()
        form_height = self.boundingRect().height()

        # Define the minimum gap between forms
        min_gap = 20

        # Generate a random offset for a more natural spread
        random_offset_x = random.randint(min_gap, min_gap * 2)
        random_offset_y = random.randint(min_gap, min_gap * 2)

        # Determine the new position (bottom right of the parent)
        new_pos = self.pos() + QPointF(form_width + random_offset_x, form_height + random_offset_y)

        # Create the new form
        new_form = FormWidget(parent=self)
        new_form.setPos(new_pos)
        self.scene().addItem(new_form)
        self.child_forms.append(new_form)

        # Create a link line between this form and the new form
        link_line = LinkLine(self, new_form)
        self.scene().addItem(link_line)
        new_form.link_line = link_line

        # Ensure the new form is fully within the scene
        self.adjustFormPosition(new_form)

        # Update the link line position
        link_line.updatePosition()

    def adjustFormPosition(self, form):
        scene_rect = self.scene().sceneRect()
        form_rect = form.sceneBoundingRect()

        # If the form is outside the scene, adjust its position
        if not scene_rect.contains(form_rect):
            new_x = min(max(form_rect.left(), scene_rect.left()), scene_rect.right() - form_rect.width())
            new_y = min(max(form_rect.top(), scene_rect.top()), scene_rect.bottom() - form_rect.height())
            form.setPos(new_x, new_y)

    def deleteForm(self):
        # Remove this form from its parent's child_forms list
        if self.parent_form:
            self.parent_form.child_forms.remove(self)

        # Recursively delete all child forms
        for child in self.child_forms[:]:  # Create a copy of the list to iterate over
            child.deleteForm()

        # Remove the link line connecting this form to its parent
        if self.link_line:
            self.scene().removeItem(self.link_line)
            self.link_line = None

        # Remove this form from the scene
        self.scene().removeItem(self)

    def updateLinkLines(self):
        if self.link_line:
            self.link_line.updatePosition()
        for child in self.child_forms:
            child.updateLinkLines()

    def submitForm(self):
        form_data = self.gatherFormData()
        message = "Form submitted with the following data:\n\n"
        for i, data in enumerate(form_data):
            message += f"Form {i + 1}:\n"
            message += f"Name: {data['name']}\n"
            message += f"Email: {data['email']}\n\n"
        QMessageBox.information(None, "Form Submitted", message)

    def gatherFormData(self):
        data = []
        current_form = self
        while current_form:
            form_data = {
                "name": current_form.name_input.widget().text(),
                "email": current_form.email_input.widget().text(),
            }
            data.append(form_data)
            current_form = current_form.parent_form
        return reversed(data)  # Reverse to get parent data first


class MainWindow(QGraphicsView):
    def __init__(self):
        super().__init__()

        # Create a scene and set it as the scene for this view
        scene = QGraphicsScene(self)
        self.setScene(scene)

        # Create the form widget and add it to the scene
        form_widget = FormWidget()
        scene.addItem(form_widget)

        # Set up the main window
        self.setWindowTitle("Draggable Form with Clone and Delete")
        self.resize(600, 400)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
