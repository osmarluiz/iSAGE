"""
Batch Annotation Tools

Provides efficient batch annotation capabilities for large datasets.
Supports automated labeling, bulk operations, and workflow optimization.
Part of the modular annotation system.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QProgressBar, QTextEdit, QCheckBox, QSpinBox, QComboBox,
        QGroupBox, QListWidget, QListWidgetItem, QTabWidget,
        QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer
    from PyQt5.QtGui import QColor, QFont, QIcon
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    class QObject: pass
    class QWidget: pass
    class QThread: pass
    class pyqtSignal: 
        def __init__(self, *args): pass

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import time
from abc import ABC, abstractmethod


class BatchOperationType(Enum):
    """Types of batch operations."""
    AUTO_LABEL = "auto_label"
    QUALITY_CHECK = "quality_check"
    FORMAT_CONVERSION = "format_conversion"
    DATA_AUGMENTATION = "data_augmentation"
    ANNOTATION_TRANSFER = "annotation_transfer"
    VALIDATION = "validation"
    CLEANUP = "cleanup"
    STATISTICS = "statistics"


class ProcessingStatus(Enum):
    """Processing status for batch items."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchItem:
    """Individual item in a batch operation."""
    id: str
    source_path: Path
    target_path: Optional[Path] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: float = 0.0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    
    def __post_init__(self):
        if isinstance(self.source_path, str):
            self.source_path = Path(self.source_path)
        if isinstance(self.target_path, str):
            self.target_path = Path(self.target_path)


@dataclass
class BatchConfiguration:
    """Configuration for batch operations."""
    operation_type: BatchOperationType
    parallel_workers: int = 4
    batch_size: int = 32
    auto_save: bool = True
    save_interval: int = 10
    skip_existing: bool = True
    validate_results: bool = True
    
    # Operation-specific settings
    confidence_threshold: float = 0.8
    quality_threshold: float = 0.7
    max_retries: int = 3
    timeout_seconds: int = 300
    
    # Output settings
    output_format: str = "json"
    compression: bool = False
    backup_original: bool = True


class BatchProcessor(ABC):
    """Abstract base class for batch processors."""
    
    @abstractmethod
    def process_item(self, item: BatchItem, config: BatchConfiguration) -> BatchItem:
        """Process a single batch item."""
        pass
    
    @abstractmethod
    def validate_item(self, item: BatchItem) -> bool:
        """Validate a processed item."""
        pass
    
    def get_processor_info(self) -> Dict[str, Any]:
        """Get information about this processor."""
        return {
            "name": self.__class__.__name__,
            "supported_operations": [],
            "requirements": []
        }


class AutoLabelProcessor(BatchProcessor):
    """Processor for automated labeling using ML models."""
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the ML model for auto-labeling."""
        # Placeholder for model loading
        # In a real implementation, this would load an actual model
        self.model = {"type": "mock_model", "confidence": 0.85}
    
    def process_item(self, item: BatchItem, config: BatchConfiguration) -> BatchItem:
        """Process item with auto-labeling."""
        start_time = time.time()
        
        try:
            # Simulate model prediction
            if not self.model:
                raise Exception("Model not loaded")
            
            # Mock prediction process
            time.sleep(0.1)  # Simulate processing time
            
            # Generate mock annotations
            predictions = self._generate_mock_predictions(item.source_path)
            
            # Filter by confidence threshold
            filtered_predictions = [
                pred for pred in predictions 
                if pred['confidence'] >= config.confidence_threshold
            ]
            
            # Save results
            if item.target_path:
                self._save_predictions(filtered_predictions, item.target_path)
            
            item.status = ProcessingStatus.COMPLETED
            item.progress = 1.0
            item.metadata['predictions'] = len(filtered_predictions)
            item.metadata['avg_confidence'] = np.mean([p['confidence'] for p in filtered_predictions]) if filtered_predictions else 0.0
            
        except Exception as e:
            item.status = ProcessingStatus.FAILED
            item.error_message = str(e)
        
        item.processing_time = time.time() - start_time
        return item
    
    def _generate_mock_predictions(self, image_path: Path) -> List[Dict[str, Any]]:
        """Generate mock predictions for testing."""
        np.random.seed(hash(str(image_path)) % 2**32)
        
        num_predictions = np.random.randint(5, 20)
        predictions = []
        
        for i in range(num_predictions):
            predictions.append({
                'id': f"pred_{i}",
                'class_id': np.random.randint(0, 5),
                'confidence': np.random.uniform(0.3, 0.99),
                'bbox': [
                    np.random.randint(0, 800),
                    np.random.randint(0, 600),
                    np.random.randint(50, 200),
                    np.random.randint(50, 200)
                ]
            })
        
        return predictions
    
    def _save_predictions(self, predictions: List[Dict[str, Any]], output_path: Path):
        """Save predictions to file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                'predictions': predictions,
                'timestamp': time.time(),
                'processor': 'AutoLabelProcessor'
            }, f, indent=2)
    
    def validate_item(self, item: BatchItem) -> bool:
        """Validate auto-labeled item."""
        if item.status != ProcessingStatus.COMPLETED:
            return False
        
        if item.target_path and item.target_path.exists():
            try:
                with open(item.target_path, 'r') as f:
                    data = json.load(f)
                return 'predictions' in data
            except:
                return False
        
        return False
    
    def get_processor_info(self) -> Dict[str, Any]:
        """Get processor information."""
        return {
            "name": "AutoLabelProcessor",
            "supported_operations": [BatchOperationType.AUTO_LABEL],
            "requirements": ["ML model"],
            "model_loaded": self.model is not None
        }


class QualityCheckProcessor(BatchProcessor):
    """Processor for annotation quality assessment."""
    
    def process_item(self, item: BatchItem, config: BatchConfiguration) -> BatchItem:
        """Process item with quality check."""
        start_time = time.time()
        
        try:
            # Simulate quality assessment
            quality_score = self._assess_quality(item.source_path)
            
            item.metadata['quality_score'] = quality_score
            item.metadata['passed_quality'] = quality_score >= config.quality_threshold
            
            if quality_score >= config.quality_threshold:
                item.status = ProcessingStatus.COMPLETED
            else:
                item.status = ProcessingStatus.FAILED
                item.error_message = f"Quality score {quality_score:.2f} below threshold {config.quality_threshold}"
            
            item.progress = 1.0
            
        except Exception as e:
            item.status = ProcessingStatus.FAILED
            item.error_message = str(e)
        
        item.processing_time = time.time() - start_time
        return item
    
    def _assess_quality(self, annotation_path: Path) -> float:
        """Assess annotation quality (mock implementation)."""
        # Mock quality assessment
        np.random.seed(hash(str(annotation_path)) % 2**32)
        return np.random.uniform(0.4, 1.0)
    
    def validate_item(self, item: BatchItem) -> bool:
        """Validate quality check results."""
        return (item.status == ProcessingStatus.COMPLETED and 
                'quality_score' in item.metadata)
    
    def get_processor_info(self) -> Dict[str, Any]:
        """Get processor information."""
        return {
            "name": "QualityCheckProcessor",
            "supported_operations": [BatchOperationType.QUALITY_CHECK],
            "requirements": ["Annotation files"]
        }


class BatchWorker(QThread):
    """Worker thread for processing batch items."""
    
    progress_updated = pyqtSignal(str, float)  # item_id, progress
    item_completed = pyqtSignal(str, object)  # item_id, BatchItem
    batch_completed = pyqtSignal()
    error_occurred = pyqtSignal(str, str)  # item_id, error_message
    
    def __init__(self, items: List[BatchItem], processor: BatchProcessor, 
                 config: BatchConfiguration):
        super().__init__()
        self.items = items
        self.processor = processor
        self.config = config
        self.should_stop = False
    
    def run(self):
        """Run the batch processing."""
        for item in self.items:
            if self.should_stop:
                break
            
            try:
                # Update progress
                self.progress_updated.emit(item.id, 0.0)
                
                # Process item
                processed_item = self.processor.process_item(item, self.config)
                
                # Validate if requested
                if self.config.validate_results:
                    if not self.processor.validate_item(processed_item):
                        processed_item.status = ProcessingStatus.FAILED
                        processed_item.error_message = "Validation failed"
                
                # Emit completion
                self.item_completed.emit(item.id, processed_item)
                
            except Exception as e:
                item.status = ProcessingStatus.FAILED
                item.error_message = str(e)
                self.error_occurred.emit(item.id, str(e))
                self.item_completed.emit(item.id, item)
        
        self.batch_completed.emit()
    
    def stop(self):
        """Stop the worker."""
        self.should_stop = True


class BatchAnnotationManager(QObject):
    """
    Manager for batch annotation operations.
    
    Features:
    - Multiple processor support
    - Parallel processing
    - Progress tracking
    - Error handling
    - Result validation
    - Resume capability
    """
    
    progress_updated = pyqtSignal(str, float)  # operation_id, progress
    operation_completed = pyqtSignal(str)  # operation_id
    item_processed = pyqtSignal(str, str, object)  # operation_id, item_id, BatchItem
    
    def __init__(self):
        super().__init__()
        self.processors = {}
        self.active_operations = {}
        self.operation_history = []
        
        # Register default processors
        self._register_default_processors()
    
    def _register_default_processors(self):
        """Register default batch processors."""
        self.processors[BatchOperationType.AUTO_LABEL] = AutoLabelProcessor()
        self.processors[BatchOperationType.QUALITY_CHECK] = QualityCheckProcessor()
    
    def register_processor(self, operation_type: BatchOperationType, processor: BatchProcessor):
        """Register a custom processor."""
        self.processors[operation_type] = processor
    
    def create_batch_operation(self, operation_id: str, items: List[BatchItem], 
                              config: BatchConfiguration) -> bool:
        """Create a new batch operation."""
        if operation_id in self.active_operations:
            return False
        
        if config.operation_type not in self.processors:
            return False
        
        operation = {
            'id': operation_id,
            'items': {item.id: item for item in items},
            'config': config,
            'processor': self.processors[config.operation_type],
            'workers': [],
            'start_time': time.time(),
            'completed_items': 0,
            'failed_items': 0
        }
        
        self.active_operations[operation_id] = operation
        return True
    
    def start_batch_operation(self, operation_id: str) -> bool:
        """Start a batch operation."""
        if operation_id not in self.active_operations:
            return False
        
        operation = self.active_operations[operation_id]
        items = list(operation['items'].values())
        config = operation['config']
        processor = operation['processor']
        
        # Split items among workers
        items_per_worker = max(1, len(items) // config.parallel_workers)
        
        for i in range(config.parallel_workers):
            start_idx = i * items_per_worker
            if i == config.parallel_workers - 1:
                worker_items = items[start_idx:]  # Last worker gets remaining items
            else:
                worker_items = items[start_idx:start_idx + items_per_worker]
            
            if worker_items:
                worker = BatchWorker(worker_items, processor, config)
                worker.item_completed.connect(
                    lambda item_id, item, op_id=operation_id: self._on_item_completed(op_id, item_id, item)
                )
                worker.batch_completed.connect(
                    lambda op_id=operation_id: self._on_worker_completed(op_id)
                )
                
                operation['workers'].append(worker)
                worker.start()
        
        return True
    
    def _on_item_completed(self, operation_id: str, item_id: str, item: BatchItem):
        """Handle item completion."""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        operation['items'][item_id] = item
        
        if item.status == ProcessingStatus.COMPLETED:
            operation['completed_items'] += 1
        elif item.status == ProcessingStatus.FAILED:
            operation['failed_items'] += 1
        
        # Calculate overall progress
        total_items = len(operation['items'])
        processed_items = operation['completed_items'] + operation['failed_items']
        progress = processed_items / total_items if total_items > 0 else 0.0
        
        self.progress_updated.emit(operation_id, progress)
        self.item_processed.emit(operation_id, item_id, item)
    
    def _on_worker_completed(self, operation_id: str):
        """Handle worker completion."""
        if operation_id not in self.active_operations:
            return
        
        operation = self.active_operations[operation_id]
        
        # Check if all workers are done
        all_done = all(not worker.isRunning() for worker in operation['workers'])
        
        if all_done:
            operation['end_time'] = time.time()
            self.operation_completed.emit(operation_id)
            
            # Move to history
            self.operation_history.append(operation)
            del self.active_operations[operation_id]
    
    def stop_operation(self, operation_id: str) -> bool:
        """Stop a running operation."""
        if operation_id not in self.active_operations:
            return False
        
        operation = self.active_operations[operation_id]
        
        for worker in operation['workers']:
            worker.stop()
            worker.wait()  # Wait for worker to finish
        
        return True
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an operation."""
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            return self._create_status_dict(operation, active=True)
        
        # Check history
        for operation in self.operation_history:
            if operation['id'] == operation_id:
                return self._create_status_dict(operation, active=False)
        
        return None
    
    def _create_status_dict(self, operation: Dict[str, Any], active: bool) -> Dict[str, Any]:
        """Create status dictionary for an operation."""
        total_items = len(operation['items'])
        completed_items = operation['completed_items']
        failed_items = operation['failed_items']
        
        status = {
            'id': operation['id'],
            'active': active,
            'total_items': total_items,
            'completed_items': completed_items,
            'failed_items': failed_items,
            'pending_items': total_items - completed_items - failed_items,
            'start_time': operation['start_time'],
            'operation_type': operation['config'].operation_type.value
        }
        
        if 'end_time' in operation:
            status['end_time'] = operation['end_time']
            status['duration'] = operation['end_time'] - operation['start_time']
        
        return status
    
    def get_processor_info(self, operation_type: BatchOperationType) -> Optional[Dict[str, Any]]:
        """Get information about a processor."""
        if operation_type in self.processors:
            return self.processors[operation_type].get_processor_info()
        return None
    
    def export_results(self, operation_id: str, output_path: Path) -> bool:
        """Export operation results."""
        status = self.get_operation_status(operation_id)
        if not status:
            return False
        
        # Find operation in history or active operations
        operation = None
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
        else:
            for op in self.operation_history:
                if op['id'] == operation_id:
                    operation = op
                    break
        
        if not operation:
            return False
        
        # Export results
        results = {
            'operation_status': status,
            'items': {item_id: {
                'id': item.id,
                'source_path': str(item.source_path),
                'target_path': str(item.target_path) if item.target_path else None,
                'status': item.status.value,
                'progress': item.progress,
                'error_message': item.error_message,
                'metadata': item.metadata,
                'processing_time': item.processing_time
            } for item_id, item in operation['items'].items()},
            'configuration': {
                'operation_type': operation['config'].operation_type.value,
                'parallel_workers': operation['config'].parallel_workers,
                'batch_size': operation['config'].batch_size,
                'confidence_threshold': operation['config'].confidence_threshold,
                'quality_threshold': operation['config'].quality_threshold
            }
        }
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            return True
        except Exception:
            return False


class BatchAnnotationWidget(QWidget):
    """
    Widget for batch annotation operations.
    
    Features:
    - Operation setup and configuration
    - Progress monitoring
    - Result visualization
    - Error handling
    - Export capabilities
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = BatchAnnotationManager()
        self.current_operation_id = None
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("🔄 Batch Annotation Tools")
        header_label.setStyleSheet("font-weight: bold; font-size: 16px; padding: 8px;")
        layout.addWidget(header_label)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Setup tab
        setup_tab = self._create_setup_tab()
        self.tab_widget.addTab(setup_tab, "Setup")
        
        # Progress tab
        progress_tab = self._create_progress_tab()
        self.tab_widget.addTab(progress_tab, "Progress")
        
        # Results tab
        results_tab = self._create_results_tab()
        self.tab_widget.addTab(results_tab, "Results")
        
        layout.addWidget(self.tab_widget)
        
        self.setLayout(layout)
    
    def _create_setup_tab(self) -> QWidget:
        """Create the setup tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Operation type
        op_group = QGroupBox("Operation Type")
        op_layout = QVBoxLayout()
        
        self.operation_combo = QComboBox()
        for op_type in BatchOperationType:
            self.operation_combo.addItem(op_type.value.title(), op_type)
        op_layout.addWidget(self.operation_combo)
        
        op_group.setLayout(op_layout)
        layout.addWidget(op_group)
        
        # Configuration
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        
        # Workers
        workers_layout = QHBoxLayout()
        workers_layout.addWidget(QLabel("Parallel Workers:"))
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 16)
        self.workers_spin.setValue(4)
        workers_layout.addWidget(self.workers_spin)
        workers_layout.addStretch()
        config_layout.addLayout(workers_layout)
        
        # Thresholds
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Confidence Threshold:"))
        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(0, 100)
        self.confidence_spin.setValue(80)
        self.confidence_spin.setSuffix("%")
        conf_layout.addWidget(self.confidence_spin)
        conf_layout.addStretch()
        config_layout.addLayout(conf_layout)
        
        # Options
        self.auto_save_check = QCheckBox("Auto-save results")
        self.auto_save_check.setChecked(True)
        config_layout.addWidget(self.auto_save_check)
        
        self.validate_check = QCheckBox("Validate results")
        self.validate_check.setChecked(True)
        config_layout.addWidget(self.validate_check)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # File selection
        files_group = QGroupBox("Input Files")
        files_layout = QVBoxLayout()
        
        files_button_layout = QHBoxLayout()
        self.add_files_btn = QPushButton("Add Files")
        self.add_folder_btn = QPushButton("Add Folder")
        self.clear_files_btn = QPushButton("Clear")
        
        files_button_layout.addWidget(self.add_files_btn)
        files_button_layout.addWidget(self.add_folder_btn)
        files_button_layout.addWidget(self.clear_files_btn)
        files_button_layout.addStretch()
        
        files_layout.addLayout(files_button_layout)
        
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(150)
        files_layout.addWidget(self.files_list)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Start button
        self.start_btn = QPushButton("Start Batch Operation")
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        layout.addWidget(self.start_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_progress_tab(self) -> QWidget:
        """Create the progress tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Status
        status_group = QGroupBox("Operation Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("No operation running")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        status_layout.addWidget(self.progress_bar)
        
        button_layout = QHBoxLayout()
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()
        
        status_layout.addLayout(button_layout)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Progress details
        details_group = QGroupBox("Progress Details")
        details_layout = QVBoxLayout()
        
        self.progress_text = QTextEdit()
        self.progress_text.setMaximumHeight(200)
        self.progress_text.setReadOnly(True)
        details_layout.addWidget(self.progress_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_results_tab(self) -> QWidget:
        """Create the results tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Results table
        results_group = QGroupBox("Results Summary")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Item", "Status", "Progress", "Time", "Error"
        ])
        results_layout.addWidget(self.results_table)
        
        # Export button
        export_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        export_layout.addStretch()
        
        results_layout.addLayout(export_layout)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        widget.setLayout(layout)
        return widget
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.add_files_btn.clicked.connect(self._add_files)
        self.add_folder_btn.clicked.connect(self._add_folder)
        self.clear_files_btn.clicked.connect(self._clear_files)
        self.start_btn.clicked.connect(self._start_operation)
        self.stop_btn.clicked.connect(self._stop_operation)
        self.export_btn.clicked.connect(self._export_results)
        
        # Manager signals
        self.manager.progress_updated.connect(self._update_progress)
        self.manager.operation_completed.connect(self._operation_completed)
        self.manager.item_processed.connect(self._item_processed)
    
    def _add_files(self):
        """Add files to the batch."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        for file_path in files:
            item = QListWidgetItem(Path(file_path).name)
            item.setData(Qt.UserRole, file_path)
            self.files_list.addItem(item)
    
    def _add_folder(self):
        """Add folder to the batch."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            folder_path = Path(folder)
            
            # Add all image files in folder
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']:
                for file_path in folder_path.glob(ext):
                    item = QListWidgetItem(f"{folder_path.name}/{file_path.name}")
                    item.setData(Qt.UserRole, str(file_path))
                    self.files_list.addItem(item)
    
    def _clear_files(self):
        """Clear the file list."""
        self.files_list.clear()
    
    def _start_operation(self):
        """Start the batch operation."""
        if self.files_list.count() == 0:
            QMessageBox.warning(self, "Warning", "No files selected for processing.")
            return
        
        # Create batch items
        items = []
        for i in range(self.files_list.count()):
            item_widget = self.files_list.item(i)
            file_path = item_widget.data(Qt.UserRole)
            
            batch_item = BatchItem(
                id=f"item_{i}",
                source_path=Path(file_path),
                target_path=Path(file_path).with_suffix('.json')
            )
            items.append(batch_item)
        
        # Create configuration
        config = BatchConfiguration(
            operation_type=self.operation_combo.currentData(),
            parallel_workers=self.workers_spin.value(),
            confidence_threshold=self.confidence_spin.value() / 100.0,
            auto_save=self.auto_save_check.isChecked(),
            validate_results=self.validate_check.isChecked()
        )
        
        # Start operation
        operation_id = f"operation_{int(time.time())}"
        self.current_operation_id = operation_id
        
        if self.manager.create_batch_operation(operation_id, items, config):
            if self.manager.start_batch_operation(operation_id):
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                self.tab_widget.setCurrentIndex(1)  # Switch to progress tab
                
                self.status_label.setText(f"Running {config.operation_type.value} operation...")
                self.progress_text.clear()
            else:
                QMessageBox.critical(self, "Error", "Failed to start batch operation.")
        else:
            QMessageBox.critical(self, "Error", "Failed to create batch operation.")
    
    def _stop_operation(self):
        """Stop the current operation."""
        if self.current_operation_id:
            self.manager.stop_operation(self.current_operation_id)
            self._reset_ui()
    
    def _update_progress(self, operation_id: str, progress: float):
        """Update progress display."""
        if operation_id == self.current_operation_id:
            self.progress_bar.setValue(int(progress * 100))
    
    def _item_processed(self, operation_id: str, item_id: str, item: BatchItem):
        """Handle item processing completion."""
        if operation_id == self.current_operation_id:
            status_text = f"✓" if item.status == ProcessingStatus.COMPLETED else "✗"
            message = f"{status_text} {item.source_path.name} - {item.status.value}"
            if item.error_message:
                message += f" ({item.error_message})"
            
            self.progress_text.append(message)
    
    def _operation_completed(self, operation_id: str):
        """Handle operation completion."""
        if operation_id == self.current_operation_id:
            self.status_label.setText("Operation completed")
            self._update_results_table()
            self._reset_ui()
            self.tab_widget.setCurrentIndex(2)  # Switch to results tab
    
    def _update_results_table(self):
        """Update the results table."""
        if not self.current_operation_id:
            return
        
        status = self.manager.get_operation_status(self.current_operation_id)
        if not status:
            return
        
        # Find operation data
        operation = None
        for op in self.manager.operation_history:
            if op['id'] == self.current_operation_id:
                operation = op
                break
        
        if not operation:
            return
        
        # Populate table
        items = operation['items']
        self.results_table.setRowCount(len(items))
        
        for row, (item_id, item) in enumerate(items.items()):
            self.results_table.setItem(row, 0, QTableWidgetItem(item.source_path.name))
            self.results_table.setItem(row, 1, QTableWidgetItem(item.status.value))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{item.progress:.1%}"))
            self.results_table.setItem(row, 3, QTableWidgetItem(f"{item.processing_time:.2f}s"))
            self.results_table.setItem(row, 4, QTableWidgetItem(item.error_message))
        
        self.export_btn.setEnabled(True)
    
    def _export_results(self):
        """Export operation results."""
        if not self.current_operation_id:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", f"batch_results_{self.current_operation_id}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            if self.manager.export_results(self.current_operation_id, Path(file_path)):
                QMessageBox.information(self, "Success", "Results exported successfully.")
            else:
                QMessageBox.critical(self, "Error", "Failed to export results.")
    
    def _reset_ui(self):
        """Reset UI to initial state."""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)


def main():
    """Test the batch annotation tools."""
    if not PYQT5_AVAILABLE:
        print("PyQt5 not available")
        return
    
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("Batch Annotation Tools Test")
    window.setGeometry(100, 100, 800, 600)
    
    # Create widget
    batch_widget = BatchAnnotationWidget()
    window.setCentralWidget(batch_widget)
    
    window.show()
    
    # Print processor info
    manager = batch_widget.manager
    for op_type in BatchOperationType:
        info = manager.get_processor_info(op_type)
        if info:
            print(f"Processor {op_type.value}: {info}")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()