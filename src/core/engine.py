import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any, Union

from .utils import (
    normalize_extension,
    get_target_formats_for_file,
    IMAGE_FORMATS,
    DOC_FORMATS,
)
from .pdf_converter import PDFConverter
from .docx_converter import DOCXConverter
from .ppt_converter import PPTConverter
from .image_converter import ImageConverter
from .ocr_engine import OCREngine
from .pdf_ops import PDFOperations

@dataclass
class ConversionResult:
    source_file: str
    target_format: str
    output_files: List[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    duration_seconds: float = 0.0

class ConversionEngine:
    """Unified facade for converting documents, presentations, images, OCR, and PDF tools."""

    @staticmethod
    def get_supported_targets(filepath: str, include_ocr: bool = True) -> List[str]:
        return get_target_formats_for_file(filepath, include_ocr=include_ocr)

    @classmethod
    def convert(
        cls,
        source_path: str,
        target_format: str,
        output_path: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ConversionResult:
        """
        Routes the conversion based on source and target formats.
        """
        start_time = time.time()
        options = options or {}
        norm_target = normalize_extension(target_format)
        src = Path(source_path).resolve()

        if not src.exists():
            return ConversionResult(
                source_file=str(src),
                target_format=target_format,
                success=False,
                error=f"Source file does not exist: {src}",
                duration_seconds=0.0
            )

        src_ext = normalize_extension(src.suffix)
        result = ConversionResult(source_file=str(src), target_format=target_format)

        try:
            # 1. OCR Conversion branch (scanned PDF or Image -> DOCX)
            if norm_target in ("docx_ocr", "docx (ocr)") or options.get("use_ocr", False):
                lang = options.get("ocr_lang", "en-US")
                out = OCREngine.to_docx_ocr(
                    source_path=str(src),
                    output_path=output_path,
                    lang=lang,
                    progress_callback=progress_callback
                )
                result.output_files = [out]

            # 2. PDF Operations (Split)
            elif src_ext == "pdf" and norm_target in ("split_pdf", "split"):
                range_str = options.get("page_range")
                if range_str:
                    out = PDFOperations.extract_page_range(
                        str(src),
                        range_str=range_str,
                        output_path=output_path,
                        progress_callback=progress_callback
                    )
                    result.output_files = [out]
                else:
                    out_dir = options.get("output_dir", None)
                    files = PDFOperations.split_all_pages(
                        str(src),
                        output_dir=out_dir,
                        progress_callback=progress_callback
                    )
                    result.output_files = files

            # 3. PDF conversions (to DOCX or Images)
            elif src_ext == "pdf":
                if norm_target in ("docx", "doc"):
                    out = PDFConverter.to_docx(
                        pdf_path=str(src),
                        output_path=output_path,
                        start_page=options.get("start_page", 0),
                        end_page=options.get("end_page", None),
                        progress_callback=progress_callback
                    )
                    result.output_files = [out]
                elif norm_target in [normalize_extension(e) for e in IMAGE_FORMATS]:
                    dpi = options.get("dpi", 200)
                    out_dir = options.get("output_dir", None)
                    files = PDFConverter.to_images(
                        pdf_path=str(src),
                        target_format=norm_target,
                        dpi=dpi,
                        output_dir=out_dir,
                        progress_callback=progress_callback
                    )
                    result.output_files = files
                else:
                    raise ValueError(f"Unsupported conversion from PDF to {target_format}")

            # 4. PowerPoint (.pptx, .ppt) to PDF
            elif src_ext in ("pptx", "ppt"):
                if norm_target == "pdf":
                    out = PPTConverter.to_pdf(
                        ppt_path=str(src),
                        output_path=output_path,
                        progress_callback=progress_callback
                    )
                    result.output_files = [out]
                else:
                    raise ValueError(f"Unsupported conversion from PowerPoint to {target_format}")

            # 5. DOCX / DOC conversions to PDF
            elif src_ext in ("docx", "doc"):
                if norm_target == "pdf":
                    out = DOCXConverter.to_pdf(
                        docx_path=str(src),
                        output_path=output_path,
                        progress_callback=progress_callback
                    )
                    result.output_files = [out]
                else:
                    raise ValueError(f"Unsupported conversion from {src_ext} to {target_format}")

            # 6. Image conversions & Editing (Crop / Resize / Rotate / Flip)
            elif f".{src_ext}" in IMAGE_FORMATS or src.suffix.lower() in IMAGE_FORMATS:
                if norm_target == "pdf":
                    out = ImageConverter.to_pdf(
                        image_paths=[str(src)],
                        output_path=output_path,
                        progress_callback=progress_callback
                    )
                    result.output_files = [out]
                elif norm_target in [normalize_extension(e) for e in IMAGE_FORMATS]:
                    quality = options.get("quality", 92)
                    lossless = options.get("lossless", False)
                    strip_metadata = options.get("strip_metadata", True)

                    # Transform options
                    crop_box = options.get("crop_box")
                    crop_aspect_ratio = options.get("crop_aspect_ratio")
                    crop_margins = options.get("crop_margins")
                    resize_dims = options.get("resize_dims")
                    resize_scale = options.get("resize_scale")
                    keep_aspect_ratio = options.get("keep_aspect_ratio", True)
                    rotate_angle = options.get("rotate_angle")
                    flip_h = options.get("flip_h", False)
                    flip_v = options.get("flip_v", False)

                    out = ImageConverter.to_image(
                        image_path=str(src),
                        target_format=norm_target,
                        output_path=output_path,
                        quality=quality,
                        lossless=lossless,
                        strip_metadata=strip_metadata,
                        crop_box=crop_box,
                        crop_aspect_ratio=crop_aspect_ratio,
                        crop_margins=crop_margins,
                        resize_dims=resize_dims,
                        resize_scale=resize_scale,
                        keep_aspect_ratio=keep_aspect_ratio,
                        rotate_angle=rotate_angle,
                        flip_h=flip_h,
                        flip_v=flip_v,
                        progress_callback=progress_callback
                    )
                    result.output_files = [out]
                else:
                    raise ValueError(f"Unsupported conversion from image to {target_format}")
            else:
                raise ValueError(f"Unsupported source format: {src_ext}")

            result.success = True
        except Exception as e:
            result.success = False
            result.error = str(e)
        finally:
            result.duration_seconds = round(time.time() - start_time, 2)

        return result

    @classmethod
    def convert_images_to_single_pdf(
        cls,
        image_paths: List[str],
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ConversionResult:
        """Merges multiple images into a single PDF file."""
        start_time = time.time()
        result = ConversionResult(
            source_file=f"[{len(image_paths)} images]",
            target_format="pdf"
        )
        try:
            out = ImageConverter.to_pdf(image_paths, output_path=output_path, progress_callback=progress_callback)
            result.output_files = [out]
            result.success = True
        except Exception as e:
            result.success = False
            result.error = str(e)
        finally:
            result.duration_seconds = round(time.time() - start_time, 2)
        return result

    @classmethod
    def merge_pdfs(
        cls,
        pdf_paths: List[str],
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ConversionResult:
        """Merges multiple PDF documents into a single PDF file."""
        start_time = time.time()
        result = ConversionResult(
            source_file=f"[{len(pdf_paths)} PDFs]",
            target_format="pdf"
        )
        try:
            out = PDFOperations.merge_pdfs(pdf_paths, output_path=output_path, progress_callback=progress_callback)
            result.output_files = [out]
            result.success = True
        except Exception as e:
            result.success = False
            result.error = str(e)
        finally:
            result.duration_seconds = round(time.time() - start_time, 2)
        return result

    @classmethod
    def split_pdf(
        cls,
        pdf_path: str,
        output_dir: Optional[str] = None,
        page_range: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ConversionResult:
        """Splits a PDF into pages or extracts a range of pages."""
        start_time = time.time()
        result = ConversionResult(
            source_file=pdf_path,
            target_format="pdf"
        )
        try:
            if page_range:
                out = PDFOperations.extract_page_range(pdf_path, range_str=page_range, output_path=None, progress_callback=progress_callback)
                result.output_files = [out]
            else:
                files = PDFOperations.split_all_pages(pdf_path, output_dir=output_dir, progress_callback=progress_callback)
                result.output_files = files
            result.success = True
        except Exception as e:
            result.success = False
            result.error = str(e)
        finally:
            result.duration_seconds = round(time.time() - start_time, 2)
        return result
