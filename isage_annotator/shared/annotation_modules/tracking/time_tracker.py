"""
Enhanced Time Tracker - Advanced time tracking with comprehensive analytics

This enhanced version addresses potential issues and adds improvements:
- Better performance analytics and prediction
- Advanced workflow analysis and optimization suggestions
- Support for multiple concurrent sessions
- Enhanced data persistence and recovery
- Real-time collaboration features
- Machine learning-based productivity insights
"""

import time
import json
import pickle
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Callable, Union
from collections import defaultdict, deque
from dataclasses import dataclass, field
from ..base_protocols import BaseComponent, QTimer, pyqtSignal
from pathlib import Path
import numpy as np
from functools import lru_cache
import sqlite3
import logging


@dataclass
class SessionEvent:
    """Represents a session event with metadata."""
    timestamp: float
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    user_id: str = ""
    image_path: str = ""
    annotation_id: str = ""


@dataclass
class ProductivityMetrics:
    """Comprehensive productivity metrics."""
    score: float
    level: str
    trend: str
    annotations_per_minute: float
    time_per_annotation: float
    focus_score: float
    efficiency_score: float
    consistency_score: float
    break_adherence: float
    optimal_time_periods: List[Tuple[int, int]]


@dataclass
class WorkflowAnalysis:
    """Workflow analysis results."""
    bottlenecks: List[str]
    optimization_suggestions: List[str]
    time_distribution: Dict[str, float]
    interruption_patterns: List[Dict[str, Any]]
    productivity_patterns: List[Dict[str, Any]]
    fatigue_indicators: List[str]


class TimeTracker(BaseComponent):
    """Enhanced time tracking component with advanced analytics."""
    
    # Enhanced time tracking signals
    sessionStarted = pyqtSignal(str)  # session_id
    sessionEnded = pyqtSignal(str, float)  # session_id, duration
    sessionPaused = pyqtSignal(str)  # session_id
    sessionResumed = pyqtSignal(str)  # session_id
    imageStarted = pyqtSignal(str)  # image_path
    imageCompleted = pyqtSignal(str, float)  # image_path, duration
    annotationMade = pyqtSignal(str, float)  # annotation_type, timestamp
    productivityUpdated = pyqtSignal(object)  # ProductivityMetrics
    milestoneReached = pyqtSignal(str, dict)  # milestone_type, data
    workflowAnalyzed = pyqtSignal(object)  # WorkflowAnalysis
    performancePredicted = pyqtSignal(dict)  # prediction_data
    breakRecommended = pyqtSignal(dict)  # break_data
    focusScoreUpdated = pyqtSignal(float)  # focus_score
    efficiencyAlertTriggered = pyqtSignal(str, dict)  # alert_type, data
    
    def __init__(self, name: str = "enhanced_time_tracker", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Enhanced session tracking
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._active_sessions: List[str] = []
        self._current_primary_session: Optional[str] = None
        self._session_events: Dict[str, List[SessionEvent]] = {}
        self._session_paused_states: Dict[str, bool] = {}
        self._session_pause_times: Dict[str, float] = {}
        self._session_total_pause_times: Dict[str, float] = {}
        
        # Enhanced image tracking
        self._image_sessions: Dict[str, Dict[str, Any]] = {}
        self._image_completion_history: List[Dict[str, Any]] = []
        self._image_difficulty_scores: Dict[str, float] = {}
        self._image_quality_scores: Dict[str, float] = {}
        self._image_rework_counts: Dict[str, int] = {}
        
        # Advanced annotation tracking
        self._annotation_events: List[SessionEvent] = []
        self._annotation_patterns: Dict[str, List[float]] = {}
        self._annotation_quality_scores: Dict[str, float] = {}
        self._annotation_revision_history: Dict[str, List[Dict[str, Any]]] = {}
        self._annotation_clusters: Dict[str, List[Dict[str, Any]]] = {}
        
        # Advanced productivity analytics
        self._productivity_window: float = 300.0  # 5 minutes
        self._productivity_history: deque = deque(maxlen=1000)
        self._productivity_thresholds: Dict[str, float] = {
            'very_low': 0.0,
            'low': 0.5,
            'medium': 1.0,
            'high': 2.0,
            'very_high': 3.0
        }
        self._productivity_trends: List[float] = []
        self._focus_periods: List[Tuple[float, float]] = []
        self._interruption_events: List[Dict[str, Any]] = []
        
        # Workflow analysis
        self._workflow_states: List[str] = []
        self._workflow_transitions: Dict[str, Dict[str, int]] = {}
        self._workflow_bottlenecks: List[str] = []
        self._workflow_optimization_suggestions: List[str] = []
        
        # Performance prediction
        self._performance_models: Dict[str, Callable] = {}
        self._performance_features: Dict[str, List[float]] = {}
        self._performance_predictions: Dict[str, Dict[str, Any]] = {}
        self._model_accuracy_scores: Dict[str, float] = {}
        
        # Enhanced break management
        self._break_patterns: List[Dict[str, Any]] = []
        self._break_effectiveness_scores: List[float] = []
        self._optimal_break_intervals: List[float] = []
        self._fatigue_indicators: List[str] = []
        self._break_recommendations: List[Dict[str, Any]] = []
        
        # Advanced milestones
        self._dynamic_milestones: Dict[str, Dict[str, Any]] = {}
        self._milestone_rewards: Dict[str, str] = {}
        self._milestone_achievements: List[Dict[str, Any]] = []
        self._personal_best_records: Dict[str, Dict[str, Any]] = {}
        
        # Data persistence
        self._data_persistence_enabled: bool = True
        self._database_path: Optional[str] = None
        self._database_connection: Optional[sqlite3.Connection] = None
        self._auto_backup_enabled: bool = True
        self._backup_interval: float = 3600.0  # 1 hour
        self._last_backup_time: Optional[float] = None
        
        # Real-time collaboration
        self._collaboration_enabled: bool = False
        self._team_session_id: Optional[str] = None
        self._team_productivity_metrics: Dict[str, Any] = {}
        self._peer_comparison_enabled: bool = False
        
        # Advanced timers
        self._main_update_timer: QTimer = QTimer()
        self._productivity_analysis_timer: QTimer = QTimer()
        self._workflow_analysis_timer: QTimer = QTimer()
        self._prediction_timer: QTimer = QTimer()
        self._backup_timer: QTimer = QTimer()
        
        # Performance optimization
        self._analysis_thread_pool: Optional[List[threading.Thread]] = None
        self._async_analysis_enabled: bool = True
        self._cache_size: int = 1000
        self._analysis_cache: Dict[str, Any] = {}
        
        # Machine learning features
        self._ml_enabled: bool = False
        self._feature_extraction_enabled: bool = True
        self._pattern_recognition_enabled: bool = True
        self._anomaly_detection_enabled: bool = True
        self._prediction_accuracy_threshold: float = 0.8
        
        # Customization and preferences
        self._user_preferences: Dict[str, Any] = {}
        self._custom_metrics: Dict[str, Callable] = {}
        self._alert_rules: List[Dict[str, Any]] = []
        self._notification_preferences: Dict[str, bool] = {}
        
        # Thread safety
        self._data_lock = threading.Lock()
        self._analysis_lock = threading.Lock()
        
        # Initialize components
        self._initialize_enhanced_features()
        self._setup_timers()
        self._setup_database()
        self._setup_machine_learning()
    
    def initialize(self, **kwargs) -> bool:
        """Initialize enhanced time tracker."""
        # Basic settings
        self._productivity_window = kwargs.get('productivity_window', 300.0)
        self._productivity_thresholds = kwargs.get('productivity_thresholds', {
            'very_low': 0.0, 'low': 0.5, 'medium': 1.0, 'high': 2.0, 'very_high': 3.0
        })
        
        # Enhanced settings
        self._data_persistence_enabled = kwargs.get('data_persistence_enabled', True)
        self._database_path = kwargs.get('database_path', None)
        self._auto_backup_enabled = kwargs.get('auto_backup_enabled', True)
        self._backup_interval = kwargs.get('backup_interval', 3600.0)
        self._collaboration_enabled = kwargs.get('collaboration_enabled', False)
        self._ml_enabled = kwargs.get('ml_enabled', False)
        self._async_analysis_enabled = kwargs.get('async_analysis_enabled', True)
        self._cache_size = kwargs.get('cache_size', 1000)
        
        # User preferences
        self._user_preferences = kwargs.get('user_preferences', {})
        self._notification_preferences = kwargs.get('notification_preferences', {})
        
        # Custom metrics and alerts
        if 'custom_metrics' in kwargs:
            self._custom_metrics.update(kwargs['custom_metrics'])
        if 'alert_rules' in kwargs:
            self._alert_rules.extend(kwargs['alert_rules'])
        
        # Performance settings
        if 'performance_models' in kwargs:
            self._performance_models.update(kwargs['performance_models'])
        
        # Initialize database if enabled
        if self._data_persistence_enabled:
            self._initialize_database()
        
        # Load historical data
        self._load_historical_data()
        
        # Setup machine learning models
        if self._ml_enabled:
            self._initialize_ml_models()
        
        return super().initialize(**kwargs)
    
    def start_session(self, session_id: str, user_id: str = "", 
                     session_type: str = "annotation", **metadata) -> None:
        """Start a new enhanced annotation session."""
        try:
            with self._data_lock:
                current_time = time.time()
                
                # Create session record
                session_data = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'session_type': session_type,
                    'start_time': current_time,
                    'end_time': None,
                    'paused': False,
                    'pause_start_time': None,
                    'total_pause_time': 0.0,
                    'metadata': metadata,
                    'statistics': {
                        'total_time': 0.0,
                        'active_time': 0.0,
                        'pause_time': 0.0,
                        'images_processed': 0,
                        'annotations_made': 0,
                        'productivity_score': 0.0,
                        'focus_score': 0.0,
                        'efficiency_score': 0.0
                    }
                }
                
                # Store session
                self._sessions[session_id] = session_data
                self._active_sessions.append(session_id)
                self._session_events[session_id] = []
                self._session_paused_states[session_id] = False
                self._session_pause_times[session_id] = 0.0
                self._session_total_pause_times[session_id] = 0.0
                
                # Set as primary session if none exists
                if not self._current_primary_session:
                    self._current_primary_session = session_id
                
                # Create session event
                event = SessionEvent(
                    timestamp=current_time,
                    event_type="session_started",
                    data=metadata,
                    session_id=session_id,
                    user_id=user_id
                )
                self._session_events[session_id].append(event)
                
                # Persist to database
                if self._data_persistence_enabled:
                    self._save_session_to_database(session_data)
                
                # Start analysis if enabled
                if self._async_analysis_enabled:
                    self._start_session_analysis(session_id)
                
                # Emit signal
                self.sessionStarted.emit(session_id)
                self.emit_state_changed({'session_started': session_id})
                
        except Exception as e:
            self.emit_error(f"Error starting session: {str(e)}")
    
    def end_session(self, session_id: Optional[str] = None) -> None:
        """End an enhanced annotation session."""
        try:
            with self._data_lock:
                if session_id is None:
                    session_id = self._current_primary_session
                
                if not session_id or session_id not in self._sessions:
                    return
                
                current_time = time.time()
                session_data = self._sessions[session_id]
                
                # Calculate final statistics
                total_time = current_time - session_data['start_time']
                if session_data['paused']:
                    pause_time = self._session_total_pause_times[session_id] + (current_time - session_data['pause_start_time'])
                else:
                    pause_time = self._session_total_pause_times[session_id]
                
                active_time = total_time - pause_time
                
                # Update session data
                session_data['end_time'] = current_time
                session_data['total_pause_time'] = pause_time
                session_data['statistics'].update({
                    'total_time': total_time,
                    'active_time': active_time,
                    'pause_time': pause_time
                })
                
                # Create session event
                event = SessionEvent(
                    timestamp=current_time,
                    event_type="session_ended",
                    data={'total_time': total_time, 'active_time': active_time},
                    session_id=session_id,
                    user_id=session_data['user_id']
                )
                self._session_events[session_id].append(event)
                
                # Perform final analysis
                self._perform_session_analysis(session_id)
                
                # Update records
                self._update_personal_best_records(session_id)
                
                # Clean up active session tracking
                if session_id in self._active_sessions:
                    self._active_sessions.remove(session_id)
                
                if self._current_primary_session == session_id:
                    self._current_primary_session = self._active_sessions[0] if self._active_sessions else None
                
                # Persist to database
                if self._data_persistence_enabled:
                    self._save_session_to_database(session_data)
                
                # Emit signal
                self.sessionEnded.emit(session_id, total_time)
                self.emit_state_changed({'session_ended': session_id})
                
        except Exception as e:
            self.emit_error(f"Error ending session: {str(e)}")
    
    def record_annotation(self, annotation_type: str = "point", 
                         session_id: Optional[str] = None,
                         image_path: Optional[str] = None,
                         annotation_id: Optional[str] = None,
                         quality_score: Optional[float] = None,
                         **metadata) -> None:
        """Record an enhanced annotation event."""
        try:
            with self._data_lock:
                if session_id is None:
                    session_id = self._current_primary_session
                
                if not session_id or session_id not in self._sessions:
                    return
                
                current_time = time.time()
                session_data = self._sessions[session_id]
                
                # Create annotation event
                event = SessionEvent(
                    timestamp=current_time,
                    event_type="annotation_made",
                    data={
                        'annotation_type': annotation_type,
                        'quality_score': quality_score,
                        **metadata
                    },
                    session_id=session_id,
                    user_id=session_data['user_id'],
                    image_path=image_path or "",
                    annotation_id=annotation_id or ""
                )
                
                # Store event
                self._session_events[session_id].append(event)
                self._annotation_events.append(event)
                
                # Update session statistics
                session_data['statistics']['annotations_made'] += 1
                
                # Update annotation patterns
                if annotation_type not in self._annotation_patterns:
                    self._annotation_patterns[annotation_type] = []
                self._annotation_patterns[annotation_type].append(current_time)
                
                # Store quality score
                if quality_score is not None and annotation_id:
                    self._annotation_quality_scores[annotation_id] = quality_score
                
                # Update productivity metrics
                self._update_productivity_metrics(session_id)
                
                # Perform real-time analysis
                if self._async_analysis_enabled:
                    self._analyze_annotation_patterns(session_id)
                
                # Check for alerts
                self._check_efficiency_alerts(session_id)
                
                # Emit signal
                self.annotationMade.emit(annotation_type, current_time)
                self.emit_state_changed({'annotation_made': annotation_type})
                
        except Exception as e:
            self.emit_error(f"Error recording annotation: {str(e)}")
    
    def analyze_workflow(self, session_id: Optional[str] = None, 
                        time_window: Optional[float] = None) -> WorkflowAnalysis:
        """Perform comprehensive workflow analysis."""
        try:
            with self._analysis_lock:
                if session_id is None:
                    session_id = self._current_primary_session
                
                if not session_id or session_id not in self._sessions:
                    return WorkflowAnalysis([], [], {}, [], [], [])
                
                current_time = time.time()
                if time_window is None:
                    time_window = self._productivity_window
                
                events = self._session_events[session_id]
                cutoff_time = current_time - time_window
                recent_events = [e for e in events if e.timestamp >= cutoff_time]
                
                # Analyze bottlenecks
                bottlenecks = self._identify_bottlenecks(recent_events)
                
                # Generate optimization suggestions
                suggestions = self._generate_optimization_suggestions(recent_events, bottlenecks)
                
                # Analyze time distribution
                time_distribution = self._analyze_time_distribution(recent_events)
                
                # Identify interruption patterns
                interruptions = self._identify_interruption_patterns(recent_events)
                
                # Analyze productivity patterns
                productivity_patterns = self._analyze_productivity_patterns(recent_events)
                
                # Identify fatigue indicators
                fatigue_indicators = self._identify_fatigue_indicators(recent_events)
                
                # Create analysis result
                analysis = WorkflowAnalysis(
                    bottlenecks=bottlenecks,
                    optimization_suggestions=suggestions,
                    time_distribution=time_distribution,
                    interruption_patterns=interruptions,
                    productivity_patterns=productivity_patterns,
                    fatigue_indicators=fatigue_indicators
                )
                
                # Cache result
                self._analysis_cache[f"workflow_{session_id}"] = analysis
                
                # Emit signal
                self.workflowAnalyzed.emit(analysis)
                
                return analysis
                
        except Exception as e:
            self.emit_error(f"Error analyzing workflow: {str(e)}")
            return WorkflowAnalysis([], [], {}, [], [], [])
    
    def predict_performance(self, session_id: Optional[str] = None, 
                          prediction_horizon: float = 3600.0) -> Dict[str, Any]:
        """Predict future performance metrics."""
        try:
            with self._analysis_lock:
                if session_id is None:
                    session_id = self._current_primary_session
                
                if not session_id or session_id not in self._sessions:
                    return {}
                
                # Extract features for prediction
                features = self._extract_prediction_features(session_id)
                
                # Make predictions using available models
                predictions = {}
                for model_name, model in self._performance_models.items():
                    try:
                        prediction = model(features)
                        predictions[model_name] = prediction
                    except Exception as e:
                        self.emit_error(f"Error in {model_name} prediction: {str(e)}")
                
                # Add basic statistical predictions
                predictions.update(self._statistical_predictions(session_id, prediction_horizon))
                
                # Store predictions
                self._performance_predictions[session_id] = predictions
                
                # Emit signal
                self.performancePredicted.emit(predictions)
                
                return predictions
                
        except Exception as e:
            self.emit_error(f"Error predicting performance: {str(e)}")
            return {}
    
    def _update_productivity_metrics(self, session_id: str) -> None:
        """Update comprehensive productivity metrics."""
        try:
            current_time = time.time()
            session_data = self._sessions[session_id]
            
            # Get recent events
            events = self._session_events[session_id]
            cutoff_time = current_time - self._productivity_window
            recent_events = [e for e in events if e.timestamp >= cutoff_time]
            
            # Calculate basic productivity score
            annotation_events = [e for e in recent_events if e.event_type == "annotation_made"]
            time_window_minutes = self._productivity_window / 60.0
            annotations_per_minute = len(annotation_events) / time_window_minutes
            
            # Calculate time per annotation
            if len(annotation_events) > 1:
                time_diffs = [annotation_events[i].timestamp - annotation_events[i-1].timestamp 
                             for i in range(1, len(annotation_events))]
                time_per_annotation = np.mean(time_diffs) if time_diffs else 0.0
            else:
                time_per_annotation = 0.0
            
            # Calculate focus score
            focus_score = self._calculate_focus_score(recent_events)
            
            # Calculate efficiency score
            efficiency_score = self._calculate_efficiency_score(recent_events)
            
            # Calculate consistency score
            consistency_score = self._calculate_consistency_score(recent_events)
            
            # Calculate break adherence
            break_adherence = self._calculate_break_adherence(session_id)
            
            # Identify optimal time periods
            optimal_periods = self._identify_optimal_time_periods(session_id)
            
            # Get productivity level
            productivity_level = self._get_productivity_level(annotations_per_minute)
            
            # Calculate trend
            trend = self._calculate_productivity_trend(session_id)
            
            # Create comprehensive metrics
            metrics = ProductivityMetrics(
                score=annotations_per_minute,
                level=productivity_level,
                trend=trend,
                annotations_per_minute=annotations_per_minute,
                time_per_annotation=time_per_annotation,
                focus_score=focus_score,
                efficiency_score=efficiency_score,
                consistency_score=consistency_score,
                break_adherence=break_adherence,
                optimal_time_periods=optimal_periods
            )
            
            # Update session statistics
            session_data['statistics'].update({
                'productivity_score': annotations_per_minute,
                'focus_score': focus_score,
                'efficiency_score': efficiency_score
            })
            
            # Store in history
            self._productivity_history.append({
                'timestamp': current_time,
                'session_id': session_id,
                'metrics': metrics
            })
            
            # Emit signals
            self.productivityUpdated.emit(metrics)
            self.focusScoreUpdated.emit(focus_score)
            
        except Exception as e:
            self.emit_error(f"Error updating productivity metrics: {str(e)}")
    
    def _calculate_focus_score(self, events: List[SessionEvent]) -> float:
        """Calculate focus score based on event patterns."""
        try:
            if not events:
                return 0.0
            
            # Calculate time between events
            time_intervals = []
            for i in range(1, len(events)):
                interval = events[i].timestamp - events[i-1].timestamp
                time_intervals.append(interval)
            
            if not time_intervals:
                return 0.0
            
            # Focus score based on consistency of intervals
            mean_interval = np.mean(time_intervals)
            std_interval = np.std(time_intervals)
            
            if mean_interval == 0:
                return 0.0
            
            # Lower variance indicates better focus
            coefficient_of_variation = std_interval / mean_interval
            focus_score = max(0.0, 1.0 - coefficient_of_variation)
            
            return min(1.0, focus_score)
            
        except Exception as e:
            self.emit_error(f"Error calculating focus score: {str(e)}")
            return 0.0
    
    def _calculate_efficiency_score(self, events: List[SessionEvent]) -> float:
        """Calculate efficiency score based on annotation patterns."""
        try:
            if not events:
                return 0.0
            
            annotation_events = [e for e in events if e.event_type == "annotation_made"]
            if not annotation_events:
                return 0.0
            
            # Calculate efficiency based on quality scores
            quality_scores = []
            for event in annotation_events:
                quality_score = event.data.get('quality_score', None)
                if quality_score is not None:
                    quality_scores.append(quality_score)
            
            if quality_scores:
                efficiency_score = np.mean(quality_scores)
            else:
                # Use annotation frequency as proxy
                total_time = events[-1].timestamp - events[0].timestamp
                if total_time > 0:
                    efficiency_score = len(annotation_events) / total_time * 60  # annotations per minute
                    efficiency_score = min(1.0, efficiency_score / 2.0)  # normalize to 0-1
                else:
                    efficiency_score = 0.0
            
            return min(1.0, max(0.0, efficiency_score))
            
        except Exception as e:
            self.emit_error(f"Error calculating efficiency score: {str(e)}")
            return 0.0
    
    def _identify_bottlenecks(self, events: List[SessionEvent]) -> List[str]:
        """Identify workflow bottlenecks."""
        try:
            bottlenecks = []
            
            if not events:
                return bottlenecks
            
            # Analyze time gaps between events
            time_gaps = []
            for i in range(1, len(events)):
                gap = events[i].timestamp - events[i-1].timestamp
                time_gaps.append((gap, events[i-1].event_type, events[i].event_type))
            
            # Find unusually long gaps
            if time_gaps:
                gap_times = [gap[0] for gap in time_gaps]
                threshold = np.percentile(gap_times, 90)  # 90th percentile
                
                long_gaps = [gap for gap in time_gaps if gap[0] > threshold]
                
                # Identify common bottleneck patterns
                bottleneck_patterns = defaultdict(int)
                for gap, from_event, to_event in long_gaps:
                    pattern = f"{from_event} -> {to_event}"
                    bottleneck_patterns[pattern] += 1
                
                # Add significant bottlenecks
                for pattern, count in bottleneck_patterns.items():
                    if count > 1:  # Multiple occurrences
                        bottlenecks.append(f"Delay in {pattern} (occurred {count} times)")
            
            return bottlenecks
            
        except Exception as e:
            self.emit_error(f"Error identifying bottlenecks: {str(e)}")
            return []
    
    def _generate_optimization_suggestions(self, events: List[SessionEvent], 
                                         bottlenecks: List[str]) -> List[str]:
        """Generate workflow optimization suggestions."""
        try:
            suggestions = []
            
            # Analyze bottlenecks for suggestions
            for bottleneck in bottlenecks:
                if "annotation_made" in bottleneck:
                    suggestions.append("Consider using keyboard shortcuts for faster annotation")
                elif "image_started" in bottleneck:
                    suggestions.append("Pre-load images to reduce loading time")
                elif "session_paused" in bottleneck:
                    suggestions.append("Take more regular breaks to maintain focus")
            
            # Analyze annotation patterns
            annotation_events = [e for e in events if e.event_type == "annotation_made"]
            if annotation_events:
                annotation_types = [e.data.get('annotation_type', 'unknown') for e in annotation_events]
                type_counts = defaultdict(int)
                for atype in annotation_types:
                    type_counts[atype] += 1
                
                # Suggest batch processing for common types
                for atype, count in type_counts.items():
                    if count > 5:
                        suggestions.append(f"Consider batch processing {atype} annotations")
            
            # Analyze timing patterns
            if len(events) > 10:
                hour_distribution = defaultdict(int)
                for event in events:
                    hour = datetime.fromtimestamp(event.timestamp).hour
                    hour_distribution[hour] += 1
                
                # Find peak hours
                peak_hour = max(hour_distribution, key=hour_distribution.get)
                suggestions.append(f"You're most productive around {peak_hour}:00 - schedule important tasks then")
            
            return suggestions
            
        except Exception as e:
            self.emit_error(f"Error generating optimization suggestions: {str(e)}")
            return []
    
    def _setup_timers(self) -> None:
        """Setup enhanced timers."""
        try:
            # Main update timer
            self._main_update_timer.timeout.connect(self._main_update)
            self._main_update_timer.start(1000)  # 1 second
            
            # Productivity analysis timer
            self._productivity_analysis_timer.timeout.connect(self._analyze_productivity)
            self._productivity_analysis_timer.start(30000)  # 30 seconds
            
            # Workflow analysis timer
            self._workflow_analysis_timer.timeout.connect(self._analyze_workflow)
            self._workflow_analysis_timer.start(60000)  # 1 minute
            
            # Prediction timer
            self._prediction_timer.timeout.connect(self._update_predictions)
            self._prediction_timer.start(300000)  # 5 minutes
            
            # Backup timer
            self._backup_timer.timeout.connect(self._perform_backup)
            self._backup_timer.start(int(self._backup_interval * 1000))
            
        except Exception as e:
            self.emit_error(f"Error setting up timers: {str(e)}")
    
    def _setup_database(self) -> None:
        """Setup database for data persistence."""
        try:
            if not self._data_persistence_enabled:
                return
            
            if not self._database_path:
                self._database_path = "annotation_tracking.db"
            
            # Create database connection
            self._database_connection = sqlite3.connect(self._database_path, check_same_thread=False)
            
            # Create tables
            self._create_database_tables()
            
        except Exception as e:
            self.emit_error(f"Error setting up database: {str(e)}")
    
    def _setup_machine_learning(self) -> None:
        """Setup machine learning models."""
        try:
            if not self._ml_enabled:
                return
            
            # Initialize basic prediction models
            self._performance_models['linear_productivity'] = self._linear_productivity_model
            self._performance_models['fatigue_detection'] = self._fatigue_detection_model
            self._performance_models['break_recommendation'] = self._break_recommendation_model
            
        except Exception as e:
            self.emit_error(f"Error setting up machine learning: {str(e)}")
    
    def _initialize_enhanced_features(self) -> None:
        """Initialize enhanced features."""
        try:
            # Initialize data structures
            self._workflow_states = ['idle', 'loading', 'annotating', 'reviewing', 'paused']
            self._workflow_transitions = {state: {} for state in self._workflow_states}
            
            # Initialize break patterns
            self._break_patterns = []
            self._break_effectiveness_scores = []
            
            # Initialize milestone rewards
            self._milestone_rewards = {
                'first_annotation': 'Welcome to annotation!',
                'speed_demon': 'Fast annotation streak!',
                'consistency_master': 'Consistent performance!',
                'focus_champion': 'Excellent focus!'
            }
            
        except Exception as e:
            self.emit_error(f"Error initializing enhanced features: {str(e)}")
    
    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """Get comprehensive enhanced statistics."""
        try:
            stats = super().get_statistics()
            
            # Add enhanced statistics
            stats.update({
                'active_sessions': len(self._active_sessions),
                'primary_session': self._current_primary_session,
                'total_sessions': len(self._sessions),
                'productivity_analytics': {
                    'current_trend': self._productivity_trends[-10:] if self._productivity_trends else [],
                    'focus_periods': len(self._focus_periods),
                    'interruption_events': len(self._interruption_events),
                    'workflow_bottlenecks': len(self._workflow_bottlenecks),
                    'optimization_suggestions': len(self._workflow_optimization_suggestions)
                },
                'performance_prediction': {
                    'models_available': len(self._performance_models),
                    'prediction_accuracy': self._model_accuracy_scores,
                    'features_extracted': len(self._performance_features)
                },
                'data_persistence': {
                    'database_enabled': self._data_persistence_enabled,
                    'database_path': self._database_path,
                    'auto_backup_enabled': self._auto_backup_enabled,
                    'last_backup': self._last_backup_time
                },
                'machine_learning': {
                    'ml_enabled': self._ml_enabled,
                    'pattern_recognition': self._pattern_recognition_enabled,
                    'anomaly_detection': self._anomaly_detection_enabled,
                    'prediction_threshold': self._prediction_accuracy_threshold
                },
                'collaboration': {
                    'collaboration_enabled': self._collaboration_enabled,
                    'team_session_id': self._team_session_id,
                    'peer_comparison': self._peer_comparison_enabled
                }
            })
            
            return stats
            
        except Exception as e:
            self.emit_error(f"Error getting enhanced statistics: {str(e)}")
            return {}
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Stop timers
            self._main_update_timer.stop()
            self._productivity_analysis_timer.stop()
            self._workflow_analysis_timer.stop()
            self._prediction_timer.stop()
            self._backup_timer.stop()
            
            # Close database connection
            if self._database_connection:
                self._database_connection.close()
            
            # Stop analysis threads
            if self._analysis_thread_pool:
                for thread in self._analysis_thread_pool:
                    if thread.is_alive():
                        thread.join(timeout=1.0)
            
            # Clear caches
            self._analysis_cache.clear()
            
        except Exception as e:
            self.emit_error(f"Error during cleanup: {str(e)}")
    
    def __del__(self):
        """Destructor."""
        try:
            self.cleanup()
        except:
            pass