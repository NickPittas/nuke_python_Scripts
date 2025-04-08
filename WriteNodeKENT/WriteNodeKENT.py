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

        # Colorspace settings
        self.finalColorspace = "sRGB"
        self.finalNodeColorspace = "sRGB"
        # For storing the current file extension (to set file_type knob)
        self.currentExtension = None

        # Dictionary to hold dynamic tag fields (except shot number and version)
        self.dynamicFields = {}  # Keys: "sequence", "description", "pixelMappingName", "colorspace", "gamma", "extension"
        # The "resolution" key is special because we need two rows (full and proxy)

        self.initUI()

    def createDynamicField(self, with_override=True, has_combo=True):
        """
        Create a widget row with a combo box (if has_combo), an override checkbox (if with_override)
        and a line edit (hidden by default).
        Returns a tuple: (container, combo, override, lineEdit)
        """
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        combo = QtWidgets.QComboBox() if has_combo else None
        if combo:
            combo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            layout.addWidget(combo)

        override_cb = QtWidgets.QCheckBox("Override") if with_override else None
        if override_cb:
            layout.addWidget(override_cb)

        line_edit = QtWidgets.QLineEdit()
        if with_override:
            line_edit.setVisible(False)
        layout.addWidget(line_edit)

        return container, combo, override_cb, line_edit

    def initUI(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        form_layout = QtWidgets.QFormLayout()
        form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setLabelAlignment(QtCore.Qt.AlignRight)

        # --- Template Selection (static) ---
        self.templateSelectCombo = QtWidgets.QComboBox()
        self.templateSelectCombo.addItems(self.template_files)
        self.templateSelectCombo.currentIndexChanged.connect(self.loadSelectedTemplate)
        form_layout.addRow("Select Template:", self.templateSelectCombo)
        self.templateNameLabel = QtWidgets.QLabel("No template loaded yet")
        form_layout.addRow("Template Name:", self.templateNameLabel)

        # --- Dynamic Fields ---
        # Sequence
        widget, combo, override_cb, line_edit = self.createDynamicField(with_override=True, has_combo=True)
        self.dynamicFields["sequence"] = {"widget": widget, "combo": combo, "override": override_cb, "lineEdit": line_edit}
        form_layout.addRow("Sequence:", widget)

        # Description
        widget, combo, override_cb, line_edit = self.createDynamicField(with_override=True, has_combo=True)
        self.dynamicFields["description"] = {"widget": widget, "combo": combo, "override": override_cb, "lineEdit": line_edit}
        form_layout.addRow("Description:", widget)

        # Pixel Mapping
        widget, combo, override_cb, line_edit = self.createDynamicField(with_override=True, has_combo=True)
        self.dynamicFields["pixelMappingName"] = {"widget": widget, "combo": combo, "override": override_cb, "lineEdit": line_edit}
        form_layout.addRow("Pixel Mapping:", widget)

        # Colorspace
        widget, combo, override_cb, line_edit = self.createDynamicField(with_override=True, has_combo=True)
        self.dynamicFields["colorspace"] = {"widget": widget, "combo": combo, "override": override_cb, "lineEdit": line_edit}
        form_layout.addRow("Colorspace:", widget)

        # Gamma
        widget, combo, override_cb, line_edit = self.createDynamicField(with_override=True, has_combo=True)
        self.dynamicFields["gamma"] = {"widget": widget, "combo": combo, "override": override_cb, "lineEdit": line_edit}
        form_layout.addRow("Gamma:", widget)

        # Extension
        widget, combo, override_cb, line_edit = self.createDynamicField(with_override=True, has_combo=True)
        self.dynamicFields["extension"] = {"widget": widget, "combo": combo, "override": override_cb, "lineEdit": line_edit}
        form_layout.addRow("Extension:", widget)

        # Resolution (Full & Proxy share the same allowed values)
        self.dynamicFields["resolution"] = {}
        widget, combo, override_cb, line_edit = self.createDynamicField(with_override=True, has_combo=True)
        self.dynamicFields["resolution"]["full"] = {"widget": widget, "combo": combo, "override": override_cb, "lineEdit": line_edit}
        form_layout.addRow("Full Resolution:", widget)

        widget, combo, override_cb, line_edit = self.createDynamicField(with_override=True, has_combo=True)
        self.dynamicFields["resolution"]["proxy"] = {"widget": widget, "combo": combo, "override": override_cb, "lineEdit": line_edit}
        form_layout.addRow("Proxy Resolution:", widget)

        # --- Shot Number (simple field; auto-increment removed) ---
        self.shotNumberWidget = QtWidgets.QWidget()
        shot_layout = QtWidgets.QHBoxLayout(self.shotNumberWidget)
        shot_layout.setContentsMargins(0, 0, 0, 0)
        self.shotNumberEdit = QtWidgets.QLineEdit()
        shot_layout.addWidget(self.shotNumberEdit)
        form_layout.addRow("Shot Number:", self.shotNumberWidget)

        # --- FPS (simple combo) ---
        self.fpsWidget = QtWidgets.QWidget()
        fps_layout = QtWidgets.QHBoxLayout(self.fpsWidget)
        fps_layout.setContentsMargins(0, 0, 0, 0)
        self.fpsCombo = QtWidgets.QComboBox()
        fps_layout.addWidget(self.fpsCombo)
        form_layout.addRow("FPS:", self.fpsWidget)

        # --- Version (has auto increment & override) ---
        self.versionWidget = QtWidgets.QWidget()
        version_layout = QtWidgets.QHBoxLayout(self.versionWidget)
        version_layout.setContentsMargins(0, 0, 0, 0)
        self.autoIncrementVersionCheck = QtWidgets.QCheckBox("Auto Increment")
        version_layout.addWidget(self.autoIncrementVersionCheck)
        self.overrideVersionCheck = QtWidgets.QCheckBox("Override")
        version_layout.addWidget(self.overrideVersionCheck)
        self.versionEdit = QtWidgets.QLineEdit(self.defaultVersion)
        self.versionEdit.setVisible(False)
        version_layout.addWidget(self.versionEdit)
        form_layout.addRow("Version:", self.versionWidget)

        # --- Frame Padding (simple field) ---
        self.framePaddingWidget = QtWidgets.QWidget()
        frame_padding_layout = QtWidgets.QHBoxLayout(self.framePaddingWidget)
        frame_padding_layout.setContentsMargins(0, 0, 0, 0)
        self.framePaddingEdit = QtWidgets.QLineEdit()
        self.framePaddingEdit.textChanged.connect(self.autoUpdatePreview)
        frame_padding_layout.addWidget(self.framePaddingEdit)
        form_layout.addRow("Frame Padding:", self.framePaddingWidget)

        # --- Base Directory (static) ---
        self.baseDirWidget = QtWidgets.QWidget()
        base_dir_layout = QtWidgets.QHBoxLayout(self.baseDirWidget)
        base_dir_layout.setContentsMargins(0, 0, 0, 0)
        self.baseDirEdit = QtWidgets.QLineEdit()
        self.baseDirEdit.textChanged.connect(self.autoUpdatePreview)
        self.baseDirButton = QtWidgets.QPushButton("Browse")
        self.baseDirButton.clicked.connect(self.browseBaseDir)
        base_dir_layout.addWidget(self.baseDirEdit)
        base_dir_layout.addWidget(self.baseDirButton)
        form_layout.addRow("Base Directory:", self.baseDirWidget)

        # --- Preview Fields (static) ---
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

        # Setup dynamic signal connections
        self.setupDynamicSignals()

        # Load the first template by default
        self.templateSelectCombo.setCurrentIndex(0)
        self.loadSelectedTemplate(0)

    def setupDynamicSignals(self):
        # Loop over each dynamic field and connect signals to update preview.
        for tag, field in self.dynamicFields.items():
            if tag == "resolution":
                for resType in ["full", "proxy"]:
                    f = field[resType]
                    if f["combo"]:
                        f["combo"].currentIndexChanged.connect(self.autoUpdatePreview)
                    if f["lineEdit"]:
                        f["lineEdit"].textChanged.connect(self.autoUpdatePreview)
                    if f["override"]:
                        # Using lambda to pass both tag and resolution type.
                        f["override"].toggled.connect(lambda checked, tag=tag, resType=resType: self.onOverrideToggled(tag, resType))
            else:
                if field["combo"]:
                    field["combo"].currentIndexChanged.connect(self.autoUpdatePreview)
                if field["lineEdit"]:
                    field["lineEdit"].textChanged.connect(self.autoUpdatePreview)
                if field["override"]:
                    field["override"].toggled.connect(lambda checked, tag=tag: self.onOverrideToggled(tag))
        # Additional signals for version and shot number are already connected in initUI.
        self.overrideVersionCheck.toggled.connect(self.onVersionOverrideToggled)
        self.versionEdit.textChanged.connect(self.autoUpdatePreview)
        self.autoIncrementVersionCheck.toggled.connect(self.autoUpdatePreview)

    def onOverrideToggled(self, tag, resType=None):
        """Generic handler to show/hide the lineEdit when override is toggled."""
        if tag == "resolution":
            field = self.dynamicFields["resolution"][resType]
        else:
            field = self.dynamicFields[tag]
        if field["override"].isChecked():
            field["lineEdit"].setVisible(True)
            if field["combo"]:
                field["combo"].setEnabled(False)
        else:
            field["lineEdit"].setVisible(False)
            if field["combo"]:
                field["combo"].setEnabled(True)
        self.autoUpdatePreview()

    def onVersionOverrideToggled(self, checked):
        self.versionEdit.setVisible(checked)
        self.autoUpdatePreview()

    def autoUpdatePreview(self):
        if self.template_data:
            QtCore.QTimer.singleShot(10, self.updatePreview)

    def browseBaseDir(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Base Directory", self.script_dir)
        if directory:
            directory = os.path.normpath(directory)
            self.baseDirEdit.setText(directory)

    def loadSelectedTemplate(self, index):
        selected_file = self.templateSelectCombo.itemText(index)
        self.template_data = self.templates_data[selected_file]
        tmpl_name = self.template_data.get("templateName", selected_file)
        self.templateNameLabel.setText(tmpl_name)
        tags = self.template_data.get("tags", {})

        # Process dynamic fields in a loop
        for tag, field in self.dynamicFields.items():
            if tag == "resolution":
                if "resolution" in tags:
                    res_info = tags.get("resolution", {})
                    allowed = res_info.get("allowed", [])
                    for resType in ["full", "proxy"]:
                        field[resType]["widget"].setVisible(True)
                        if field[resType]["combo"]:
                            field[resType]["combo"].clear()
                            field[resType]["combo"].addItems(allowed)
                else:
                    for resType in ["full", "proxy"]:
                        field[resType]["widget"].setVisible(False)
            else:
                if tag in tags:
                    field["widget"].setVisible(True)
                    info = tags.get(tag, {})
                    allowed = info.get("allowed", [])
                    if field["combo"]:
                        field["combo"].clear()
                        field["combo"].addItems(allowed)
                        default_val = info.get("default", "")
                        if default_val in allowed:
                            field["combo"].setCurrentText(default_val)
                        elif allowed:
                            field["combo"].setCurrentIndex(0)
                else:
                    field["widget"].setVisible(False)

        # Shot Number
        if "shotNumber" in tags:
            self.shotNumberWidget.setVisible(True)
            shot_info = tags.get("shotNumber", {})
            shot_default = shot_info.get("default", "0010")
            self.shotNumberEdit.setText(shot_default)
        else:
            self.shotNumberWidget.setVisible(False)

        # FPS
        if "fps" in tags:
            self.fpsWidget.setVisible(True)
            fps_info = tags.get("fps", {})
            allowed = fps_info.get("allowed", [])
            self.fpsCombo.clear()
            self.fpsCombo.addItems(allowed)
            default_fps = fps_info.get("default", None)
            if default_fps and default_fps in allowed:
                self.fpsCombo.setCurrentText(default_fps)
        else:
            self.fpsWidget.setVisible(False)

        # Frame Padding
        if "frame_padding" in tags:
            self.framePaddingWidget.setVisible(True)
            fpad_info = tags.get("frame_padding", {})
            self.framePaddingEdit.setText(fpad_info.get("default", "4"))
        else:
            self.framePaddingWidget.setVisible(False)

        self.previewFullEdit.clear()
        self.previewProxyEdit.clear()
        self.autoUpdatePreview()

    def updatePreview(self):
        if not self.template_data:
            nuke.message("No template loaded.")
            return

        # Run extension logic to auto-set colorspace/gamma
        self.onExtensionChanged()

        def get_field_value(tag, resType=None):
            """Helper to get the current value from a dynamic field."""
            if tag == "resolution":
                field = self.dynamicFields["resolution"][resType]
            else:
                field = self.dynamicFields[tag]
            if field["override"] and field["override"].isChecked():
                return field["lineEdit"].text()
            else:
                return field["combo"].currentText() if field["combo"] else field["lineEdit"].text()

        sequence = get_field_value("sequence")
        shotNumber = self.shotNumberEdit.text()
        description = get_field_value("description")
        if not re.match(r'^[a-z][a-zA-Z0-9_]*$', description):
            QtWidgets.QMessageBox.warning(self, "Invalid Description",
                                          "Use camelCase or underscores only (no spaces/other chars).")
            return
        pixelMapping = get_field_value("pixelMappingName")
        fullRes = get_field_value("resolution", "full")
        proxyRes = get_field_value("resolution", "proxy")
        colorspace_val = get_field_value("colorspace")
        self.finalColorspace = colorspace_val
        gamma = get_field_value("gamma")
        fps = self.fpsCombo.currentText()
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
        framePadding = self.framePaddingEdit.text()
        try:
            int(framePadding)
        except:
            QtWidgets.QMessageBox.warning(self, "Frame Padding Error",
                                          "Frame Padding must be an integer.")
            return
        extension = get_field_value("extension")
        # Store current extension for use in createWriteNode (for file_type knob)
        self.currentExtension = extension

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
            self.previewFullEdit.clear()
            self.previewProxyEdit.clear()
            return

        fullPath = os.path.normpath(os.path.join(baseDir, version, fullRes, filenameFull))
        proxyPath = os.path.normpath(os.path.join(baseDir, version, proxyRes, filenameProxy))
        self.previewFullEdit.setPlainText(fullPath)
        self.previewProxyEdit.setPlainText(proxyPath)

        # Adjust node colorspace if using an ACES OCIO config
        config_name = nuke.root()["OCIO_config"].value() if "OCIO_config" in nuke.root().knobs() else ""
        self.finalNodeColorspace = self.finalColorspace
        if "aces" in config_name.lower():
            cspace_l = self.finalColorspace.lower()
            if cspace_l == "srgb":
                self.finalNodeColorspace = "Output - sRGB"
            elif cspace_l == "rec709":
                self.finalNodeColorspace = "Output - Rec.709"
            elif cspace_l == "acescg":
                self.finalNodeColorspace = "scene_linear"

    def onExtensionChanged(self):
        if not self.template_data:
            return
        field_ext = self.dynamicFields["extension"]
        if field_ext["override"].isChecked():
            return
        ext = field_ext["combo"].currentText().lower()
        if ext in ["mov", "mp4"]:
            if not self.dynamicFields["colorspace"]["override"].isChecked():
                idx = self.dynamicFields["colorspace"]["combo"].findText("rec709", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["colorspace"]["combo"].setCurrentIndex(idx)
            if not self.dynamicFields["gamma"]["override"].isChecked():
                idx = self.dynamicFields["gamma"]["combo"].findText("g24", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["gamma"]["combo"].setCurrentIndex(idx)
        elif ext in ["jpg", "png", "tif", "tiff"]:
            if not self.dynamicFields["colorspace"]["override"].isChecked():
                idx = self.dynamicFields["colorspace"]["combo"].findText("sRGB", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["colorspace"]["combo"].setCurrentIndex(idx)
            if not self.dynamicFields["gamma"]["override"].isChecked():
                idx = self.dynamicFields["gamma"]["combo"].findText("g22", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["gamma"]["combo"].setCurrentIndex(idx)
        elif ext == "exr":
            if not self.dynamicFields["colorspace"]["override"].isChecked():
                idx = self.dynamicFields["colorspace"]["combo"].findText("acescg", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["colorspace"]["combo"].setCurrentIndex(idx)
            if not self.dynamicFields["gamma"]["override"].isChecked():
                idx = self.dynamicFields["gamma"]["combo"].findText("lin", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["gamma"]["combo"].setCurrentIndex(idx)
        self.onColorspaceChanged()

    def onColorspaceChanged(self):
        if not self.template_data:
            return
        if self.dynamicFields["colorspace"]["override"].isChecked():
            return
        cspace = self.dynamicFields["colorspace"]["combo"].currentText().lower()
        if not self.dynamicFields["gamma"]["override"].isChecked():
            if cspace == "rec709":
                idx = self.dynamicFields["gamma"]["combo"].findText("g24", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["gamma"]["combo"].setCurrentIndex(idx)
            elif cspace == "srgb":
                idx = self.dynamicFields["gamma"]["combo"].findText("g22", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["gamma"]["combo"].setCurrentIndex(idx)
            elif cspace == "acescg":
                idx = self.dynamicFields["gamma"]["combo"].findText("lin", QtCore.Qt.MatchFixedString)
                if idx >= 0:
                    self.dynamicFields["gamma"]["combo"].setCurrentIndex(idx)
        self.autoUpdatePreview()

    def createWriteNode(self):
        """Creates a single Write node with full-resolution and proxy paths."""
        self.updatePreview()  # Ensure preview is up to date

        fullPath = self.previewFullEdit.toPlainText()
        proxyPath = self.previewProxyEdit.toPlainText()
        if not fullPath or not proxyPath:
            QtWidgets.QMessageBox.warning(self, "Error", "Preview paths are empty. Check your inputs.")
            return

        for path_dir in [os.path.dirname(fullPath), os.path.dirname(proxyPath)]:
            if not os.path.exists(path_dir):
                try:
                    os.makedirs(path_dir)
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Directory Error",
                                                   f"Could not create directory {path_dir}:\n{e}")
                    return

        writeNode = nuke.createNode("Write", inpanel=False)
        writeNode["file"].setValue(fullPath)
        writeNode["proxy"].setValue(proxyPath)
        writeNode["colorspace"].setValue(self.finalNodeColorspace)
        writeNode["create_directories"].setValue("True")

        # Set the file_type knob to the current extension (as determined in updatePreview)
        if self.currentExtension:
            writeNode["file_type"].setValue(self.currentExtension)

        # nuke.message(f"Write node created:\nFull: {fullPath}\nProxy: {proxyPath}")
        self.accept()

    def saveSettings(self):
        self.updatePreview()  # Make sure we have the latest data
        default_save_path = os.path.join(self.script_dir, "custom_settings.json")
        chosen_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Settings as JSON",
                                                                 default_save_path, "JSON Files (*.json)")
        if not chosen_path:
            return
        settings = {}
        settings["templateFile"] = self.templateSelectCombo.currentText()
        settings["baseDirectory"] = self.baseDirEdit.text()
        for tag, field in self.dynamicFields.items():
            if tag == "resolution":
                settings["fullResolution"] = field["full"]["lineEdit"].text() if field["full"]["override"].isChecked() else field["full"]["combo"].currentText()
                settings["proxyResolution"] = field["proxy"]["lineEdit"].text() if field["proxy"]["override"].isChecked() else field["proxy"]["combo"].currentText()
            else:
                settings[tag] = field["lineEdit"].text() if field["override"].isChecked() else field["combo"].currentText()
        settings["shotNumber"] = self.shotNumberEdit.text()
        settings["fps"] = self.fpsCombo.currentText()
        settings["version"] = self.versionEdit.text() if self.overrideVersionCheck.isChecked() else self.defaultVersion
        settings["framePadding"] = self.framePaddingEdit.text()
        settings["autoIncrementVersion"] = self.autoIncrementVersionCheck.isChecked()
        try:
            with open(chosen_path, "w") as outfile:
                json.dump(settings, outfile, indent=4)
            nuke.message(f"Settings saved to:\n{chosen_path}")
        except Exception as e:
            nuke.message(f"Error saving JSON:\n{e}")

    def loadSettings(self):
        default_load_path = os.path.join(self.script_dir, "custom_settings.json")
        chosen_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Settings from JSON",
                                                                 default_load_path, "JSON Files (*.json)")
        if not chosen_path:
            return
        try:
            with open(chosen_path, "r") as infile:
                settings = json.load(infile)
        except Exception as e:
            nuke.message(f"Error loading JSON:\n{e}")
            return
        template_file = settings.get("templateFile", "")
        idx = self.templateSelectCombo.findText(template_file)
        if idx >= 0:
            self.templateSelectCombo.setCurrentIndex(idx)
        base_dir = settings.get("baseDirectory", "")
        if base_dir:
            self.baseDirEdit.setText(base_dir)
        for tag, field in self.dynamicFields.items():
            if tag == "resolution":
                full_val = settings.get("fullResolution", "")
                proxy_val = settings.get("proxyResolution", "")
                if full_val:
                    if full_val in field["full"]["combo"].currentText():
                        field["full"]["override"].setChecked(False)
                        field["full"]["combo"].setCurrentText(full_val)
                    else:
                        field["full"]["override"].setChecked(True)
                        field["full"]["lineEdit"].setText(full_val)
                if proxy_val:
                    if proxy_val in field["proxy"]["combo"].currentText():
                        field["proxy"]["override"].setChecked(False)
                        field["proxy"]["combo"].setCurrentText(proxy_val)
                    else:
                        field["proxy"]["override"].setChecked(True)
                        field["proxy"]["lineEdit"].setText(proxy_val)
            else:
                val = settings.get(tag, "")
                if val:
                    if val in field["combo"].currentText():
                        field["override"].setChecked(False)
                        field["combo"].setCurrentText(val)
                    else:
                        field["override"].setChecked(True)
                        field["lineEdit"].setText(val)
        self.shotNumberEdit.setText(settings.get("shotNumber", "0010"))
        self.fpsCombo.setCurrentText(settings.get("fps", "2997"))
        self.autoIncrementVersionCheck.setChecked(settings.get("autoIncrementVersion", False))
        version_val = settings.get("version", self.defaultVersion)
        if version_val != self.defaultVersion:
            self.overrideVersionCheck.setChecked(True)
            self.versionEdit.setText(version_val)
        else:
            self.overrideVersionCheck.setChecked(False)
        self.framePaddingEdit.setText(settings.get("framePadding", "4"))
        self.autoUpdatePreview()


def main():
    dialog = WriteNodeKENTDialog()
    dialog.exec_()


if __name__ == '__main__':
    main()
