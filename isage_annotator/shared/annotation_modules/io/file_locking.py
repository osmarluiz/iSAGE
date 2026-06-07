"""
File Locking System for Annotation Modules
Provides robust file locking mechanisms to prevent data corruption
from concurrent access to sessions and datasets.
Based on legacy ABILIUS file locking implementation.
"""

import os
import time
import fcntl
import errno
from typing import Optional, Union
from pathlib import Path
from contextlib import contextmanager
import threading
import tempfile
import logging

logger = logging.getLogger(__name__)


class SessionLockError(Exception):
    """Exception raised when session locking fails."""
    pass


class FileLockError(Exception):
    """Exception raised when file locking fails."""
    pass


class SessionLockManager:
    """Manages exclusive locks on annotation sessions."""
    
    def __init__(self, timeout: int = 30):
        """
        Initialize session lock manager.
        
        Args:
            timeout: Maximum time to wait for lock acquisition (seconds)
        """
        self.timeout = timeout
        self.active_locks = {}  # Track active locks per thread
        self._lock = threading.Lock()
    
    @contextmanager
    def acquire_session_lock(self, session_dir: Union[str, Path], 
                           operation: str = "general", 
                           timeout: Optional[int] = None):
        """
        Acquire exclusive lock on session directory.
        
        Args:
            session_dir: Path to session directory
            operation: Description of operation requiring lock
            timeout: Override default timeout
            
        Yields:
            Lock context manager
            
        Raises:
            SessionLockError: If lock cannot be acquired
        """
        session_path = Path(session_dir)
        lock_file = session_path / ".session.lock"
        timeout = timeout or self.timeout
        
        # Ensure session directory exists
        session_path.mkdir(parents=True, exist_ok=True)
        
        # Create lock file
        lock_fd = None
        start_time = time.time()
        
        try:
            while True:
                try:
                    # Try to open lock file exclusively
                    lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    
                    # Write lock information
                    lock_info = f"PID: {os.getpid()}\nOperation: {operation}\nTime: {time.ctime()}\n"
                    os.write(lock_fd, lock_info.encode())
                    os.fsync(lock_fd)
                    
                    # Track this lock
                    thread_id = threading.get_ident()
                    with self._lock:
                        if thread_id not in self.active_locks:
                            self.active_locks[thread_id] = []
                        self.active_locks[thread_id].append((lock_file, lock_fd))
                    
                    logger.info(f"Acquired session lock: {session_path.name} for {operation}")
                    break
                    
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        # Lock file exists, check if it's stale
                        if self._is_stale_lock(lock_file):
                            logger.warning(f"Removing stale lock file: {lock_file}")
                            try:
                                lock_file.unlink()
                                continue
                            except FileNotFoundError:
                                pass  # Another process removed it
                        
                        # Check timeout
                        if time.time() - start_time > timeout:
                            raise SessionLockError(
                                f"Timeout waiting for session lock on {session_path}. "
                                f"Session may be in use by another process."
                            )
                        
                        # Wait and retry
                        time.sleep(0.1)
                    else:
                        raise SessionLockError(f"Failed to acquire session lock: {e}")
            
            yield
            
        finally:
            # Release lock
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                    lock_file.unlink()
                    
                    # Remove from tracking
                    thread_id = threading.get_ident()
                    with self._lock:
                        if thread_id in self.active_locks:
                            self.active_locks[thread_id] = [
                                (f, fd) for f, fd in self.active_locks[thread_id] 
                                if f != lock_file
                            ]
                            if not self.active_locks[thread_id]:
                                del self.active_locks[thread_id]
                    
                    logger.info(f"Released session lock: {session_path.name}")
                    
                except Exception as e:
                    logger.warning(f"Error releasing session lock: {e}")
    
    def _is_stale_lock(self, lock_file: Path) -> bool:
        """
        Check if a lock file is stale (from a dead process).
        
        Args:
            lock_file: Path to lock file
            
        Returns:
            True if lock is stale
        """
        try:
            if not lock_file.exists():
                return True
            
            # Check file age (consider locks older than 1 hour as stale)
            file_age = time.time() - lock_file.stat().st_mtime
            if file_age > 3600:  # 1 hour
                return True
            
            # Try to read PID from lock file
            try:
                with open(lock_file, 'r') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        if line.startswith('PID: '):
                            pid = int(line.split(': ')[1])
                            
                            # Check if process is still running
                            try:
                                os.kill(pid, 0)  # Signal 0 just checks if process exists
                                return False  # Process exists, lock is not stale
                            except ProcessLookupError:
                                return True  # Process doesn't exist, lock is stale
                            except PermissionError:
                                return False  # Process exists but we can't signal it
                            
            except (ValueError, IndexError, FileNotFoundError):
                pass  # Can't parse PID, assume it's stale
            
            return True
            
        except Exception:
            return False  # If in doubt, don't remove the lock
    
    def cleanup_stale_locks(self, sessions_dir: Union[str, Path]):
        """
        Clean up stale lock files in sessions directory.
        
        Args:
            sessions_dir: Directory containing session subdirectories
        """
        sessions_path = Path(sessions_dir)
        if not sessions_path.exists():
            return
        
        cleaned_count = 0
        for session_dir in sessions_path.iterdir():
            if session_dir.is_dir():
                lock_file = session_dir / ".session.lock"
                if lock_file.exists() and self._is_stale_lock(lock_file):
                    try:
                        lock_file.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned stale lock: {session_dir.name}")
                    except Exception as e:
                        logger.warning(f"Could not clean stale lock {lock_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned {cleaned_count} stale session locks")
    
    def is_session_locked(self, session_dir: Union[str, Path]) -> bool:
        """
        Check if a session is currently locked.
        
        Args:
            session_dir: Path to session directory
            
        Returns:
            True if session is locked
        """
        lock_file = Path(session_dir) / ".session.lock"
        return lock_file.exists() and not self._is_stale_lock(lock_file)
    
    def get_lock_info(self, session_dir: Union[str, Path]) -> Optional[dict]:
        """
        Get information about current session lock.
        
        Args:
            session_dir: Path to session directory
            
        Returns:
            Dictionary with lock information or None if not locked
        """
        lock_file = Path(session_dir) / ".session.lock"
        if not lock_file.exists():
            return None
        
        try:
            with open(lock_file, 'r') as f:
                content = f.read()
            
            info = {}
            for line in content.split('\n'):
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    info[key.lower()] = value
            
            return info
            
        except Exception:
            return None


class FileLockManager:
    """Manages file-level locking for specific operations."""
    
    @staticmethod
    @contextmanager
    def lock_file(file_path: Union[str, Path], 
                  mode: str = "r+", 
                  timeout: int = 10):
        """
        Acquire exclusive lock on a specific file.
        
        Args:
            file_path: Path to file to lock
            mode: File open mode
            timeout: Maximum time to wait for lock
            
        Yields:
            File handle with exclusive lock
            
        Raises:
            FileLockError: If lock cannot be acquired
        """
        file_path = Path(file_path)
        start_time = time.time()
        
        while True:
            try:
                # Open file and acquire lock
                file_handle = open(file_path, mode)
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                try:
                    yield file_handle
                finally:
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
                    file_handle.close()
                
                break
                
            except (IOError, OSError) as e:
                if hasattr(e, 'errno') and e.errno in (errno.EAGAIN, errno.EACCES):
                    # Lock is held by another process
                    if time.time() - start_time > timeout:
                        raise FileLockError(f"Timeout waiting for file lock: {file_path}")
                    time.sleep(0.1)
                else:
                    raise FileLockError(f"Failed to acquire file lock: {e}")
    
    @staticmethod
    @contextmanager
    def atomic_write(file_path: Union[str, Path], 
                     mode: str = "w", 
                     encoding: str = "utf-8"):
        """
        Perform atomic write operation with temporary file.
        
        Args:
            file_path: Target file path
            mode: Write mode
            encoding: File encoding
            
        Yields:
            Temporary file handle for writing
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temporary file in same directory
        temp_fd, temp_path = tempfile.mkstemp(
            suffix='.tmp',
            prefix=f'.{file_path.name}.',
            dir=file_path.parent
        )
        
        try:
            with os.fdopen(temp_fd, mode, encoding=encoding) as temp_file:
                yield temp_file
                temp_file.flush()
                os.fsync(temp_file.fileno())
            
            # Atomic move
            temp_path_obj = Path(temp_path)
            temp_path_obj.replace(file_path)
            
        except Exception:
            # Clean up temporary file on error
            try:
                Path(temp_path).unlink()
            except FileNotFoundError:
                pass
            raise


# Global session lock manager instance
session_lock_manager = SessionLockManager()


# Convenience functions
def acquire_session_lock(session_dir: Union[str, Path], 
                        operation: str = "general",
                        timeout: Optional[int] = None):
    """
    Acquire session lock (convenience function).
    
    Args:
        session_dir: Path to session directory
        operation: Description of operation
        timeout: Lock timeout
        
    Returns:
        Context manager for session lock
    """
    return session_lock_manager.acquire_session_lock(session_dir, operation, timeout)


def is_session_locked(session_dir: Union[str, Path]) -> bool:
    """
    Check if session is locked (convenience function).
    
    Args:
        session_dir: Path to session directory
        
    Returns:
        True if session is locked
    """
    return session_lock_manager.is_session_locked(session_dir)


def cleanup_stale_locks(sessions_dir: Union[str, Path]):
    """
    Clean up stale locks (convenience function).
    
    Args:
        sessions_dir: Directory containing sessions
    """
    session_lock_manager.cleanup_stale_locks(sessions_dir)


# Context manager for file operations
lock_file = FileLockManager.lock_file
atomic_write = FileLockManager.atomic_write