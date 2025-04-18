import nuke
import nukescripts
from PySide6 import QtWidgets, QtCore
import os
import re
import glob
import threading

# Global cache to avoid redundant scans
FRAME_RANGE_CACHE = {}

class FileScanner(QtCore.QObject):
    progress_updated = QtCore.Signal(int, str)
    scan_complete = QtCore.Signal(int, int)
    
    def __init__(self, path):
        super(FileScanner, self).__init__()
        self.path = path
        self.running = False
        # Use global cache
        self._cache = FRAME_RANGE_CACHE
        
    def scan(self):
        """Fast scan directory to determine frame range of sequence."""
        self.running = True
        directory = os.path.dirname(self.path)
        basename = os.path.basename(self.path)
        
        # Check cache first
        cache_key = f"{directory}:{basename}"
        if cache_key in self._cache:
            first, last = self._cache[cache_key]
            self.scan_complete.emit(first, last)
            self.running = False
            return

        # Check if this is a sequence
        sequence_pattern = re.search(r'(%\d*d|#+)', basename)
        if not sequence_pattern:
            self.scan_complete.emit(1, 1)
            self.running = False
            return

        self.progress_updated.emit(0, "Analyzing file pattern...")
        
        # Skip inference and go directly to full scan methods
        try:
            # Fast access scan - only check first and last files by sorted order
            first, last = self._fast_scan(directory, basename)
            if first is not None and last is not None:
                self._cache[cache_key] = (first, last)
                self.scan_complete.emit(first, last)
                self.running = False
                return
        except Exception as e:
            self.progress_updated.emit(40, f"Fast scan failed, trying full scan: {str(e)}")
            
        # Final fallback - use traditional scan but with optimizations
        try:
            first, last = self._traditional_scan(directory, basename)
            if first is not None and last is not None:
                self._cache[cache_key] = (first, last)
                self.scan_complete.emit(first, last)
                self.running = False
                return
        except Exception as e:
            self.progress_updated.emit(90, f"Full scan failed: {str(e)}")
            
        # Default if all methods fail
        self.scan_complete.emit(1, 1)
        self.running = False
    
    def _infer_frame_range(self, directory, basename):
        """Try to infer frame range directly from context without scanning files."""
        # Check common frame patterns for VFX sequences (1001-1100, etc.)
        common_ranges = [(1, 100), (1001, 1100), (0, 100), (101, 200)]
        pattern_matches = self._get_frame_pattern(basename)
        if not pattern_matches:
            return None, None
            
        start_pattern, end_pattern, frame_pattern = pattern_matches
        
        self.progress_updated.emit(10, "Checking common frame ranges...")
        
        # Check if any common ranges exist without scanning the whole directory
        for first, last in common_ranges:
            # Check if first frame exists
            first_path = self._format_path_with_frame(basename, directory, first)
            if os.path.exists(first_path):
                # Check if last frame exists
                last_path = self._format_path_with_frame(basename, directory, last)
                if os.path.exists(last_path):
                    return first, last
                    
        return None, None
    
    def _fast_scan(self, directory, basename):
        """Fast scan using os.scandir and sorting optimization to find true range."""
        pattern_matches = self._get_frame_pattern(basename)
        if not pattern_matches:
            return None, None
            
        start_pattern, end_pattern, frame_pattern = pattern_matches
        
        # Create partial pattern to match with scandir
        # This is much faster than glob on network drives
        self.progress_updated.emit(20, "Fast scanning directory...")
        
        # Only check if directory exists and is accessible
        if not os.path.exists(directory):
            return None, None
            
        # Quick scan to check frames
        try:
            # Only get filenames that start with our prefix
            matching_files = []
            file_count = 0
            self.progress_updated.emit(25, "Listing files in directory...")
            
            for entry in os.scandir(directory):
                if not self.running:
                    return None, None
                
                if file_count % 1000 == 0:
                    self.progress_updated.emit(25 + min(25, file_count // 1000), 
                                              f"Examining files: {file_count} found...")
                
                if entry.is_file() and entry.name.startswith(start_pattern):
                    matching_files.append(entry.name)
                    file_count += 1
                    
            # Exit early if no files found
            if not matching_files:
                return None, None
                
            # Sort filenames (much faster than globbing everything)
            self.progress_updated.emit(50, f"Sorting {len(matching_files)} files...")
            matching_files.sort()
            
            # Process all matching files to extract frame numbers
            frames = []
            min_frame = 99999999
            max_frame = -1
            
            # Sample approach to save time with huge sequences
            if len(matching_files) > 1000:
                self.progress_updated.emit(60, "Large sequence detected, sampling frames...")
                # For very large sequences, sample files from start, middle, and end
                sample_size = 100
                step = max(1, len(matching_files) // sample_size)
                sample_indices = list(range(0, len(matching_files), step))
                # Always include first and last files
                if len(matching_files)-1 not in sample_indices:
                    sample_indices.append(len(matching_files)-1)
                if 0 not in sample_indices:
                    sample_indices.insert(0, 0)
                
                # Process samples
                for i, idx in enumerate(sample_indices):
                    if not self.running:
                        return None, None
                    
                    self.progress_updated.emit(60 + (i * 20) // len(sample_indices), 
                                              f"Processing file {i+1} of {len(sample_indices)}...")
                    
                    filename = matching_files[idx]
                    match = frame_pattern.match(filename)
                    if match:
                        try:
                            frame = int(match.group(1))
                            min_frame = min(min_frame, frame)
                            max_frame = max(max_frame, frame)
                        except:
                            pass
                            
                # Ensure we check boundary frames directly for accuracy
                self.progress_updated.emit(80, "Verifying frame boundaries...")
                
                # Verify first frame
                first_file = matching_files[0]
                match = frame_pattern.match(first_file)
                if match:
                    try:
                        frame = int(match.group(1))
                        min_frame = min(min_frame, frame)
                    except:
                        pass
                
                # Verify last frame
                last_file = matching_files[-1]
                match = frame_pattern.match(last_file)
                if match:
                    try:
                        frame = int(match.group(1))
                        max_frame = max(max_frame, frame)
                    except:
                        pass
                
                if min_frame < 99999999 and max_frame > -1:
                    self.progress_updated.emit(90, f"Found range: {min_frame}-{max_frame}")
                    return min_frame, max_frame
            else:
                # For smaller sequences, process all files
                self.progress_updated.emit(60, "Processing all frames...")
                
                for i, filename in enumerate(matching_files):
                    if i % 100 == 0:
                        progress = 60 + (i * 30) // len(matching_files)
                        self.progress_updated.emit(progress, f"Processing file {i+1} of {len(matching_files)}...")
                    
                    match = frame_pattern.match(filename)
                    if match:
                        try:
                            frame = int(match.group(1))
                            frames.append(frame)
                        except:
                            pass
                
                if frames:
                    min_frame = min(frames)
                    max_frame = max(frames)
                    self.progress_updated.emit(90, f"Found range: {min_frame}-{max_frame}")
                    return min_frame, max_frame
                
        except Exception as e:
            self.progress_updated.emit(85, f"Error in fast scan: {str(e)}")
            
        return None, None
        
    def _traditional_scan(self, directory, basename):
        """Traditional scan with optimizations for speed and handling large frame ranges."""
        self.progress_updated.emit(50, "Performing detailed scan...")
        
        pattern_matches = self._get_frame_pattern(basename)
        if not pattern_matches:
            return None, None
            
        start_pattern, end_pattern, frame_pattern = pattern_matches
        
        frames = []
        try:
            # Use a set for faster lookups
            frame_set = set()
            
            # Algorithm: check files with a binary search approach
            # Start with common frames, then extend outward
            common_frames = [1, 1001, 0, 101, 10001, 100001]  # Add higher frame numbers
            
            # Check common frames first
            self.progress_updated.emit(55, "Checking common frame numbers...")
            for frame in common_frames:
                test_path = self._format_path_with_frame(basename, directory, frame)
                if os.path.exists(test_path):
                    frame_set.add(frame)
            
            if frame_set:
                # We found at least one frame, now check boundaries
                min_frame = min(frame_set)
                max_frame = max(frame_set)
                
                # Check lower bounds with exponential backoff
                self.progress_updated.emit(60, "Searching for first frame...")
                step = 1
                while True:
                    if not self.running:
                        return None, None
                        
                    test_frame = min_frame - step
                    if test_frame < 0:
                        break
                        
                    test_path = self._format_path_with_frame(basename, directory, test_frame)
                    if os.path.exists(test_path):
                        frame_set.add(test_frame)
                        min_frame = test_frame
                    else:
                        # Try one more step, then break if not found
                        last_chance = test_frame - 1
                        if last_chance >= 0:
                            test_path = self._format_path_with_frame(basename, directory, last_chance)
                            if os.path.exists(test_path):
                                frame_set.add(last_chance)
                                min_frame = last_chance
                        break
                    
                    step *= 2
                
                # Check upper bounds with exponential increase up to 150000
                self.progress_updated.emit(70, "Searching for last frame...")
                step = 1
                max_possible_frame = 150000  # Set max frame limit
                
                while max_frame < max_possible_frame:
                    if not self.running:
                        return None, None
                        
                    test_frame = max_frame + step
                    if test_frame > max_possible_frame:
                        break
                        
                    test_path = self._format_path_with_frame(basename, directory, test_frame)
                    if os.path.exists(test_path):
                        frame_set.add(test_frame)
                        max_frame = test_frame
                        self.progress_updated.emit(70, f"Found frame {max_frame}...")
                    else:
                        # Binary search to find the exact last frame
                        lower = max_frame + 1
                        upper = test_frame - 1
                        
                        # Only do binary search if gap is significant
                        if upper - lower > 10:
                            self.progress_updated.emit(80, f"Narrowing down last frame between {lower}-{upper}...")
                            while lower <= upper:
                                if not self.running:
                                    return None, None
                                    
                                mid = (lower + upper) // 2
                                test_path = self._format_path_with_frame(basename, directory, mid)
                                if os.path.exists(test_path):
                                    frame_set.add(mid)
                                    max_frame = max(max_frame, mid)
                                    lower = mid + 1
                                else:
                                    upper = mid - 1
                        
                        # Linear search for the last few frames
                        self.progress_updated.emit(85, "Final check for last frame...")
                        for frame in range(max_frame + 1, max_frame + 20):
                            test_path = self._format_path_with_frame(basename, directory, frame)
                            if os.path.exists(test_path):
                                frame_set.add(frame)
                                max_frame = frame
                            else:
                                break
                                
                        break
                    
                    # Use exponential step to find upper bound faster
                    step *= 2
                
                frames = list(frame_set)
                
            if frames:
                self.progress_updated.emit(95, f"Found range: {min(frames)}-{max(frames)}")
                return min(frames), max(frames)
                
        except Exception as e:
            self.progress_updated.emit(95, f"Error in traditional scan: {str(e)}")
        
        return None, None
    
    def _get_frame_pattern(self, basename):
        """Parse filename to get frame pattern parts."""
        try:
            if '%' in basename and 'd' in basename:
                # %04d notation
                pattern_parts = re.split(r'(%\d*d)', basename)
                if len(pattern_parts) >= 3:
                    start_pattern = pattern_parts[0]
                    end_pattern = ''.join(pattern_parts[2:])
                    # Escape for regex use
                    regex_pattern = f"^{re.escape(start_pattern)}(\\d+){re.escape(end_pattern)}$"
                    frame_pattern = re.compile(regex_pattern)
                    return start_pattern, end_pattern, frame_pattern
            else:
                # #### notation
                hash_match = re.search(r'(#+)', basename)
                if hash_match:
                    hash_str = hash_match.group(1)
                    pattern_parts = basename.split(hash_str, 1)
                    if len(pattern_parts) == 2:
                        start_pattern = pattern_parts[0]
                        end_pattern = pattern_parts[1]
                        # Escape for regex use
                        regex_pattern = f"^{re.escape(start_pattern)}(\\d+){re.escape(end_pattern)}$"
                        frame_pattern = re.compile(regex_pattern)
                        return start_pattern, end_pattern, frame_pattern
                        
        except Exception as e:
            pass
            
        return None
        
    def _format_path_with_frame(self, basename, directory, frame):
        """Format path with frame number."""
        if '%' in basename and 'd' in basename:
            try:
                frame_path = basename % frame
                return os.path.join(directory, frame_path)
            except:
                pass
        else:
            # #### format
            hash_match = re.search(r'(#+)', basename)
            if hash_match:
                hash_str = hash_match.group(1)
                hash_len = len(hash_str)
                frame_str = str(frame).zfill(hash_len)
                frame_path = basename.replace(hash_str, frame_str)
                return os.path.join(directory, frame_path)
                
        # If no formatting possible, just return as is
        return os.path.join(directory, basename)
    
    def stop(self):
        self.running = False


class FileProxySwitcherPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(FileProxySwitcherPanel, self).__init__(parent)
        
        # Shared scanner cache
        self.scanner_cache = {}
        
        # Create layout
        self.main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # Operation selection
        operation_group = QtWidgets.QGroupBox("Operation")
        operation_layout = QtWidgets.QVBoxLayout()
        operation_group.setLayout(operation_layout)
        
        self.file_to_proxy_radio = QtWidgets.QRadioButton("Copy File to Proxy")
        self.proxy_to_file_radio = QtWidgets.QRadioButton("Copy Proxy to File")
        self.swap_file_proxy_radio = QtWidgets.QRadioButton("Swap File and Proxy")
        self.only_update_range_radio = QtWidgets.QRadioButton("Only Update Frame Range")
        
        self.file_to_proxy_radio.setChecked(True)
        
        operation_layout.addWidget(self.file_to_proxy_radio)
        operation_layout.addWidget(self.proxy_to_file_radio)
        operation_layout.addWidget(self.swap_file_proxy_radio)
        operation_layout.addWidget(self.only_update_range_radio)
        
        self.main_layout.addWidget(operation_group)
        
        # Frame Range Source selection
        range_group = QtWidgets.QGroupBox("Frame Range Source")
        range_layout = QtWidgets.QVBoxLayout()
        range_group.setLayout(range_layout)
        
        self.use_file_range_radio = QtWidgets.QRadioButton("Use Range from File")
        self.use_proxy_range_radio = QtWidgets.QRadioButton("Use Range from Proxy")
        self.keep_original_range_radio = QtWidgets.QRadioButton("Keep Original Range")
        
        self.use_file_range_radio.setChecked(True)
        
        range_layout.addWidget(self.use_file_range_radio)
        range_layout.addWidget(self.use_proxy_range_radio)
        range_layout.addWidget(self.keep_original_range_radio)
        
        self.main_layout.addWidget(range_group)
        
        # Progress section
        progress_group = QtWidgets.QGroupBox("Progress")
        progress_layout = QtWidgets.QVBoxLayout()
        progress_group.setLayout(progress_layout)
        
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        self.status_label = QtWidgets.QLabel("Ready")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        self.main_layout.addWidget(progress_group)
        
        # Execute button
        self.button_layout = QtWidgets.QHBoxLayout()
        
        self.execute_button = QtWidgets.QPushButton("Execute")
        self.execute_button.clicked.connect(self.execute_operation)
        
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.cancel_button.setEnabled(False)
        
        self.button_layout.addWidget(self.execute_button)
        self.button_layout.addWidget(self.cancel_button)
        
        self.main_layout.addLayout(self.button_layout)
        
        # Add stretch to keep UI compact
        self.main_layout.addStretch()
        
        # Initialize scanner and thread
        self.scanner = None
        self.scanner_thread = None
        self.current_operation = None
        self.current_read_nodes = []
        self.current_node_index = 0
        
        # Set fixed width for better appearance in dockable panel
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)
    
    def reset_progress(self):
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
    
    def execute_operation(self):
        """Execute the selected operation on selected read nodes."""
        # Get selected read nodes
        self.current_read_nodes = nuke.selectedNodes('Read')
        
        if not self.current_read_nodes:
            nuke.message("Please select one or more Read nodes")
            return
        
        # Begin undo command
        nuke.Undo.begin("File/Proxy Switcher")
        
        # Determine operation
        if self.file_to_proxy_radio.isChecked():
            self.current_operation = "file_to_proxy"
        elif self.proxy_to_file_radio.isChecked():
            self.current_operation = "proxy_to_file"
        elif self.swap_file_proxy_radio.isChecked():
            self.current_operation = "swap_file_proxy"
        elif self.only_update_range_radio.isChecked():
            self.current_operation = "update_range"
        
        # Execute operation
        try:
            # First phase - copy operations (fast)
            if self.current_operation == "file_to_proxy":
                for i, read_node in enumerate(self.current_read_nodes):
                    progress = int((i / len(self.current_read_nodes)) * 100)
                    self.progress_bar.setValue(progress)
                    self.status_label.setText(f"Copying file to proxy: node {i+1} of {len(self.current_read_nodes)}")
                    QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
                    self.copy_file_to_proxy(read_node)
            
            elif self.current_operation == "proxy_to_file":
                for i, read_node in enumerate(self.current_read_nodes):
                    progress = int((i / len(self.current_read_nodes)) * 100)
                    self.progress_bar.setValue(progress)
                    self.status_label.setText(f"Copying proxy to file: node {i+1} of {len(self.current_read_nodes)}")
                    QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
                    self.copy_proxy_to_file(read_node)
                    
            elif self.current_operation == "swap_file_proxy":
                for i, read_node in enumerate(self.current_read_nodes):
                    progress = int((i / len(self.current_read_nodes)) * 100)
                    self.progress_bar.setValue(progress)
                    self.status_label.setText(f"Swapping file and proxy: node {i+1} of {len(self.current_read_nodes)}")
                    QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
                    self.swap_file_and_proxy(read_node)
            
            # Second phase - handle frame range updates (can be slow)
            if (not self.keep_original_range_radio.isChecked() or 
                self.current_operation == "update_range"):
                # Start with first node
                self.current_node_index = 0
                self.process_next_node_range()
            else:
                # No range updates needed
                self.finish_operation()
                
        except Exception as e:
            nuke.Undo.end()
            nuke.message(f"Error: {str(e)}")
            self.reset_progress()
            self.execute_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
    
    def swap_file_and_proxy(self, read_node):
        """Swap file and proxy paths."""
        # Get both paths
        file_path = read_node['file'].value()
        proxy_path = read_node['proxy'].value()
        
        # Check if both are set
        if not file_path or not proxy_path:
            return  # Skip this node but continue with others
        
        # Store the original file path script format
        file_script = read_node['file'].toScript()
        proxy_script = read_node['proxy'].toScript()
        
        # Swap the paths using the exact script format
        read_node['file'].fromScript(proxy_script)
        read_node['proxy'].fromScript(file_script)
    
    def process_next_node_range(self):
        """Process frame range for the current node and move to next."""
        # Apply a small pause to prevent UI freezing
        QtCore.QTimer.singleShot(1, self._continue_processing)
        
    def _continue_processing(self):
        """Continue processing after a brief pause for UI updates."""
        if self.current_node_index >= len(self.current_read_nodes):
            # All nodes processed
            self.finish_operation()
            return
        
        # Get current node
        read_node = self.current_read_nodes[self.current_node_index]
        node_name = read_node.name()
        
        # Update progress
        node_progress = int((self.current_node_index / len(self.current_read_nodes)) * 100)
        self.progress_bar.setValue(node_progress)
        
        # Choose which range to update
        if self.use_file_range_radio.isChecked():
            file_path = read_node['file'].value()
            if not file_path:
                # Skip to next node
                self.current_node_index += 1
                self.process_next_node_range()
                return
                
            self.status_label.setText(f"Scanning file range for {node_name} ({self.current_node_index+1}/{len(self.current_read_nodes)})")
            self.execute_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # Create scanner for this file
            self.scanner = FileScanner(file_path)
            self.scanner.progress_updated.connect(self.update_scan_progress)
            self.scanner.scan_complete.connect(self.file_range_complete)
            
            # Start scanner in a thread
            self.scanner_thread = threading.Thread(target=self.scanner.scan)
            self.scanner_thread.daemon = True
            self.scanner_thread.start()
            
        elif self.use_proxy_range_radio.isChecked():
            proxy_path = read_node['proxy'].value()
            if not proxy_path:
                # Skip to next node
                self.current_node_index += 1
                self.process_next_node_range()
                return
                
            self.status_label.setText(f"Scanning proxy range for {node_name} ({self.current_node_index+1}/{len(self.current_read_nodes)})")
            self.execute_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # Create scanner for this file
            self.scanner = FileScanner(proxy_path)
            self.scanner.progress_updated.connect(self.update_scan_progress)
            self.scanner.scan_complete.connect(self.proxy_range_complete)
            
            # Start scanner in a thread
            self.scanner_thread = threading.Thread(target=self.scanner.scan)
            self.scanner_thread.daemon = True
            self.scanner_thread.start()
        else:
            # Skip to next node
            self.current_node_index += 1
            self.process_next_node_range()
    
    def update_scan_progress(self, progress, status):
        """Update progress bar and status for current scan."""
        # Calculate progress as a combination of node progress and scan progress
        node_weight = self.current_node_index / len(self.current_read_nodes)
        scan_weight = 1.0 / len(self.current_read_nodes)
        total_progress = int((node_weight + (progress/100.0) * scan_weight) * 100)
        
        self.progress_bar.setValue(total_progress)
        self.status_label.setText(status)
        
        # Process events to keep UI responsive, but don't process too many
        # This technique prevents UI freezing while avoiding excessive event processing
        QtWidgets.QApplication.instance().processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
    
    def file_range_complete(self, first, last):
        if self.current_node_index < len(self.current_read_nodes):
            read_node = self.current_read_nodes[self.current_node_index]
            
            # Set the frame range on the node
            read_node['first'].setValue(first)
            read_node['last'].setValue(last)
            read_node['origfirst'].setValue(first)
            read_node['origlast'].setValue(last)
            
            # Update progress status
            self.status_label.setText(f"Set range {first}-{last} on {read_node.name()}")
            
            # Move to next node
            self.current_node_index += 1
            self.process_next_node_range()
    
    def proxy_range_complete(self, first, last):
        if self.current_node_index < len(self.current_read_nodes):
            read_node = self.current_read_nodes[self.current_node_index]
            
            # Set the frame range on the node
            read_node['first'].setValue(first)
            read_node['last'].setValue(last)
            read_node['origfirst'].setValue(first)
            read_node['origlast'].setValue(last)
            
            # Update progress status
            self.status_label.setText(f"Set range {first}-{last} on {read_node.name()}")
            
            # Move to next node
            self.current_node_index += 1
            self.process_next_node_range()
    
    def cancel_operation(self):
        if self.scanner:
            self.scanner.stop()
        
        # Clean up
        nuke.Undo.end()
        self.reset_progress()
        self.execute_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    def finish_operation(self):
        # End undo command
        nuke.Undo.end()
        
        # Update UI
        self.progress_bar.setValue(100)
        self.status_label.setText("Operation complete")
        self.execute_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    def copy_file_to_proxy(self, read_node):
        # Get file path
        file_path = read_node['file'].value()
        
        if not file_path:
            return  # Skip this node but continue with others
        
        # Copy to proxy preserving exact path formatting
        read_node['proxy'].fromScript(read_node['file'].toScript())
    
    def copy_proxy_to_file(self, read_node):
        # Get proxy path
        proxy_path = read_node['proxy'].value()
        
        # Check if proxy is set
        if not proxy_path:
            return  # Skip this node but continue with others
        
        # Copy to file preserving exact path formatting
        read_node['file'].fromScript(read_node['proxy'].toScript())


def show_panel():
    """Show panel as a dialog."""
    panel = FileProxySwitcherPanel()
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("File/Proxy Switcher")
    layout = QtWidgets.QVBoxLayout()
    layout.addWidget(panel)
    dialog.setLayout(layout)
    dialog.resize(300, 400)
    dialog.exec_()

# For dockable panel support
def create_panel():
    """Create panel for dockable UI."""
    return FileProxySwitcherPanel()

# Register panel with Nuke
if hasattr(nuke, 'GUI') and nuke.GUI:
    try:
        nukescripts.registerWidgetAsPanel(
            'proxy2file.create_panel',
            'File/Proxy Switcher',
            'uk.co.thefoundry.FileProxySwitcher',
            create=True
        )
    except:
        # In case panel was already registered
        pass

# If loaded directly, show the panel
if __name__ == "__main__":
    show_panel()