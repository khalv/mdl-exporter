import os

from bpy.types import Operator
from bpy.props import EnumProperty

def load_texture_list():
    directory = os.path.dirname(__file__)
        
    path = os.path.join(directory, "../textures.txt")
    l = []
    with open(path, 'r') as f:
        l = [(line[:-1], os.path.basename(line[:-1]), os.path.basename(line[:-1])) for line in f.readlines()]
        
    return l
    
texture_paths = load_texture_list()
     
class WAR3_OT_search_texture(Operator):
    bl_idname = "object.search_texture"
    bl_label = "Search"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_property = "path"
    
    target : EnumProperty(
                name = "Target Type",
                items = [('Emitter', 'Emitter', ''),
                         ('Material', 'Material', '')]
            )
    
    path : EnumProperty(
                name = "Path",
                items = texture_paths
            )
    
    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}
        
    def execute(self, context):
        try:
            if self.target == 'Material':
                mat = context.active_object.active_material
                i = mat.mdl_layer_index
                item = mat.mdl_layers[i]
                item.path = self.path
            else:
                psys = context.active_object.particle_systems.active.settings.mdl_particle_sys
                psys.texture_path = self.path
                
        except IndexError:
            pass
            
        return {'FINISHED'}