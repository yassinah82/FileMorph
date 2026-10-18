import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
import customtkinter

def build_installer():
    root = Path(__file__).resolve().parent
    installer_dir = root / "installer"
    dist_dir = root / "dist" / "FileMorph"
    dist_setup_dir = root / "dist_setup"
    dist_setup_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print("        FileMorph Standalone Setup Wizard Generator              ")
    print("=================================================================")

    # 1. Verify dist/FileMorph/FileMorph.exe
    exe_file = dist_dir / "FileMorph.exe"
    if not exe_file.exists():
        print("[*] Compiling main application via build_exe.py first...")
        res = subprocess.run([sys.executable, str(root / "build_exe.py")], cwd=str(root))
        if res.returncode != 0:
            print("[-] Error compiling main application.")
            sys.exit(1)

    # 2. Build Uninstaller executable if needed
    uninstaller_exe = installer_dir / "uninstaller.exe"
    if not uninstaller_exe.exists():
        print("[*] Compiling uninstaller.exe...")
        cmd_uninst = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm", "--onefile", "--windowed",
            "--name", "uninstaller",
            "--distpath", str(installer_dir),
            "--workpath", str(root / "build" / "uninstaller"),
            str(installer_dir / "uninstaller.py")
        ]
        res = subprocess.run(cmd_uninst, cwd=str(root))
        if res.returncode != 0:
            print("[-] Warning: Failed to build uninstaller.exe, fallback script will be used.")

    # 3. Create fresh payload.zip
    payload_zip = installer_dir / "payload.zip"
    print(f"[*] Packaging distribution into {payload_zip.name}...")
    with zipfile.ZipFile(payload_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in dist_dir.rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(dist_dir))
    zip_size_mb = os.path.getsize(payload_zip) / (1024 * 1024)
    print(f"[+] Payload compressed: {zip_size_mb:.1f} MB")

    # 4. Compile installer_wizard.py into FileMorph_Setup.exe
    print("[*] Compiling FileMorph_Setup.exe via PyInstaller...")
    icon_path = root / "assets" / "icon.ico"
    ctk_path = Path(customtkinter.__file__).parent

    cmd_installer = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "FileMorph_Setup",
        f"--icon={icon_path}",
        "--distpath", str(dist_setup_dir),
        "--workpath", str(root / "build" / "installer"),
        # Embedded payload and assets
        f"--add-data={payload_zip};.",
        f"--add-data={uninstaller_exe};.",
        f"--add-data={root / 'assets'};assets/",
        f"--add-data={ctk_path};customtkinter/",
        # Hidden imports
        "--hidden-import=customtkinter",
        "--hidden-import=win32com",
        "--hidden-import=pythoncom",
        str(installer_dir / "installer_wizard.py")
    ]

    res = subprocess.run(cmd_installer, cwd=str(root))
    if res.returncode == 0:
        setup_exe = dist_setup_dir / "FileMorph_Setup.exe"
        sz_mb = os.path.getsize(setup_exe) / (1024 * 1024)
        print("\n=================================================================")
        print(" [SUCCESS] Setup Wizard Executable Created Successfully!")
        print(f" Location: {setup_exe}")
        print(f" Size: {sz_mb:.1f} MB (100% self-contained standalone installer)")
        print("=================================================================")
    else:
        print(f"[-] Installer compilation failed with exit code {res.returncode}")
        sys.exit(1)

    # 5. Check Inno Setup compiler if available
    iscc_candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe"
    ]
    iscc_bin = next((p for p in iscc_candidates if os.path.exists(p)), shutil.which("iscc"))
    if iscc_bin:
        print(f"[*] Found Inno Setup at {iscc_bin}. Also compiling FileMorph_InnoSetup.exe...")
        subprocess.run([iscc_bin, str(installer_dir / "FileMorph.iss")])

if __name__ == "__main__":
    build_installer()
