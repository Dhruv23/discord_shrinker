import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

TARGET_MB = 9.5
TARGET_BYTES = int(TARGET_MB * 1024 * 1024)
SAFETY_FACTOR = 0.95

# New strategy: preserve res, reduce fps/audio first; res is final fallback
NEW_ATTEMPTS_PRE_SCALE = [
    # (codec, preset, fps, audio_kbps)
    ("libx265", "medium", None, 96),
    ("libx265", "medium", 30,   96),
    ("libx265", "medium", 30,   64),
    ("libx265", "medium", 24,   64),
]

# Resolution fallback (used by new strategy only if needed)
DOWNSCALE_WIDTHS = [1280, 960, 854, 640]

# Legacy strategy fallback (old behavior): start with no scale, then downscale
LEGACY_DOWNSCALE_STEPS = [None, 1280, 960, 854, 640]


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return p


def ffmpeg_exists():
    return shutil.which("ffmpeg") and shutil.which("ffprobe")


def get_duration_seconds(infile: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(infile)
    ]
    return float(run(cmd).stdout.strip())


def build_vf(scale_width=None, fps=None):
    filters = []
    if fps is not None:
        filters.append(f"fps={fps}")
    if scale_width is not None:
        # Keep aspect ratio; -2 forces even height
        filters.append(f"scale={scale_width}:-2")
    return ",".join(filters) if filters else None


def cleanup_pass_files_everywhere(folder: Path):
    # Clean up any ffmpeg 2-pass artifacts that might remain
    for pat in ("*.log*", "*.mbtree", "*.passlog*"):
        for f in folder.glob(pat):
            try:
                f.unlink()
            except Exception:
                pass


def cleanup_passlog_set(passlog_base: str):
    """
    Remove files created by -passlogfile.
    ffmpeg may create multiple files with suffixes, e.g.:
      <passlog>-0.log
      <passlog>-0.log.mbtree
    We remove everything that starts with the base name.
    """
    base = Path(passlog_base).name
    folder = Path(passlog_base).parent
    for f in folder.glob(base + "*"):
        try:
            f.unlink()
        except Exception:
            pass


def compute_target_kbps(duration_s: float, audio_kbps: int) -> tuple[int, int]:
    """Return (video_kbps, audio_kbps) for target size."""
    total_bits = TARGET_BYTES * 8 * SAFETY_FACTOR
    total_bps = total_bits / max(duration_s, 0.1)

    audio_bps = audio_kbps * 1000
    # Avoid absurdly low video bitrate; if too long, quality will degrade regardless.
    video_bps = max(int(total_bps - audio_bps), 80_000)

    return int(video_bps / 1000), int(audio_kbps)


def encode_2pass(
    infile: Path,
    outfile: Path,
    duration_s: float,
    codec: str,
    preset: str,
    audio_kbps: int,
    fps=None,
    scale_width=None,
    legacy_rate_control: bool = False,
    threads: int = 4,
) -> str:
    """
    2-pass encode to target size.
    If legacy_rate_control=True, adds maxrate/bufsize (old script style).
    Returns passlog base path.
    """
    v_k, a_k = compute_target_kbps(duration_s, audio_kbps)
    passlog = str(outfile) + ".passlog"
    vf = build_vf(scale_width=scale_width, fps=fps)

    # Windows null sink for pass 1
    null_sink = "NUL" if os.name == "nt" else "/dev/null"

    # PASS 1
    cmd1 = ["ffmpeg", "-y", "-i", str(infile)]
    if vf:
        cmd1 += ["-vf", vf]

    cmd1 += [
        "-c:v", codec,
        "-preset", preset,
        "-b:v", f"{v_k}k",
        "-threads", str(threads),
    ]

    if legacy_rate_control:
        cmd1 += ["-maxrate", f"{int(v_k * 1.2)}k", "-bufsize", f"{int(v_k * 2)}k"]

    cmd1 += [
        "-pass", "1",
        "-passlogfile", passlog,
        "-an",
        "-f", "mp4",
        null_sink,  # output MUST be last
    ]
    run(cmd1)

    # PASS 2
    cmd2 = ["ffmpeg", "-y", "-i", str(infile)]
    if vf:
        cmd2 += ["-vf", vf]

    cmd2 += [
        "-c:v", codec,
        "-preset", preset,
        "-b:v", f"{v_k}k",
        "-threads", str(threads),
    ]

    if legacy_rate_control:
        cmd2 += ["-maxrate", f"{int(v_k * 1.2)}k", "-bufsize", f"{int(v_k * 2)}k"]

    cmd2 += [
        "-pass", "2",
        "-passlogfile", passlog,
        "-c:a", "aac",
        "-b:a", f"{a_k}k",
        "-movflags", "+faststart",
    ]

    # HEVC tag in MP4 for compatibility (helps some Apple/QuickTime players)
    if codec == "libx265":
        cmd2 += ["-tag:v", "hvc1"]

    cmd2 += [str(outfile)]  # output MUST be last
    run(cmd2)

    return passlog


def attempt_encode(
    infile: Path,
    outfile: Path,
    duration_s: float,
    codec: str,
    preset: str,
    audio_kbps: int,
    fps=None,
    scale_width=None,
    legacy_rate_control: bool = False,
    threads: int = 4,
) -> Path | None:
    tmp_out = outfile.with_name(
        outfile.stem
        + f"__{codec}_fps{fps or 'src'}_a{audio_kbps}"
        + (f"_w{scale_width}" if scale_width else "")
        + ".mp4"
    )

    passlog = None
    try:
        passlog = encode_2pass(
            infile=infile,
            outfile=tmp_out,
            duration_s=duration_s,
            codec=codec,
            preset=preset,
            audio_kbps=audio_kbps,
            fps=fps,
            scale_width=scale_width,
            legacy_rate_control=legacy_rate_control,
            threads=threads,
        )
    finally:
        if passlog:
            cleanup_passlog_set(passlog)

    if not tmp_out.exists():
        return None

    if tmp_out.stat().st_size <= TARGET_BYTES:
        return tmp_out

    return None


def new_strategy(infile: Path, outfile: Path, duration_s: float, threads: int = 4) -> Path | None:
    # Try HEVC + fps/audio tweaks without scaling first
    for codec, preset, fps, audio_kbps in NEW_ATTEMPTS_PRE_SCALE:
        try:
            out = attempt_encode(
                infile, outfile, duration_s,
                codec, preset, audio_kbps,
                fps=fps, scale_width=None,
                legacy_rate_control=False,
                threads=threads,
            )
            if out:
                return out
        except RuntimeError:
            # If x265 fails on user's ffmpeg build, continue; legacy fallback likely succeeds with x264.
            continue

    # Final fallback in "new strategy": scale, but keep the better efficiency settings
    codec, preset, fps, audio_kbps = ("libx265", "medium", 30, 64)
    for w in DOWNSCALE_WIDTHS:
        try:
            out = attempt_encode(
                infile, outfile, duration_s,
                codec, preset, audio_kbps,
                fps=fps, scale_width=w,
                legacy_rate_control=False,
                threads=threads,
            )
            if out:
                return out
        except RuntimeError:
            continue

    return None


def legacy_strategy(infile: Path, outfile: Path, duration_s: float, threads: int = 4) -> Path | None:
    # Old behavior: H.264 2-pass + scale steps; include maxrate/bufsize like the old script
    codec, preset, audio_kbps = ("libx264", "medium", 96)

    for w in LEGACY_DOWNSCALE_STEPS:
        try:
            out = attempt_encode(
                infile, outfile, duration_s,
                codec, preset, audio_kbps,
                fps=None, scale_width=w,
                legacy_rate_control=True,
                threads=threads,
            )
            if out:
                return out
        except RuntimeError:
            continue

    return None


def process_video(input_path: str, output_path: str = None, threads: int = 4) -> str:
    """
    Main logic to process a single video file.
    Returns the path to the successful output file.
    Raises RuntimeError or FileNotFoundError on failure.
    """
    infile = Path(input_path).resolve()
    if not infile.exists():
        raise FileNotFoundError(f"Input not found: {infile}")

    if not ffmpeg_exists():
        raise RuntimeError("ffmpeg/ffprobe not found. Install FFmpeg and add it to PATH.")

    outfile = Path(output_path).resolve() if output_path else infile.with_name(infile.stem + "_shrunk.mp4")
    workdir = outfile.parent

    # Ensure workdir exists (if output_path was provided in a non-existent dir)
    workdir.mkdir(parents=True, exist_ok=True)

    duration_s = get_duration_seconds(infile)
    print(f"Duration: {duration_s:.2f}s | Target: <= {TARGET_MB} MB")

    # --- Try new strategy first ---
    print("\n== Trying quality-preserving strategy (HEVC + FPS/audio before scaling) ==")
    out = new_strategy(infile, outfile, duration_s, threads=threads)

    # --- If new strategy fails, use legacy approach ---
    if out is None:
        print("\n== New strategy failed. Falling back to legacy strategy (H.264 + scaling) ==")
        out = legacy_strategy(infile, outfile, duration_s, threads=threads)

    # Cleanup temp mp4s except the winner
    for f in workdir.glob(outfile.stem + "__*.mp4"):
        if out is None or f != out:
            try:
                f.unlink()
            except Exception:
                pass

    # Nuke pass logs everywhere (covers any weird naming)
    cleanup_pass_files_everywhere(workdir)

    if out is None:
        raise RuntimeError("Could not compress under 9.5MB. Try trimming the clip shorter.")

    # Move winning temp output into final outfile name
    try:
        if outfile.exists():
            outfile.unlink()
    except Exception:
        pass

    out.replace(outfile)
    print(f"\nSuccess: {outfile} ({outfile.stat().st_size / (1024 * 1024):.2f} MB)")
    return str(outfile)


def main():
    ap = argparse.ArgumentParser(
        description="Shrink a video to <= 9.5MB with quality-preserving attempts + legacy fallback."
    )
    ap.add_argument("input", help="Input video path")
    ap.add_argument("-o", "--output", help="Output path (default: <input>_shrunk.mp4)")
    ap.add_argument("--threads", type=int, default=4, help="FFmpeg threads per encode job (default: 4)")
    args = ap.parse_args()

    try:
        process_video(args.input, args.output, args.threads)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1 if "ffmpeg" in str(e) else 2)


if __name__ == "__main__":
    main()
