import bpy

from bpy.props import (
        FloatProperty,
        IntProperty,
        EnumProperty,
        BoolProperty,
        StringProperty,
        CollectionProperty,
        )
  
from bpy.types import PropertyGroup

class War3MaterialLayerProperties(PropertyGroup):
    name : StringProperty(
        name = "Name",
        description = "Name of this layer - this value is not exported.",
        default = "Layer",
        maxlen = 16
        )
        
    texture_type : EnumProperty(
        name = "Texture Type",
        items = [('0', "Image", "", 0, 0),
                 ('1', "Team Color", "", 0, 1),
                 ('2', "Team Glow", "", 0, 2),
                 ('11', "Cliff", "", 0, 11),
                 ('31', "Lordaeron Tree", "", 0, 31),
                 ('32', "Ashenvale Tree", "", 0, 32),
                 ('33', "Barrens Tree", "", 0, 33),
                 ('34', "Northrend Tree", "", 0, 34),
                 ('35', "Mushroom Tree", "", 0, 35),
                 ('36', "Replaceable ID", "", 0, 36)],
        default = '0'
        )
        
    replaceable_id : IntProperty(
        name = "ID",
        description = "ID of the replaceable texture.",
        default = 100,
        min = 0
        )
        
    filter_mode : EnumProperty(
        name = "Filter Mode",
        items = [('None', "Opaque", ""),
                 ('Blend', "Blend", ""),
                 ('Transparent', "Transparent", ""),
                 ('Additive', "Additive", ""),
                 ('AddAlpha', "Additive Alpha", ""),
                 ('Modulate', "Modulate", ""),
                 ('Modulate2x', "Modulate 2X", "")],
        default = 'None'
        )
        
    unshaded : BoolProperty(
        name = "Unshaded",
        description = "Whether or not to apply shadows to this layer.",
        default = False
        )
        
    two_sided : BoolProperty(
        name = "Two Sided",
        description = "Whether or not to render backfaces.",
        default = False
        )
        
    no_depth_test : BoolProperty(
        name = "No Depth Test",
        description = "If true, this layer will always render, even if it's occluded.",
        default = False    
        )
        
    no_depth_set : BoolProperty(
        name = "No Depth Set",
        description = "If true, this layer will never occlude other objects which are rendered afterwards.",
        default = False    
        )
        
    alpha : FloatProperty(
        name = "Alpha",
        description = "Alpha factor used with the blend filter mode. Can be animated.",
        default = 1.0,
        options = {'ANIMATABLE'},
        min = 0.0,
        max = 1.0
        )
    path : StringProperty(
        name = "Texture Path",
        default = "",
        maxlen = 256
        )
     
    @classmethod
    def register(cls):
        bpy.types.Material.mdl_layers = CollectionProperty(type=War3MaterialLayerProperties, options={'HIDDEN'})
        bpy.types.Material.mdl_layer_index = IntProperty(name="Layer index", description="", default=0, options={'HIDDEN'}) 
        bpy.types.Material.priority_plane = IntProperty(name="Priority Plane", description="Order at which this material will be rendered", default=0, options={'HIDDEN'})
     
    @classmethod    
    def unregister(cls):
        del bpy.types.Material.mdl_layers
        del bpy.types.Material.mdl_layer_index
        del bpy.types.Material.priority_plane