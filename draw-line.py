# /// script
# dependencies = [
#   "moviepy",
# ]
# ///
# !/usr/bin/env python3
"""
A simple script

Usage:
./template_py_scripts.py -h

./template_py_scripts.py -v # To log INFO messages
./template_py_scripts.py -vv # To log DEBUG messages
"""

import logging
import os
import platform
import subprocess
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import numpy as np
from moviepy.editor import ColorClip, CompositeVideoClip, VideoFileClip
from moviepy.video.VideoClip import VideoClip


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
    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input video file",
    )
    parser.add_argument(
        "--output",
        default="output_with_line.mp4",
        help="Path to the output video file (default: output_with_line.mp4)",
    )
    parser.add_argument(
        "--color",
        default="#FF0000",
        help="Line color in hex format (default: #FF0000 for red)",
    )
    parser.add_argument(
        "--thickness",
        type=int,
        default=5,
        help="Line thickness in pixels (default: 5)",
    )
    parser.add_argument(
        "--draw-duration",
        type=float,
        default=2.0,
        help="Duration in seconds for the line to draw (default: 2.0)",
    )
    parser.add_argument(
        "--start-time",
        type=float,
        default=10.0,
        help="Time in seconds when the line should start animating (default: 10.0)",
    )
    parser.add_argument(
        "--absolute",
        action="store_true",
        default=True,
        help="Use absolute pixel coordinates instead of percentages",
    )
    parser.add_argument(
        "--start-x",
        type=float,
        default=50.0,
        help="Starting X position (default: 50.0 percent or pixels if --absolute)",
    )
    parser.add_argument(
        "--start-y",
        type=float,
        default=100.0,
        help="Starting Y position (default: 100.0 percent or pixels if --absolute)",
    )
    parser.add_argument(
        "--end-x",
        type=float,
        default=50.0,
        help="Ending X position (default: 50.0 percent or pixels if --absolute)",
    )
    parser.add_argument(
        "--end-y",
        type=float,
        default=0.0,
        help="Ending Y position (default: 0.0 percent or pixels if --absolute)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the output file after processing",
    )
    return parser.parse_args()


def open_file(filepath):
    if platform.system() == "Darwin":  # macOS
        subprocess.call(("open", filepath))
    elif platform.system() == "Windows":  # Windows
        os.startfile(filepath)
    else:  # Linux variants
        subprocess.call(("xdg-open", filepath))


def make_mask_creator(
    clip_height,
    clip_width,
    start_x,
    start_y,
    end_x,
    end_y,
    line_thickness,
    draw_duration,
    start_time,
    use_absolute_coords,
):
    # Convert percentage positions to pixel coordinates if not using absolute coordinates
    if not use_absolute_coords:
        start_x = int((start_x / 100.0) * clip_width)
        start_y = int((start_y / 100.0) * clip_height)
        end_x = int((end_x / 100.0) * clip_width)
        end_y = int((end_y / 100.0) * clip_height)
    else:
        start_x = int(start_x)
        start_y = int(start_y)
        end_x = int(end_x)
        end_y = int(end_y)

    def create_mask(t):
        # Create a grayscale mask frame
        mask = np.zeros((clip_height, clip_width), dtype="float32")

        # Only start drawing after start_time
        if t < start_time:
            return mask

        # Adjust time to account for delay
        adjusted_t = t - start_time

        if adjusted_t < draw_duration:
            # Calculate the current progress (0 to 1)
            progress = adjusted_t / draw_duration

            # Calculate current endpoint using linear interpolation
            current_x = int(start_x + (end_x - start_x) * progress)
            current_y = int(start_y + (end_y - start_y) * progress)

            # Draw line from start point to current point
            x_coords = np.linspace(start_x, current_x, num=1000)
            y_coords = np.linspace(start_y, current_y, num=1000)

            for x, y in zip(x_coords, y_coords):
                x, y = int(x), int(y)
                if 0 <= x < clip_width and 0 <= y < clip_height:
                    mask[
                        max(0, y - line_thickness // 2) : min(
                            clip_height, y + line_thickness // 2
                        ),
                        max(0, x - line_thickness // 2) : min(
                            clip_width, x + line_thickness // 2
                        ),
                    ] = 1.0
        else:
            # Draw complete line
            x_coords = np.linspace(start_x, end_x, num=1000)
            y_coords = np.linspace(start_y, end_y, num=1000)

            for x, y in zip(x_coords, y_coords):
                x, y = int(x), int(y)
                if 0 <= x < clip_width and 0 <= y < clip_height:
                    mask[
                        max(0, y - line_thickness // 2) : min(
                            clip_height, y + line_thickness // 2
                        ),
                        max(0, x - line_thickness // 2) : min(
                            clip_width, x + line_thickness // 2
                        ),
                    ] = 1.0

        return mask

    return create_mask


def draw_line(
    video_file,
    output_file,
    line_color="#FF0000",
    line_thickness=5,
    draw_duration=2.0,
    start_time=10.0,
    start_x=50.0,
    start_y=100.0,
    end_x=50.0,
    end_y=0.0,
    use_absolute_coords=False,
):
    logging.info(f"Processing video: {video_file}")
    logging.info(f"Line color: {line_color}")
    logging.info(f"Line thickness: {line_thickness}")
    logging.info(f"Draw duration: {draw_duration} seconds")
    logging.info(f"Start time: {start_time} seconds")
    coord_type = "pixels" if use_absolute_coords else "percent"
    logging.info(f"Using {coord_type} coordinates")
    logging.info(f"Line start position: ({start_x}, {start_y}) {coord_type}")
    logging.info(f"Line end position: ({end_x}, {end_y}) {coord_type}")

    # Load the video clip
    clip = VideoFileClip(video_file)
    clip_width, clip_height = clip.size

    # Convert hex to RGB
    np_color = [int(line_color[i : i + 2], 16) for i in (1, 3, 5)]

    # Create a solid color clip for the line
    line_clip = ColorClip(size=(clip_width, clip_height), color=np_color)
    line_clip = line_clip.set_duration(clip.duration)

    # Create the mask
    create_mask = make_mask_creator(
        clip_height,
        clip_width,
        start_x,
        start_y,
        end_x,
        end_y,
        line_thickness,
        draw_duration,
        start_time,
        use_absolute_coords,
    )
    mask_clip = VideoClip(make_frame=create_mask, duration=clip.duration, ismask=True)

    # Apply the mask to the color clip
    line_clip = line_clip.set_mask(mask_clip)

    # Composite the clips
    video_with_line = CompositeVideoClip([clip, line_clip])

    logging.info(f"Writing output to: {output_file}")
    video_with_line.write_videofile(output_file, codec="libx264", fps=clip.fps)

    logging.info(f"Video saved with an animated line: {output_file}")
    return output_file


def main(args):
    logging.debug(f"Debug mode: {args.verbose >= 2}")
    output_file = draw_line(
        args.input,
        args.output,
        args.color,
        args.thickness,
        args.draw_duration,
        args.start_time,
        args.start_x,
        args.start_y,
        args.end_x,
        args.end_y,
        args.absolute,
    )

    if args.open:
        logging.info("Opening output file...")
        open_file(output_file)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
