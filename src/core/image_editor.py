import os
from pathlib import Path
from typing import Tuple, Optional, Union
from PIL import Image

class ImageEditor:
    """Provides high-performance image transformations: Crop, Resize, Rotate, and Flip."""

    @staticmethod
    def crop(
        img: Image.Image,
        box: Optional[Tuple[int, int, int, int]] = None,
        aspect_ratio: Optional[str] = None,
        margins_percent: Optional[Tuple[float, float, float, float]] = None
    ) -> Image.Image:
        """
        Crops an image using:
        - box: (left, top, right, bottom) pixel coordinates
        - aspect_ratio: string like '1:1', '16:9', '4:3', '3:2' (centered crop)
        - margins_percent: (top%, right%, bottom%, left%) where 0.1 = 10%
        """
        width, height = img.size

        if box:
            left, top, right, bottom = box
            left = max(0, min(width - 1, left))
            top = max(0, min(height - 1, top))
            right = max(left + 1, min(width, right))
            bottom = max(top + 1, min(height, bottom))
            return img.crop((left, top, right, bottom))

        if aspect_ratio:
            try:
                parts = aspect_ratio.split(":")
                target_ratio = float(parts[0]) / float(parts[1])
            except Exception:
                target_ratio = 1.0

            current_ratio = width / height
            if current_ratio > target_ratio:
                # Image is wider than target: trim left and right
                new_width = int(height * target_ratio)
                offset = (width - new_width) // 2
                return img.crop((offset, 0, offset + new_width, height))
            else:
                # Image is taller than target: trim top and bottom
                new_height = int(width / target_ratio)
                offset = (height - new_height) // 2
                return img.crop((0, offset, width, offset + new_height))

        if margins_percent:
            m_top, m_right, m_bottom, m_left = margins_percent
            left = int(width * (m_left / 100.0))
            top = int(height * (m_top / 100.0))
            right = int(width * (1.0 - m_right / 100.0))
            bottom = int(height * (1.0 - m_bottom / 100.0))
            return img.crop((left, top, max(left + 1, right), max(top + 1, bottom)))

        return img

    @staticmethod
    def resize(
        img: Image.Image,
        width: Optional[int] = None,
        height: Optional[int] = None,
        scale: Optional[float] = None,
        keep_aspect_ratio: bool = True
    ) -> Image.Image:
        """
        Resizes an image using high-quality Lanczos resampling.
        - scale: 0.5 (50%), 2.0 (200%), etc.
        - width/height: specific dimensions (with keep_aspect_ratio support)
        """
        orig_w, orig_h = img.size

        if scale is not None and scale > 0:
            new_w = max(1, int(orig_w * scale))
            new_h = max(1, int(orig_h * scale))
            return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        if width and height:
            if keep_aspect_ratio:
                # Scale within the bounding box
                ratio = min(width / orig_w, height / orig_h)
                new_w = max(1, int(orig_w * ratio))
                new_h = max(1, int(orig_h * ratio))
                return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            else:
                return img.resize((width, height), Image.Resampling.LANCZOS)
        elif width and not height:
            ratio = width / orig_w
            new_h = max(1, int(orig_h * ratio))
            return img.resize((width, new_h), Image.Resampling.LANCZOS)
        elif height and not width:
            ratio = height / orig_h
            new_w = max(1, int(orig_w * ratio))
            return img.resize((new_w, height), Image.Resampling.LANCZOS)

        return img

    @staticmethod
    def rotate(
        img: Image.Image,
        angle: float,
        expand: bool = True
    ) -> Image.Image:
        """
        Rotates image by angle in degrees counter-clockwise (90, 180, 270, etc.).
        Fast-paths common 90-degree rotations using Image.Transpose.
        """
        norm_angle = int(angle) % 360
        if norm_angle == 90:
            return img.transpose(Image.Transpose.ROTATE_90)
        elif norm_angle == 180:
            return img.transpose(Image.Transpose.ROTATE_180)
        elif norm_angle == 270:
            return img.transpose(Image.Transpose.ROTATE_270)
        elif norm_angle == 0:
            return img
        else:
            return img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=expand)

    @staticmethod
    def flip(
        img: Image.Image,
        horizontal: bool = False,
        vertical: bool = False
    ) -> Image.Image:
        """Flips image horizontally and/or vertically."""
        if horizontal:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if vertical:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return img
