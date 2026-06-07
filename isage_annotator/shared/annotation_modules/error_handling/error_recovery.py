"""
Error Recovery System for Annotation System
Provides automated recovery mechanisms for common error scenarios.
Based on legacy ABILIUS error recovery implementation.
"""

import os
import time
import threading
import tempfile
import shutil
from typing import Dict, List, Optional, Callable, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

from .error_manager import ErrorInfo, ErrorSeverity, ErrorCategory, get_global_error_manager

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategy types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    RESTORE_BACKUP = "restore_backup"
    CLEAR_CACHE = "clear_cache"
    RESTART_COMPONENT = "restart_component"
    USER_INTERVENTION = "user_intervention"
    IGNORE = "ignore"


@dataclass
class RecoveryAction:
    """Recovery action definition."""
    strategy: RecoveryStrategy
    description: str
    action_func: Callable[[ErrorInfo], bool]
    max_attempts: int = 3
    retry_delay: float = 1.0
    prerequisites: List[str] = None


class ErrorRecovery:
    """Automated error recovery system."""
    
    def __init__(self):
        self._recovery_actions: Dict[ErrorCategory, List[RecoveryAction]] = {}
        self._recovery_history: Dict[str, List[str]] = {}  # error_id -> list of attempted strategies
        self._component_restarters: Dict[str, Callable[[], bool]] = {}
        self._backup_managers: Dict[str, 'BackupManager'] = {}
        
        # Recovery statistics
        self._recovery_stats: Dict[RecoveryStrategy, Dict[str, int]] = {}
        for strategy in RecoveryStrategy:
            self._recovery_stats[strategy] = {'attempts': 0, 'successes': 0, 'failures': 0}
        
        # Threading
        self._lock = threading.RLock()
        
        # Setup default recovery actions
        self._setup_default_recovery_actions()
        
        # Register with error manager
        error_manager = get_global_error_manager()
        error_manager.register_recovery_handler(ErrorCategory.IO_ERROR, self.handle_io_error)
        error_manager.register_recovery_handler(ErrorCategory.MEMORY_ERROR, self.handle_memory_error)
        error_manager.register_recovery_handler(ErrorCategory.NETWORK_ERROR, self.handle_network_error)
        error_manager.register_recovery_handler(ErrorCategory.DATA_ERROR, self.handle_data_error)
        error_manager.register_recovery_handler(ErrorCategory.UI_ERROR, self.handle_ui_error)
    
    def register_component_restarter(self, component: str, restart_func: Callable[[], bool]) -> None:
        """Register component restart function."""
        with self._lock:
            self._component_restarters[component] = restart_func
    
    def register_backup_manager(self, component: str, backup_manager: 'BackupManager') -> None:
        """Register backup manager for component."""
        with self._lock:
            self._backup_managers[component] = backup_manager
    
    def add_recovery_action(self, category: ErrorCategory, action: RecoveryAction) -> None:
        """Add recovery action for error category."""
        with self._lock:
            if category not in self._recovery_actions:
                self._recovery_actions[category] = []
            self._recovery_actions[category].append(action)
    
    def attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt recovery for error."""
        with self._lock:
            error_id = error_info.error_id
            
            # Initialize recovery history
            if error_id not in self._recovery_history:
                self._recovery_history[error_id] = []
            
            # Get recovery actions for this category
            actions = self._recovery_actions.get(error_info.category, [])
            
            for action in actions:
                # Skip if already tried this strategy
                if action.strategy.value in self._recovery_history[error_id]:
                    continue
                
                # Check prerequisites
                if action.prerequisites and not self._check_prerequisites(action.prerequisites):
                    continue
                
                # Attempt recovery
                if self._attempt_action(error_info, action):
                    return True
            
            return False
    
    def _attempt_action(self, error_info: ErrorInfo, action: RecoveryAction) -> bool:
        """Attempt specific recovery action."""
        strategy = action.strategy
        error_id = error_info.error_id
        
        logger.info(f"Attempting recovery strategy '{strategy.value}' for error {error_id}")
        
        # Update statistics
        self._recovery_stats[strategy]['attempts'] += 1
        
        # Record attempt
        self._recovery_history[error_id].append(strategy.value)
        
        for attempt in range(action.max_attempts):
            try:
                if action.action_func(error_info):
                    logger.info(f"Recovery successful: {strategy.value} for error {error_id}")
                    self._recovery_stats[strategy]['successes'] += 1
                    return True
                
                # Wait before retry
                if attempt < action.max_attempts - 1:
                    time.sleep(action.retry_delay * (attempt + 1))  # Exponential backoff
                    
            except Exception as e:
                logger.warning(f"Recovery action {strategy.value} failed: {e}")
        
        logger.warning(f"Recovery failed: {strategy.value} for error {error_id}")
        self._recovery_stats[strategy]['failures'] += 1
        return False
    
    def _check_prerequisites(self, prerequisites: List[str]) -> bool:
        """Check if prerequisites are met."""
        for prereq in prerequisites:
            if prereq == "disk_space":
                if not self._check_disk_space():
                    return False
            elif prereq == "write_permission":
                if not self._check_write_permission():
                    return False
            elif prereq == "network_connectivity":
                if not self._check_network_connectivity():
                    return False
        return True
    
    def _check_disk_space(self, min_space_mb: int = 100) -> bool:
        """Check if sufficient disk space is available."""
        try:
            temp_dir = tempfile.gettempdir()
            stat = shutil.disk_usage(temp_dir)
            free_mb = stat.free / (1024 * 1024)
            return free_mb >= min_space_mb
        except Exception:
            return False
    
    def _check_write_permission(self) -> bool:
        """Check if write permission is available."""
        try:
            temp_dir = tempfile.gettempdir()
            test_file = Path(temp_dir) / f"test_write_{os.getpid()}.tmp"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False
    
    def _check_network_connectivity(self) -> bool:
        """Check basic network connectivity."""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except Exception:
            return False
    
    # Specific error handlers
    
    def handle_io_error(self, error_info: ErrorInfo) -> bool:
        """Handle I/O errors."""
        return self.attempt_recovery(error_info)
    
    def handle_memory_error(self, error_info: ErrorInfo) -> bool:
        """Handle memory errors."""
        return self.attempt_recovery(error_info)
    
    def handle_network_error(self, error_info: ErrorInfo) -> bool:
        """Handle network errors."""
        return self.attempt_recovery(error_info)
    
    def handle_data_error(self, error_info: ErrorInfo) -> bool:
        """Handle data errors."""
        return self.attempt_recovery(error_info)
    
    def handle_ui_error(self, error_info: ErrorInfo) -> bool:
        """Handle UI errors."""
        return self.attempt_recovery(error_info)
    
    # Recovery action implementations
    
    def _retry_operation(self, error_info: ErrorInfo) -> bool:
        """Simple retry recovery."""
        try:
            # Extract retry information from context
            retry_func = error_info.context.get('retry_func')
            if retry_func and callable(retry_func):
                return retry_func()
            
            logger.warning(f"No retry function available for error {error_info.error_id}")
            return False
            
        except Exception as e:
            logger.warning(f"Retry failed: {e}")
            return False
    
    def _clear_cache_recovery(self, error_info: ErrorInfo) -> bool:
        """Clear cache recovery."""
        try:
            # Try to clear various caches
            from ..cache.smart_cache import clear_global_cache
            clear_global_cache()
            
            # Clear component-specific cache if available
            cache_manager = error_info.context.get('cache_manager')
            if cache_manager and hasattr(cache_manager, 'clear'):
                cache_manager.clear()
            
            logger.info("Cache cleared for recovery")
            return True
            
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")
            return False
    
    def _restart_component_recovery(self, error_info: ErrorInfo) -> bool:
        """Restart component recovery."""
        try:
            component = error_info.component
            
            if component in self._component_restarters:
                restart_func = self._component_restarters[component]
                return restart_func()
            
            logger.warning(f"No restart function registered for component {component}")
            return False
            
        except Exception as e:
            logger.warning(f"Component restart failed: {e}")
            return False
    
    def _restore_backup_recovery(self, error_info: ErrorInfo) -> bool:
        """Restore from backup recovery."""
        try:
            component = error_info.component
            
            if component in self._backup_managers:
                backup_manager = self._backup_managers[component]
                return backup_manager.restore_latest_backup()
            
            # Try to restore from context information
            backup_path = error_info.context.get('backup_path')
            target_path = error_info.context.get('target_path')
            
            if backup_path and target_path:
                backup_path = Path(backup_path)
                target_path = Path(target_path)
                
                if backup_path.exists():
                    shutil.copy2(backup_path, target_path)
                    logger.info(f"Restored {target_path} from backup")
                    return True
            
            logger.warning(f"No backup available for component {component}")
            return False
            
        except Exception as e:
            logger.warning(f"Backup restore failed: {e}")
            return False
    
    def _fallback_recovery(self, error_info: ErrorInfo) -> bool:
        """Fallback recovery using alternative method."""
        try:
            fallback_func = error_info.context.get('fallback_func')
            if fallback_func and callable(fallback_func):
                return fallback_func()
            
            # Generic fallback strategies
            if error_info.category == ErrorCategory.IO_ERROR:
                return self._io_fallback_recovery(error_info)
            elif error_info.category == ErrorCategory.MEMORY_ERROR:
                return self._memory_fallback_recovery(error_info)
            
            return False
            
        except Exception as e:
            logger.warning(f"Fallback recovery failed: {e}")
            return False
    
    def _io_fallback_recovery(self, error_info: ErrorInfo) -> bool:
        """I/O specific fallback recovery."""
        try:
            # Try alternative file operations
            file_path = error_info.context.get('file_path')
            if file_path:
                file_path = Path(file_path)
                
                # Try creating parent directories
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Try with temporary file
                temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
                if temp_path.exists():
                    temp_path.replace(file_path)
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _memory_fallback_recovery(self, error_info: ErrorInfo) -> bool:
        """Memory specific fallback recovery."""
        try:
            # Clear caches
            self._clear_cache_recovery(error_info)
            
            # Try garbage collection
            import gc
            gc.collect()
            
            # Reduce batch size if available
            batch_size = error_info.context.get('batch_size')
            if batch_size and batch_size > 1:
                new_batch_size = max(1, batch_size // 2)
                error_info.context['batch_size'] = new_batch_size
                logger.info(f"Reduced batch size from {batch_size} to {new_batch_size}")
                return True
            
            return False
            
        except Exception:
            return False
    
    def _setup_default_recovery_actions(self) -> None:
        """Setup default recovery actions for each error category."""
        
        # I/O Error recovery actions
        self.add_recovery_action(ErrorCategory.IO_ERROR, RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            description="Retry file operation",
            action_func=self._retry_operation,
            max_attempts=3,
            retry_delay=1.0
        ))
        
        self.add_recovery_action(ErrorCategory.IO_ERROR, RecoveryAction(
            strategy=RecoveryStrategy.FALLBACK,
            description="Use alternative file operation",
            action_func=self._fallback_recovery,
            max_attempts=1
        ))
        
        self.add_recovery_action(ErrorCategory.IO_ERROR, RecoveryAction(
            strategy=RecoveryStrategy.RESTORE_BACKUP,
            description="Restore from backup",
            action_func=self._restore_backup_recovery,
            max_attempts=1
        ))
        
        # Memory Error recovery actions
        self.add_recovery_action(ErrorCategory.MEMORY_ERROR, RecoveryAction(
            strategy=RecoveryStrategy.CLEAR_CACHE,
            description="Clear cache to free memory",
            action_func=self._clear_cache_recovery,
            max_attempts=1
        ))
        
        self.add_recovery_action(ErrorCategory.MEMORY_ERROR, RecoveryAction(
            strategy=RecoveryStrategy.FALLBACK,
            description="Use memory-efficient alternative",
            action_func=self._fallback_recovery,
            max_attempts=1
        ))
        
        # Network Error recovery actions
        self.add_recovery_action(ErrorCategory.NETWORK_ERROR, RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            description="Retry network operation",
            action_func=self._retry_operation,
            max_attempts=5,
            retry_delay=2.0,
            prerequisites=["network_connectivity"]
        ))
        
        # Data Error recovery actions
        self.add_recovery_action(ErrorCategory.DATA_ERROR, RecoveryAction(
            strategy=RecoveryStrategy.RESTORE_BACKUP,
            description="Restore data from backup",
            action_func=self._restore_backup_recovery,
            max_attempts=1
        ))
        
        # UI Error recovery actions
        self.add_recovery_action(ErrorCategory.UI_ERROR, RecoveryAction(
            strategy=RecoveryStrategy.RESTART_COMPONENT,
            description="Restart UI component",
            action_func=self._restart_component_recovery,
            max_attempts=1
        ))
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        with self._lock:
            stats = {
                'total_recovery_attempts': sum(
                    data['attempts'] for data in self._recovery_stats.values()
                ),
                'total_recovery_successes': sum(
                    data['successes'] for data in self._recovery_stats.values()
                ),
                'strategy_stats': {}
            }
            
            for strategy, data in self._recovery_stats.items():
                success_rate = 0
                if data['attempts'] > 0:
                    success_rate = data['successes'] / data['attempts']
                
                stats['strategy_stats'][strategy.value] = {
                    'attempts': data['attempts'],
                    'successes': data['successes'],
                    'failures': data['failures'],
                    'success_rate': success_rate
                }
            
            # Overall success rate
            if stats['total_recovery_attempts'] > 0:
                stats['overall_success_rate'] = stats['total_recovery_successes'] / stats['total_recovery_attempts']
            else:
                stats['overall_success_rate'] = 0
            
            return stats


class BackupManager:
    """Manages backups for error recovery."""
    
    def __init__(self, component_name: str, backup_dir: Union[str, Path] = None):
        self.component_name = component_name
        self.backup_dir = Path(backup_dir) if backup_dir else Path(tempfile.gettempdir()) / "annotation_backups" / component_name
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self.max_backups = 10
    
    def create_backup(self, source_path: Union[str, Path], backup_name: str = None) -> Optional[Path]:
        """Create backup of file or directory."""
        try:
            with self._lock:
                source_path = Path(source_path)
                
                if not source_path.exists():
                    return None
                
                if backup_name is None:
                    timestamp = int(time.time())
                    backup_name = f"{source_path.name}_{timestamp}"
                
                backup_path = self.backup_dir / backup_name
                
                if source_path.is_file():
                    shutil.copy2(source_path, backup_path)
                else:
                    shutil.copytree(source_path, backup_path)
                
                # Clean old backups
                self._cleanup_old_backups()
                
                logger.info(f"Created backup: {backup_path}")
                return backup_path
                
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
            return None
    
    def restore_latest_backup(self) -> bool:
        """Restore the most recent backup."""
        try:
            with self._lock:
                backups = list(self.backup_dir.glob("*"))
                if not backups:
                    return False
                
                # Sort by modification time
                latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
                
                # This is a simplified restore - in practice, you'd need target path
                logger.info(f"Would restore from: {latest_backup}")
                return True
                
        except Exception as e:
            logger.warning(f"Failed to restore backup: {e}")
            return False
    
    def _cleanup_old_backups(self) -> None:
        """Remove old backups beyond max_backups limit."""
        try:
            backups = list(self.backup_dir.glob("*"))
            if len(backups) <= self.max_backups:
                return
            
            # Sort by modification time and remove oldest
            backups.sort(key=lambda p: p.stat().st_mtime)
            
            for backup in backups[:-self.max_backups]:
                if backup.is_file():
                    backup.unlink()
                else:
                    shutil.rmtree(backup)
                logger.info(f"Removed old backup: {backup}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")


# Global error recovery instance
_global_error_recovery: Optional[ErrorRecovery] = None
_recovery_lock = threading.Lock()


def get_global_error_recovery() -> ErrorRecovery:
    """Get or create global error recovery instance."""
    global _global_error_recovery
    if _global_error_recovery is None:
        with _recovery_lock:
            if _global_error_recovery is None:
                _global_error_recovery = ErrorRecovery()
    return _global_error_recovery