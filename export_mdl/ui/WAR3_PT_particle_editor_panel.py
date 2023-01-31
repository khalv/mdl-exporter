import bpy
from bpy.types import Panel

class WAR3_PT_particle_editor_panel(Panel):
    """Creates a particle editor Panel in the Particles window"""
    bl_idname = "WAR3_PT_particle_editor_panel"
    bl_label = "MDL Particle Emitter"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'particle'
    
    @classmethod
    def poll(self, context):
        return context.active_object is not None and len(context.active_object.particle_systems)
    
    def draw(self, context):
        layout = self.layout
        
        psys = context.active_object.particle_systems.active.settings.mdl_particle_sys
        
        row = layout.row(align=True) 
        row.menu('WAR3_MT_emitter_presets', text='Presets')
        row.operator('particle.emitter_preset_add', text='', icon='ADD')
        row.operator('particle.emitter_preset_add', text='', icon='REMOVE').remove_active = True
        
        layout.prop(psys, "emitter_type")
        
        if psys.emitter_type == 'ParticleEmitter':
            layout.prop(psys, "model_path")
            layout.prop(psys, "emission_rate")
            layout.prop(psys, "life_span")
            layout.prop(psys, "speed")
            layout.prop(psys, "gravity")
            
            layout.separator()
            
            layout.label(text="Emission Cone")
            layout.prop(psys, "longitude")
            layout.prop(psys, "latitude")
            
        elif psys.emitter_type == 'RibbonEmitter':
            layout.prop_search(psys, "ribbon_material", bpy.data, "materials")
            # layout.prop(psys, "texture_path")
            
            row = layout.row()
            row.label(text="Texture Path")
            row.operator("object.search_texture", text="", icon='VIEWZOOM').target = 'Emitter'
            row.prop(psys, "texture_path", text="")
            
            layout.separator()
            
            layout.prop(psys, "ribbon_color")
            
            layout.separator()
            
            layout.prop(psys, "emission_rate")
            layout.prop(psys, "life_span")
            layout.prop(psys, "gravity")
            
            layout.label(text="Spritesheet Size")
            row = layout.row()
            col = row.column()
            col.label(text="Rows")
            col.prop(psys, "rows")
            col = row.column()
            col.label(text="Columns")
            col.prop(psys, "cols")
        else:
            row = layout.row()
            row.label(text="Texture Path")
            row.operator("object.search_texture", text="", icon='VIEWZOOM').target = 'Emitter'
            row.prop(psys, "texture_path", text="")
            
            layout.prop(psys, "filter_mode")
            layout.prop(psys, "priority_plane")
            
            layout.separator()
            
            layout.prop(psys, "emission_rate")
            layout.prop(psys, "speed")
            layout.prop(psys, "life_span")
            layout.prop(psys, "gravity")
            layout.prop(psys, "variation")
            layout.prop(psys, "latitude")
            
            if psys.tail == True:
                layout.prop(psys, "tail_length")
            
            layout.separator()
            
            layout.label(text="Segments")
            row = layout.row()
            box = row.box()
            box.label(text="Color")
            box.prop(psys, "start_color")
            box.label(text="Alpha")
            box.prop(psys, "start_alpha")
            box.label(text="Scale")
            box.prop(psys, "start_scale")
            box = row.box()
            box.label(text="Color")
            box.prop(psys, "mid_color")
            box.label(text="Alpha")
            box.prop(psys, "mid_alpha")
            box.label(text="Scale")
            box.prop(psys, "mid_scale")
            box = row.box()
            box.label(text="Color")
            box.prop(psys, "end_color")
            box.label(text="Alpha")
            box.prop(psys, "end_alpha")
            box.label(text="Scale")
            box.prop(psys, "end_scale")
            
            layout.prop(psys, "time")
            
            layout.separator()
            
            layout.label(text="Spritesheet Size")
            row = layout.row()
            col = row.column()
            col.label(text="Rows")
            col.prop(psys, "rows")
            col = row.column()
            col.label(text="Columns")
            col.prop(psys, "cols")
            
            layout.separator()
            
            if psys.head and psys.rows * psys.cols > 1:
                layout.label(text="Head Sprite Settings")
                row = layout.row()
                col = row.column()
                col.label(text="Birth")
                box = col.box()
                box.label(text="Start")
                box.prop(psys, "head_life_start")
                box.label(text="End")
                box.prop(psys, "head_life_end")
                box.label(text="Repeat")
                box.prop(psys, "head_life_repeat")
            
            
                col = row.column()
                col.label(text="Decay")
                box = col.box()
                box.label(text="Start")
                box.prop(psys, "head_decay_start")
                box.label(text="End")
                box.prop(psys, "head_decay_end")
                box.label(text="Repeat")
                box.prop(psys, "head_decay_repeat")
                layout.separator()
            
            if psys.tail and psys.rows * psys.cols > 1:
                layout.label(text="Tail Sprite Settings")
                row = layout.row()
                col = row.column()
                col.label(text="Birth")
                box = col.box()
                box.label(text="Start")
                box.prop(psys, "tail_life_start")
                box.label(text="End")
                box.prop(psys, "tail_life_end")
                box.label(text="Repeat")
                box.prop(psys, "tail_life_repeat")
                
                
                col = row.column()
                col.label(text="Decay")
                box = col.box()
                box.label(text="Start")
                box.prop(psys, "tail_decay_start")
                box.label(text="End")
                box.prop(psys, "tail_decay_end")
                box.label(text="Repeat")
                box.prop(psys, "tail_decay_repeat")
            
            row = layout.row()
            col = row.column()
            col.prop(psys, "unshaded")
            col.prop(psys, "unfogged")
            col.prop(psys, "line_emitter")
            col.prop(psys, "sort_far_z")
            col = row.column()
            col.prop(psys, "model_space")
            col.prop(psys, "xy_quad")
            col.prop(psys, "head")
            col.prop(psys, "tail")