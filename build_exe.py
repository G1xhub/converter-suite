"""
Build Script for Converter Suite
Uses PyInstaller to create a standalone executable.
"""

import PyInstaller.__main__
import shutil
import os
from pathlib import Path

# Configuration
APP_NAME = "ConverterSuite"
MAIN_SCRIPT = "main.py"
ICON_FILE = "src/assets/icon.ico"  # Optional, if you have one
ADDITIONAL_DATA = [
    # CustomTkinter data
    ('c:/Users/jgrae/AppData/Local/Programs/Python/Python313/Lib/site-packages/customtkinter', 'customtkinter/'),
    # Add source code if needed (usually not needed if imported)
    ('src', 'src'),
]

# Check if deps folder exists and bundle it
DEPS_DIR = Path("deps")
if DEPS_DIR.exists():
    ADDITIONAL_DATA.append(('deps', 'deps'))

def build():
    """Run PyInstaller build."""
    
    # Clean previous builds
    shutil.rmtree('build', ignore_errors=True)
    shutil.rmtree('dist', ignore_errors=True)
    
    # Common arguments
    args = [
        MAIN_SCRIPT,
        f'--name={APP_NAME}',
        '--noconfirm',
        '--windowed',  # No console window
        '--clean',
        f'--icon={ICON_FILE}',
        
        # Imports
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=tkinterdnd2',
        '--hidden-import=customtkinter',
        '--hidden-import=pypdf2',
        '--hidden-import=reportlab',
        
        # Data
        '--collect-all=customtkinter',
        '--collect-all=tkinterdnd2',
    ]
    
    # Add bundled data
    for src, dst in ADDITIONAL_DATA:
        # Check if src is absolute or relative
        # PyInstaller expects: src;dst (Windows) or src:dst (Unix)
        # We let collect-all handle ctk, but explicit adds here:
        if src == 'deps' and Path(src).exists():
             args.append(f'--add-data={src}{os.pathsep}{dst}')
    
    print("Building Converter Suite...")
    PyInstaller.__main__.run(args)
    print("Build complete! Check ./dist folder.")

if __name__ == "__main__":
    build()
