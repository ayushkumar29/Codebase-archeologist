import logging
import pathspec
from pathlib import Path
from typing import Generator, List, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


class CodeScanner:
    
    DEFAULT_IGNORE_DIRS = {
        ".git", ".svn", ".hg",
        "__pycache__", ".pytest_cache", ".mypy_cache",
        "node_modules", ".venv", "venv", "env",
        "dist", "build", ".tox", ".eggs",
        ".idea", ".vscode"
    }
    
    def __init__(
        self,
        extensions: Optional[list[str]] = None,
        ignore_dirs: Optional[set[str]] = None
    ):
        default_extensions = [".py", ".js", ".ts", ".jsx", ".tsx"]
        
        if extensions is None:
            try:
                from src.config import get_settings
                settings = get_settings()
                extensions = settings.supported_extensions
            except Exception:
                extensions = default_extensions
                
        self.extensions = set(extensions)
        self.ignore_dirs = ignore_dirs or self.DEFAULT_IGNORE_DIRS
        
    def scan(self, root_path: Path | str) -> Generator[Path, None, None]:
        root = Path(root_path)
        
        if not root.exists():
            raise FileNotFoundError(f"Path does not exist: {root}")
            
        if root.is_file():
            if root.suffix in self.extensions:
                yield root
            return
            
        logger.info(f"Scanning directory: {root}")
        file_count = 0
        
        for path in root.rglob("*"):
            if any(ignored in path.parts for ignored in self.ignore_dirs):
                continue
                
            if path.is_file() and path.suffix in self.extensions:
                file_count += 1
                logger.debug(f"Found: {path}")
                yield path
                
        logger.info(f"Scan complete. Found {file_count} files.")
        
    def scan_to_list(self, root_path: Path | str) -> list[Path]:
        return list(self.scan(root_path))
    
    def get_file_info(self, file_path: Path) -> dict:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")
        
        return {
            "path": str(file_path.absolute()),
            "name": file_path.name,
            "extension": file_path.suffix,
            "language": self._extension_to_language(file_path.suffix),
            "lines_of_code": len([l for l in lines if l.strip()]),
            "total_lines": len(lines),
            "size_bytes": file_path.stat().st_size
        }
    
    @staticmethod
    def _extension_to_language(ext: str) -> str:
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby"
        }
        return mapping.get(ext, "unknown")
