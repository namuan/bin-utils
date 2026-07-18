#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "moviepy",
#   "numpy",
# ]
# ///
"""
Render amplitude-style bars waveform video from a WAV file.

Usage:
./bars_amplitude.py gen.wav gen_bars.mp4
"""
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import numpy as np
from moviepy import AudioFileClip, VideoClip


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("audio", help="Input WAV file")
    parser.add_argument("output", help="Output MP4 file")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--bars", type=int, default=64, help="Number of bars")
    parser.add_argument("--fps", type=int, default=25)
    parser.add_argument("--color", default="#00e5ff", help="Bar base color (hex)")
    parser.add_argument("--pad", type=int, default=80, help="Padding around the waves (px)")
    parser.add_argument("-v", "--verbose", action="count", default=0, dest="verbose")
    return parser.parse_args()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def smooth(alpha, n):
    # triangle-ish smoothing kernel for gentle bar blending
    k = np.concatenate([np.linspace(0.5, 1.0, n // 2), np.linspace(1.0, 0.5, n - n // 2)])
    return np.convolve(alpha, k / k.sum(), mode="same")


def make_frame(audio_clip, sr, samples, n_bars, w, h, color, pad):
    bg_top = np.array([10, 12, 24], dtype=np.float32)
    bg_bot = np.array([2, 4, 12], dtype=np.float32)
    base = np.array(color, dtype=np.float32)
    peak = np.array([180, 255, 255], dtype=np.float32)

    # precompute vertical background gradient (h, 3)
    yy = np.linspace(0, 1, h)[:, None]
    bg = bg_top * (1 - yy) + bg_bot * yy  # (h, 3)

    def frame(t):
        start = max(0, int((t - 0.03) * sr))
        end = min(len(samples), int((t + 0.03) * sr))
        chunk = samples[start:end]
        if chunk.size == 0:
            chunk = np.zeros(1)
        band = np.array_split(chunk, n_bars)
        amps = np.array([np.sqrt(np.mean(b ** 2)) if b.size else 0.0 for b in band])
        # gentle temporal smoothing across bars for a calmer look
        amps = smooth(amps, max(3, n_bars // 16))
        max_amp = max(amps.max(), 1e-6)
        amps = np.clip(amps / max_amp, 0, 1)

        img = np.repeat(bg[:, None, :], w, axis=1).astype(np.float32)

        x0_pad, x1_pad = pad, w - pad
        y0_pad, y1_pad = pad, h - pad
        inner_w = max(1, x1_pad - x0_pad)
        inner_h = max(1, y1_pad - y0_pad)

        gap = max(1, inner_w // (n_bars * 6))
        bar_w = (inner_w - gap * (n_bars - 1)) / n_bars
        radius = min(bar_w / 2, 14)

        # coordinate grids for vectorized rounded-bar masking
        xs = np.arange(w)[None, :, None]          # (1, w, 1)
        ys = np.arange(h)[:, None, None]          # (h, 1, 1)

        for i, a in enumerate(amps):
            bx0 = int(x0_pad + i * (bar_w + gap))
            bx1 = int(bx0 + bar_w)
            if bx1 <= bx0:
                continue
            bh = int(max(a, 0.02) * inner_h)
            by0 = y0_pad + (inner_h - bh) // 2
            by1 = by0 + bh
            c = base * (1 - a) + peak * a  # brighter at higher amplitude

            # masks: broadcast over (h, w)
            xmask = (xs[:, :, 0] >= bx0) & (xs[:, :, 0] < bx1)
            ymask = (ys[:, :, 0] >= by0) & (ys[:, :, 0] < by1)
            mask = xmask & ymask
            # round the top corners
            if radius > 0:
                corner_band = (ys[:, :, 0] >= by0) & (ys[:, :, 0] < by0 + radius)
                cx = (bx0 + bx1 - 1) / 2.0
                dx = np.abs(xs[:, :, 0] - cx)
                dy = (by0 + radius) - ys[:, :, 0]
                in_corner = corner_band & (dx > bar_w / 2 - radius)
                outside = dx * dx + dy * dy > radius * radius
                mask &= ~(in_corner & outside)
            img[mask] = c

        img = np.clip(img, 0, 255).astype(np.uint8)
        return img
    return frame


def main(args):
    audio = AudioFileClip(args.audio)
    sr = int(audio.fps)
    samples = audio.to_soundarray()  # (N, channels) or (N,)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    samples = np.asarray(samples, dtype=np.float32)
    if samples.max() > 1.0:
        samples = samples / 32768.0

    color = hex_to_rgb(args.color)
    frame_fn = make_frame(audio, sr, samples, args.bars, args.width, args.height, color, args.pad)

    clip = VideoClip(frame_fn, duration=audio.duration)
    clip = clip.with_audio(audio)
    clip.write_videofile(
        args.output,
        fps=args.fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
    )


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
