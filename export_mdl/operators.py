import bpy

from bpy.props import (
        FloatProperty,
        IntProperty,
        EnumProperty,
        BoolProperty,
        StringProperty,
        FloatVectorProperty,
        IntVectorProperty,
        PointerProperty,
        )
        
from bpy.types import Operator

from .properties import War3EventTypesContainer

from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        axis_conversion,
        orientation_helper_factory,
        )
        
from mathutils import Matrix
        
IOMDLOrientationHelper = orientation_helper_factory("IOMDLOrientationHelper", axis_forward='-X', axis_up='Z')  
  
class War3ExportMDL(Operator, ExportHelper, IOMDLOrientationHelper):
    """MDL Exporter"""
    bl_idname = 'export.mdl_exporter'
    bl_description = 'Warctaft 3 MDL Exporter'
    bl_label = 'Export .MDL'
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    filename_ext = ".mdl"
    filter_glob = StringProperty(default="*.mdl", options={'HIDDEN'})
    
    use_selection = BoolProperty(
            name="Selected Objects",
            description="Export only selected objects on visible layers",
            default=False,
            )
            
    global_scale = FloatProperty(
            name="Scale",
            min=0.01, max=1000.0,
            default=60.0,
            )
    
    def execute(self, context):                                   
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
        
        global_matrix = axis_conversion(to_forward=self.axis_forward,
                                 to_up=self.axis_up,
                                 ).to_4x4() * Matrix.Scale(self.global_scale, 4)
                                 
        
        keywords = self.as_keywords(ignore=("axis_forward",
                                    "axis_up",
                                    "global_scale",
                                    "filter_glob",
                                    ))
        
        keywords["global_matrix"] = global_matrix
        
        from . import export_mdl
        export_mdl.save(self, context, **keywords)
        
        return {'FINISHED'}
       
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "use_selection")
        layout.prop(self, "global_scale")
        layout.prop(self, "axis_forward")
        layout.prop(self, "axis_up")
       
    @classmethod
    def poll(cls, context):
        return context.active_object != None
  
war3_event_types = War3EventTypesContainer() 
  
class War3CreateEventObject(Operator):
    bl_idname = "object.create_eventobject"
    bl_label = "Add MDL Event Object"
    
    def invoke(self, context, event):
        bpy.ops.object.empty_add(type='PLAIN_AXES',radius=0.3,location=context.scene.cursor_location)
            
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
    
class War3CreateCollisionShape(Operator):
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
        
class War3MaterialListActions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "custom.list_action"
    bl_label = "List Actions"
    bl_description = "Move items up and down, add and remove"
    bl_options = {'REGISTER'}
    
    name_counter = 0

    action = bpy.props.EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", "")))
            
    @classmethod
    def poll(self,context):
        return context.active_object is not None and context.active_object.active_material is not None

    def invoke(self, context, event):

        try:
            mat = context.active_object.active_material
            i = mat.mdl_layer_index
            item = mat.mdl_layers[i]
        except IndexError:
            pass
        else:
            if self.action == 'DOWN' and i < len(mat.mdl_layers) - 1:
                mat.mdl_layers.move(i, i+1)
                mat.mdl_layer_index += 1
            elif self.action == 'UP' and i >= 1:
                mat.mdl_layers.move(i, i-1)
                mat.mdl_layer_index -= 1

            elif self.action == 'REMOVE':
                if i > 0:
                    mat.mdl_layer_index -= 1
                if len(mat.mdl_layers):
                    mat.mdl_layers.remove(i)

        if self.action == 'ADD':
            if context.active_object:
                item = mat.mdl_layers.add()
                item.name = "Layer %d" % self.name_counter
                War3MaterialListActions.name_counter += 1
                mat.mdl_layer_index = len(mat.mdl_layers)-1
            else:
                self.report({'INFO'}, "Nothing selected in the Viewport")
                
        return {"FINISHED"}