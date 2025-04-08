import nuke

def set_frame_range_from_read():
    """
    Sets the project frame range based on the currently selected Read node.
    If no Read node is selected, displays an error message.
    """
    # Get selected nodes
    selected_nodes = nuke.selectedNodes()
    
    # Filter for Read nodes only
    read_nodes = [node for node in selected_nodes if node.Class() == "Read"]
    
    if not read_nodes:
        nuke.message("Error: Please select a Read node first.")
        return
        
    # Use the first selected Read node if multiple are selected
    read_node = read_nodes[0]
    
    if len(read_nodes) > 1:
        nuke.message("Multiple Read nodes selected. Using: " + read_node.name())
    
    # Get the frame range from the Read node
    first_frame = read_node['first'].value()
    last_frame = read_node['last'].value()
    
    # Set the project frame range
    root = nuke.root()
    root['first_frame'].setValue(first_frame)
    root['last_frame'].setValue(last_frame)
    
    # Also set the frame range in the viewer
    # This is equivalent to the user pressing the 'F' key with the Read node selected
    nuke.frame(first_frame)
    for viewer in nuke.allNodes('Viewer'):
        viewer['frame_range'].setValue(f"{first_frame}-{last_frame}")
    
    print(f"Project frame range set to: {first_frame}-{last_frame}")
    nuke.message(f"Project frame range set to: {first_frame}-{last_frame}")

# Code to add this to a menu - add this in your menu.py file or in this file
def add_to_menu():
    menubar = nuke.menu("Nuke")
    fileMenu = menubar.findItem("Edit")
    fileMenu.addCommand("Set Frame Range from Read", set_frame_range_from_read, "alt+r")

# Call this to add the menu item when importing this module
add_to_menu()