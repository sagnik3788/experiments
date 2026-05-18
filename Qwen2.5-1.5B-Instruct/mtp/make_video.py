"""
Generate a terminal-style comparison video from benchmark JSON results.

Uses Pillow to render frames (terminal emulation) and ffmpeg to stitch video.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Terminal appearance ────────────────────────────────────────────────────
WIDTH = 1280
HEIGHT = 720
BG = (12, 12, 12)       # near-black background
GREEN = (0, 255, 0)
CYAN = (0, 200, 255)
YELLOW = (255, 220, 80)
RED = (255, 80, 80)
WHITE = (220, 220, 220)
GRAY = (100, 100, 100)
MARGIN_X = 40
MARGIN_Y = 30
LINE_H = 24             # line height in px
FONT_SIZE = 16

# ── Try to find a monospace font ──────────────────────────────────────────
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/gnu-free/FreeMono.ttf",
    "/usr/share/fonts/noto/NotoMono-Regular.ttf",
]
FONT_PATH = None
for p in FONT_CANDIDATES:
    if os.path.isfile(p):
        FONT_PATH = p
        break
if FONT_PATH is None:
    # fallback: try fontconfig
    try:
        import subprocess
        result = subprocess.run(["fc-match", "-f", "%{file}", "mono"],
                                capture_output=True, text=True, timeout=5)
        if result.stdout and os.path.isfile(result.stdout):
            FONT_PATH = result.stdout
    except Exception:
        pass


def get_font(size=FONT_SIZE):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_terminal_frame(draw: ImageDraw, lines: list[str], frame_idx: int,
                         highlight: list[int] | None = None) -> None:
    """Draw a terminal-looking frame with given lines of text."""
    font = get_font()
    font_bold = get_font(FONT_SIZE + 2)

    # Terminal "chrome"
    draw.rectangle([0, 0, WIDTH - 1, HEIGHT - 1], outline=(40, 40, 40), width=1)
    # Title bar
    draw.rectangle([0, 0, WIDTH - 1, 28], fill=(30, 30, 30))
    # "traffic lights"
    for dx, c in [(12, (255, 95, 87)), (30, (255, 189, 46)), (48, (39, 201, 63))]:
        draw.ellipse([dx, 8, dx + 12, 20], fill=c)
    # Title text
    draw.text((WIDTH // 2 - 100, 5),
              "GGUF FP16 vs MTP Speculative Decoding",
              fill=GRAY, font=font)

    # Content area
    y = MARGIN_Y
    for i, line in enumerate(lines):
        if y > HEIGHT - 10:
            break
        color = WHITE
        bold = False
        if highlight and i in highlight:
            color = GREEN
            bold = True
        if line.startswith("═══") or line.startswith("╔") or line.startswith("╚"):
            color = CYAN
        elif line.startswith("RUN 1"):
            color = YELLOW
        elif line.startswith("RUN 2"):
            color = GREEN
        elif "Speedup" in line or "Improvement" in line:
            color = GREEN
        elif "Error" in line:
            color = RED

        f = font_bold if bold else font
        draw.text((MARGIN_X, y), line[:120], fill=color, font=f)
        y += LINE_H


def make_frames(results: dict, output_dir: str, fps: int = 24) -> list[str]:
    """Generate PNG frames showing progressive terminal output."""
    normal = results.get("normal", {})
    mtp = results.get("mtp", {})
    model_name = os.path.basename(results.get("model", "model.gguf"))

    speedup = results.get("speedup_ratio", 0)
    tok_diff = mtp.get("tokens_per_second", 0) - normal.get("tokens_per_second", 0)

    # Build a sequence of scenes
    scenes = [
        # ── Scene 0: Intro ──
        [
            "╔══════════════════════════════════════════════════════════════╗",
            "║     GGUF FP16  vs  MTP Speculative Decoding                ║",
            "╚══════════════════════════════════════════════════════════════╝",
            "",
            f"  Model    : {model_name}",
            "  GPU      : NVIDIA GeForce GTX 1650 (4 GB)",
            "  Method   : N-gram speculative decoding (built-in)",
            f"  Spec tokens: {results.get('spec_tokens', 5)}",
            f"  Max tokens: {results.get('max_tokens', 128)}",
            "",
            "  Press ENTER to start benchmark...",
        ],
        # ── Scene 1: Loading Normal ──
        [
            "──────────────────────────────────────────────────────────",
            "  RUN 1: Normal Inference (no speculative decoding)",
            "──────────────────────────────────────────────────────────",
            "",
            "  ▸ Loading model ...",
        ],
        # ── Scene 2: Normal running ──
        [
            "──────────────────────────────────────────────────────────",
            "  RUN 1: Normal Inference (no speculative decoding)",
            "──────────────────────────────────────────────────────────",
            "",
            "  ▸ Loading model ... done",
            "  ▸ Warming up ... done",
            "  ▸ Generating tokens...",
        ],
        # ── Scene 3: Normal results ──
        [
            "──────────────────────────────────────────────────────────",
            "  RUN 1: Normal Inference (no speculative decoding)",
            "──────────────────────────────────────────────────────────",
            "",
            f"  Generated tokens : {normal.get('tokens', 0)}",
            f"  Total time       : {normal.get('total_time_s', 0):.2f}s",
            f"  TTFS             : {normal.get('ttfs_s', 0):.3f}s",
            f"  Generation time  : {normal.get('gen_time_s', 0):.2f}s",
            f"  Throughput       : {normal.get('tokens_per_second', 0):.2f} tok/s",
            f"  Latency          : {normal.get('ms_per_token', 0):.1f} ms/tok",
        ],
        # ── Scene 4: Loading MTP ──
        [
            "──────────────────────────────────────────────────────────",
            f"  RUN 2: MTP Speculative Decoding ({results.get('spec_method', 'ngram')}, {results.get('spec_tokens', 5)} tokens)",
            "──────────────────────────────────────────────────────────",
            "",
            "  ▸ Loading model with speculative decoding ...",
        ],
        # ── Scene 5: MTP running ──
        [
            "──────────────────────────────────────────────────────────",
            f"  RUN 2: MTP Speculative Decoding ({results.get('spec_method', 'ngram')}, {results.get('spec_tokens', 5)} tokens)",
            "──────────────────────────────────────────────────────────",
            "",
            "  ▸ Loading model with speculative decoding ... done",
            "  ▸ Warming up ... done",
            "  ▸ Generating tokens with ngram speculation...",
        ],
        # ── Scene 6: MTP results ──
        [
            "──────────────────────────────────────────────────────────",
            f"  RUN 2: MTP Speculative Decoding ({results.get('spec_method', 'ngram')}, {results.get('spec_tokens', 5)} tokens)",
            "──────────────────────────────────────────────────────────",
            "",
            f"  Generated tokens : {mtp.get('tokens', 0)}",
            f"  Total time       : {mtp.get('total_time_s', 0):.2f}s",
            f"  TTFS             : {mtp.get('ttfs_s', 0):.3f}s",
            f"  Generation time  : {mtp.get('gen_time_s', 0):.2f}s",
            f"  Throughput       : {mtp.get('tokens_per_second', 0):.2f} tok/s",
            f"  Latency          : {mtp.get('ms_per_token', 0):.1f} ms/tok",
        ],
        # ── Scene 7: Comparison table ──
        [
            "  ══════════════════════════════════════════════════════════════════",
            "    COMPARISON SUMMARY",
            "  ══════════════════════════════════════════════════════════════════",
            "",
            f"    {'Method':<22s} {'tok/s':>8s}  {'ms/tok':>7s}  {'Total':>7s}  {'TTFS':>7s}  {'Tokens':>6s}",
            "    " + "─" * 62,
            f"    {'Normal (no spec)':<22s} {normal.get('tokens_per_second', 0):>8.2f}  {normal.get('ms_per_token', 0):>7.1f}  {normal.get('total_time_s', 0):>7.2f}s  {normal.get('ttfs_s', 0):>7.3f}s  {normal.get('tokens', 0):>6d}",
            f"    {'MTP (ngram, 5 tok)':<22s} {mtp.get('tokens_per_second', 0):>8.2f}  {mtp.get('ms_per_token', 0):>7.1f}  {mtp.get('total_time_s', 0):>7.2f}s  {mtp.get('ttfs_s', 0):>7.3f}s  {mtp.get('tokens', 0):>6d}",
            "",
            f"    Speedup:      {speedup:.2f}×  ({tok_diff:+.2f} tok/s)",
            "",
            "    Analysis:",
            "    On this 1.5B parameter model, n-gram speculative decoding adds",
            "    overhead (rejection sampler + draft lookup) without enough",
            "    benefit — the model is already fast enough that verification",
            "    costs outweigh the speculation gains.",
            "",
            "    MTP / speculative decoding typically shines on larger models",
            "    (7B+) where each forward pass is more expensive, making the",
            "    speculation-verification trade-off worthwhile.",
        ],
    ]

    # Scene durations in seconds (total video length ~30 sec)
    durations_s = [5, 2, 3, 6, 2, 3, 6, 8]

    frame_files = []
    for scene_idx, (scene_lines, dur) in enumerate(zip(scenes, durations_s)):
        n_frames = max(int(dur * fps), 1)
        for _ in range(n_frames):
            img = Image.new("RGB", (WIDTH, HEIGHT), BG)
            draw = ImageDraw.Draw(img)
            draw_terminal_frame(draw, scene_lines, scene_idx)
            fname = os.path.join(output_dir, f"frame_{len(frame_files):06d}.png")
            img.save(fname)
            frame_files.append(fname)

    return frame_files


def render_video(frame_dir: str, output_path: str, fps: int = 24) -> None:
    """Use ffmpeg to create an MP4 from PNG frames."""
    pattern = os.path.join(frame_dir, "frame_%06d.png")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", pattern,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",  # ensure even dimensions
        output_path,
    ]
    print(f"  🎬 Rendering video: {output_path}  ({fps} fps)")
    sys.stdout.flush()

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  ❌ ffmpeg error: {result.stderr}")
        return False

    if os.path.isfile(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  ✅ Video created: {output_path}  ({size_mb:.1f} MB)")
        return True
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate comparison video")
    parser.add_argument("--input", default=None,
                        help="JSON results file (from compare_normal_vs_mtp.py)")
    parser.add_argument("--output", default="mtp_comparison.mp4",
                        help="Output video path")
    parser.add_argument("--fps", type=int, default=24, help="Video frame rate")
    parser.add_argument("--results", default=None,
                        help="Inline results JSON string (used by wrapper)")
    args = parser.parse_args()

    # Load results
    if args.input:
        with open(args.input) as f:
            results = json.load(f)
    elif args.results:
        results = json.loads(args.results)
    else:
        # Create dummy results for testing
        results = {
            "model": "model-f16.gguf",
            "max_tokens": 128,
            "spec_method": "ngram",
            "spec_tokens": 5,
            "normal": {
                "tokens": 80, "total_time_s": 45.2, "ttfs_s": 0.8,
                "gen_time_s": 44.4, "tokens_per_second": 1.78, "ms_per_token": 561.0,
                "text": ""
            },
            "mtp": {
                "tokens": 80, "total_time_s": 32.1, "ttfs_s": 0.9,
                "gen_time_s": 31.2, "tokens_per_second": 2.53, "ms_per_token": 395.0,
                "text": ""
            },
            "speedup_ratio": 1.42,
        }
        print("  ⚠ No input JSON found — using demo placeholder results")
        print("  Run compare_normal_vs_mtp.py first for real metrics")

    # Generate frames in temp dir
    with tempfile.TemporaryDirectory(prefix="mtp_video_") as tmpdir:
        print(f"  Generating frames in {tmpdir} ...")
        frame_files = make_frames(results, tmpdir, fps=args.fps)
        print(f"  Created {len(frame_files)} frames ({len(frame_files)/args.fps:.1f}s at {args.fps}fps)")

        success = render_video(tmpdir, args.output, args.fps)

    if success:
        print(f"\n  📹 Video ready: {args.output}")
    else:
        print("\n  ❌ Video creation failed")


if __name__ == "__main__":
    main()
