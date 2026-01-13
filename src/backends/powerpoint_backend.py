
import os
import time
import logging
from pathlib import Path
from typing import Optional, Tuple, List
import tempfile

logger = logging.getLogger(__name__)

# Try to import win32com
try:
    import win32com.client
    import pythoncom
    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False
    logger.warning("win32com not available. PowerPoint COM backend disabled.")


class PowerPointBackend:
    """
    Backend for checking and converting presentations using Microsoft PowerPoint (Windows COM).
    """

    @staticmethod
    def is_available() -> bool:
        """Check if PowerPoint COM automation is available."""
        if not COM_AVAILABLE:
            return False
        try:
            # We don't want to launch PPT just to check, but we can check if the class exists
            # A lightweight check is to see if we can instantiate the Dispatch without error,
            # but that launches it. Instead, trust the import on Windows, or just try-catch the conversion.
            # For now, if win32com is importable and we are on Windows, we assume yes.
            return os.name == 'nt'
        except:
            return False

    @staticmethod
    def convert_to_images(
        input_path: Path,
        output_dir: Path,
        output_format: str = "png",
        progress_callback=None
    ) -> Tuple[bool, List[Path], Optional[str]]:
        """
        Convert presentation slides to images using PowerPoint COM.
        """
        if not COM_AVAILABLE:
            return False, [], "win32com not installed"

        pp = None
        pres = None
        created_files = []
        
        try:
            # Initialize COM in this thread
            pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
            
            # Launch PowerPoint
            try:
                pp = win32com.client.Dispatch("PowerPoint.Application")
            except Exception as e:
                return False, [], f"Failed to dispatch PowerPoint: {e}"

            # Make it visible (sometimes required for export to work properly) but minimized
            try:
                pp.Visible = True
                pp.WindowState = 2  # Minimize
            except:
                pass

            # Open Presentation
            pres = pp.Presentations.Open(str(input_path), 1, 0, 0) # ReadOnly, Untitled, WithWindow=0
            
            total_slides = pres.Slides.Count
            base_name = input_path.stem
            
            # Format mapping for Export
            # PPT uses specific strings. JPG, PNG, BMP are standard.
            export_fmt = output_format.upper()
            if export_fmt == "JPEG": export_fmt = "JPG"

            for i in range(1, total_slides + 1):
                if progress_callback:
                    progress_callback(i / total_slides, f"Exporting slide {i}/{total_slides}")
                
                # Determine output path
                # Standard naming: filename_slide_X.ext
                # We can handle the "separate folder" logic if output_dir is already set to that folder
                filename = f"{base_name}_slide_{i}.{output_format.lower()}"
                output_path = output_dir / filename
                
                # Export
                # Syntax: expression.Export(FileName, FilterName, ScaleWidth, ScaleHeight)
                pres.Slides(i).Export(str(output_path), export_fmt)
                
                if output_path.exists():
                    created_files.append(output_path)
                    if progress_callback:
                        progress_callback(i / total_slides, f"{filename} ... DONE")
            
            return True, created_files, None

        except Exception as e:
            logger.exception("PowerPoint COM conversion failed")
            return False, [], str(e)

        finally:
            # Cleanup
            if pres:
                try: pres.Close()
                except: pass
            if pp:
                try: 
                    if pp.Presentations.Count == 0:
                        pp.Quit()
                except: pass
            
            pythoncom.CoUninitialize()

    @staticmethod
    def convert_to_pdf(
        input_path: Path,
        output_dir: Path,
        progress_callback=None
    ) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Convert presentation to PDF using PowerPoint COM.
        """
        if not COM_AVAILABLE:
            return False, None, "win32com not installed"

        pp = None
        pres = None
        
        try:
            pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
            pp = win32com.client.Dispatch("PowerPoint.Application")
            try: pp.Visible = True; pp.WindowState = 2
            except: pass

            pres = pp.Presentations.Open(str(input_path), 1, 0, 0)
            
            output_name = f"{input_path.stem}.pdf"
            output_path = output_dir / output_name
            
            if progress_callback:
                progress_callback(0.5, "Exporting to PDF...")

            # 32 is ppSaveAsPDF
            pres.SaveAs(str(output_path), 32)
            
            return True, output_path, None

        except Exception as e:
            logger.exception("PowerPoint COM PDF conversion failed")
            return False, None, str(e)

        finally:
            if pres:
                try: pres.Close()
                except: pass
            if pp:
                try: 
                    if pp.Presentations.Count == 0:
                        pp.Quit()
                except: pass
            pythoncom.CoUninitialize()

# Singleton instance
powerpoint_backend = PowerPointBackend()
