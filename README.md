# 🎥 shrink.py

**Automatically shrink any video to ≤ 9.5MB on Windows**

---

## 📌 What This Program Does

`shrink.py` compresses any video file so that the final output is **9.5MB or smaller**.

It does this by:

* Calculating the correct bitrate based on video duration
* Using **2-pass H.264 encoding** for accurate file size targeting
* Automatically lowering resolution if needed
* Keeping audio intact (configurable bitrate)
* Ensuring the final file fits under the 9.5MB limit

This is useful for:

* Discord upload limits
* Email attachment limits
* LMS submissions
* Forms that require <10MB files

---

# 🖥️ System Requirements

* Windows 10 or 11
* Python 3.8+
* FFmpeg (must be installed and added to PATH)

---

# 🔧 Installation Instructions (Step-By-Step)

---

## ✅ Step 1 — Install Python

1. Go to:

   ```
   https://www.python.org/downloads/
   ```
2. Download the latest Python version.
3. **IMPORTANT:** During installation:

   * ✅ Check **“Add Python to PATH”**
4. Finish installation.

Verify it worked:

Open Command Prompt and run:

```bash
python --version
```

You should see something like:

```
Python 3.12.1
```

---

## ✅ Step 2 — Install FFmpeg (Required)

This script depends on FFmpeg to encode video.

### 1️⃣ Download FFmpeg

Go to:

```
https://www.gyan.dev/ffmpeg/builds/
```

Download:

> **ffmpeg-release-essentials.zip**

---

### 2️⃣ Extract FFmpeg

1. Extract the ZIP file.
2. Move the extracted folder somewhere permanent, for example:

```
C:\ffmpeg
```

Inside that folder you should see:

```
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

---

### 3️⃣ Add FFmpeg to PATH

1. Press **Windows Key**

2. Search for:

   ```
   Environment Variables
   ```

3. Click:

   > Edit the system environment variables

4. Click:

   > Environment Variables

5. Under **System variables**, select:

   ```
   Path
   ```

6. Click **Edit**

7. Click **New**

8. Add:

   ```
   C:\ffmpeg\bin
   ```

9. Click OK on everything.

---

### 4️⃣ Verify FFmpeg Works

Open a **new Command Prompt** and run:

```bash
ffmpeg -version
```

If installed correctly, it will print FFmpeg version info.

If it says “not recognized”, restart your computer and try again.

---

# 📂 Installing shrink.py

1. Create a folder anywhere (example):

   ```
   C:\VideoShrinker
   ```

2. Save the file as:

   ```
   shrink.py
   ```

   inside that folder.

---

# ▶️ How To Run The Program

Open Command Prompt.

Navigate to the folder:

```bash
cd C:\VideoShrinker
```

Run:

```bash
python shrink.py yourvideo.mp4
```

---

# 📤 Output

The script creates:

```
yourvideo_shrunk.mp4
```

in the same directory.

It guarantees:

```
≤ 9.5MB
```

---

# ⚙️ Optional Arguments

### Specify Output Name

```bash
python shrink.py input.mp4 -o output.mp4
```

---

### Lower Audio Bitrate (For Very Long Videos)

If the video is long and won’t fit:

```bash
python shrink.py input.mp4 --audio-kbps 64
```

Lower audio bitrate = more room for video quality.

---

# 🧠 How It Works (Technical Explanation)

The script:

1. Uses `ffprobe` to detect video duration.
2. Calculates the exact total bitrate required to hit 9.5MB.
3. Reserves part of bitrate for audio.
4. Uses **2-pass x264 encoding** for accurate size targeting.
5. If file is still too large:

   * Automatically downscales resolution (1280 → 960 → 854 → 640).
6. Stops once file is under 9.5MB.

---

# 📊 Quality Expectations

| Video Length | Expected Quality            |
| ------------ | --------------------------- |
| 15–30 sec    | Very good                   |
| 1 min        | Good                        |
| 2–3 min      | Moderate                    |
| 5+ min       | Low (size limit too strict) |

File size is controlled by bitrate.
Longer videos must sacrifice quality to stay under 9.5MB.

---

# ❗ Troubleshooting

---

### ❌ “ffmpeg not recognized”

Fix:

* Make sure `C:\ffmpeg\bin` is in PATH
* Restart Command Prompt
* Restart computer if needed

---

### ❌ Output still larger than 9.5MB

Try:

```bash
python shrink.py input.mp4 --audio-kbps 64
```

Or trim the video shorter.

---

### ❌ Very blurry output

That means the video is too long for 9.5MB.

Remember:

> File size depends on duration × bitrate.

---

# 🔒 Safety Notes

* This script **does not modify your original file**.
* It creates a new compressed copy.
* Works with most common formats:

  * .mp4
  * .mov
  * .avi
  * .mkv
  * etc.

---

# 📁 Example Folder Layout

```
C:\VideoShrinker
│
├── shrink.py
├── input.mp4
└── input_shrunk.mp4
```

---

# 🎯 Example Full Usage

```bash
cd C:\VideoShrinker
python shrink.py presentation.mov -o submission.mp4 --audio-kbps 64
```

---

# 🚀 Done

You now have a Windows-compatible video compressor that:

* Automatically calculates bitrate
* Uses professional 2-pass encoding
* Ensures file size ≤ 9.5MB
* Works from Command Prompt

---