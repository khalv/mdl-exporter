import bpy
from bpy.types import Operator
from bpy.props import FloatProperty, StringProperty
from bpy_extras.io_utils import ImportHelper, axis_conversion

from mathutils import Matrix

from ..classes.War3ImportSettings import War3ImportSettings 

class WAR3_OT_import_mdl(Operator, ImportHelper):
    """MDL Importer"""
    bl_idname = 'import.mdl_importer'
    bl_description = 'Warcraft 3 MDL Importer'
    bl_label = 'Import .MDL'
    filename_ext = '.mdl'

    filter_glob : StringProperty(
        default="*.mdl", options={'HIDDEN'}
        )
    
    filepath : StringProperty(
            subtype="FILE_PATH"
            )

    global_scale : FloatProperty(
            name="Import scale",
            description="Warcraft models use different units, and need to be scaled down by about a factor of 60",
            min=0.001, 
            max=100.0,
            default=0.016,
            )

    def execute(self, context):
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

        settings = War3ImportSettings()
        settings.global_matrix = Matrix.Scale(self.global_scale, 4)
        settings.global_matrix = axis_conversion(to_forward='-X',
                                 to_up='Z',
                                 ).to_4x4().inverted() @ Matrix.Scale(self.global_scale, 4)

        from .. import import_mdl
        import_mdl.load(self, context, settings, filepath=filepath)

        return {'FINISHED'}

    def draw(self, context):
        pass