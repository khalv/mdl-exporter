if "bpy" in locals():
    import importlib
    importlib.reload(WAR3_MT_emitter_presets)
    importlib.reload(WAR3_PT_billboard_panel)
    importlib.reload(WAR3_PT_event_panel)
    importlib.reload(WAR3_PT_light_panel)
    importlib.reload(WAR3_PT_material_panel)
    importlib.reload(WAR3_PT_particle_editor_panel)
    importlib.reload(WAR3_PT_sequences_panel)
    importlib.reload(WAR3_UL_material_layer_list)
    importlib.reload(WAR3_UL_sequence_list)
    importlib.reload(WAR3_MT_add_object)
else:
    from . import WAR3_MT_emitter_presets
    from . import WAR3_PT_billboard_panel
    from . import WAR3_PT_event_panel
    from . import WAR3_PT_light_panel
    from . import WAR3_PT_material_panel
    from . import WAR3_PT_particle_editor_panel
    from . import WAR3_PT_sequences_panel
    from . import WAR3_UL_material_layer_list
    from . import WAR3_UL_sequence_list
    from . import WAR3_MT_add_object

import bpy

classes = [
    WAR3_MT_emitter_presets.WAR3_MT_emitter_presets,
    WAR3_PT_billboard_panel.WAR3_PT_billboard_panel,
    WAR3_PT_event_panel.WAR3_PT_event_panel,
    WAR3_PT_light_panel.WAR3_PT_light_panel,
    WAR3_PT_material_panel.WAR3_PT_material_panel,
    WAR3_PT_particle_editor_panel.WAR3_PT_particle_editor_panel,
    WAR3_PT_sequences_panel.WAR3_PT_sequences_panel,
    WAR3_UL_material_layer_list.WAR3_UL_material_layer_list,
    WAR3_UL_sequence_list.WAR3_UL_sequence_list,
    WAR3_MT_add_object.WAR3_MT_add_object
]