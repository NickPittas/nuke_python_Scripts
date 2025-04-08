import nuke
import nukescripts

class ProxyPanel(nukescripts.PythonPanel):
    def __init__(self):
        nukescripts.PythonPanel.__init__(self, 'Proxy Panel', 'com.example.ProxyPanel')
        
        # Create knobs
        self.proxy = nuke.Boolean_Knob('proxy', 'Enable Proxy')
        self.proxy.setFlag(nuke.STARTLINE)
        self.proxy.setTooltip("Enable or disable proxy mode")

        self.full_rez = nuke.WH_Knob('full_rez', 'Full Resolution')
        self.full_rez.setTooltip("Set the full resolution width and height")
        self.set_full_rez = nuke.PyScript_Knob('set_full_rez', 'Set Full Res from Node')
        self.set_full_rez.setTooltip("Set full resolution from selected node")
        self.proxy_rez = nuke.WH_Knob('proxy_rez', 'Proxy Resolution')
        self.proxy_rez.setTooltip("Set the proxy resolution width and height")
        self.set_proxy_rez = nuke.PyScript_Knob('set_proxy_rez', 'Set Proxy Res from Node')
        self.set_proxy_rez.setTooltip("Set proxy resolution from selected node")

        self.resize_x = nuke.Double_Knob('resize_x', 'Resize Ratio')
        self.resize_x.setEnabled(False)
        self.resize_x.setFlag(nuke.STARTLINE)
        self.resize_x.setTooltip("Calculated resize ratio (Full Res / Proxy Res)")

        self.create_transform = nuke.PyScript_Knob('create_transform', 'Create Transform Node')
        self.create_transform.setFlag(nuke.STARTLINE)
        self.create_transform.setTooltip("Create a Transform node with dynamic scale")

        # Add dividers for better organization
        self.divider1 = nuke.Text_Knob("divider1", "")
        self.divider2 = nuke.Text_Knob("divider2", "")
        
        # Add knobs to the panel
        for k in (self.proxy, self.divider1, 
                  self.full_rez, self.set_full_rez, 
                  self.proxy_rez, self.set_proxy_rez, 
                  self.divider2, self.resize_x, self.create_transform):
            self.addKnob(k)
        
        # Set default values
        self.full_rez.setValue([1920, 1080])
        self.proxy_rez.setValue([960, 540])
        
        # Initial update of resize ratio
        self.update_resize_ratio()
        
    def knobChanged(self, knob):
        if knob in (self.full_rez, self.proxy_rez, self.proxy):
            self.update_resize_ratio()
        elif knob == self.set_full_rez:
            self.set_resolution_from_node(self.full_rez)
        elif knob == self.set_proxy_rez:
            self.set_resolution_from_node(self.proxy_rez)
        elif knob == self.create_transform:
            self.create_transform_node()
        
        # Update all TCL variables
        self.update_tcl_variables()
    
    def update_resize_ratio(self):
        full_w, full_h = self.full_rez.value()
        proxy_w, proxy_h = self.proxy_rez.value()
        if proxy_w != 0 and proxy_h != 0:
            ratio = full_w / proxy_w
            if self.proxy.value():
                ratio = 1 / ratio if ratio != 0 else 1
            else:
                ratio = 1
            self.resize_x.setValue(ratio)
        else:
            self.resize_x.setValue(1.0)

    def update_tcl_variables(self):
        nuke.tcl(f'set ::proxy_panel_proxy {int(self.proxy.value())}')
        full_w, full_h = self.full_rez.value()
        nuke.tcl(f'set ::proxy_panel_full_rez_width {full_w}')
        nuke.tcl(f'set ::proxy_panel_full_rez_height {full_h}')
        proxy_w, proxy_h = self.proxy_rez.value()
        nuke.tcl(f'set ::proxy_panel_proxy_rez_width {proxy_w}')
        nuke.tcl(f'set ::proxy_panel_proxy_rez_height {proxy_h}')
        nuke.tcl(f'set ::proxy_panel_resize_ratio {self.resize_x.value()}')

    def set_resolution_from_node(self, target_knob):
        selected_node = nuke.selectedNode()
        if selected_node:
            width = selected_node.width()
            height = selected_node.height()
            target_knob.setValue([width, height])
            self.update_resize_ratio()
        else:
            nuke.message("Please select a node first.")

    def create_transform_node(self):
        selected_node = nuke.selectedNode()
        if selected_node:
            transform = nuke.createNode('Sphere_Proxy')
            transform.setInput(0, selected_node)
        else:
            nuke.message("Please select a node first.")


    def showModalDialog(self):
        result = nukescripts.PythonPanel.showModalDialog(self)
        return result

# Global variable to store the panel instance
proxy_panel = None

def create_proxy_panel():
    global proxy_panel
    if proxy_panel is None:
        proxy_panel = ProxyPanel()
    return proxy_panel

def show_proxy_panel():
    panel = create_proxy_panel()
    panel.show()

# Initialize the TCL-accessible variables
nuke.tcl('set ::proxy_panel_proxy 0')
nuke.tcl('set ::proxy_panel_full_rez_width 1920')
nuke.tcl('set ::proxy_panel_full_rez_height 1080')
nuke.tcl('set ::proxy_panel_proxy_rez_width 960')
nuke.tcl('set ::proxy_panel_proxy_rez_height 540')
nuke.tcl('set ::proxy_panel_resize_ratio 1.0')

# Add the panel to Nuke's Custom Panels menu
nuke.menu('Pane').addCommand('ProxyPanel', show_proxy_panel)
