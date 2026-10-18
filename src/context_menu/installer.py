import os
import sys
import winreg
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict

KEY_NAME = "FileMorphConvert"
ROOT_MENU_LABEL = "FileMorph Converter"
WIN11_OVERRIDE_KEY = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32"

SUPPORTED_EXTENSIONS = [
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"
]

def is_windows_11() -> bool:
    """Returns True if the operating system is Windows 11 (Build >= 22000)."""
    try:
        return sys.getwindowsversion().build >= 22000
    except Exception:
        return False

def is_win11_main_menu_enabled() -> bool:
    """Checks if the Windows 11 top-level main context menu override is active in HKCU."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN11_OVERRIDE_KEY, 0, winreg.KEY_READ):
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

def restart_explorer():
    """Restarts Windows Explorer to apply context menu changes immediately."""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Stop-Process -Name explorer -Force"],
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass

def enable_win11_main_menu(restart_exp: bool = True) -> Tuple[bool, str]:
    """
    Enables FileMorph on the Windows 11 main (top-level) right-click menu,
    bypassing the 'Show more options' (Shift+F10) screen.
    """
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN11_OVERRIDE_KEY) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
        if restart_exp:
            restart_explorer()
        return True, "Windows 11 main context menu successfully enabled. FileMorph is now visible directly on right-click."
    except Exception as e:
        return False, f"Failed to enable Windows 11 main menu: {e}"

def disable_win11_main_menu(restart_exp: bool = True) -> Tuple[bool, str]:
    """Restores default Windows 11 truncated context menu."""
    try:
        base_clsid = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}"
        delete_key_tree(winreg.HKEY_CURRENT_USER, base_clsid)
        if restart_exp:
            restart_explorer()
        return True, "Restored default Windows 11 context menu."
    except Exception as e:
        return False, f"Failed to restore default Windows 11 context menu: {e}"

def get_installed_exe_or_python() -> Tuple[str, str]:
    """
    Returns (executable, script_arg).
    If standalone FileMorph.exe exists in dist, use it directly (0-python dependency).
    Otherwise, fallback to pythonw.exe with main.py.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    dist_exe_dir = project_root / "dist" / "FileMorph" / "FileMorph.exe"
    dist_exe_single = project_root / "dist" / "FileMorph.exe"
    if dist_exe_dir.exists():
        return str(dist_exe_dir), ""
    if dist_exe_single.exists():
        return str(dist_exe_single), ""

    # Pythonw fallback
    exe_path = Path(sys.executable)
    pythonw = exe_path.with_name("pythonw.exe")
    launcher = str(pythonw) if pythonw.exists() else str(exe_path)
    main_script = str(project_root / "main.py")
    return launcher, f'"{main_script}"'

def get_icon_path() -> str:
    """Returns icon path if available, or python.exe icon."""
    current_dir = Path(__file__).resolve().parent.parent.parent
    ico = current_dir / "assets" / "icon.ico"
    if ico.exists():
        return str(ico)
    return sys.executable

def format_command(sub_args: str = "") -> str:
    """Builds shell command string."""
    launcher, script_arg = get_installed_exe_or_python()
    if script_arg:
        if sub_args:
            return f'"{launcher}" {script_arg} "%1" {sub_args}'
        return f'"{launcher}" {script_arg} "%1"'
    else:
        if sub_args:
            return f'"{launcher}" "%1" {sub_args}'
        return f'"{launcher}" "%1"'

def get_subactions_for_ext(ext: str) -> List[Dict[str, str]]:
    """Defines contextual cascading quick actions based on file type."""
    ext = ext.lower()
    actions = [
        {"key": "OpenGUI", "label": "Open Converter Window...", "args": ""}
    ]

    if ext == ".pdf":
        actions.extend([
            {"key": "ToDocx", "label": "Quick Convert to DOCX", "args": "--to docx --headless --notify"},
            {"key": "ToPng", "label": "Quick Convert to PNG (High-Res)", "args": "--to png --dpi 200 --headless --notify"},
            {"key": "ToWebp", "label": "Quick Convert to WEBP", "args": "--to webp --headless --notify"},
            {"key": "SplitPdf", "label": "Quick Split PDF into Pages", "args": "--split-pdf --headless --notify"},
            {"key": "ToDocxOcr", "label": "Extract Text via OCR to DOCX", "args": '--to "docx (ocr)" --headless --notify'}
        ])
    elif ext in (".pptx", ".ppt"):
        actions.extend([
            {"key": "ToPdf", "label": "Quick Convert Presentation to PDF", "args": "--to pdf --headless --notify"}
        ])
    elif ext in (".docx", ".doc"):
        actions.extend([
            {"key": "ToPdf", "label": "Quick Convert Document to PDF", "args": "--to pdf --headless --notify"}
        ])
    else:
        # Image formats
        actions.extend([
            {"key": "ToPdf", "label": "Quick Convert to PDF", "args": "--to pdf --headless --notify"},
            {"key": "ToPng", "label": "Quick Convert to PNG", "args": "--to png --headless --notify"},
            {"key": "ToJpg", "label": "Quick Convert to JPG", "args": "--to jpg --quality 90 --headless --notify"},
            {"key": "ToWebp", "label": "Quick Convert to WEBP (Optimized)", "args": "--to webp --quality 85 --headless --notify"},
            {"key": "ToDocxOcr", "label": "Extract Text via OCR to DOCX", "args": '--to "docx (ocr)" --headless --notify'}
        ])

    return actions

def install_context_menu(cascading: bool = True, enable_win11_direct: bool = True) -> Tuple[bool, str]:
    """
    Registers a modern cascading context menu entry in HKCU.
    Optionally activates the Windows 11 top-level main context menu direct view.
    """
    icon_path = get_icon_path()

    try:
        for ext in SUPPORTED_EXTENSIONS:
            base_key_path = f"Software\\Classes\\SystemFileAssociations\\{ext}\\shell\\{KEY_NAME}"

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base_key_path) as root_key:
                winreg.SetValueEx(root_key, "MUIVerb", 0, winreg.REG_SZ, ROOT_MENU_LABEL)
                if icon_path:
                    winreg.SetValueEx(root_key, "Icon", 0, winreg.REG_SZ, icon_path)

                if cascading:
                    winreg.SetValueEx(root_key, "SubCommands", 0, winreg.REG_SZ, "")
                else:
                    winreg.SetValueEx(root_key, "", 0, winreg.REG_SZ, "Change File Type...")

            if cascading:
                actions = get_subactions_for_ext(ext)
                for act in actions:
                    sub_key_path = f"{base_key_path}\\shell\\{act['key']}"
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_key_path) as sub_key:
                        winreg.SetValueEx(sub_key, "MUIVerb", 0, winreg.REG_SZ, act["label"])
                        if icon_path:
                            winreg.SetValueEx(sub_key, "Icon", 0, winreg.REG_SZ, icon_path)

                    cmd_key_path = f"{sub_key_path}\\command"
                    cmd_str = format_command(act["args"])
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cmd_key_path) as cmd_key:
                        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd_str)
            else:
                cmd_key_path = f"{base_key_path}\\command"
                cmd_str = format_command()
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cmd_key_path) as cmd_key:
                    winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd_str)

        # On Windows 11, enable direct top-level main right click
        if is_windows_11() and enable_win11_direct:
            enable_win11_main_menu(restart_exp=True)

        return True, "Cascading context menu successfully installed on Windows 11 main right-click menu."
    except Exception as e:
        return False, f"Failed to register context menu: {e}"

def delete_key_tree(root, subkey):
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                    delete_key_tree(root, f"{subkey}\\{child}")
                except OSError:
                    break
        winreg.DeleteKey(root, subkey)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

def uninstall_context_menu() -> Tuple[bool, str]:
    """Completely removes all context menu entries from HKCU."""
    targets = ["*"] + [f"SystemFileAssociations\\{ext}" for ext in SUPPORTED_EXTENSIONS]
    removed_count = 0

    for target in targets:
        key_path = f"Software\\Classes\\{target}\\shell\\{KEY_NAME}"
        if delete_key_tree(winreg.HKEY_CURRENT_USER, key_path):
            removed_count += 1

    return True, f"Context menu entries cleanly removed ({removed_count} keys removed)."

def is_context_menu_installed() -> bool:
    """Checks if the context menu key exists in HKCU."""
    try:
        test_path = f"Software\\Classes\\SystemFileAssociations\\.pdf\\shell\\{KEY_NAME}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, test_path, 0, winreg.KEY_READ):
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
