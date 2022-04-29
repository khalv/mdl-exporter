import bpy
from bpy.types import Operator

from ..properties.War3EventTypesContainer import war3_event_types
  
class WAR3_OT_create_eventobject(Operator):
    bl_idname = "object.create_eventobject"
    bl_label = "Add Event Object"
    
    def invoke(self, context, event):
        bpy.ops.object.empty_add(type='PLAIN_AXES',radius=0.25,location=context.scene.cursor.location)
            
        obj = context.active_object   
        
        obj['event_type'] = 'SND'
                            
        obj['event_id']   = war3_event_types.enums[obj['event_type']][0][0]
        
        obj['event_track'] = 0
        
        events = context.window_manager.events
        events.event_type = 'SND'
        events.event_id = obj['event_id']
        
        counter = 0
        while True:
            if bpy.data.objects.get("%s%d%s" % (obj['event_type'], counter, obj['event_id'])) is None:
                obj.name = "%s%d%s" % (obj['event_type'], counter, obj['event_id'])
                break
            counter += 1
        
        return {'FINISHED'}