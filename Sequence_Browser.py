import os
import re
import subprocess
import nuke
import nukescripts
from PySide6 import QtWidgets, QtCore, QtGui

class DraggableListWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super(DraggableListWidget, self).__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def startDrag(self, supportedActions):
        drag = QtGui.QDrag(self)
        mimedata = QtCore.QMimeData()
        selected_items = self.selectedItems()
        urls = []
        for selected_item in selected_items:
            data = selected_item.data(QtCore.Qt.UserRole)
            item_type = selected_item.data(QtCore.Qt.UserRole + 1)
            if item_type == 'sequence':
                frames = sorted(data['frames'])
                num_digits = len(frames[0])
                # Use '#' characters in the frame pattern for sequences
                frame_pattern = '#' * num_digits
                file_pattern = '{}{}{}'.format(data['base_name'], frame_pattern, data['ext'])
                full_path = os.path.join(self.parent().dir_path.text(), file_pattern)
            elif item_type in ('image', 'video'):
                # Use the exact file path for single images and videos
                full_path = data
            else:
                full_path = ''
            if full_path:
                full_path = full_path.replace('\\', '/')
                url = QtCore.QUrl.fromLocalFile(full_path)
                urls.append(url)
        if urls:
            # Set the URLs in the MIME data
            mimedata.setUrls(urls)
            drag.setMimeData(mimedata)
            drag.exec_(QtCore.Qt.CopyAction)

class SequenceBrowserPanel(QtWidgets.QWidget):
    def __init__(self):
        super(SequenceBrowserPanel, self).__init__()

        # Set up the main layout
        self.setWindowTitle("Sequence Browser")
        self.setGeometry(300, 300, 1000, 800)
        layout = QtWidgets.QVBoxLayout(self)

        # Directory browsing widgets
        self.dir_label = QtWidgets.QLabel("Select Directory:")
        self.dir_path = QtWidgets.QLineEdit(self)
        self.dir_button = QtWidgets.QPushButton("Browse", self)
        self.dir_button.clicked.connect(self.browse_directory)

        # Thumbnail display area using the custom DraggableListWidget
        self.thumb_view = DraggableListWidget(self)
        self.thumb_view.setViewMode(QtWidgets.QListView.IconMode)
        self.thumb_view.setIconSize(QtCore.QSize(128, 128))
        self.thumb_view.setGridSize(QtCore.QSize(150, 150))
        self.thumb_view.setResizeMode(QtWidgets.QListView.Adjust)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setVisible(False)

        # Playback and Import buttons
        self.button_layout = QtWidgets.QHBoxLayout()
        self.play_button = QtWidgets.QPushButton("Play Selected", self)
        self.play_button.clicked.connect(self.play_selected_sequence)
        self.import_button = QtWidgets.QPushButton("Import Selected", self)
        self.import_button.clicked.connect(self.import_selected_sequence)

        self.button_layout.addWidget(self.play_button)
        self.button_layout.addWidget(self.import_button)

        # Add widgets to layout
        layout.addWidget(self.dir_label)
        layout.addWidget(self.dir_path)
        layout.addWidget(self.dir_button)
        layout.addWidget(self.thumb_view)
        layout.addWidget(self.progress_bar)
        layout.addLayout(self.button_layout)

        # Paths to cineSync and MPC-HC
        self.cinesync_path = self.get_cinesync_path()
        self.mpc_path = self.get_mpc_path()

    def get_cinesync_path(self):
        """Determine the path to the cineSync executable."""
        # Update this path to point to your cineSync executable
        return "C:/Program Files (x86)/cineSync Play/cineSyncPlay.exe"

    def get_mpc_path(self):
        """Determine the path to the Media Player Classic executable."""
        # Update this path to point to your MPC-HC executable
        return "C:/Program Files (x86)/K-Lite Codec Pack/MPC-HC64/mpc-hc64.exe"

    def browse_directory(self):
        """Open file dialog to select a directory and load its contents."""
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.dir_path.setText(directory)
            self.load_thumbnails(directory)

    def load_thumbnails(self, directory):
        """Load thumbnails for images, image sequences, and video files."""
        self.thumb_view.clear()
        image_extensions = ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.exr', '.dpx')
        video_extensions = ('.mov', '.mp4', '.avi', '.mkv', '.mxf')

        # Only list files in the selected directory
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        files = [f for f in files if f.lower().endswith(image_extensions + video_extensions)]

        # Group image sequences
        sequences, single_images = self.find_image_sequences(files, image_extensions)

        total_items = len(sequences) + len(single_images) + len([f for f in files if f.lower().endswith(video_extensions)])
        if total_items == 0:
            return

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(total_items)

        index = 0

        # Add image sequences
        for seq_key, seq_info in sequences.items():
            seq_name = seq_key  # Display the key as the sequence name
            item = QtWidgets.QListWidgetItem(seq_name)

            # Generate thumbnail using the middle frame
            middle_frame = seq_info['frames'][len(seq_info['frames']) // 2]
            num_digits = len(middle_frame)
            frame_number = middle_frame.zfill(num_digits)
            frame_filename = f"{seq_info['base_name']}{frame_number}{seq_info['ext']}"
            frame_filepath = os.path.join(directory, frame_filename)

            pixmap = self.create_thumbnail(frame_filepath)
            if pixmap:
                item.setIcon(QtGui.QIcon(pixmap))
            else:
                # Set a default icon if thumbnail creation fails
                image_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
                item.setIcon(image_icon)

            item.setData(QtCore.Qt.UserRole, seq_info)
            item.setData(QtCore.Qt.UserRole + 1, 'sequence')  # Custom role to identify type
            self.thumb_view.addItem(item)
            index += 1
            self.progress_bar.setValue(index)
            QtWidgets.QApplication.processEvents()  # Update UI during processing

        # Add single images
        for image_file in single_images:
            file_path = os.path.join(directory, image_file)
            item = QtWidgets.QListWidgetItem(image_file)

            # Generate thumbnail for the image
            pixmap = self.create_thumbnail(file_path)
            if pixmap:
                item.setIcon(QtGui.QIcon(pixmap))
            else:
                # Set a default icon if thumbnail creation fails
                image_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
                item.setIcon(image_icon)

            item.setData(QtCore.Qt.UserRole, file_path)
            item.setData(QtCore.Qt.UserRole + 1, 'image')  # Custom role to identify type
            self.thumb_view.addItem(item)
            index += 1
            self.progress_bar.setValue(index)
            QtWidgets.QApplication.processEvents()

        # Add video files
        for file_name in files:
            if file_name.lower().endswith(video_extensions):
                file_path = os.path.join(directory, file_name)
                item = QtWidgets.QListWidgetItem(file_name)
                # Set a default video icon
                video_icon = self.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay)
                item.setIcon(video_icon)
                item.setData(QtCore.Qt.UserRole, file_path)
                item.setData(QtCore.Qt.UserRole + 1, 'video')  # Custom role to identify type
                self.thumb_view.addItem(item)
                index += 1
                self.progress_bar.setValue(index)
                QtWidgets.QApplication.processEvents()  # Update UI during processing

        # Hide progress bar when done
        self.progress_bar.setVisible(False)

    def create_thumbnail(self, filepath):
        """Create a thumbnail for the given image file."""
        try:
            pixmap = QtGui.QPixmap(filepath)
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(128, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                return thumbnail
            else:
                return None
        except Exception as e:
            print(f"Failed to create thumbnail for {filepath}: {e}")
            return None

    def find_image_sequences(self, files, image_extensions):
        """Find and group image sequences, also identify single images."""
        sequences = {}
        single_images = []

        # Build a dictionary of files with their base names and extensions
        for file_name in files:
            if file_name.lower().endswith(image_extensions):
                base_name, frame_str, ext = self.parse_filename(file_name)
                if base_name is not None:
                    key = (base_name or '') + ext
                    if key not in sequences:
                        sequences[key] = {'base_name': base_name or '', 'ext': ext, 'frames': []}
                    sequences[key]['frames'].append(frame_str)
                else:
                    single_images.append(file_name)

        # Remove sequences with only one frame and treat them as single images
        for key in list(sequences.keys()):
            if len(sequences[key]['frames']) == 1:
                frame_str = sequences[key]['frames'][0]
                file_name = f"{sequences[key]['base_name']}{frame_str}{sequences[key]['ext']}"
                single_images.append(file_name)
                del sequences[key]

        return sequences, single_images

    def parse_filename(self, filename):
        """Parse the filename to extract base name, frame number, and extension."""
        # Match patterns with three or more digits, base name can be empty
        match = re.match(r'^(.*?)(\d{3,})(\.\w+)$', filename)
        if match:
            base_name = match.group(1)
            frame_str = match.group(2)
            ext = match.group(3)
            return base_name, frame_str, ext
        else:
            return None, None, None

    def play_selected_sequence(self):
        """Play the selected sequences, images, or video files using cineSync or MPC-HC."""
        selected_items = self.thumb_view.selectedItems()
        for selected_item in selected_items:
            data = selected_item.data(QtCore.Qt.UserRole)
            item_type = selected_item.data(QtCore.Qt.UserRole + 1)
            if item_type == 'sequence':
                self.play_with_cinesync(data, item_type)
            elif item_type == 'image':
                self.play_with_cinesync(data, item_type)
            elif item_type == 'video':
                if data.lower().endswith('.mkv'):
                    # Play .mkv files with MPC-HC
                    self.play_with_mpc(data)
                else:
                    # Play other videos with cineSync
                    self.play_with_cinesync(data, item_type)

    def play_with_cinesync(self, data, item_type):
        """Launch cineSync to play the media."""
        try:
            if os.path.exists(self.cinesync_path):
                if item_type == 'sequence':
                    # Handle image sequences
                    frames = sorted(data['frames'])
                    num_digits = len(frames[0])
                    frame_numbers = [int(f) for f in frames]
                    file_list = [os.path.join(self.dir_path.text(), '{}{}{}'.format(data['base_name'], str(f).zfill(num_digits), data['ext'])) for f in frame_numbers]
                elif item_type in ('video', 'image'):
                    # Handle video files and single images
                    full_path = data
                    file_list = [full_path]
                else:
                    return

                # Prepare the command to launch cineSync
                args = [self.cinesync_path] + file_list
                subprocess.Popen(args)
            else:
                nuke.message("cineSync not found at the specified path:\n{}".format(self.cinesync_path))
        except Exception as e:
            nuke.message("Failed to launch cineSync:\n{}".format(str(e)))

    def play_with_mpc(self, file_path):
        """Launch MPC-HC to play the .mkv video file."""
        try:
            if os.path.exists(self.mpc_path):
                # Launch MPC-HC
                subprocess.Popen([self.mpc_path, file_path])
            else:
                nuke.message("MPC-HC not found at the specified path:\n{}".format(self.mpc_path))
        except Exception as e:
            nuke.message("Failed to launch MPC-HC:\n{}".format(str(e)))

    def import_selected_sequence(self):
        """Import the selected sequences, images, or video files into Nuke as Read nodes."""
        selected_items = self.thumb_view.selectedItems()
        for selected_item in selected_items:
            data = selected_item.data(QtCore.Qt.UserRole)
            item_type = selected_item.data(QtCore.Qt.UserRole + 1)
            if item_type == 'sequence':
                # Import image sequence
                self.import_sequence_in_nuke(data)
            elif item_type == 'video':
                # Import video file
                self.import_video_in_nuke(data)
            elif item_type == 'image':
                # Import single image
                self.import_image_in_nuke(data)

    def import_sequence_in_nuke(self, seq_info):
        """Import an image sequence into Nuke as a Read node."""
        try:
            frames = sorted(seq_info['frames'])
            num_digits = len(frames[0])
            frame_pattern = '%0{}d'.format(num_digits)
            file_pattern = '{}{}{}'.format(seq_info['base_name'], frame_pattern, seq_info['ext'])
            full_path = os.path.join(self.dir_path.text(), file_pattern)
            full_path = full_path.replace('\\', '/')

            # Convert frame strings to integers to find min and max
            frame_numbers = [int(f) for f in frames]
            first_frame = min(frame_numbers)
            last_frame = max(frame_numbers)

            # Create Read node
            read_node = nuke.createNode('Read', 'file "{}"'.format(full_path), inpanel=False)

            # Set frame range on the Read node
            read_node['first'].setValue(first_frame)
            read_node['last'].setValue(last_frame)
            read_node['origfirst'].setValue(first_frame)
            read_node['origlast'].setValue(last_frame)
        except Exception as e:
            nuke.message("Failed to import sequence into Nuke:\n{}".format(str(e)))

    def import_video_in_nuke(self, file_path):
        """Import a video file into Nuke as a Read node."""
        try:
            # Create Read node
            read_node = nuke.createNode('Read', 'file "{}"'.format(file_path.replace('\\', '/')), inpanel=False)
        except Exception as e:
            nuke.message("Failed to import video into Nuke:\n{}".format(str(e)))

    def import_image_in_nuke(self, file_path):
        """Import a single image into Nuke as a Read node."""
        try:
            # Create Read node
            read_node = nuke.createNode('Read', 'file "{}"'.format(file_path.replace('\\', '/')), inpanel=False)
        except Exception as e:
            nuke.message("Failed to import image into Nuke:\n{}".format(str(e)))

# Register the panel to Nuke's menu system and make it dockable
def sequence_browser_panel():
    nukescripts.panels.registerWidgetAsPanel(
        "Sequence_Browser.SequenceBrowserPanel",
        "Sequence Browser",
        "com.example.SequenceBrowserPanel",
        True
    )

# Automatically register the panel when the plugin is imported
sequence_browser_panel()
