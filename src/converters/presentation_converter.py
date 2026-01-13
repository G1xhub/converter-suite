"""
Presentation Converter
Converts presentations (PPTX, ODP) to images or PDF using LibreOffice.
"""

from pathlib import Path
from typing import Optional
import time
import logging

from .base import (
    BaseConverter,
    ConversionCategory,
    ConversionOptions,
    ConversionResult
)
from ..backends.libreoffice_backend import libreoffice_backend
from ..backends.powerpoint_backend import powerpoint_backend

logger = logging.getLogger(__name__)


class PresentationConverter(BaseConverter):
    """
    Converter for presentation files.
    Prioritizes Microsoft PowerPoint (COM) on Windows, falls back to LibreOffice.
    """
    
    @property
    def category(self) -> ConversionCategory:
        return ConversionCategory.PRESENTATION
    
    @property
    def name(self) -> str:
        return "Presentation Converter (PowerPoint/LibreOffice)"
    
    @property
    def supported_input_formats(self) -> list[str]:
        return ['pptx', 'ppt', 'odp', 'ppsx', 'pps']
    
    @property
    def supported_output_formats(self) -> list[str]:
        return ['pdf', 'png', 'jpg', 'odp', 'pptx']
    
    def validate_dependencies(self) -> tuple[bool, str]:
        """Check if PowerPoint or LibreOffice is available."""
        if powerpoint_backend.is_available():
            return True, "Microsoft PowerPoint available"
        if libreoffice_backend.is_available():
            return True, "LibreOffice available"
        return False, "Neither PowerPoint nor LibreOffice found."
    
    def convert(
        self,
        input_path: Path,
        output_format: str,
        options: Optional[ConversionOptions] = None
    ) -> ConversionResult:
        """Convert a presentation file."""
        start_time = time.time()
        options = options or ConversionOptions()
        output_format = output_format.lower().lstrip('.')
        
        # Determine strict output mode
        # If output file is specified in options (rarely used for images), use it, else dir
        
        # Priority 1: PowerPoint Backend (Windows)
        if powerpoint_backend.is_available():
            try:
                return self._convert_with_powerpoint(input_path, output_format, options, start_time)
            except Exception as e:
                logger.warning(f"PowerPoint conversion failed, trying LibreOffice: {e}")
                # Fallthrough to LibreOffice
        
        # Priority 2: LibreOffice
        if libreoffice_backend.is_available():
             return self._convert_with_libreoffice(input_path, output_format, options, start_time)

        return ConversionResult(
            success=False,
            input_path=input_path,
            error_message="No suitable backend found (PowerPoint or LibreOffice missing)"
        )

    def _convert_with_powerpoint(self, input_path, output_format, options, start_time):
        self._report_progress(0.1, f"Opening {input_path.name} (PowerPoint)")
        
        output_dir = options.output_dir or input_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_format in ('png', 'jpg', 'jpeg', 'bmp'):
            success, files, msg = powerpoint_backend.convert_to_images(
                input_path, 
                output_dir, 
                output_format,
                lambda p, m: self._report_progress(p, m)
            )
            output_path = files[0] if files else None
        elif output_format == 'pdf':
            success, output_path, msg = powerpoint_backend.convert_to_pdf(
                input_path,
                output_dir,
                lambda p, m: self._report_progress(p, m)
            )
        else:
            return ConversionResult(False, input_path, error_message=f"Format {output_format} not supported by PowerPoint backend yet")

        duration = time.time() - start_time
        return ConversionResult(success, input_path, output_path, error_message=msg, duration_seconds=duration)

    def _convert_with_libreoffice(self, input_path, output_format, options, start_time):
        self._report_progress(0.1, f"Opening {input_path.name} (LibreOffice)")
        output_dir = options.output_dir or input_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if output_format in ('png', 'jpg', 'jpeg'):
            success, image_paths, msg = libreoffice_backend.convert_presentation_to_images(
                input_path, output_dir, output_format
            )
            output_path = image_paths[0] if image_paths else None
        else:
            success, output_path, msg = libreoffice_backend.convert(
                input_path, output_format, output_dir
            )
            
        duration = time.time() - start_time
        return ConversionResult(success, input_path, output_path, error_message=msg, duration_seconds=duration)
