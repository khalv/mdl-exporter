import bpy
import os

from bpy.props import (
        FloatProperty,
        IntProperty,
        EnumProperty,
        BoolProperty,
        StringProperty,
        FloatVectorProperty,
        IntVectorProperty,
        PointerProperty
        )

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
    
class CUSTOM_OT_create_col_shape(bpy.types.Operator):
    bl_idname = "object.create_collision_shape"
    bl_label = "Add MDL Collision Shape"
    
    shape = EnumProperty(
            name = "Type",
            items = [('SPHERE', "Collision Sphere", ""),
                     ('CUBE', "Collision Box", "")],
            default = 'SPHERE'
        )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
        
    def execute(self, context):
        bpy.ops.object.empty_add(type=self.shape, radius=1.0, view_align=False, location=context.scene.cursor_location)
            
        obj = context.active_object
        counter = 0
        
        while True:
            if not any((bpy.data.objects.get("Collision%s%d" % (name, counter)) for name in ('Box', 'Sphere'))):
                obj.name = "Collision%s%d" % ('Sphere' if self.shape == 'SPHERE' else 'Box', counter)
                break
            counter += 1
        
        return {'FINISHED'}
        
class BillboardSettings(bpy.types.PropertyGroup):
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
        
class CUSTOM_PT_BillboardPanel(bpy.types.Panel):  
    """Displays billboard settings in the Object panel"""
    bl_idname = "OBJECT_PT_billboard_panel"
    bl_label = "MDL Billboard Options"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'object'
    
    @classmethod
    def register(cls):
        bpy.types.Object.mdl_billboard = PointerProperty(type=BillboardSettings)
       
    @classmethod
    def unregister(cls):
        del bpy.types.Object.mdl_billboard
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        
        if obj is None:
            return False
            
        if obj.type == 'EMPTY' and obj.name.lower().startswith("bone"):
            return True
            
        if obj.type == 'LAMP':
            return True
            
        if obj.name.endswith(" Ref"):
            return True
                
        return False

    def draw(self, context):
        layout = self.layout
        data = context.active_object.mdl_billboard
        layout.prop(data, "billboarded")
        layout.prop(data, "billboard_lock_x")
        layout.prop(data, "billboard_lock_y")
        layout.prop(data, "billboard_lock_z")