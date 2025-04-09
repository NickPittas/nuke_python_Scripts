# Nuke Python Scripts

A collection of utility scripts for Foundry's Nuke.

## Installation
1. Copy these scripts to your Nuke scripts directory:
   - Windows: `%USERPROFILE%/.nuke`
   - Mac: `~/Library/Application Support/Nuke`
   - Linux: `~/.nuke`

2. Add the following to your `menu.py`:

```python
# Import necessary modules
import nuke
import custom_write_node
import ffmpeg_convert
import FindKeyframes
import proxy_panel
import render_progress_panel
import render_progress_panel2
import search_replace_panel
import Sequence_Browser
import version_increment
import WriteNodeKENT.WriteNodeKENT

# Create Custom Menu
toolbar = nuke.toolbar("Nodes")
m = toolbar.addMenu("Custom Tools", icon="custom_tools.png")

# Write Node Tools
m.addCommand("Custom Write", "custom_write_node.create()", icon="Write.png", shortcut="Shift+W")
m.addCommand("WriteNodeKENT", "WriteNodeKENT.WriteNodeKENT.create()", icon="Write.png", shortcut="Ctrl+Alt+W")

# Render Management
m.addCommand("Version Increment", "version_increment.increment()", icon="Version.png", shortcut="Ctrl+Alt+Up")

# Sequence Tools
m.addCommand("Set Frame Range", "ReadtoFrameRange.set_range()", icon="FrameRange.png", shortcut="Ctrl+Alt+F")
m.addCommand("Find Keyframes", "FindKeyframes.show_panel()", icon="Keys.png", shortcut="Alt+K")
m.addCommand("Reduce Keyframes", "reduceKeyframes.show_panel()", icon="Reduce.png", shortcut="Shift+Alt+K")

# Utility Panels
m.addCommand("Proxy Settings", "proxy_panel.show()", icon="Proxy.png", shortcut="Ctrl+Alt+P")
m.addCommand("Search and Replace", "search_replace_panel.show()", icon="Search.png", shortcut="Ctrl+Alt+S")
m.addCommand("FFmpeg Convert", "ffmpeg_convert.show_panel()", icon="Convert.png", shortcut="Ctrl+Alt+C")
m.addCommand("Render Progress Panel", "render_progress_panel.show_panel()", icon="Render.png", shortcut="Alt+R")
m.addCommand("Sequence Browser", "Sequence_Browser.show()", icon="Browser.png", shortcut="Ctrl+B")

# Other Tools
m.addCommand("Sphere Resolution", "SphereResolutionLL180.create()", icon="Sphere.png", shortcut="Ctrl+Alt+L")
```

## Scripts Description

### Write Node Tools
- **custom_write_node.py** (Shortcut: `Shift+W`)
  - Creates Write nodes with automatic path creation
  - Adds version control knobs
  - Template options: EXR/MOV output
  - Custom knobs: compression, colorspace, FPS

- **WriteNodeKENT** (Shortcut: `Ctrl+Alt+W`)
  - Template-based file paths
  - Automatic version control
  - Built-in presets for different deliverable types
  - Custom colorspace management

### Render Management
- **version_increment.py** (Shortcut: `Ctrl+Alt+Up`)
  - Auto-increment version numbers
  - Batch version update
  - Version history tracking

### Sequence Tools
- **ReadtoFrameRange.py** (Shortcut: `Ctrl+Alt+F`)
  - Auto-detects sequence length
  - Sets project frame range
  - Handles mixed frame ranges

- **FindKeyframes.py** (Shortcut: `Alt+K`)
  - Keyframe visualization
  - Navigation tools
  - Selection tools
  - Copy/paste keyframes

- **reduceKeyframes.py** (Shortcut: `Shift+Alt+K`)
  - Smart keyframe reduction
  - Tolerance settings
  - Preview changes
  - Undo support

### Utility Panels
- **proxy_panel.py** (Panel)
  - Quick proxy toggle
  - Resolution presets
  - Batch proxy settings

- **search_replace_panel.py** (Panel)
  - Node parameter search
  - Batch replace
  - Regular expression support
  - Search history

- **ffmpeg_convert.py** (Panel)
  - Format conversion
  - Batch processing
  - Custom presets
  - Progress monitoring

- **render_progress_panel.py** (Panel)
  - Real-time render monitoring
  - ETA calculation
  - Frame statistics
  - Error logging

  - **Sequence_Browser.py** (Panel)
  - Thumbnail preview
  - Sequence detection
  - Format filtering
  - Quick import options

### Other Tools
- **SphereResolutionLL180.py** (Shortcut: `Ctrl+Alt+L`)
  - 360° content tools
  - Resolution calculator
  - Format presets

## Requirements
- Nuke 11.0 or later
- Python 2.7+ (compatible with Python 3 for newer Nuke versions)
- FFmpeg (for ffmpeg_convert.py)
  - Windows: Add FFmpeg to PATH
  - Mac/Linux: Install via package manager

## Custom Icons
Place your custom icons in:
- Windows: `%USERPROFILE%/.nuke/icons/`
- Mac: `~/Library/Application Support/Nuke/icons/`
- Linux: `~/.nuke/icons/`