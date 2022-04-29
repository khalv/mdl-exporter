from bpy.types import Menu

class WAR3_MT_emitter_presets(Menu):
    bl_label = "Emitter Presets"
    preset_subdir = "mdl_exporter/emitters"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset