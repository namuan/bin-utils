import sys
from dataclasses import dataclass
from typing import List

from PyQt6 import QtWidgets
from PyQt6.QtCore import QRectF
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass
class CodeClass:
    class_name: str
    methods: List[str]


class BoundingRect(QGraphicsRectItem):
    def __init__(self, pos: QRectF, code_class: CodeClass):
        super().__init__()
        self.pos = pos
        self.code_class = code_class
        self.__init_ui()

    def __init_ui(self):
        self.acceptHoverEvents()
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
        self.setRect(self.pos)
        self.render()

    def box(self):
        return QRectF(
            self.rect().x(),
            self.rect().y(),
            self.rect().width(),
            self.rect().height(),
        )

    def render(self):
        class_data = '<div style="font-family: Arial; font-size: 14px;">'
        class_data += f"<strong>{self.code_class.class_name}</strong><br>"
        class_data += "-----<br>"
        class_data += "<br>".join([f"{method}" for method in self.code_class.methods])
        class_data += "</div>"
        t = QGraphicsTextItem(self)
        t.setHtml(class_data)
        t.setPos(self.pos.x(), self.pos.y())


class BoundingEllipse(QGraphicsRectItem):
    def __init__(self, child_boxes: List[BoundingRect]):
        super().__init__(self.__find_boundaries([x.box() for x in child_boxes]))

    @staticmethod
    def __find_boundaries(child_boxes: List[QRectF]) -> QRectF:
        top_left_most = child_boxes[0]
        bottom_right_most = child_boxes[0]

        for child in child_boxes:
            # update top_left_most
            if child.x() < top_left_most.x() or (child.x() == top_left_most.x() and child.y() < top_left_most.y()):
                top_left_most = child

            # update bottom_right_most
            child_right = child.x() + child.width()
            child_bottom = child.y() + child.height()
            bottom_right_most_right = bottom_right_most.x() + bottom_right_most.width()
            bottom_right_most_bottom = bottom_right_most.y() + bottom_right_most.height()

            if child_right > bottom_right_most_right or (
                child_right == bottom_right_most_right and child_bottom > bottom_right_most_bottom
            ):
                bottom_right_most = child

        return QRectF(
            top_left_most.x() - 10,
            top_left_most.y() - 10,
            bottom_right_most.x() + bottom_right_most.width() - top_left_most.x() + 20,
            bottom_right_most.y() + bottom_right_most.height() - top_left_most.y() + 20,
        )


class ZoomGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.__zoom = 0
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            factor = 1.25
            self.__zoom += 1
        else:
            factor = 0.8

        if self.__zoom > 0:
            self.scale(factor, factor)
        else:
            self.__zoom = 0


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.__init_ui()

    def __init_ui(self):
        view = ZoomGraphicsView()
        self.__scene = QGraphicsScene()
        self.__scene.setSceneRect(0, 0, 800, 800)

        item1 = BoundingRect(
            QRectF(100, 100, 100, 100), CodeClass(class_name="MyClassA", methods=["method1", "method2"])
        )
        item2 = BoundingRect(
            QRectF(500, 100, 100, 100), CodeClass(class_name="MyClassB", methods=["method1", "method2"])
        )
        item3 = BoundingRect(
            QRectF(500, 500, 100, 100), CodeClass(class_name="MyClassC", methods=["method1", "method2"])
        )
        # item.setLineWidth(8) If you want to change the edge line width, add the code.
        # item.setColor(QColor(255, 255, 255)) If you want to change the color of the line to white, add the code.
        # item.setStyle(Qt.SolidLine) If you want to change the style of line from dashed to solid line, add the code.
        self.__scene.addItem(item1)
        self.__scene.addItem(item2)
        self.__scene.addItem(item3)

        items_group = BoundingEllipse([item1, item2, item3])
        self.__scene.addItem(items_group)
        view.setScene(self.__scene)

        lay = QVBoxLayout()
        lay.addWidget(view)

        self.setLayout(lay)


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec()


if __name__ == "__main__":
    main()
