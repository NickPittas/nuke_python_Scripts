import os
import json
import re
import nuke

# Determine Nuke version and import the appropriate Qt module
try:
    nuke_version = int(nuke.NUKE_VERSION_MAJOR)
except Exception:
    nuke_version = 15  # Default fallback

if nuke_version >= 16:
    from PySide6 import QtWidgets, QtCore
else:
    from PySide2 import QtWidgets, QtCore

class WriteNodeKENTDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(WriteNodeKENTDialog, self).__init__(parent)
        self.setWindowTitle("Write Node KENT")
        self.setMinimumWidth(800)  # Wider dialog to accommodate paths

        # Folder where this script resides
        self.script_dir = os.path.dirname(__file__)

        # Gather JSON templates in the script folder
        self.template_files = [
            f for f in os.listdir(self.script_dir)
            if f.lower().endswith('.json')
        ]
        if not self.template_files:
            nuke.message(f"No JSON template files found in:\n{self.script_dir}")
            self.close()
            return

        # Load each JSON template into a dict
        self.templates_data = {}
        for tmpl_file in self.template_files:
            full_path = os.path.join(self.script_dir, tmpl_file)
            try:
                with open(full_path, 'r') as f:
                    self.templates_data[tmpl_file] = json.load(f)
            except Exception as e:
                nuke.message(f"Error loading {tmpl_file}:\n{e}")

        # Determine default version from the current Nuke script (e.g., v001)
        script_name = nuke.root().name()
        match = re.search(r'v(\d{3,})', script_name)
        self.defaultVersion = "v" + match.group(1) if match else "v001"

        # Store template data and colorspace
        self.template_data = None
        self.finalColorspace = "sRGB"
        self.finalNodeColorspace = "sRGB"

        self.initUI()

    def initUI(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()
        form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setLabelAlignment(QtCore.Qt.AlignRight)

        # --- Template Selection (always visible) ---
        self.templateSelectCombo = QtWidgets.QComboBox()
        self.templateSelectCombo.addItems(self.template_files)
        self.templateSelectCombo.currentIndexChanged.connect(self.loadSelectedTemplate)
        form_layout.addRow("Select Template:", self.templateSelectCombo)

        self.templateNameLabel = QtWidgets.QLabel("No template loaded yet")
        form_layout.addRow("Template Name:", self.templateNameLabel)

        # --- Sequence Row ---
        self.sequenceRow = QtWidgets.QWidget()
        seq_layout = QtWidgets.QHBoxLayout(self.sequenceRow)
        self.sequenceCombo = QtWidgets.QComboBox()
        seq_layout.addWidget(self.sequenceCombo)
        self.overrideSequenceCheck = QtWidgets.QCheckBox("Override")
        seq_layout.addWidget(self.overrideSequenceCheck)
        self.sequenceEdit = QtWidgets.QLineEdit()
        self.sequenceEdit.setVisible(False)
        self.overrideSequenceCheck.toggled.connect(self.onSequenceOverrideToggled)
        seq_layout.addWidget(self.sequenceEdit)
        form_layout.addRow("Sequence:", self.sequenceRow)

        # --- Shot Number Row (auto-increment removed) ---
        self.shotNumberRow = QtWidgets.QWidget()
        shot_layout = QtWidgets.QHBoxLayout(self.shotNumberRow)
        self.shotNumberEdit = QtWidgets.QLineEdit()
        shot_layout.addWidget(self.shotNumberEdit)
        form_layout.addRow("Shot Number:", self.shotNumberRow)

        # --- Description Row ---
        self.descriptionRow = QtWidgets.QWidget()
        desc_layout = QtWidgets.QHBoxLayout(self.descriptionRow)
        self.descriptionCombo = QtWidgets.QComboBox()
        self.descriptionCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        desc_layout.addWidget(self.descriptionCombo)
        self.overrideDescriptionCheck = QtWidgets.QCheckBox("Override")
        desc_layout.addWidget(self.overrideDescriptionCheck)
        self.descriptionEdit = QtWidgets.QLineEdit()
        self.descriptionEdit.setVisible(False)
        self.overrideDescriptionCheck.toggled.connect(self.onDescriptionOverrideToggled)
        desc_layout.addWidget(self.descriptionEdit)
        form_layout.addRow("Description:", self.descriptionRow)

        # --- Pixel Mapping Row ---
        self.pixelMappingRow = QtWidgets.QWidget()
        pix_layout = QtWidgets.QHBoxLayout(self.pixelMappingRow)
        self.pixelMappingCombo = QtWidgets.QComboBox()
        self.pixelMappingCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        pix_layout.addWidget(self.pixelMappingCombo)
        self.overridePixelMappingCheck = QtWidgets.QCheckBox("Override")
        pix_layout.addWidget(self.overridePixelMappingCheck)
        self.pixelMappingEdit = QtWidgets.QLineEdit()
        self.pixelMappingEdit.setVisible(False)
        self.overridePixelMappingCheck.toggled.connect(self.onPixelMappingOverrideToggled)
        pix_layout.addWidget(self.pixelMappingEdit)
        form_layout.addRow("Pixel Mapping:", self.pixelMappingRow)

        # --- Full Resolution Row ---
        self.fullResRow = QtWidgets.QWidget()
        full_res_layout = QtWidgets.QHBoxLayout(self.fullResRow)
        self.fullResCombo = QtWidgets.QComboBox()
        self.fullResCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        full_res_layout.addWidget(self.fullResCombo)
        self.overrideFullResCheck = QtWidgets.QCheckBox("Override")
        full_res_layout.addWidget(self.overrideFullResCheck)
        self.fullResEdit = QtWidgets.QLineEdit()
        self.fullResEdit.setVisible(False)
        self.overrideFullResCheck.toggled.connect(self.onFullResOverrideToggled)
        full_res_layout.addWidget(self.fullResEdit)
        form_layout.addRow("Full Resolution:", self.fullResRow)

        # --- Proxy Resolution Row ---
        self.proxyResRow = QtWidgets.QWidget()
        proxy_res_layout = QtWidgets.QHBoxLayout(self.proxyResRow)
        self.proxyResCombo = QtWidgets.QComboBox()
        self.proxyResCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        proxy_res_layout.addWidget(self.proxyResCombo)
        self.overrideProxyResCheck = QtWidgets.QCheckBox("Override")
        proxy_res_layout.addWidget(self.overrideProxyResCheck)
        self.proxyResEdit = QtWidgets.QLineEdit()
        self.proxyResEdit.setVisible(False)
        self.overrideProxyResCheck.toggled.connect(self.onProxyResOverrideToggled)
        proxy_res_layout.addWidget(self.proxyResEdit)
        form_layout.addRow("Proxy Resolution:", self.proxyResRow)

        # --- Colorspace Row ---
        self.colorspaceRow = QtWidgets.QWidget()
        colorspace_layout = QtWidgets.QHBoxLayout(self.colorspaceRow)
        self.colorspaceCombo = QtWidgets.QComboBox()
        self.colorspaceCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.colorspaceCombo.currentIndexChanged.connect(self.onColorspaceChanged)
        colorspace_layout.addWidget(self.colorspaceCombo)
        self.overrideColorspaceCheck = QtWidgets.QCheckBox("Override")
        colorspace_layout.addWidget(self.overrideColorspaceCheck)
        self.colorspaceEdit = QtWidgets.QLineEdit()
        self.colorspaceEdit.setVisible(False)
        self.overrideColorspaceCheck.toggled.connect(self.onColorspaceOverrideToggled)
        colorspace_layout.addWidget(self.colorspaceEdit)
        form_layout.addRow("Colorspace:", self.colorspaceRow)

        # --- Gamma Row ---
        self.gammaRow = QtWidgets.QWidget()
        gamma_layout = QtWidgets.QHBoxLayout(self.gammaRow)
        self.gammaCombo = QtWidgets.QComboBox()
        self.gammaCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        gamma_layout.addWidget(self.gammaCombo)
        self.overrideGammaCheck = QtWidgets.QCheckBox("Override")
        gamma_layout.addWidget(self.overrideGammaCheck)
        self.gammaEdit = QtWidgets.QLineEdit()
        self.gammaEdit.setVisible(False)
        self.overrideGammaCheck.toggled.connect(self.onGammaOverrideToggled)
        gamma_layout.addWidget(self.gammaEdit)
        form_layout.addRow("Gamma:", self.gammaRow)

        # --- FPS Row ---
        self.fpsRow = QtWidgets.QWidget()
        fps_layout = QtWidgets.QHBoxLayout(self.fpsRow)
        self.fpsCombo = QtWidgets.QComboBox()
        fps_layout.addWidget(self.fpsCombo)
        form_layout.addRow("FPS:", self.fpsRow)

        # --- Version Row (unchanged) ---
        self.versionRow = QtWidgets.QWidget()
        version_layout = QtWidgets.QHBoxLayout(self.versionRow)
        self.autoIncrementVersionCheck = QtWidgets.QCheckBox("Auto Increment")
        version_layout.addWidget(self.autoIncrementVersionCheck)
        self.overrideVersionCheck = QtWidgets.QCheckBox("Override")
        version_layout.addWidget(self.overrideVersionCheck)
        self.versionEdit = QtWidgets.QLineEdit(self.defaultVersion)
        self.versionEdit.setVisible(False)
        self.overrideVersionCheck.toggled.connect(self.onVersionOverrideToggled)
        version_layout.addWidget(self.versionEdit)
        form_layout.addRow("Version:", self.versionRow)

        # --- Frame Padding Row ---
        self.framePaddingRow = QtWidgets.QWidget()
        frame_padding_layout = QtWidgets.QHBoxLayout(self.framePaddingRow)
        self.framePaddingEdit = QtWidgets.QLineEdit()
        self.framePaddingEdit.textChanged.connect(self.autoUpdatePreview)
        frame_padding_layout.addWidget(self.framePaddingEdit)
        form_layout.addRow("Frame Padding:", self.framePaddingRow)

        # --- Extension Row ---
        self.extensionRow = QtWidgets.QWidget()
        ext_layout = QtWidgets.QHBoxLayout(self.extensionRow)
        self.extensionCombo = QtWidgets.QComboBox()
        self.extensionCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.extensionCombo.currentIndexChanged.connect(self.onExtensionChanged)
        ext_layout.addWidget(self.extensionCombo)
        self.overrideExtensionCheck = QtWidgets.QCheckBox("Override")
        ext_layout.addWidget(self.overrideExtensionCheck)
        self.extensionEdit = QtWidgets.QLineEdit()
        self.extensionEdit.setVisible(False)
        self.overrideExtensionCheck.toggled.connect(self.onExtensionOverrideToggled)
        ext_layout.addWidget(self.extensionEdit)
        form_layout.addRow("Extension:", self.extensionRow)

        # --- Base Directory Row (always visible) ---
        self.baseDirRow = QtWidgets.QWidget()
        base_dir_layout = QtWidgets.QHBoxLayout(self.baseDirRow)
        self.baseDirEdit = QtWidgets.QLineEdit()
        self.baseDirEdit.textChanged.connect(self.autoUpdatePreview)
        self.baseDirButton = QtWidgets.QPushButton("Browse")
        self.baseDirButton.clicked.connect(self.browseBaseDir)
        base_dir_layout.addWidget(self.baseDirEdit)
        base_dir_layout.addWidget(self.baseDirButton)
        form_layout.addRow("Base Directory:", self.baseDirRow)

        # --- Preview Fields (always visible) ---
        self.previewFullEdit = QtWidgets.QTextEdit()
        self.previewFullEdit.setReadOnly(True)
        self.previewFullEdit.setMinimumHeight(60)
        form_layout.addRow("Full Resolution Path:", self.previewFullEdit)
        self.previewProxyEdit = QtWidgets.QTextEdit()
        self.previewProxyEdit.setReadOnly(True)
        self.previewProxyEdit.setMinimumHeight(60)
        form_layout.addRow("Proxy Resolution Path:", self.previewProxyEdit)

        main_layout.addLayout(form_layout)

        # --- Buttons ---
        button_layout = QtWidgets.QHBoxLayout()
        self.loadSettingsButton = QtWidgets.QPushButton("Load Settings")
        self.loadSettingsButton.clicked.connect(self.loadSettings)
        self.saveSettingsButton = QtWidgets.QPushButton("Save Settings")
        self.saveSettingsButton.clicked.connect(self.saveSettings)
        self.createNodesButton = QtWidgets.QPushButton("Create Write Node")
        self.createNodesButton.clicked.connect(self.createWriteNode)
        self.cancelButton = QtWidgets.QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        button_layout.addWidget(self.loadSettingsButton)
        button_layout.addWidget(self.saveSettingsButton)
        button_layout.addWidget(self.createNodesButton)
        button_layout.addWidget(self.cancelButton)
        main_layout.addLayout(button_layout)

        # Connect signals for auto-update preview
        self.setupAutoUpdate()

        # Load the first template by default
        self.templateSelectCombo.setCurrentIndex(0)
        self.loadSelectedTemplate(0)

    def setupAutoUpdate(self):
        # Connect all UI elements that should trigger a preview update
        self.sequenceCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.sequenceEdit.textChanged.connect(self.autoUpdatePreview)
        self.shotNumberEdit.textChanged.connect(self.autoUpdatePreview)
        self.descriptionCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.descriptionEdit.textChanged.connect(self.autoUpdatePreview)
        self.pixelMappingCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.pixelMappingEdit.textChanged.connect(self.autoUpdatePreview)
        self.fullResCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.fullResEdit.textChanged.connect(self.autoUpdatePreview)
        self.proxyResCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.proxyResEdit.textChanged.connect(self.autoUpdatePreview)
        self.colorspaceCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.colorspaceEdit.textChanged.connect(self.autoUpdatePreview)
        self.gammaCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.gammaEdit.textChanged.connect(self.autoUpdatePreview)
        self.fpsCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.extensionCombo.currentIndexChanged.connect(self.autoUpdatePreview)
        self.extensionEdit.textChanged.connect(self.autoUpdatePreview)
        self.versionEdit.textChanged.connect(self.autoUpdatePreview)
        
        # Checkboxes
        self.overrideSequenceCheck.toggled.connect(self.autoUpdatePreview)
        self.overrideDescriptionCheck.toggled.connect(self.autoUpdatePreview)
        self.overridePixelMappingCheck.toggled.connect(self.autoUpdatePreview)
        self.overrideFullResCheck.toggled.connect(self.autoUpdatePreview)
        self.overrideProxyResCheck.toggled.connect(self.autoUpdatePreview)
        self.overrideColorspaceCheck.toggled.connect(self.autoUpdatePreview)
        self.overrideGammaCheck.toggled.connect(self.autoUpdatePreview)
        self.overrideVersionCheck.toggled.connect(self.autoUpdatePreview)
        self.overrideExtensionCheck.toggled.connect(self.autoUpdatePreview)
        self.autoIncrementVersionCheck.toggled.connect(self.autoUpdatePreview)

    def autoUpdatePreview(self):
        if self.template_data:
            # Use a timer to prevent too many updates at once
            QtCore.QTimer.singleShot(10, self.updatePreview)

    # --- Toggle functions for override checkboxes ---
    def onSequenceOverrideToggled(self, checked):
        self.sequenceEdit.setVisible(checked)
        self.sequenceCombo.setEnabled(not checked)
        self.autoUpdatePreview()

    def onDescriptionOverrideToggled(self, checked):
        self.descriptionEdit.setVisible(checked)
        self.descriptionCombo.setEnabled(not checked)
        self.autoUpdatePreview()

    def onPixelMappingOverrideToggled(self, checked):
        self.pixelMappingEdit.setVisible(checked)
        self.pixelMappingCombo.setEnabled(not checked)
        self.autoUpdatePreview()

    def onFullResOverrideToggled(self, checked):
        self.fullResEdit.setVisible(checked)
        self.fullResCombo.setEnabled(not checked)
        self.autoUpdatePreview()

    def onProxyResOverrideToggled(self, checked):
        self.proxyResEdit.setVisible(checked)
        self.proxyResCombo.setEnabled(not checked)
        self.autoUpdatePreview()

    def onColorspaceOverrideToggled(self, checked):
        self.colorspaceEdit.setVisible(checked)
        self.colorspaceCombo.setEnabled(not checked)
        if not checked:
            self.onColorspaceChanged()
        self.autoUpdatePreview()

    def onGammaOverrideToggled(self, checked):
        self.gammaEdit.setVisible(checked)
        self.gammaCombo.setEnabled(not checked)
        if not checked:
            self.onExtensionChanged()
            self.onColorspaceChanged()
        self.autoUpdatePreview()

    def onVersionOverrideToggled(self, checked):
        self.versionEdit.setVisible(checked)
        self.autoUpdatePreview()

    def onExtensionOverrideToggled(self, checked):
        self.extensionEdit.setVisible(checked)
        self.extensionCombo.setEnabled(not checked)
        if not checked:
            self.onExtensionChanged()
        self.autoUpdatePreview()

    def onExtensionChanged(self):
        if not self.template_data:
            return
        if self.overrideExtensionCheck.isChecked():
            return

        ext = self.extensionCombo.currentText().lower()
        if not self.overrideColorspaceCheck.isChecked() or not self.overrideGammaCheck.isChecked():
            if ext in ["mov", "mp4"]:
                if not self.overrideColorspaceCheck.isChecked():
                    idx = self.colorspaceCombo.findText("rec709", QtCore.Qt.MatchFixedString)
                    if idx >= 0:
                        self.colorspaceCombo.setCurrentIndex(idx)
                if not self.overrideGammaCheck.isChecked():
                    idxg = self.gammaCombo.findText("g24", QtCore.Qt.MatchFixedString)
                    if idxg >= 0:
                        self.gammaCombo.setCurrentIndex(idxg)
            elif ext in ["jpg", "png", "tif", "tiff"]:
                if not self.overrideColorspaceCheck.isChecked():
                    idx = self.colorspaceCombo.findText("sRGB", QtCore.Qt.MatchFixedString)
                    if idx >= 0:
                        self.colorspaceCombo.setCurrentIndex(idx)
                if not self.overrideGammaCheck.isChecked():
                    idxg = self.gammaCombo.findText("g22", QtCore.Qt.MatchFixedString)
                    if idxg >= 0:
                        self.gammaCombo.setCurrentIndex(idxg)
            elif ext == "exr":
                if not self.overrideColorspaceCheck.isChecked():
                    idx = self.colorspaceCombo.findText("acescg", QtCore.Qt.MatchFixedString)
                    if idx >= 0:
                        self.colorspaceCombo.setCurrentIndex(idx)
                if not self.overrideGammaCheck.isChecked():
                    idxg = self.gammaCombo.findText("lin", QtCore.Qt.MatchFixedString)
                    if idxg >= 0:
                        self.gammaCombo.setCurrentIndex(idxg)
        self.onColorspaceChanged()

    def onColorspaceChanged(self):
        if not self.template_data:
            return
        if self.overrideColorspaceCheck.isChecked():
            return

        cspace = self.colorspaceCombo.currentText().lower()
        if not self.overrideGammaCheck.isChecked():
            if cspace == "rec709":
                idx = self.gammaCombo.findText("g24", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.gammaCombo.setCurrentIndex(idx)
            elif cspace == "srgb":
                idx = self.gammaCombo.findText("g22", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.gammaCombo.setCurrentIndex(idx)
            elif cspace == "acescg":
                idx = self.gammaCombo.findText("lin", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.gammaCombo.setCurrentIndex(idx)
        
        self.autoUpdatePreview()

    def browseBaseDir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Base Directory",
            self.script_dir
        )
        if directory:
            directory = os.path.normpath(directory)
            self.baseDirEdit.setText(directory)

    def loadSelectedTemplate(self, index):
        selected_file = self.templateSelectCombo.itemText(index)
        self.template_data = self.templates_data[selected_file]

        # Update the template name label
        tmpl_name = self.template_data.get("templateName", selected_file)
        self.templateNameLabel.setText(tmpl_name)

        # Get the tags dictionary from the template
        tags = self.template_data.get("tags", {})

        # --- Sequence ---
        if "sequence" in tags:
            self.sequenceRow.setVisible(True)
            seq_info = tags.get("sequence", {})
            seq_allowed = seq_info.get("allowed", [])
            self.sequenceCombo.clear()
            self.sequenceCombo.addItems(seq_allowed)
            seq_default = seq_info.get("default", "")
            if seq_default in seq_allowed:
                self.sequenceCombo.setCurrentText(seq_default)
            elif seq_allowed:
                self.sequenceCombo.setCurrentIndex(0)
        else:
            self.sequenceRow.setVisible(False)

        # --- Shot Number ---
        if "shotNumber" in tags:
            self.shotNumberRow.setVisible(True)
            shot_info = tags.get("shotNumber", {})
            shot_default = shot_info.get("default", "0010")
            self.shotNumberEdit.setText(shot_default)
        else:
            self.shotNumberRow.setVisible(False)

        # --- Description ---
        if "description" in tags:
            self.descriptionRow.setVisible(True)
            desc_info = tags.get("description", {})
            desc_allowed = desc_info.get("allowed", [])
            self.descriptionCombo.clear()
            self.descriptionCombo.addItems(desc_allowed)
        else:
            self.descriptionRow.setVisible(False)

        # --- Pixel Mapping ---
        if "pixelMappingName" in tags:
            self.pixelMappingRow.setVisible(True)
            pxm_info = tags.get("pixelMappingName", {})
            pxm_allowed = pxm_info.get("allowed", [])
            self.pixelMappingCombo.clear()
            self.pixelMappingCombo.addItems(pxm_allowed)
        else:
            self.pixelMappingRow.setVisible(False)

        # --- Resolution (Full & Proxy) ---
        if "resolution" in tags:
            self.fullResRow.setVisible(True)
            self.proxyResRow.setVisible(True)
            res_info = tags.get("resolution", {})
            res_allowed = res_info.get("allowed", [])
            self.fullResCombo.clear()
            self.fullResCombo.addItems(res_allowed)
            self.proxyResCombo.clear()
            self.proxyResCombo.addItems(res_allowed)
        else:
            self.fullResRow.setVisible(False)
            self.proxyResRow.setVisible(False)

        # --- Colorspace ---
        if "colorspace" in tags:
            self.colorspaceRow.setVisible(True)
            cspace_info = tags.get("colorspace", {})
            cspace_allowed = cspace_info.get("allowed", [])
            self.colorspaceCombo.clear()
            self.colorspaceCombo.addItems(cspace_allowed)
        else:
            self.colorspaceRow.setVisible(False)

        # --- Gamma ---
        if "gamma" in tags:
            self.gammaRow.setVisible(True)
            gamma_info = tags.get("gamma", {})
            gamma_allowed = gamma_info.get("allowed", [])
            self.gammaCombo.clear()
            self.gammaCombo.addItems(gamma_allowed)
        else:
            self.gammaRow.setVisible(False)

        # --- FPS ---
        if "fps" in tags:
            self.fpsRow.setVisible(True)
            fps_info = tags.get("fps", {})
            fps_allowed = fps_info.get("allowed", [])
            self.fpsCombo.clear()
            self.fpsCombo.addItems(fps_allowed)
            default_fps = fps_info.get("default", None)
            if default_fps and default_fps in fps_allowed:
                self.fpsCombo.setCurrentText(default_fps)
        else:
            self.fpsRow.setVisible(False)

        # --- Frame Padding ---
        if "frame_padding" in tags:
            self.framePaddingRow.setVisible(True)
            fpad_info = tags.get("frame_padding", {})
            frame_pad_default = fpad_info.get("default", "4")
            self.framePaddingEdit.setText(frame_pad_default)
        else:
            self.framePaddingRow.setVisible(False)

        # --- Extension ---
        if "extension" in tags:
            self.extensionRow.setVisible(True)
            ext_info = tags.get("extension", {})
            ext_allowed = ext_info.get("allowed", [])
            self.extensionCombo.clear()
            self.extensionCombo.addItems(ext_allowed)
        else:
            self.extensionRow.setVisible(False)

        # Clear previews and update
        self.previewFullEdit.clear()
        self.previewProxyEdit.clear()
        self.autoUpdatePreview()

    def updatePreview(self):
        if not self.template_data:
            nuke.message("No template loaded.")
            return

        # Run extension logic to auto-set colorspace/gamma
        self.onExtensionChanged()

        # --- Gather Field Values ---
        # Sequence
        if self.overrideSequenceCheck.isChecked():
            sequence = self.sequenceEdit.text()
        else:
            sequence = self.sequenceCombo.currentText()

        # Shot Number (auto-increment removed; using value as-is)
        shotNumber = self.shotNumberEdit.text()

        # Description
        if self.overrideDescriptionCheck.isChecked():
            description = self.descriptionEdit.text()
            if not re.match(r'^[a-z][a-zA-Z0-9_]*$', description):
                QtWidgets.QMessageBox.warning(
                    self, "Invalid Description",
                    "Use camelCase or underscores only (no spaces/other chars)."
                )
                return
        else:
            description = self.descriptionCombo.currentText()

        # Pixel Mapping
        if self.overridePixelMappingCheck.isChecked():
            pixelMapping = self.pixelMappingEdit.text()
        else:
            pixelMapping = self.pixelMappingCombo.currentText()

        # Full Resolution
        if self.overrideFullResCheck.isChecked():
            fullRes = self.fullResEdit.text()
        else:
            fullRes = self.fullResCombo.currentText()

        # Proxy Resolution
        if self.overrideProxyResCheck.isChecked():
            proxyRes = self.proxyResEdit.text()
        else:
            proxyRes = self.proxyResCombo.currentText()

        # Colorspace (for filename)
        if self.overrideColorspaceCheck.isChecked():
            self.finalColorspace = self.colorspaceEdit.text()
        else:
            self.finalColorspace = self.colorspaceCombo.currentText()

        # Gamma
        if self.overrideGammaCheck.isChecked():
            gamma = self.gammaEdit.text()
        else:
            gamma = self.gammaCombo.currentText()

        # FPS
        fps = self.fpsCombo.currentText()

        # Version
        if self.overrideVersionCheck.isChecked():
            version = self.versionEdit.text()
        else:
            version = self.defaultVersion
            
        if self.autoIncrementVersionCheck.isChecked():
            m = re.match(r'v(\d+)', version)
            if m:
                num = int(m.group(1)) + 1
                version = "v" + str(num).zfill(len(m.group(1)))
                self.versionEdit.setText(version)

        # Frame Padding
        framePadding = self.framePaddingEdit.text()
        try:
            int(framePadding)
        except:
            QtWidgets.QMessageBox.warning(
                self, "Frame Padding Error",
                "Frame Padding must be an integer."
            )
            return

        # Extension
        if self.overrideExtensionCheck.isChecked():
            extension = self.extensionEdit.text()
        else:
            extension = self.extensionCombo.currentText()

        # Build the base filename using the template string
        template_str = self.template_data["templateString"]

        filenameFull = template_str.replace("<sequence>", sequence)\
            .replace("<shotNumber>", shotNumber)\
            .replace("<description>", description)\
            .replace("<pixelMappingName>", pixelMapping)\
            .replace("<resolution>", fullRes)\
            .replace("<colorspace>", self.finalColorspace)\
            .replace("<gamma>", gamma)\
            .replace("<fps>", fps)\
            .replace("<version>", version)\
            .replace("<frame_padding>", "%" + "0{}d".format(framePadding))\
            .replace("<extension>", extension)

        filenameProxy = template_str.replace("<sequence>", sequence)\
            .replace("<shotNumber>", shotNumber)\
            .replace("<description>", description)\
            .replace("<pixelMappingName>", pixelMapping)\
            .replace("<resolution>", proxyRes)\
            .replace("<colorspace>", self.finalColorspace)\
            .replace("<gamma>", gamma)\
            .replace("<fps>", fps)\
            .replace("<version>", version)\
            .replace("<frame_padding>", "%" + "0{}d".format(framePadding))\
            .replace("<extension>", extension)

        baseDir = os.path.normpath(self.baseDirEdit.text())
        if not baseDir:
            # Don't show error during auto-updates, just clear preview
            self.previewFullEdit.clear()
            self.previewProxyEdit.clear()
            return

        # Build full paths
        fullPath = os.path.normpath(os.path.join(baseDir, version, fullRes, filenameFull))
        proxyPath = os.path.normpath(os.path.join(baseDir, version, proxyRes, filenameProxy))

        self.previewFullEdit.setPlainText(fullPath)
        self.previewProxyEdit.setPlainText(proxyPath)

        # Adjust node colorspace if using an ACES OCIO config
        config_name = nuke.root()["OCIO_config"].value() if "OCIO_config" in nuke.root().knobs() else ""
        self.finalNodeColorspace = self.finalColorspace  # default
        if "aces" in config_name.lower():
            cspace_l = self.finalColorspace.lower()
            if cspace_l == "srgb":
                self.finalNodeColorspace = "Output - sRGB"
            elif cspace_l == "rec709":
                self.finalNodeColorspace = "Output - Rec.709"
            elif cspace_l == "acescg":
                self.finalNodeColorspace = "scene_linear (ACES - ACEScg)"
                
    def createWriteNode(self):
        """Creates a single Write node with full-resolution and proxy paths."""
        self.updatePreview()  # Ensure preview is up to date

        fullPath = self.previewFullEdit.toPlainText()
        proxyPath = self.previewProxyEdit.toPlainText()
        if not fullPath or not proxyPath:
            QtWidgets.QMessageBox.warning(
                self, "Error",
                "Preview paths are empty. Check your inputs."
            )
            return

        # Make directories if needed
        for path_dir in [os.path.dirname(fullPath), os.path.dirname(proxyPath)]:
            if not os.path.exists(path_dir):
                try:
                    os.makedirs(path_dir)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(
                        self, "Directory Error",
                        f"Could not create directory {path_dir}:\n{e}"
                    )
                    return

        # Create one Write node
        writeNode = nuke.createNode("Write", inpanel=False)
        writeNode["file"].setValue(fullPath)
        writeNode["proxy"].setValue(proxyPath)
        # finalNodeColorspace is adjusted if ACES config is found
        writeNode["colorspace"].setValue(self.finalNodeColorspace)

        nuke.message(f"Write node created:\nFull: {fullPath}\nProxy: {proxyPath}")
        self.accept()

    def saveSettings(self):
        """Save the current UI selections to a JSON file in the same folder as the script."""
        self.updatePreview()  # Make sure we have the latest data

        # Let user choose a file name; default to script folder
        default_save_path = os.path.join(self.script_dir, "custom_settings.json")
        chosen_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Settings as JSON",
            default_save_path,
            "JSON Files (*.json)"
        )
        if not chosen_path:
            return  # user canceled

        # Gather the current selections
        settings = {}
        settings["templateFile"] = self.templateSelectCombo.currentText()
        settings["baseDirectory"] = self.baseDirEdit.text()
        settings["sequence"] = self.sequenceEdit.text() if self.overrideSequenceCheck.isChecked() else self.sequenceCombo.currentText()
        settings["shotNumber"] = self.shotNumberEdit.text()
        settings["description"] = self.descriptionEdit.text() if self.overrideDescriptionCheck.isChecked() else self.descriptionCombo.currentText()
        settings["pixelMapping"] = self.pixelMappingEdit.text() if self.overridePixelMappingCheck.isChecked() else self.pixelMappingCombo.currentText()
        settings["fullResolution"] = self.fullResEdit.text() if self.overrideFullResCheck.isChecked() else self.fullResCombo.currentText()
        settings["proxyResolution"] = self.proxyResEdit.text() if self.overrideProxyResCheck.isChecked() else self.proxyResCombo.currentText()
        settings["colorspace"] = self.finalColorspace
        settings["gamma"] = self.gammaEdit.text() if self.overrideGammaCheck.isChecked() else self.gammaCombo.currentText()
        settings["fps"] = self.fpsCombo.currentText()
        settings["version"] = self.versionEdit.text() if self.overrideVersionCheck.isChecked() else self.defaultVersion
        settings["framePadding"] = self.framePaddingEdit.text()
        settings["extension"] = self.extensionEdit.text() if self.overrideExtensionCheck.isChecked() else self.extensionCombo.currentText()

        settings["autoIncrementVersion"] = self.autoIncrementVersionCheck.isChecked()

        # Write to chosen JSON
        try:
            with open(chosen_path, "w") as outfile:
                json.dump(settings, outfile, indent=4)
            nuke.message(f"Settings saved to:\n{chosen_path}")
        except Exception as e:
            nuke.message(f"Error saving JSON:\n{e}")
            
    def loadSettings(self):
        """Load previously saved settings from a JSON file, and restore them in the UI."""
        # Default to script folder
        default_load_path = os.path.join(self.script_dir, "custom_settings.json")
        chosen_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Settings from JSON",
            default_load_path,
            "JSON Files (*.json)"
        )
        if not chosen_path:
            return  # user canceled

        # Parse JSON
        try:
            with open(chosen_path, "r") as infile:
                settings = json.load(infile)
        except Exception as e:
            nuke.message(f"Error loading JSON:\n{e}")
            return

        # 1) templateFile => set the template combo
        template_file = settings.get("templateFile", "")
        idx = self.templateSelectCombo.findText(template_file)
        if idx >= 0:
            self.templateSelectCombo.setCurrentIndex(idx)

        # 2) baseDirectory
        base_dir = settings.get("baseDirectory", "")
        if base_dir:
            self.baseDirEdit.setText(base_dir)

        # 3) sequence
        seq_val = settings.get("sequence", "")
        if seq_val:
            seq_info = self.template_data["tags"].get("sequence", {})
            seq_allowed = seq_info.get("allowed", [])
            if seq_val in seq_allowed:
                self.overrideSequenceCheck.setChecked(False)
                self.sequenceCombo.setCurrentText(seq_val)
            else:
                self.overrideSequenceCheck.setChecked(True)
                self.sequenceEdit.setText(seq_val)

        # 4) shotNumber
        self.shotNumberEdit.setText(settings.get("shotNumber", "0010"))

        # 5) description
        desc_val = settings.get("description", "")
        if desc_val:
            desc_info = self.template_data["tags"].get("description", {})
            desc_allowed = desc_info.get("allowed", [])
            if desc_val in desc_allowed:
                self.overrideDescriptionCheck.setChecked(False)
                self.descriptionCombo.setCurrentText(desc_val)
            else:
                self.overrideDescriptionCheck.setChecked(True)
                self.descriptionEdit.setText(desc_val)

        # 6) pixelMapping
        pxm_val = settings.get("pixelMapping", "")
        if pxm_val:
            pxm_info = self.template_data["tags"].get("pixelMappingName", {})
            pxm_allowed = pxm_info.get("allowed", [])
            if pxm_val in pxm_allowed:
                self.overridePixelMappingCheck.setChecked(False)
                self.pixelMappingCombo.setCurrentText(pxm_val)
            else:
                self.overridePixelMappingCheck.setChecked(True)
                self.pixelMappingEdit.setText(pxm_val)

        # 7) fullResolution
        full_res_val = settings.get("fullResolution", "")
        if full_res_val:
            res_info = self.template_data["tags"].get("resolution", {})
            res_allowed = res_info.get("allowed", [])
            if full_res_val in res_allowed:
                self.overrideFullResCheck.setChecked(False)
                self.fullResCombo.setCurrentText(full_res_val)
            else:
                self.overrideFullResCheck.setChecked(True)
                self.fullResEdit.setText(full_res_val)

        # 8) proxyResolution
        proxy_res_val = settings.get("proxyResolution", "")
        if proxy_res_val:
            if proxy_res_val in res_allowed:
                self.overrideProxyResCheck.setChecked(False)
                self.proxyResCombo.setCurrentText(proxy_res_val)
            else:
                self.overrideProxyResCheck.setChecked(True)
                self.proxyResEdit.setText(proxy_res_val)

        # 9) colorspace
        cspace_val = settings.get("colorspace", "sRGB")
        if cspace_val:
            cspace_info = self.template_data["tags"].get("colorspace", {})
            cspace_allowed = cspace_info.get("allowed", [])
            if cspace_val in cspace_allowed:
                self.overrideColorspaceCheck.setChecked(False)
                self.colorspaceCombo.setCurrentText(cspace_val)
            else:
                self.overrideColorspaceCheck.setChecked(True)
                self.colorspaceEdit.setText(cspace_val)

        # 10) gamma
        gamma_val = settings.get("gamma", "g22")
        if gamma_val:
            gamma_info = self.template_data["tags"].get("gamma", {})
            gamma_allowed = gamma_info.get("allowed", [])
            if gamma_val in gamma_allowed:
                self.overrideGammaCheck.setChecked(False)
                self.gammaCombo.setCurrentText(gamma_val)
            else:
                self.overrideGammaCheck.setChecked(True)
                self.gammaEdit.setText(gamma_val)

        # 11) fps
        self.fpsCombo.setCurrentText(settings.get("fps", "2997"))

        # 12) version
        self.autoIncrementVersionCheck.setChecked(settings.get("autoIncrementVersion", False))
        version_val = settings.get("version", self.defaultVersion)
        if version_val != self.defaultVersion:
            self.overrideVersionCheck.setChecked(True)
            self.versionEdit.setText(version_val)
        else:
            self.overrideVersionCheck.setChecked(False)

        # 13) framePadding
        self.framePaddingEdit.setText(settings.get("framePadding", "4"))

        # 14) extension
        ext_val = settings.get("extension", "exr")
        if ext_val:
            ext_info = self.template_data["tags"].get("extension", {})
            ext_allowed = ext_info.get("allowed", [])
            if ext_val in ext_allowed:
                self.overrideExtensionCheck.setChecked(False)
                self.extensionCombo.setCurrentText(ext_val)
            else:
                self.overrideExtensionCheck.setChecked(True)
                self.extensionEdit.setText(ext_val)

        # Refresh previews
        self.autoUpdatePreview()


def main():
    dialog = WriteNodeKENTDialog()
    dialog.exec_()

if __name__ == '__main__':
    main()
