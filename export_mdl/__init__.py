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
  imp.reload(properties)
  imp.reload(operators)
  imp.reload(classes)
  imp.reload(export_mdl)
  imp.reload(ui)
else:
  from . import properties, operators, classes, export_mdl, ui

import bpy
import os
import shutil
        
def menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(operators.War3ExportMDL.bl_idname,text="Warcraft MDL (.mdl)")  

def register():
    bpy.utils.register_class(properties.War3MaterialLayerProperties)
    bpy.utils.register_class(properties.War3EventProperties)
    bpy.utils.register_module(__name__);
    bpy.types.INFO_MT_file_export.append(menu_func)
    
    presets_path = os.path.join(bpy.utils.user_resource('SCRIPTS', "presets"), "mdl_exporter")
    emitters_path = os.path.join(presets_path, "emitters")
    
    print(emitters_path)
    
    if not os.path.exists(emitters_path):
        os.makedirs(emitters_path)
        source_path = os.path.join(os.path.join(os.path.dirname(__file__), "presets"), "emitters")
        files = os.listdir(source_path) 
        [shutil.copy2(os.path.join(source_path, f), emitters_path) for f in files]
    
    
def unregister():
    bpy.utils.unregister_class(properties.War3MaterialLayerProperties)
    bpy.utils.unregister_class(properties.War3EventProperties)
    bpy.utils.unregister_module(__name__);
    bpy.types.INFO_MT_file_export.remove(menu_func)
    
if __name__ == "__main__":
    register()
                                         