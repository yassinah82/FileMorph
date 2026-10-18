import os
import sys
import shutil
import zipfile
import threading
import winreg
import subprocess
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_NAME = "FileMorph"
APP_VERSION = "1.0.0"
PUBLISHER = "FileMorph Software"
ESTIMATED_SIZE_KB = 285000

def is_windows_11() -> bool:
    """Returns True if running on Windows 11 (Build >= 22000)."""
    try:
        return sys.getwindowsversion().build >= 22000
    except Exception:
        return False

def enable_win11_main_menu():
    """Enables classic full context menu on Windows 11 so FileMorph appears directly on right-click."""
    try:
        key_path = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
    except Exception:
        pass

def restart_explorer():
    """Restarts explorer.exe so Windows 11 context menu applies immediately."""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Stop-Process -Name explorer -Force"],
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass

def get_bundle_dir() -> Path:
    """Returns the directory of the running script or PyInstaller _MEIPASS."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

def get_default_install_dir() -> str:
    """Default to %LOCALAPPDATA%\\Programs\\FileMorph (Standard modern Windows user install)."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return str(Path(local_app_data) / "Programs" / APP_NAME)
    return str(Path(os.environ.get("USERPROFILE", "C:")) / APP_NAME)

def get_free_space_mb(path: str) -> int:
    """Returns available disk space in MB for the drive containing path."""
    try:
        drive = Path(path).anchor
        if not drive:
            drive = "C:\\"
        usage = shutil.disk_usage(drive)
        return int(usage.free / (1024 * 1024))
    except Exception:
        return 10000

def create_windows_shortcut(target_exe: str, shortcut_path: str, working_dir: str, icon_path: str, desc: str):
    """Creates a Windows .lnk shortcut using WScript.Shell."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = str(target_exe)
        shortcut.WorkingDirectory = str(working_dir)
        shortcut.IconLocation = f"{icon_path},0"
        shortcut.Description = desc
        shortcut.save()
        return True
    except Exception:
        try:
            ps_cmd = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{shortcut_path}"); '
                f'$s.TargetPath = "{target_exe}"; '
                f'$s.WorkingDirectory = "{working_dir}"; '
                f'$s.IconLocation = "{icon_path},0"; '
                f'$s.Description = "{desc}"; '
                f'$s.Save()'
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except Exception:
            return False

def register_uninstall_entry(install_dir: str):
    """Registers in Windows Settings > Installed Apps / Programs & Features."""
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FileMorph"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "FileMorph Universal File Converter")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            icon_ico = str(Path(install_dir) / "assets" / "icon.ico")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, icon_ico)
            
            uninstall_exe = str(Path(install_dir) / "Uninstall.exe")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}"')
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, ESTIMATED_SIZE_KB)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    except Exception as e:
        print(f"Failed to register uninstall entry: {e}")

def add_to_user_path(install_dir: str):
    """Adds install_dir to HKCU Environment Path."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                curr_path, reg_type = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                curr_path = ""
                reg_type = winreg.REG_EXPAND_SZ

            parts = [p.strip() for p in curr_path.split(";") if p.strip()]
            clean_dir = os.path.normpath(install_dir)
            if clean_dir not in [os.path.normpath(p) for p in parts]:
                parts.append(clean_dir)
                winreg.SetValueEx(key, "Path", 0, reg_type, ";".join(parts))
    except Exception:
        pass


class SetupWizard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FileMorph Setup")
        self.geometry("640x450")
        self.resizable(False, False)

        bundle_dir = get_bundle_dir()
        icon_path = bundle_dir / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Wizard State
        self.current_step = 0
        self.install_dir = get_default_install_dir()
        self.task_desktop_shortcut = ctk.BooleanVar(value=True)
        self.task_start_shortcut = ctk.BooleanVar(value=True)
        self.task_context_menu = ctk.BooleanVar(value=True)
        self.task_win11_main = ctk.BooleanVar(value=True)
        self.task_add_path = ctk.BooleanVar(value=False)
        self.task_launch_app = ctk.BooleanVar(value=True)

        self._build_layout()
        self._show_step(0)

    def _build_layout(self):
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=0, pady=0)

        self.nav_frame = ctk.CTkFrame(self, height=52, corner_radius=0, fg_color=("gray85", "#1e293b"))
        self.nav_frame.pack(fill="x", side="bottom")

        div = ctk.CTkFrame(self.nav_frame, height=1, fg_color=("gray70", "#334155"))
        div.pack(fill="x", side="top")

        btn_box = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        btn_box.pack(side="right", padx=16, pady=10)

        self.back_btn = ctk.CTkButton(
            btn_box,
            text="< Back",
            width=85,
            command=self._on_back
        )
        self.back_btn.pack(side="left", padx=6)

        self.next_btn = ctk.CTkButton(
            btn_box,
            text="Next >",
            width=85,
            command=self._on_next
        )
        self.next_btn.pack(side="left", padx=6)

        self.cancel_btn = ctk.CTkButton(
            btn_box,
            text="Cancel",
            width=85,
            fg_color=("gray75", "#334155"),
            hover_color=("gray65", "#475569"),
            command=self._on_cancel
        )
        self.cancel_btn.pack(side="left", padx=(10, 0))

    def _clear_content(self):
        for w in self.content_container.winfo_children():
            w.destroy()

    def _show_step(self, step: int):
        self.current_step = step
        self._clear_content()

        if step == 0:
            self._render_welcome_page()
        elif step == 1:
            self._render_location_page()
        elif step == 2:
            self._render_tasks_page()
        elif step == 3:
            self._render_ready_page()
        elif step == 4:
            self._render_installing_page()
        elif step == 5:
            self._render_finish_page()

    # --- Step 0: Welcome Page ---
    def _render_welcome_page(self):
        self.back_btn.configure(state="disabled")
        self.next_btn.configure(state="normal", text="Next >")
        self.cancel_btn.configure(state="normal", text="Cancel")

        sidebar = ctk.CTkFrame(self.content_container, width=170, corner_radius=0, fg_color=("#1d4ed8", "#0f172a"))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand_lbl = ctk.CTkLabel(
            sidebar,
            text="FileMorph",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#ffffff"
        )
        brand_lbl.pack(pady=(40, 4))

        ver_lbl = ctk.CTkLabel(
            sidebar,
            text=f"Version {APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        ver_lbl.pack(pady=(0, 20))

        right = ctk.CTkFrame(self.content_container, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=25, pady=25)

        title = ctk.CTkLabel(
            right,
            text="Welcome to the FileMorph Setup Wizard",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            wraplength=400,
            justify="left"
        )
        title.pack(anchor="w", pady=(10, 15))

        body = (
            "This will install FileMorph on your computer.\n\n"
            "FileMorph provides high-fidelity conversions directly from your Windows Explorer right-click menu:\n"
            "• PowerPoint, Word, and Images to PDF\n"
            "• PDF to Word (DOCX) & High-Res Images\n"
            "• PDF Split and Multi-PDF Merge\n"
            "• Image Studio: Crop, Resize, Rotate & Flip\n"
            "• Hardware-accelerated Windows Native OCR\n"
            "• Main right-click menu integration for Windows 11\n\n"
            "Click Next to continue, or Cancel to exit Setup."
        )
        lbl = ctk.CTkLabel(
            right,
            text=body,
            font=ctk.CTkFont(size=12),
            wraplength=400,
            justify="left"
        )
        lbl.pack(anchor="w")

    # --- Step 1: Destination Location Page ---
    def _render_location_page(self):
        self.back_btn.configure(state="normal")
        self.next_btn.configure(state="normal", text="Next >")

        header = ctk.CTkFrame(self.content_container, height=60, corner_radius=0, fg_color=("gray85", "#1e293b"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        h_title = ctk.CTkLabel(header, text="Select Destination Location", font=ctk.CTkFont(size=14, weight="bold"))
        h_title.pack(anchor="w", padx=20, pady=(10, 2))
        h_sub = ctk.CTkLabel(header, text="Where should FileMorph be installed?", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
        h_sub.pack(anchor="w", padx=20)

        center = ctk.CTkFrame(self.content_container, fg_color="transparent")
        center.pack(fill="both", expand=True, padx=25, pady=20)

        info = ctk.CTkLabel(
            center,
            text="Setup will install FileMorph into the following folder.\nTo continue, click Next. To choose a different folder, click Browse.",
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        info.pack(anchor="w", pady=(0, 12))

        picker_box = ctk.CTkFrame(center, fg_color="transparent")
        picker_box.pack(fill="x", pady=(0, 20))

        self.dir_entry = ctk.CTkEntry(picker_box, width=380)
        self.dir_entry.insert(0, self.install_dir)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_btn = ctk.CTkButton(picker_box, text="Browse...", width=80, command=self._browse_install_dir)
        browse_btn.pack(side="left")

        free_mb = get_free_space_mb(self.install_dir)
        space_info = ctk.CTkLabel(
            center,
            text=f"At least {int(ESTIMATED_SIZE_KB / 1024)} MB of free disk space is required.\nAvailable on selected drive: {free_mb:,} MB",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "#94a3b8"),
            justify="left"
        )
        space_info.pack(anchor="w")

    def _browse_install_dir(self):
        chosen = filedialog.askdirectory(title="Select Destination Folder", initialdir=self.install_dir)
        if chosen:
            self.install_dir = str(Path(chosen) / APP_NAME)
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, self.install_dir)

    # --- Step 2: Select Tasks Page ---
    def _render_tasks_page(self):
        self.back_btn.configure(state="normal")
        self.next_btn.configure(state="normal", text="Next >")

        header = ctk.CTkFrame(self.content_container, height=60, corner_radius=0, fg_color=("gray85", "#1e293b"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        h_title = ctk.CTkLabel(header, text="Select Additional Tasks", font=ctk.CTkFont(size=14, weight="bold"))
        h_title.pack(anchor="w", padx=20, pady=(10, 2))
        h_sub = ctk.CTkLabel(header, text="Which additional tasks should be performed?", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
        h_sub.pack(anchor="w", padx=20)

        center = ctk.CTkFrame(self.content_container, fg_color="transparent")
        center.pack(fill="both", expand=True, padx=25, pady=15)

        t_lbl = ctk.CTkLabel(center, text="Select the additional tasks you would like Setup to perform while installing FileMorph:", font=ctk.CTkFont(size=12))
        t_lbl.pack(anchor="w", pady=(0, 10))

        cb1 = ctk.CTkCheckBox(center, text="Create a Desktop shortcut", variable=self.task_desktop_shortcut)
        cb1.pack(anchor="w", pady=4)

        cb2 = ctk.CTkCheckBox(center, text="Create a Start Menu shortcut", variable=self.task_start_shortcut)
        cb2.pack(anchor="w", pady=4)

        cb3 = ctk.CTkCheckBox(center, text="Enable Windows Explorer Context Menu (Cascading 1-click conversions)", variable=self.task_context_menu)
        cb3.pack(anchor="w", pady=4)

        if is_windows_11():
            cb_win11 = ctk.CTkCheckBox(
                center,
                text="Show directly on Windows 11 main context menu (Bypass 'Show more options')",
                variable=self.task_win11_main
            )
            cb_win11.pack(anchor="w", pady=4)

        cb4 = ctk.CTkCheckBox(center, text="Add FileMorph to User PATH environment variable", variable=self.task_add_path)
        cb4.pack(anchor="w", pady=4)

    # --- Step 3: Ready to Install Page ---
    def _render_ready_page(self):
        self.back_btn.configure(state="normal")
        self.next_btn.configure(state="normal", text="Install")

        header = ctk.CTkFrame(self.content_container, height=60, corner_radius=0, fg_color=("gray85", "#1e293b"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        h_title = ctk.CTkLabel(header, text="Ready to Install", font=ctk.CTkFont(size=14, weight="bold"))
        h_title.pack(anchor="w", padx=20, pady=(10, 2))
        h_sub = ctk.CTkLabel(header, text="Setup is now ready to begin installing FileMorph on your computer.", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
        h_sub.pack(anchor="w", padx=20)

        center = ctk.CTkFrame(self.content_container, fg_color="transparent")
        center.pack(fill="both", expand=True, padx=25, pady=15)

        summary_box = ctk.CTkTextbox(center, height=180, font=ctk.CTkFont(size=12))
        summary_box.pack(fill="both", expand=True)

        tasks_list = []
        if self.task_desktop_shortcut.get():
            tasks_list.append("• Create Desktop shortcut")
        if self.task_start_shortcut.get():
            tasks_list.append("• Create Start Menu shortcut")
        if self.task_context_menu.get():
            tasks_list.append("• Enable Windows Explorer Context Menu")
        if is_windows_11() and self.task_win11_main.get():
            tasks_list.append("• Show directly on Windows 11 main right-click menu")
        if self.task_add_path.get():
            tasks_list.append("• Add to user PATH")

        text = (
            f"Destination Location:\n  {self.install_dir}\n\n"
            f"Additional Tasks:\n  " + "\n  ".join(tasks_list) + "\n\n"
            "Click Install to proceed with the installation."
        )
        summary_box.insert("1.0", text)
        summary_box.configure(state="disabled")

    # --- Step 4: Installing Page ---
    def _render_installing_page(self):
        self.back_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")

        header = ctk.CTkFrame(self.content_container, height=60, corner_radius=0, fg_color=("gray85", "#1e293b"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        h_title = ctk.CTkLabel(header, text="Installing...", font=ctk.CTkFont(size=14, weight="bold"))
        h_title.pack(anchor="w", padx=20, pady=(10, 2))
        h_sub = ctk.CTkLabel(header, text="Please wait while Setup installs FileMorph on your computer.", font=ctk.CTkFont(size=11), text_color=("gray40", "#94a3b8"))
        h_sub.pack(anchor="w", padx=20)

        center = ctk.CTkFrame(self.content_container, fg_color="transparent")
        center.pack(fill="both", expand=True, padx=25, pady=40)

        self.install_status_lbl = ctk.CTkLabel(center, text="Extracting files...", font=ctk.CTkFont(size=12))
        self.install_status_lbl.pack(anchor="w", pady=(0, 8))

        self.install_progress = ctk.CTkProgressBar(center)
        self.install_progress.pack(fill="x", pady=(0, 15))
        self.install_progress.set(0.0)

        threading.Thread(target=self._perform_installation, daemon=True).start()

    def _perform_installation(self):
        try:
            target_path = Path(self.install_dir).resolve()
            target_path.mkdir(parents=True, exist_ok=True)

            bundle_dir = get_bundle_dir()
            payload_zip = bundle_dir / "payload.zip"

            if not payload_zip.exists():
                payload_zip = Path(__file__).resolve().parent / "payload.zip"

            if not payload_zip.exists():
                raise FileNotFoundError(f"Installer payload not found: {payload_zip}")

            # 1. Extract ZIP payload
            with zipfile.ZipFile(payload_zip, 'r') as z:
                total_files = len(z.infolist())
                for idx, item in enumerate(z.infolist()):
                    z.extract(item, target_path)
                    if idx % 50 == 0:
                        pct = (idx / total_files) * 0.70
                        self._update_progress(pct, f"Extracting: {item.filename}")

            self._update_progress(0.75, "Copying uninstaller...")

            # 2. Copy Uninstaller
            uninstaller_src = bundle_dir / "uninstaller.exe"
            if not uninstaller_src.exists():
                uninstaller_src = Path(__file__).resolve().parent / "uninstaller.exe"

            target_uninstaller = target_path / "Uninstall.exe"
            if uninstaller_src.exists():
                shutil.copy2(uninstaller_src, target_uninstaller)
            else:
                py_src = Path(__file__).resolve().parent / "uninstaller.py"
                if py_src.exists():
                    shutil.copy2(py_src, target_path / "uninstaller.py")

            # 3. Create Shortcuts
            target_exe = target_path / "FileMorph.exe"
            icon_ico = target_path / "assets" / "icon.ico"
            if not icon_ico.exists():
                icon_ico = target_exe

            if self.task_desktop_shortcut.get():
                self._update_progress(0.80, "Creating Desktop shortcut...")
                desktop_lnk = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "FileMorph.lnk"
                create_windows_shortcut(
                    target_exe=str(target_exe),
                    shortcut_path=str(desktop_lnk),
                    working_dir=str(target_path),
                    icon_path=str(icon_ico),
                    desc="FileMorph Universal File Converter"
                )

            if self.task_start_shortcut.get():
                self._update_progress(0.85, "Creating Start Menu shortcut...")
                start_folder = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\FileMorph"
                start_folder.mkdir(parents=True, exist_ok=True)
                create_windows_shortcut(
                    target_exe=str(target_exe),
                    shortcut_path=str(start_folder / "FileMorph.lnk"),
                    working_dir=str(target_path),
                    icon_path=str(icon_ico),
                    desc="FileMorph Universal File Converter"
                )
                if target_uninstaller.exists():
                    create_windows_shortcut(
                        target_exe=str(target_uninstaller),
                        shortcut_path=str(start_folder / "Uninstall FileMorph.lnk"),
                        working_dir=str(target_path),
                        icon_path=str(target_uninstaller),
                        desc="Uninstall FileMorph"
                    )

            # 4. Context Menu Integration
            if self.task_context_menu.get():
                self._update_progress(0.90, "Registering Windows Context Menu...")
                try:
                    subprocess.run(
                        [str(target_exe), "--install-menu"],
                        cwd=str(target_path),
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=15
                    )
                except Exception:
                    pass

            # 5. Windows 11 Main Menu Direct Toggle
            if is_windows_11() and self.task_win11_main.get():
                self._update_progress(0.94, "Enabling Windows 11 main context menu...")
                enable_win11_main_menu()

            # 6. User PATH
            if self.task_add_path.get():
                add_to_user_path(str(target_path))

            # 7. Windows Installed Apps entry
            self._update_progress(0.98, "Registering in Windows Installed Apps...")
            register_uninstall_entry(str(target_path))

            self._update_progress(1.0, "Installation complete.")
            self.after(300, lambda: self._show_step(5))

        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Installation Error", f"Installation failed:\n{e}"))
            self.after(0, self._on_cancel)

    def _update_progress(self, pct: float, msg: str):
        self.after(0, lambda: self._apply_progress(pct, msg))

    def _apply_progress(self, pct: float, msg: str):
        self.install_progress.set(pct)
        if len(msg) > 55:
            msg = msg[:52] + "..."
        self.install_status_lbl.configure(text=msg)

    # --- Step 5: Finished Page ---
    def _render_finish_page(self):
        self.back_btn.configure(state="disabled")
        self.next_btn.configure(state="normal", text="Finish", command=self._on_finish)
        self.cancel_btn.configure(state="disabled")

        sidebar = ctk.CTkFrame(self.content_container, width=170, corner_radius=0, fg_color=("#059669", "#064e3b"))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand_lbl = ctk.CTkLabel(
            sidebar,
            text="FileMorph",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#ffffff"
        )
        brand_lbl.pack(pady=(40, 4))

        ver_lbl = ctk.CTkLabel(
            sidebar,
            text="Setup Complete",
            font=ctk.CTkFont(size=12),
            text_color="#a7f3d0"
        )
        ver_lbl.pack(pady=(0, 20))

        right = ctk.CTkFrame(self.content_container, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=25, pady=25)

        title = ctk.CTkLabel(
            right,
            text="Completing the FileMorph Setup Wizard",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            wraplength=400,
            justify="left"
        )
        title.pack(anchor="w", pady=(10, 15))

        body = (
            "FileMorph has been successfully installed on your computer.\n\n"
            "FileMorph is now ready to use from your Desktop, Start Menu, "
            "or directly on your Windows 11 main right-click menu."
        )
        lbl = ctk.CTkLabel(right, text=body, font=ctk.CTkFont(size=12), wraplength=400, justify="left")
        lbl.pack(anchor="w", pady=(0, 20))

        cb = ctk.CTkCheckBox(right, text="Launch FileMorph now", variable=self.task_launch_app)
        cb.pack(anchor="w")

    def _on_next(self):
        if self.current_step == 1:
            path_val = self.dir_entry.get().strip()
            if not path_val:
                messagebox.showwarning("Warning", "Please specify a valid destination folder.")
                return
            self.install_dir = path_val

        self._show_step(self.current_step + 1)

    def _on_back(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _on_cancel(self):
        if messagebox.askyesno("Exit Setup", "Are you sure you want to exit FileMorph Setup?"):
            self.destroy()

    def _on_finish(self):
        if is_windows_11() and self.task_win11_main.get():
            restart_explorer()

        if self.task_launch_app.get():
            target_exe = Path(self.install_dir) / "FileMorph.exe"
            if target_exe.exists():
                subprocess.Popen([str(target_exe)], cwd=str(self.install_dir))
        self.destroy()

def main():
    app = SetupWizard()
    app.mainloop()

if __name__ == "__main__":
    main()
