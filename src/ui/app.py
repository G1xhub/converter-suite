"""
Converter Suite - Main Application UI
Redesigned with "Tech Noir" Terminal Aesthetic.
Features: Tabs, Symmetrical Layout, LED Indicator.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import logging
import time
import copy
from typing import Optional

# Configure CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue") # We will override colors manually for Black/White theme

# Try to import drag-and-drop support
DND_AVAILABLE = False
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    pass

from ..converters.registry import registry
from ..converters.base import ConversionCategory, ConversionOptions
from ..converters.image_converter import ImageConverter
from ..converters.video_converter import VideoConverter
from ..converters.audio_converter import AudioConverter
from ..converters.document_converter import DocumentConverter
from ..converters.presentation_converter import PresentationConverter
from ..utils.dependency_checker import dependency_checker

logger = logging.getLogger(__name__)


class LEDIndicator(ctk.CTkCanvas):
    """A simple LED indicator widget."""
    def __init__(self, master, width=20, height=20, bg='black', **kwargs):
        super().__init__(master, width=width, height=height, highlightthickness=0, bg=bg, **kwargs)
        self.width = width
        self.height = height
        self.state = "idle" # idle, running, error
        self.draw()

    def set_state(self, state: str):
        self.state = state
        self.draw()

    def draw(self):
        self.delete("all")
        color = "#333333" # Grey/Off
        glow_color = None
        
        if self.state == "running":
            color = "#00FF00" # Terminal Green
            glow_color = "#004400"
        elif self.state == "error":
            color = "#FF0000" # Red
            glow_color = "#440000"
        elif self.state == "ready":
             color = "#00CC00" # Dim Green

        # Draw glow if active
        if glow_color:
             self.create_oval(2, 2, self.width-2, self.height-2, fill=glow_color, outline="")

        # Draw LED center
        pad = 6 if glow_color else 4
        self.create_oval(pad, pad, self.width-pad, self.height-pad, fill=color, outline="")


class ConverterApp(ctk.CTk if not DND_AVAILABLE else type('ConverterApp', (ctk.CTk, TkinterDnD.DnDWrapper), {})):
    """
    Main application window for Converter Suite.
    "Tech Noir" Terminal Theme.
    """
    
    # Theme Configuration
    THEMES = {
        "dark": {
            "BG": "#000000",
            "FG": "#E0E0E0",
            "ACCENT": "#FFFFFF",
            "DIM": "#888888",
            "BORDER": "#444444",
            "TERMINAL_BG": "#0C0C0C",
            "TERMINAL_TEXT": "#00FF00",
            "BUTTON_FG": "white",
            "BUTTON_TEXT": "black",
        },
        "light": {
            "BG": "#F5F1E6",          # Oatmeal / Earthy Beige
            "FG": "#3E3B36",          # Dark Charcoal/Brown
            "ACCENT": "#5C5951",      # Deep Taupe
            "DIM": "#5C5951",         # Taupe for secondary text
            "BORDER": "#B0A899",      # Stone Gray/Beige
            "TERMINAL_BG": "#2B2821", # Dark Brown (Retro Terminal)
            "TERMINAL_TEXT": "#E8C547", # Amber/Gold for terminal text
            "BUTTON_FG": "#3E3B36",   # Dark for button
            "BUTTON_TEXT": "#F5F1E6", # Light text
        }
    }

    FONT_MAIN = ("Roboto", 15) 
    FONT_MONO = ("Consolas", 13) 
    FONT_HEADER = ("Roboto", 14, "bold") 
    FONT_BUTTON = ("Consolas", 16, "bold") 
    
    CATEGORIES = [
        ("DOCS", ConversionCategory.DOCUMENT),
        ("IMAGES", ConversionCategory.IMAGE),
        ("VIDEO", ConversionCategory.VIDEO),
        ("AUDIO", ConversionCategory.AUDIO),
        ("PRESENTATIONS", ConversionCategory.PRESENTATION),
    ]
    
    def __init__(self):
        super().__init__()
        
        if DND_AVAILABLE:
            self.TkdndVersion = TkinterDnD._require(self)
        
        self.title("Converter Suite // TERMINAL")
        self.geometry("1100x800")
        self.minsize(950, 700)
        
        # State
        self.current_theme = "dark"
        self.colors = self.THEMES[self.current_theme]
        
        self.configure(fg_color=self.colors["BG"])
        
        self.current_category: Optional[ConversionCategory] = None
        self.output_dir = Path.home() / "ConvertedFiles"
        self.output_dir.mkdir(exist_ok=True)
        self.selected_files: list[Path] = []
        self.output_format = tk.StringVar(value="")
        self.create_folders_var = tk.BooleanVar(value=False)
        self.is_converting = False
        
        self.tab_buttons: dict[str, ctk.CTkButton] = {}

        self._register_converters()
        self._setup_ui()
        
        # Select first category
        self._on_tab_change("DOCS")

    def _register_converters(self):
        registry.clear()
        registry.register(ImageConverter())
        registry.register(VideoConverter())
        registry.register(AudioConverter())
        registry.register(DocumentConverter())
        registry.register(PresentationConverter())

    def _toggle_theme(self):
        """Switch between dark and light themes."""
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.colors = self.THEMES[self.current_theme]
        
        # Re-apply background
        self.configure(fg_color=self.colors["BG"])
        
        # Rebuild UI to apply new colors (simplest way to ensure everything updates)
        # Destroy main containers
        for widget in [self.header_frame, self.content_frame, self.bottom_frame]:
            widget.destroy()
            
        # Rebuild
        self._setup_ui()
        
        # Restore tab state
        cat_name = "DOCS"
        for name, cat in self.CATEGORIES:
             if cat == self.current_category:
                 cat_name = name
                 break
        self._on_tab_change(cat_name)
        
        # Restore file list visuals
        self._update_file_list()
        self._update_output_tree()
        self._update_button_state()
        
        # Log it
        self._log(f"THEME SWITCHED TO {self.current_theme.upper()}")

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Content expands
        self.grid_rowconfigure(2, weight=0) # Bottom is fixed height
        
        # --- 1. HEADER & TABS ---
        self.header_frame = ctk.CTkFrame(self, fg_color=self.colors["BG"], height=60, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 0))
        self.header_frame.grid_columnconfigure(0, weight=1) 
        self.header_frame.grid_columnconfigure(2, weight=1) 

        # Logo / Title (Left)
        title_panel = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_panel.grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(title_panel, text="CONVERTER_SUITE", font=("Consolas", 20, "bold"), text_color=self.colors["FG"]).pack(anchor="w")
        ctk.CTkLabel(title_panel, text="v0.1.7 [PRO]", font=("Consolas", 10), text_color=self.colors["DIM"]).pack(anchor="w")

        # Custom Browser Tabs (Center)
        self.tabs_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.tabs_container.grid(row=0, column=1, sticky="ew", padx=40)
        
        self.tab_buttons = {} # Reset
        for name, cat in self.CATEGORIES:
            btn = ctk.CTkButton(
                self.tabs_container,
                text=name,
                font=self.FONT_HEADER,
                width=120,
                height=35,
                corner_radius=5, 
                border_width=0,
                fg_color="transparent", 
                text_color=self.colors["DIM"],
                hover_color=self.colors["BORDER"], # Use border color for hover
                command=lambda n=name: self._on_tab_change(n)
            )
            btn.pack(side="left", padx=5) 
            self.tab_buttons[name] = btn

        # Theme Toggle (Right)
        theme_btn = ctk.CTkButton(
            self.header_frame,
            text="☀/mnt" if self.current_theme == "dark" else "☾/dark",
            width=60,
            fg_color="transparent",
            border_width=1,
            border_color=self.colors["DIM"],
            text_color=self.colors["FG"],
            command=self._toggle_theme
        )
        theme_btn.grid(row=0, column=2, sticky="e")

        # --- 2. MAIN CONTENT (Split View) ---
        self.content_frame = ctk.CTkFrame(self, fg_color=self.colors["BG"], corner_radius=0)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1, uniform="group1") # Left
        self.content_frame.grid_columnconfigure(1, weight=1, uniform="group1") # Right
        self.content_frame.grid_rowconfigure(0, weight=1)

        # LEFT COLUMN: INPUT
        self._setup_left_column()

        # RIGHT COLUMN: OUTPUT
        self._setup_right_column()


        # --- 3. BOTTOM: TERMINAL LOG (LEFT) & EXECUTE (RIGHT) ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent", height=150, corner_radius=0)
        self.bottom_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.bottom_frame.grid_columnconfigure(0, weight=3, uniform="bottom") # Log Area (Left)
        self.bottom_frame.grid_columnconfigure(1, weight=2, uniform="bottom") # Execute Area (Right)
        self.bottom_frame.grid_propagate(False) # Enforce height
        
        # LEFT: Log & LED
        self.log_container = ctk.CTkFrame(self.bottom_frame, fg_color=self.colors["TERMINAL_BG"], border_width=1, border_color=self.colors["BORDER"], corner_radius=0)
        self.log_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.log_container.grid_columnconfigure(0, weight=1)
        self.log_container.grid_rowconfigure(1, weight=1)

        # LED Indicator
        self.led_canvas = ctk.CTkCanvas(self.log_container, width=40, height=20, bg=self.colors["TERMINAL_BG"], highlightthickness=0)
        self.led_canvas.grid(row=0, column=0, sticky="w", padx=10, pady=(10,0))
        self.led = LEDIndicator(self.led_canvas, width=15, height=15, bg=self.colors["TERMINAL_BG"])
        self.led.pack(side="left")
        ctk.CTkLabel(self.led_canvas, text="SYSTEM_STATUS", font=("Consolas", 10), text_color=self.colors["DIM"]).pack(side="left", padx=5)

        # Log Box
        self.log_box = ctk.CTkTextbox(
            self.log_container,
            font=self.FONT_MONO,
            fg_color="transparent",
            text_color=self.colors["TERMINAL_TEXT"],
            height=100
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.log_box.insert("end", "> SYSTEM INITIALIZED...\n> WAITING FOR INPUT...\n")
        self.log_box.configure(state="disabled")

        # RIGHT: Execute Button Tile
        self.execute_container = ctk.CTkFrame(self.bottom_frame, fg_color=self.colors["TERMINAL_BG"], border_width=1, border_color=self.colors["BORDER"], corner_radius=0)
        self.execute_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.execute_container.grid_columnconfigure(0, weight=1)
        self.execute_container.grid_rowconfigure(0, weight=1)

        self.convert_btn = ctk.CTkButton(
            self.execute_container,
            text="> EXECUTE CONVERSION",
            font=self.FONT_BUTTON,
            fg_color=self.colors["BUTTON_FG"], 
            text_color=self.colors["BUTTON_TEXT"],
            hover_color=self.colors["BORDER"],
            corner_radius=0,
            command=self._start_conversion
        )
        self.convert_btn.pack(expand=True, fill="both", padx=2, pady=2)
        
        self._update_button_state()


    def _setup_left_column(self):
        self.left_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent", border_width=1, border_color=self.colors["BORDER"], corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.left_frame.grid_rowconfigure(1, weight=0) # Drop Zone (Fixed/Limited)
        self.left_frame.grid_rowconfigure(3, weight=1) # File List (Expands)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Label
        ctk.CTkLabel(self.left_frame, text=" [ INPUT SOURCE ] ", font=self.FONT_MONO, text_color=self.colors["DIM"], fg_color=self.colors["BG"]).grid(row=0, column=0, sticky="nw", padx=10, pady=10)

        # Drop Zone (Limited Height)
        # For Drop Zone BG in Light Mode, we need something distinct but not black
        drop_bg_color = "#E8E4D9" if self.current_theme == "light" else "#080808"
        
        self.drop_zone = ctk.CTkFrame(self.left_frame, fg_color=drop_bg_color, border_width=2, border_color=self.colors["BORDER"], corner_radius=0, height=200) # Fixed height hint
        self.drop_zone.grid(row=1, column=0, sticky="ew", padx=20, pady=20)
        self.drop_zone.grid_propagate(False) # Enforce height
        
        self.drop_label = ctk.CTkLabel(self.drop_zone, text="DRAG FILES HERE", font=("Consolas", 19, "bold"), text_color=self.colors["DIM"])
        self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Click to browse
        self.drop_zone.bind("<Button-1>", lambda e: self._browse_files())
        self.drop_label.bind("<Button-1>", lambda e: self._browse_files())
        
        if DND_AVAILABLE:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind('<<Drop>>', self._on_drop)

        # File List (Expands)
        self.file_list_label = ctk.CTkLabel(self.left_frame, text="SELECTED FILES:", font=self.FONT_MONO, text_color=self.colors["DIM"], anchor="w")
        self.file_list_label.grid(row=2, column=0, sticky="w", padx=20, pady=(0,5))

        list_bg_color = "#FFFFFF" if self.current_theme == "light" else "#080808"

        self.file_list = ctk.CTkTextbox(self.left_frame, font=self.FONT_MONO, fg_color=list_bg_color, text_color=self.colors["FG"], border_width=1, border_color=self.colors["BORDER"])
        self.file_list.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.file_list.configure(state="disabled")

    def _setup_right_column(self):
        self.right_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent", border_width=1, border_color=self.colors["BORDER"], corner_radius=0)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(3, weight=1) # Tree expands

        # Label
        ctk.CTkLabel(self.right_frame, text=" [ CONFIGURATION ] ", font=self.FONT_MONO, text_color=self.colors["DIM"], fg_color=self.colors["BG"]).grid(row=0, column=0, sticky="nw", padx=10, pady=10)

        # Settings Container (Fixed Height approx)
        self.settings_container = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.settings_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=0)
        self.settings_container.grid_columnconfigure(0, weight=1)
        
        # Colors for inputs
        input_fg = "#FFF" if self.current_theme == "light" else "#111111" # Background of inputs
        input_txt = self.colors["FG"]

        # 1. Output Format
        ctk.CTkLabel(self.settings_container, text="TARGET FORM", font=("Consolas", 14, "bold"), text_color=self.colors["FG"], anchor="w").pack(fill="x", pady=(10, 5))
        self.format_menu = ctk.CTkOptionMenu(
            self.settings_container, 
            variable=self.output_format, 
            values=[],
            fg_color=self.colors["BORDER"], button_color=self.colors["DIM"], button_hover_color=self.colors["BORDER"], text_color=self.colors["BG"], # Inverted for contrast
            font=self.FONT_MONO, corner_radius=0
        )
        self.format_menu.pack(fill="x", pady=(0, 20))

        # 2. Quality
        ctk.CTkLabel(self.settings_container, text="QUALITY RATIO", font=("Consolas", 14, "bold"), text_color=self.colors["FG"], anchor="w").pack(fill="x", pady=(0, 5))
        self.quality_var = tk.IntVar(value=90)
        self.quality_slider = ctk.CTkSlider(
            self.settings_container, 
            from_=1, to=100, variable=self.quality_var, 
            progress_color=self.colors["FG"], button_color=self.colors["FG"], button_hover_color=self.colors["BORDER"],
            border_width=0
        )
        self.quality_slider.pack(fill="x", pady=(0, 0))
        self.quality_label = ctk.CTkLabel(self.settings_container, text="90%", font=self.FONT_MONO, text_color=self.colors["DIM"])
        self.quality_label.pack(anchor="e")
        self.quality_var.trace_add("write", lambda *_: self.quality_label.configure(text=f"{self.quality_var.get()}%"))

        # 3. Output Path
        ctk.CTkLabel(self.settings_container, text="DESTINATION VECTOR", font=("Consolas", 14, "bold"), text_color=self.colors["FG"], anchor="w").pack(fill="x", pady=(10, 5))
        self.path_entry = ctk.CTkEntry(
            self.settings_container, 
            fg_color=self.colors["TERMINAL_BG"], border_color=self.colors["BORDER"], text_color=self.colors["FG"], 
            font=self.FONT_MONO, corner_radius=0
        )
        self.path_entry.insert(0, str(self.output_dir))
        self.path_entry.configure(state="readonly")
        self.path_entry.pack(fill="x", pady=(0, 5))
        
        ctk.CTkButton(
            self.settings_container, text="BROWSE...", 
            command=self._browse_output_dir,
            font=self.FONT_MONO, 
            fg_color=self.colors["BORDER"], 
            hover_color=self.colors["DIM"], 
            text_color=self.colors["BG"], # contrast
            corner_radius=0, width=100
        ).pack(anchor="e")

        # 4. Create Folder Option
        self.folder_chk = ctk.CTkCheckBox(
            self.settings_container,
            text="ISOLATE IN FOLDERS",
            variable=self.create_folders_var,
            command=self._update_output_tree, 
            font=("Consolas", 13),
            text_color=self.colors["FG"],
            fg_color=self.colors["BORDER"],
            hover_color=self.colors["DIM"],
            border_color=self.colors["BORDER"],
            corner_radius=0
        )
        self.folder_chk.pack(fill="x", pady=(20, 0))

        # 5. Output Tree Preview
        ctk.CTkLabel(self.right_frame, text=" [ OUTPUT PREVIEW ] ", font=self.FONT_MONO, text_color=self.colors["DIM"], fg_color=self.colors["BG"]).grid(row=2, column=0, sticky="nw", padx=10, pady=(20, 10))
        
        list_bg_color = "#FFFFFF" if self.current_theme == "light" else "#111111"
        self.tree_preview = ctk.CTkTextbox(
            self.right_frame,
            font=self.FONT_MONO,
            fg_color=list_bg_color,
            text_color=self.colors["DIM"],
            border_width=0,
            wrap="none" # Better for trees
        )
        self.tree_preview.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.tree_preview.configure(state="disabled")


    def _on_tab_change(self, value):
        # Update Tab Styling
        for name, btn in self.tab_buttons.items():
            if name == value:
                # Active Tab: Highlighted
                btn.configure(fg_color=self.colors["BORDER"], text_color=self.colors["BG"]) 
            else:
                # Inactive
                btn.configure(fg_color="transparent", text_color=self.colors["DIM"])

        # Find category object
        for name, cat in self.CATEGORIES:
            if name == value:
                self.current_category = cat
                break
        
        self.selected_files.clear()
        self._update_file_list()
        
        # Update settings for this category
        converters = registry.get_converters(self.current_category)
        if converters:
            conv = converters[0]
            fmts = conv.supported_output_formats
            self.output_format.set(fmts[0] if fmts else "")
            self.format_menu.configure(values=fmts)
            
            self.format_menu.configure(values=fmts)
            
            # Show supported inputs in log
            inputs = ", ".join(conv.supported_input_formats[:5])
            self._log(f"SWITCHED TO {value}. SUPPORTS: {inputs}...")
            
            self._update_output_tree() # Refresh tree
            self._update_button_state()

    def _log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _on_progress_log(self, progress, message):
        """Callback for converter progress."""
        if message:
            # Don't show timestamp for these intermediate logs to keep it cleaner? 
            # User asked for: "filename.png ...done!"
            # Let's keep it simple and just log the message. 
            # We can use _log to keep consistency or direct insert.
            # Let's use direct insert for "list" style or _log for consistency.
            # _log adds a new line.
            self._log(message)

    def _update_output_tree(self, *args):
        """Update the output tree preview based on settings."""
        self.tree_preview.configure(state="normal")
        self.tree_preview.delete("0.0", "end")
        
        if not self.selected_files:
            self.tree_preview.insert("end", "\n[NO FILES SELECTED]")
        else:
            fmt = self.output_format.get().lower() or "fmt"
            for f in self.selected_files[:5]: # Limit preview
                if self.create_folders_var.get():
                    self.tree_preview.insert("end", f"📂 {f.stem}/\n")
                    self.tree_preview.insert("end", f" └── 📄 {f.stem}.{fmt}\n")
                else:
                    self.tree_preview.insert("end", f"📄 {f.stem}.{fmt}\n")
            
            if len(self.selected_files) > 5:
                self.tree_preview.insert("end", f"... (+{len(self.selected_files)-5} more)")
                
        self.tree_preview.configure(state="disabled")

    def _update_button_state(self):
        """Update start button appearance based on validity."""
        if self.selected_files and self.output_format.get():
            self.convert_btn.configure(
                state="normal", 
                fg_color=self.colors["BUTTON_FG"], 
                text_color=self.colors["BUTTON_TEXT"]
            )
        else:
            self.convert_btn.configure(state="disabled", fg_color=self.colors["BORDER"], text_color=self.colors["DIM"]) # Dimmed

    def _browse_files(self):
        if not self.current_category: return
        converters = registry.get_converters(self.current_category)
        if not converters: return
        
        exts = converters[0].supported_input_formats
        file_types = [("Supported", " ".join(f"*.{ext}" for ext in exts))]
        files = filedialog.askopenfilenames(filetypes=file_types)
        if files:
            self.selected_files = [Path(f) for f in files]
            self._update_file_list()
            self._update_output_tree() # Refresh tree
            self._update_button_state() # Check valid
            self._log(f"LOADED {len(files)} FILE(S).")

    def _update_file_list(self):
        self.file_list.configure(state="normal")
        self.file_list.delete("0.0", "end")
        if self.selected_files:
            for f in self.selected_files:
                self.file_list.insert("end", f"> {f.name}\n")
            self.drop_label.configure(text=f"{len(self.selected_files)} FILES READY")
        else:
            self.drop_label.configure(text="DRAG FILES HERE")
        self.file_list.configure(state="disabled")

    def _on_drop(self, event):
        if DND_AVAILABLE:
            files = self.tk.splitlist(event.data)
            valid = [Path(f) for f in files if Path(f).is_file()]
            self.selected_files.extend(valid)
            self._update_file_list()
            self._update_output_tree() # Refresh tree
            self._update_button_state() # Check valid
            self._log(f"DROPPED {len(valid)} FILE(S).")

    def _browse_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.output_dir)
        if d:
            self.output_dir = Path(d)
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, str(d))
            self.path_entry.configure(state="readonly")

    def _start_conversion(self):
        if not self.selected_files:
            self._log("ERROR: NO FILES SELECTED.")
            return
        if self.is_converting: return

        self.is_converting = True
        self.convert_btn.configure(state="disabled", text="PROCESSING...")
        self.led.set_state("running")
        
        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _run_conversion(self):
        try:
            self._log("INITIALIZING BATCH JOB...")
            converter = registry.find_converter(self.selected_files[0].suffix.lstrip('.'), self.output_format.get())
            
            if not converter:
                self._log("ERROR: NO SUITABLE CONVERTER FOUND.")
                self.after(0, self._on_finish, "error")
                return

            # Hook up detailed logging
            converter.set_progress_callback(self._on_progress_log)

            base_opts = ConversionOptions(output_dir=self.output_dir, quality=self.quality_var.get(), overwrite=True)
            
            for f in self.selected_files:
                opts = copy.copy(base_opts)
                if self.create_folders_var.get():
                    opts.output_dir = base_opts.output_dir / f.stem
                    # Create directory immediately to be safe, though most converters do it
                    try: opts.output_dir.mkdir(exist_ok=True)
                    except: pass
                
                self._log(f"CONVERTING: {f.name} -> {self.output_format.get().upper()}...")
                res = converter.convert(f, self.output_format.get(), opts)
                if res.success:
                    self._log(f"SUCCESS: {f.name}")
                else:
                    self._log(f"FAIL: {f.name} - {res.error_message}")
            
            self._log("JOB COMPLETE.")
            self.after(0, self._on_finish, "ready")

        except Exception as e:
            self._log(f"CRITICAL ERROR: {e}")
            self.after(0, self._on_finish, "error")

    def _on_finish(self, state="idle"):
        self.is_converting = False
        self.convert_btn.configure(state="normal", text="> EXECUTE CONVERSION")
        self.led.set_state(state)


if __name__ == "__main__":
    app = ConverterApp()
    app.mainloop()
