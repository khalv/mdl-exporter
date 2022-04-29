from bpy.types import Panel

class WAR3_PT_sequences_panel(Panel):
    """Creates a sequence editor Panel in the Scene window"""
    bl_idname = "WAR3_PT_sequences_panel"
    bl_label = "MDL Sequences"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'scene'
    
    @classmethod
    def poll(self, context):

        sequences = context.scene.mdl_sequences
        return len(sequences) > 0
        
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()
        row.template_list("WAR3_UL_sequence_list", "", scene, "mdl_sequences", scene, "mdl_sequence_index", rows=2)
        
        sequences = getattr(scene, "mdl_sequences", None)
        index = getattr(scene, "mdl_sequence_index", None)
        
        layout.operator("custom.add_anim_sequence", text="Add Sequence")
        
        if sequences is not None and len(sequences):
            active_sequence = sequences[index]
            
            col = layout.column(align=True)
            col.prop(active_sequence, "name_display")
            col.separator()
            
            row = layout.row()
            col = row.column()
            col.label(text="Start")
            col = row.column()
            col.label(text="End")
            
            row = layout.row()
            col = row.column()
            col.enabled = False
            col.prop(active_sequence, "start")
            col = row.column()
            col.enabled = False
            col.prop(active_sequence, "end")
            
            col.separator()
            
            col = layout.column()
            col.prop(active_sequence, "rarity")
            col.separator()
            if 'walk' in active_sequence.name.lower():
                col.prop(active_sequence, "move_speed")
                col.separator()
            col.prop(active_sequence, "non_looping")