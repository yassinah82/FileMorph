import os
import sys
import winreg
from pathlib import Path
from typing import List, Tuple, Dict

KEY_NAME = "FileMorphConvert"
ROOT_MENU_LABEL = "FileMorph Converter"

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
        # pythonw "main.py" "%1" ...
        if sub_args:
            return f'"{launcher}" {script_arg} "%1" {sub_args}'
        return f'"{launcher}" {script_arg} "%1"'
    else:
        # FileMorph.exe "%1" ...
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
            {"key": "ToDocxOcr", "label": "Extract Text via OCR to DOCX", "args": '--to "docx (ocr)" --headless --notify'}
        ])
    elif ext in (".docx", ".doc"):
        actions.extend([
            {"key": "ToPdf", "label": "Quick Convert to PDF", "args": "--to pdf --headless --notify"}
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

def install_context_menu(cascading: bool = True) -> Tuple[bool, str]:
    """
    Registers a modern cascading or direct context menu entry in HKCU.
    """
    icon_path = get_icon_path()
    supported_extensions = [
        ".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"
    ]

    try:
        for ext in supported_extensions:
            base_key_path = f"Software\\Classes\\SystemFileAssociations\\{ext}\\shell\\{KEY_NAME}"

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base_key_path) as root_key:
                winreg.SetValueEx(root_key, "MUIVerb", 0, winreg.REG_SZ, ROOT_MENU_LABEL)
                if icon_path:
                    winreg.SetValueEx(root_key, "Icon", 0, winreg.REG_SZ, icon_path)

                if cascading:
                    # Windows Cascading Submenu pattern
                    winreg.SetValueEx(root_key, "SubCommands", 0, winreg.REG_SZ, "")
                else:
                    winreg.SetValueEx(root_key, "", 0, winreg.REG_SZ, "Change File Type...")

            if cascading:
                # Add sub-actions under 'shell' subkey
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
                # Direct single action
                cmd_key_path = f"{base_key_path}\\command"
                cmd_str = format_command()
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cmd_key_path) as cmd_key:
                    winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd_str)

        return True, "Cascading context menu successfully installed with 1-click Quick Convert actions."
    except Exception as e:
        return False, f"Failed to register context menu: {e}"

def uninstall_context_menu() -> Tuple[bool, str]:
    """
    Completely removes all context menu entries from HKCU.
    """
    supported_extensions = [
        "*", ".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"
    ]
    targets = ["*"] + [f"SystemFileAssociations\\{ext}" for ext in supported_extensions if ext != "*"]
    removed_count = 0

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
