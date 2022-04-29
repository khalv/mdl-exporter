import bpy
from bpy.props import PointerProperty
from bpy.types import Panel

from ..properties.War3BillboardProperties import War3BillboardProperties

class WAR3_PT_billboard_panel(Panel):  
    """Displays billboard settings in the Object panel"""
    bl_idname = "WAR3_PT_billboard_panel"
    bl_label = "MDL Billboard Options"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'object'
    
    @classmethod
    def register(cls):
        bpy.types.Object.mdl_billboard = PointerProperty(type=War3BillboardProperties)
       
    @classmethod
    def unregister(cls):
        del bpy.types.Object.mdl_billboard
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        
        if obj is None:
            return False
            
        if obj.type == 'EMPTY' and obj.name.lower().startswith("bone"):
            return True
            
        if obj.type in ('LAMP', 'LIGHT'):
            return True
            
        if obj.name.endswith(" Ref"):
            return True
                
        return False

    def draw(self, context):
        layout = self.layout
        data = context.active_object.mdl_billboard
        layout.prop(data, "billboarded")
        layout.prop(data, "billboard_lock_x")
        layout.prop(data, "billboard_lock_y")
        layout.prop(data, "billboard_lock_z")