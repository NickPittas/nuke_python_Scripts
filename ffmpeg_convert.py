import nuke
import nukescripts
import subprocess
import shlex
from PySide6 import QtWidgets, QtCore
import os

class FFMPEGConverterPanel(QtWidgets.QWidget):
    def __init__(self):
        super(FFMPEGConverterPanel, self).__init__()
        self.setWindowTitle("FFmpeg Converter Panel")
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setFixedWidth(400)  # Make the UI more compact

        # File Selection
        file_selection_layout = QtWidgets.QHBoxLayout()
        self.file_path_edit = QtWidgets.QLineEdit()
        self.file_path_edit.textChanged.connect(self.update_command_display)
        file_selection_layout.addWidget(self.file_path_edit)
        self.browse_button = QtWidgets.QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_file)
        file_selection_layout.addWidget(self.browse_button)
        self.layout().addLayout(file_selection_layout)

        # Write Node Selection
        write_node_layout = QtWidgets.QHBoxLayout()
        self.write_node_label = QtWidgets.QLabel("Selected Write Node:")
        write_node_layout.addWidget(self.write_node_label)
        self.write_node_name_label = QtWidgets.QLabel("None")
        write_node_layout.addWidget(self.write_node_name_label)
        self.layout().addLayout(write_node_layout)

        self.refresh_button = QtWidgets.QPushButton("Refresh Write Node Selection")
        self.refresh_button.clicked.connect(self.update_selected_write_node)
        self.layout().addWidget(self.refresh_button)
        self.write_node = None
        self.convert_button = None  # Initialize convert_button to avoid attribute error

        # Video Format Selection
        format_layout = QtWidgets.QHBoxLayout()
        format_layout.addWidget(QtWidgets.QLabel("Format:"))
        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItems(["mp4", "mov", "mxf"])
        self.format_combo.currentIndexChanged.connect(self.update_format_options)
        format_layout.addWidget(self.format_combo)
        self.layout().addLayout(format_layout)

        # Format Options (Codec Selection)
        codec_layout = QtWidgets.QHBoxLayout()
        codec_layout.addWidget(QtWidgets.QLabel("Codec:"))
        self.format_options_combo = QtWidgets.QComboBox()
        self.format_options_combo.currentIndexChanged.connect(self.update_command_display)
        codec_layout.addWidget(self.format_options_combo)
        self.layout().addLayout(codec_layout)

        # Resolution Selection
        resolution_layout = QtWidgets.QHBoxLayout()
        resolution_layout.addWidget(QtWidgets.QLabel("Resolution (WxH):"))
        self.resolution_width = QtWidgets.QSpinBox()
        self.resolution_width.setRange(1, 8192)
        self.resolution_width.setValue(nuke.root().format().width())
        self.resolution_width.valueChanged.connect(self.update_command_display)
        resolution_layout.addWidget(self.resolution_width)
        self.resolution_height = QtWidgets.QSpinBox()
        self.resolution_height.setRange(1, 8192)
        self.resolution_height.setValue(nuke.root().format().height())
        self.resolution_height.valueChanged.connect(self.update_command_display)
        resolution_layout.addWidget(self.resolution_height)
        self.layout().addLayout(resolution_layout)

        # Frame Rate and Overwrite Option
        options_layout = QtWidgets.QHBoxLayout()
        options_layout.addWidget(QtWidgets.QLabel("Frame Rate:"))
        self.frame_rate = QtWidgets.QDoubleSpinBox()
        self.frame_rate.setRange(1, 120)
        self.frame_rate.setValue(24.0)
        self.frame_rate.valueChanged.connect(self.update_command_display)
        options_layout.addWidget(self.frame_rate)
        self.overwrite_checkbox = QtWidgets.QCheckBox("Overwrite")
        self.overwrite_checkbox.stateChanged.connect(self.update_command_display)
        options_layout.addWidget(self.overwrite_checkbox)
        self.layout().addLayout(options_layout)

        # Filename Prefix and Suffix
        filename_layout = QtWidgets.QHBoxLayout()
        filename_layout.addWidget(QtWidgets.QLabel("Prefix:"))
        self.prefix_edit = QtWidgets.QLineEdit()
        self.prefix_edit.textChanged.connect(self.update_command_display)
        filename_layout.addWidget(self.prefix_edit)
        filename_layout.addWidget(QtWidgets.QLabel("Suffix:"))
        self.suffix_edit = QtWidgets.QLineEdit()
        self.suffix_edit.textChanged.connect(self.update_command_display)
        filename_layout.addWidget(self.suffix_edit)
        self.layout().addLayout(filename_layout)

        # FFmpeg Command Display
        self.command_display = QtWidgets.QTextEdit()
        self.command_display.setReadOnly(True)
        self.layout().addWidget(self.command_display)

        # Convert Button
        self.convert_button = QtWidgets.QPushButton("Convert to Video")
        self.convert_button.clicked.connect(self.convert_to_video)
        self.layout().addWidget(self.convert_button)
        self.convert_button.setEnabled(True)  # Enable the button as we can now convert from file

        # Update the selected write node after initializing the UI
        self.update_selected_write_node()

    def browse_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File to Convert")
        if file_path:
            self.file_path_edit.setText(file_path)
            self.update_command_display()

    def update_selected_write_node(self):
        selected_nodes = nuke.selectedNodes("Write")
        if selected_nodes:
            self.write_node = selected_nodes[0]
            self.write_node_name_label.setText(self.write_node.name())
        else:
            self.write_node = None
            self.write_node_name_label.setText("None")
        self.update_format_options()
        self.update_command_display()

    def update_format_options(self):
        selected_format = self.format_combo.currentText()
        self.format_options_combo.clear()
        if selected_format in ["mov", "mxf"]:
            self.format_options_combo.addItems([
                "DNxHR LB", "DNxHR SQ", "DNxHR HQ", "DNxHR HQX", "DNxHR 444"
            ])
            if selected_format == "mov":
                self.format_options_combo.addItems([
                    "ProRes 422 Proxy", "ProRes 422 LT", "ProRes 422", "ProRes 422 HQ",
                    "ProRes 4444", "ProRes 4444 XQ", "ProRes 4444 Alpha",
                    "H.264", "H.265"
                ])
            elif selected_format == "mxf":
                self.format_options_combo.addItems(["XDCAM HD422"])
        elif selected_format == "mp4":
            self.format_options_combo.addItems(["H.264", "H.265", "MPEG-4", "VP9"])

        self.update_command_display()

    def update_command_display(self):
        input_path = self.file_path_edit.text() or (nuke.filename(self.write_node) if self.write_node else "")
        if not input_path:
            self.command_display.setText("No input file selected.")
            return

        # Check for padded sequence
        base_name = os.path.basename(input_path)
        padded_number = ''.join([char if char.isdigit() else '' for char in base_name])
        is_sequence = '#' in base_name or (padded_number and len(padded_number) > 1)
        if is_sequence:
            num_hashes = len(padded_number) if padded_number else base_name.count('#')
            input_path = input_path.replace(padded_number, f'%0{num_hashes}d') if padded_number else input_path.replace('#' * num_hashes, f'%0{num_hashes}d')

        # Get output file path
        base_path, extension = os.path.splitext(input_path)
        base_path_clean = base_path.replace('%0' + str(len(padded_number)) + 'd', '') if is_sequence else base_path
        video_format = self.format_combo.currentText()
        folder_path = os.path.normpath(os.path.join(os.path.dirname(base_path), video_format))
        prefix = f"{self.prefix_edit.text()}_" if self.prefix_edit.text() else ""
        suffix = f"{self.suffix_edit.text()}" if self.suffix_edit.text() else ""
        output_file = os.path.normpath(os.path.join(folder_path, f"{prefix}{os.path.basename(base_path_clean)}{suffix}.{video_format}"))

        # Correct the output file name for padded sequences
        if is_sequence:
            output_file = output_file.replace(os.path.basename(base_path_clean), f"{prefix}{os.path.basename(base_path_clean)}{suffix}")
            output_file = output_file.replace('%0' + str(num_hashes) + 'd', '')

        # Remove redundant dots from the output file path
        output_file = output_file.replace('..', '.')

        # Build the ffmpeg command
        codec = self.format_options_combo.currentText()
        command = [
            'ffmpeg',
            '-y' if self.overwrite_checkbox.isChecked() else '-n'
        ]

        if is_sequence:
            command.extend(['-framerate', str(self.frame_rate.value())])

        command.extend([
            '-i', f'"{input_path}"',  # Quote path to handle spaces
            '-s', f'{self.resolution_width.value()}x{self.resolution_height.value()}'
        ])

        if "DNxHR" in codec:
            command.extend(['-c:v', 'dnxhd'])
            if "LB" in codec:
                command.extend(['-profile:v', 'dnxhr_lb'])
            elif "SQ" in codec:
                command.extend(['-profile:v', 'dnxhr_sq'])
            elif "HQ" in codec:
                command.extend(['-profile:v', 'dnxhr_hq'])
            elif "HQX" in codec:
                command.extend(['-profile:v', 'dnxhr_hqx'])
            elif "444" in codec:
                command.extend(['-profile:v', 'dnxhr_444'])
        elif "ProRes" in codec:
            command.extend(['-c:v', 'prores_ks'])
            if "Proxy" in codec:
                command.extend(['-profile:v', '0'])
            elif "LT" in codec:
                command.extend(['-profile:v', '1'])
            elif "HQ" in codec:
                command.extend(['-profile:v', '3'])
            elif "4444" in codec:
                if "XQ" in codec:
                    command.extend(['-profile:v', '5'])
                elif "Alpha" in codec:
                    command.extend(['-profile:v', '4', '-pix_fmt', 'yuva444p10le'])
                else:
                    command.extend(['-profile:v', '4'])
            else:
                command.extend(['-profile:v', '2'])  # Standard
        elif codec == "H.264":
            command.extend(['-c:v', 'libx264', '-crf', '23'])
        elif codec == "H.265":
            command.extend(['-c:v', 'libx265', '-crf', '28'])
        elif codec == "MPEG-4":
            command.extend(['-c:v', 'mpeg4', '-q:v', '5'])
        elif codec == "VP9":
            command.extend(['-c:v', 'libvpx-vp9', '-crf', '30', '-b:v', '0'])
        elif codec == "XDCAM HD422":
            command.extend(['-c:v', 'mpeg2video', '-b:v', '50M', '-minrate', '50M', '-maxrate', '50M', '-bufsize', '17M'])

        command.extend([f'"{output_file}"'])

        # Set command in the display
        self.command_display.setText(' '.join(command))

    def convert_to_video(self):
        input_path = self.file_path_edit.text() or (nuke.filename(self.write_node) if self.write_node else "")
        if not input_path:
            nuke.message("Please select an input file or Write node.")
            return

        # Get the command from the display
        command = shlex.split(self.command_display.toPlainText())

        # Extract the output file path from the command
        output_file = command[-1].strip('"')
        output_folder = os.path.dirname(output_file)

        # Create the output folder if it doesn't exist
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            nuke.message(f"Failed to create output folder: {e}")
            return

        # Execute the FFmpeg command
        try:
            subprocess.run(command, check=True)
            nuke.message("FFmpeg conversion completed successfully!")
        except subprocess.CalledProcessError as e:
            nuke.message(f"FFmpeg conversion failed: {e}")

# Create the Dockable Panel
def create_ffmpeg_converter_panel():
    nukescripts.registerWidgetAsPanel(
        'ffmpeg_convert.FFMPEGConverterPanel', 
        'FFmpeg Converter Panel', 
        'uk.co.thefoundry.ffmpegConverterPanel', 
        create=True
    )