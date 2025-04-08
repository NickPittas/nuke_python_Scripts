import os
import json
import re
import nuke

# Determine Nuke version and import the appropriate Qt module.
try:
    nuke_version = int(nuke.NUKE_VERSION_MAJOR)
except Exception:
    nuke_version = 15  # Default fallback.

if nuke_version >= 16:
    from PySide6 import QtWidgets, QtCore
else:
    from PySide2 import QtWidgets, QtCore

class WriteNodeKENTDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(WriteNodeKENTDialog, self).__init__(parent)
        self.setWindowTitle("Write Node KENT")
        self.setMinimumWidth(620)

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

        # Determine default version from the current Nuke script (e.g., v001).
        script_name = nuke.root().name()
        match = re.search(r'v(\d{3,})', script_name)
        self.defaultVersion = "v" + match.group(1) if match else "v001"

        # Will store the currently selected template’s data here
        self.template_data = None

        # The final colorspace string used for naming. This might be "acescg", "srgb", etc.
        self.finalColorspace = "sRGB"
        # The final colorspace actually assigned to the Nuke node if ACES config is detected
        self.finalNodeColorspace = "sRGB"

        self.initUI()

    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        formLayout = QtWidgets.QFormLayout()

        #
        # 1) Template Selection
        #
        self.templateSelectCombo = QtWidgets.QComboBox()
        self.templateSelectCombo.addItems(self.template_files)
        self.templateSelectCombo.currentIndexChanged.connect(self.loadSelectedTemplate)
        formLayout.addRow("Select Template:", self.templateSelectCombo)

        self.templateNameLabel = QtWidgets.QLabel("No template loaded yet")
        formLayout.addRow("Template Name:", self.templateNameLabel)

        #
        # 2) Sequence: dropdown + override
        #
        self.sequenceCombo = QtWidgets.QComboBox()
        self.overrideSequenceCheck = QtWidgets.QCheckBox("Override Sequence")
        self.sequenceEdit = QtWidgets.QLineEdit()
        self.sequenceEdit.setVisible(False)
        self.overrideSequenceCheck.toggled.connect(self.onSequenceOverrideToggled)

        formLayout.addRow("Sequence (from JSON):", self.sequenceCombo)
        formLayout.addRow(self.overrideSequenceCheck, self.sequenceEdit)

        #
        # 3) Shot Number & Auto-Increment
        #
        self.shotNumberEdit = QtWidgets.QLineEdit()
        self.autoIncrementShotCheck = QtWidgets.QCheckBox("Auto Increment Shot Number")
        formLayout.addRow("Shot Number:", self.shotNumberEdit)
        formLayout.addRow(self.autoIncrementShotCheck)

        #
        # 4) Description
        #
        self.descriptionCombo = QtWidgets.QComboBox()
        self.overrideDescriptionCheck = QtWidgets.QCheckBox("Override Description")
        self.descriptionEdit = QtWidgets.QLineEdit()
        self.descriptionEdit.setVisible(False)
        self.overrideDescriptionCheck.toggled.connect(self.onDescriptionOverrideToggled)

        formLayout.addRow("Description (Default):", self.descriptionCombo)
        formLayout.addRow(self.overrideDescriptionCheck, self.descriptionEdit)

        #
        # 5) Pixel Mapping
        #
        self.pixelMappingCombo = QtWidgets.QComboBox()
        self.overridePixelMappingCheck = QtWidgets.QCheckBox("Override Pixel Mapping")
        self.pixelMappingEdit = QtWidgets.QLineEdit()
        self.pixelMappingEdit.setVisible(False)
        self.overridePixelMappingCheck.toggled.connect(self.onPixelMappingOverrideToggled)

        formLayout.addRow("Pixel Mapping Name:", self.pixelMappingCombo)
        formLayout.addRow(self.overridePixelMappingCheck, self.pixelMappingEdit)

        #
        # 6) Full Resolution
        #
        self.fullResCombo = QtWidgets.QComboBox()
        self.overrideFullResCheck = QtWidgets.QCheckBox("Override Full Res")
        self.fullResEdit = QtWidgets.QLineEdit()
        self.fullResEdit.setVisible(False)
        self.overrideFullResCheck.toggled.connect(self.onFullResOverrideToggled)

        formLayout.addRow("Full Resolution:", self.fullResCombo)
        formLayout.addRow(self.overrideFullResCheck, self.fullResEdit)

        #
        # 7) Proxy Resolution
        #
        self.proxyResCombo = QtWidgets.QComboBox()
        self.overrideProxyResCheck = QtWidgets.QCheckBox("Override Proxy Res")
        self.proxyResEdit = QtWidgets.QLineEdit()
        self.proxyResEdit.setVisible(False)
        self.overrideProxyResCheck.toggled.connect(self.onProxyResOverrideToggled)

        formLayout.addRow("Proxy Resolution:", self.proxyResCombo)
        formLayout.addRow(self.overrideProxyResCheck, self.proxyResEdit)

        #
        # 8) Colorspace
        #
        self.colorspaceCombo = QtWidgets.QComboBox()
        # If user changes the combo, we might auto-change gamma (unless gamma override is checked).
        self.colorspaceCombo.currentIndexChanged.connect(self.onColorspaceChanged)

        self.overrideColorspaceCheck = QtWidgets.QCheckBox("Override Colorspace")
        self.colorspaceEdit = QtWidgets.QLineEdit()
        self.colorspaceEdit.setVisible(False)
        self.overrideColorspaceCheck.toggled.connect(self.onColorspaceOverrideToggled)

        formLayout.addRow("Colorspace:", self.colorspaceCombo)
        formLayout.addRow(self.overrideColorspaceCheck, self.colorspaceEdit)

        #
        # 9) Gamma
        #
        self.gammaCombo = QtWidgets.QComboBox()
        self.overrideGammaCheck = QtWidgets.QCheckBox("Override Gamma")
        self.gammaEdit = QtWidgets.QLineEdit()
        self.gammaEdit.setVisible(False)
        self.overrideGammaCheck.toggled.connect(self.onGammaOverrideToggled)

        formLayout.addRow("Gamma:", self.gammaCombo)
        formLayout.addRow(self.overrideGammaCheck, self.gammaEdit)

        #
        # 10) FPS
        #
        self.fpsCombo = QtWidgets.QComboBox()
        formLayout.addRow("FPS:", self.fpsCombo)

        #
        # 11) Version & Auto-Increment
        #
        self.versionEdit = QtWidgets.QLineEdit(self.defaultVersion)
        self.overrideVersionCheck = QtWidgets.QCheckBox("Override Version")
        self.overrideVersionCheck.toggled.connect(self.onVersionOverrideToggled)
        self.versionEdit.setVisible(False)

        self.autoIncrementVersionCheck = QtWidgets.QCheckBox("Auto Increment Version")
        formLayout.addRow("Version:", self.autoIncrementVersionCheck)
        formLayout.addRow(self.overrideVersionCheck, self.versionEdit)

        #
        # 12) Frame Padding
        #
        self.framePaddingEdit = QtWidgets.QLineEdit()
        formLayout.addRow("Frame Padding:", self.framePaddingEdit)

        #
        # 13) Extension
        #
        self.extensionCombo = QtWidgets.QComboBox()
        # If user changes extension => auto-set rec709/g24, sRGB/g22, acescg/lin, etc. if not overridden
        self.extensionCombo.currentIndexChanged.connect(self.onExtensionChanged)

        self.overrideExtensionCheck = QtWidgets.QCheckBox("Override Extension")
        self.extensionEdit = QtWidgets.QLineEdit()
        self.extensionEdit.setVisible(False)
        self.overrideExtensionCheck.toggled.connect(self.onExtensionOverrideToggled)

        formLayout.addRow("Extension:", self.extensionCombo)
        formLayout.addRow(self.overrideExtensionCheck, self.extensionEdit)

        #
        # 14) Base Directory
        #
        self.baseDirEdit = QtWidgets.QLineEdit()
        self.baseDirButton = QtWidgets.QPushButton("Browse")
        self.baseDirButton.clicked.connect(self.browseBaseDir)
        baseDirLayout = QtWidgets.QHBoxLayout()
        baseDirLayout.addWidget(self.baseDirEdit)
        baseDirLayout.addWidget(self.baseDirButton)
        formLayout.addRow("Base Directory:", baseDirLayout)

        #
        # 15) Preview Fields
        #
        self.previewFullEdit = QtWidgets.QTextEdit()
        self.previewFullEdit.setReadOnly(True)
        self.previewProxyEdit = QtWidgets.QTextEdit()
        self.previewProxyEdit.setReadOnly(True)
        formLayout.addRow("Full Resolution Preview:", self.previewFullEdit)
        formLayout.addRow("Proxy Resolution Preview:", self.previewProxyEdit)

        layout.addLayout(formLayout)

        #
        # 16) Buttons (Update, Load, Save, Create, Cancel)
        #
        buttonLayout = QtWidgets.QHBoxLayout()

        self.updatePreviewButton = QtWidgets.QPushButton("Update Preview")
        self.updatePreviewButton.clicked.connect(self.updatePreview)

        self.loadSettingsButton = QtWidgets.QPushButton("Load Settings")
        self.loadSettingsButton.clicked.connect(self.loadSettings)

        self.saveSettingsButton = QtWidgets.QPushButton("Save Settings")
        self.saveSettingsButton.clicked.connect(self.saveSettings)

        self.createNodesButton = QtWidgets.QPushButton("Create Write Node")
        self.createNodesButton.clicked.connect(self.createWriteNode)

        self.cancelButton = QtWidgets.QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)

        buttonLayout.addWidget(self.updatePreviewButton)
        buttonLayout.addWidget(self.loadSettingsButton)
        buttonLayout.addWidget(self.saveSettingsButton)
        buttonLayout.addWidget(self.createNodesButton)
        buttonLayout.addWidget(self.cancelButton)
        layout.addLayout(buttonLayout)

        #
        # Load the first template by default
        #
        self.templateSelectCombo.setCurrentIndex(0)
        self.loadSelectedTemplate(0)

    # -------------------------------------------------------------------------
    # Override checkbox toggles: show/hide the text fields
    # -------------------------------------------------------------------------
    def onSequenceOverrideToggled(self, checked):
        self.sequenceEdit.setVisible(checked)
        self.sequenceCombo.setEnabled(not checked)

    def onDescriptionOverrideToggled(self, checked):
        self.descriptionEdit.setVisible(checked)
        self.descriptionCombo.setEnabled(not checked)

    def onPixelMappingOverrideToggled(self, checked):
        self.pixelMappingEdit.setVisible(checked)
        self.pixelMappingCombo.setEnabled(not checked)

    def onFullResOverrideToggled(self, checked):
        self.fullResEdit.setVisible(checked)
        self.fullResCombo.setEnabled(not checked)

    def onProxyResOverrideToggled(self, checked):
        self.proxyResEdit.setVisible(checked)
        self.proxyResCombo.setEnabled(not checked)

    def onColorspaceOverrideToggled(self, checked):
        self.colorspaceEdit.setVisible(checked)
        self.colorspaceCombo.setEnabled(not checked)
        # If the user unchecks override, re-run the auto gamma logic
        if not checked:
            self.onColorspaceChanged()

    def onGammaOverrideToggled(self, checked):
        self.gammaEdit.setVisible(checked)
        self.gammaCombo.setEnabled(not checked)
        # If the user unchecks override, re-run the auto logic
        if not checked:
            self.onExtensionChanged()
            self.onColorspaceChanged()

    def onVersionOverrideToggled(self, checked):
        self.versionEdit.setVisible(checked)

    def onExtensionOverrideToggled(self, checked):
        self.extensionEdit.setVisible(checked)
        self.extensionCombo.setEnabled(not checked)
        # If user unchecks override, auto-set rec709/g24, etc.
        if not checked:
            self.onExtensionChanged()

    # -------------------------------------------------------------------------
    # Template loading
    # -------------------------------------------------------------------------
    def loadSelectedTemplate(self, index):
        """Loads the JSON data for the currently selected template
        and updates the UI defaults accordingly."""
        selected_file = self.templateSelectCombo.itemText(index)
        self.template_data = self.templates_data[selected_file]

        # Template name label
        tmpl_name = self.template_data.get("templateName", selected_file)
        self.templateNameLabel.setText(tmpl_name)

        #
        # Sequence from JSON
        #
        seq_info = self.template_data["tags"].get("sequence", {})
        seq_allowed = seq_info.get("allowed", [])
        self.sequenceCombo.clear()
        self.sequenceCombo.addItems(seq_allowed)
        seq_default = seq_info.get("default", "")
        if seq_default in seq_allowed:
            self.sequenceCombo.setCurrentText(seq_default)
        elif seq_allowed:
            self.sequenceCombo.setCurrentIndex(0)

        #
        # Shot Number
        #
        shot_info = self.template_data["tags"].get("shotNumber", {})
        shot_default = shot_info.get("default", "0010")
        self.shotNumberEdit.setText(shot_default)

        #
        # Description
        #
        desc_info = self.template_data["tags"].get("description", {})
        desc_allowed = desc_info.get("allowed", [])
        self.descriptionCombo.clear()
        self.descriptionCombo.addItems(desc_allowed)

        #
        # Pixel Mapping
        #
        pxm_info = self.template_data["tags"].get("pixelMappingName", {})
        pxm_allowed = pxm_info.get("allowed", [])
        self.pixelMappingCombo.clear()
        self.pixelMappingCombo.addItems(pxm_allowed)

        #
        # Resolution (Full + Proxy use the same allowed list)
        #
        res_info = self.template_data["tags"].get("resolution", {})
        res_allowed = res_info.get("allowed", [])
        self.fullResCombo.clear()
        self.fullResCombo.addItems(res_allowed)
        self.proxyResCombo.clear()
        self.proxyResCombo.addItems(res_allowed)

        #
        # Colorspace
        #
        cspace_info = self.template_data["tags"].get("colorspace", {})
        cspace_allowed = cspace_info.get("allowed", [])
        self.colorspaceCombo.clear()
        self.colorspaceCombo.addItems(cspace_allowed)

        #
        # Gamma
        #
        gamma_info = self.template_data["tags"].get("gamma", {})
        gamma_allowed = gamma_info.get("allowed", [])
        self.gammaCombo.clear()
        self.gammaCombo.addItems(gamma_allowed)

        #
        # FPS
        #
        fps_info = self.template_data["tags"].get("fps", {})
        fps_allowed = fps_info.get("allowed", [])
        self.fpsCombo.clear()
        self.fpsCombo.addItems(fps_allowed)
        # Possibly set a default if there's one
        default_fps = fps_info.get("default", None)
        if default_fps and default_fps in fps_allowed:
            self.fpsCombo.setCurrentText(default_fps)

        #
        # Frame Padding
        #
        fpad_info = self.template_data["tags"].get("frame_padding", {})
        frame_pad_default = fpad_info.get("default", "4")
        self.framePaddingEdit.setText(frame_pad_default)

        #
        # Extension
        #
        ext_info = self.template_data["tags"].get("extension", {})
        ext_allowed = ext_info.get("allowed", [])
        self.extensionCombo.clear()
        self.extensionCombo.addItems(ext_allowed)

        #
        # Clear previews
        #
        self.previewFullEdit.clear()
        self.previewProxyEdit.clear()

    # -------------------------------------------------------------------------
    # Auto-logic for colorspace/gamma based on extension & colorspace
    # -------------------------------------------------------------------------
    def onExtensionChanged(self):
        """
        Immediately set colorspace & gamma for typical formats if not overridden:
          - mov/mp4 => rec709/g24
          - jpg, png, tif, tiff => sRGB/g22
          - exr => acescg/lin
        """
        if not self.template_data:
            return
        if self.overrideExtensionCheck.isChecked():
            return  # user is overriding extension

        ext = self.extensionCombo.currentText().lower()
        if not self.overrideColorspaceCheck.isChecked() or not self.overrideGammaCheck.isChecked():
            # We'll do auto sets only if the user is not overriding them
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

        # Also re-run colorspace logic in case we just changed it
        self.onColorspaceChanged()

    def onColorspaceChanged(self):
        """
        If colorspace changes to rec709 => gamma g24,
        sRGB => g22, acescg => lin, unless gamma is overridden.
        """
        if not self.template_data:
            return
        if self.overrideColorspaceCheck.isChecked():
            return  # user is overriding colorspace

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
            else:
                # do nothing if unknown
                pass

    # -------------------------------------------------------------------------
    # Browsing base directory
    # -------------------------------------------------------------------------
    def browseBaseDir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Base Directory",
            self.script_dir  # default to script folder
        )
        if directory:
            directory = os.path.normpath(directory)
            self.baseDirEdit.setText(directory)

    # -------------------------------------------------------------------------
    # Update Preview
    # -------------------------------------------------------------------------
    def updatePreview(self):
        """
        Gathers user inputs, applies auto-changes for extension => colorspace/gamma,
        checks if root.OCIO_config contains 'aces' => remap finalColorspace => finalNodeColorspace,
        and then shows the final paths in the preview fields.
        """
        if not self.template_data:
            nuke.message("No template loaded.")
            return

        # Run extension logic first so we can auto-set colorspace/gamma
        self.onExtensionChanged()

        # 1) Sequence
        if self.overrideSequenceCheck.isChecked():
            sequence = self.sequenceEdit.text()
        else:
            sequence = self.sequenceCombo.currentText()

        # 2) Shot Number + Auto-Increment
        shotNumber = self.shotNumberEdit.text()
        shot_info = self.template_data["tags"].get("shotNumber", {})
        increment_val = shot_info.get("increment", 10)
        if self.autoIncrementShotCheck.isChecked():
            try:
                shot_int = int(shotNumber)
                shot_int += increment_val
                shotNumber = str(shot_int).zfill(4)
                self.shotNumberEdit.setText(shotNumber)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Shot Number Error", f"Invalid shot number: {e}")
                return

        # 3) Description
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

        # 4) Pixel Mapping
        if self.overridePixelMappingCheck.isChecked():
            pixelMapping = self.pixelMappingEdit.text()
        else:
            pixelMapping = self.pixelMappingCombo.currentText()

        # 5) Full Resolution
        if self.overrideFullResCheck.isChecked():
            fullRes = self.fullResEdit.text()
        else:
            fullRes = self.fullResCombo.currentText()

        # 6) Proxy Resolution
        if self.overrideProxyResCheck.isChecked():
            proxyRes = self.proxyResEdit.text()
        else:
            proxyRes = self.proxyResCombo.currentText()

        # 7) Colorspace (as displayed in filename)
        if self.overrideColorspaceCheck.isChecked():
            self.finalColorspace = self.colorspaceEdit.text()
        else:
            self.finalColorspace = self.colorspaceCombo.currentText()

        # 8) Gamma
        if self.overrideGammaCheck.isChecked():
            gamma = self.gammaEdit.text()
        else:
            gamma = self.gammaCombo.currentText()

        # 9) FPS
        fps = self.fpsCombo.currentText()

        # 10) Version + Auto-Increment
        version = self.versionEdit.text()
        if self.autoIncrementVersionCheck.isChecked():
            m = re.match(r'v(\d+)', version)
            if m:
                num = int(m.group(1)) + 1
                version = "v" + str(num).zfill(len(m.group(1)))
                self.versionEdit.setText(version)

        # 11) Frame Padding
        framePadding = self.framePaddingEdit.text()
        try:
            int(framePadding)
        except:
            QtWidgets.QMessageBox.warning(
                self, "Frame Padding Error",
                "Frame Padding must be an integer."
            )
            return

        # 12) Extension
        if self.overrideExtensionCheck.isChecked():
            extension = self.extensionEdit.text()
        else:
            extension = self.extensionCombo.currentText()

        # Build the base file name from the template
        template_str = self.template_data["templateString"]

        # We'll build two filenames: one for full, one for proxy,
        # each substituting <resolution> differently.
        filenameFull = template_str
        filenameFull = filenameFull.replace("<sequence>", sequence)
        filenameFull = filenameFull.replace("<shotNumber>", shotNumber)
        filenameFull = filenameFull.replace("<description>", description)
        filenameFull = filenameFull.replace("<pixelMappingName>", pixelMapping)
        filenameFull = filenameFull.replace("<resolution>", fullRes)
        filenameFull = filenameFull.replace("<colorspace>", self.finalColorspace)
        filenameFull = filenameFull.replace("<gamma>", gamma)
        filenameFull = filenameFull.replace("<fps>", fps)
        filenameFull = filenameFull.replace("<version>", version)
        filenameFull = filenameFull.replace("<frame_padding>", "%" + "0{}d".format(framePadding))
        filenameFull = filenameFull.replace("<extension>", extension)

        filenameProxy = template_str
        filenameProxy = filenameProxy.replace("<sequence>", sequence)
        filenameProxy = filenameProxy.replace("<shotNumber>", shotNumber)
        filenameProxy = filenameProxy.replace("<description>", description)
        filenameProxy = filenameProxy.replace("<pixelMappingName>", pixelMapping)
        filenameProxy = filenameProxy.replace("<resolution>", proxyRes)
        filenameProxy = filenameProxy.replace("<colorspace>", self.finalColorspace)
        filenameProxy = filenameProxy.replace("<gamma>", gamma)
        filenameProxy = filenameProxy.replace("<fps>", fps)
        filenameProxy = filenameProxy.replace("<version>", version)
        filenameProxy = filenameProxy.replace("<frame_padding>", "%" + "0{}d".format(framePadding))
        filenameProxy = filenameProxy.replace("<extension>", extension)

        baseDir = os.path.normpath(self.baseDirEdit.text())
        if not baseDir:
            QtWidgets.QMessageBox.warning(
                self, "No Base Directory",
                "Please select a base directory."
            )
            return

        # Full-Resolution Path: <baseDir>\<version>\<fullRes>\<filenameFull>
        fullPath = os.path.join(baseDir, version, fullRes, filenameFull)
        fullPath = os.path.normpath(fullPath)

        # Proxy Path: <baseDir>\<version>\<proxyRes>\<filenameProxy>
        proxyPath = os.path.join(baseDir, version, proxyRes, filenameProxy)
        proxyPath = os.path.normpath(proxyPath)

        self.previewFullEdit.setPlainText(fullPath)
        self.previewProxyEdit.setPlainText(proxyPath)

        # Next: If root OCIO config has "aces" in its name, we map the node colorspace:
        # srgb => "Output - sRGB"
        # rec709 => "Output - Rec.709"
        # acescg => "scene_linear (ACES - ACEScg)"
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
            # else keep whatever was set

    # -------------------------------------------------------------------------
    # Create the Write node
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Save the current settings to a JSON file
    # -------------------------------------------------------------------------
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
        # if override is checked, we use self.colorspaceEdit, else colorspaceCombo
        # but we already store self.finalColorspace in updatePreview
        # so let's just store that
        settings["gamma"] = self.gammaEdit.text() if self.overrideGammaCheck.isChecked() else self.gammaCombo.currentText()
        settings["fps"] = self.fpsCombo.currentText()
        # If version override is checked, use that, otherwise defaultVersion
        settings["version"] = self.versionEdit.text() if self.overrideVersionCheck.isChecked() else self.defaultVersion
        settings["framePadding"] = self.framePaddingEdit.text()
        settings["extension"] = self.extensionEdit.text() if self.overrideExtensionCheck.isChecked() else self.extensionCombo.currentText()

        settings["autoIncrementShot"] = self.autoIncrementShotCheck.isChecked()
        settings["autoIncrementVersion"] = self.autoIncrementVersionCheck.isChecked()

        # Write to chosen JSON
        try:
            with open(chosen_path, "w") as outfile:
                json.dump(settings, outfile, indent=4)
            nuke.message(f"Settings saved to:\n{chosen_path}")
        except Exception as e:
            nuke.message(f"Error saving JSON:\n{e}")

    # -------------------------------------------------------------------------
    # Load the current settings from a JSON file
    # -------------------------------------------------------------------------
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
        # else if not found, do nothing

        # 2) baseDirectory
        base_dir = settings.get("baseDirectory", "")
        if base_dir:
            self.baseDirEdit.setText(base_dir)

        # 3) sequence
        seq_val = settings.get("sequence", "")
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
        self.autoIncrementShotCheck.setChecked(settings.get("autoIncrementShot", False))

        # 5) description
        desc_val = settings.get("description", "")
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
        if proxy_res_val in res_allowed:
            self.overrideProxyResCheck.setChecked(False)
            self.proxyResCombo.setCurrentText(proxy_res_val)
        else:
            self.overrideProxyResCheck.setChecked(True)
            self.proxyResEdit.setText(proxy_res_val)

        # 9) colorspace
        cspace_val = settings.get("colorspace", "sRGB")
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
        ext_info = self.template_data["tags"].get("extension", {})
        ext_allowed = ext_info.get("allowed", [])
        if ext_val in ext_allowed:
            self.overrideExtensionCheck.setChecked(False)
            self.extensionCombo.setCurrentText(ext_val)
        else:
            self.overrideExtensionCheck.setChecked(True)
            self.extensionEdit.setText(ext_val)

        # Refresh previews
        self.updatePreview()

    # -------------------------------------------------------------------------
    # End of class
    # -------------------------------------------------------------------------

def main():
    dialog = WriteNodeKENTDialog()
    dialog.exec_()

if __name__ == '__main__':
    main()
