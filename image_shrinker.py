import shutil
from pathlib import Path
from PIL import Image

TARGET_MB = 9.5
TARGET_BYTES = int(TARGET_MB * 1024 * 1024)

def shrink_image(file_path: str, output_dir: str) -> str:
    """
    Shrinks an image file to be under 9.5MB.
    - If already smaller, copies it.
    - If larger, converts to JPG and reduces quality.
    - If still larger, resizes dimensions.
    Returns the path to the output file.
    """
    input_path = Path(file_path).resolve()
    output_dir_path = Path(output_dir).resolve()
    output_dir_path.mkdir(parents=True, exist_ok=True)

    input_size = input_path.stat().st_size

    # Case 1: Already small enough
    if input_size <= TARGET_BYTES:
        output_path = output_dir_path / input_path.name

        if output_path.exists():
            # shutil.copy2 will overwrite
            pass

        shutil.copy2(input_path, output_path)
        return str(output_path)

    # Case 2: Needs shrinking
    # We will force output to be JPG to save space/allow compression
    output_path = output_dir_path / (input_path.stem + ".jpg")

    try:
        with Image.open(input_path) as img:
            # Handle transparency replacement with white background
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img = img.convert("RGBA")
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3]) # 3 is alpha channel in RGBA
                img = background
            else:
                img = img.convert("RGB")

            # Strategy A: Reduce Quality first (without resizing)
            # Loop quality from 95 down to 50
            for quality in range(95, 45, -5):
                img.save(output_path, "JPEG", quality=quality, optimize=True)
                if output_path.stat().st_size <= TARGET_BYTES:
                    return str(output_path)

            # Strategy B: Resize + Quality 85
            # If we are here, quality 50 didn't work.
            # Start resizing.

            scale = 0.9
            while True:
                new_w = int(img.width * scale)
                new_h = int(img.height * scale)

                # Safety break
                if new_w < 100 or new_h < 100:
                    raise RuntimeError("Cannot shrink image under 9.5MB without making it too small.")

                resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                resized_img.save(output_path, "JPEG", quality=85, optimize=True)

                if output_path.stat().st_size <= TARGET_BYTES:
                    return str(output_path)

                scale *= 0.9 # Reduce size by another ~10% relative to original

    except Exception as e:
        # Cleanup partial file on error
        if output_path.exists():
             try:
                output_path.unlink()
             except:
                pass
        raise e
