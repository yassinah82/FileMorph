# FileMorph — Windows Universal File Type Converter & Shell Extension

> [!IMPORTANT]
> ### 🤖 100% Fully AI-Made Project
> **This entire repository and application was autonomously conceived, architected, coded, and built by AI.**
> From the conversion pipelines, safe Windows COM process lifecycles, and Native Windows Media OCR integration, to the CustomTkinter GUI, Windows Registry context menu extensions, end-to-end integration tests, and standalone Setup Wizard installer — every line was created using **Google DeepMind's Antigravity AI**.

**FileMorph** is a high-performance Windows desktop application and Shell extension for seamless file conversions directly from the Windows Explorer context menu or a standalone UI.

---

## 🚀 Supported Conversions & Capabilities

| Source Format | Target Format | Engine / Library | Technical Highlights |
| :--- | :--- | :--- | :--- |
| **PowerPoint (PPTX / PPT)** | **PDF** | `pywin32` / MS PowerPoint COM | Pixel-perfect presentation export to PDF with clean COM lifecycle handling. |
| **PDF** | **DOCX / DOC** | `pdf2docx` | High-fidelity table, paragraph, margin, and font extraction. |
| **PDF** | **Split PDF / Page Extraction** | `PyMuPDF` (`pymupdf`) | Instant lossless splitting into single pages or custom ranges (e.g. `1-3, 5, 8-10`). |
| **Multiple PDFs** | **Merge to Single PDF** | `PyMuPDF` (`pymupdf`) | Combine multiple PDFs in custom order into one document, preserving links and vector graphics. |
| **PDF (Scanned) / Images** | **DOCX (with OCR)** | `Windows.Media.Ocr` (`winocr`) | **Native Windows Hardware-Accelerated OCR**. Extracts text from scanned documents directly into formatted Word documents without external Tesseract binaries. |
| **PDF** | **Images (PNG, JPG, WEBP, BMP, TIFF)** | `PyMuPDF` (`pymupdf`) | Multi-page rendering at customizable DPI (100–300 DPI). Self-contained, zero Poppler dependency. |
| **DOCX / DOC** | **PDF** | `pywin32` / MS Word COM | Pixel-perfect native Microsoft Word rendering with safe process lifecycle cleanup (`Quit()` / `Close()`). |
| **Images (JPG, PNG, WEBP, BMP, TIFF, ICO)** | **PDF** | `Pillow` | Single image conversion or **multi-image merge** into a unified multi-page PDF. |
| **Image to Image** (JPG ↔ PNG ↔ WEBP ↔ BMP ↔ TIFF ↔ ICO) | `Pillow` | Automatic Alpha / RGBA composite to RGB (prevents JPEG crash), WEBP lossy/lossless, and quality control. |
| **Image Studio Tools** | **Crop, Resize, Rotate & Flip** | `Pillow` | Aspect-ratio crop (1:1, 16:9, 4:3), Lanczos scaling, 90°/180° rotation, and horizontal/vertical flips. |

---

## 🪟 Native Cascading Windows Explorer Context Menu

FileMorph features a **Cascading Context Menu** with **1-Click Quick Actions** directly in Windows Explorer:

```
Right-Click File (PDF, PPTX, DOCX, PNG, JPG, WEBP, etc.)
 └── FileMorph Converter  ▶
      ├── 🖥️ Open Converter Window...
      ├── 📄 Quick Convert to PDF (Presentations, Documents, Images)
      ├── 📝 Quick Convert to DOCX
      ├── ✂️ Quick Split PDF into Pages
      ├── 🖼️ Quick Convert to PNG (High-Res)
      ├── 🌐 Quick Convert to WEBP (Optimized)
      └── 🔍 Extract Text via OCR to DOCX
```

### Context Menu Highlights:
- **Instant 1-Click Execution**: Clicking any Quick Convert option runs headlessly, converts in < 0.2s, plays a subtle chime, and highlights the new file in Windows Explorer (`--notify`).
- **Targeted display**: Registered under `SystemFileAssociations`, only appearing on relevant document and image extensions.
- **No Administrator Privileges Required**: Installed directly in `HKEY_CURRENT_USER` (HKCU).
- **Zero Console Popups**: Uses the compiled native `FileMorph.exe` or `pythonw.exe`.

### 1-Click Context Menu Control:
- **Install / Update**: Double-click [`install_context_menu.bat`](file:///d:/antigravty/install_context_menu.bat)
- **Uninstall**: Double-click [`uninstall_context_menu.bat`](file:///d:/antigravty/uninstall_context_menu.bat)
- **In-App Toggle**: Click the **Context Menu: Enabled** button in the app header.

---

## 🛡️ Privacy & Lossless Optimization Features

1. **EXIF / GPS Metadata Stripping**:
   - Strips sensitive location data, camera serial numbers, and personal timestamps from photos before saving.
2. **Lossless Compression**:
   - WEBP: Lossless WebP encoding with maximum compression effort (`method=6`).
   - PNG: Maximum DEFLATE compression (`compress_level=9`).
   - JPEG: Optimized Huffman tables (`optimize=True`) and progressive rendering.
3. **Smart Alpha Compositing**:
   - Automatically composites transparent PNG/WEBP images onto a clean white background when converting to JPEG/BMP to prevent crashes.

---

## 📦 Standalone Executable Build

FileMorph is bundled with a standalone PyInstaller build pipeline. You can run FileMorph completely standalone without having Python installed on the target machine:

- **Executable Location**: `d:\antigravty\dist\FileMorph\FileMorph.exe`
- **Rebuild Anytime**: Double-click [`build_exe.bat`](file:///d:/antigravty/build_exe.bat)

---

## 🛠️ Project Structure

```
d:\antigravty\
├── assets\
│   ├── icon.ico                     # Multi-resolution Windows app icon (16x16 to 256x256)
│   ├── icon.png                     # Logo asset
│   └── generate_icon.py             # Icon generator script
├── dist_setup\
│   └── FileMorph_Setup.exe          # Single Standalone Setup Wizard Executable (Shareable to any PC)
├── dist\
│   └── FileMorph\
│       └── FileMorph.exe            # Compiled Standalone Windows Application
├── installer\
│   ├── installer_wizard.py          # Setup Wizard GUI source
│   ├── uninstaller.py               # Clean Uninstaller module
│   ├── FileMorph.iss                # Alternative Inno Setup script
│   └── payload.zip                  # Embedded application binaries
├── src\
│   ├── core\
│   │   ├── utils.py                 # Format normalization, alpha-safe blending, extensions
│   │   ├── pdf_converter.py         # PDF -> DOCX & PDF -> Image renderer
│   │   ├── docx_converter.py        # DOCX/DOC -> PDF via Word COM
│   │   ├── image_converter.py       # Image -> Image, Multi-image -> PDF, Lossless, EXIF stripping
│   │   ├── ocr_engine.py            # Windows Native OCR (Windows.Media.Ocr)
│   │   └── engine.py                # Unified conversion engine orchestrator
│   ├── gui\
│   │   └── app.py                   # Modern CustomTkinter GUI with OCR & Privacy options
│   ├── context_menu\
│   │   └── installer.py             # Windows Registry cascading context menu manager
│   └── cli.py                       # CLI router supporting headless, notify, and batch actions
├── tests\
│   └── test_conversions.py          # 9-test automated test suite
├── main.py                          # Unified entrypoint (GUI / CLI / Registry)
├── build_installer.py               # Setup Wizard builder script
├── build_installer.bat              # 1-click Setup Wizard Builder
├── build_exe.py                     # Standalone PyInstaller build script
├── build_exe.bat                    # 1-click executable builder
├── install_context_menu.bat         # 1-click Context Menu Installer
├── uninstall_context_menu.bat       # 1-click Context Menu Uninstaller
├── run_filemorph.bat                # 1-click App Launcher
└── requirements.txt                 # Dependencies
```

---

## 💻 CLI Usage Examples

```powershell
# 1. Quick 1-click headless conversions with explorer notification:
python main.py document.pdf --to docx --headless --notify
python main.py photo.jpg --to webp --lossless --notify
python main.py scan.png --to "docx (ocr)" --notify

# 2. Merge multiple photos into one single PDF:
python main.py page1.jpg page2.jpg page3.png --to pdf --merge

# 3. Manage Windows Explorer Context Menu:
python main.py --install-menu
python main.py --uninstall-menu
python main.py --menu-status
```
