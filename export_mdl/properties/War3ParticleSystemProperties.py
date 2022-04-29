import bpy

from bpy.props import (
        FloatProperty,
        IntProperty,
        EnumProperty,
        BoolProperty,
        StringProperty,
        FloatVectorProperty,
        PointerProperty
        )
  
from bpy.types import PropertyGroup

class War3ParticleSystemProperties(PropertyGroup):

    emitter_type : EnumProperty(
        name = "Emitter Type",
        items = [('ParticleEmitter', "Model Emitter", ""),
                 ('ParticleEmitter2', "Particle Emitter", ""),
                 ('RibbonEmitter', "Ribbon Emitter", "")],
        default = 'ParticleEmitter2'
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
        default = 'Blend'
        )
 
    unshaded : BoolProperty(
        name = "Unshaded",
        description = "Whether or not to apply shadows to this layer.",
        default = False
        )
    unfogged : BoolProperty(
        name = "Unfogged",
        description = "Whether or this layer will be affected by fog.",
        default = False
        )
        
    line_emitter : BoolProperty(
        name = "Line Emitter",
        description = "If true, particles will move in a 2D plane.",
        default = False    
        )
        
    sort_far_z : BoolProperty(
        name = "Sort Far Z",
        description = "If true, particles from this emitter will be rendered front to back.",
        default = False
        )
        
    model_space : BoolProperty(
        name = "Model Space",
        description = "Whether or not particles should be simulated relative to their parent object.",
        default = False    
        )
        
    xy_quad : BoolProperty(
        name = "XY Quad",
        description = "If true, particles will appear as flat planes facing upwards.",
        default = False    
        )
        
    head : BoolProperty(
        name = "Head",
        description = "Whether or not to render the head of the particle.",
        default = True 
        )
        
    tail : BoolProperty(
        name = "Tail",
        description = "Whether or not to render the tail of the particle. Tails will stretch along the direction of velocity.",
        default = False
        )
       
    emission_rate : FloatProperty(
        name = "Emission Rate",
        description = "Amount of particles emitted per second.",
        options = {'ANIMATABLE'},
        min = 0.0,
        default = 100.0
        )
    speed : FloatProperty(
        name = "Speed",
        description = "The velocity of each particle.",
        options = {'ANIMATABLE'},
        default = 100
        )
        
    latitude : FloatProperty(
        name = "Latitude",
        description = "How far particles can deviate from the emisison axis.",
        options = {'ANIMATABLE'},
        # subtype = 'ANGLE',
        # unit = 'ROTATION',
        min = 0,
        max = 180,
        default = 0
        )
        
    longitude : FloatProperty(
        name = "Longitude",
        description = "Maximum cone angle of the emitter.",
        default = 0
        )
        
    variation : FloatProperty(
        name = "Variation",
        description = "Maximum percentage of the base speed at which the emission velocity of a particle might vary.",
        options = {'ANIMATABLE'},
        default = 0,
        min = 0
        )
        
    gravity : FloatProperty(
        name = "Gravity",
        description = "The amount of downwards velocity applied to the particle each second. Can be negative.",
        options = {'ANIMATABLE'},
        default = 0
        )
        
    start_color : FloatVectorProperty(
        name = "",
        description = "Color of the particle at the start of its lifetime.",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0)
        )
        
    mid_color : FloatVectorProperty(
        name = "",
        description = "Color of the particle at the middle of its lifetime.",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0)
        )
        
    end_color : FloatVectorProperty(
        name = "",
        description = "Color of the particle at the end of its lifetime.",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0)
        )
        
    start_alpha : IntProperty(
        name = "",
        min = 0,
        max = 255,
        default = 255
        )
        
    mid_alpha : IntProperty(
        name = "",
        min = 0,
        max = 255,
        default = 255
        )
        
    end_alpha : IntProperty(
        name = "",
        min = 0,
        max = 255,
        default = 255
        )
        
    start_scale : FloatProperty(
        name = "",
        min = 0,
        default = 1
        )
        
    mid_scale : FloatProperty(
        name = "",
        min = 0,
        default = 1
        )
        
    end_scale : FloatProperty(
        name = "",
        min = 0,
        default = 1
        )
        
    rows : IntProperty(
        name = "",
        min = 1,
        default = 1
    )
    
    cols : IntProperty(
        name = "",
        min = 1,
        default = 1
    )
    
    life_span : FloatProperty(
        name = "Lifespan",
        description = "How long the particle will last (in seconds)",
        subtype = 'TIME',
        unit = 'TIME',
        min = 0.0,
        default = 1.0
        )
        
    tail_length : FloatProperty(
        name = "Tail Length",
        description = "Length of the tail relative to its width.",
        min = 0
        )
        
    time : FloatProperty(
        name = "Time",
        description = "This value controls how long it takes to transition between the start and the middle segments.",
        min = 0.0,
        max = 1.0,
        default = 0.5
        )
        
    priority_plane : IntProperty(
        name = "Priority Plane",
        description = "Higher priority particles will render over lower priorities.",
        default = 0
    )
    
    ribbon_material : PointerProperty(
        name = "Ribbon Material",
        type=bpy.types.Material
        )
        
    ribbon_color : FloatVectorProperty(
        name = "Color",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0)
        )
        
    texture_path : StringProperty(
        name = "Texture Path",
        default = "",
        maxlen = 256
        )
        
    model_path : StringProperty(
        name = "Model Path",
        default = "",
        maxlen = 100
        )
        
    head_life_start : IntProperty(
        name = "",
        default = 0
        )
        
    head_life_end : IntProperty(
        name = "",
        default = 0
        )
        
    head_life_repeat : IntProperty(
        name = "",
        default = 1
        )
        
    head_decay_start : IntProperty(
        name = "",
        default = 0
        )
        
    head_decay_end : IntProperty(
        name = "",
        default = 0
        )
        
    head_decay_repeat : IntProperty(
        name = "",
        default = 1
        )
        
    tail_life_start : IntProperty(
        name = "",
        default = 0
        )
        
    tail_life_end : IntProperty(
        name = "",
        default = 0
        )
        
    tail_life_repeat : IntProperty(
        name = "",
        default = 1
        )
        
    tail_decay_start : IntProperty(
        name = "",
        default = 0
        )
        
    tail_decay_end : IntProperty(
        name = "",
        default = 0
        )
        
    tail_decay_repeat : IntProperty(
        name = "",
        default = 1
        )
        
    alpha : FloatProperty(
        name = "Alpha",
        description = "Transparency of the material.",
        default = 1.0
        )
        
    @classmethod
    def register(cls):
        bpy.types.ParticleSettings.mdl_particle_sys = PointerProperty(type=War3ParticleSystemProperties)
        
    @classmethod
    def unregister(cls):
        del bpy.types.ParticleSettings.mdl_particle_sys