import nuke
import nukescripts

def setup_resolutions(resolution="8K", fps=29.97):
    """
    Set up Nuke project with selected resolution and fps.
    
    Args:
        resolution (str): Resolution to set - "8K", "10K", or "12K"
        fps (float): Frame rate to set - 29.97 or 59.94
    """
    # Validate inputs
    if resolution not in ["8K", "10K", "12K"]:
        print(f"Invalid resolution '{resolution}'. Using 8K as default.")
        resolution = "8K"
    
    if fps not in [29.97, 59.94]:
        print(f"Invalid fps '{fps}'. Using 29.97 as default.")
        fps = 29.97
    
    # Format name to search for
    format_name = f"{resolution} LL180 Sphere"
    
    # Get reference to root node
    root = nuke.root()
   
    # Set main resolution to selected format
    format_found = False
    for format in nuke.formats():
        if format.name() == format_name:
            root['format'].setValue(format)
            format_found = True
            break
    
    if not format_found:
        print(f"Warning: Format '{format_name}' not found!")
   
    # Set FPS to selected value
    root['fps'].setValue(fps)
   
    # Enable proxy mode
    root['proxy'].setValue(False)
   
    # Set proxy format to 4K Proxy LL180 Sphere
    for format in nuke.formats():
        if format.name() == "4K Proxy LL180 Sphere":
            nuke.root().knob('proxy_type').setValue(0)
            root['proxy_format'].setValue(format)            
            break
   
    # Set proxy mode to always
    nuke.root().knob('proxySetting').setValue(3)
    nuke.root().knob('colorManagement').setValue('OCIO')
    nuke.root().knob('OCIO_config').setValue('aces_1.2')
   
    print(f"Resolution set to {resolution} LL180 Sphere, FPS set to {fps}!")

def show_setup_dialog():
    """Show a dialog for selecting resolution and FPS options"""
    # Create panel
    p = nukescripts.PythonPanel("Resolution and FPS Setup")
    
    # Add knobs
    k_res = nuke.Enumeration_Knob('resolution', 'Resolution', ['8K', '10K', '12K'])
    k_fps = nuke.Enumeration_Knob('fps', 'Frame Rate', ['29.97', '59.94'])
    
    p.addKnob(k_res)
    p.addKnob(k_fps)
    
    # Show the panel
    if p.showModalDialog():
        # Get values and call the setup function
        res = p.knobs()['resolution'].value()
        fps = float(p.knobs()['fps'].value())
        setup_resolutions(res, fps)

# Add the command to Nuke's menu system


# You can also add it to a custom menu if preferred
# customMenu = menubar.addMenu("Custom Tools")
# customMenu.addCommand("Set Project Resolution", show_setup_dialog)