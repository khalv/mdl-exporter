from bpy.types import Operator
from bpy.props import EnumProperty

from ..properties.War3EventTypesContainer import event_items

class WAR3_OT_search_event_id(Operator):
    bl_idname = "object.search_eventid"
    bl_label = "Search"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_property = "ids"
    
    ids : EnumProperty(
                name = "Event ID",
                items = event_items,
            )
    
    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}
        
    def execute(self, context):
        context.window_manager.events.event_id = self.ids
        return {'FINISHED'}