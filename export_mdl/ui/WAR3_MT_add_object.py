from bpy.types import Menu

from ..operators.WAR3_OT_create_collision_shape import WAR3_OT_create_collision_shape
from ..operators.WAR3_OT_create_eventobject import WAR3_OT_create_eventobject
from ..operators.WAR3_OT_add_anim_sequence import WAR3_OT_add_anim_sequence

class WAR3_MT_add_object(Menu):
    bl_idname = "WAR3_MT_add_object"
    bl_label = "Add MDL object"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout

        layout.operator(WAR3_OT_create_collision_shape.bl_idname)
        layout.operator(WAR3_OT_create_eventobject.bl_idname)
        layout.operator(WAR3_OT_add_anim_sequence.bl_idname)

def menu_func(self, context):
    self.layout.menu(WAR3_MT_add_object.bl_idname, text="MDL data")