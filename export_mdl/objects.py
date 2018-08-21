import bpy
import os

class EventTypeData:

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
        
event_data = EventTypeData() 

def update_event_id(self, context):
    obj = context.active_object
    obj.name = obj.name[:-len(obj['event_id'])] + self.event_id
    obj['event_id'] = str(self.event_id)


def update_event_type(self, context):
    obj = context.active_object

    self.event_id = event_data.enums[self.event_type][0][0]
    obj.name = self.event_type + obj.name[len(obj['event_type']):-len(obj['event_id'])] + self.event_id
    obj['event_type'] = self.event_type
    obj['event_id'] = self.event_id
    CUSTOM_OT_create_eventobject.name_counter += 1   

class CUSTOM_PT_EventObjectPanel(bpy.types.Panel):  
    """Displays event object properties in the Object panel"""
    bl_idname = "OBJECT_PT_event_panel"
    bl_label = "Event Object"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'object'
    
    @classmethod
    def register(cls):
        bpy.types.WindowManager.events = bpy.props.PointerProperty(type=EventPropertyGroup)
       
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
        
        layout.prop(events, "event_type")
        layout.separator()
        layout.prop(events, "event_id")

def get_event_items(self, context):
    return event_data.enums[self.event_type]
        
class EventPropertyGroup(bpy.types.PropertyGroup):
    event_type =    bpy.props.EnumProperty(
                        name = "Event Type",
                        items = [('SND', "Sound", ""),
                                 ('FTP', "Footprint", ""),
                                 ('SPN', "Spawned Object", ""),
                                 ('SPL', "Splat", ""),
                                 ('UBR', "UberSplat", "")],
                        default = 'SND',
                        update = update_event_type
                        )
                            
    event_id  = bpy.props.EnumProperty(
                    name = "Event ID",
                    items = get_event_items,
                    update = update_event_id
                    )
        
class CUSTOM_OT_create_eventobject(bpy.types.Operator):
    bl_idname = "object.create_eventobject"
    bl_label = "Add MDL Event Object"

    name_counter = 0
    
    def invoke(self, context, event):
        bpy.ops.object.empty_add(type='PLAIN_AXES',radius=0.3,location=context.scene.cursor_location)
            
        obj = context.active_object   
        
        obj['event_type'] = 'SND'
                            
        obj['event_id']   = event_data.enums[obj['event_type']][0][0]
        
        obj['event_track'] = 0
        
        events = context.window_manager.events
        events.event_type = 'SND'
        events.event_id = obj['event_id']
        
        obj.name = "%s%d%s" % (obj['event_type'], self.name_counter, obj['event_id'])
        CUSTOM_OT_create_eventobject.name_counter += 1
        
        return {'FINISHED'}
    
class CUSTOM_OT_create_colshape(bpy.types.Operator):
    bl_idname = "object.create_collision_shape"
    bl_label = "Add MDL Collision Shape"
    
    action = bpy.props.EnumProperty(
            items = [('Sphere', "Collision Sphere", ""),
                     ('Box', "Collision Box", "")]
            )
        
    def invoke(self, context, event):
        if self.action == 'Sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(location=context.scene.cursor_location, size=0.5)
        elif self.action == 'Box':
            bpy.ops.mesh.primitive_cube_add(location=context.scene.cursor_location, radius=0.5)
            
        obj = context.active_object
        obj.draw_type = 'WIRE'    
        
        return {'FINISHED'}