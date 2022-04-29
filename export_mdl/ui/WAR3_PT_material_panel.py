from bpy.types import Panel  

class WAR3_PT_material_panel(Panel):
    """Creates a material editor Panel in the Material window"""
    bl_idname = "WAR3_PT_material_panel"
    bl_label = "MDL Material Settings"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'material'
    
    @classmethod
    def poll(self, context):
        return context.active_object is not None and context.active_object.active_material is not None
    
    def draw(self, context):
        layout = self.layout
        mat = context.active_object.active_material
    
        layout.prop(mat, "priority_plane")
        layout.separator()
        layout.label(text="Layers")
        
        layers = getattr(mat, "mdl_layers", None)
        index = getattr(mat, "mdl_layer_index", None)
        
        if layers is not None and index is not None:
            row = layout.row()
            
            row.template_list("WAR3_UL_material_layer_list", "", mat, "mdl_layers", mat, "mdl_layer_index", rows=2)
            
            col = row.column(align=True)
            col.operator("custom.list_action", icon='ADD', text="").action = 'ADD'
            col.operator("custom.list_action", icon='REMOVE', text="").action = 'REMOVE'
            col.separator()
            col.operator("custom.list_action", icon='TRIA_UP', text="").action = 'UP'
            col.operator("custom.list_action", icon='TRIA_DOWN', text="").action = 'DOWN'
            
            col = layout.column(align=True)
            
            if len(layers):
                active_layer = layers[index]
                col.prop(active_layer, "name")
                col.separator()
                col.prop(active_layer, "texture_type")
                if active_layer.texture_type == '0': # Image texture
                    row = col.row()
                    row.label(text="Texture Path")
                    row.operator("object.search_texture", text="", icon='VIEWZOOM').target = 'Material'
                    row.prop(active_layer, "path", text="")
                    
                elif active_layer.texture_type == '36':
                    col.prop(active_layer, "replaceable_id")
                col.separator()
                col.prop(active_layer, "filter_mode")
                if active_layer.filter_mode in {'Blend', 'Transparent', 'AddAlpha'}:
                    col.prop(active_layer, "alpha")
                col.separator()
                col.prop(active_layer, "unshaded")
                col.prop(active_layer, "two_sided")
                col.prop(active_layer, "no_depth_test")
                col.prop(active_layer, "no_depth_set")