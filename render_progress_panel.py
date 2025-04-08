# Filename: render_progress_panel.py

import nuke
import nukescripts
import threading
import subprocess
import time
import re
import os
import sys
import multiprocessing
import logging
from PySide6 import QtWidgets, QtCore, QtGui
from threading import Lock
from PySide6.QtCore import QSettings

# Attempt to import psutil for system information
try:
    import psutil
except ImportError:
    psutil = None
    logging.warning('psutil module not found. System RAM information will not be available.')

# Import signal module
import signal

# Set up logging
log_file = os.path.join(os.path.expanduser('~'), '.nuke', 'render_progress_panel.log')
logging.basicConfig(
    filename=log_file,
    filemode='a',
    format='%(asctime)s [%(levelname)s]: %(message)s',
    level=logging.INFO
)

class RenderProgressPanel(QtWidgets.QWidget):
    """
    A panel for managing and monitoring multi-threaded rendering of Write nodes in Nuke.
    """

    def __init__(self, parent=None):
        super(RenderProgressPanel, self).__init__(parent)
        self.setWindowTitle('Render Progress Panel')
        self.setMinimumSize(500, 400)  # Adjusted panel size
        self.render_threads = []
        self.thread_widgets = {}
        self.threads = []
        self.is_rendering = False
        self.progress_lock = Lock()
        self.settings = QSettings('YourCompanyName', 'RenderProgressPanel')
        self.init_ui()

    def init_ui(self):
        # Main layout
        self.layout = QtWidgets.QVBoxLayout(self)

        banner_path = os.path.join(os.path.dirname(__file__), 'banner.png')
        if os.path.exists(banner_path):
            self.banner_label = QtWidgets.QLabel()
            self.pixmap = QtGui.QPixmap(banner_path)
            
            # Set the label to the original size of the pixmap
            self.banner_label.setPixmap(self.pixmap)
            self.banner_label.setFixedSize(self.pixmap.size())
            
            # Create a horizontal layout to center the banner
            banner_layout = QtWidgets.QHBoxLayout()
            banner_layout.addStretch()
            banner_layout.addWidget(self.banner_label)
            banner_layout.addStretch()
            
            # Add the banner layout to the main layout
            self.layout.addLayout(banner_layout)
        else:
            logging.warning(f"Banner image not found at {banner_path}")
#################################################################################################
        # Write node selection dropdown
        write_node_layout = QtWidgets.QVBoxLayout()  # Main vertical layout
        hbox_write_node = QtWidgets.QHBoxLayout()  # Horizontal layout for label and combo box

        self.write_node_label = QtWidgets.QLabel('Write Node:')
        self.write_node_combo = QtWidgets.QComboBox()
        self.populate_write_nodes()

        # Set size policies to keep widgets together
        self.write_node_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.write_node_combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Add widgets to horizontal layout
        hbox_write_node.addWidget(self.write_node_label)
        hbox_write_node.addWidget(self.write_node_combo)
        hbox_write_node.addStretch()  # This will push the widgets to the left

        # Create separator line
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)

        # Add horizontal layout and separator to the main vertical layout
        write_node_layout.addLayout(hbox_write_node)
        write_node_layout.addWidget(separator)

        # Add the main write node layout to the parent layout
        self.layout.addLayout(write_node_layout)
#################################################################################################
        # Custom frame range and overwrite option
        frame_range_layout = QtWidgets.QVBoxLayout()
        frame_range_layout_1 = QtWidgets.QHBoxLayout()
        frame_range_layout_2 = QtWidgets.QHBoxLayout()

        self.custom_frame_range_checkbox = QtWidgets.QCheckBox("Frame Range")
        self.overwrite_checkbox = QtWidgets.QCheckBox("Overwrite")
        self.start_frame_spinbox = QtWidgets.QSpinBox()
        self.start_frame_spinbox.setMinimum(-99999)
        self.start_frame_spinbox.setMaximum(99999)
        self.start_frame_spinbox.setEnabled(False)
        self.end_frame_spinbox = QtWidgets.QSpinBox()
        self.end_frame_spinbox.setMinimum(-99999)
        self.end_frame_spinbox.setMaximum(99999)
        self.end_frame_spinbox.setEnabled(False)

        # Adjust sizes and spacing
        self.custom_frame_range_checkbox.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.overwrite_checkbox.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.start_frame_spinbox.setMaximumWidth(80)
        self.end_frame_spinbox.setMaximumWidth(80)

        # Add "Frames" title
        frames_title = QtWidgets.QLabel("Frames")
        frames_title.setAlignment(QtCore.Qt.AlignLeft)
        font = frames_title.font()
        font.setBold(True)
        frames_title.setFont(font)

        # First line: Frame Range and Overwrite checkboxes
        frame_range_layout_1.addWidget(self.custom_frame_range_checkbox)
        frame_range_layout_1.addWidget(self.overwrite_checkbox)
        frame_range_layout_1.addStretch()

        # Second line: First and Last frame inputs
        frame_range_layout_2.addWidget(QtWidgets.QLabel("First:"))
        frame_range_layout_2.addWidget(self.start_frame_spinbox)
        frame_range_layout_2.addWidget(QtWidgets.QLabel("Last:"))
        frame_range_layout_2.addWidget(self.end_frame_spinbox)
        frame_range_layout_2.addStretch()

        # Add separator line
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)

        # Arrange all elements in the main frame_range_layout
        frame_range_layout.addWidget(frames_title)
        frame_range_layout.addLayout(frame_range_layout_1)
        frame_range_layout.addLayout(frame_range_layout_2)
        frame_range_layout.addWidget(separator)

        # Add the main layout to the parent layout
        self.layout.addLayout(frame_range_layout)
#################################################################################################
        # Batch Rendering Options
        batch_layout = QtWidgets.QVBoxLayout()  # Changed to QVBoxLayout
        batch_options_layout = QtWidgets.QHBoxLayout()  # New horizontal layout for existing elements
        self.batch_render_checkbox = QtWidgets.QCheckBox("Enable Batch Rendering")
        self.batch_size_label = QtWidgets.QLabel("Batch Size:")
        self.batch_size_spinbox = QtWidgets.QSpinBox()
        self.batch_size_spinbox.setMinimum(1)
        self.batch_size_spinbox.setMaximum(10000)
        self.batch_size_spinbox.setValue(10)
        self.batch_size_spinbox.setEnabled(False)  # Disabled by default

        # Add existing widgets to the horizontal layout
        batch_options_layout.addWidget(self.batch_render_checkbox)
        batch_options_layout.addWidget(self.batch_size_label)
        batch_options_layout.addWidget(self.batch_size_spinbox)
        batch_options_layout.addStretch()

        # Create separator line
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)

        # Add horizontal layout and separator to the main vertical layout
        batch_layout.addLayout(batch_options_layout)
        batch_layout.addWidget(separator)

        # Add the main batch layout to the parent layout
        self.layout.addLayout(batch_layout)
        # Connect the checkbox to enable/disable the batch size spinbox
        self.batch_render_checkbox.stateChanged.connect(self.batch_render_toggled)
#################################################################################################

        # Number of Threads and suggestions
        hbox_threads = QtWidgets.QHBoxLayout()
        self.threads_label = QtWidgets.QLabel('Number of Instances:')
        self.threads_spinbox = QtWidgets.QSpinBox()
        cpu_count = multiprocessing.cpu_count()
        self.threads_spinbox.setMinimum(1)
        self.threads_spinbox.setMaximum(cpu_count)
        # Suggested value based on CPU cores
        suggested_threads = max(1, cpu_count // 2)
        saved_num_threads = self.settings.value('num_threads', defaultValue=suggested_threads, type=int)
        self.threads_spinbox.setValue(saved_num_threads)
        self.threads_recommend_label = QtWidgets.QLabel(f'Suggested: {suggested_threads}')
        self.threads_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.threads_spinbox.setMaximumWidth(80)
        hbox_threads.addWidget(self.threads_label)
        hbox_threads.addWidget(self.threads_spinbox)
        hbox_threads.addWidget(self.threads_recommend_label)
        hbox_threads.addStretch()
        self.layout.addLayout(hbox_threads)

        # # Expose -m and -c variables
        hbox_memory = QtWidgets.QHBoxLayout()
        self.memory_label = QtWidgets.QLabel('Max Threads (-m):')
        self.memory_lineedit = QtWidgets.QLineEdit()
        self.memory_lineedit.setMaximumWidth(100)
        self.memory_lineedit.setPlaceholderText('e.g., 4G')
        # Suggested values based on system RAM
        if psutil:
            total_ram = psutil.virtual_memory().total
            suggested_m = f"{int(total_ram * 0.8 / (1024**3))}G"
            suggested_c = f"{int(total_ram * 0.5 / (1024**3))}G"
        else:
            suggested_m = 'Specify'
            suggested_c = 'Specify'
        self.memory_suggest_label = QtWidgets.QLabel(f'Suggested: {suggested_m}')
        hbox_memory.addWidget(self.memory_label)
        hbox_memory.addWidget(self.memory_lineedit)
        hbox_memory.addWidget(self.memory_suggest_label)
        hbox_memory.addStretch()
        self.layout.addLayout(hbox_memory)

        # Add a line break by creating a new horizontal layout
        hbox_cache = QtWidgets.QHBoxLayout()
        self.cache_label = QtWidgets.QLabel('Cache Size (-c):')
        self.cache_lineedit = QtWidgets.QLineEdit()
        self.cache_lineedit.setMaximumWidth(100)
        self.cache_lineedit.setPlaceholderText('e.g., 2G')
        self.cache_suggest_label = QtWidgets.QLabel(f'Suggested: {suggested_c}')
        hbox_cache.addWidget(self.cache_label)
        hbox_cache.addWidget(self.cache_lineedit)
        hbox_cache.addWidget(self.cache_suggest_label)
        hbox_cache.addStretch()
        self.layout.addLayout(hbox_cache)

        # Overall progress bar
        self.overall_progress_bar = QtWidgets.QProgressBar()
        self.layout.addWidget(self.overall_progress_bar)

        # Overall estimated time remaining
        self.overall_estimated_time_label = QtWidgets.QLabel('Estimated time remaining: N/A')
        self.layout.addWidget(self.overall_estimated_time_label)

        # Start, Pause, and Stop buttons
        hbox_buttons = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton('Start Render')
        self.pause_button = QtWidgets.QPushButton('Pause Render')
        self.pause_button.setEnabled(False)
        self.stop_button = QtWidgets.QPushButton('Stop Render')
        self.stop_button.setEnabled(False)
        hbox_buttons.addWidget(self.start_button)
        hbox_buttons.addWidget(self.pause_button)
        hbox_buttons.addWidget(self.stop_button)
        hbox_buttons.addStretch()
        self.layout.addLayout(hbox_buttons)

        # Scroll Area for thread progress
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_widget)
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)
        self.layout.addWidget(self.scroll_area)

        # Grouped Log Area (collapsible)
        self.collapsible_log_group = CollapsibleWidget(title='Show Errors and Frame Logs')
        self.grouped_log_text_edit = QtWidgets.QTextEdit()
        self.grouped_log_text_edit.setReadOnly(True)
        self.collapsible_log_group.add_widget(self.grouped_log_text_edit)
        self.layout.addWidget(self.collapsible_log_group)

        # Signals and slots
        self.start_button.clicked.connect(self.start_render)
        self.pause_button.clicked.connect(self.pause_render)
        self.stop_button.clicked.connect(self.stop_render)
        self.write_node_combo.currentIndexChanged.connect(self.write_node_changed)
        self.custom_frame_range_checkbox.stateChanged.connect(self.custom_frame_range_toggled)

        # Connect the batch render checkbox
        self.batch_render_checkbox.stateChanged.connect(self.batch_render_toggled)

        # Set up a timer to monitor write node changes
        self.write_node_timer = QtCore.QTimer()
        self.write_node_timer.setInterval(5000)  # Check every 5 seconds
        self.write_node_timer.timeout.connect(self.populate_write_nodes)
        self.write_node_timer.start()

        # Load saved settings
        self.load_settings()

    def populate_write_nodes(self):
        """
        Populates the write node dropdown with all Write nodes in the script.
        """
        current_selection = self.write_node_combo.currentText()
        self.write_node_combo.blockSignals(True)  # Prevent signal during update
        self.write_node_combo.clear()
        write_nodes = nuke.allNodes('Write')
        for node in write_nodes:
            self.write_node_combo.addItem(node.name())
        # Restore previous selection if possible
        index = self.write_node_combo.findText(current_selection)
        if index >= 0:
            self.write_node_combo.setCurrentIndex(index)
        self.write_node_combo.blockSignals(False)
        self.write_node_changed()  # Update write_node variable

    def write_node_changed(self):
        """
        Updates the selected write node.
        """
        self.write_node = nuke.toNode(self.write_node_combo.currentText())

    def custom_frame_range_toggled(self, state):
        """
        Enables or disables the custom frame range spin boxes based on the checkbox.
        """
        is_checked = state == QtCore.Qt.Checked
        self.start_frame_spinbox.setEnabled(is_checked)
        self.end_frame_spinbox.setEnabled(is_checked)

    def batch_render_toggled(self, state):
        """
        Enables or disables the batch size spinbox based on the checkbox.
        """
        is_checked = state == QtCore.Qt.Checked
        self.batch_size_spinbox.setEnabled(is_checked)

    def frame_exists(self, frame):
        """
        Checks if the output file for a given frame already exists.
        """
        try:
            filename = self.write_node['file'].evaluate(frame)
            filename = nuke.callbacks.filenameFilter(filename)
            return os.path.exists(filename)
        except Exception as e:
            logging.error(f"Error evaluating filename for frame {frame}: {e}")
            return False

    def start_render(self):
        """
        Initiates the rendering process.
        """
        if self.is_rendering:
            nuke.message('Render is already in progress.')
            return
        if not self.write_node_combo.currentText():
            nuke.message('Please select a Write node.')
            return

        self.write_node = nuke.toNode(self.write_node_combo.currentText())

        # Save the script before rendering
        nuke.scriptSave()

        # Get frame range
        if self.custom_frame_range_checkbox.isChecked():
            start_frame = self.start_frame_spinbox.value()
            end_frame = self.end_frame_spinbox.value()
        else:
            start_frame = int(nuke.root()['first_frame'].value())
            end_frame = int(nuke.root()['last_frame'].value())

        if start_frame > end_frame:
            nuke.message('Start frame must be less than or equal to end frame.')
            return

        num_threads = self.threads_spinbox.value()

        # Save settings
        self.settings.setValue('num_threads', num_threads)

        # Get -m and -c options
        max_ram = self.memory_lineedit.text().strip()
        cache_size = self.cache_lineedit.text().strip()

        # Get batch rendering settings
        batch_render_enabled = self.batch_render_checkbox.isChecked()
        batch_size = self.batch_size_spinbox.value()

        # Prepare frames to render
        # At the start of the render, calculate the total number of frames
        all_frames = list(range(start_frame, end_frame + 1))  # Ensure this is the full range of frames
        self.total_frames_all = len(all_frames)  # This should be the total number of frames

        # If overwrite is disabled, remove frames that have already been rendered
        if not self.overwrite_checkbox.isChecked():
            all_frames = [frame for frame in all_frames if not self.frame_exists(frame)]

        if not all_frames:
            nuke.message('All frames have already been rendered. Nothing to do.')
            return

        self.total_frames_all = len(all_frames)  # Store the total number of frames to render

        # Initialize shared data structures if batch rendering is enabled
        if batch_render_enabled:
            self.remaining_frames = all_frames.copy()  # Shared list of frames
            self.batch_size_value = batch_size
            self.remaining_frames_lock = threading.Lock()  # Lock for thread synchronization

            # Each thread will not have a predefined frame range
            frames_per_thread = [None] * num_threads  # Placeholder
        else:
            # Divide frames equally among threads
            frames_per_thread = [[] for _ in range(num_threads)]
            for idx, frame in enumerate(all_frames):
                frames_per_thread[idx % num_threads].append(frame)

        # Disable start button, enable pause and stop buttons
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.threads_spinbox.setEnabled(False)
        self.custom_frame_range_checkbox.setEnabled(False)
        self.start_frame_spinbox.setEnabled(False)
        self.end_frame_spinbox.setEnabled(False)
        self.write_node_combo.setEnabled(False)
        self.overwrite_checkbox.setEnabled(False)
        self.memory_lineedit.setEnabled(False)
        self.cache_lineedit.setEnabled(False)
        self.batch_render_checkbox.setEnabled(False)
        self.batch_size_spinbox.setEnabled(False)

        # Clear previous thread widgets
        for widget in self.thread_widgets.values():
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
        self.thread_widgets.clear()
        self.render_threads.clear()
        self.threads.clear()

        # Reset overall progress bar and estimated time
        self.overall_progress_bar.setValue(0)
        self.overall_estimated_time_label.setText('Estimated time remaining: N/A')

        # Initialize total frames rendered
        self.total_frames_rendered = 0

        # Start threads
        for idx in range(num_threads):
            thread_id = idx + 1
            frames_to_render = frames_per_thread[idx] if not batch_render_enabled else None

            render_thread = RenderThread(
                self.write_node,
                frames_to_render,
                thread_id,
                max_ram=max_ram,
                cache_size=cache_size,
                batch_render=batch_render_enabled,
                batch_size=batch_size if batch_render_enabled else None,
                remaining_frames=self.remaining_frames if batch_render_enabled else None,
                remaining_frames_lock=self.remaining_frames_lock if batch_render_enabled else None
            )

            render_thread.progress_updated.connect(self.update_progress)
            render_thread.render_finished.connect(self.render_complete)
            render_thread.render_stopped.connect(self.render_stopped)
            render_thread.log_message.connect(self.update_log)
            render_thread.batch_started.connect(self.reset_thread_progress)

            # Create UI components for each thread without the log
            thread_widget = QtWidgets.QGroupBox(f'Thread {thread_id}')
            vbox = QtWidgets.QVBoxLayout()
            progress_bar = QtWidgets.QProgressBar()
            stats_label = QtWidgets.QLabel('Time per frame: N/A\nEstimated time remaining: N/A')
            vbox.addWidget(progress_bar)
            vbox.addWidget(stats_label)
            thread_widget.setLayout(vbox)
            self.scroll_layout.addWidget(thread_widget)
            self.thread_widgets[thread_id] = thread_widget

            # Store widgets for updating
            render_thread.progress_bar = progress_bar
            render_thread.stats_label = stats_label
            self.render_threads.append(render_thread)

            # Start the thread
            thread = QtCore.QThread()
            render_thread.moveToThread(thread)
            thread.started.connect(render_thread.run)
            thread.finished.connect(thread.deleteLater)
            render_thread.thread = thread
            self.threads.append(thread)
            thread.start()

        self.is_rendering = True

    def pause_render(self):
        """
        Pauses or resumes all running render threads.
        """
        if not self.is_rendering:
            return
        if self.pause_button.text() == 'Pause Render':
            for render_thread in self.render_threads:
                render_thread.pause()
            self.pause_button.setText('Resume Render')
            logging.info('Rendering paused by user.')
        else:
            for render_thread in self.render_threads:
                render_thread.resume()
            self.pause_button.setText('Pause Render')
            logging.info('Rendering resumed by user.')

    def stop_render(self):
        """
        Stops all running render threads.
        """
        if not self.is_rendering:
            return
        for render_thread in self.render_threads:
            render_thread.stop()
            if render_thread.thread.isRunning():
                render_thread.thread.quit()
                render_thread.thread.wait()
        # Disable stop and pause buttons
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        logging.info('Rendering stopped by user.')

    def reset_thread_progress(self, thread_id, total_frames):
        """
        Resets the progress bar and statistics when a new batch starts.
        """
        render_thread = next((rt for rt in self.render_threads if rt.thread_id == thread_id), None)
        if render_thread:
            render_thread.progress_bar.setValue(0)
            render_thread.stats_label.setText('Time/frame: N/A\nETA: N/A')
            # Optionally, update the thread's group box title to reflect the new batch
            thread_widget = self.thread_widgets.get(thread_id)
            if thread_widget:
                thread_widget.setTitle(f'Thread {thread_id}: New Batch ({total_frames} frames)')

    def update_progress(self, current_frame, total_frames, time_per_frame, thread_id):
        """
        Updates the progress bars, statistics, and estimated time.
        """
        with self.progress_lock:
            render_thread = next((rt for rt in self.render_threads if rt.thread_id == thread_id), None)
            if render_thread:
                # Increment the frames rendered for the current thread
                render_thread.frames_rendered += 1  # Each frame counts only when rendered
                total_frames_thread = render_thread.total_frames

                # Update the progress bar for this specific thread
                progress = int((render_thread.frames_rendered / total_frames_thread) * 100) if total_frames_thread else 0
                render_thread.progress_bar.setValue(progress)

                # Update the time per frame and estimated time remaining for the thread
                if render_thread.frames_rendered > 0:
                    render_thread.time_per_frame = time_per_frame
                    estimated_time_remaining = max(0, time_per_frame * (total_frames_thread - render_thread.frames_rendered))
                    formatted_estimated_time = self.format_time(estimated_time_remaining)
                    render_thread.stats_label.setText(
                        f'Time per frame: {time_per_frame:.2f}s\nEstimated time remaining: {formatted_estimated_time}'
                    )

                # Now recalculate total frames rendered correctly
                self.total_frames_rendered = sum(rt.frames_rendered for rt in self.render_threads)

                # Ensure total_frames_rendered doesn't exceed total_frames_all
                if self.total_frames_rendered > self.total_frames_all:
                    self.total_frames_rendered = self.total_frames_all

                # Calculate overall progress as the ratio of total frames rendered to all frames
                overall_progress = int((self.total_frames_rendered / self.total_frames_all) * 100)
                if overall_progress > 100:  # Cap it at 100%
                    overall_progress = 100
                self.overall_progress_bar.setValue(overall_progress)

                # Calculate the overall estimated time remaining
                estimated_times = [
                    max(0, (rt.total_frames - rt.frames_rendered) * rt.time_per_frame)
                    for rt in self.render_threads if rt.time_per_frame is not None
                ]
                if estimated_times:
                    total_estimated_time_remaining = sum(estimated_times)
                    formatted_total_estimated_time = self.format_time(total_estimated_time_remaining)
                    self.overall_estimated_time_label.setText(f'Estimated time remaining: {formatted_total_estimated_time}')
                else:
                    self.overall_estimated_time_label.setText('Estimated time remaining: N/A')

    def format_time(self, seconds):
        """
        Formats time in seconds to a string in hours, minutes, and seconds.
        """
        seconds = int(seconds)
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f'{hours}h {minutes}m'
        elif seconds >= 60:
            minutes = seconds // 60
            seconds = seconds % 60
            return f'{minutes}m {seconds}s'
        else:
            return f'{seconds}s'

    def render_complete(self, total_duration, thread_id):
        """
        Handles the completion of a render thread.
        """
        render_thread = next((rt for rt in self.render_threads if rt.thread_id == thread_id), None)
        if render_thread:
            # Update the stats label for the total duration
            render_thread.stats_label.setText(
                render_thread.stats_label.text() + f'\nTotal duration: {total_duration:.2f}s'
            )
            # Append the "Render complete" message to the grouped log
            self.grouped_log_text_edit.append(f"Thread {thread_id}: Render complete.")

            # Clean up the thread
            render_thread.thread.quit()
            render_thread.thread.wait()
            logging.info(f'Thread {thread_id} render complete.')

        # Check if all threads are done
        if all(not rt.is_running for rt in self.render_threads):
            self.finish_rendering()

    def render_stopped(self, thread_id):
        """
        Handles the stopping of a render thread.
        """
        render_thread = next((rt for rt in self.render_threads if rt.thread_id == thread_id), None)
        if render_thread:
            # No need to append to individual log, directly update the grouped log
            self.grouped_log_text_edit.append(f"Thread {thread_id}: Render stopped.")
            # Stop and clean up the thread
            render_thread.thread.quit()
            render_thread.thread.wait()
            logging.warning(f'Thread {thread_id} render stopped.')
        
        # Check if all threads are done
        if all(not rt.is_running for rt in self.render_threads):
            self.finish_rendering()

    def finish_rendering(self):
        """
        Resets the UI elements after rendering is complete or stopped.
        """
        self.is_rendering = False
        # Enable start button, disable pause and stop buttons
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText('Pause Render')
        self.threads_spinbox.setEnabled(True)
        self.custom_frame_range_checkbox.setEnabled(True)
        self.start_frame_spinbox.setEnabled(self.custom_frame_range_checkbox.isChecked())
        self.end_frame_spinbox.setEnabled(self.custom_frame_range_checkbox.isChecked())
        self.write_node_combo.setEnabled(True)
        self.overwrite_checkbox.setEnabled(True)
        self.memory_lineedit.setEnabled(True)
        self.cache_lineedit.setEnabled(True)
        self.batch_render_checkbox.setEnabled(True)
        self.batch_size_spinbox.setEnabled(self.batch_render_checkbox.isChecked())
        self.write_node_label.setText('Write Node:')
        logging.info('All rendering complete.')

    def update_log(self, message, thread_id):
        """
        Updates the grouped log text edit with only error messages and frame rendering progress.
        """
        # Check if the log message is an error or contains frame rendering info
        if 'Error' in message or 'ERROR' in message or 'Writing' in message:
            self.grouped_log_text_edit.append(f"Thread {thread_id}: {message}")

    def load_settings(self):
        """
        Loads saved settings.
        """
        num_threads = self.settings.value('num_threads', defaultValue=self.threads_spinbox.value(), type=int)
        self.threads_spinbox.setValue(num_threads)

    def closeEvent(self, event):
        """
        Handles the closing event to save settings.
        """
        # Save settings
        self.settings.setValue('num_threads', self.threads_spinbox.value())
        event.accept()

class RenderThread(QtCore.QObject):
    """
    A render thread that runs a Nuke command-line render process.
    """
    progress_updated = QtCore.Signal(int, int, float, int)  # current_frame, total_frames, time_per_frame, thread_id
    render_finished = QtCore.Signal(float, int)  # total_duration, thread_id
    render_stopped = QtCore.Signal(int)  # thread_id
    log_message = QtCore.Signal(str, int)  # message, thread_id
    batch_started = QtCore.Signal(int, int)  # thread_id, total_frames

    def __init__(self, write_node, frames_to_render, thread_id, max_ram=None, cache_size=None,
                 batch_render=False, batch_size=None, remaining_frames=None, remaining_frames_lock=None):
        """
        Initializes the RenderThread with the specified parameters.
        """
        super(RenderThread, self).__init__()
        self.write_node = write_node
        self.frames_to_render = frames_to_render  # Now a list of frames
        self.process = None
        self.is_running = False
        self.is_paused = False
        self.thread_id = thread_id
        self.progress_bar = None
        self.stats_label = None
        self.log_text_edit = None
        self.max_ram = max_ram  # Store -m option
        self.cache_size = cache_size  # Store -c option
        self.batch_render = batch_render  # Batch rendering flag
        self.batch_size = batch_size
        self.remaining_frames = remaining_frames
        self.remaining_frames_lock = remaining_frames_lock
        self.time_per_frame = None
        self.frames_rendered = 0
        self.total_frames_rendered = 0  # Total frames rendered by this thread
        if self.batch_render:
            self.total_frames = 0  # Will be updated dynamically
        else:
            self.total_frames = len(self.frames_to_render)

    def log(self, level, message):
        """
        Logs a message with the specified severity level.
        """
        logging.log(level, message)

    def stop(self):
        """
        Stops the render process.
        """
        if self.process and self.is_running:
            if os.name == 'nt':
                self.process.terminate()
            else:
                self.process.terminate()
            self.is_running = False
            self.log(logging.INFO, "Render process terminated by user.")

    def pause(self):
        """
        Pauses the render process.
        """
        if self.process and self.is_running and not self.is_paused:
            if os.name == 'nt':
                # Windows does not support SIGSTOP, so we suspend the process
                import psutil
                process = psutil.Process(self.process.pid)
                process.suspend()
            else:
                # Unix-like systems can use SIGSTOP
                self.process.send_signal(signal.SIGSTOP)
            self.is_paused = True
            self.log(logging.INFO, "Render process paused by user.")

    def resume(self):
        """
        Resumes the render process.
        """
        if self.process and self.is_running and self.is_paused:
            if os.name == 'nt':
                import psutil
                process = psutil.Process(self.process.pid)
                process.resume()
            else:
                self.process.send_signal(signal.SIGCONT)
            self.is_paused = False
            self.log(logging.INFO, "Render process resumed by user.")

    @QtCore.Slot()
    def run(self):
        """
        Executes the render process in a separate thread.
        """
        import threading
        import queue

        self.is_running = True
        self.start_time = time.time()  # Start time before processing batches

        nuke_executable = nuke.EXE_PATH
        script_path = nuke.root().name()
        if script_path == '':
            nuke.executeInMainThread(nuke.message, args=("Please save your script before rendering.",))
            self.log(logging.ERROR, "Script not saved.")
            self.is_running = False
            self.render_stopped.emit(self.thread_id)
            return

        write_node_name = self.write_node.name()

        if not self.batch_render:
            # Non-batch rendering logic
            if not self.frames_to_render:
                self.log_message.emit("No frames to render. Skipping.", self.thread_id)
                self.is_running = False
                self.render_finished.emit(0.0, self.thread_id)
                return
            self.total_frames = len(self.frames_to_render)
        else:
            # Batch rendering
            self.frames_to_render = []

        # Initialize counters
        self.frames_rendered = 0
        self.total_frames_rendered = 0

        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue

            if self.batch_render:
                # Get next batch of frames
                with self.remaining_frames_lock:
                    if not self.remaining_frames:
                        break  # No more frames to render
                    batch_frames = self.remaining_frames[:self.batch_size]
                    del self.remaining_frames[:self.batch_size]
                self.frames_to_render = batch_frames
                self.total_frames = len(self.frames_to_render)
                self.frames_rendered = 0  # Reset for new batch

                if not self.frames_to_render:
                    break

                # Emit signal to reset progress bar
                self.batch_started.emit(self.thread_id, self.total_frames)
            else:
                if not self.frames_to_render:
                    break  # No frames to render

            # Start batch timer
            self.batch_start_time = time.time()

            # Build command for the current batch
            frame_ranges = self.frames_to_frame_ranges(self.frames_to_render)
            cmd = [
                nuke_executable,
                '-V',            # Suppress Nuke version banner
                '-x',            # Render mode
            ]

            # Add -m and -c options if specified
            if self.max_ram:
                cmd.extend(['-m', self.max_ram])
            if self.cache_size:
                cmd.extend(['-c', self.cache_size])

            # Add frame ranges
            for frame_range in frame_ranges:
                cmd.extend(['-F', frame_range])

            cmd.extend([
                '-X',
                write_node_name,
                script_path
            ])

            self.log(logging.INFO, f"Command: {' '.join(cmd)}")
            self.log_message.emit(f"Executing command: {' '.join(cmd)}", self.thread_id)

            # Start process
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
            except Exception as e:
                error_msg = f"Failed to start render process:\n{e}"
                nuke.executeInMainThread(nuke.message, args=(error_msg,))
                self.log(logging.ERROR, error_msg)
                self.is_running = False
                self.render_stopped.emit(self.thread_id)
                return

            # Start threads to read stdout and stderr
            stdout_queue = queue.Queue()
            stderr_queue = queue.Queue()

            stdout_thread = threading.Thread(target=self.read_stream, args=(self.process.stdout, stdout_queue))
            stderr_thread = threading.Thread(target=self.read_stream, args=(self.process.stderr, stderr_queue))

            stdout_thread.start()
            stderr_thread.start()

            while self.is_running:
                if self.is_paused:
                    time.sleep(0.1)
                    continue

                # Process stdout
                try:
                    line = stdout_queue.get_nowait()
                except queue.Empty:
                    line = None

                if line:
                    self.log_message.emit(line.strip(), self.thread_id)
                    if 'Writing' in line:
                        # Parse current frame
                        match = re.search(r'Writing.*?(\d+)', line)
                        if match:
                            current_frame = int(match.group(1))
                            elapsed_time = time.time() - self.batch_start_time
                            self.frames_rendered += 1
                            self.total_frames_rendered += 1
                            if self.frames_rendered > 0:
                                time_per_frame = elapsed_time / self.frames_rendered
                                self.progress_updated.emit(current_frame, self.total_frames, time_per_frame, self.thread_id)
                else:
                    # No new stdout line
                    pass

                # Process stderr
                try:
                    err_line = stderr_queue.get_nowait()
                except queue.Empty:
                    err_line = None

                if err_line:
                    self.log_message.emit(err_line.strip(), self.thread_id)
                    if 'Error' in err_line or 'ERROR' in err_line:
                        self.log(logging.ERROR, err_line.strip())
                else:
                    # No new stderr line
                    pass

                # Check if process has finished
                if self.process.poll() is not None:
                    break

                # Sleep briefly to prevent busy-waiting
                time.sleep(0.1)

            stdout_thread.join()
            stderr_thread.join()
            self.process.wait()

            if self.is_running:
                if self.process.returncode != 0:
                    # Render process failed unexpectedly
                    error_msg = f"Render process failed with return code {self.process.returncode}."
                    nuke.executeInMainThread(nuke.message, args=(error_msg,))
                    self.log(logging.ERROR, error_msg)
                    self.render_stopped.emit(self.thread_id)
                    self.is_running = False  # Exit the loop
                    return
                else:
                    # Batch completed successfully
                    self.log(logging.INFO, f"Batch completed.")
            else:
                # Render was stopped by the user
                self.log(logging.INFO, f"Render process was terminated by the user. Return code: {self.process.returncode}")
                self.render_stopped.emit(self.thread_id)
                self.is_running = False  # Exit the loop
                return

            if not self.batch_render:
                break  # Exit loop if not batch rendering

        # After all batches have been processed
        if self.is_running:
            total_duration = time.time() - self.start_time
            self.render_finished.emit(total_duration, self.thread_id)
            self.log(logging.INFO, f"Thread {self.thread_id} completed all batches in {total_duration:.2f}s.")
            self.is_running = False

    def read_stream(self, stream, queue):
        """
        Reads lines from a stream and puts them into a queue.
        """
        while True:
            line = stream.readline()
            if not line:
                break
            queue.put(line)
        stream.close()

    def frames_to_frame_ranges(self, frames):
        """
        Converts a list of frames into a list of contiguous frame ranges.
        For example, [1,2,3,5,6,7,9] becomes ['1-3', '5-7', '9']
        """
        if not frames:
            return []
        frames = sorted(set(frames))
        ranges = []
        start = prev = frames[0]
        for frame in frames[1:]:
            if frame == prev + 1:
                prev = frame
            else:
                if start == prev:
                    ranges.append(f"{start}")
                else:
                    ranges.append(f"{start}-{prev}")
                start = prev = frame
        # Add the last range
        if start == prev:
            ranges.append(f"{start}")
        else:
            ranges.append(f"{start}-{prev}")
        return ranges

class CollapsibleWidget(QtWidgets.QWidget):
    """
    A custom widget that can be collapsed or expanded.
    """
    def __init__(self, title='', parent=None):
        super(CollapsibleWidget, self).__init__(parent)
        self.toggle_button = QtWidgets.QToolButton(text=title, checkable=True, checked=False)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.setChecked(False)

        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_widget)
        self.content_widget.setVisible(False)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.toggle_button.toggled.connect(self.on_toggled)

    def on_toggled(self, checked):
        self.content_widget.setVisible(checked)
        if checked:
            self.toggle_button.setArrowType(QtCore.Qt.DownArrow)
        else:
            self.toggle_button.setArrowType(QtCore.Qt.RightArrow)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

# Register the panel to make it dockable
def render_progress_panel():
    return RenderProgressPanel()

nukescripts.registerWidgetAsPanel('render_progress_panel.RenderProgressPanel', 'Render Progress Panel', 'uk.co.thefoundry.RenderProgressPanel')

# Add menu item to open the panel
nuke.menu('Pane').addCommand('Render Progress Panel', lambda: nukescripts.panels.restorePanel('uk.co.thefoundry.RenderProgressPanel'))
