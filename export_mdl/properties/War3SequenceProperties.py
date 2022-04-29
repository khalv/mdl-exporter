import bpy

from bpy.props import IntProperty, BoolProperty, StringProperty, CollectionProperty
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
    
def get_sequence_start(self):
    scene = bpy.context.scene
    if not len(scene.mdl_sequences):
        return 0
    # active_sequence = scene.mdl_sequences[scene.mdl_sequence_index]
    return min(tuple(m.frame for m in scene.timeline_markers if m.name == self.name))
            
def get_sequence_end(self):
    scene = bpy.context.scene
    if not len(scene.mdl_sequences):
        return 0
    # active_sequence = scene.mdl_sequences[scene.mdl_sequence_index]
    return max(tuple(m.frame for m in scene.timeline_markers if m.name == self.name))
    
class War3SequenceProperties(PropertyGroup):

    # Backing field
    
    name_display : StringProperty(
        name = "Name",
        default = "",
        get = get_sequence_name,
        set = set_sequence_name
        )

    name : StringProperty(
        name = "",
        default = "Sequence"
        )
        
    start : IntProperty(
        name = "",
        get = get_sequence_start
        )
        
    end : IntProperty(
        name = "",
        get = get_sequence_end
        )

    rarity : IntProperty(
        name = "Rarity",
        description = "How rarely this sequence should play.",
        default = 0,
        min = 0
        )
        
    non_looping : BoolProperty(
        name = "Non Looping",
        default = False
        )
        
    move_speed : IntProperty(
        name = "Movement Speed",
        description = "The unit movement speed at which this animation will play at 100% speed.",
        default = 270,
        min = 0
        )
                    
    @classmethod
    def register(cls):
        bpy.types.Scene.mdl_sequences = CollectionProperty(type=War3SequenceProperties, options={'HIDDEN'})
        bpy.types.Scene.mdl_sequence_index = IntProperty(name="Sequence index", description="", default=0, options={'HIDDEN'}) 
        bpy.types.WindowManager.mdl_sequence_refreshing = BoolProperty(name="sequence refreshing", description="", default=False, options={'HIDDEN'})
        
        if sequence_changed_handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(sequence_changed_handler)
     
    @classmethod    
    def unregister(cls):
        if sequence_changed_handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(sequence_changed_handler)     
    
        del bpy.types.Scene.mdl_sequences
        del bpy.types.Scene.mdl_sequence_index  
        del bpy.types.WindowManager.mdl_sequence_refreshing   