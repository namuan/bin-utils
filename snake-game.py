import random
import time

import pygame


class Snake:
    def __init__(self):
        self.body = [(0, 0)]
        self.direction = "right"

    def draw(self, screen):
        for i in self.body:
            pygame.draw.rect(screen, "Yellow", (i[0] * 21 + 25, i[1] * 21 + 25, 20, 20))

    def update(self, apple):
        last_snake_position = self.body[0]
        new_snake_position = None

        if self.direction == "up":
            new_snake_position = (last_snake_position[0], last_snake_position[1] - 1)
        elif self.direction == "down":
            new_snake_position = (last_snake_position[0], last_snake_position[1] + 1)
        elif self.direction == "left":
            new_snake_position = (last_snake_position[0] - 1, last_snake_position[1])
        elif self.direction == "right":
            new_snake_position = (last_snake_position[0] + 1, last_snake_position[1])

        # check wall collision
        if (
            new_snake_position[0] < 0
            or new_snake_position[0] >= 20
            or new_snake_position[1] < 0
            or new_snake_position[1] >= 15
        ):
            return True

        # check snake collision
        for i in self.body:
            if new_snake_position == i:
                return True

        # add snake block
        self.body.insert(0, new_snake_position)

        # check apple collission
        if new_snake_position == apple.position:
            apple.regen()
        else:
            # remove the oldest block
            self.body.pop()

        return False

    def score(self):
        return len(self.body) - 1

    def change_direction(self, key):
        if key == pygame.K_UP:
            if self.direction != "down":
                self.direction = "up"
        elif key == pygame.K_DOWN:
            if self.direction != "up":
                self.direction = "down"
        elif key == pygame.K_LEFT:
            if self.direction != "right":
                self.direction = "left"
        elif key == pygame.K_RIGHT:
            if self.direction != "left":
                self.direction = "right"


class Apple:
    def __init__(self):
        self.position = None

    def regen(self):
        self.position = (random.randint(0, 19), random.randint(0, 14))

    def draw(self, screen):
        if self.position:
            pygame.draw.rect(screen, "Red", (self.position[0] * 21 + 25, self.position[1] * 21 + 25, 20, 20))


class World:
    def __init__(self):
        pygame.init()
        self.font = pygame.font.Font(None, 25)
        self.screen = pygame.display.set_mode((800, 400))
        self.regen()

    def regen(self):
        self.snake = Snake()
        self.apple = Apple()
        self.game_over = False

    def get_input(self, input_events):
        for event in input_events:
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()
                elif event.key == pygame.K_SPACE:
                    self.regen()
                else:
                    self.snake.change_direction(event.key)

    def update_state(self):
        # update state
        if not self.apple.position:
            self.apple.regen()

        if not self.game_over:
            self.game_over = self.snake.update(self.apple)

    def draw(self):
        self.screen.fill("Blue")

        for x in range(20):
            for y in range(15):
                pygame.draw.rect(self.screen, "Black", (x * 21 + 25, y * 21 + 25, 20, 20))

        self.draw_text("SCORE: %d" % self.snake.score(), "Green", 500, 25)

        if self.game_over:
            self.draw_text("GAME OVER", "Green", 25, 360)

        self.apple.draw(self.screen)
        self.snake.draw(self.screen)

        pygame.display.update()

    def draw_text(self, text, color, x, y):
        text_image = self.font.render(text, True, color)
        self.screen.blit(text_image, ((x, y)))

    def quit(self):
        pygame.quit()
        exit()


####

world = World()

while True:
    # get input
    world.get_input(pygame.event.get())

    # update state
    world.update_state()

    # draw world
    world.draw()

    time.sleep(1 / 10)
