import nuke
import os
import re

def increment_version(filepath):
    """
    Takes a filepath with version number and returns a new filepath with incremented version.
    Handles various version number formats (v01, v001, v0001, etc.)
    """
    directory, filename = os.path.split(filepath)
    version_pattern = r'v(\d+)'
    matches = list(re.finditer(version_pattern, filename))
    
    if not matches:
        raise ValueError("No version number found in filename")
    
    last_match = matches[-1]
    current_version_str = last_match.group(1)
    version_length = len(current_version_str)
    
    new_version = str(int(current_version_str) + 1).zfill(version_length)
    new_version_str = f'v{new_version}'
    
    start, end = last_match.span()
    new_filename = filename[:start] + new_version_str + filename[end:]
    new_directory = os.path.join(directory, new_version_str)
    new_filepath = os.path.join(new_directory, new_filename)
    
    print(f"Original path: {filepath}")
    print(f"New path: {new_filepath}")
    
    return new_filepath, new_filename

def find_input_read(node, visited=None):
    if visited is None:
        visited = set()
        
    if node in visited:
        return None
    visited.add(node)
    
    print(f"Checking node: {node.name()} of class {node.Class()}")
    
    if node.Class() == "Read":
        print(f"Found Read node: {node.name()}")
        return node
        
    for input_num in range(node.inputs()):
        input_node = node.input(input_num)
        if input_node:
            read_node = find_input_read(input_node, visited)
            if read_node:
                return read_node
    return None

def create_write_node():
    """Creates a write node with incremented version based on selected node's input Read node"""
    try:
        selected = nuke.selectedNode()
        if not selected:
            nuke.message("Please select a node")
            return
        
        print(f"Selected node: {selected.name()} of class {selected.Class()}")
        
        read_node = find_input_read(selected)
        if not read_node:
            nuke.message("No Read node found in input tree")
            return
            
        read_path = read_node['file'].value()
        print(f"Read path: {read_path}")
        
        new_path, new_filename = increment_version(read_path)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        
        # Create Write node
        write_node = nuke.nodes.Write()
        print("Write node created")
        
        # Set Write node parameters
        write_node['file'].setValue(new_path)
        write_node['create_directories'].setValue(True)
        
        # Position write node
        write_node.setXYpos(selected.xpos(), selected.ypos() + 100)
        
        print("Write node setup complete")
        return write_node
        
    except Exception as e:
        print(f"Error in create_write_node: {str(e)}")
        nuke.message(f"Error: {str(e)}")
        return None