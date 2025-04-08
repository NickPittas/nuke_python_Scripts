import nuke
import os
import re
import shutil

def get_version_from_script_name(script_name):
    version_match = re.search(r'v(\d+)', script_name)
    if version_match:
        version_num = int(version_match.group(1))
        return f"v{version_num:03d}"
    return 'v001'

def create_render_path():
    write_node = nuke.thisNode()
    project_path = nuke.root().name().replace('\\', '/')
    
    script_name = os.path.splitext(os.path.basename(project_path))[0]
    script_name_no_spaces = script_name.replace(' ', '_')
    
    path_parts = re.split(r'/|\\', project_path)
    projects_index = next((i for i, part in enumerate(path_parts) if part.lower() == 'projects'), -1)
    
    if projects_index != -1:
        project_root = '/'.join(path_parts[:projects_index])
    else:
        project_root = nuke.getFilename('Select project root directory', default=os.path.dirname(project_path))
        if not project_root:
            nuke.message("No project path selected. Aborting.")
            return
    
    # Ensure project_root doesn't end with a slash
    project_root = project_root.rstrip('/')
    
    version = get_version_from_script_name(script_name)
    script_name_with_version = f"{script_name_no_spaces}_{version}"
    
    file_type = write_node['custom_file_type'].value()
    
    base_path = os.path.join(project_root, 'Renders', 'Nuke', script_name_no_spaces, version).replace('\\', '/')
    
    if file_type == 'EXR':
        render_path = f"{base_path}/EXR/{script_name_no_spaces}_{version}.####.exr"
    else:  # MOV
        render_path = f"{base_path}/MOV/{script_name_no_spaces}_{version}.mov"
    
    os.makedirs(os.path.dirname(render_path), exist_ok=True)
    
    script_copy_name = f"{script_name_with_version}.nk"
    script_copy_path = f"{base_path}/{script_copy_name}"
    shutil.copy2(project_path, script_copy_path)
    
    write_node['file'].setValue(render_path)
    write_node['file_type'].setValue(file_type.lower())
    
    nuke.message(f"Render path set. Folder structure created.\nScript copied to: {script_copy_path}")

def add_custom_knobs():
    write_node = nuke.thisNode()
    if write_node.Class() != 'Write':
        return

    if 'custom_file_type' not in write_node.knobs():
        file_type_knob = nuke.Enumeration_Knob('custom_file_type', 'File Type', ['EXR', 'MOV'])
        button = nuke.PyScript_Knob('create_render_path', 'Create Render Path', 'custom_write_node.create_render_path()')
        
        write_node.addKnob(file_type_knob)
        write_node.addKnob(button)

nuke.addOnCreate(add_custom_knobs, nodeClass='Write')