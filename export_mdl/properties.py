import bpy
import os

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
from bpy.app.handlers import persistent

@persistent
def sequence_changed_handler(self):

    context = bpy.context
    # Prevent recursion
    if context.window_manager.mdl_sequence_refreshing:
        return
        
    context.window_manager.mdl_sequence_refreshing = True
    markers = set()
    
    sequences = context.scene.mdl_sequences
    
    for marker in context.scene.timeline_markers:
        if len([m for m in context.scene.timeline_markers if m.name == marker.name]) == 2:
            markers.add(marker.name)
            
    for marker in markers:
        if marker not in sequences:
            s = sequences.add()
            s.name = marker
            if any(tag in s.name.lower() for tag in ['attack', 'death', 'decay']):
                s.non_looping = True
        
    for sequence in sequences.values():
        if sequence.name not in markers:
            index = sequences.find(sequence.name)
            if context.scene.mdl_sequence_index >= index:
                context.scene.mdl_sequence_index = index-1
            sequences.remove(index)
        
    context.window_manager.mdl_sequence_refreshing = False

def set_sequence_name(self, value):
    for marker in bpy.context.scene.timeline_markers:
        if marker.name == self.name:
            marker.name = value
    self.name = value
    
def get_sequence_name(self):
    return self.name

class War3SequenceProperties(PropertyGroup):

    # Backing field
    
    name_display = StringProperty(
        name = "Name",
        default = "",
        get = get_sequence_name,
        set = set_sequence_name
        )

    name = StringProperty(
        name = "",
        default = "Sequence",
        )

    rarity = IntProperty(
        name = "Rarity",
        description = "How rarely this sequence should play.",
        default = 0,
        min = 0
        )
        
    non_looping = BoolProperty(
        name = "Non Looping",
        default = False
        )
        
    move_speed = IntProperty(
        name = "Movement Speed",
        description = "The unit movement speed at which this animation will play at 100% speed.",
        default = 270,
        min = 0
        )
                    
    @classmethod
    def register(cls):
        bpy.types.Scene.mdl_sequences = CollectionProperty(type=War3SequenceProperties, options={'HIDDEN'})
        bpy.types.Scene.mdl_sequence_index = IntProperty(name="Sequence index", description="", default=0, options={'HIDDEN'}) 
        bpy.types.WindowManager.mdl_sequence_refreshing = BoolProperty(name="", description="", default=False, options={'HIDDEN'})
        
        if sequence_changed_handler not in bpy.app.handlers.scene_update_post:
            bpy.app.handlers.scene_update_post.append(sequence_changed_handler)
     
    @classmethod    
    def unregister(cls):
        del bpy.types.Scene.mdl_sequences
        del bpy.types.Scene.mdl_sequence_index  
        del bpy.types.WindowManager.mdl_sequence_refreshing

        if sequence_changed_handler in bpy.app.handlers.scene_update_post:
            bpy.app.handlers.scene_update_post.remove(sequence_changed_handler)        

class War3MaterialLayerProperties(PropertyGroup):
    name = StringProperty(
        name = "Name",
        description = "Name of this layer - this value is not exported.",
        default = "Layer",
        maxlen = 16
        )
        
    texture_type = EnumProperty(
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
        
    replaceable_id = IntProperty(
        name = "ID",
        description = "ID of the replaceable texture.",
        default = 100,
        min = 0
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
        default = 'None'
        )
        
    unshaded = BoolProperty(
        name = "Unshaded",
        description = "Whether or not to apply shadows to this layer.",
        default = False
        )
        
    two_sided = BoolProperty(
        name = "Two Sided",
        description = "Whether or not to render backfaces.",
        default = False
        )
        
    no_depth_test = BoolProperty(
        name = "No Depth Test",
        description = "If true, this layer will always render, even if it's occluded.",
        default = False    
        )
        
    no_depth_set = BoolProperty(
        name = "No Depth Set",
        description = "If true, this layer will never occlude other objects which are rendered afterwards.",
        default = False    
        )
        
    alpha = FloatProperty(
        name = "Alpha",
        description = "Alpha factor used with the blend filter mode. Can be animated.",
        default = 1.0,
        options = {'ANIMATABLE'},
        min = 0.0,
        max = 1.0
        )
    path = StringProperty(
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

class War3BillboardProperties(PropertyGroup):
    billboarded = BoolProperty(
        name = "Billboarded",
        description = "If true, this object will always face the camera.",
        default = False
        )
    billboard_lock_x = BoolProperty(
        name = "Billboard Lock X",
        description = "Limits billboarding around the X axis.",
        default = False,
        )
    billboard_lock_y = BoolProperty(
        name = "Billboard Lock Y",
        description = "Limits billboarding around the Y axis.",
        default = False
        )
    billboard_lock_z = BoolProperty(
        name = "Billboard Lock Z",
        description = "Limits billboarding around the Z axis.",
        default = False
        )
        
class War3EventTypesContainer:

    def __init__(self):
        self.enums = {}
        
        directory = os.path.dirname(__file__)
        
        path = os.path.join(directory, "sound_types.txt")
        l = []
        
        with open(path, 'r') as f:
            for i in f.readlines():
                enum = i.split(" ")
                l.append((enum[0], enum[1][:-1], ""))
        
        self.enums['SND'] = l

        path = os.path.join(directory, "splat_types.txt")
        l = []
        
        with open(path, 'r') as f:
            for i in f.readlines():
                enum = i.split(" ")
                l.append((enum[0], enum[1][:-1], ""))
        
        self.enums['SPL'] = l
        self.enums['FTP'] = l

        path = os.path.join(directory, "ubersplat_types.txt")
        l = []
        
        with open(path, 'r') as f:
            for i in f.readlines():
                enum = i.split(" ")
                l.append((enum[0], enum[1][:-1], ""))
        
        self.enums['UBR'] = l
        
        path = os.path.join(directory, "spawnobject_types.txt")
        l = []
        
        with open(path, 'r') as f:
            for i in f.readlines():
                enum = i.split(" ")
                l.append((enum[0], enum[1][:-1].split("\\")[-1], ""))
        
        self.enums['SPN'] = l

war3_event_types = War3EventTypesContainer()        
        
def update_event_type(self, context):
    obj = context.active_object

    counter = 0
    
    self.event_id = war3_event_types.enums[self.event_type][0][0]
    
    while True:
        if not any([ob for ob in context.scene.objects if ob.name.startswith("%s%d" % (self.event_type, counter))]):
            obj.name = "%s%d%s" % (self.event_type, counter, self.event_id)
            break
        counter += 1
    
    obj['event_type'] = self.event_type
    obj['event_id'] = self.event_id

def get_event_items(self, context):
    return war3_event_types.enums[self.event_type]

def update_event_id(self, context):
    obj = context.active_object
    
    counter = 0
    obj.name = "EVENT"
    
    while True:
        if not any([ob for ob in context.scene.objects if ob.name.startswith("%s%d" % (self.event_type, counter))]):
            obj.name = "%s%d%s" % (self.event_type, counter, self.event_id)
            break
        counter += 1
    
    obj['event_id'] = str(self.event_id)        
        
class War3EventProperties(PropertyGroup):

    event_type = EnumProperty(
                        name = "Event Type",
                        items = [('SND', "Sound", ""),
                                 ('FTP', "Footprint", ""),
                                 ('SPN', "Spawned Object", ""),
                                 ('SPL', "Splat", ""),
                                 ('UBR', "UberSplat", "")],
                        default = 'SND',
                        update = update_event_type
                        )
                            
    event_id  = EnumProperty(
                        name = "Event ID",
                        items = get_event_items,
                        update = update_event_id
                        )
                        
class War3ParticleSystemProperties(PropertyGroup):

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
        maxlen = 256
        )
        
    model_path = StringProperty(
        name = "Model Path",
        default = "",
        maxlen = 100
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
        bpy.types.ParticleSettings.mdl_particle_sys = PointerProperty(type=War3ParticleSystemProperties)
        
    @classmethod
    def unregister(cls):
        del bpy.types.ParticleSettings.mdl_particle_sys
        
class War3LightSettings(PropertyGroup):
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