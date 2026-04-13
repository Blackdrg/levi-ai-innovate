import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class FileSystemInterface:
    """
    Sovereign v15.0: Sandboxed File System Interface.
    Enforces strict boundaries: only temp levi_sandbox directory.
    Includes directory traversal protection and size limits.
    """
    
    # Cross-platform temp directory support (Windows/Linux)
    SANDBOX_ROOT = Path(tempfile.gettempdir()) / "levi_sandbox"
    MAX_FILE_SIZE_MB = 100
    ALLOWED_EXTENSIONS = {
        ".py", ".txt", ".json", ".csv", ".md",
        ".yaml", ".yml", ".sql", ".sh"
    }
    
    def __init__(self, mission_id: str):
        """
        Initialize FileSystemInterface for a specific mission.
        """
        self.mission_id = mission_id
        self.mission_dir = (self.SANDBOX_ROOT / mission_id).resolve()
        self._ensure_sandbox_exists()
    
    def _ensure_sandbox_exists(self):
        """Create mission specific sandbox directory."""
        if not self.SANDBOX_ROOT.exists():
            self.SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
            
        self.mission_dir.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions (rwx------)
        try:
            os.chmod(self.mission_dir, 0o700)
        except Exception as e:
            logger.warning(f"[Sandbox] Failed to set permissions on {self.mission_dir}: {e}")
    
    def _validate_path(self, file_path: str) -> Path:
        """
        Validate that a path is within sandbox boundaries.
        Prevents directory traversal attacks.
        """
        # Join and resolve to absolute path
        requested_path = (self.mission_dir / file_path).resolve()
        
        # Check if resolved path starts with the mission_dir
        if not str(requested_path).startswith(str(self.mission_dir)):
            logger.critical(f"[Security] Sandbox escape attempt: {file_path}")
            raise PermissionError(f"Access denied: {file_path} is outside of sandbox.")
        
        return requested_path
    
    def _validate_extension(self, file_path: Path):
        """Validate file extension is in the whitelist."""
        if file_path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"Extension {file_path.suffix} not allowed in sandbox.")
    
    async def read_file(self, file_path: str) -> str:
        """Read file contents safely."""
        path = self._validate_path(file_path)
        
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise IOError(f"File too large: {file_size_mb:.1f}MB (max {self.MAX_FILE_SIZE_MB}MB)")
            
        # Perform read in thread
        return await asyncio.to_thread(self._read_sync, path)

    def _read_sync(self, path: Path) -> str:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def write_file(self, file_path: str, content: str) -> str:
        """Write file contents safely."""
        path = self._validate_path(file_path)
        self._validate_extension(path)
        
        # Ensure parent directory exists within sandbox
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Perform write in thread
        return await asyncio.to_thread(self._write_sync, path, content)

    def _write_sync(self, path: Path, content: str) -> str:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return str(path)
    
    async def list_files(self, directory: str = "") -> List[str]:
        """List files within the mission sandbox."""
        path = self._validate_path(directory)
        
        if not path.is_dir():
            raise ValueError(f"Not a directory: {directory}")
            
        def _list():
            return [str(f.relative_to(self.mission_dir)) for f in path.glob("**/*") if f.is_file()]
            
        return await asyncio.to_thread(_list)

    def cleanup(self):
        """Delete mission sandbox directory."""
        import shutil
        if self.mission_dir.exists():
            shutil.rmtree(self.mission_dir)
            logger.info(f"[Sandbox] Cleaned up mission workspace: {self.mission_id}")

class ArtisanAgentFS:
    """Helper for ArtisanAgent to use the sandbox."""
    def __init__(self, mission_id: str):
        self.fs = FileSystemInterface(mission_id)

    async def run_operation(self, op: str, **kwargs):
        if op == "read":
            return await self.fs.read_file(kwargs["path"])
        elif op == "write":
            return await self.fs.write_file(kwargs["path"], kwargs["content"])
        elif op == "list":
            return await self.fs.list_files(kwargs.get("path", ""))
        else:
            raise ValueError(f"Unknown FS operation: {op}")
