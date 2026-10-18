import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Callable

class DOCXConverter:
    """Handles DOCX/DOC to PDF conversions with native Windows Word COM and LibreOffice fallback."""

    @staticmethod
    def to_pdf(
        docx_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Converts .docx or .doc to .pdf.
        Uses MS Word COM automation with full error handling and resource cleanup.
        """
        src = Path(docx_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        if not output_path:
            out_file = src.with_suffix(".pdf")
        else:
            out_file = Path(output_path).resolve()

        if progress_callback:
            progress_callback(0.2, "Initializing Word automation engine...")

        # Try MS Word via COM (standard high-fidelity method on Windows)
        try:
            return DOCXConverter._convert_with_msword(str(src), str(out_file), progress_callback)
        except Exception as com_err:
            # Check for LibreOffice fallback if Word COM is unavailable
            if progress_callback:
                progress_callback(0.4, f"MS Word COM failed ({com_err}). Trying fallback...")
            try:
                return DOCXConverter._convert_with_libreoffice(str(src), str(out_file), progress_callback)
            except Exception as lo_err:
                raise RuntimeError(
                    f"DOCX to PDF conversion failed.\nMS Word Error: {com_err}\nFallback Error: {lo_err}"
                )

    @staticmethod
    def _convert_with_msword(
        src_path: str,
        out_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """Uses win32com to export PDF via MS Word with thread-safe CoInitialize."""
        import pythoncom
        import win32com.client

        # Initialize COM library for the current thread (essential for GUI / background threads)
        pythoncom.CoInitialize()

        word = None
        doc = None
        try:
            # Constants for Word automation
            wdFormatPDF = 17
            wdDoNotSaveChanges = 0

            # Start hidden Word instance
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False

            if progress_callback:
                progress_callback(0.5, "Opening document in Word...")

            # Open document ReadOnly
            doc = word.Documents.Open(
                FileName=src_path,
                ReadOnly=True,
                AddToRecentFiles=False,
                Visible=False
            )

            if progress_callback:
                progress_callback(0.75, "Exporting to PDF...")

            # Save as PDF
            doc.SaveAs2(FileName=out_path, FileFormat=wdFormatPDF)

            if progress_callback:
                progress_callback(1.0, "Export completed successfully.")

            return out_path
        finally:
            # Ensure document and Word process are ALWAYS cleanly closed
            if doc is not None:
                try:
                    doc.Close(SaveChanges=wdDoNotSaveChanges)
                except Exception:
                    pass
            if word is not None:
                try:
                    word.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()

    @staticmethod
    def _convert_with_libreoffice(
        src_path: str,
        out_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """Fallback: uses headless LibreOffice if installed."""
        possible_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        soffice_bin = next((p for p in possible_paths if os.path.exists(p)), None)
        if not soffice_bin:
            raise FileNotFoundError("Neither Microsoft Word nor LibreOffice was found for DOCX conversion.")

        out_dir = str(Path(out_path).parent)
        cmd = [
            soffice_bin,
            "--headless",
            "--convert-to", "pdf",
            src_path,
            "--outdir", out_dir
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice failed: {result.stderr}")

        expected_out = Path(out_dir) / f"{Path(src_path).stem}.pdf"
        if str(expected_out) != out_path and expected_out.exists():
            os.replace(expected_out, out_path)

        if progress_callback:
            progress_callback(1.0, "Conversion completed.")

        return out_path
