import bpy

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       EnumProperty,
                       PointerProperty,
                       FloatVectorProperty
                       )   


class LightSettings(bpy.types.PropertyGroup):
    light_type = EnumProperty(
        name = "Type",
        items = [('Omnidirectional', "Omnidirectional", ""),
                 ('Directional', "Directional", ""),
                 ('Ambient', "Ambient", "")],
        default = 'Omnidirectional'
        )

    atten_start = FloatProperty(
        name = "Attenuation Start",
        description = "Range at which the light intensity starts to taper off.",
        min = 0,
        default = 80
        )
        
    atten_end = FloatProperty(
        name = "Attenuation End",
        description = "Maximum range of the light.",
        min = 0,
        default = 200
        )
        
    intensity = FloatProperty(
        name = "Intensity",
        min = 0,
        default = 10,
        )
       
    amb_intensity = FloatProperty(
        name = "Ambient Intensity",
        min = 0,
        default = 0
        )
    color = FloatVectorProperty(
        name = "Color",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0),
        )
        
    amb_color = FloatVectorProperty(
        name = "Ambient Color",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0),
        )
               
class CUSTOM_PT_LightPanel(bpy.types.Panel):  
    """Displays light properties in the lamp panel"""
    bl_idname = "OBJECT_PT_light_panel"
    bl_label = "MDL Light Settings"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'data'
    
    @classmethod
    def register(cls):
        bpy.types.Lamp.mdl_light = PointerProperty(type=LightSettings)
       
    @classmethod
    def unregister(cls):
        del bpy.types.Lamp.mdl_light
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        return obj is not None and obj.type == 'LAMP'

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