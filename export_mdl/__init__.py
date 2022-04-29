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
    "name": "MDL Importer/Exporter", 
    "author": "Kalle Halvarsson",
    "blender": (2, 80, 0),
    "location": "File > Export > Warcraft MDL (.mdl)",
    "description": "Import or export Warcraft .MDL models",
    "category": "Import-Export"
    } 

if "bpy" in locals():
    import importlib
    importlib.reload(properties)
    importlib.reload(operators)
    importlib.reload(ui)
else:
    from . import properties
    from . import operators
    from . import ui

import bpy
import os
import shutil
        
def export_menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(operators.WAR3_OT_export_mdl.WAR3_OT_export_mdl.bl_idname, text="Warcraft MDL (.mdl)")  

def import_menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(operators.WAR3_OT_import_mdl.WAR3_OT_import_mdl.bl_idname, text="Warcraft MDL (.mdl)")  

def register():
    from bpy.utils import register_class

    for cls in properties.classes + operators.classes + ui.classes:
        register_class(cls)
        
    bpy.types.TOPBAR_MT_file_export.append(export_menu_func)
    bpy.types.TOPBAR_MT_file_import.append(import_menu_func)
    bpy.types.VIEW3D_MT_add.append(ui.WAR3_MT_add_object.menu_func)
    
    presets_path = os.path.join(bpy.utils.user_resource('SCRIPTS', path="presets"), "mdl_exporter")
    emitters_path = os.path.join(presets_path, "emitters")
    
    if not os.path.exists(emitters_path):
        os.makedirs(emitters_path)
        source_path = os.path.join(os.path.join(os.path.dirname(__file__), "presets"), "emitters")
        files = os.listdir(source_path) 
        [shutil.copy2(os.path.join(source_path, f), emitters_path) for f in files]
    
    
def unregister():
    from bpy.utils import unregister_class
        
    bpy.types.TOPBAR_MT_file_export.remove(export_menu_func)
    bpy.types.TOPBAR_MT_file_import.remove(import_menu_func)
    bpy.types.VIEW3D_MT_add.remove(ui.WAR3_MT_add_object.menu_func)

    for cls in reversed(properties.classes + operators.classes + ui.classes):
        unregister_class(cls)
    
if __name__ == "__main__":
    register()
                                         