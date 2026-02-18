# 🎥 Media Shrinker (GUI & CLI)

A tool to shrink videos (MP4) and images (JPG, PNG) to under **9.5 MB**, preserving quality as much as possible.

## Features

- **Videos (MP4):** Uses FFmpeg to intelligently shrink video size using HEVC, reducing FPS/audio bitrate before resorting to resolution downscaling.
- **Images (JPG/PNG):** Uses Pillow to optimize JPEG quality and resize if necessary. Handles transparency by compositing onto a white background.
- **GUI:** User-friendly interface to select multiple files and track progress.
- **CLI:** Command-line interface for scripting and automation.

---

## Requirements

- Python 3.8+
- FFmpeg (must be in PATH)

## Installation

1.  **Install Python** from [python.org](https://www.python.org/downloads/). Ensure you check "Add Python to PATH".
2.  **Install FFmpeg** (Required for video shrinking):
    - Windows: Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), extract, and add `bin` folder to your PATH.
    - macOS: `brew install ffmpeg`
    - Linux: `sudo apt install ffmpeg`
3.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

---

## Usage

### GUI (Recommended)

Run the graphical interface:

```bash
python gui.py
```

1.  Click **Select Files** to choose MP4 videos or JPG/PNG images.
2.  Click **Start Shrinking**.
3.  Processed files will be saved in an `output` folder in the same directory as the source file.

### CLI (Command Line)

To shrink a single video:

```bash
python shrink.py input_video.mp4
```

To shrink recursively (Linux/WSL/Git Bash):

```bash
./shrink_all.sh
```

---

## How it Works

### Videos
1.  Prefer **H.265/HEVC** for better compression.
2.  Reduce **FPS** if needed.
3.  Reduce **Audio Bitrate**.
4.  Reduce **Resolution** only as a last resort.

### Images
1.  Convert PNG/transparent images to JPG (white background).
2.  Reduce JPEG **Quality** (down to 50%).
3.  **Resize** dimensions iteratively if quality reduction isn't enough.

---

## Troubleshooting

- **"ffmpeg not recognized"**: Ensure FFmpeg `bin` folder is in your system PATH.
- **"ModuleNotFoundError: No module named 'PIL'"**: Run `pip install -r requirements.txt`.
