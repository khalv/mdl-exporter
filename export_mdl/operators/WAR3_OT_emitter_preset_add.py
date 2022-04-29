from bl_operators.presets import AddPresetBase
from bpy.types import Menu, Operator
   
class WAR3_MT_emitter_presets(Menu):
    bl_label = "Emitter Presets"
    preset_subdir = "mdl_exporter/emitters"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset
   
class WAR3_OT_emitter_preset_add(AddPresetBase, Operator):
    '''Add an Emitter Preset'''
    bl_idname = "particle.emitter_preset_add"
    bl_label = "Add Emitter Preset"
    bl_options = {'INTERNAL'}
    preset_menu = "PARTICLE_MT_emitter_presets"

    # variable used for all preset values
    preset_defines = [
        "psys = bpy.context.object.particle_systems.active.settings.mdl_particle_sys"
        ]

    # properties to store in the preset
    preset_values = [
        "psys.emitter_type",
        "psys.model_path",
        "psys.texture_path",
        "psys.filter_mode",
        "psys.emission_rate",
        "psys.life_span",
        "psys.speed",
        "psys.gravity",
        "psys.longitude",
        "psys.latitude",
        "psys.ribbon_material",
        "psys.ribbon_color",
        "psys.variation",
        "psys.head",
        "psys.tail",
        "psys.tail_length",
        "psys.start_color",
        "psys.start_alpha",
        "psys.start_scale",
        "psys.mid_color",
        "psys.mid_alpha",
        "psys.mid_scale",
        "psys.end_color",
        "psys.end_alpha",
        "psys.end_scale",
        "psys.time",
        "psys.rows",
        "psys.cols",
        "psys.head_life_start",
        "psys.head_life_end",
        "psys.head_life_repeat",
        "psys.head_decay_start",
        "psys.head_decay_end",
        "psys.head_decay_repeat",
        "psys.tail_life_start",
        "psys.tail_life_end",
        "psys.tail_life_repeat",
        "psys.tail_decay_start",
        "psys.tail_decay_end",
        "psys.tail_decay_repeat",
        "psys.unshaded",
        "psys.unfogged",
        "psys.line_emitter",
        "psys.sort_far_z",
        "psys.model_space",
        "psys.xy_quad",
        ]

    # where to store the preset
    preset_subdir = "mdl_exporter/emitters"
        