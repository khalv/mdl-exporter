import bpy

from bpy.types import Operator
from bpy.props import EnumProperty

class WAR3_OT_create_collision_shape(Operator):
    bl_idname = "object.create_collision_shape"
    bl_label = "Add Collision Shape"
    
    shape : EnumProperty(
            name = "Type",
            items = [('SPHERE', "Collision Sphere", ""),
                     ('CUBE', "Collision Box", "")],
            default = 'SPHERE'
        )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
        
    def execute(self, context):
        bpy.ops.object.empty_add(type=self.shape, radius=1.0, align='WORLD', location=context.scene.cursor.location)
            
        obj = context.active_object
        counter = 0
        
        while True:
            if not any((bpy.data.objects.get("Collision%s%d" % (name, counter)) for name in ('Box', 'Sphere'))):
                obj.name = "Collision%s%d" % ('Sphere' if self.shape == 'SPHERE' else 'Box', counter)
                break
            counter += 1
        
        return {'FINISHED'}