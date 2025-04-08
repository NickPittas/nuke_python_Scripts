# Nuke Python Scripts

A collection of utility scripts for Foundry's Nuke.

## Installation
1. Copy these scripts to your Nuke scripts directory:
   - Windows: `%USERPROFILE%/.nuke`
   - Mac: `~/Library/Application Support/Nuke`
   - Linux: `~/.nuke`
2. Add the following to your `init.py` or `menu.py`:

```python
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
```

## Scripts Description

### Write Node Tools
- **custom_write_node.py**: Adds custom knobs to Write nodes with automatic path creation and version control. Creates organized render directories with EXR/MOV output options.
- **WriteNodeKENT**: Advanced Write node system with template-based file path management and colorspace control.

### Render Management
- **render_progress_panel.py** / **render_progress_panel2.py**: Provides a panel to monitor render progress with detailed statistics and time estimates.
- **version_increment.py**: Utility for managing version numbers in Nuke scripts and rendered outputs.

### Sequence Tools
- **Sequence_Browser.py**: File browser specifically designed for image sequences and movie files.
- **ReadtoFrameRange.py**: Automatically sets frame ranges based on input sequences.
- **FindKeyframes.py**: Helps identify and work with keyframes in animations.
- **reduceKeyframes.py**: Optimizes animations by reducing unnecessary keyframes.

### Utility Panels
- **proxy_panel.py**: Interface for managing proxy resolution settings.
- **search_replace_panel.py**: Panel for finding and replacing text in node parameters.
- **ffmpeg_convert.py**: Integration with FFmpeg for video format conversion.

### Other Tools
- **SphereResolutionLL180.py**: Utility for working with spherical/360° content.

## Usage

After installation, these tools will be available in Nuke's interface:
- Write node tools will automatically add custom knobs to new Write nodes
- Panels can be accessed through Nuke's Windows menu or via Python commands
- Other utilities can be called through Nuke's Script Editor or custom menu items

## Requirements
- Nuke 11.0 or later
- Python 2.7+ (compatible with Python 3 for newer Nuke versions)
- FFmpeg (for ffmpeg_convert.py)