import bpy

from bpy.types import Operator
from bpy.props import FloatProperty, BoolProperty, StringProperty

from bpy_extras.io_utils import (
        ExportHelper,
        axis_conversion,
        orientation_helper,
        )
        
from mathutils import Matrix

from ..classes.War3ExportSettings import War3ExportSettings

@orientation_helper(axis_forward='-X', axis_up='Z')
class WAR3_OT_export_mdl(Operator, ExportHelper):
    """MDL Exporter"""
    bl_idname = 'export.mdl_exporter'
    bl_description = 'Warctaft 3 MDL Exporter'
    bl_label = 'Export .MDL'
    filename_ext = ".mdl"
    
    filter_glob : StringProperty(
            default="*.mdl", options={'HIDDEN'}
            )
    
    filepath : StringProperty(
            subtype="FILE_PATH"
            )
    
    use_selection : BoolProperty(
            name="Selected Objects",
            description="Export only selected objects on visible layers",
            default=False,
            )
            
    global_scale : FloatProperty(
            name="Scale",
            min=0.01, 
            max=1000.0,
            default=60.0,
            )
            
    optimize_animation : BoolProperty(
            name="Optimize Keyframes",
            description="Remove keyframes if the resulting motion deviates less than the tolerance value."
            )
            
    optimize_tolerance : FloatProperty(
            name="Tolerance",
            min=0.001, 
            soft_max=0.1,
            default=0.05,
            subtype='DISTANCE',
            unit='LENGTH'
            )
    
    def execute(self, context):                                   
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
        
        settings = War3ExportSettings()
        settings.global_matrix = axis_conversion(to_forward=self.axis_forward,
                                 to_up=self.axis_up,
                                 ).to_4x4() @ Matrix.Scale(self.global_scale, 4)
                                 
        settings.use_selection = self.use_selection
        settings.optimize_animation = self.optimize_animation
        settings.optimize_tolerance = self.optimize_tolerance
        
        from .. import export_mdl
        export_mdl.save(self, context, settings, filepath=filepath, mdl_version=800)
        
        return {'FINISHED'}
       
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "use_selection")
        layout.prop(self, "global_scale")
        layout.prop(self, "axis_forward")
        layout.prop(self, "axis_up")
        layout.separator()
        layout.prop(self, 'optimize_animation')
        if self.optimize_animation:
            box = layout.box()
            box.label(text="EXPERIMENTAL", icon='ERROR')
            layout.prop(self, 'optimize_tolerance')