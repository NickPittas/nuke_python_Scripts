# Nuke Keyframe Range noOp Creator
# This script finds all keyframes in selected nodes (including inside groups and gizmos),
# identifies the first and last keyframes, and creates a noOp node with animation 
# that goes from 1 to 0 to 0 to 1 at the keyframe boundaries (to control disable knobs).

import nuke

def create_keyframe_range_noOp():
    # Get selected nodes
    selected_nodes = nuke.selectedNodes()
    
    if not selected_nodes:
        nuke.message("Please select at least one node with keyframes")
        return
    
    # Initialize min and max frame values
    min_frame = float('inf')  # Start with infinity for finding minimum
    max_frame = float('-inf')  # Start with negative infinity for finding maximum
    found_keyframes = False
    
    print("Starting keyframe search on selected nodes...")
    print(f"Number of selected nodes: {len(selected_nodes)}")
    
    # Function to recursively scan nodes and their internals for keyframes
    def scan_node_for_keyframes(node):
        nonlocal min_frame, max_frame, found_keyframes
        
        # Check each knob of the node
        for knob_name in node.knobs():
            try:
                knob = node[knob_name]
                
                # Skip knobs that don't support animation or frequently cause errors
                if isinstance(knob, (nuke.File_Knob, nuke.EvalString_Knob, nuke.Multiline_Eval_String_Knob)):
                    continue
                
                # Check if knob is animated
                if knob.isAnimated():
                    try:
                        # Try to get arraySize - this will fail for some knob types
                        has_array = hasattr(knob, 'arraySize') and knob.arraySize() > 1
                    except:
                        has_array = False
                        
                    # Handle array knobs (like transform, which has x, y, etc.)
                    if has_array:
                        for i in range(knob.arraySize()):
                            if knob.isAnimated(i):
                                try:
                                    curves = knob.animations()
                                    if i < len(curves) and curves[i]:
                                        keyframes = curves[i].keys()
                                        if keyframes:
                                            found_keyframes = True
                                            for key in keyframes:
                                                frame = key.x
                                                min_frame = min(min_frame, frame)
                                                max_frame = max(max_frame, frame)
                                except Exception as e:
                                    print(f"Error processing array knob {knob_name} on {node.name()}: {str(e)}")
                    # Handle regular animated knobs
                    else:
                        try:
                            curve = knob.animation(0)
                            if curve:
                                keyframes = curve.keys()
                                if keyframes:
                                    # Debug: print each keyframe we find
                                    print(f"Found keyframe at frame {frame} in {node.name()}.{knob_name}[{i}]")
                                    found_keyframes = True
                                    for key in keyframes:
                                        frame = key.x
                                        min_frame = min(min_frame, frame)
                                        max_frame = max(max_frame, frame)
                        except Exception as e:
                            print(f"Error processing knob {knob_name} on {node.name()}: {str(e)}")
            except Exception as e:
                print(f"Error accessing knob {knob_name} on {node.name()}: {str(e)}")
                continue
        
        # Check if node is a group or gizmo and scan its internals
        if node.Class() in ("Group", "Gizmo"):
            try:
                # Enter the group/gizmo context
                with node:
                    # Get all nodes inside the group/gizmo
                    internal_nodes = nuke.allNodes(recurseGroups=False)
                    # Scan each internal node
                    for internal_node in internal_nodes:
                        scan_node_for_keyframes(internal_node)
            except Exception as e:
                print(f"Error scanning inside {node.name()}: {str(e)}")
    
    # Scan through all selected nodes to find keyframes
    for node in selected_nodes:
        try:
            print(f"Scanning node: {node.name()} ({node.Class()})")
            scan_node_for_keyframes(node)
        except Exception as e:
            print(f"Error scanning node {node.name()}: {str(e)}")
    
    print(f"Keyframe search completed. Found keyframes: {found_keyframes}")
    print(f"Min frame: {min_frame if min_frame != float('inf') else 'None found'}")
    print(f"Max frame: {max_frame if max_frame != float('-inf') else 'None found'}")
    
    if not found_keyframes or min_frame == float('inf') or max_frame == float('-inf'):
        nuke.message("No keyframes found in selected nodes")
        return
    
    # Create a new noOp node without connecting to anything in empty space
    # Store current selection to restore it later
    temp_selection = nuke.selectedNodes()
    # Deselect all nodes to ensure the new node isn't connected to anything
    [n.setSelected(False) for n in temp_selection]
    # Create the node in empty space
    noOp = nuke.createNode("NoOp", "name KeyframeRange tile_color 0x7fff00ff", inpanel=False)
    # Restore original selection
    [n.setSelected(True) for n in temp_selection]
    
    # Create a new knob for animation
    tab = nuke.Tab_Knob("KeyframeRange", "Keyframe Range")
    noOp.addKnob(tab)
    
    value_knob = nuke.Double_Knob("rangeValue", "Range Value (for disable)")
    value_knob.setRange(0, 1)
    value_knob.setTooltip("Use this to drive a disable knob - 0 means disabled, 1 means enabled")
    noOp.addKnob(value_knob)
    
    # Add knobs to show the frame range
    start_knob = nuke.Int_Knob("rangeStart", "Range Start")
    start_knob.setValue(int(min_frame))
    start_knob.setEnabled(False)
    noOp.addKnob(start_knob)
    
    end_knob = nuke.Int_Knob("rangeEnd", "Range End")
    end_knob.setValue(int(max_frame))
    end_knob.setEnabled(False)
    noOp.addKnob(end_knob)
    
    # Add text knob with usage information
    info_knob = nuke.Text_Knob("info", "", "This node represents the keyframe range from all selected nodes.\nThe Range Value is 0 between first and last keyframes (for disable knobs).\nLink this to a disable knob with an expression, e.g.: parent.KeyframeRange.rangeValue")
    noOp.addKnob(info_knob)
    
    # Add a button to recalculate the keyframe range
    recalc_script = """
# Get reference to this node
node = nuke.thisNode()

# Store the current node selection
selected_nodes = nuke.selectedNodes()

# Remove this node from the selection
for n in selected_nodes:
    n.setSelected(False)

# If no nodes are selected after removing this one, show an error
if len(selected_nodes) == 0:
    nuke.message("Please select at least one node with keyframes")
else:
    # Initialize min and max frame values
    min_frame = float('inf')
    max_frame = float('-inf')
    found_keyframes = False
    
            # Function to recursively scan nodes and internals for keyframes
    def scan_node_for_keyframes(node):
        nonlocal min_frame, max_frame, found_keyframes
        
        # Check each knob of the node
        for knob_name in node.knobs():
            try:
                knob = node[knob_name]
                
                # Skip knobs that don't support animation or frequently cause errors
                if isinstance(knob, (nuke.File_Knob, nuke.EvalString_Knob, nuke.Multiline_Eval_String_Knob)):
                    continue
                
                # Check if knob is animated
                if knob.isAnimated():
                    try:
                        # Try to get arraySize - this will fail for some knob types
                        has_array = hasattr(knob, 'arraySize') and knob.arraySize() > 1
                    except:
                        has_array = False
                        
                    # Handle array knobs (like transform, which has x, y, etc.)
                    if has_array:
                        for i in range(knob.arraySize()):
                            if knob.isAnimated(i):
                                try:
                                    curves = knob.animations()
                                    if i < len(curves) and curves[i]:
                                        keyframes = curves[i].keys()
                                        if keyframes:
                                            found_keyframes = True
                                            for key in keyframes:
                                                frame = key.x
                                                min_frame = min(min_frame, frame)
                                                max_frame = max(max_frame, frame)
                                except Exception as e:
                                    print(f"Error processing array knob {knob_name} on {node.name()}: {str(e)}")
                    # Handle regular animated knobs
                    else:
                        try:
                            curve = knob.animation(0)
                            if curve:
                                keyframes = curve.keys()
                                if keyframes:
                                    found_keyframes = True
                                    for key in keyframes:
                                        frame = key.x
                                        min_frame = min(min_frame, frame)
                                        max_frame = max(max_frame, frame)
                        except Exception as e:
                            print(f"Error processing knob {knob_name} on {node.name()}: {str(e)}")
            except Exception as e:
                print(f"Error accessing knob {knob_name} on {node.name()}: {str(e)}")
                continue
        
        # Check if node is a group or gizmo and scan its internals
        if node.Class() in ("Group", "Gizmo"):
            try:
                # Enter the group/gizmo context
                with node:
                    # Get all nodes inside the group/gizmo
                    internal_nodes = nuke.allNodes(recurseGroups=False)
                    # Scan each internal node
                    for internal_node in internal_nodes:
                        scan_node_for_keyframes(internal_node)
            except Exception as e:
                print(f"Error scanning inside {node.name()}: {str(e)}")
        
    # Scan all selected nodes
    for n in selected_nodes:
        try:
            scan_node_for_keyframes(n)
        except Exception as e:
            print(f"Error scanning node {n.name()}: {str(e)}")
        
    # Restore the selection
    for n in selected_nodes:
        n.setSelected(True)
    
    if not found_keyframes:
        nuke.message("No keyframes found in selected nodes")
    else:
        # Remove existing animation from rangeValue knob
        value_knob = node['rangeValue']
        value_knob.clearAnimated()
        
        # Create fresh animation
        value_knob.setAnimated()
        
        # Set keyframes
        print(f"Setting keyframes: {min_frame-1}:1, {min_frame}:0, {max_frame}:0, {max_frame+1}:1")
        value_knob.setValueAt(1, min_frame - 1)  # 1 - node enabled
        value_knob.setValueAt(0, min_frame)      # 0 - node disabled
        value_knob.setValueAt(0, max_frame)      # 0 - node disabled
        value_knob.setValueAt(1, max_frame + 1)  # 1 - node enabled
        
        # Ensure animation curve is set to constant interpolation
        for curve in value_knob.animations():
            if curve:
                for key in curve.keys():
                    key.interpolation = nuke.CONSTANT
        
        # Update range values
        print(f"Setting range knobs - Start: {int(min_frame)}, End: {int(max_frame)}")
        node['rangeStart'].setValue(int(min_frame))
        node['rangeEnd'].setValue(int(max_frame))
        
        print(f"Updated KeyframeRange noOp with animation from frame {min_frame - 1} to {max_frame + 1}")
        print(f"First keyframe found at frame: {min_frame}")
        print(f"Last keyframe found at frame: {max_frame}")
"""
    
    recalc_button = nuke.PyScript_Knob("recalculate", "Recalculate Range", recalc_script)
    noOp.addKnob(recalc_button)
    
    # Set keyframes on the value knob
    # Make sure the knob is animated first
    value_knob.setAnimated()
    
    # Frame before first keyframe (1 - node enabled)
    value_knob.setValueAt(1, min_frame - 1)
    # First keyframe (0 - node disabled)
    value_knob.setValueAt(0, min_frame)
    # Last keyframe (0 - node disabled)
    value_knob.setValueAt(0, max_frame)
    # Frame after last keyframe (1 - node enabled)
    value_knob.setValueAt(1, max_frame + 1)
    
    # Ensure animation curve is set to constant interpolation for clean transitions
    for curve in value_knob.animations():
        if curve:
            for key in curve.keys():
                key.interpolation = nuke.CONSTANT
    
    # Display information
    print(f"Created KeyframeRange noOp with animation from frame {min_frame - 1} to {max_frame + 1}")
    print(f"First keyframe found at frame: {min_frame}")
    print(f"Last keyframe found at frame: {max_frame}")

# If this script is imported as a module, we don't want to automatically run it
# if __name__ == "__main__":
#     create_keyframe_range_noOp()

# # To add this script to the toolbar, save it to your .nuke folder as keyframe_range.py
# # and add this to your menu.py:
# """
# toolbar = nuke.toolbar("Nodes")
# toolbar.addCommand("Custom/KeyframeRange", "import keyframe_range; keyframe_range.create_keyframe_range_noOp()")
# """