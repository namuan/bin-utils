#!/usr/bin/env python3
"""
Simple script to demonstrate animating software architecture diagrams using PyGame

Requires
* brew install imagemagick

Usage:
./arch-animate.py -h
"""
import logging
import os
import subprocess
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

import pygame as pg
from pygame.locals import QUIT

from common_utils import setup_logging


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-c", "--convert-to-animation", default=False, action="store_true", help="Generate animated gif"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    return parser.parse_args()


directory_now = os.path.dirname(os.path.realpath(__file__))
output_directory = Path.cwd() / "output_dir"
output_directory.mkdir(exist_ok=True)

pg.init()

# colors
bg_color = (255, 255, 255)  # white

aqua = (0, 255, 255)
black = (0, 0, 0)
blue = (0, 0, 255)
fuchsia = (255, 0, 255)
gray = (128, 128, 128)
green = (0, 128, 0)
lime = (0, 255, 0)
maroon = (128, 0, 0)
navy_blue = (0, 0, 128)
olive = (128, 128, 0)
purple = (128, 0, 128)
red = (255, 0, 0)
silver = (192, 192, 192)
teal = (0, 128, 128)
white = (255, 255, 255)
yellow = (255, 255, 0)

# fonts
application_label_font = pg.font.SysFont("Arial", 15)


def convert_files_to_animated_gif(frame_delay, filename_list):
    target_filename = "arch-animate-final.gif"
    command_list = ["convert", "-delay", frame_delay, "-loop", "0"] + filename_list + [target_filename]
    logging.info(f"🚒 Converting to animated gif {' '.join(command_list)}")
    subprocess.call(command_list, cwd=output_directory)
    logging.info("Deleting temporary generated files ...")
    for f in output_directory.glob("temp-arch-animate*.png"):
        f.unlink(missing_ok=True)
    logging.info(f"✅ Generated {target_filename}")


def update(dt):
    """
    Update game. Called once per frame.
    dt is the amount of time passed since last frame.
    If you want to have constant apparent movement no matter your framerate,
    what you can do is something like
    x += v * dt
    and this will scale your velocity based on time. Extend as necessary."""

    # Go through events that are passed to the script by the window.
    for event in pg.event.get():
        # We need to handle these events. Initially the only one you'll want to care
        # about is the QUIT event, because if you don't handle it, your game will crash
        # whenever someone tries to exit.
        if event.type == QUIT:
            pg.quit()  # Opposite of pygame.init
            sys.exit()  # Not including this line crashes the script on Windows. Possibly
            # on other operating systems too, but I don't know for sure.
        # Handle other events as you wish.


def darker(c):
    shade_factor = 0.5
    newR = c[0] * (1 - shade_factor)
    newG = c[1] * (1 - shade_factor)
    newB = c[2] * (1 - shade_factor)
    return newR, newG, newB


def lighten(c):
    factor = 0.2
    return [255 - (255 - c[0]) * (1 - factor), 255 - (255 - c[1]) * (1 - factor), 255 - (255 - c[2]) * (1 - factor)]


class Application:
    def __init__(self, label, start_x, start_y, height, width, color):
        self.label = label
        self.x = start_x
        self.y = start_y
        self.height = height
        self.width = width
        self.color = color
        self.border_width = 4

    def draw_on(self, drawing_screen):
        pg.draw.rect(drawing_screen, lighten(self.color), [self.x, self.y, self.width, self.height], 0)
        for i in range(self.border_width):
            pg.draw.rect(
                drawing_screen,
                darker(self.color),
                [self.x - i, self.y - i, self.width + self.border_width, self.height + self.border_width],
                1,
            )
        rendered_label = application_label_font.render(self.label, True, black)
        drawing_screen.blit(rendered_label, (self.x, self.y - 20))

    def move_to(self, x, y):
        self.x = self.x + x
        self.y += y

    def centre(self):
        return self.x + (self.width / 2), self.y + (self.height / 2)


class Message:
    def __init__(self, source_component: Application):
        self.x, self.y = source_component.centre()
        self.color = yellow
        self.radius = 8
        self.border_width = 1

    def draw_on(self, drawing_screen):
        pg.draw.circle(drawing_screen, lighten(self.color), (self.x, self.y), self.radius, 0)
        for i in range(self.border_width):
            pg.draw.circle(drawing_screen, darker(self.color), (self.x - i, self.y - i), self.radius + i, 1)

    def move_to(self, target_component):
        target_centre_x, target_centre_y = target_component.centre()
        dx, dy = (target_centre_x - self.x, target_centre_y - self.y)
        step_x, step_y = (dx / 25.0, dy / 25.0)

        self.x = self.x + step_x
        self.y = self.y + step_y


app_a = Application("Gateway", 100, 100, 50, 100, lime)
app_b = Application("Payment Service", 400, 100, 50, 100, fuchsia)
message = Message(app_a)
message_2 = Message(app_b)


def draw_scene(screen):
    app_a.draw_on(screen)
    app_b.draw_on(screen)
    message.draw_on(screen)
    message.move_to(app_b)
    message_2.draw_on(screen)
    message_2.move_to(app_a)


def draw(screen):
    """
    Draw things to the window. Called once per frame.
    """
    screen.fill(bg_color)

    # Redraw screen here.
    draw_scene(screen)

    # Flip the display so that the things we drew actually show up.
    pg.display.flip()


def draw_diagram(args):
    fps = 60
    fps_clock = pg.time.Clock()

    img_height = 640
    img_width = 480

    # shrink for smooth-ness
    final_height = int(round(0.3 * img_height))
    final_width = int(round(0.3 * img_width))

    screen = pg.display.set_mode((img_height, img_width))
    pg.display.set_caption("Arch Animate")

    frame_number = 0
    dt = 1 / fps * 1000
    while True:
        update(dt)
        draw(screen)

        # Save screen
        shrunk_surface = pg.transform.smoothscale(screen, (final_width, final_height))
        if args.convert_to_animation:
            pg.image.save(shrunk_surface, output_directory / f"temp-arch-animate-{frame_number}.png")
            frame_number += 1

        dt = fps_clock.tick(fps)


def main(args):
    draw_diagram(args)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
