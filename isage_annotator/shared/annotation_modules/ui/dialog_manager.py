"""
Dialog Manager - Manages modal dialogs and user interactions

This module provides centralized dialog management for various user interactions
including file dialogs, confirmation dialogs, and custom modal dialogs.
"""

import os
from typing import Dict, Any, List, Optional, Tuple, Callable
from ..base_protocols import BaseComponent, QWidget, QDialog, QMessageBox, QFileDialog
from ..base_protocols import QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout
from ..base_protocols import QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QCheckBox, QSpinBox
from .base_ui import BaseUI


class DialogManager(BaseUI):
    """Centralized dialog management system."""
    
    # Dialog manager signals
    dialogOpened = pyqtSignal(str)  # dialog_type
    dialogClosed = pyqtSignal(str, object)  # dialog_type, result
    dialogAccepted = pyqtSignal(str, object)  # dialog_type, data
    dialogRejected = pyqtSignal(str)  # dialog_type
    
    def __init__(self, name: str = "dialog_manager", version: str = "1.0.0"):
        super().__init__(name, version)
        
        # Dialog configuration
        self._parent_widget: Optional[QWidget] = None
        self._theme_manager = None
        self._modal_dialogs: Dict[str, QDialog] = {}
        
        # Dialog settings
        self._default_dialog_size: Tuple[int, int] = (400, 300)
        self._remember_positions: bool = True
        self._dialog_positions: Dict[str, Tuple[int, int]] = {}
        
        # File dialog settings
        self._last_directory: str = str(Path.cwd())
        self._file_filters: Dict[str, str] = {
            'image': 'Images (*.png *.jpg *.jpeg *.bmp *.tiff *.gif)',
            'json': 'JSON Files (*.json)',
            'text': 'Text Files (*.txt)',
            'all': 'All Files (*)'
        }
        
        # Dialog templates
        self._dialog_templates: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self._dialog_stats: Dict[str, int] = {
            'total_opened': 0,
            'total_accepted': 0,
            'total_rejected': 0
        }
    
    def initialize(self, **kwargs) -> bool:
        """Initialize dialog manager."""
        self._parent_widget = kwargs.get('parent_widget', None)
        self._theme_manager = kwargs.get('theme_manager', None)
        self._default_dialog_size = kwargs.get('default_dialog_size', (400, 300))
        self._remember_positions = kwargs.get('remember_positions', True)
        self._last_directory = kwargs.get('default_directory', str(Path.cwd()))
        
        # Add custom file filters
        if 'file_filters' in kwargs:
            self._file_filters.update(kwargs['file_filters'])
        
        return super().initialize(**kwargs)
    
    def set_parent_widget(self, parent: QWidget) -> None:
        """Set parent widget for dialogs."""
        self._parent_widget = parent
    
    def set_theme_manager(self, theme_manager) -> None:
        """Set theme manager for dialog styling."""
        self._theme_manager = theme_manager
    
    def show_message(self, title: str, message: str, message_type: str = "info", buttons: Optional[List[str]] = None) -> str:
        """Show message dialog."""
        try:
            self._dialog_stats['total_opened'] += 1
            self.dialogOpened.emit('message')
            
            # Create message box
            msg_box = QMessageBox(self._parent_widget)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            
            # Set icon based on type
            if message_type == "info":
                msg_box.setIcon(QMessageBox.Information)
            elif message_type == "warning":
                msg_box.setIcon(QMessageBox.Warning)
            elif message_type == "error":
                msg_box.setIcon(QMessageBox.Critical)
            elif message_type == "question":
                msg_box.setIcon(QMessageBox.Question)
            
            # Set buttons
            if buttons:
                msg_box.setStandardButtons(QMessageBox.NoButton)
                for button_text in buttons:
                    msg_box.addButton(button_text, QMessageBox.ActionRole)
            else:
                if message_type == "question":
                    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                else:
                    msg_box.setStandardButtons(QMessageBox.Ok)
            
            # Apply theme if available
            if self._theme_manager:
                self._apply_theme_to_dialog(msg_box)
            
            # Show dialog
            result = msg_box.exec_()
            
            # Get button text
            clicked_button = msg_box.clickedButton()
            if clicked_button:
                button_text = clicked_button.text()
            else:
                button_text = "Ok" if result == QMessageBox.Ok else "Cancel"
            
            # Update statistics
            if result == QMessageBox.Ok or result == QMessageBox.Yes:
                self._dialog_stats['total_accepted'] += 1
                self.dialogAccepted.emit('message', button_text)
            else:
                self._dialog_stats['total_rejected'] += 1
                self.dialogRejected.emit('message')
            
            self.dialogClosed.emit('message', button_text)
            return button_text
            
        except Exception as e:
            self.emit_error(f"Error showing message dialog: {str(e)}")
            return "Error"
    
    def show_confirmation(self, title: str, message: str, buttons: Optional[Tuple[str, str]] = None) -> bool:
        """Show confirmation dialog."""
        try:
            if buttons is None:
                buttons = ("Yes", "No")
            
            result = self.show_message(title, message, "question", list(buttons))
            return result == buttons[0]
            
        except Exception as e:
            self.emit_error(f"Error showing confirmation dialog: {str(e)}")
            return False
    
    def show_input_dialog(self, title: str, label: str, default_value: str = "", input_type: str = "text") -> Optional[str]:
        """Show input dialog."""
        try:
            from PyQt5.QtWidgets import QInputDialog
            
            self._dialog_stats['total_opened'] += 1
            self.dialogOpened.emit('input')
            
            if input_type == "text":
                result, ok = QInputDialog.getText(self._parent_widget, title, label, text=default_value)
            elif input_type == "multiline":
                result, ok = QInputDialog.getMultiLineText(self._parent_widget, title, label, text=default_value)
            elif input_type == "int":
                result, ok = QInputDialog.getInt(self._parent_widget, title, label, value=int(default_value) if default_value else 0)
            elif input_type == "double":
                result, ok = QInputDialog.getDouble(self._parent_widget, title, label, value=float(default_value) if default_value else 0.0)
            else:
                result, ok = QInputDialog.getText(self._parent_widget, title, label, text=default_value)
            
            # Update statistics
            if ok:
                self._dialog_stats['total_accepted'] += 1
                self.dialogAccepted.emit('input', result)
                self.dialogClosed.emit('input', result)
                return str(result)
            else:
                self._dialog_stats['total_rejected'] += 1
                self.dialogRejected.emit('input')
                self.dialogClosed.emit('input', None)
                return None
                
        except Exception as e:
            self.emit_error(f"Error showing input dialog: {str(e)}")
            return None
    
    def show_file_dialog(self, dialog_type: str, title: str, file_filter: str = "all", directory: Optional[str] = None) -> Optional[str]:
        """Show file dialog."""
        try:
            self._dialog_stats['total_opened'] += 1
            self.dialogOpened.emit('file')
            
            if directory is None:
                directory = self._last_directory
            
            # Get filter string
            filter_string = self._file_filters.get(file_filter, self._file_filters['all'])
            
            # Show appropriate dialog
            if dialog_type == "open":
                result, _ = QFileDialog.getOpenFileName(self._parent_widget, title, directory, filter_string)
            elif dialog_type == "save":
                result, _ = QFileDialog.getSaveFileName(self._parent_widget, title, directory, filter_string)
            elif dialog_type == "directory":
                result = QFileDialog.getExistingDirectory(self._parent_widget, title, directory)
            elif dialog_type == "open_multiple":
                results, _ = QFileDialog.getOpenFileNames(self._parent_widget, title, directory, filter_string)
                result = results if results else None
            else:
                result = None
            
            # Update last directory
            if result:
                if isinstance(result, str):
                    self._last_directory = os.path.dirname(result)
                elif isinstance(result, list) and result:
                    self._last_directory = os.path.dirname(result[0])
                
                self._dialog_stats['total_accepted'] += 1
                self.dialogAccepted.emit('file', result)
            else:
                self._dialog_stats['total_rejected'] += 1
                self.dialogRejected.emit('file')
            
            self.dialogClosed.emit('file', result)
            return result
            
        except Exception as e:
            self.emit_error(f"Error showing file dialog: {str(e)}")
            return None
    
    def show_custom_dialog(self, dialog_id: str, title: str, fields: List[Dict[str, Any]], size: Optional[Tuple[int, int]] = None) -> Optional[Dict[str, Any]]:
        """Show custom dialog with specified fields."""
        try:
            self._dialog_stats['total_opened'] += 1
            self.dialogOpened.emit('custom')
            
            # Create dialog
            dialog = QDialog(self._parent_widget)
            dialog.setWindowTitle(title)
            dialog.setModal(True)
            
            # Set size
            if size:
                dialog.resize(size[0], size[1])
            else:
                dialog.resize(*self._default_dialog_size)
            
            # Restore position if remembered
            if self._remember_positions and dialog_id in self._dialog_positions:
                pos = self._dialog_positions[dialog_id]
                dialog.move(pos[0], pos[1])
            
            # Create layout
            layout = QVBoxLayout()
            form_layout = QFormLayout()
            
            # Create fields
            field_widgets = {}
            for field in fields:
                field_name = field['name']
                field_type = field.get('type', 'text')
                field_label = field.get('label', field_name)
                default_value = field.get('default', '')
                
                widget = self._create_field_widget(field_type, field, default_value)
                if widget:
                    form_layout.addRow(field_label, widget)
                    field_widgets[field_name] = widget
            
            layout.addLayout(form_layout)
            
            # Add buttons
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)
            
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            # Apply theme if available
            if self._theme_manager:
                self._apply_theme_to_dialog(dialog)
            
            # Show dialog
            result = dialog.exec_()
            
            # Remember position
            if self._remember_positions:
                self._dialog_positions[dialog_id] = (dialog.x(), dialog.y())
            
            # Get field values
            if result == QDialog.Accepted:
                field_values = {}
                for field_name, widget in field_widgets.items():
                    field_values[field_name] = self._get_field_value(widget)
                
                self._dialog_stats['total_accepted'] += 1
                self.dialogAccepted.emit('custom', field_values)
                self.dialogClosed.emit('custom', field_values)
                return field_values
            else:
                self._dialog_stats['total_rejected'] += 1
                self.dialogRejected.emit('custom')
                self.dialogClosed.emit('custom', None)
                return None
                
        except Exception as e:
            self.emit_error(f"Error showing custom dialog: {str(e)}")
            return None
    
    def create_dialog_template(self, template_id: str, title: str, fields: List[Dict[str, Any]], size: Optional[Tuple[int, int]] = None) -> None:
        """Create reusable dialog template."""
        try:
            self._dialog_templates[template_id] = {
                'title': title,
                'fields': fields,
                'size': size
            }
            
            self.emit_state_changed({'dialog_templates_count': len(self._dialog_templates)})
            
        except Exception as e:
            self.emit_error(f"Error creating dialog template: {str(e)}")
    
    def show_template_dialog(self, template_id: str, dialog_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Show dialog from template."""
        try:
            if template_id not in self._dialog_templates:
                self.emit_error(f"Dialog template not found: {template_id}")
                return None
            
            template = self._dialog_templates[template_id]
            
            if dialog_id is None:
                dialog_id = template_id
            
            return self.show_custom_dialog(
                dialog_id,
                template['title'],
                template['fields'],
                template['size']
            )
            
        except Exception as e:
            self.emit_error(f"Error showing template dialog: {str(e)}")
            return None
    
    def show_progress_dialog(self, title: str, message: str, maximum: int = 100, cancellable: bool = True) -> 'ProgressDialog':
        """Show progress dialog."""
        try:
            from .progress_dialog import ProgressDialog
            
            self._dialog_stats['total_opened'] += 1
            self.dialogOpened.emit('progress')
            
            dialog = ProgressDialog(self._parent_widget, title, message, maximum, cancellable)
            
            # Apply theme if available
            if self._theme_manager:
                self._apply_theme_to_dialog(dialog)
            
            return dialog
            
        except Exception as e:
            self.emit_error(f"Error showing progress dialog: {str(e)}")
            return None
    
    def close_all_dialogs(self) -> None:
        """Close all open modal dialogs."""
        try:
            for dialog in self._modal_dialogs.values():
                if dialog.isVisible():
                    dialog.close()
            
            self._modal_dialogs.clear()
            
        except Exception as e:
            self.emit_error(f"Error closing dialogs: {str(e)}")
    
    def set_last_directory(self, directory: str) -> None:
        """Set last used directory for file dialogs."""
        if os.path.exists(directory):
            self._last_directory = directory
            self.emit_state_changed({'last_directory': directory})
    
    def get_last_directory(self) -> str:
        """Get last used directory."""
        return self._last_directory
    
    def add_file_filter(self, filter_name: str, filter_string: str) -> None:
        """Add custom file filter."""
        self._file_filters[filter_name] = filter_string
        self.emit_state_changed({'file_filters_count': len(self._file_filters)})
    
    def get_file_filters(self) -> Dict[str, str]:
        """Get all file filters."""
        return self._file_filters.copy()
    
    def get_dialog_statistics(self) -> Dict[str, Any]:
        """Get dialog usage statistics."""
        return {
            'total_opened': self._dialog_stats['total_opened'],
            'total_accepted': self._dialog_stats['total_accepted'],
            'total_rejected': self._dialog_stats['total_rejected'],
            'acceptance_rate': self._dialog_stats['total_accepted'] / max(1, self._dialog_stats['total_opened']),
            'templates_count': len(self._dialog_templates),
            'remembered_positions': len(self._dialog_positions)
        }
    
    def _create_field_widget(self, field_type: str, field_config: Dict[str, Any], default_value: Any) -> Optional[QWidget]:
        """Create widget for dialog field."""
        try:
            if field_type == 'text':
                widget = QLineEdit()
                widget.setText(str(default_value))
                return widget
            
            elif field_type == 'multiline':
                widget = QTextEdit()
                widget.setPlainText(str(default_value))
                widget.setMaximumHeight(100)
                return widget
            
            elif field_type == 'int':
                widget = QSpinBox()
                widget.setMinimum(field_config.get('min', -999999))
                widget.setMaximum(field_config.get('max', 999999))
                widget.setValue(int(default_value) if default_value else 0)
                return widget
            
            elif field_type == 'checkbox':
                widget = QCheckBox()
                widget.setChecked(bool(default_value))
                return widget
            
            elif field_type == 'combo':
                widget = QComboBox()
                items = field_config.get('items', [])
                widget.addItems(items)
                if default_value in items:
                    widget.setCurrentText(str(default_value))
                return widget
            
            return None
            
        except Exception as e:
            self.emit_error(f"Error creating field widget: {str(e)}")
            return None
    
    def _get_field_value(self, widget: QWidget) -> Any:
        """Get value from field widget."""
        try:
            if isinstance(widget, QLineEdit):
                return widget.text()
            elif isinstance(widget, QTextEdit):
                return widget.toPlainText()
            elif isinstance(widget, QSpinBox):
                return widget.value()
            elif isinstance(widget, QCheckBox):
                return widget.isChecked()
            elif isinstance(widget, QComboBox):
                return widget.currentText()
            
            return None
            
        except Exception as e:
            self.emit_error(f"Error getting field value: {str(e)}")
            return None
    
    def _apply_theme_to_dialog(self, dialog: QWidget) -> None:
        """Apply theme to dialog."""
        try:
            if not self._theme_manager:
                return
            
            # Get theme colors
            colors = self._theme_manager.get_all_colors()
            
            # Apply stylesheet
            dialog.setStyleSheet(f"""
                QDialog {{
                    background-color: {colors.get('background', '#ffffff')};
                    color: {colors.get('text', '#000000')};
                }}
                
                QLabel {{
                    color: {colors.get('text', '#000000')};
                }}
                
                QPushButton {{
                    background-color: {colors.get('button_background', '#f0f0f0')};
                    color: {colors.get('text', '#000000')};
                    border: 1px solid {colors.get('border', '#c0c0c0')};
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-height: 20px;
                }}
                
                QPushButton:hover {{
                    background-color: {colors.get('button_hover', '#e0e0e0')};
                }}
                
                QPushButton:pressed {{
                    background-color: {colors.get('button_pressed', '#d0d0d0')};
                }}
                
                QLineEdit, QTextEdit, QSpinBox, QComboBox {{
                    background-color: {colors.get('input_background', '#ffffff')};
                    color: {colors.get('text', '#000000')};
                    border: 1px solid {colors.get('input_border', '#c0c0c0')};
                    border-radius: 4px;
                    padding: 4px;
                }}
                
                QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
                    border: 2px solid {colors.get('input_focus', '#4a90e2')};
                }}
            """)
            
        except Exception as e:
            self.emit_error(f"Error applying theme to dialog: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dialog manager statistics."""
        stats = super().get_statistics()
        stats.update({
            'default_dialog_size': self._default_dialog_size,
            'remember_positions': self._remember_positions,
            'last_directory': self._last_directory,
            'file_filters_count': len(self._file_filters),
            'dialog_templates_count': len(self._dialog_templates),
            'modal_dialogs_count': len(self._modal_dialogs),
            'dialog_statistics': self.get_dialog_statistics()
        })
        return stats