import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tqdm import tqdm

TARGET_MB = 9.5
TARGET_BYTES = int(TARGET_MB * 1024 * 1024)

# How much of the total bitrate budget to reserve for audio
AUDIO_KBPS = 96  # keep it reasonable; drop to 64 if you need more room for video

# Safety margin so we reliably land under the limit (container overhead, bitrate variance, etc.)
SAFETY_FACTOR = 0.95

# If first attempt doesn't fit, progressively downscale and retry
DOWNSCALE_STEPS = [
    None,        # no scaling first
    1280,        # scale width to 1280 (keep aspect)
    960,
    854,         # ~480p width for 16:9
    640,
]

def run(cmd):
    """Run a command and raise if it fails."""
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed:\n{' '.join(cmd)}\n\nSTDERR:\n{p.stderr}")
    return p

def ffmpeg_exists():
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

def get_duration_seconds(infile: Path) -> float:
    # ffprobe duration
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(infile)
    ]
    out = run(cmd).stdout.strip()
    return float(out)

def build_scale_filter(target_width):
    if target_width is None:
        return None
    # Keep aspect ratio, ensure height is even (required by many encoders)
    return f"scale={target_width}:-2"

def encode_to_target(infile: Path, outfile: Path, duration_s: float, scale_width=None):
    # Total target bits = bytes * 8
    total_bits = TARGET_BYTES * 8 * SAFETY_FACTOR

    # total bitrate (bps) = total bits / duration
    total_bps = total_bits / max(duration_s, 0.1)

    audio_bps = AUDIO_KBPS * 1000
    video_bps = max(int(total_bps - audio_bps), 50_000)  # don't go below something tiny

    # Use 2-pass for better size control
    # Convert to kbits for ffmpeg
    v_k = int(video_bps / 1000)
    a_k = int(audio_bps / 1000)

    # temp passlog in same folder
    passlog = str(outfile) + ".passlog"

    vf = build_scale_filter(scale_width)

    # Pass 1
    cmd1 = ["ffmpeg", "-y", "-i", str(infile)]
    if vf:
        cmd1 += ["-vf", vf]
    cmd1 += [
        "-c:v", "libx264",
        "-b:v", f"{v_k}k",
        "-maxrate", f"{int(v_k*1.2)}k",
        "-bufsize", f"{int(v_k*2)}k",
        "-pass", "1",
        "-passlogfile", passlog,
        "-an",
        "-f", "mp4",
        "NUL" if os.name == "nt" else "/dev/null"
    ]
    run(cmd1)

    # Pass 2
    cmd2 = ["ffmpeg", "-y", "-i", str(infile)]
    if vf:
        cmd2 += ["-vf", vf]
    cmd2 += [
        "-c:v", "libx264",
        "-b:v", f"{v_k}k",
        "-maxrate", f"{int(v_k*1.2)}k",
        "-bufsize", f"{int(v_k*2)}k",
        "-pass", "2",
        "-passlogfile", passlog,
        "-c:a", "aac",
        "-b:a", f"{a_k}k",
        "-movflags", "+faststart",
        str(outfile)
    ]
    run(cmd2)

    # Cleanup pass logs
    for ext in ["", ".mbtree", ".log", ".log.mbtree"]:
        try:
            Path(passlog + ext).unlink(missing_ok=True)
        except Exception:
            pass

def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024.0:
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} TB"

def main():
    ap = argparse.ArgumentParser(description="Shrink a video to <= 9.5MB (Windows-friendly).")
    ap.add_argument("input", help="Input video path")
    ap.add_argument("-o", "--output", help="Output path (default: input_shrunk.mp4)")
    ap.add_argument("--audio-kbps", type=int, default=AUDIO_KBPS, help="Audio bitrate kbps (default: 96)")
    args = ap.parse_args()

    global AUDIO_KBPS
    AUDIO_KBPS = args.audio_kbps

    infile = Path(args.input).resolve()
    if not infile.exists():
        print(f"Input not found: {infile}")
        sys.exit(1)

    if not ffmpeg_exists():
        print("Error: ffmpeg/ffprobe not found. Install FFmpeg and add it to PATH.")
        sys.exit(1)

    outfile = Path(args.output).resolve() if args.output else infile.with_name(infile.stem + "_shrunk.mp4")

    duration_s = get_duration_seconds(infile)
    print(f"Duration: {duration_s:.2f}s")
    print(f"Target: <= {TARGET_MB} MB")

    # Try multiple downscale steps until size fits
    for step, width in enumerate(DOWNSCALE_STEPS, start=1):
        tmp_out = outfile if width is None else outfile.with_name(outfile.stem + f"_w{width}.mp4")

        print("\n" + ("=" * 60))
        print(f"Attempt {step}: " + ("no scaling" if width is None else f"scale to width {width}px"))
        try:
            encode_to_target(infile, tmp_out, duration_s, scale_width=width)
        except RuntimeError as e:
            print(e)
            continue

        out_size = tmp_out.stat().st_size
        print(f"Output size: {human_size(out_size)}")

        if out_size <= TARGET_BYTES:
            # If we wrote to a temp named output, rename to requested output
            if tmp_out != outfile:
                tmp_out.replace(outfile)
            print(f"\n✅ Success: {outfile} ({human_size(outfile.stat().st_size)})")
            return
        else:
            print("❌ Still too large, trying next step...")

            # remove oversized temp outputs (but keep final if user explicitly named it)
            if tmp_out.exists() and tmp_out != outfile:
                try:
                    tmp_out.unlink()
                except Exception:
                    pass

    print("\nCould not get under 9.5MB with the current strategy.")
    print("Try lowering --audio-kbps (e.g. 64) or trim the video length.")
    sys.exit(2)

if __name__ == "__main__":
    main()
