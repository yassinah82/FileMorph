import os
import sys
import subprocess
from pathlib import Path
import customtkinter

def build():
    root = Path(__file__).resolve().parent
    icon_path = root / "assets" / "icon.ico"
    main_py = root / "main.py"
    ctk_path = Path(customtkinter.__file__).parent

    print("=======================================================")
    print("Building standalone FileMorph.exe via PyInstaller...")
    print("=======================================================")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",             # onedir is vastly faster to launch than onearc/onefile on Windows
        "--windowed",           # GUI mode without console window
        "--name", "FileMorph",
        f"--icon={icon_path}",
        # Bundle CustomTkinter themes and assets
        f"--add-data={ctk_path};customtkinter/",
        f"--add-data={root / 'assets'};assets/",
        # Hidden imports
        "--hidden-import=customtkinter",
        "--hidden-import=pymupdf",
        "--hidden-import=fitz",
        "--hidden-import=pdf2docx",
        "--hidden-import=docx2pdf",
        "--hidden-import=winocr",
        "--hidden-import=winrt",
        "--hidden-import=win32com",
        "--hidden-import=pythoncom",
        "--hidden-import=docx",
        "--hidden-import=PIL",
        str(main_py)
    ]

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(root))
    if result.returncode == 0:
        exe_loc = root / "dist" / "FileMorph" / "FileMorph.exe"
        print("\n=======================================================")
        print(f"Build succeeded! Standalone executable created at:\n{exe_loc}")
        print("=======================================================")
    else:
        print(f"\nBuild failed with exit code {result.returncode}")

if __name__ == "__main__":
    build()
