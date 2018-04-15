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
    import importlib
    if "export_mdl" in locals():
        importlib.reload(export_mdl)
        
import bpy    

from bpy.props import (
        CollectionProperty,
        StringProperty,
        BoolProperty,
        EnumProperty,
        FloatProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        axis_conversion,
        )
        
        
class MDLExporter(bpy.types.Operator, ExportHelper):
    """MDL Exporter"""
    bl_idname = 'export.mdl_exporter'
    bl_description = 'Warctaft 3 MDL Exporter'
    bl_label = 'Export .MDL'
    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
    filename_ext = ".mdl"
    filter_glob = StringProperty(default="*.mdl", options={'HIDDEN'})
    
    def execute(self, context):                                   
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
        
        from . import export_mdl
        export_mdl.save(self, context, filepath)
        
        return {'FINISHED'}
       
    @classmethod
    def poll(cls, context):
        return context.active_object != None
                                            
    #def draw(self, context):
    #    layout = self.layout

    #    row = layout.row()
    #    row.prop(self, "use_mesh_modifiers")
        
def menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(MDLExporter.bl_idname,text="Warcraft MDL (.mdl)")  

def register():
    bpy.utils.register_module(__name__);
    bpy.types.INFO_MT_file_export.append(menu_func)
    
def unregister():
    bpy.utils.unregister_module(__name__);
    bpy.types.INFO_MT_file_export.remove(menu_func)
    
if __name__ == "__main__":
    register()
                                         