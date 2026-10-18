import os
import sys
import threading
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..core import ConversionEngine, ConversionResult, get_target_formats_for_file, OCREngine
from ..context_menu.installer import is_context_menu_installed, install_context_menu, uninstall_context_menu

# Set CTk appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FileMorphApp(ctk.CTk):
    def __init__(self, initial_files: Optional[List[str]] = None):
        super().__init__()

        self.title("FileMorph - Universal File Converter")
        self.geometry("740x650")
        self.minsize(700, 580)

        # Set Icon if available
        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # State
        self.selected_files: List[str] = [f for f in (initial_files or []) if Path(f).exists()]
        self.is_converting = False
        self.latest_outputs: List[str] = []

        self._build_ui()
        self._refresh_file_view()

    def _build_ui(self):
        # Header Frame
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "#1e293b"), height=70)
        header.pack(fill="x", padx=0, pady=0)

        title_label = ctk.CTkLabel(
            header,
            text="FileMorph Converter",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=("gray10", "#f8fafc")
        )
        title_label.pack(side="left", padx=20, pady=16)

        # Context Menu Toggle Button
        self.menu_btn = ctk.CTkButton(
            header,
            text="Context Menu: ...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=30,
            command=self._toggle_context_menu
        )
        self.menu_btn.pack(side="right", padx=20, pady=16)
        self._update_menu_btn_label()

        # Main Container
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.pack(fill="both", expand=True, padx=20, pady=12)

        # 1. Selected Files Section
        file_header_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        file_header_frame.pack(fill="x", pady=(0, 6))

        file_label = ctk.CTkLabel(
            file_header_frame,
            text="Selected Files",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        file_label.pack(side="left")

        btn_box = ctk.CTkFrame(file_header_frame, fg_color="transparent")
        btn_box.pack(side="right")

        add_file_btn = ctk.CTkButton(
            btn_box,
            text="+ Add Files",
            width=90,
            height=28,
            command=self._browse_files
        )
        add_file_btn.pack(side="left", padx=(0, 6))

        clear_btn = ctk.CTkButton(
            btn_box,
            text="Clear",
            width=60,
            height=28,
            fg_color=("gray75", "#334155"),
            hover_color=("gray65", "#475569"),
            command=self._clear_files
        )
        clear_btn.pack(side="left")

        # Scrollable file list textbox
        self.file_listbox = ctk.CTkTextbox(
            self.main_content,
            height=95,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.file_listbox.pack(fill="x", pady=(0, 12))
        self.file_listbox.configure(state="disabled")

        # 2. Conversion Configuration Frame
        config_frame = ctk.CTkFrame(self.main_content, corner_radius=10, fg_color=("gray90", "#0f172a"))
        config_frame.pack(fill="x", pady=(0, 12), padx=0, ipadx=10, ipady=10)

        # Target format selector row
        format_row = ctk.CTkFrame(config_frame, fg_color="transparent")
        format_row.pack(fill="x", padx=15, pady=6)

        format_label = ctk.CTkLabel(
            format_row,
            text="Convert to:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=100,
            anchor="w"
        )
        format_label.pack(side="left")

        self.format_dropdown = ctk.CTkOptionMenu(
            format_row,
            values=["Select a file first..."],
            width=180,
            command=self._on_format_changed
        )
        self.format_dropdown.pack(side="left", padx=10)

        self.format_hint = ctk.CTkLabel(
            format_row,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94a3b8")
        )
        self.format_hint.pack(side="left", padx=10)

        # Dynamic Options Frame 1 (DPI / Quality / Merging)
        self.options_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        self.options_frame.pack(fill="x", padx=15, pady=4)

        # Merge images checkbox
        self.merge_images_var = ctk.BooleanVar(value=False)
        self.merge_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Merge all selected images into a single multi-page PDF",
            variable=self.merge_images_var
        )

        # DPI selector (for PDF -> Image)
        self.dpi_label = ctk.CTkLabel(self.options_frame, text="DPI Quality:")
        self.dpi_var = ctk.StringVar(value="200 DPI (High)")
        self.dpi_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["100 DPI (Compact)", "150 DPI (Standard)", "200 DPI (High)", "300 DPI (Ultra)"],
            variable=self.dpi_var,
            width=160
        )

        # Quality slider (for JPEG / WEBP)
        self.quality_label = ctk.CTkLabel(self.options_frame, text="Quality: 90%")
        self.quality_slider = ctk.CTkSlider(
            self.options_frame,
            from_=50,
            to=100,
            number_of_steps=50,
            command=self._on_quality_slider_change
        )
        self.quality_slider.set(90)

        # Lossless compression checkbox
        self.lossless_var = ctk.BooleanVar(value=False)
        self.lossless_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Lossless Compression",
            variable=self.lossless_var
        )

        # Privacy / Advanced Row
        privacy_row = ctk.CTkFrame(config_frame, fg_color="transparent")
        privacy_row.pack(fill="x", padx=15, pady=4)

        self.strip_exif_var = ctk.BooleanVar(value=True)
        self.strip_exif_checkbox = ctk.CTkCheckBox(
            privacy_row,
            text="Strip EXIF / GPS Metadata (Privacy)",
            variable=self.strip_exif_var
        )
        self.strip_exif_checkbox.pack(side="left")

        # 3. Output Directory Frame
        out_row = ctk.CTkFrame(config_frame, fg_color="transparent")
        out_row.pack(fill="x", padx=15, pady=(8, 4))

        out_label = ctk.CTkLabel(
            out_row,
            text="Output Directory:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=120,
            anchor="w"
        )
        out_label.pack(side="left")

        self.out_dir_entry = ctk.CTkEntry(
            out_row,
            placeholder_text="Same directory as source files",
            width=360
        )
        self.out_dir_entry.pack(side="left", padx=10, fill="x", expand=True)

        browse_out_btn = ctk.CTkButton(
            out_row,
            text="Browse...",
            width=80,
            fg_color=("gray75", "#334155"),
            hover_color=("gray65", "#475569"),
            command=self._browse_output_dir
        )
        browse_out_btn.pack(side="left")

        # 4. Progress and Conversion Action
        action_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        action_frame.pack(fill="x", pady=10)

        self.progress_bar = ctk.CTkProgressBar(action_frame)
        self.progress_bar.pack(fill="x", pady=(0, 6))
        self.progress_bar.set(0.0)

        self.status_label = ctk.CTkLabel(
            action_frame,
            text="Ready to convert",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "#94a3b8")
        )
        self.status_label.pack(side="left")

        self.show_folder_btn = ctk.CTkButton(
            action_frame,
            text="Open in Explorer",
            width=130,
            height=32,
            fg_color=("gray70", "#334155"),
            state="disabled",
            command=self._open_output_folder
        )
        self.show_folder_btn.pack(side="right", padx=(10, 0))

        self.convert_btn = ctk.CTkButton(
            action_frame,
            text="Start Conversion",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            height=36,
            width=160,
            command=self._start_conversion_thread
        )
        self.convert_btn.pack(side="right")

    def _update_menu_btn_label(self):
        installed = is_context_menu_installed()
        if installed:
            self.menu_btn.configure(
                text="Context Menu: Enabled",
                fg_color="#059669",
                hover_color="#047857"
            )
        else:
            self.menu_btn.configure(
                text="Enable in Context Menu",
                fg_color="#2563eb",
                hover_color="#1d4ed8"
            )

    def _toggle_context_menu(self):
        installed = is_context_menu_installed()
        if installed:
            ok, msg = uninstall_context_menu()
            if ok:
                messagebox.showinfo("Context Menu", "Right-click context menu has been removed.")
        else:
            ok, msg = install_context_menu(cascading=True)
            if ok:
                messagebox.showinfo(
                    "Context Menu",
                    "Right-click cascading context menu has been enabled!\n"
                    "You can now right-click any supported file in Explorer for 1-click Quick Conversions."
                )
        self._update_menu_btn_label()

    def _browse_files(self):
        files = filedialog.askopenfilenames(
            title="Select Files to Convert",
            filetypes=[
                ("All Supported Files", "*.pdf;*.docx;*.doc;*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tiff"),
                ("PDF Documents", "*.pdf"),
                ("Word Documents", "*.docx;*.doc"),
                ("Images", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tiff;*.ico"),
                ("All Files", "*.*")
            ]
        )
        if files:
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self._refresh_file_view()

    def _clear_files(self):
        self.selected_files.clear()
        self._refresh_file_view()

    def _refresh_file_view(self):
        self.file_listbox.configure(state="normal")
        self.file_listbox.delete("1.0", "end")

        if not self.selected_files:
            self.file_listbox.insert("1.0", "No files selected. Click '+ Add Files' or right-click any file in Windows Explorer.")
            self.format_dropdown.configure(values=["Select a file first..."])
            self.format_dropdown.set("Select a file first...")
            self.convert_btn.configure(state="disabled")
            self._hide_dynamic_options()
        else:
            lines = [f"• {f} ({self._format_file_size(f)})" for f in self.selected_files]
            self.file_listbox.insert("1.0", "\n".join(lines))
            self.convert_btn.configure(state="normal")
            self._update_supported_formats()

        self.file_listbox.configure(state="disabled")

    def _format_file_size(self, path: str) -> str:
        try:
            sz = os.path.getsize(path)
            if sz < 1024:
                return f"{sz} B"
            elif sz < 1024 * 1024:
                return f"{sz / 1024:.1f} KB"
            return f"{sz / (1024 * 1024):.1f} MB"
        except Exception:
            return "Unknown size"

    def _update_supported_formats(self):
        if not self.selected_files:
            return

        first_file = self.selected_files[0]
        targets = get_target_formats_for_file(first_file, include_ocr=OCREngine.is_available())

        targets_upper = [t.upper() for t in targets]
        if targets_upper:
            self.format_dropdown.configure(values=targets_upper)
            self.format_dropdown.set(targets_upper[0])
            self._on_format_changed(targets_upper[0])
        else:
            self.format_dropdown.configure(values=["Unsupported File Type"])
            self.format_dropdown.set("Unsupported File Type")
            self.convert_btn.configure(state="disabled")

    def _hide_dynamic_options(self):
        for widget in (self.merge_checkbox, self.dpi_label, self.dpi_menu, self.quality_label, self.quality_slider, self.lossless_checkbox):
            widget.pack_forget()

    def _on_format_changed(self, choice: str):
        choice = choice.lower()
        self._hide_dynamic_options()

        first_file = self.selected_files[0] if self.selected_files else ""
        first_ext = Path(first_file).suffix.lower() if first_file else ""

        # OCR option
        if "ocr" in choice:
            self.format_hint.configure(text="Uses Windows Native OCR to extract text into an editable Word document")
            return

        # PDF -> Images: show DPI selector
        if first_ext == ".pdf" and choice in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
            self.dpi_label.pack(side="left", padx=(0, 6))
            self.dpi_menu.pack(side="left", padx=(0, 15))
            self.format_hint.configure(text="Converts each page of PDF into separate image")

        # Images -> PDF: show Merge checkbox if multiple
        elif choice == "pdf" and len(self.selected_files) > 1:
            self.merge_checkbox.pack(side="left")
            self.format_hint.configure(text=f"Batch convert {len(self.selected_files)} images to PDF")

        # Any -> JPEG / WEBP: show quality slider
        elif choice in ("jpg", "jpeg", "webp"):
            self.quality_label.pack(side="left", padx=(0, 6))
            self.quality_slider.pack(side="left", padx=(0, 10))
            if choice == "webp":
                self.lossless_checkbox.pack(side="left", padx=(0, 10))
            self.format_hint.configure(text=f"Convert to compressed {choice.upper()}")

        elif choice == "png":
            self.lossless_checkbox.pack(side="left", padx=(0, 10))
            self.format_hint.configure(text="Optimized PNG with Deflate compression")

        elif first_ext == ".pdf" and choice == "docx":
            self.format_hint.configure(text="Extracts editable Word document with layouts and tables")
        elif first_ext in (".docx", ".doc") and choice == "pdf":
            self.format_hint.configure(text="Direct high-fidelity PDF export via Word COM")
        else:
            self.format_hint.configure(text="")

    def _on_quality_slider_change(self, val):
        self.quality_label.configure(text=f"Quality: {int(val)}%")

    def _browse_output_dir(self):
        dir_selected = filedialog.askdirectory(title="Select Output Folder")
        if dir_selected:
            self.out_dir_entry.delete(0, "end")
            self.out_dir_entry.insert(0, dir_selected)

    def _open_output_folder(self):
        if self.latest_outputs:
            target = self.latest_outputs[0]
            if os.path.exists(target):
                subprocess.run(f'explorer /select,"{os.path.abspath(target)}"', shell=True)
                return
        out_dir = self.out_dir_entry.get().strip()
        if out_dir and os.path.exists(out_dir):
            os.startfile(out_dir)
        elif self.selected_files:
            os.startfile(str(Path(self.selected_files[0]).parent))

    def _start_conversion_thread(self):
        if not self.selected_files or self.is_converting:
            return

        target_format = self.format_dropdown.get().strip().lower()
        if not target_format or target_format in ("select a file first...", "unsupported file type"):
            messagebox.showwarning("Warning", "Please select a valid target format.")
            return

        self.is_converting = True
        self.convert_btn.configure(state="disabled", text="Converting...")
        self.show_folder_btn.configure(state="disabled")
        self.progress_bar.set(0.0)

        # Gather options
        options: Dict[str, Any] = {}
        dpi_str = self.dpi_var.get()
        if "100" in dpi_str:
            options["dpi"] = 100
        elif "150" in dpi_str:
            options["dpi"] = 150
        elif "300" in dpi_str:
            options["dpi"] = 300
        else:
            options["dpi"] = 200

        options["quality"] = int(self.quality_slider.get())
        options["lossless"] = self.lossless_var.get()
        options["strip_metadata"] = self.strip_exif_var.get()

        custom_out_dir = self.out_dir_entry.get().strip()
        if custom_out_dir:
            options["output_dir"] = custom_out_dir

        thread = threading.Thread(
            target=self._run_conversion,
            args=(self.selected_files.copy(), target_format, options),
            daemon=True
        )
        thread.start()

    def _run_conversion(self, files: List[str], target_format: str, options: Dict[str, Any]):
        total_files = len(files)
        success_count = 0
        all_created_files: List[str] = []
        errors: List[str] = []

        # Check if merge images to PDF is active
        if target_format == "pdf" and self.merge_images_var.get() and total_files > 1:
            self._update_status(0.2, "Merging all images into single PDF...")
            custom_out_dir = options.get("output_dir", None)
            first_path = Path(files[0])
            out_folder = Path(custom_out_dir) if custom_out_dir else first_path.parent
            merged_pdf_path = str(out_folder / f"{first_path.stem}_merged.pdf")

            res = ConversionEngine.convert_images_to_single_pdf(
                image_paths=files,
                output_path=merged_pdf_path,
                progress_callback=lambda p, msg: self._update_status(p, msg)
            )
            if res.success:
                all_created_files.extend(res.output_files)
                success_count = total_files
            else:
                errors.append(f"Merge error: {res.error}")
        else:
            for idx, file_path in enumerate(files):
                base_pct = idx / total_files
                file_pct_share = 1.0 / total_files

                def progress_cb(pct, msg):
                    overall = base_pct + (pct * file_pct_share)
                    self._update_status(overall, f"[{idx + 1}/{total_files}] {Path(file_path).name}: {msg}")

                out_dir = options.get("output_dir", None)
                res = ConversionEngine.convert(
                    source_path=file_path,
                    target_format=target_format,
                    output_path=None if not out_dir else str(Path(out_dir) / f"{Path(file_path).stem}.{target_format}"),
                    options=options,
                    progress_callback=progress_cb
                )

                if res.success:
                    success_count += 1
                    all_created_files.extend(res.output_files)
                else:
                    errors.append(f"{Path(file_path).name}: {res.error}")

        self._on_conversion_finished(success_count, total_files, all_created_files, errors)

    def _update_status(self, progress: float, message: str):
        self.after(0, lambda: self._apply_status(progress, message))

    def _apply_status(self, progress: float, message: str):
        self.progress_bar.set(max(0.0, min(1.0, progress)))
        self.status_label.configure(text=message)

    def _on_conversion_finished(self, success_cnt: int, total_cnt: int, created_files: List[str], errors: List[str]):
        self.after(0, lambda: self._finish_ui(success_cnt, total_cnt, created_files, errors))

    def _finish_ui(self, success_cnt: int, total_cnt: int, created_files: List[str], errors: List[str]):
        self.is_converting = False
        self.convert_btn.configure(state="normal", text="Start Conversion")
        self.latest_outputs = created_files

        if created_files:
            self.show_folder_btn.configure(state="normal")

        if errors:
            self.progress_bar.set(1.0)
            self.status_label.configure(text=f"Completed with errors ({success_cnt}/{total_cnt} succeeded)")
            err_msg = "\n".join(errors[:5])
            if len(errors) > 5:
                err_msg += f"\n...and {len(errors) - 5} more errors."
            messagebox.showerror("Conversion Issues", f"Some files could not be converted:\n\n{err_msg}")
        else:
            self.progress_bar.set(1.0)
            self.status_label.configure(text=f"All {success_cnt} file(s) converted successfully!")
            messagebox.showinfo("Success", f"Successfully converted {success_cnt} file(s)!\nOutput files saved.")

def launch_gui(initial_files: Optional[List[str]] = None):
    app = FileMorphApp(initial_files=initial_files)
    app.mainloop()

if __name__ == "__main__":
    launch_gui()
