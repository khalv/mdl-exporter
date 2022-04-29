import bpy

from bpy.props import PointerProperty   
from bpy.types import Panel  

from ..properties.War3LightSettings import War3LightSettings
            
class WAR3_PT_light_panel(Panel):  
    """Displays light properties in the lamp panel"""
    bl_idname = "WAR3_PT_light_panel"
    bl_label = "MDL Light Settings"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'data'
    
    @classmethod
    def register(cls):
        bpy.types.Light.mdl_light = PointerProperty(type=War3LightSettings)
       
    @classmethod
    def unregister(cls):
        del bpy.types.Light.mdl_light
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        return obj is not None and obj.type in ('LAMP', 'LIGHT')

    def draw(self, context):
        layout = self.layout
        data = context.active_object.data.mdl_light
        
        layout.prop(data, "light_type")
        layout.prop(data, "atten_start")
        layout.prop(data, "atten_end")
        if data.light_type != 'Ambient':
            layout.prop(data, "color")
            layout.prop(data, "intensity")
        else:
            layout.prop(data, "amb_color")
            layout.prop(data, "amb_intensity")