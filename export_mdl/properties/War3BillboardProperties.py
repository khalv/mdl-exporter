from bpy.props import BoolProperty
from bpy.types import PropertyGroup

class War3BillboardProperties(PropertyGroup):
    billboarded : BoolProperty(
        name = "Billboarded",
        description = "If true, this object will always face the camera.",
        default = False
        )
    billboard_lock_x : BoolProperty(
        name = "Billboard Lock X",
        description = "Limits billboarding around the X axis.",
        default = False,
        )
    billboard_lock_y : BoolProperty(
        name = "Billboard Lock Y",
        description = "Limits billboarding around the Y axis.",
        default = False
        )
    billboard_lock_z : BoolProperty(
        name = "Billboard Lock Z",
        description = "Limits billboarding around the Z axis.",
        default = False
        )