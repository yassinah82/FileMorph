import os
from pathlib import Path
from typing import List, Optional, Callable, Union, Dict, Any
from PIL import Image

from .utils import normalize_extension, prepare_image_for_mode

class ImageConverter:
    """Handles Image-to-Image and Image-to-PDF conversions with optimization and privacy controls."""

    @staticmethod
    def to_image(
        image_path: str,
        target_format: str,
        output_path: Optional[str] = None,
        quality: int = 92,
        lossless: bool = False,
        strip_metadata: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Converts any supported image format to another image format.
        Supports lossless compression presets, optimization, and EXIF privacy stripping.
        """
        src = Path(image_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Image not found: {src}")

        norm_target = normalize_extension(target_format)
        save_ext = "jpg" if norm_target == "jpeg" else norm_target

        if not output_path:
            out_file = src.with_suffix(f".{save_ext}")
        else:
            out_file = Path(output_path).resolve()

        if progress_callback:
            progress_callback(0.2, "Reading source image...")

        with Image.open(src) as img:
            exif_data = None if strip_metadata else img.info.get("exif")

            if progress_callback:
                progress_callback(0.5, f"Optimizing and converting to {norm_target.upper()}...")

            img = prepare_image_for_mode(img, norm_target)

            save_kwargs: Dict[str, Any] = {}
            if exif_data:
                save_kwargs["exif"] = exif_data

            if norm_target in ("jpeg", "jpg"):
                save_kwargs.update({
                    "quality": quality,
                    "optimize": True,
                    "progressive": True
                })
            elif norm_target == "webp":
                if lossless:
                    save_kwargs.update({"lossless": True, "method": 6})
                else:
                    save_kwargs.update({"quality": quality, "lossless": False, "method": 6})
            elif norm_target == "png":
                # Maximum compression level for PNG
                save_kwargs.update({
                    "optimize": True,
                    "compress_level": 9
                })
            elif norm_target == "tiff":
                save_kwargs.update({"compression": "tiff_deflate"})
            elif norm_target == "ico":
                save_kwargs.update({
                    "sizes": [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
                })

            img.save(out_file, **save_kwargs)

        if progress_callback:
            progress_callback(1.0, "Saved successfully.")

        return str(out_file)

    @staticmethod
    def to_pdf(
        image_paths: Union[str, List[str]],
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Converts a single image or merges multiple images into a high-quality PDF.
        """
        if isinstance(image_paths, str):
            image_paths = [image_paths]

        if not image_paths:
            raise ValueError("No images provided for PDF conversion.")

        first_path = Path(image_paths[0]).resolve()
        if not output_path:
            out_file = first_path.with_suffix(".pdf")
        else:
            out_file = Path(output_path).resolve()

        total = len(image_paths)
        converted_images: List[Image.Image] = []

        try:
            for idx, img_path in enumerate(image_paths):
                if progress_callback:
                    pct = (idx / total) * 0.8 + 0.1
                    progress_callback(pct, f"Processing image {idx + 1} of {total}...")

                p = Path(img_path).resolve()
                if not p.exists():
                    raise FileNotFoundError(f"Image not found: {p}")

                raw = Image.open(p)
                # Convert RGBA to RGB with white background for PDF compatibility
                rgb_img = prepare_image_for_mode(raw, "pdf")
                converted_images.append(rgb_img)

            if progress_callback:
                progress_callback(0.9, "Generating PDF document...")

            first_img = converted_images[0]
            rest_imgs = converted_images[1:] if len(converted_images) > 1 else []

            first_img.save(
                out_file,
                "PDF",
                resolution=150.0,
                save_all=True,
                append_images=rest_imgs
            )

            if progress_callback:
                progress_callback(1.0, "PDF created successfully.")

            return str(out_file)
        finally:
            for img in converted_images:
                try:
                    img.close()
                except Exception:
                    pass
