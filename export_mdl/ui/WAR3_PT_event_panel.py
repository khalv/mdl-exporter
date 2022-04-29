import bpy
from bpy.types import Panel
from ..properties.War3EventProperties import War3EventProperties

class WAR3_PT_event_panel(Panel):  
    """Displays event object properties in the Object panel"""
    bl_idname = "WAR3_PT_event_panel"
    bl_label = "Event Object"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'object'
    
    @classmethod
    def register(cls):
        bpy.types.WindowManager.events = bpy.props.PointerProperty(type=War3EventProperties)
       
    @classmethod
    def unregister(cls):
        del bpy.types.WindowManager.events
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        
        if obj is None or obj.get('event_type') is None:
            return False
        
        if obj is not None:
            events = context.window_manager.events
            if events.event_type != obj['event_type']:
                events.event_type = obj['event_type']
            
            if events.event_id != obj['event_id']:
                events.event_id = obj['event_id']
                
        return True

    def draw(self, context):
        layout = self.layout
        
        events = context.window_manager.events
        
        row = layout.row()
        row.label(text="Event Type")
        op = row.operator("object.search_eventtype", text="", icon='VIEWZOOM')
        row.prop(events, "event_type", text="")
        
        layout.separator()
        
        row = layout.row()
        row.label(text="Event ID")
        op = row.operator("object.search_eventid", text="", icon='VIEWZOOM')
        row.prop(events, "event_id", text="")