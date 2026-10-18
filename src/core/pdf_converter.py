import os
from pathlib import Path
from typing import List, Callable, Optional
import pymupdf as fitz
from pdf2docx import Converter

from .utils import normalize_extension, prepare_image_for_mode

class PDFConverter:
    """Handles PDF conversions: PDF -> DOCX and PDF -> Images."""

    @staticmethod
    def to_docx(
        pdf_path: str,
        output_path: Optional[str] = None,
        start_page: int = 0,
        end_page: Optional[int] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Converts PDF to DOCX using pdf2docx.
        """
        pdf_path = str(Path(pdf_path).resolve())
        if not output_path:
            output_path = str(Path(pdf_path).with_suffix(".docx"))
        else:
            output_path = str(Path(output_path).resolve())

        if progress_callback:
            progress_callback(0.1, "Initializing PDF parser...")

        cv = Converter(pdf_path)
        try:
            if progress_callback:
                progress_callback(0.3, "Extracting layouts and text...")
            
            # Convert specified page range (0-indexed)
            cv.convert(output_path, start=start_page, end=end_page)
            
            if progress_callback:
                progress_callback(1.0, "Conversion completed.")
        finally:
            cv.close()

        return output_path

    @staticmethod
    def to_images(
        pdf_path: str,
        target_format: str = "png",
        dpi: int = 200,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[str]:
        """
        Renders PDF pages to image files (PNG, JPG, WEBP, BMP, TIFF).
        Self-contained via PyMuPDF - no Poppler installation required!
        """
        pdf_path = str(Path(pdf_path).resolve())
        target_format = normalize_extension(target_format)
        
        # Pillow / PyMuPDF format string mapping
        save_ext = "jpg" if target_format == "jpeg" else target_format

        src_path = Path(pdf_path)
        if not output_dir:
            out_folder = src_path.parent
        else:
            out_folder = Path(output_dir).resolve()
            out_folder.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        created_files: List[str] = []

        # Calculate matrix scaling factor from 72 DPI base
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        try:
            for page_index in range(total_pages):
                if progress_callback:
                    pct = (page_index / total_pages) * 0.9 + 0.05
                    progress_callback(pct, f"Rendering page {page_index + 1} of {total_pages}...")

                page = doc.load_page(page_index)
                
                # If target is JPEG/BMP, don't use alpha
                alpha = target_format not in ("jpeg", "bmp")
                pix = page.get_pixmap(matrix=matrix, alpha=alpha)

                if total_pages == 1:
                    filename = f"{src_path.stem}.{save_ext}"
                else:
                    filename = f"{src_path.stem}_page_{page_index + 1}.{save_ext}"

                dest_file = str(out_folder / filename)
                
                # PyMuPDF supports direct pixmap saving for common formats
                if target_format in ("png", "jpeg", "jpg"):
                    pix.save(dest_file)
                else:
                    # For webp, bmp, tiff, convert pixmap to Pillow Image
                    from PIL import Image
                    mode = "RGBA" if pix.alpha else "RGB"
                    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                    img = prepare_image_for_mode(img, target_format)
                    img.save(dest_file)

                created_files.append(dest_file)

            if progress_callback:
                progress_callback(1.0, f"Rendered {total_pages} pages successfully.")
        finally:
            doc.close()

        return created_files
