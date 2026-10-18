import os
import sys
import argparse
import subprocess
import winsound
from pathlib import Path
from typing import List

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
            # Highlight newly converted file in Windows Explorer
            subprocess.run(f'explorer /select,"{os.path.abspath(output_file)}"', shell=True)
        except Exception:
            pass

def run_cli():
    parser = argparse.ArgumentParser(
        description="FileMorph: Powerful Document and Image File Type Converter for Windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch GUI:
  filemorph
  filemorph document.pdf

  # Quick 1-click headless conversion:
  filemorph document.pdf --to docx --headless --notify
  filemorph photo.jpg --to webp --lossless --notify
  filemorph scanned_receipt.png --to "docx (ocr)" --notify

  # Manage Windows Explorer Context Menu:
  filemorph --install-menu
  filemorph --uninstall-menu
        """
    )

    parser.add_argument("files", nargs="*", help="File path(s) to convert")
    parser.add_argument("--to", dest="target_format", help="Target format (e.g. docx, pdf, png, webp, jpg, 'docx (ocr)')")
    parser.add_argument("--outdir", dest="output_dir", help="Output directory")
    parser.add_argument("--quality", type=int, default=90, help="Image quality (1-100) for JPEG and WEBP")
    parser.add_argument("--dpi", type=int, default=200, help="DPI resolution for PDF-to-image rendering")
    parser.add_argument("--lossless", action="store_true", help="Enable lossless compression for WEBP/PNG")
    parser.add_argument("--preserve-exif", action="store_true", help="Preserve EXIF metadata instead of stripping for privacy")
    parser.add_argument("--merge", action="store_true", help="Merge multiple images into a single PDF")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode without showing GUI")
    parser.add_argument("--notify", action="store_true", help="Provide visual completion feedback and highlight in Explorer")

    # Context menu actions
    parser.add_argument("--install-menu", action="store_true", help="Register context menu in Windows Explorer")
    parser.add_argument("--uninstall-menu", action="store_true", help="Remove context menu from Windows Explorer")
    parser.add_argument("--menu-status", action="store_true", help="Check context menu installation status")

    args = parser.parse_args()

    # Handle Context Menu flags
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

    # If target_format is provided or headless flag is set, run headless conversion
    if args.target_format or args.headless:
        if not args.files:
            print("Error: No files specified for conversion.")
            sys.exit(1)

        norm_target = normalize_extension(args.target_format or "")
        if not norm_target:
            print("Error: Target format (--to) is required for headless conversion.")
            sys.exit(1)

        options = {
            "quality": args.quality,
            "dpi": args.dpi,
            "lossless": args.lossless,
            "strip_metadata": not args.preserve_exif,
            "output_dir": args.output_dir
        }

        print(f"[*] Starting conversion to {norm_target.upper()}...")

        if norm_target == "pdf" and args.merge and len(args.files) > 1:
            out_folder = Path(args.output_dir) if args.output_dir else Path(args.files[0]).parent
            merged_pdf = str(out_folder / f"{Path(args.files[0]).stem}_merged.pdf")
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
                    print(f"[+] Converted: {f} -> {', '.join(res.output_files)} ({res.duration_seconds}s)")
                else:
                    errors.append(f"{Path(f).name}: {res.error}")
                    print(f"[-] Failed: {f} - {res.error}")

            if errors and args.notify:
                show_windows_alert("FileMorph Conversion Error", "\n".join(errors), is_error=True)
            elif last_created and args.notify:
                notify_completion(last_created)

            print(f"Done. {success}/{len(args.files)} files converted successfully.")
        return

    # Otherwise, launch modern GUI
    from .gui.app import launch_gui
    launch_gui(initial_files=args.files)
