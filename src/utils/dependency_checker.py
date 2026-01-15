"""
Dependency Checker
Validates and locates required external tools (FFmpeg, Pandoc, LibreOffice).
"""

import os
import shutil
import subprocess
import platform
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about an external dependency."""
    name: str
    available: bool
    path: Optional[Path] = None
    version: Optional[str] = None
    error: Optional[str] = None


class DependencyChecker:
    """
    Checks for and locates external dependencies.
    Supports bundled dependencies in ./deps/ and system-installed versions.
    """
    
    def __init__(self, app_dir: Optional[Path] = None):
        """
        Initialize dependency checker.
        
        Args:
            app_dir: Root directory of the application (for bundled deps)
        """
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.app_dir = Path(sys.executable).parent
        else:
            # Running from source
            self.app_dir = app_dir or Path(__file__).parent.parent.parent
            
        self.deps_dir = self.app_dir / "deps"
        self.system = platform.system().lower()  # 'windows', 'darwin', 'linux'
        
        # Cache for found paths
        self._cache: dict[str, DependencyInfo] = {}
    
    def _get_platform_subdir(self) -> str:
        """Get platform-specific subdirectory name."""
        if self.system == 'windows':
            return 'win'
        elif self.system == 'darwin':
            return 'mac'
        return 'linux'
    
    def _get_executable_name(self, base_name: str) -> str:
        """Get platform-specific executable name."""
        if self.system == 'windows':
            return f"{base_name}.exe"
        return base_name
    
    def _run_version_command(self, executable: Path, args: list[str]) -> Optional[str]:
        """Run a version command and extract version string."""
        try:
            result = subprocess.run(
                [str(executable)] + args,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if self.system == 'windows' else 0
            )
            output = result.stdout or result.stderr
            # Extract first line as version info
            if output:
                return output.strip().split('\n')[0][:100]
        except Exception as e:
            logger.debug(f"Failed to get version for {executable}: {e}")
        return None
    
    def _find_in_bundled(self, name: str) -> Optional[Path]:
        """Look for bundled dependency."""
        # Check standard structure: deps/name/platform/exe
        platform_dir = self.deps_dir / name / self._get_platform_subdir()
        executable = platform_dir / self._get_executable_name(name)
        
        if executable.exists() and executable.is_file():
            return executable
        
        # Also check direct in deps folder: deps/name/exe
        executable = self.deps_dir / name / self._get_executable_name(name)
        if executable.exists():
            return executable
            
        return None
    
    def _find_in_path(self, name: str) -> Optional[Path]:
        """Look for dependency in system PATH."""
        executable = shutil.which(name)
        if executable:
            return Path(executable)
        return None
    
    def _find_libreoffice(self) -> Optional[Path]:
        """Find LibreOffice soffice executable."""
        # Check bundled first
        bundled = self._find_in_bundled('libreoffice')
        if bundled:
            return bundled
        
        # Platform-specific locations
        if self.system == 'windows':
            possible_paths = [
                Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'LibreOffice' / 'program' / 'soffice.exe',
                Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'LibreOffice' / 'program' / 'soffice.exe',
                Path.home() / 'LibreOfficePortable' / 'App' / 'libreoffice' / 'program' / 'soffice.exe',
            ]
        elif self.system == 'darwin':
            possible_paths = [
                Path('/Applications/LibreOffice.app/Contents/MacOS/soffice'),
                Path.home() / 'Applications/LibreOffice.app/Contents/MacOS/soffice',
            ]
        else:  # Linux
            possible_paths = [
                Path('/usr/bin/soffice'),
                Path('/usr/bin/libreoffice'),
                Path('/snap/bin/libreoffice'),
                Path.home() / '.local/bin/soffice',
            ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Fall back to PATH
        return self._find_in_path('soffice') or self._find_in_path('libreoffice')
    
    def check_ffmpeg(self) -> DependencyInfo:
        """Check for FFmpeg availability."""
        if 'ffmpeg' in self._cache:
            return self._cache['ffmpeg']
        
        path = self._find_in_bundled('ffmpeg') or self._find_in_path('ffmpeg')
        
        if path:
            version = self._run_version_command(path, ['-version'])
            info = DependencyInfo(
                name='FFmpeg',
                available=True,
                path=path,
                version=version
            )
        else:
            info = DependencyInfo(
                name='FFmpeg',
                available=False,
                error='FFmpeg not found. Required for video/audio conversion.'
            )
        
        self._cache['ffmpeg'] = info
        return info
    
    def check_pandoc(self) -> DependencyInfo:
        """Check for Pandoc availability."""
        if 'pandoc' in self._cache:
            return self._cache['pandoc']
        
        path = self._find_in_bundled('pandoc') or self._find_in_path('pandoc')
        
        if path:
            version = self._run_version_command(path, ['--version'])
            info = DependencyInfo(
                name='Pandoc',
                available=True,
                path=path,
                version=version
            )
        else:
            info = DependencyInfo(
                name='Pandoc',
                available=False,
                error='Pandoc not found. Required for document conversion.'
            )
        
        self._cache['pandoc'] = info
        return info
    
    def check_libreoffice(self) -> DependencyInfo:
        """Check for LibreOffice availability."""
        if 'libreoffice' in self._cache:
            return self._cache['libreoffice']
        
        path = self._find_libreoffice()
        
        if path:
            version = self._run_version_command(path, ['--version'])
            info = DependencyInfo(
                name='LibreOffice',
                available=True,
                path=path,
                version=version
            )
        else:
            info = DependencyInfo(
                name='LibreOffice',
                available=False,
                error='LibreOffice not found. Required for presentation/document conversion.'
            )
        
        self._cache['libreoffice'] = info
        return info
    
    def check_poppler(self) -> DependencyInfo:
        """Check for Poppler (pdftoppm/pdftocairo) availability."""
        if 'poppler' in self._cache:
            return self._cache['poppler']
        
        # Look for pdftoppm which is part of poppler-utils
        path = self._find_in_bundled('poppler') or self._find_in_path('pdftoppm')
        
        if path:
            version = self._run_version_command(path, ['-v'])
            info = DependencyInfo(
                name='Poppler',
                available=True,
                path=path,
                version=version
            )
        else:
            info = DependencyInfo(
                name='Poppler',
                available=False,
                error='Poppler not found. Required for PDF to image conversion.'
            )
        
        self._cache['poppler'] = info
        return info
    
    def check_all(self) -> dict[str, DependencyInfo]:
        """Check all dependencies and return status dict."""
        return {
            'ffmpeg': self.check_ffmpeg(),
            'pandoc': self.check_pandoc(),
            'libreoffice': self.check_libreoffice(),
            'poppler': self.check_poppler(),
        }
    
    def get_missing_dependencies(self) -> list[DependencyInfo]:
        """Get list of missing dependencies."""
        all_deps = self.check_all()
        return [dep for dep in all_deps.values() if not dep.available]
    
    def clear_cache(self) -> None:
        """Clear cached dependency information."""
        self._cache.clear()
    
    def get_ffmpeg_path(self) -> Optional[Path]:
        """Get FFmpeg executable path or None."""
        info = self.check_ffmpeg()
        return info.path if info.available else None
    
    def get_pandoc_path(self) -> Optional[Path]:
        """Get Pandoc executable path or None."""
        info = self.check_pandoc()
        return info.path if info.available else None
    
    def get_libreoffice_path(self) -> Optional[Path]:
        """Get LibreOffice executable path or None."""
        info = self.check_libreoffice()
        return info.path if info.available else None


# Global instance
dependency_checker = DependencyChecker()
