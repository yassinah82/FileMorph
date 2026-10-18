import os
from pathlib import Path
from typing import List, Optional, Callable
import pymupdf as fitz

class PDFOperations:
    """Provides high-performance, lossless PDF operations: Split and Merge."""

    @staticmethod
    def parse_page_range(range_str: str, max_pages: int) -> List[int]:
        """
        Parses human-friendly page strings like '1-3, 5, 8-10' into 0-indexed page integers.
        """
        pages = set()
        parts = [p.strip() for p in range_str.split(",") if p.strip()]

        for part in parts:
            if "-" in part:
                sub = part.split("-")
                start = int(sub[0].strip())
                end = int(sub[1].strip())
                for pg in range(start, end + 1):
                    if 1 <= pg <= max_pages:
                        pages.add(pg - 1)
            else:
                pg = int(part)
                if 1 <= pg <= max_pages:
                    pages.add(pg - 1)

        return sorted(list(pages))

    @classmethod
    def split_all_pages(
        cls,
        pdf_path: str,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[str]:
        """
        Splits a multi-page PDF into separate single-page PDF files.
        (e.g., document_page_1.pdf, document_page_2.pdf, ...)
        """
        src = Path(pdf_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"PDF not found: {src}")

        out_folder = Path(output_dir).resolve() if output_dir else src.parent
        out_folder.mkdir(parents=True, exist_ok=True)

        doc = fitz.open(str(src))
        total_pages = len(doc)
        output_files: List[str] = []

        try:
            for idx in range(total_pages):
                if progress_callback:
                    pct = (idx / total_pages) * 0.95
                    progress_callback(pct, f"Extracting page {idx + 1} of {total_pages}...")

                single_doc = fitz.open()
                single_doc.insert_pdf(doc, from_page=idx, to_page=idx)
                
                filename = f"{src.stem}_page_{idx + 1}.pdf"
                dest_file = str(out_folder / filename)
                single_doc.save(dest_file)
                single_doc.close()
                output_files.append(dest_file)

            if progress_callback:
                progress_callback(1.0, f"Split into {len(output_files)} PDF pages successfully.")

            return output_files
        finally:
            doc.close()

    @classmethod
    def extract_page_range(
        cls,
        pdf_path: str,
        range_str: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Extracts selected page ranges (e.g., '1-3, 5, 8-10') into a single new PDF document.
        """
        src = Path(pdf_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"PDF not found: {src}")

        if not output_path:
            clean_range = range_str.replace(" ", "").replace(",", "_")
            out_file = src.parent / f"{src.stem}_pages_{clean_range}.pdf"
        else:
            out_file = Path(output_path).resolve()

        doc = fitz.open(str(src))
        max_pages = len(doc)
        page_indices = cls.parse_page_range(range_str, max_pages)

        if not page_indices:
            doc.close()
            raise ValueError(f"No valid pages found in range '{range_str}' for document with {max_pages} pages.")

        if progress_callback:
            progress_callback(0.3, f"Extracting {len(page_indices)} pages from PDF...")

        new_doc = fitz.open()
        try:
            for idx, p_num in enumerate(page_indices):
                new_doc.insert_pdf(doc, from_page=p_num, to_page=p_num)
                if progress_callback:
                    pct = 0.3 + (idx / len(page_indices)) * 0.6
                    progress_callback(pct, f"Writing extracted page {p_num + 1}...")

            new_doc.save(str(out_file))

            if progress_callback:
                progress_callback(1.0, f"Extracted {len(page_indices)} pages to {out_file.name}.")

            return str(out_file)
        finally:
            new_doc.close()
            doc.close()

    @classmethod
    def merge_pdfs(
        cls,
        pdf_paths: List[str],
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Merges multiple PDF documents into a single unified PDF file in the given order.
        """
        if not pdf_paths or len(pdf_paths) < 2:
            raise ValueError("At least 2 PDF files are required for merging.")

        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        merged_doc = fitz.open()
        total_files = len(pdf_paths)

        try:
            for idx, p in enumerate(pdf_paths):
                if progress_callback:
                    pct = (idx / total_files) * 0.85
                    progress_callback(pct, f"Merging [{idx + 1}/{total_files}]: {Path(p).name}...")

                src_path = Path(p).resolve()
                if not src_path.exists():
                    raise FileNotFoundError(f"PDF not found: {src_path}")

                sub_doc = fitz.open(str(src_path))
                merged_doc.insert_pdf(sub_doc)
                sub_doc.close()

            if progress_callback:
                progress_callback(0.9, "Finalizing merged PDF...")

            merged_doc.save(str(out_file))

            if progress_callback:
                progress_callback(1.0, f"Successfully merged {total_files} PDF files.")

            return str(out_file)
        finally:
            merged_doc.close()
