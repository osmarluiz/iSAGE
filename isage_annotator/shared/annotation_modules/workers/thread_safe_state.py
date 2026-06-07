"""
Thread-Safe State Management for Annotation System
Provides thread-safe state management with events and locks.
Based on legacy ABILIUS threading implementations.
"""

import threading
import time
import logging
from typing import Optional, Any, Dict, Callable, Set
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class OperationState(Enum):
    """States for long-running operations."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass
class StateChange:
    """Represents a state change event."""
    previous_state: OperationState
    new_state: OperationState
    timestamp: float = field(default_factory=time.time)
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class ThreadSafeState:
    """Thread-safe state management with events and callbacks."""
    
    def __init__(self, initial_state: OperationState = OperationState.IDLE):
        self._state = initial_state
        self._state_lock = threading.RLock()
        self._state_history = []
        
        # Event system
        self._state_callbacks: Dict[OperationState, Set[Callable]] = {}
        self._transition_callbacks: Set[Callable] = set()
        
        # Control events
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        # Initialize pause event as set (not paused)
        self._pause_event.set()
        
        # Statistics
        self._state_counts = {state: 0 for state in OperationState}
        self._state_counts[initial_state] = 1
        
    @property
    def current_state(self) -> OperationState:
        """Get current state."""
        with self._state_lock:
            return self._state
            
    def set_state(self, new_state: OperationState, message: str = None, data: Dict[str, Any] = None) -> bool:
        """Set new state with validation."""
        with self._state_lock:
            if new_state == self._state:
                return False  # No change
                
            # Validate state transition
            if not self._is_valid_transition(self._state, new_state):
                logger.warning(f"Invalid state transition: {self._state} -> {new_state}")
                return False
                
            previous_state = self._state
            self._state = new_state
            
            # Update statistics
            self._state_counts[new_state] += 1
            
            # Create state change event
            state_change = StateChange(
                previous_state=previous_state,
                new_state=new_state,
                message=message,
                data=data
            )
            
            # Add to history
            self._state_history.append(state_change)
            
            # Limit history size
            if len(self._state_history) > 1000:
                self._state_history = self._state_history[-500:]
                
            logger.info(f"State changed: {previous_state} -> {new_state}" + 
                       (f" ({message})" if message else ""))
                
        # Call callbacks outside of lock to avoid deadlock
        self._notify_state_callbacks(state_change)
        
        return True
        
    def _is_valid_transition(self, from_state: OperationState, to_state: OperationState) -> bool:
        """Validate if state transition is allowed."""
        # Define valid transitions
        valid_transitions = {
            OperationState.IDLE: {OperationState.RUNNING},
            OperationState.RUNNING: {OperationState.PAUSED, OperationState.STOPPING, OperationState.COMPLETED, OperationState.FAILED},
            OperationState.PAUSED: {OperationState.RUNNING, OperationState.STOPPING, OperationState.FAILED},
            OperationState.STOPPING: {OperationState.STOPPED, OperationState.FAILED},
            OperationState.STOPPED: {OperationState.IDLE},
            OperationState.FAILED: {OperationState.IDLE},
            OperationState.COMPLETED: {OperationState.IDLE}
        }
        
        return to_state in valid_transitions.get(from_state, set())
        
    def _notify_state_callbacks(self, state_change: StateChange) -> None:
        """Notify registered callbacks of state change."""
        # Notify state-specific callbacks
        state_callbacks = self._state_callbacks.get(state_change.new_state, set())
        for callback in state_callbacks:
            try:
                callback(state_change)
            except Exception as e:
                logger.error(f"Error in state callback: {e}")
                
        # Notify transition callbacks
        for callback in self._transition_callbacks:
            try:
                callback(state_change)
            except Exception as e:
                logger.error(f"Error in transition callback: {e}")
                
    def register_state_callback(self, state: OperationState, callback: Callable[[StateChange], None]) -> None:
        """Register callback for specific state."""
        with self._state_lock:
            if state not in self._state_callbacks:
                self._state_callbacks[state] = set()
            self._state_callbacks[state].add(callback)
            
    def register_transition_callback(self, callback: Callable[[StateChange], None]) -> None:
        """Register callback for any state transition."""
        with self._state_lock:
            self._transition_callbacks.add(callback)
            
    def unregister_state_callback(self, state: OperationState, callback: Callable[[StateChange], None]) -> None:
        """Unregister state callback."""
        with self._state_lock:
            if state in self._state_callbacks:
                self._state_callbacks[state].discard(callback)
                
    def unregister_transition_callback(self, callback: Callable[[StateChange], None]) -> None:
        """Unregister transition callback."""
        with self._state_lock:
            self._transition_callbacks.discard(callback)
            
    def request_stop(self) -> None:
        """Request operation to stop."""
        self._stop_event.set()
        self._pause_event.set()  # Unpause if paused
        
    def request_pause(self) -> None:
        """Request operation to pause."""
        self._pause_event.clear()
        
    def request_resume(self) -> None:
        """Request operation to resume."""
        self._pause_event.set()
        
    def is_stop_requested(self) -> bool:
        """Check if stop was requested."""
        return self._stop_event.is_set()
        
    def is_pause_requested(self) -> bool:
        """Check if pause was requested."""
        return not self._pause_event.is_set()
        
    def wait_if_paused(self, timeout: float = None) -> bool:
        """Wait if paused. Returns True if should continue, False if should stop."""
        if self.is_pause_requested():
            if self.current_state == OperationState.RUNNING:
                self.set_state(OperationState.PAUSED, "Operation paused")
                
            # Wait for resume or stop
            while not self._pause_event.wait(timeout=0.1):
                if self.is_stop_requested():
                    return False
                    
            if self.current_state == OperationState.PAUSED:
                self.set_state(OperationState.RUNNING, "Operation resumed")
                
        return not self.is_stop_requested()
        
    def reset(self) -> None:
        """Reset state to idle."""
        with self._state_lock:
            self._state = OperationState.IDLE
            self._stop_event.clear()
            self._pause_event.set()
            
    @contextmanager
    def operation_context(self, operation_name: str = "Operation"):
        """Context manager for operation lifecycle."""
        try:
            # Start operation
            if not self.set_state(OperationState.RUNNING, f"Starting {operation_name}"):
                raise RuntimeError(f"Cannot start {operation_name}: invalid state {self.current_state}")
                
            yield self
            
            # Complete operation
            if self.current_state == OperationState.RUNNING:
                self.set_state(OperationState.COMPLETED, f"{operation_name} completed")
                
        except Exception as e:
            # Mark as failed
            self.set_state(OperationState.FAILED, f"{operation_name} failed: {str(e)}")
            raise
            
        finally:
            # Clean up
            if self.current_state in {OperationState.COMPLETED, OperationState.FAILED}:
                self.set_state(OperationState.IDLE)
                
    def get_state_history(self, limit: int = 50) -> list:
        """Get recent state history."""
        with self._state_lock:
            return self._state_history[-limit:]
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get state statistics."""
        with self._state_lock:
            return {
                'current_state': self._state.value,
                'state_counts': {state.value: count for state, count in self._state_counts.items()},
                'history_length': len(self._state_history),
                'is_stop_requested': self.is_stop_requested(),
                'is_pause_requested': self.is_pause_requested(),
                'registered_callbacks': sum(len(callbacks) for callbacks in self._state_callbacks.values()),
                'transition_callbacks': len(self._transition_callbacks)
            }


class OperationController:
    """Controller for managing long-running operations with state."""
    
    def __init__(self, name: str):
        self.name = name
        self.state = ThreadSafeState()
        self._operation_thread: Optional[threading.Thread] = None
        self._operation_func: Optional[Callable] = None
        self._operation_args: tuple = ()
        self._operation_kwargs: dict = {}
        
    def start_operation(self, operation_func: Callable, *args, **kwargs) -> bool:
        """Start a new operation."""
        if self.state.current_state != OperationState.IDLE:
            logger.warning(f"Cannot start operation: current state is {self.state.current_state}")
            return False
            
        self._operation_func = operation_func
        self._operation_args = args
        self._operation_kwargs = kwargs
        
        # Start operation thread
        self._operation_thread = threading.Thread(target=self._run_operation, daemon=True)
        self._operation_thread.start()
        
        return True
        
    def _run_operation(self) -> None:
        """Run the operation with state management."""
        try:
            with self.state.operation_context(self.name):
                result = self._operation_func(self.state, *self._operation_args, **self._operation_kwargs)
                logger.info(f"Operation {self.name} completed with result: {result}")
                
        except Exception as e:
            logger.error(f"Operation {self.name} failed: {e}")
            
    def stop_operation(self, timeout: float = 5.0) -> bool:
        """Stop the current operation."""
        if self.state.current_state not in {OperationState.RUNNING, OperationState.PAUSED}:
            return True
            
        self.state.request_stop()
        
        # Wait for operation to stop
        if self._operation_thread and self._operation_thread.is_alive():
            self._operation_thread.join(timeout=timeout)
            
            if self._operation_thread.is_alive():
                logger.warning(f"Operation {self.name} did not stop within timeout")
                return False
                
        return True
        
    def pause_operation(self) -> bool:
        """Pause the current operation."""
        if self.state.current_state != OperationState.RUNNING:
            return False
            
        self.state.request_pause()
        return True
        
    def resume_operation(self) -> bool:
        """Resume the paused operation."""
        if self.state.current_state != OperationState.PAUSED:
            return False
            
        self.state.request_resume()
        return True
        
    def get_status(self) -> Dict[str, Any]:
        """Get operation status."""
        return {
            'name': self.name,
            'state': self.state.current_state.value,
            'statistics': self.state.get_statistics(),
            'thread_alive': self._operation_thread and self._operation_thread.is_alive()
        }