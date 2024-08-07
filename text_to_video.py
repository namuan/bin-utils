#!/usr/bin/env python3

"""
Text-to-Video Generator

This script converts text files into a video where each word appears sequentially.
It uses MoviePy to create video clips for each word and concatenates them into a final video.

Examples:
    Basic usage:
    python text_to_video.py -i input.txt -o output.mp4

    With verbose logging:
    python text_to_video.py -i input.txt -o output.mp4 -v

    Multiple input files:
    python text_to_video.py -i file1.txt file2.txt -o output.mp4
"""

import argparse
import logging
import re
from multiprocessing import cpu_count

from moviepy.editor import (
    ColorClip,
    CompositeVideoClip,
    TextClip,
    concatenate_videoclips,
)


def create_word_clip(
    word,
    duration=0.5,
    fontsize=70,
    font="Arial",
    text_color="white",
    border_color="black",
    border_width=2,
    fade_duration=0.1,
):
    def create_text_clip(color):
        return TextClip(word, fontsize=fontsize, color=color, font=font, stroke_color=color, stroke_width=border_width)

    txt_clip = create_text_clip(text_color)
    border_clip = create_text_clip(border_color)

    composed_clip = CompositeVideoClip([border_clip, txt_clip]).set_duration(duration)

    # Add fade in and fade out
    return composed_clip.fadein(fade_duration).fadeout(fade_duration)


def create_pause_clip(duration=1.0):
    return ColorClip(size=(500, 100), color=(0, 0, 0)).set_duration(duration)


def create_video_from_text_files(file_names, output_file):
    clips = []
    for file_name in file_names:
        logging.info(f"Processing file: {file_name}")
        with open(file_name) as file:
            text = file.read()
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                words = sentence.split()
                for i, word in enumerate(words):
                    logging.debug(f"Creating clip for word: {word}")
                    clip = create_word_clip(
                        word, text_color="white", border_color="black", border_width=2, fade_duration=0.3
                    )
                    clips.append(clip)

                    # Add a small pause after each word
                    clips.append(create_pause_clip(0.1))

                # Add a longer pause at the end of each sentence
                clips.append(create_pause_clip(1.0))

    logging.info("Concatenating clips...")
    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.on_color(size=(500, 100), color=(0, 0, 0))

    logging.info(f"Writing video file: {output_file}")
    final_clip.write_videofile(
        output_file, fps=120, codec="libx264", preset="superfast", audio=False, threads=cpu_count()
    )
    logging.info("Video creation completed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-i", "--input", nargs="+", required=True, help="Input text file(s)")
    parser.add_argument("-o", "--output", required=True, help="Output video file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

    create_video_from_text_files(args.input, args.output)


if __name__ == "__main__":
    main()
