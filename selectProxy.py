import nuke
from PySide6 import QtWidgets, QtCore

def set_proxy_for_selected():
    # Get selected node
    selected_nodes = nuke.selectedNodes('Read')
    
    if not selected_nodes:
        nuke.message('Please select a Read node first')
        return
    
    selected_node = selected_nodes[0]
    
    # Get all read nodes except the selected one
    all_reads = [n for n in nuke.allNodes('Read') if n != selected_node]
    
    if not all_reads:
        nuke.message('No other Read nodes found to use as proxy')
        return
    
    # Create a dialog
    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle('Select Proxy Read Node')
    
    layout = QtWidgets.QVBoxLayout()
    
    # Create a dropdown (combo box) instead of a list
    combo_box = QtWidgets.QComboBox()
    
    # Add all read nodes to the dropdown
    for read in all_reads:
        node_name = read.name()
        file_path = read['file'].getValue()
        
        # Create a more descriptive item text
        item_text = f"{node_name} - {file_path}"
        combo_box.addItem(item_text)
    
    layout.addWidget(combo_box)
    
    # Add buttons
    button_layout = QtWidgets.QHBoxLayout()
    ok_button = QtWidgets.QPushButton('OK')
    cancel_button = QtWidgets.QPushButton('Cancel')
    
    button_layout.addWidget(ok_button)
    button_layout.addWidget(cancel_button)
    
    layout.addLayout(button_layout)
    
    dialog.setLayout(layout)
    
    # Connect signals
    ok_button.clicked.connect(dialog.accept)
    cancel_button.clicked.connect(dialog.reject)
    
    # Show dialog
    result = dialog.exec_()
    
    if result == QtWidgets.QDialog.Accepted and combo_box.currentIndex() >= 0:
        proxy_node = all_reads[combo_box.currentIndex()]
        
        # Set up proxy
        selected_node['proxy'].setValue(proxy_node['file'].getValue())
        
        # Copy the format properly
        format_name = proxy_node['format'].value()
        selected_node['proxy_format'].setValue(format_name)
        
        # No longer enabling proxy mode at all

# Run the function
set_proxy_for_selected()