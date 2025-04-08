import nuke
import nukescripts
from PySide6 import QtWidgets, QtCore, QtGui

class SearchReplacePanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SearchReplacePanel, self).__init__(parent)
        self.setObjectName('SearchReplacePanel')
        self.setWindowTitle('Search Replace in Knobs')
        self.setMinimumWidth(350)
        self.setMinimumHeight(150)
        self.init_ui()

    def init_ui(self):
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(2)

        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setSpacing(2)

        self.knob_input = QtWidgets.QLineEdit()
        self.knob_input.setPlaceholderText("Enter knob name")
        self.type_label = QtWidgets.QLabel("")
        self.type_label.setMinimumWidth(60)
        self.knob_input.textChanged.connect(self.check_knob_type)
        grid_layout.addWidget(QtWidgets.QLabel("Knob:"), 0, 0)
        grid_layout.addWidget(self.knob_input, 0, 1)
        grid_layout.addWidget(self.type_label, 0, 2)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Leave empty to replace all")
        self.replace_input = QtWidgets.QLineEdit()
        self.replace_input.setPlaceholderText("New value")
        
        grid_layout.addWidget(QtWidgets.QLabel("Search:"), 1, 0)
        grid_layout.addWidget(self.search_input, 1, 1, 1, 2)
        grid_layout.addWidget(QtWidgets.QLabel("Replace:"), 2, 0)
        grid_layout.addWidget(self.replace_input, 2, 1, 1, 2)

        self.layout.addLayout(grid_layout)

        self.execute_button = QtWidgets.QPushButton("Execute")
        self.execute_button.clicked.connect(self.execute_search_replace)
        self.execute_button.setFixedHeight(25)
        self.layout.addWidget(self.execute_button)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(50)
        self.log_text.setMinimumHeight(50)
        self.layout.addWidget(self.log_text)

    def check_knob_type(self):
        knob_name = self.knob_input.text()
        
        if not knob_name:
            self.type_label.setText("")
            return

        selected_nodes = nuke.selectedNodes()
        if not selected_nodes:
            self.type_label.setText("(No selection)")
            return

        for node in selected_nodes:
            knob = node.knob(knob_name)
            if knob:
                value = knob.value()
                if isinstance(value, str):
                    self.type_label.setText("(Text)")
                elif isinstance(value, int):
                    self.type_label.setText("(Int)")
                elif isinstance(value, float):
                    self.type_label.setText("(Float)")
                elif isinstance(value, bool):
                    self.type_label.setText("(Bool)")
                else:
                    self.type_label.setText(f"({type(value).__name__})")
                return

        self.type_label.setText("(Not found)")

    def log_message(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def execute_search_replace(self):
        knob_name = self.knob_input.text()
        search_str = self.search_input.text()
        replace_str = self.replace_input.text()
        
        if not knob_name:
            nuke.message("Please provide a knob name")
            return
        if not replace_str and not search_str:
            nuke.message("Please provide at least a replace value")
            return
            
        selected_nodes = nuke.selectedNodes()
        if not selected_nodes:
            nuke.message("Please select at least one node")
            return
            
        modified_count = 0
        self.log_text.clear()
        
        for node in selected_nodes:
            try:
                knob = node.knob(knob_name)
                if knob:
                    current_value = knob.value()
                    
                    # Text handling
                    if isinstance(current_value, str):
                        if not search_str:
                            knob.setValue(replace_str)
                            modified_count += 1
                            self.log_message(f"{node.name()}: {current_value} → {replace_str}")
                        elif search_str in current_value:
                            new_value = current_value.replace(search_str, replace_str)
                            knob.setValue(new_value)
                            modified_count += 1
                            self.log_message(f"{node.name()}: {current_value} → {new_value}")
                    
                    # Numeric handling
                    elif isinstance(current_value, (int, float)):
                        try:
                            if not search_str:
                                new_value = (int if isinstance(current_value, int) else float)(replace_str)
                                knob.setValue(new_value)
                                modified_count += 1
                                self.log_message(f"{node.name()}: {current_value} → {new_value}")
                            else:
                                current_num = float(current_value)
                                search_num = float(search_str)
                                if current_num == search_num:
                                    new_value = (int if isinstance(current_value, int) else float)(replace_str)
                                    knob.setValue(new_value)
                                    modified_count += 1
                                    self.log_message(f"{node.name()}: {current_value} → {new_value}")
                        except ValueError:
                            self.log_message(f"Error: Invalid numeric value for {node.name()}.{knob_name}")
                    
                    # Boolean handling
                    elif isinstance(current_value, bool):
                        try:
                            if not search_str or str(current_value).lower() == search_str.lower():
                                new_value = bool(int(replace_str))
                                knob.setValue(new_value)
                                modified_count += 1
                                self.log_message(f"{node.name()}: {current_value} → {new_value}")
                        except ValueError:
                            self.log_message(f"Error: Invalid boolean value for {node.name()}.{knob_name}")
                        
            except Exception as e:
                self.log_message(f"Error: {node.name()} - {str(e)}")
        
        if modified_count > 0:
            nuke.message(f"Modified {modified_count} node(s)")
        else:
            nuke.message("No matching knobs found or no changes needed")

def search_replace_panel():
    return SearchReplacePanel()

nukescripts.registerWidgetAsPanel('search_replace_panel.SearchReplacePanel', 'Search Replace Panel', 'uk.co.thefoundry.SearchReplacePanel')
nuke.menu('Pane').addCommand('Search Replace Panel', lambda: nukescripts.panels.restorePanel('uk.co.thefoundry.SearchReplacePanel'))
