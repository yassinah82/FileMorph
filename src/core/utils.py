import os
from pathlib import Path
from typing import Dict, List, Set
from PIL import Image

# Supported format groups
DOC_FORMATS: Set[str] = {".pdf", ".docx", ".doc", ".pptx", ".ppt"}
IMAGE_FORMATS: Set[str] = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".ico"}
ALL_SUPPORTED_FORMATS: Set[str] = DOC_FORMATS | IMAGE_FORMATS

# Normalization mapping for standardizing extension strings
EXTENSION_MAP: Dict[str, str] = {
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "png": "png",
    "webp": "webp",
    "wpeg": "webp",  # Common typo handling
    "bmp": "bmp",
    "tiff": "tiff",
    "tif": "tiff",
    "ico": "ico",
    "pdf": "pdf",
    "docx": "docx",
    "doc": "doc",
    "pptx": "pptx",
    "ppt": "ppt",
    "txt": "txt",
    "docx (ocr)": "docx_ocr",
    "txt (ocr)": "txt_ocr",
    "split pdf": "split_pdf"
}

def normalize_extension(ext: str) -> str:
    """Strip dots and lowercase extension name."""
    clean = ext.strip().lower().lstrip(".")
    return EXTENSION_MAP.get(clean, clean)

def get_target_formats_for_file(filepath: str, include_ocr: bool = True) -> List[str]:
    """Returns a list of valid target conversion formats based on input file type."""
    ext = Path(filepath).suffix.lower()
    norm_ext = normalize_extension(ext)

    if norm_ext == "pdf":
        targets = ["docx", "png", "jpg", "webp", "bmp", "tiff"]
        if include_ocr:
            targets.append("docx (ocr)")
        targets.append("split pdf")
        return targets
    elif norm_ext in ("docx", "doc", "pptx", "ppt"):
        return ["pdf"]
    elif Path(filepath).suffix.lower() in IMAGE_FORMATS:
        img_targets = ["pdf", "png", "jpg", "webp", "bmp", "tiff", "ico"]
        if include_ocr:
            img_targets.append("docx (ocr)")
        # Include self for image transformations (e.g. crop/resize/rotate PNG to PNG)
        return img_targets
    return []

def prepare_image_for_mode(img: Image.Image, target_format: str, bg_color=(255, 255, 255)) -> Image.Image:
    """
    Handles alpha channels safely.
    If target format (like JPEG, BMP, or PDF) does not support alpha channel,
    blend over a solid background (default white) to prevent Pillow OS/ValueErrors.
    """
    target_format = normalize_extension(target_format)
    needs_rgb = target_format in ("jpeg", "bmp")

    if needs_rgb or target_format == "pdf":
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img_rgba = img.convert("RGBA")
            background = Image.new("RGBA", img_rgba.size, (*bg_color, 255))
            composite = Image.alpha_composite(background, img_rgba)
            return composite.convert("RGB")
        elif img.mode != "RGB":
            return img.convert("RGB")
    elif target_format == "ico":
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        if img.size[0] > 256 or img.size[1] > 256:
            img = img.resize((256, 256), Image.Resampling.LANCZOS)
    return img

def generate_output_path(input_path: str, target_ext: str, output_dir: str = None) -> str:
    """Generates an output file path with the target extension."""
    p = Path(input_path)
    target_ext = target_ext.lstrip(".")
    folder = Path(output_dir) if output_dir else p.parent
    return str(folder / f"{p.stem}.{target_ext}")
