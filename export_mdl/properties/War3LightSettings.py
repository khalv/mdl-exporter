from bpy.props import FloatProperty, EnumProperty, FloatVectorProperty
from bpy.types import PropertyGroup

class War3LightSettings(PropertyGroup):
    light_type : EnumProperty(
        name = "Type",
        items = [('Omnidirectional', "Omnidirectional", ""),
                 ('Directional', "Directional", ""),
                 ('Ambient', "Ambient", "")],
        default = 'Omnidirectional'
        )

    atten_start : FloatProperty(
        name = "Attenuation Start",
        description = "Range at which the light intensity starts to taper off.",
        min = 0,
        default = 80
        )
        
    atten_end : FloatProperty(
        name = "Attenuation End",
        description = "Maximum range of the light.",
        min = 0,
        default = 200
        )
        
    intensity : FloatProperty(
        name = "Intensity",
        min = 0,
        default = 10,
        )
       
    amb_intensity : FloatProperty(
        name = "Ambient Intensity",
        min = 0,
        default = 0
        )
    color : FloatVectorProperty(
        name = "Color",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0),
        )
        
    amb_color : FloatVectorProperty(
        name = "Ambient Color",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0),
        )