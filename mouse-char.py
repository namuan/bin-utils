import sys
import math
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor, QTransform
from PyQt6.QtCore import Qt, QTimer, QPointF, QPoint

class Missile:
    def __init__(self, start_pos, target_pos):
        self.pos = QPointF(start_pos.x(), start_pos.y())
        self.target = QPointF(target_pos.x(), target_pos.y())
        self.speed = 5
        self.width = 4
        self.length = 12
        direction = self.target - self.pos
        distance = (direction.x() ** 2 + direction.y() ** 2) ** 0.5
        if distance > 0:
            self.velocity = QPointF(
                direction.x() * self.speed / distance,
                direction.y() * self.speed / distance
            )
            self.angle = math.degrees(math.atan2(direction.y(), direction.x()))
        else:
            self.velocity = QPointF(0, 0)
            self.angle = 0
        self.active = True

    def update(self, mouse_pos):
        self.pos += self.velocity
        distance_to_mouse = ((mouse_pos.x() - self.pos.x()) ** 2 + (mouse_pos.y() - self.pos.y()) ** 2) ** 0.5
        if distance_to_mouse < self.width + 10:
            self.active = False
            return True
        distance_to_target = ((self.target.x() - self.pos.x()) ** 2 + (self.target.y() - self.pos.y()) ** 2) ** 0.5
        if distance_to_target < self.speed:
            self.active = False
        return False

    def draw(self, painter):
        if self.active:
            painter.save()
            painter.translate(self.pos.x(), self.pos.y())
            painter.rotate(self.angle)
            pen = QPen(QColor(0, 255, 0, 200), 1)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 255, 0, 100))
            painter.drawEllipse(QPoint(0, 0), int(self.length / 2), int(self.width / 2))
            painter.restore()

class Explosion:
    def __init__(self, pos):
        self.pos = QPointF(pos.x(), pos.y())
        self.radius = 5
        self.max_radius = 30
        self.alpha = 255
        self.active = True
        self.growth_rate = 2
        self.fade_rate = 15

    def update(self):
        self.radius += self.growth_rate
        self.alpha -= self.fade_rate
        if self.radius >= self.max_radius or self.alpha <= 0:
            self.active = False

    def draw(self, painter):
        if self.active:
            pen = QPen(QColor(255, 165, 0, int(self.alpha)), 2)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 165, 0, int(self.alpha / 2)))
            render_pos = QPoint(int(self.pos.x()), int(self.pos.y()))
            painter.drawEllipse(render_pos, int(self.radius), int(self.radius))

class TransparentCharacter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initCharacter()
        self.initTimer()
        self.missiles = []
        self.explosions = []
        self.fire_cooldown = 0
        self.fire_interval = 15

    def initUI(self):
        self.setWindowTitle('Transparent Character')
        self.showMaximized()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setMouseTracking(True)

    def initCharacter(self):
        self.char_pos = QPointF(200, 150)
        self.char_radius = 20
        self.move_speed = 2
        self.pulse_phase = 0  # Tracks sine wave phase for pulsing

    def initTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateCharacter)
        self.timer.start(16)

    def updateCharacter(self):
        global_mouse_pos = QCursor.pos()
        mouse_pos = self.mapFromGlobal(global_mouse_pos)
        mouse_pos_f = QPointF(mouse_pos.x(), mouse_pos.y())
        direction = mouse_pos_f - self.char_pos
        distance = (direction.x() ** 2 + direction.y() ** 2) ** 0.5
        if distance > 0:
            direction = QPointF(
                direction.x() * self.move_speed / distance,
                direction.y() * self.move_speed / distance
            )
            self.char_pos += direction
            self.char_pos.setX(max(self.char_radius, min(self.screen().size().width() - self.char_radius, self.char_pos.x())))
            self.char_pos.setY(max(self.char_radius, min(self.screen().size().height() - self.char_radius, self.char_pos.y())))

        # Update pulse phase
        self.pulse_phase += 0.1  # Adjust for pulse speed

        # Handle missile firing
        if self.fire_cooldown <= 0:
            missile = Missile(self.char_pos, mouse_pos)
            self.missiles.append(missile)
            self.fire_cooldown = self.fire_interval
        else:
            self.fire_cooldown -= 1

        # Update missiles and check for hits
        for missile in self.missiles:
            if missile.update(mouse_pos):
                self.explosions.append(Explosion(missile.pos))
        self.missiles = [m for m in self.missiles if m.active]

        # Update explosions
        for explosion in self.explosions:
            explosion.update()
        self.explosions = [e for e in self.explosions if e.active]

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dynamic radius for pulsing effect
        current_radius = self.char_radius + 2 * math.sin(self.pulse_phase)

        # Draw character with pulsing radius
        pen = QPen(QColor(255, 0, 0, 200), 2)
        painter.setPen(pen)
        painter.setBrush(QColor(255, 0, 0, 100))
        render_pos = QPoint(int(self.char_pos.x()), int(self.char_pos.y()))
        painter.drawEllipse(render_pos, int(current_radius), int(current_radius))

        # Draw missiles
        for missile in self.missiles:
            missile.draw(painter)

        # Draw explosions
        for explosion in self.explosions:
            explosion.draw(painter)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TransparentCharacter()
    window.show()
    sys.exit(app.exec())
