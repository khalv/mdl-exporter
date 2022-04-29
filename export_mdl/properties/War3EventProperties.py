from bpy.props import EnumProperty
from bpy.types import PropertyGroup

from .War3EventTypesContainer import update_event_type, get_event_items

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

    event_type : EnumProperty(
                        name = "Event Type",
                        items = [('SND', "Sound", ""),
                                 ('FTP', "Footprint", ""),
                                 ('SPN', "Spawned Object", ""),
                                 ('SPL', "Splat", ""),
                                 ('UBR', "UberSplat", "")],
                        default = 'SND',
                        update = update_event_type
                        )
                            
    event_id  : EnumProperty(
                        name = "Event ID",
                        items = get_event_items,
                        update = update_event_id
                        )