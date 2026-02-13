## Updated README (for the new “don’t drop resolution first” behavior) + batch Bash script

Below are two things:

1. An updated `README.md` you can paste into your repo
2. A `shrink_all.sh` script that **recursively finds videos that are NOT already shrunk** and runs `shrink.py` on all of them **in the background**

---

# README.md

````md
# 🎥 shrink.py — Shrink videos to ≤ 9.5 MB (Windows-friendly)

This tool re-encodes videos to fit under **9.5 MB**, while trying to preserve visual quality and resolution as much as possible.

## What it does

Given an input video, `shrink.py` will:

1. Prefer **H.265/HEVC (libx265)** for better quality-per-byte than H.264.
2. If the file is still too large, it will **reduce FPS before reducing resolution**.
3. If still too large, it will **lower audio bitrate**.
4. **Only as a final fallback**, it will reduce resolution.

It produces an output file under **9.5 MB**, and cleans up temporary/intermediate files and ffmpeg 2-pass log files.

---

## Requirements

- Windows 10/11
- Python 3.8+
- FFmpeg installed and available in PATH (must include `ffmpeg` and `ffprobe`)

---

## Install prerequisites

### 1) Install Python
1. Download from:
   https://www.python.org/downloads/
2. During install, check:
   ✅ **Add Python to PATH**
3. Verify in Command Prompt:
   ```bash
   python --version
````

### 2) Install FFmpeg (Required)

1. Download FFmpeg builds (Windows):
   [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)

   * Download: **ffmpeg-release-essentials.zip**
2. Extract it somewhere permanent, e.g.:
   `C:\ffmpeg`
3. Add FFmpeg `bin` to PATH:
   `C:\ffmpeg\bin`

Verify in a NEW Command Prompt:

```bash
ffmpeg -version
ffprobe -version
```

---

## Running shrink.py

From the folder containing `shrink.py`:

```bash
python shrink.py input_video.mp4
```

Output will be created in the same folder:

* `input_video_shrunk.mp4`

### Optional: choose output name

```bash
python shrink.py input_video.mp4 -o output.mp4
```

---

## Notes on quality

A 9.5 MB limit is strict. What’s possible depends mostly on **duration**.

To preserve resolution, the script tries:

* HEVC first (more efficient than H.264)
* FPS reduction (less noticeable than downscaling)
* Audio reduction
* Resolution reduction as last resort

If your clip is very long (e.g. several minutes), you may still need to trim it for good quality.

---

## Batch shrinking (recursive) with shrink_all.sh

This repo includes `shrink_all.sh`, which:

* Recursively searches the current folder and subfolders for video files
* Skips any file that already ends with `_shrunk.<ext>`
* Runs `shrink.py` on each remaining video
* Runs jobs **in the background** and writes logs to `shrink_logs/`

### Supported environments

Because `.sh` scripts are Unix shell scripts, run it using one of:

* **WSL (Windows Subsystem for Linux)**
* **Git Bash** (installed with Git for Windows)

### How to run it (WSL or Git Bash)

1. Make it executable (WSL / Git Bash):

```bash
chmod +x shrink_all.sh
```

2. Run it from your project folder:

```bash
./shrink_all.sh
```

It will start background jobs immediately and return you to the prompt.

### Logs

It creates:

* `shrink_logs/`
* One log file per input video, plus a `pids.txt` file

To check progress:

```bash
tail -f shrink_logs/*.log
```

To list running jobs (WSL):

```bash
ps aux | grep shrink.py
```

---

## Troubleshooting

### “ffmpeg not recognized”

FFmpeg isn’t in PATH. Add `C:\ffmpeg\bin` to PATH and reopen your terminal.

### Still looks bad

The clip may be too long to look good under 9.5 MB. Consider trimming, or accept the final fallback (resolution downscale).




## Quick note (so it works in WSL smoothly)

If you run this in **WSL**, your Python command might be `python3` instead of `python`.
If `python` fails in WSL, change this line in `shrink_all.sh`:

```bash
( python "${PY_SCRIPT}" "$file" ) >"$log" 2>&1 &
```

to:

```bash
( python3 "${PY_SCRIPT}" "$file" ) >"$log" 2>&1 &
```

---