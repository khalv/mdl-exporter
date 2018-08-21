# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "MDL Exporter", 
    "author": "Kalle Halvarsson",
    "blender": (2, 79, 0),
    "location": "File > Export > Warcraft MDL (.mdl)",
    "description": "Export mesh as Warcraft .MDL",
    "category": "Import-Export"} 


if "bpy" in locals():
  import imp
  imp.reload(materials)
  imp.reload(objects)
  imp.reload(export_mdl)
else:
  from . import materials, objects, export_mdl

import bpy  
  
from bpy.props import (
        CollectionProperty,
        StringProperty,
        BoolProperty,
        EnumProperty,
        FloatProperty,
        IntProperty
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        axis_conversion,
        orientation_helper_factory,
        )
        
IOMDLOrientationHelper = orientation_helper_factory("IOMDLOrientationHelper", axis_forward='-X', axis_up='Z')  
  
class MDLExporter(bpy.types.Operator, ExportHelper, IOMDLOrientationHelper):
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
        
        from mathutils import Matrix
        
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

        
def menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(MDLExporter.bl_idname,text="Warcraft MDL (.mdl)")  

def register():
    bpy.utils.register_class(materials.MaterialLayerSettings)
    bpy.utils.register_class(objects.EventPropertyGroup)
    bpy.utils.register_module(__name__);
    bpy.types.INFO_MT_file_export.append(menu_func)
    
def unregister():
    bpy.utils.unregister_class(materials.MaterialLayerSettings)
    bpy.utils.unregister_class(objects.EventPropertyGroup)
    bpy.utils.unregister_module(__name__);
    bpy.types.INFO_MT_file_export.remove(menu_func)
    
if __name__ == "__main__":
    register()
                                         