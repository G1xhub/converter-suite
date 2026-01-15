"""
eBook Converter
Converts between eBook formats using Pandoc.
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
from ..backends.pandoc_backend import pandoc_backend

logger = logging.getLogger(__name__)


class EbookConverter(BaseConverter):
    """
    Converter for eBook files using Pandoc.
    Primary focus on EPUB conversions.
    """
    
    @property
    def category(self) -> ConversionCategory:
        return ConversionCategory.EBOOK
    
    @property
    def name(self) -> str:
        return "eBook Converter (Pandoc)"
    
    @property
    def supported_input_formats(self) -> list[str]:
        # Pandoc supports reading EPUB, but not MOBI directly involved without Calibre
        # We focus on converting TO/FROM epub
        return ['epub', 'docx', 'odt', 'txt', 'md', 'html', 'rtf', 'tex']
    
    @property
    def supported_output_formats(self) -> list[str]:
        return ['epub', 'pdf', 'docx', 'txt', 'html', 'md']
    
    def validate_dependencies(self) -> tuple[bool, str]:
        """Check if Pandoc is available."""
        if pandoc_backend.is_available():
            return True, "Pandoc available"
        return False, "Pandoc not found. Please install Pandoc for eBook conversion."
    
    def convert(
        self,
        input_path: Path,
        output_format: str,
        options: Optional[ConversionOptions] = None
    ) -> ConversionResult:
        """Convert an eBook file."""
        start_time = time.time()
        options = options or ConversionOptions()
        output_format = output_format.lower().lstrip('.')
        
        if not pandoc_backend.is_available():
            return ConversionResult(
                success=False,
                input_path=input_path,
                error_message="Pandoc not available"
            )
        
        try:
            self._report_progress(0.1, f"Reading {input_path.name}")
            
            # Determine output path
            output_path = self.get_output_path(input_path, output_format, options)
            
            # Handle overwrite
            if output_path.exists() and not options.overwrite:
                return ConversionResult(
                    success=False,
                    input_path=input_path,
                    error_message=f"Output file already exists: {output_path}"
                )
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._report_progress(0.3, f"Converting to {output_format.upper()}")
            
            # Use Pandoc for conversion
            # EPUB to PDF might require a specific PDF engine, handled by backend
            success, msg = pandoc_backend.convert(
                input_path,
                output_path
            )
            
            self._report_progress(1.0, "Complete")
            duration = time.time() - start_time
            
            if success:
                return ConversionResult(
                    success=True,
                    input_path=input_path,
                    output_path=output_path,
                    duration_seconds=duration
                )
            else:
                return ConversionResult(
                    success=False,
                    input_path=input_path,
                    error_message=msg,
                    duration_seconds=duration
                )
                
        except Exception as e:
            logger.exception(f"eBook conversion failed: {input_path}")
            return ConversionResult(
                success=False,
                input_path=input_path,
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )
