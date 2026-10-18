import os
import sys
import shutil
import winreg
import subprocess
import ctypes
from pathlib import Path

APP_NAME = "FileMorph"
UNINSTALL_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FileMorph"
CONTEXT_KEY_NAME = "FileMorphConvert"

def show_msg(text: str, title: str = "FileMorph Uninstall", flags: int = 0x40) -> int:
    """Uses Windows MessageBox API."""
    return ctypes.windll.user32.MessageBoxW(0, text, title, flags)

def delete_registry_key_tree(root, subkey):
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                    delete_registry_key_tree(root, f"{subkey}\\{child}")
                except OSError:
                    break
        winreg.DeleteKey(root, subkey)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

def remove_context_menu():
    """Cleans up context menu entries from HKCU."""
    extensions = ["*", ".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"]
    targets = ["*"] + [f"SystemFileAssociations\\{ext}" for ext in extensions if ext != "*"]
    for target in targets:
        delete_registry_key_tree(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{target}\\shell\\{CONTEXT_KEY_NAME}")

def remove_shortcuts():
    """Removes Desktop and Start Menu shortcuts."""
    # Desktop
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "FileMorph.lnk"
    if desktop.exists():
        try:
            desktop.unlink()
        except Exception:
            pass

    # Start Menu
    appdata = os.environ.get("APPDATA", "")
    start_menu = Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\FileMorph"
    if start_menu.exists():
        try:
            shutil.rmtree(start_menu, ignore_errors=True)
        except Exception:
            pass

def remove_uninstall_entry():
    """Removes from Windows Installed Apps / Programs and Features."""
    delete_registry_key_tree(winreg.HKEY_CURRENT_USER, UNINSTALL_REG_KEY)

def remove_from_user_path(install_dir: str):
    """Removes install_dir from HKCU\Environment PATH."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                curr_path, _ = winreg.QueryValueEx(key, "Path")
                parts = [p.strip() for p in curr_path.split(";") if p.strip()]
                clean_dir = os.path.normpath(install_dir)
                new_parts = [p for p in parts if os.path.normpath(p) != clean_dir]
                if len(new_parts) != len(parts):
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, ";".join(new_parts))
            except FileNotFoundError:
                pass
    except Exception:
        pass

def main():
    # Prompt confirmation (MB_YESNO = 0x04, MB_ICONQUESTION = 0x20)
    ret = show_msg(
        "Are you sure you want to completely remove FileMorph and all of its components?",
        "FileMorph Uninstall",
        0x04 | 0x20
    )
    # IDYES = 6
    if ret != 6:
        sys.exit(0)

    install_dir = str(Path(__file__).resolve().parent)

    # 1. Clean registry context menu
    remove_context_menu()

    # 2. Remove shortcuts
    remove_shortcuts()

    # 3. Remove Windows Installed Apps entry
    remove_uninstall_entry()

    # 4. Remove from user PATH
    remove_from_user_path(install_dir)

    # 5. Show success message
    show_msg(
        "FileMorph was successfully removed from your computer.",
        "Uninstall Complete",
        0x40  # MB_ICONINFORMATION
    )

    # 6. Schedule directory removal in background after process exits
    cmd = f'cmd /c "ping 127.0.0.1 -n 2 > nul & rd /s /q \\"{install_dir}\\""'
    subprocess.Popen(cmd, shell=True, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    sys.exit(0)

if __name__ == "__main__":
    main()
