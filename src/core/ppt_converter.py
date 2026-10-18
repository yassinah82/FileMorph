import os
import subprocess
from pathlib import Path
from typing import Optional, Callable

class PPTConverter:
    """Handles PowerPoint (.pptx, .ppt) to PDF conversions with MS PowerPoint COM and fallback."""

    @staticmethod
    def to_pdf(
        ppt_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        src = Path(ppt_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"PowerPoint file not found: {src}")

        if not output_path:
            out_file = src.with_suffix(".pdf")
        else:
            out_file = Path(output_path).resolve()

        if progress_callback:
            progress_callback(0.2, "Initializing PowerPoint engine...")

        try:
            return PPTConverter._convert_with_powerpoint(str(src), str(out_file), progress_callback)
        except Exception as ppt_err:
            if progress_callback:
                progress_callback(0.4, f"PowerPoint COM failed ({ppt_err}). Trying fallback...")
            try:
                return PPTConverter._convert_with_libreoffice(str(src), str(out_file), progress_callback)
            except Exception as lo_err:
                raise RuntimeError(
                    f"PowerPoint to PDF conversion failed.\nMS PowerPoint Error: {ppt_err}\nFallback Error: {lo_err}"
                )

    @staticmethod
    def _convert_with_powerpoint(
        src_path: str,
        out_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """Uses PowerPoint COM automation with thread-safe CoInitialize and guaranteed cleanup."""
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()

        ppt = None
        deck = None
        try:
            # Constants
            ppSaveAsPDF = 32
            msoFalse = 0

            if progress_callback:
                progress_callback(0.3, "Opening PowerPoint application...")

            ppt = win32com.client.DispatchEx("PowerPoint.Application")

            if progress_callback:
                progress_callback(0.5, "Loading presentation...")

            # Open presentation without displaying UI window
            deck = ppt.Presentations.Open(
                src_path,
                ReadOnly=True,
                Untitled=msoFalse,
                WithWindow=msoFalse
            )

            if progress_callback:
                progress_callback(0.75, "Exporting slides to PDF...")

            deck.SaveAs(out_path, ppSaveAsPDF)

            if progress_callback:
                progress_callback(1.0, "Export completed successfully.")

            return out_path
        finally:
            if deck is not None:
                try:
                    deck.Close()
                except Exception:
                    pass
            if ppt is not None:
                try:
                    ppt.Quit()
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
            raise FileNotFoundError("Neither Microsoft PowerPoint nor LibreOffice was found for presentation conversion.")

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
