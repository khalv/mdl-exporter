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
    "blender": (2, 80, 0),
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

from bpy.utils import register_class, unregister_class

classes = (
    properties.War3MaterialLayerProperties,
    properties.War3EventProperties,
    properties.War3SequenceProperties,
    properties.War3BillboardProperties,
    properties.War3ParticleSystemProperties,
    properties.War3LightSettings,
    operators.WAR3_OT_export_mdl,
    operators.WAR3_OT_search_event_type,
    operators.WAR3_OT_search_event_id,
    operators.WAR3_OT_search_texture,
    operators.WAR3_OT_create_eventobject,
    operators.WAR3_OT_create_collision_shape,
    operators.WAR3_OT_material_list_action,
    operators.WAR3_OT_emitter_preset_add,
    operators.WAR3_OT_add_anim_sequence,
    operators.WAR3_MT_emitter_presets,
    ui.WAR3_UL_sequence_list,
    ui.WAR3_UL_material_layer_list,
    ui.WAR3_PT_sequences_panel,
    ui.WAR3_PT_event_panel,
    ui.WAR3_PT_billboard_panel,
    ui.WAR3_PT_material_panel,
    ui.WAR3_PT_particle_editor_panel,
    ui.WAR3_PT_light_panel
)
        
def menu_func(self, context):
    self.layout.operator_context = 'INVOKE_DEFAULT'
    self.layout.operator(operators.WAR3_OT_export_mdl.bl_idname, text="Warcraft MDL (.mdl)")  

def register():
    for cls in classes:
        register_class(cls)
        
    bpy.types.TOPBAR_MT_file_export.append(menu_func)
    
    presets_path = os.path.join(bpy.utils.user_resource('SCRIPTS', "presets"), "mdl_exporter")
    emitters_path = os.path.join(presets_path, "emitters")
    
    if not os.path.exists(emitters_path):
        os.makedirs(emitters_path)
        source_path = os.path.join(os.path.join(os.path.dirname(__file__), "presets"), "emitters")
        files = os.listdir(source_path) 
        [shutil.copy2(os.path.join(source_path, f), emitters_path) for f in files]
    
    
def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
        
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    
if __name__ == "__main__":
    register()
                                         