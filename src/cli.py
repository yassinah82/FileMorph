import os
import sys
import argparse
import subprocess
import winsound
from pathlib import Path
from typing import List, Tuple, Optional

from .core import ConversionEngine, normalize_extension, OCREngine
from .context_menu.installer import install_context_menu, uninstall_context_menu, is_context_menu_installed

def show_windows_alert(title: str, message: str, is_error: bool = False):
    """Native Windows message dialog."""
    try:
        import ctypes
        icon_flag = 0x10 if is_error else 0x40
        ctypes.windll.user32.MessageBoxW(0, message, title, icon_flag)
    except Exception:
        print(f"[{title}] {message}")

def notify_completion(output_file: str):
    """Gives smooth feedback: plays chime and highlights output file in Explorer."""
    try:
        winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass

    if os.path.exists(output_file):
        try:
            subprocess.run(f'explorer /select,"{os.path.abspath(output_file)}"', shell=True)
        except Exception:
            pass

def parse_crop_box(val: str) -> Optional[Tuple[int, int, int, int]]:
    try:
        parts = [int(p.strip()) for p in val.split(",")]
        if len(parts) == 4:
            return (parts[0], parts[1], parts[2], parts[3])
    except Exception:
        pass
    return None

def parse_resize_dims(val: str) -> Optional[Tuple[Optional[int], Optional[int]]]:
    try:
        if "x" in val.lower():
            w_str, h_str = val.lower().split("x")
            w = int(w_str.strip()) if w_str.strip() else None
            h = int(h_str.strip()) if h_str.strip() else None
            return (w, h)
    except Exception:
        pass
    return None

def run_cli():
    parser = argparse.ArgumentParser(
        description="FileMorph: Universal Document, Presentation, Image Converter & PDF Studio for Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch Modern GUI:
  filemorph
  filemorph document.pdf
  filemorph presentation.pptx

  # PowerPoint & Document to PDF:
  filemorph presentation.pptx --to pdf --headless --notify
  filemorph report.docx --to pdf --headless --notify

  # PDF Split and Merge:
  filemorph large_document.pdf --split-pdf --headless --notify
  filemorph large_document.pdf --page-range "1-3,5" --headless --notify
  filemorph doc1.pdf doc2.pdf doc3.pdf --merge-pdfs --notify

  # Image Crop, Resize, Rotate:
  filemorph photo.jpg --crop-ratio 1:1 --rotate 90 --headless
  filemorph image.png --resize 1920x1080 --to webp --lossless
  filemorph photo.png --rotate 180 --flip-h --to jpg

  # Windows Explorer Context Menu:
  filemorph --install-menu
  filemorph --uninstall-menu
        """
    )

    parser.add_argument("files", nargs="*", help="File path(s) to convert or process")
    parser.add_argument("--to", dest="target_format", help="Target format (e.g. docx, pdf, png, webp, jpg, 'docx (ocr)', 'split_pdf')")
    parser.add_argument("--outdir", dest="output_dir", help="Output directory")

    # Image Transform Flags
    parser.add_argument("--crop", dest="crop_box", help="Crop box in pixels: left,top,right,bottom (e.g. 50,50,400,400)")
    parser.add_argument("--crop-ratio", dest="crop_ratio", help="Center-crop to aspect ratio: 1:1, 16:9, 4:3, 3:2")
    parser.add_argument("--resize", dest="resize_dims", help="Resize dimensions: WIDTHxHEIGHT (e.g. 1920x1080)")
    parser.add_argument("--scale", type=float, dest="resize_scale", help="Resize scale factor (e.g. 0.5 for 50%%, 2.0 for 200%%)")
    parser.add_argument("--rotate", type=float, dest="rotate_angle", help="Rotate angle in degrees (e.g. 90, 180, 270)")
    parser.add_argument("--flip-h", action="store_true", help="Flip image horizontally")
    parser.add_argument("--flip-v", action="store_true", help="Flip image vertically")

    # PDF Operation Flags
    parser.add_argument("--split-pdf", action="store_true", help="Split PDF into individual single-page PDF files")
    parser.add_argument("--page-range", dest="page_range", help="Extract specific page ranges (e.g. '1-3, 5, 8-10')")
    parser.add_argument("--merge-pdfs", action="store_true", help="Merge multiple selected PDF files into one")

    # Quality & Privacy
    parser.add_argument("--quality", type=int, default=90, help="Image quality (1-100) for JPEG and WEBP")
    parser.add_argument("--dpi", type=int, default=200, help="DPI resolution for PDF-to-image rendering")
    parser.add_argument("--lossless", action="store_true", help="Enable lossless compression for WEBP/PNG")
    parser.add_argument("--preserve-exif", action="store_true", help="Preserve EXIF metadata instead of stripping for privacy")
    parser.add_argument("--merge", action="store_true", help="Merge multiple images into a single PDF")

    # Execution controls
    parser.add_argument("--headless", action="store_true", help="Run in headless mode without showing GUI")
    parser.add_argument("--notify", action="store_true", help="Provide visual completion feedback and highlight in Explorer")

    # Context menu actions
    parser.add_argument("--install-menu", action="store_true", help="Register context menu in Windows Explorer")
    parser.add_argument("--uninstall-menu", action="store_true", help="Remove context menu from Windows Explorer")
    parser.add_argument("--menu-status", action="store_true", help="Check context menu installation status")

    args = parser.parse_args()

    # Context Menu Flags
    if args.install_menu:
        ok, msg = install_context_menu(cascading=True)
        print(msg)
        return
    elif args.uninstall_menu:
        ok, msg = uninstall_context_menu()
        print(msg)
        return
    elif args.menu_status:
        installed = is_context_menu_installed()
        print(f"Context menu installed: {installed}")
        return

    # PDF Split Quick Command
    if args.split_pdf or args.page_range:
        if not args.files:
            print("Error: No PDF file specified for splitting.")
            sys.exit(1)
        pdf_file = args.files[0]
        res = ConversionEngine.split_pdf(
            pdf_path=pdf_file,
            output_dir=args.output_dir,
            page_range=args.page_range,
            progress_callback=lambda p, m: print(f"[{int(p*100)}%] {m}")
        )
        if res.success:
            print(f"[+] Split completed: {len(res.output_files)} file(s) created.")
            if args.notify and res.output_files:
                notify_completion(res.output_files[0])
        else:
            print(f"[-] Split error: {res.error}")
            if args.notify:
                show_windows_alert("FileMorph Error", f"Split error: {res.error}", is_error=True)
        return

    # PDF Merge Command
    if (args.merge_pdfs or (args.merge and args.files and all(f.lower().endswith(".pdf") for f in args.files))):
        if len(args.files) < 2:
            print("Error: At least 2 PDF files are required for merging.")
            sys.exit(1)
        out_folder = Path(args.output_dir) if args.output_dir else Path(args.files[0]).parent
        merged_out = str(out_folder / f"{Path(args.files[0]).stem}_merged.pdf")
        res = ConversionEngine.merge_pdfs(
            pdf_paths=args.files,
            output_path=merged_out,
            progress_callback=lambda p, m: print(f"[{int(p*100)}%] {m}")
        )
        if res.success:
            print(f"[+] Successfully merged {len(args.files)} PDFs into: {res.output_files[0]}")
            if args.notify:
                notify_completion(res.output_files[0])
        else:
            print(f"[-] PDF Merge error: {res.error}")
            if args.notify:
                show_windows_alert("FileMorph Error", f"PDF Merge error: {res.error}", is_error=True)
        return

    # If target_format is provided or image transforms or headless flag is set
    has_transforms = any([args.crop_box, args.crop_ratio, args.resize_dims, args.resize_scale, args.rotate_angle, args.flip_h, args.flip_v])

    if args.target_format or args.headless or has_transforms:
        if not args.files:
            print("Error: No files specified for processing.")
            sys.exit(1)

        norm_target = normalize_extension(args.target_format) if args.target_format else normalize_extension(Path(args.files[0]).suffix)

        options = {
            "quality": args.quality,
            "dpi": args.dpi,
            "lossless": args.lossless,
            "strip_metadata": not args.preserve_exif,
            "output_dir": args.output_dir,
            "crop_box": parse_crop_box(args.crop_box) if args.crop_box else None,
            "crop_aspect_ratio": args.crop_ratio,
            "resize_dims": parse_resize_dims(args.resize_dims) if args.resize_dims else None,
            "resize_scale": args.resize_scale,
            "rotate_angle": args.rotate_angle,
            "flip_h": args.flip_h,
            "flip_v": args.flip_v
        }

        print(f"[*] Starting operation (Target: {norm_target.upper()})...")

        if norm_target == "pdf" and args.merge and len(args.files) > 1 and not all(f.lower().endswith(".pdf") for f in args.files):
            out_folder = Path(args.output_dir) if args.output_dir else Path(args.files[0]).parent
            merged_pdf = str(out_folder / f"{Path(args.files[0]).stem}_images_merged.pdf")
            res = ConversionEngine.convert_images_to_single_pdf(
                image_paths=args.files,
                output_path=merged_pdf,
                progress_callback=lambda p, m: print(f"[{int(p*100)}%] {m}")
            )
            if res.success:
                print(f"[+] Merged {len(args.files)} images into: {res.output_files[0]}")
                if args.notify:
                    notify_completion(res.output_files[0])
            else:
                print(f"[-] Merge failed: {res.error}")
                if args.notify:
                    show_windows_alert("FileMorph Error", f"Merge failed: {res.error}", is_error=True)
                sys.exit(1)
        else:
            success = 0
            last_created = None
            errors = []
            for f in args.files:
                res = ConversionEngine.convert(
                    source_path=f,
                    target_format=norm_target,
                    options=options,
                    progress_callback=lambda p, m: print(f"[{int(p*100)}%] {m}")
                )
                if res.success:
                    success += 1
                    last_created = res.output_files[0] if res.output_files else None
                    print(f"[+] Processed: {f} -> {', '.join(res.output_files)} ({res.duration_seconds}s)")
                else:
                    errors.append(f"{Path(f).name}: {res.error}")
                    print(f"[-] Failed: {f} - {res.error}")

            if errors and args.notify:
                show_windows_alert("FileMorph Error", "\n".join(errors), is_error=True)
            elif last_created and args.notify:
                notify_completion(last_created)

            print(f"Done. {success}/{len(args.files)} file(s) processed successfully.")
        return

    # Otherwise, launch modern GUI
    from .gui.app import launch_gui
    launch_gui(initial_files=args.files)
