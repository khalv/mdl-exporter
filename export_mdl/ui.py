import bpy
from . import operators, properties

from bpy.props import (
        PointerProperty
        )
        
from bpy.types import (
        Panel, 
        UIList,
        )
        
from .operators import WAR3_OT_material_list_action

class WAR3_UL_sequence_list(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon='TIME')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value='TIME')

class WAR3_PT_sequences_panel(Panel):
    """Creates a sequence editor Panel in the Scene window"""
    bl_idname = "WAR3_PT_sequences_panel"
    bl_label = "MDL Sequences"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'scene'
    
    @classmethod
    def poll(self,context):

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
                
class WAR3_UL_material_layer_list(UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        icons = {'0' : 'IMAGE_DATA', '1' : 'TEXTURE', '2' : 'SHADING_TEXTURE', '11' : 'FACESEL', '36' : 'IMAGE_RGB_ALPHA', 'Tree' : 'MESH_CONE'}
        icon = icons[item.texture_type] if item.texture_type in icons.keys() else icons['Tree']
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon=icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
            
        
class WAR3_PT_event_panel(Panel):  
    """Displays event object properties in the Object panel"""
    bl_idname = "WAR3_PT_event_panel"
    bl_label = "Event Object"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'object'
    
    @classmethod
    def register(cls):
        bpy.types.WindowManager.events = bpy.props.PointerProperty(type=properties.War3EventProperties)
       
    @classmethod
    def unregister(cls):
        del bpy.types.WindowManager.events
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        
        if obj is None or obj.get('event_type') is None:
            return False
        
        if obj is not None:
            events = context.window_manager.events
            if events.event_type != obj['event_type']:
                events.event_type = obj['event_type']
            
            if events.event_id != obj['event_id']:
                events.event_id = obj['event_id']
                
        return True

    def draw(self, context):
        layout = self.layout
        
        events = context.window_manager.events
        
        row = layout.row()
        row.label(text="Event Type")
        op = row.operator("object.search_eventtype", text="", icon='VIEWZOOM')
        row.prop(events, "event_type", text="")
        
        layout.separator()
        
        row = layout.row()
        row.label(text="Event ID")
        op = row.operator("object.search_eventid", text="", icon='VIEWZOOM')
        row.prop(events, "event_id", text="")

class WAR3_PT_billboard_panel(Panel):  
    """Displays billboard settings in the Object panel"""
    bl_idname = "WAR3_PT_billboard_panel"
    bl_label = "MDL Billboard Options"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'object'
    
    @classmethod
    def register(cls):
        bpy.types.Object.mdl_billboard = PointerProperty(type=properties.War3BillboardProperties)
       
    @classmethod
    def unregister(cls):
        del bpy.types.Object.mdl_billboard
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        
        if obj is None:
            return False
            
        if obj.type == 'EMPTY' and obj.name.lower().startswith("bone"):
            return True
            
        if obj.type in ('LAMP', 'LIGHT'):
            return True
            
        if obj.name.endswith(" Ref"):
            return True
                
        return False

    def draw(self, context):
        layout = self.layout
        data = context.active_object.mdl_billboard
        layout.prop(data, "billboarded")
        layout.prop(data, "billboard_lock_x")
        layout.prop(data, "billboard_lock_y")
        layout.prop(data, "billboard_lock_z")
        
class WAR3_PT_material_panel(Panel):
    """Creates a material editor Panel in the Material window"""
    bl_idname = "WAR3_PT_material_panel"
    bl_label = "MDL Material Settings"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'material'
    
    @classmethod
    def poll(self,context):
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
            
class WAR3_PT_light_panel(Panel):  
    """Displays light properties in the lamp panel"""
    bl_idname = "WAR3_PT_light_panel"
    bl_label = "MDL Light Settings"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'data'
    
    @classmethod
    def register(cls):
        bpy.types.Light.mdl_light = PointerProperty(type=properties.War3LightSettings)
       
    @classmethod
    def unregister(cls):
        del bpy.types.Light.mdl_light
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        return obj is not None and obj.type in ('LAMP', 'LIGHT')

    def draw(self, context):
        layout = self.layout
        data = context.active_object.data.mdl_light
        
        layout.prop(data, "light_type")
        layout.prop(data, "atten_start")
        layout.prop(data, "atten_end")
        if data.light_type != 'Ambient':
            layout.prop(data, "color")
            layout.prop(data, "intensity")
        else:
            layout.prop(data, "amb_color")
            layout.prop(data, "amb_intensity")