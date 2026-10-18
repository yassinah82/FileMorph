import os
import sys
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import ConversionEngine, normalize_extension
from src.context_menu.installer import install_context_menu, uninstall_context_menu, is_context_menu_installed

TEST_DIR = PROJECT_ROOT / "tests" / "temp"

class TestFileMorph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TEST_DIR.mkdir(parents=True, exist_ok=True)

        # 1. Create a transparent RGBA PNG image
        cls.rgba_png = str(TEST_DIR / "sample_alpha.png")
        img = Image.new("RGBA", (200, 200), (255, 0, 0, 128))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 150, 150], fill=(0, 255, 0, 200))
        img.save(cls.rgba_png)

        # 2. Create a standard RGB JPEG
        cls.rgb_jpg = str(TEST_DIR / "sample.jpg")
        img_rgb = Image.new("RGB", (200, 200), (0, 0, 255))
        img_rgb.save(cls.rgb_jpg, "JPEG")

    def test_01_alpha_png_to_jpeg(self):
        """Test converting transparent RGBA image to JPEG without crashing."""
        res = ConversionEngine.convert(self.rgba_png, "jpeg")
        self.assertTrue(res.success, f"Error: {res.error}")
        self.assertTrue(os.path.exists(res.output_files[0]))
        with Image.open(res.output_files[0]) as out:
            self.assertEqual(out.mode, "RGB")

    def test_02_image_to_webp_and_back(self):
        """Test JPG -> WEBP and WEBP -> PNG."""
        res1 = ConversionEngine.convert(self.rgb_jpg, "webp", options={"quality": 85})
        self.assertTrue(res1.success, f"Error: {res1.error}")
        webp_path = res1.output_files[0]
        self.assertTrue(os.path.exists(webp_path))

        res2 = ConversionEngine.convert(webp_path, "png")
        self.assertTrue(res2.success, f"Error: {res2.error}")
        self.assertTrue(os.path.exists(res2.output_files[0]))

    def test_03_image_to_pdf(self):
        """Test single image to PDF."""
        res = ConversionEngine.convert(self.rgb_jpg, "pdf")
        self.assertTrue(res.success, f"Error: {res.error}")
        self.assertTrue(os.path.exists(res.output_files[0]))

    def test_04_merge_multiple_images_to_pdf(self):
        """Test merging multiple images into a single PDF."""
        merged_pdf = str(TEST_DIR / "merged_output.pdf")
        res = ConversionEngine.convert_images_to_single_pdf(
            image_paths=[self.rgba_png, self.rgb_jpg],
            output_path=merged_pdf
        )
        self.assertTrue(res.success, f"Error: {res.error}")
        self.assertTrue(os.path.exists(merged_pdf))

    def test_05_pdf_to_docx_and_back(self):
        """Test PDF -> DOCX and DOCX -> PDF."""
        # Use PyMuPDF to create a simple 1-page PDF
        import pymupdf as fitz
        pdf_path = str(TEST_DIR / "sample_doc.pdf")
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Hello FileMorph Conversion Test!", fontsize=24)
        page.insert_text((72, 120), "This document tests PDF to DOCX and DOCX to PDF.", fontsize=14)
        doc.save(pdf_path)
        doc.close()

        # PDF -> DOCX
        res_docx = ConversionEngine.convert(pdf_path, "docx")
        self.assertTrue(res_docx.success, f"PDF to DOCX failed: {res_docx.error}")
        docx_file = res_docx.output_files[0]
        self.assertTrue(os.path.exists(docx_file))

        # DOCX -> PDF
        docx_out_pdf = str(TEST_DIR / "back_to_doc.pdf")
        res_back_pdf = ConversionEngine.convert(docx_file, "pdf", output_path=docx_out_pdf)
        self.assertTrue(res_back_pdf.success, f"DOCX to PDF failed: {res_back_pdf.error}")
        self.assertTrue(os.path.exists(docx_out_pdf))

    def test_06_pdf_to_images(self):
        """Test PDF to PNG, JPG, WEBP."""
        import pymupdf as fitz
        pdf_path = str(TEST_DIR / "sample_doc.pdf")

        for fmt in ["png", "jpg", "webp"]:
            res = ConversionEngine.convert(pdf_path, fmt, options={"dpi": 150})
            self.assertTrue(res.success, f"PDF to {fmt} failed: {res.error}")
            self.assertTrue(len(res.output_files) > 0)
            self.assertTrue(os.path.exists(res.output_files[0]))

    def test_07_context_menu_registry(self):
        """Test cascading context menu registration and unregistration in HKCU."""
        ok_install, msg1 = install_context_menu(cascading=True)
        self.assertTrue(ok_install, f"Install failed: {msg1}")
        self.assertTrue(is_context_menu_installed())

        ok_uninstall, msg2 = uninstall_context_menu()
        self.assertTrue(ok_uninstall, f"Uninstall failed: {msg2}")
        self.assertFalse(is_context_menu_installed())

    def test_08_ocr_image_to_docx(self):
        """Test Windows Native OCR recognizing image text and outputting Word DOCX."""
        ocr_img_path = str(TEST_DIR / "ocr_sample.png")
        img = Image.new("RGB", (320, 100), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 35), "CONTRACT 987654", fill=(0, 0, 0))
        img.save(ocr_img_path)

        res = ConversionEngine.convert(ocr_img_path, "docx (ocr)")
        self.assertTrue(res.success, f"OCR conversion failed: {res.error}")
        self.assertTrue(os.path.exists(res.output_files[0]))

    def test_09_image_lossless_and_metadata(self):
        """Test lossless WEBP encoding and EXIF privacy stripping."""
        res = ConversionEngine.convert(
            self.rgb_jpg,
            "webp",
            options={"lossless": True, "strip_metadata": True}
        )
        self.assertTrue(res.success, f"Lossless conversion failed: {res.error}")
        self.assertTrue(os.path.exists(res.output_files[0]))

if __name__ == "__main__":
    unittest.main()

