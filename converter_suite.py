import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from PIL import Image, ImageTk
import tempfile
import win32com.client
import pythoncom
import threading

# Configuration for CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DND_AVAILABLE = False
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    pass

class PPTXConverter(ctk.CTk, TkinterDnD.DnDWrapper if DND_AVAILABLE else object):
    def __init__(self):
        super().__init__()
        
        if DND_AVAILABLE:
            self.TkdndVersion = TkinterDnD._require(self)

        self.title("Converter Suite Pro")
        self.geometry("1100x700")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.output_dir = os.path.expanduser("~/Pictures")
        self.image_format = tk.StringVar(value="PNG")
        self.quality = tk.IntVar(value=95)
        self.number_slides = tk.BooleanVar(value=True)
        self.current_preview_file = None
        
        # Keep track of card images to prevent garbage collection
        self.gallery_images = []

        self.setup_ui()

    def setup_ui(self):
        self.create_sidebar()
        self.create_main_area()

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        logo_label = ctk.CTkLabel(self.sidebar_frame, text="Converter Suite", font=ctk.CTkFont(size=20, weight="bold"))
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Output Format
        lbl_format = ctk.CTkLabel(self.sidebar_frame, text="Output Format:", anchor="w")
        lbl_format.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.format_menu = ctk.CTkSegmentedButton(self.sidebar_frame, values=["PNG", "JPG", "BMP"], 
                                                  command=self.change_format_callback)
        self.format_menu.set("PNG")
        self.format_menu.grid(row=2, column=0, padx=20, pady=(5, 10), sticky="ew")

        # Quality
        lbl_quality = ctk.CTkLabel(self.sidebar_frame, text="JPG Quality:", anchor="w")
        lbl_quality.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.quality_slider = ctk.CTkSlider(self.sidebar_frame, from_=1, to=100, variable=self.quality, number_of_steps=99)
        self.quality_slider.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="ew")

        # Checkboxes
        self.chk_numbering = ctk.CTkSwitch(self.sidebar_frame, text="Number Slides", variable=self.number_slides)
        self.chk_numbering.grid(row=5, column=0, padx=20, pady=10, sticky="w")

        # Output Directory
        lbl_dir = ctk.CTkLabel(self.sidebar_frame, text="Output Directory:", anchor="w")
        lbl_dir.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.entry_dir = ctk.CTkEntry(self.sidebar_frame, placeholder_text=self.output_dir)
        self.entry_dir.insert(0, self.output_dir)
        self.entry_dir.configure(state="readonly")
        self.entry_dir.grid(row=7, column=0, padx=20, pady=(5, 5), sticky="ew")
        
        btn_browse = ctk.CTkButton(self.sidebar_frame, text="Browse Folder", command=self.browse_dir)
        btn_browse.grid(row=8, column=0, padx=20, pady=5, sticky="n")

        # Help / Status
        lbl_help = ctk.CTkLabel(self.sidebar_frame, text="Supported:\nPPTX, PPT, PDF, ODP", 
                                font=ctk.CTkFont(size=12), text_color="gray")
        lbl_help.grid(row=9, column=0, padx=20, pady=20, sticky="s")


    def create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.main_frame.grid_rowconfigure(0, weight=1) # Drop zone
        self.main_frame.grid_rowconfigure(1, weight=0) # Progress Bar
        self.main_frame.grid_rowconfigure(2, weight=3) # Gallery
        self.main_frame.grid_columnconfigure(0, weight=1)

        # -- Top: Drag & Drop Zone --
        self.drop_frame = ctk.CTkFrame(self.main_frame, border_width=2, border_color="gray")
        self.drop_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        self.drop_label = ctk.CTkLabel(self.drop_frame, text="DRAG & DROP FILES HERE\n\nor click to select", 
                                       font=ctk.CTkFont(size=20, weight="bold"))
        self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
        
        self.drop_label.bind("<Button-1>", lambda e: self.select_files())
        self.drop_frame.bind("<Button-1>", lambda e: self.select_files())

        if DND_AVAILABLE:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self.on_drop)

        # -- Middle: Progress Bar & Status --
        self.status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.status_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.status_frame, orientation="horizontal")
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=10)
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Ready", text_color="gray")
        self.lbl_status.grid(row=1, column=0, sticky="w", padx=10)

        # -- Bottom: Gallery View --
        # We replace "File List + Log" with a nice Scrollable Frame
        self.gallery_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Gallery Output")
        self.gallery_frame.grid(row=2, column=0, sticky="nsew")
        self.gallery_frame.grid_columnconfigure(0, weight=1)
        self.gallery_frame.grid_columnconfigure(1, weight=1)
        self.gallery_frame.grid_columnconfigure(2, weight=1)
        # We will grid items in columns (e.g. 3 columns)

    def change_format_callback(self, value):
        self.image_format.set(value)

    def clear_gallery(self):
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()
        self.gallery_images = [] # Clear references

    def add_gallery_item(self, image_path, title, idx):
        # Create a card for the image
        try:
            pil_img = Image.open(image_path)
            # Create thumbnail
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(160, 120))
            self.gallery_images.append(ctk_img) # keep ref

            row = idx // 3 
            col = idx % 3

            card = ctk.CTkFrame(self.gallery_frame)
            card.grid(row=row, column=col, padx=10, pady=10)
            
            img_label = ctk.CTkLabel(card, text="", image=ctk_img)
            img_label.pack(padx=5, pady=5)
            
            txt_label = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10), wraplength=150)
            txt_label.pack(padx=5, pady=(0,5))
            
            # Simple interaction: Click to open
            img_label.bind("<Button-1>", lambda e, p=image_path: os.startfile(p) if os.name == 'nt' else None)
            
        except Exception as e:
            print(f"Error adding gallery item: {e}")

    def browse_dir(self):
        dir = filedialog.askdirectory(initialdir=self.output_dir)
        if dir:
            self.output_dir = dir
            self.entry_dir.configure(state="normal")
            self.entry_dir.delete(0, "end")
            self.entry_dir.insert(0, dir)
            self.entry_dir.configure(state="readonly")

    def on_drop(self, event):
        if DND_AVAILABLE:
            files = self.Tk.splitlist(self, event.data)
            for f in files:
                if os.path.isfile(f):
                    threading.Thread(target=self.convert, args=(f,), daemon=True).start()

    def select_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Files", "*.pptx *.ppt *.ppsx *.pps *.pdf *.odp")])
        for f in files:
            threading.Thread(target=self.convert, args=(f,), daemon=True).start()

    def update_status(self, text, progress=None):
        def _update():
            self.lbl_status.configure(text=text)
            if progress is not None:
                self.progress_bar.set(progress)
        self.after(0, _update)

    def add_to_gallery_threadsafe(self, path, name, idx):
        self.after(0, lambda: self.add_gallery_item(path, name, idx))

    def convert(self, file_path):
        try:
            self.update_status(f"Starting: {os.path.basename(file_path)}", 0.0)
            self.after(0, self.clear_gallery)
            
            abs_path = os.path.abspath(file_path)
            file_ext = os.path.splitext(abs_path)[1].lower()
            
            # --- PowerPoint ---
            if file_ext in ('.pptx', '.ppt', '.ppsx', '.pps'):
                pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
                pp = win32com.client.Dispatch("PowerPoint.Application")
                try: 
                    pp.Visible = True
                    pp.WindowState = 2 # Minimize
                except: pass

                pres = None
                try:
                    pres = pp.Presentations.Open(abs_path, 1, 0, 0)
                    base = os.path.splitext(os.path.basename(file_path))[0]
                    temp_dir = tempfile.gettempdir()
                    total_slides = pres.Slides.Count

                    for i in range(1, total_slides + 1):
                        self.update_status(f"Converting slide {i} of {total_slides}...", i / total_slides)
                        
                        temp_img = os.path.join(temp_dir, f"temp_{i}.jpg")
                        pres.Slides(i).Export(temp_img, "JPG")

                        img = Image.open(temp_img)
                        num = f"_slide_{i}" if self.number_slides.get() else ""
                        filename = f"{base}{num}.{self.image_format.get().lower()}"
                        final = os.path.join(self.output_dir, filename)

                        fmt = self.image_format.get()
                        if fmt == "JPG":
                            img.save(final, "JPEG", quality=self.quality.get())
                        else:
                            img.save(final, fmt)

                        os.remove(temp_img)
                        self.add_to_gallery_threadsafe(final, filename, i-1)

                    pres.Close()
                finally:
                    try: pp.Quit()
                    except: pass
                    pythoncom.CoUninitialize()
            
            # --- PDF ---
            elif file_ext == '.pdf':
                from pdf2image import convert_from_path, pdfinfo_from_path
                base = os.path.splitext(os.path.basename(file_path))[0]
                
                # Get page count first for progress
                try:
                    info = pdfinfo_from_path(abs_path)
                    total_pages = info["Pages"]
                except:
                    total_pages = 10 # approximate fallback

                # We convert one by one or in batches if possible, but pdf2image is usually all at once unless we iterate.
                # Use thread_count for speed, but progress bar is harder.
                # Let's convert valid progress.
                images = convert_from_path(abs_path)
                total_pages = len(images)
                
                for i, img in enumerate(images):
                    self.update_status(f"Saving page {i+1} of {total_pages}...", (i+1) / total_pages)
                    
                    num = f"_slide_{i+1}" if self.number_slides.get() else ""
                    filename = f"{base}{num}.{self.image_format.get().lower()}"
                    final = os.path.join(self.output_dir, filename)
                    
                    fmt = self.image_format.get()
                    if fmt == "JPG":
                        img.save(final, "JPEG", quality=self.quality.get())
                    else:
                        img.save(final, fmt)
                    
                    self.add_to_gallery_threadsafe(final, filename, i)

            self.update_status(f"Completed: {os.path.basename(file_path)}", 1.0)

        except Exception as e:
            import traceback
            self.update_status(f"Error: {str(e)}", 0.0)
            print(traceback.format_exc())

if __name__ == "__main__":
    app = PPTXConverter()
    app.mainloop()
