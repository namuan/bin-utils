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

# Colors

bg_color = (255, 255, 255)  # white
some_color = (255, 0, 0)


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


def draw_scene(screen):
    pg.draw.circle(screen, some_color, (300, 50), 100, 1)


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
    pg.init()

    fps = 60
    fps_clock = pg.time.Clock()

    img_height = 640
    img_width = 480

    # shrink for smooth-ness
    final_height = int(round(0.3 * img_height))
    final_width = int(round(0.3 * img_width))

    screen = pg.display.set_mode((img_height, img_width))

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
