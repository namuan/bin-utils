#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "pynput",
#   "pyautogui",
# ]
# ///
"""
A PyAutoGUI script recorder and converter.

Records mouse and keyboard actions and converts them to a PyAutoGUI script.
Use double Ctrl press to stop recording.

Usage:
./pyautogui-script-generator.py -h
./pyautogui-script-generator.py -v  # To log INFO messages
./pyautogui-script-generator.py -vv # To log DEBUG messages
"""
import logging
import time
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any

from pynput import mouse, keyboard


@dataclass
class AutoGuiScriptGenerator:
    recording: List[Dict[str, Any]] = field(default_factory=list)
    last_ctrl_press_time: float = 0
    exit_script: bool = False
    key_mappings: Dict[str, str] = field(default_factory=lambda: {
        "cmd": "win",
        "alt_l": "alt",
        "alt_r": "alt",
        "ctrl_l": "ctrl",
        "ctrl_r": "ctrl"
    })

    def on_press(self, key):
        try:
            json_object = {"action": "pressed_key", "key": key.char, "_time": time.time()}
        except AttributeError:
            if key == keyboard.Key.ctrl:
                current_time = time.time()
                if current_time - self.last_ctrl_press_time < 0.5:
                    print("Recording saved. Converting to PyAutoGUI script...")
                    self.exit_script = True
                    return False
                self.last_ctrl_press_time = current_time

            json_object = {"action": "pressed_key", "key": str(key), "_time": time.time()}

        logging.debug(f"Captured {json_object}")
        self.recording.append(json_object)

    def on_release(self, key):
        try:
            json_object = {"action": "released_key", "key": key.char, "_time": time.time()}
        except AttributeError:
            json_object = {"action": "released_key", "key": str(key), "_time": time.time()}

        logging.debug(f"Captured {json_object}")
        self.recording.append(json_object)

    def on_click(self, x, y, button, pressed):
        if self.exit_script:
            return False

        json_object = {
            "action": "clicked" if pressed else "unclicked",
            "button": str(button),
            "x": x,
            "y": y,
            "_time": time.time(),
        }

        logging.debug(f"Captured {json_object}")
        self.recording.append(json_object)

    def on_scroll(self, x, y, dx, dy):
        json_object = {
            "action": "scroll",
            "vertical_direction": int(dy),
            "horizontal_direction": int(dx),
            "x": x,
            "y": y,
            "_time": time.time(),
        }

        logging.debug(f"Captured {json_object}")
        self.recording.append(json_object)

    def on_move(self, x, y):
        if len(self.recording) >= 1:
            if (self.recording[-1]["action"] == "pressed" and self.recording[-1]["button"] == "Button.left") or (
                    self.recording[-1]["action"] == "moved" and time.time() - self.recording[-1]["_time"] > 0.02
            ):
                json_object = {"action": "moved", "x": x, "y": y, "_time": time.time()}

                logging.debug(f"Captured {json_object}")
                self.recording.append(json_object)

    def start_recording(self):
        logging.info("Started recording... Press Ctrl twice to stop")
        keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        mouse_listener = mouse.Listener(on_click=self.on_click, on_scroll=self.on_scroll, on_move=self.on_move)

        keyboard_listener.start()
        mouse_listener.start()
        keyboard_listener.join()
        mouse_listener.join()

    def convert_to_pyautogui_script(self, recording: List[Dict[str, Any]],
                                    output_file: Path) -> None:
        """Converts recording to a Python script using PyAutoGUI"""

        # Filter out released and scroll events
        def excluded_actions(object):
            return "released" not in object["action"] and \
                "scroll" not in object["action"]

        recording = list(filter(excluded_actions, recording))

        if not recording:
            return

        with open(output_file, "w") as output:
            output.write("import time\n")
            output.write("import pyautogui\n\n")

            for i, step in enumerate(recording):
                print(step)

                not_first_element = (i - 1) > 0
                if not_first_element:
                    pause_in_seconds = (step["_time"] - recording[i - 1]["_time"]) * 1.1
                    output.write(f"time.sleep({pause_in_seconds})\n\n")
                else:
                    output.write("time.sleep(1)\n\n")

                if step["action"] == "pressed_key":
                    key = step["key"].replace("Key.", "") if "Key." in step["key"] else step["key"]

                    if key in self.key_mappings:
                        key = self.key_mappings[key]

                    output.write(f"pyautogui.press('{key}')\n")

                if step["action"] == "clicked":
                    output.write(f"pyautogui.moveTo({step['x']}, {step['y']})\n")

                    if step["button"] == "Button.right":
                        output.write("pyautogui.mouseDown(button='right')\n")
                    else:
                        output.write("pyautogui.mouseDown()\n")

                if step["action"] == "unclicked":
                    output.write(f"pyautogui.moveTo({step['x']}, {step['y']})\n")

                    if step["button"] == "Button.right":
                        output.write("pyautogui.mouseUp(button='right')\n")
                    else:
                        output.write("pyautogui.mouseUp()\n")

        print(f"Recording converted. Saved to '{output_file}'")


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[
            logging.StreamHandler(),
        ],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


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
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output script path",
    )
    return parser.parse_args()


def main(args):
    script_generator = AutoGuiScriptGenerator()
    script_generator.start_recording()
    script_generator.convert_to_pyautogui_script(script_generator.recording, args.output)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
