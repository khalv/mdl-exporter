import bpy

from bpy.props import (
        FloatProperty,
        IntProperty,
        EnumProperty,
        BoolProperty,
        StringProperty,
        CollectionProperty,
        FloatVectorProperty,
        IntVectorProperty,
        PointerProperty
        )
    
from bpy.types import PropertyGroup
        
class ParticleSystemSettings(PropertyGroup):

    emitter_type = EnumProperty(
        name = "Emitter Type",
        items = [('ParticleEmitter', "Model Emitter", ""),
                 ('ParticleEmitter2', "Particle Emitter", ""),
                 ('RibbonEmitter', "Ribbon Emitter", "")],
        default = 'ParticleEmitter2'
        )

    filter_mode = EnumProperty(
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
 
    unshaded = BoolProperty(
        name = "Unshaded",
        description = "Whether or not to apply shadows to this layer.",
        default = False
        )
    unfogged = BoolProperty(
        name = "Unfogged",
        description = "Whether or this layer will be affected by fog.",
        default = False
        )
        
    line_emitter = BoolProperty(
        name = "Line Emitter",
        description = "If true, particles will move in a 2D plane.",
        default = False    
        )
        
    sort_far_z = BoolProperty(
        name = "Sort Far Z",
        description = "If true, particles from this emitter will be rendered front to back.",
        default = False
        )
        
    model_space = BoolProperty(
        name = "Model Space",
        description = "Whether or not particles should be simulated relative to their parent object.",
        default = False    
        )
        
    xy_quad = BoolProperty(
        name = "XY Quad",
        description = "If true, particles will appear as flat planes facing upwards.",
        default = False    
        )
        
    head = BoolProperty(
        name = "Head",
        description = "Whether or not to render the head of the particle.",
        default = True 
        )
        
    tail = BoolProperty(
        name = "Tail",
        description = "Whether or not to render the tail of the particle. Tails will stretch along the direction of velocity.",
        default = False
        )
       
    emission_rate = IntProperty(
        name = "Emission Rate",
        description = "Amount of particles emitted per second.",
        options = {'ANIMATABLE'},
        min = 0,
        default = 100
        )
    speed = IntProperty(
        name = "Speed",
        description = "The velocity of each particle.",
        options = {'ANIMATABLE'},
        default = 100
        )
        
    latitude = IntProperty(
        name = "Latitude",
        description = "How far particles can deviate from the emisison axis.",
        options = {'ANIMATABLE'},
        # subtype = 'ANGLE',
        # unit = 'ROTATION',
        min = 0,
        max = 180,
        default = 0
        )
        
    longitude = FloatProperty(
        name = "Longitude",
        description = "Maximum cone angle of the emitter.",
        default = 0
        )
        
    variation = FloatProperty(
        name = "Variation",
        description = "Maximum percentage of the base speed at which the emission velocity of a particle might vary.",
        options = {'ANIMATABLE'},
        default = 0,
        min = 0
        )
        
    gravity = FloatProperty(
        name = "Gravity",
        description = "The amount of downwards velocity applied to the particle each second. Can be negative.",
        options = {'ANIMATABLE'},
        default = 0
        )
        
    start_color = FloatVectorProperty(
        name = "",
        description = "Color of the particle at the start of its lifetime.",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0)
        )
        
    mid_color = FloatVectorProperty(
        name = "",
        description = "Color of the particle at the middle of its lifetime.",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0)
        )
        
    end_color = FloatVectorProperty(
        name = "",
        description = "Color of the particle at the end of its lifetime.",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0)
        )
        
    start_alpha = IntProperty(
        name = "",
        min = 0,
        max = 255,
        default = 255
        )
        
    mid_alpha = IntProperty(
        name = "",
        min = 0,
        max = 255,
        default = 255
        )
        
    end_alpha = IntProperty(
        name = "",
        min = 0,
        max = 255,
        default = 255
        )
        
    start_scale = IntProperty(
        name = "",
        min = 0,
        default = 1
        )
        
    mid_scale = IntProperty(
        name = "",
        min = 0,
        default = 1
        )
        
    end_scale = IntProperty(
        name = "",
        min = 0,
        default = 1
        )
        
    rows = IntProperty(
        name = "",
        min = 1,
        default = 1
    )
    
    cols = IntProperty(
        name = "",
        min = 1,
        default = 1
    )
    
    life_span = FloatProperty(
        name = "Lifespan",
        description = "How long the particle will last (in seconds)",
        subtype = 'TIME',
        unit = 'TIME',
        min = 0.0,
        default = 1.0
        )
        
    tail_length = FloatProperty(
        name = "Tail Length",
        description = "Length of the tail relative to its width.",
        min = 0
        )
        
    time = FloatProperty(
        name = "Time",
        description = "This value controls how long it takes to transition between the start and the middle segments.",
        min = 0.0,
        max = 1.0,
        default = 0.5
        )
        
    priority_plane = IntProperty(
        name = "Priority Plane",
        description = "Higher priority particles will render over lower priorities.",
        default = 0
    )
    
    ribbon_material = PointerProperty(
        name = "Ribbon Material",
        type=bpy.types.Material
        )
        
    ribbon_color = FloatVectorProperty(
        name = "Color",
        subtype = 'COLOR',
        default = (1.0, 1.0, 1.0)
        )
        
    texture_path = StringProperty(
        name = "Texture Path",
        default = "",
        maxlen = 128
        )
        
    model_path = StringProperty(
        name = "Model Path",
        default = "",
        maxlen = 128
        )
        
    head_life_start = IntProperty(
        name = "",
        default = 0
        )
        
    head_life_end = IntProperty(
        name = "",
        default = 0
        )
        
    head_life_repeat = IntProperty(
        name = "",
        default = 1
        )
        
    head_decay_start = IntProperty(
        name = "",
        default = 0
        )
        
    head_decay_end = IntProperty(
        name = "",
        default = 0
        )
        
    head_decay_repeat = IntProperty(
        name = "",
        default = 1
        )
        
    tail_life_start = IntProperty(
        name = "",
        default = 0
        )
        
    tail_life_end = IntProperty(
        name = "",
        default = 0
        )
        
    tail_life_repeat = IntProperty(
        name = "",
        default = 1
        )
        
    tail_decay_start = IntProperty(
        name = "",
        default = 0
        )
        
    tail_decay_end = IntProperty(
        name = "",
        default = 0
        )
        
    tail_decay_repeat = IntProperty(
        name = "",
        default = 1
        )
        
    alpha = FloatProperty(
        name = "Alpha",
        description = "Transparency of the material.",
        default = 1.0
        )
        
    @classmethod
    def register(cls):
        bpy.types.ParticleSettings.mdl_particle_sys = PointerProperty(type=ParticleSystemSettings)
        
    @classmethod
    def unregister(cls):
        del bpy.types.ParticleSettings.mdl_particle_sys
        
class CUSTOM_PT_ParticleEditorPanel(bpy.types.Panel):
    """Creates a particle editor Panel in the Particles window"""
    bl_idname = "OBJECT_PT_particle_editor_panel"
    bl_label = "MDL Particle Emitter"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'particle'
    
    @classmethod
    def poll(self, context):
        return context.active_object is not None and len(context.active_object.particle_systems)
    
    def draw(self, context):
        layout = self.layout
        
        psys = context.active_object.particle_systems.active.settings.mdl_particle_sys
        
        layout.prop(psys, "emitter_type")
        
        if psys.emitter_type == 'ParticleEmitter':
            layout.prop(psys, "model_path")
            layout.prop(psys, "emission_rate")
            layout.prop(psys, "life_span")
            layout.prop(psys, "speed")
            layout.prop(psys, "gravity")
            
            layout.separator()
            
            layout.label("Emission Cone")
            layout.prop(psys, "longitude")
            layout.prop(psys, "latitude")
            
        elif psys.emitter_type == 'RibbonEmitter':
            layout.prop_search(psys, "ribbon_material", bpy.data, "materials")
            layout.prop(psys, "texture_path")
            layout.separator()
            
            layout.prop(psys, "ribbon_color")
            
            layout.separator()
            
            layout.prop(psys, "emission_rate")
            layout.prop(psys, "life_span")
            layout.prop(psys, "gravity")
            
            layout.label("Spritesheet Size")
            row = layout.row()
            col = row.column()
            col.label("Rows")
            col.prop(psys, "rows")
            col = row.column()
            col.label("Columns")
            col.prop(psys, "cols")
        else:
            layout.prop(psys, "texture_path")
            layout.prop(psys, "filter_mode")
            
            layout.separator()
            
            layout.prop(psys, "emission_rate")
            layout.prop(psys, "speed")
            layout.prop(psys, "life_span")
            layout.prop(psys, "gravity")
            layout.prop(psys, "variation")
            layout.prop(psys, "latitude")
            
            if psys.tail == True:
                layout.prop(psys, "tail_length")
            
            layout.separator()
            
            layout.label("Segments")
            row = layout.row()
            box = row.box()
            box.label("Color")
            box.prop(psys, "start_color")
            box.label("Alpha")
            box.prop(psys, "start_alpha")
            box.label("Scale")
            box.prop(psys, "start_scale")
            box = row.box()
            box.label("Color")
            box.prop(psys, "mid_color")
            box.label("Alpha")
            box.prop(psys, "mid_alpha")
            box.label("Scale")
            box.prop(psys, "mid_scale")
            box = row.box()
            box.label("Color")
            box.prop(psys, "end_color")
            box.label("Alpha")
            box.prop(psys, "end_alpha")
            box.label("Scale")
            box.prop(psys, "end_scale")
            
            layout.prop(psys, "time")
            
            layout.separator()
            
            layout.label("Spritesheet Size")
            row = layout.row()
            col = row.column()
            col.label("Rows")
            col.prop(psys, "rows")
            col = row.column()
            col.label("Columns")
            col.prop(psys, "cols")
            
            layout.separator()
            
            layout.label("Head Sprite Settings")
            row = layout.row()
            col = row.column()
            col.label("Birth")
            box = col.box()
            box.label("Start")
            box.prop(psys, "head_life_start")
            box.label("End")
            box.prop(psys, "head_life_end")
            box.label("Repeat")
            box.prop(psys, "head_life_repeat")
            
            
            col = row.column()
            col.label("Decay")
            box = col.box()
            box.label("Start")
            box.prop(psys, "head_decay_start")
            box.label("End")
            box.prop(psys, "head_decay_end")
            box.label("Repeat")
            box.prop(psys, "head_decay_repeat")
            layout.separator()
            
            layout.label("Tail Sprite Settings")
            row = layout.row()
            col = row.column()
            col.label("Birth")
            box = col.box()
            box.label("Start")
            box.prop(psys, "tail_life_start")
            box.label("End")
            box.prop(psys, "tail_life_end")
            box.label("Repeat")
            box.prop(psys, "tail_life_repeat")
            
            
            col = row.column()
            col.label("Decay")
            box = col.box()
            box.label("Start")
            box.prop(psys, "tail_decay_start")
            box.label("End")
            box.prop(psys, "tail_decay_end")
            box.label("Repeat")
            box.prop(psys, "tail_decay_repeat")
            
            row = layout.row()
            col = row.column()
            col.prop(psys, "unshaded")
            col.prop(psys, "unfogged")
            col.prop(psys, "line_emitter")
            col.prop(psys, "sort_far_z")
            col = row.column()
            col.prop(psys, "model_space")
            col.prop(psys, "xy_quad")
            col.prop(psys, "head")
            col.prop(psys, "tail")