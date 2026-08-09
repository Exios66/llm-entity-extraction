"""Image utility helpers for document processing.

Convert TIFF/PDF pages to grayscale PNGs, encode to base64, resize with padding.
"""

from __future__ import annotations

import io
import base64
from pathlib import Path

from PIL import Image


def encode_image_base64(image_path: Path) -> str:
    """Read an image file and return its base64-encoded contents."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_image_bytes_base64(image_bytes: bytes) -> str:
    """Base64-encode raw image bytes."""
    return base64.b64encode(image_bytes).decode("utf-8")


def resize_with_padding(img: Image.Image, target_size: tuple[int, int], fill: int = 255) -> Image.Image:
    """Resize an image to target_size with aspect-ratio-preserving white padding.

    Args:
        img: PIL Image (any mode).
        target_size: (width, height) in pixels.
        fill: Background fill value (255 = white for grayscale).

    Returns:
        A new PIL Image of exactly target_size.
    """
    tw, th = target_size
    iw, ih = img.size
    scale = min(tw / iw, th / ih)
    new_w = max(int(iw * scale), 1)
    new_h = max(int(ih * scale), 1)
    resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Center the resized image on a blank canvas
    canvas = Image.new("L", (tw, th), fill)
    offset_x = (tw - new_w) // 2
    offset_y = (th - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def tiff_to_png_bytes(tiff_bytes: bytes, target_size: tuple[int, int] = (1024, 1024)) -> bytes:
    """Convert a TIFF blob to a fixed-size padded grayscale PNG.

    Args:
        tiff_bytes: Raw TIFF file contents.
        target_size: Output image dimensions (width, height).

    Returns:
        PNG-encoded bytes at 300 DPI metadata.
    """
    with Image.open(io.BytesIO(tiff_bytes)) as img:
        if img.mode != "L":
            img = img.convert("L")
        padded = resize_with_padding(img, target_size, fill=255)
        buffer = io.BytesIO()
        padded.save(buffer, format="PNG", dpi=(300, 300))
        return buffer.getvalue()


def pdf_to_png_bytes(pdf_bytes: bytes, page_num: int = 0, target_size: tuple[int, int] = (1024, 1024)) -> bytes:
    """Convert a single PDF page to a grayscale PNG.

    Args:
        pdf_bytes: Raw PDF file contents.
        page_num: Page number to convert (0-indexed).
        target_size: Output image dimensions (width, height).

    Returns:
        PNG-encoded bytes at 300 DPI metadata.
    """
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise ImportError("pdf2image is required for PDF conversion. Install with: pip install pdf2image")

    images = convert_from_bytes(pdf_bytes, first_page=page_num + 1, last_page=page_num + 1, dpi=300)
    if not images:
        raise ValueError(f"No page found at index {page_num}")

    img = images[0]
    if img.mode != "L":
        img = img.convert("L")
    padded = resize_with_padding(img, target_size, fill=255)
    buffer = io.BytesIO()
    padded.save(buffer, format="PNG", dpi=(300, 300))
    return buffer.getvalue()
