import os
from pathlib import Path
from typing import List, Optional, Callable, Union, Dict, Any, Tuple
from PIL import Image

from .utils import normalize_extension, prepare_image_for_mode
from .image_editor import ImageEditor

class ImageConverter:
    """Handles Image-to-Image, transformations (Crop/Resize/Rotate/Flip), and Image-to-PDF conversions."""

    @staticmethod
    def to_image(
        image_path: str,
        target_format: str,
        output_path: Optional[str] = None,
        quality: int = 92,
        lossless: bool = False,
        strip_metadata: bool = True,
        # Transform options
        crop_box: Optional[Tuple[int, int, int, int]] = None,
        crop_aspect_ratio: Optional[str] = None,
        crop_margins: Optional[Tuple[float, float, float, float]] = None,
        resize_dims: Optional[Tuple[Optional[int], Optional[int]]] = None,
        resize_scale: Optional[float] = None,
        keep_aspect_ratio: bool = True,
        rotate_angle: Optional[float] = None,
        flip_h: bool = False,
        flip_v: bool = False,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Converts any supported image format to another image format with optional
        Cropping, Resizing, Rotation, Flipping, Lossless compression, and EXIF privacy stripping.
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
            progress_callback(0.15, "Reading source image...")

        with Image.open(src) as img:
            exif_data = None if strip_metadata else img.info.get("exif")

            # 1. Apply Rotation / Flips first
            if rotate_angle:
                if progress_callback:
                    progress_callback(0.3, f"Rotating by {rotate_angle}°...")
                img = ImageEditor.rotate(img, rotate_angle)

            if flip_h or flip_v:
                if progress_callback:
                    progress_callback(0.4, "Flipping image...")
                img = ImageEditor.flip(img, horizontal=flip_h, vertical=flip_v)

            # 2. Apply Crop
            if crop_box or crop_aspect_ratio or crop_margins:
                if progress_callback:
                    progress_callback(0.5, "Cropping image...")
                img = ImageEditor.crop(img, box=crop_box, aspect_ratio=crop_aspect_ratio, margins_percent=crop_margins)

            # 3. Apply Resize
            if resize_dims or resize_scale:
                if progress_callback:
                    progress_callback(0.65, "Resizing image...")
                w, h = resize_dims if resize_dims else (None, None)
                img = ImageEditor.resize(img, width=w, height=h, scale=resize_scale, keep_aspect_ratio=keep_aspect_ratio)

            if progress_callback:
                progress_callback(0.8, f"Encoding {norm_target.upper()} format...")

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
            progress_callback(1.0, "Saved image successfully.")

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
