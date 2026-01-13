# -*- coding: utf-8 -*-
"""
Build script to create EXE from Converter Suite
"""
import os
import subprocess
import shutil
import sys

def clean_build():
    """Clean build directories"""
    print("Cleaning build directories...")
    
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"  Removing {dir_name}...")
            shutil.rmtree(dir_name, ignore_errors=True)
    
    # Clean pycache
    if os.path.exists('__pycache__'):
        shutil.rmtree('__pycache__', ignore_errors=True)

def build_exe():
    """Build EXE using PyInstaller"""
    print("\n" + "="*50)
    print("Building Converter_Suite.exe")
    print("="*50 + "\n")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller found: {PyInstaller.__version__}")
    except ImportError:
        print("[ERROR] PyInstaller not found!")
        print("Install with: pip install pyinstaller")
        sys.exit(1)
    
    # Clean first
    clean_build()
    
    # Build with PyInstaller
    print("\nBuilding EXE...")
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=Converter_Suite',
        '--hidden-import=tkinterdnd2',
        '--hidden-import=pdf2image',
        '--hidden-import=svgwrite',
        '--hidden-import=PIL._tkinter_finder',
        '--noconfirm',
        'converter_suite.py'
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print("\n[ERROR] Build failed!")
        sys.exit(1)
    
    # Check if EXE was created
    exe_path = os.path.join('dist', 'Converter_Suite.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n" + "="*50)
        print(f"[SUCCESS] EXE created!")
        print(f"[PATH] {exe_path}")
        print(f"[SIZE] {size_mb:.1f} MB")
        print("="*50 + "\n")
        
        # Ask if user wants to test
        print("Would you like to test the EXE now? (y/n)")
        # Uncomment to enable testing:
        # response = input().strip().lower()
        # if response == 'y':
        #     subprocess.run([exe_path])
    else:
        print("\n[ERROR] EXE not found in dist/ folder!")
        sys.exit(1)

if __name__ == '__main__':
    try:
        build_exe()
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
