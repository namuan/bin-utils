#!/usr/bin/env python3
"""
A simple script to capture mouse position
# From: https://github.com/renanstn/mouse-screen-position/blob/master/src/screen_position.py
"""
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from tkinter import END, INSERT, LEFT, Button, Frame, IntVar, Label, Text, Tk

import pyautogui


class App:
    def __init__(self, base):
        base.title("Mouse Position")
        base.resizable(0, 0)
        self.pos_x = IntVar()
        self.pos_y = IntVar()
        self.rgb_r = IntVar()
        self.rgb_g = IntVar()
        self.rgb_b = IntVar()
        self.frame0 = Frame(base)
        self.frame0.pack()
        self.frame1 = Frame(base)
        self.frame1.pack(fill="x")
        self.lb_x = Label(self.frame0)
        self.lb_y = Label(self.frame0)
        self.lb_rgb = Label(self.frame0)
        self.bt_take = Button(self.frame0, text="Take", command=self.take)
        self.tx_log = Text(self.frame1, height=10, width=40)
        self.bt_reset = Button(self.frame0, text="Reset", command=self.reset)
        self.lb_x.pack(side=LEFT)
        self.lb_y.pack(side=LEFT)
        self.lb_rgb.pack(side=LEFT)
        self.bt_take.pack(side=LEFT)
        self.bt_reset.pack(side=LEFT)
        self.tx_log.pack(fill="x")
        self.bt_take.focus_force()
        self.bt_take.bind("<Return>", self.take)

    def take(self):
        pos = pyautogui.position()
        rgb = pyautogui.screenshot().getpixel(pos)
        self.pos_x = pos[0]
        self.pos_y = pos[1]
        self.rgb_r = rgb[0]
        self.rgb_g = rgb[1]
        self.rgb_b = rgb[2]

        self.lb_x["text"] = "X: %i" % self.pos_x
        self.lb_y["text"] = "Y: %i -" % self.pos_y
        self.lb_rgb["text"] = "(R: %i G: %i B: %i)" % (self.rgb_r, self.rgb_g, self.rgb_b)

        self.tx_log.insert(INSERT, "X: %i " % self.pos_x)
        self.tx_log.insert(INSERT, "Y: %i - " % self.pos_y)
        self.tx_log.insert(INSERT, "(R: %i G: %i B: %i)\n" % (self.rgb_r, self.rgb_g, self.rgb_b))

    def reset(self):
        self.lb_x["text"] = ""
        self.lb_y["text"] = ""
        self.lb_rgb["text"] = ""
        self.tx_log.delete(0.0, END)
        self.bt_take.focus_force()


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
    return parser.parse_args()


def main(args):
    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    args = parse_args()
    main(args)
