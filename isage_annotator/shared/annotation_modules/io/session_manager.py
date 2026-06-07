"""
Session Manager - Manages annotation sessions with recovery

This module provides session management functionality with crash recovery,
session persistence, and multi-session support.
"""

import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from ..base_protocols import BaseComponent, AnnotationData
from .json_saver import JsonSaver
from .json_loader import JsonLoader
from .auto_saver import AutoSaver
from .file_locking import acquire_session_lock, is_session_locked, cleanup_stale_locks


class SessionManager(BaseComponent):
    """Manages annotation sessions with recovery support."""
    
    # Session manager signals
    sessionStarted = pyqtSignal(str)  # session_id
    sessionSaved = pyqtSignal(str)  # session_id
    sessionLoaded = pyqtSignal(str)  # session_id
    sessionEnded = pyqtSignal(str)  # session_id
    sessionRecovered = pyqtSignal(str)  # session_id
    
    def __init__(self, name: str = "session_manager", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Session configuration
        self._session_directory: Optional[str] = None
        self._current_session_id: Optional[str] = None
        self._session_metadata: Dict[str, Any] = {}
        
        # Session settings
        self._auto_save_enabled: bool = True
        self._recovery_enabled: bool = True
        self._session_timeout: float = 3600.0  # 1 hour
        self._max_sessions: int = 100
        self._session_locking_enabled: bool = True
        
        # Session state
        self._session_start_time: float = 0.0
        self._session_data: Optional[AnnotationData] = None
        self._session_active: bool = False
        self._session_modified: bool = False
        self._session_lock_context = None
        
        # Components
        self._json_saver: JsonSaver = JsonSaver()
        self._json_loader: JsonLoader = JsonLoader()
        self._auto_saver: Optional[AutoSaver] = None
        
        # Session history
        self._session_history: List[Dict[str, Any]] = []
        self._recovery_sessions: List[Dict[str, Any]] = []
    
    def initialize(self, **kwargs) -> bool:
        """Initialize session manager."""
        self._session_directory = kwargs.get('session_directory', None)
        self._auto_save_enabled = kwargs.get('auto_save_enabled', True)
        self._recovery_enabled = kwargs.get('recovery_enabled', True)
        self._session_timeout = kwargs.get('session_timeout', 3600.0)
        self._max_sessions = kwargs.get('max_sessions', 100)
        
        # Initialize components
        saver_config = kwargs.get('saver_config', {})
        loader_config = kwargs.get('loader_config', {})
        
        self._json_saver.initialize(**saver_config)
        self._json_loader.initialize(**loader_config)
        
        # Set up session directory
        if self._session_directory:
            self._setup_session_directory()
        
        # Load session history
        self._load_session_history()
        
        # Check for recovery sessions
        if self._recovery_enabled:
            self._check_recovery_sessions()
        
        return super().initialize(**kwargs)
    
    def start_session(self, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start a new annotation session."""
        try:
            # End current session if active
            if self._session_active:
                self.end_session()
            
            # Generate session ID if not provided
            if session_id is None:
                session_id = self._generate_session_id()
            
            # Initialize session
            self._current_session_id = session_id
            self._session_start_time = time.time()
            self._session_metadata = metadata or {}
            self._session_active = True
            self._session_modified = False
            
            # Add system metadata
            self._session_metadata.update({
                'session_id': session_id,
                'start_time': self._session_start_time,
                'start_datetime': datetime.now().isoformat(),
                'manager_version': self._version
            })
            
            # Create session directory
            if self._session_directory:
                session_dir = self._get_session_directory(session_id)
                os.makedirs(session_dir, exist_ok=True)
                
                # Acquire session lock
                if self._session_locking_enabled:
                    self._acquire_session_lock(session_dir)
            
            # Setup auto saver
            if self._auto_save_enabled:
                self._setup_auto_saver()
            
            # Save initial session state
            self._save_session_state()
            
            # Update history
            self._add_to_session_history(session_id, 'started')
            
            self.sessionStarted.emit(session_id)
            self.emit_state_changed({
                'session_active': True,
                'current_session': session_id,
                'session_start_time': self._session_start_time
            })
            
            return session_id
            
        except Exception as e:
            self.emit_error(f"Error starting session: {str(e)}")
            return ""
    
    def end_session(self, save_session: bool = True) -> bool:
        """End current annotation session."""
        if not self._session_active:
            return True
        
        try:
            # Stop auto saver
            if self._auto_saver:
                self._auto_saver.stop()
                self._auto_saver = None
            
            # Save session if requested
            if save_session:
                self.save_session()
            
            # Update session metadata
            self._session_metadata.update({
                'end_time': time.time(),
                'end_datetime': datetime.now().isoformat(),
                'duration': time.time() - self._session_start_time,
                'modified': self._session_modified
            })
            
            # Save final session state
            self._save_session_state()
            
            # Update history
            self._add_to_session_history(self._current_session_id, 'ended')
            
            session_id = self._current_session_id
            
            # Release session lock
            if self._session_locking_enabled:
                self._release_session_lock()
            
            # Clear session state
            self._current_session_id = None
            self._session_start_time = 0.0
            self._session_metadata.clear()
            self._session_active = False
            self._session_modified = False
            self._session_data = None
            
            self.sessionEnded.emit(session_id)
            self.emit_state_changed({
                'session_active': False,
                'current_session': None
            })
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error ending session: {str(e)}")
            return False
    
    def save_session(self, session_path: Optional[str] = None) -> bool:
        """Save current session data."""
        if not self._session_active or not self._current_session_id:
            return False
        
        try:
            # Determine save path
            if session_path is None:
                session_path = self._get_session_file_path(self._current_session_id)
            
            # Create session save data
            session_data = {
                'session_metadata': self._session_metadata,
                'annotation_data': self._session_data.to_dict() if self._session_data else None,
                'save_time': time.time(),
                'save_datetime': datetime.now().isoformat()
            }
            
            # Save session
            success = self._json_saver.save_session_data(session_data, session_path)
            
            if success:
                self._session_modified = False
                self._add_to_session_history(self._current_session_id, 'saved')
                
                self.sessionSaved.emit(self._current_session_id)
                self.emit_state_changed({
                    'session_saved': True,
                    'session_modified': False,
                    'last_save_time': time.time()
                })
            
            return success
            
        except Exception as e:
            self.emit_error(f"Error saving session: {str(e)}")
            return False
    
    def load_session(self, session_id: str) -> bool:
        """Load existing session."""
        try:
            # End current session
            if self._session_active:
                self.end_session()
            
            # Load session data
            session_path = self._get_session_file_path(session_id)
            if not os.path.exists(session_path):
                self.emit_error(f"Session file not found: {session_path}")
                return False
            
            session_data = self._json_loader.load_session_data(session_path)
            if not session_data:
                return False
            
            # Restore session state
            self._current_session_id = session_id
            self._session_metadata = session_data.get('session_metadata', {})
            self._session_start_time = self._session_metadata.get('start_time', time.time())
            self._session_active = True
            self._session_modified = False
            
            # Restore annotation data
            annotation_data = session_data.get('annotation_data')
            if annotation_data:
                self._session_data = AnnotationData.from_dict(annotation_data)
            
            # Setup auto saver
            if self._auto_save_enabled:
                self._setup_auto_saver()
            
            # Update history
            self._add_to_session_history(session_id, 'loaded')
            
            self.sessionLoaded.emit(session_id)
            self.emit_state_changed({
                'session_active': True,
                'current_session': session_id,
                'session_loaded': True
            })
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error loading session: {str(e)}")
            return False
    
    def recover_session(self, session_id: str) -> bool:
        """Recover crashed session."""
        try:
            # Check if session is in recovery list
            recovery_session = None
            for session in self._recovery_sessions:
                if session['session_id'] == session_id:
                    recovery_session = session
                    break
            
            if not recovery_session:
                self.emit_error(f"No recovery data found for session: {session_id}")
                return False
            
            # Load recovery data
            recovery_path = recovery_session['recovery_path']
            if not os.path.exists(recovery_path):
                self.emit_error(f"Recovery file not found: {recovery_path}")
                return False
            
            # Load session
            success = self.load_session(session_id)
            if success:
                # Remove from recovery list
                self._recovery_sessions.remove(recovery_session)
                
                # Clean up recovery file
                try:
                    os.remove(recovery_path)
                except:
                    pass
                
                self.sessionRecovered.emit(session_id)
                self.emit_state_changed({'session_recovered': True})
            
            return success
            
        except Exception as e:
            self.emit_error(f"Error recovering session: {str(e)}")
            return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions."""
        sessions = []
        
        try:
            if not self._session_directory:
                return sessions
            
            # Search for session files
            session_pattern = os.path.join(self._session_directory, "*", "session.json")
            import glob
            
            for session_file in glob.glob(session_pattern):
                try:
                    # Get session info
                    session_info = self._json_loader.get_file_info(session_file)
                    if session_info:
                        # Extract session ID from path
                        session_id = os.path.basename(os.path.dirname(session_file))
                        session_info['session_id'] = session_id
                        sessions.append(session_info)
                        
                except Exception as e:
                    self.emit_error(f"Error reading session file {session_file}: {str(e)}")
                    continue
            
            # Sort by creation time
            sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return sessions
            
        except Exception as e:
            self.emit_error(f"Error listing sessions: {str(e)}")
            return sessions
    
    def get_recovery_sessions(self) -> List[Dict[str, Any]]:
        """Get sessions that can be recovered."""
        return self._recovery_sessions.copy()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and its data."""
        try:
            # Cannot delete active session
            if self._current_session_id == session_id:
                self.emit_error("Cannot delete active session")
                return False
            
            # Delete session directory
            session_dir = self._get_session_directory(session_id)
            if os.path.exists(session_dir):
                import shutil
                shutil.rmtree(session_dir)
            
            # Remove from history
            self._session_history = [
                entry for entry in self._session_history
                if entry.get('session_id') != session_id
            ]
            
            # Save updated history
            self._save_session_history()
            
            self.emit_state_changed({'session_deleted': session_id})
            return True
            
        except Exception as e:
            self.emit_error(f"Error deleting session: {str(e)}")
            return False
    
    def set_session_data(self, data: AnnotationData) -> None:
        """Set session annotation data."""
        self._session_data = data
        self._session_modified = True
        
        # Notify auto saver
        if self._auto_saver:
            self._auto_saver.notify_data_changed()
        
        self.emit_state_changed({'session_modified': True})
    
    def get_session_data(self) -> Optional[AnnotationData]:
        """Get session annotation data."""
        return self._session_data
    
    def get_current_session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self._current_session_id
    
    def get_session_metadata(self) -> Dict[str, Any]:
        """Get session metadata."""
        return self._session_metadata.copy()
    
    def is_session_active(self) -> bool:
        """Check if session is active."""
        return self._session_active
    
    def is_session_modified(self) -> bool:
        """Check if session is modified."""
        return self._session_modified
    
    def get_session_duration(self) -> float:
        """Get current session duration in seconds."""
        if not self._session_active:
            return 0.0
        
        return time.time() - self._session_start_time
    
    def set_session_directory(self, directory: str) -> bool:
        """Set session directory."""
        try:
            self._session_directory = directory
            self._setup_session_directory()
            self.emit_state_changed({'session_directory': directory})
            return True
            
        except Exception as e:
            self.emit_error(f"Error setting session directory: {str(e)}")
            return False
    
    def get_session_directory(self) -> Optional[str]:
        """Get session directory."""
        return self._session_directory
    
    def set_session_locking(self, enabled: bool) -> None:
        """Enable/disable session locking."""
        self._session_locking_enabled = enabled
        self.emit_state_changed({'session_locking': enabled})
    
    def is_session_locking_enabled(self) -> bool:
        """Check if session locking is enabled."""
        return self._session_locking_enabled
    
    def _acquire_session_lock(self, session_dir: str) -> bool:
        """Acquire session lock."""
        try:
            # Check if session is already locked
            if is_session_locked(session_dir):
                self.emit_error(f"Session directory is already locked: {session_dir}")
                return False
            
            # Acquire lock
            self._session_lock_context = acquire_session_lock(session_dir, "annotation_session")
            self._session_lock_context.__enter__()
            
            return True
            
        except Exception as e:
            self.emit_error(f"Error acquiring session lock: {str(e)}")
            return False
    
    def _release_session_lock(self) -> bool:
        """Release session lock."""
        try:
            if self._session_lock_context:
                self._session_lock_context.__exit__(None, None, None)
                self._session_lock_context = None
                return True
            return False
            
        except Exception as e:
            self.emit_error(f"Error releasing session lock: {str(e)}")
            return False
    
    def cleanup_stale_session_locks(self) -> int:
        """Clean up stale session locks."""
        if not self._session_directory:
            return 0
            
        try:
            cleanup_stale_locks(self._session_directory)
            return 1
            
        except Exception as e:
            self.emit_error(f"Error cleaning up stale locks: {str(e)}")
            return 0
    
    def check_session_lock_status(self, session_id: str) -> bool:
        """Check if a session is locked."""
        if not self._session_directory:
            return False
            
        session_dir = self._get_session_directory(session_id)
        return is_session_locked(session_dir)
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"
    
    def _setup_session_directory(self) -> None:
        """Setup session directory structure."""
        if not self._session_directory:
            return
        
        # Create main session directory
        os.makedirs(self._session_directory, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['active', 'completed', 'recovery']
        for subdir in subdirs:
            os.makedirs(os.path.join(self._session_directory, subdir), exist_ok=True)
    
    def _get_session_directory(self, session_id: str) -> str:
        """Get directory for specific session."""
        return os.path.join(self._session_directory, 'active', session_id)
    
    def _get_session_file_path(self, session_id: str) -> str:
        """Get file path for session data."""
        session_dir = self._get_session_directory(session_id)
        return os.path.join(session_dir, 'session.json')
    
    def _setup_auto_saver(self) -> None:
        """Setup auto saver for current session."""
        if not self._auto_save_enabled or not self._current_session_id:
            return
        
        try:
            # Create auto saver
            self._auto_saver = AutoSaver()
            
            # Configure auto saver
            auto_save_config = {
                'save_interval': 300.0,  # 5 minutes
                'change_detection': True,
                'save_on_change': False,
                'max_unsaved_changes': 10
            }
            
            self._auto_saver.initialize(**auto_save_config)
            
            # Set callbacks
            self._auto_saver.set_data_getter(lambda: self._session_data)
            self._auto_saver.set_output_path(self._get_session_file_path(self._current_session_id))
            
            # Start auto saver
            self._auto_saver.start()
            
        except Exception as e:
            self.emit_error(f"Error setting up auto saver: {str(e)}")
    
    def _save_session_state(self) -> None:
        """Save session state for recovery."""
        if not self._session_directory or not self._current_session_id:
            return
        
        try:
            # Create state file
            state_file = os.path.join(
                self._session_directory, 
                'recovery', 
                f"{self._current_session_id}_state.json"
            )
            
            state_data = {
                'session_id': self._current_session_id,
                'metadata': self._session_metadata,
                'state_time': time.time(),
                'state_datetime': datetime.now().isoformat(),
                'session_active': self._session_active,
                'session_modified': self._session_modified
            }
            
            self._json_saver.save_session_data(state_data, state_file)
            
        except Exception as e:
            self.emit_error(f"Error saving session state: {str(e)}")
    
    def _load_session_history(self) -> None:
        """Load session history."""
        if not self._session_directory:
            return
        
        try:
            history_file = os.path.join(self._session_directory, 'history.json')
            if os.path.exists(history_file):
                history_data = self._json_loader.load_session_data(history_file)
                if history_data:
                    self._session_history = history_data.get('history', [])
                    
        except Exception as e:
            self.emit_error(f"Error loading session history: {str(e)}")
    
    def _save_session_history(self) -> None:
        """Save session history."""
        if not self._session_directory:
            return
        
        try:
            history_file = os.path.join(self._session_directory, 'history.json')
            history_data = {
                'history': self._session_history,
                'updated_at': datetime.now().isoformat()
            }
            
            self._json_saver.save_session_data(history_data, history_file)
            
        except Exception as e:
            self.emit_error(f"Error saving session history: {str(e)}")
    
    def _add_to_session_history(self, session_id: str, action: str) -> None:
        """Add entry to session history."""
        entry = {
            'session_id': session_id,
            'action': action,
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
        
        self._session_history.append(entry)
        
        # Limit history size
        if len(self._session_history) > self._max_sessions:
            self._session_history = self._session_history[-self._max_sessions:]
        
        # Save history
        self._save_session_history()
    
    def _check_recovery_sessions(self) -> None:
        """Check for sessions that can be recovered."""
        if not self._session_directory:
            return
        
        try:
            recovery_dir = os.path.join(self._session_directory, 'recovery')
            if not os.path.exists(recovery_dir):
                return
            
            # Find state files
            import glob
            state_files = glob.glob(os.path.join(recovery_dir, "*_state.json"))
            
            for state_file in state_files:
                try:
                    state_data = self._json_loader.load_session_data(state_file)
                    if not state_data:
                        continue
                    
                    session_id = state_data.get('session_id')
                    if not session_id:
                        continue
                    
                    # Check if session was properly closed
                    if state_data.get('session_active', False):
                        # Check if session file exists
                        session_file = self._get_session_file_path(session_id)
                        if os.path.exists(session_file):
                            recovery_info = {
                                'session_id': session_id,
                                'recovery_path': state_file,
                                'session_path': session_file,
                                'crash_time': state_data.get('state_time', 0),
                                'metadata': state_data.get('metadata', {})
                            }
                            
                            self._recovery_sessions.append(recovery_info)
                            
                except Exception as e:
                    self.emit_error(f"Error checking recovery file {state_file}: {str(e)}")
                    continue
                    
        except Exception as e:
            self.emit_error(f"Error checking recovery sessions: {str(e)}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # End session if active
            if self._session_active:
                self.end_session()
            
            # Clean up components
            if self._auto_saver:
                self._auto_saver.cleanup()
            
            if hasattr(self._json_saver, 'cleanup'):
                self._json_saver.cleanup()
            
            if hasattr(self._json_loader, 'cleanup'):
                self._json_loader.cleanup()
                
        except Exception as e:
            self.emit_error(f"Error in cleanup: {str(e)}")
        
        super().cleanup()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        stats = super().get_statistics()
        stats.update({
            'session_directory': self._session_directory,
            'current_session_id': self._current_session_id,
            'session_active': self._session_active,
            'session_modified': self._session_modified,
            'session_duration': self.get_session_duration(),
            'auto_save_enabled': self._auto_save_enabled,
            'recovery_enabled': self._recovery_enabled,
            'session_timeout': self._session_timeout,
            'max_sessions': self._max_sessions,
            'session_history_count': len(self._session_history),
            'recovery_sessions_count': len(self._recovery_sessions)
        })
        return stats