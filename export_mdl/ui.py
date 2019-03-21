import bpy
from . import operators, properties

from bpy.props import (
        PointerProperty
        )
        
from bpy.types import (
        Panel, 
        UIList
        )
        
from .operators import War3MaterialListActions

class War3SequenceList(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon='TIME')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value='TIME')

class War3SequencePanel(Panel):
    """Creates a sequence editor Panel in the Scene window"""
    bl_idname = "OBJECT_PT_sequences_panel"
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
        row.template_list("War3SequenceList", "", scene, "mdl_sequences", scene, "mdl_sequence_index", rows=2)
        
        sequences = getattr(scene, "mdl_sequences", None)
        index = getattr(scene, "mdl_sequence_index", None)
        
        if sequences is not None and len(sequences):
            active_sequence = sequences[index]
            
            col = layout.column(align=True)
            col.prop(active_sequence, "name_display")
            col.separator()
            
            row = layout.row()
            col = row.column()
            col.label("Start")
            col = row.column()
            col.label("End")
            
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
                
class War3MaterialLayerList(UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        icons = {'0' : 'IMAGE_DATA', '1' : 'TEXTURE', '2' : 'POTATO', '11' : 'FACESEL', '36' : 'IMAGE_RGB_ALPHA', 'Tree' : 'MESH_CONE'}
        icon = icons[item.texture_type] if item.texture_type in icons.keys() else icons['Tree']
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon=icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
            
        
class War3EventObjectPanel(Panel):  
    """Displays event object properties in the Object panel"""
    bl_idname = "OBJECT_PT_event_panel"
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
        row.label("Event Type")
        op = row.operator("object.search_eventtype", text="", icon='VIEWZOOM')
        row.prop(events, "event_type", text="")
        
        layout.separator()
        
        row = layout.row()
        row.label("Event ID")
        op = row.operator("object.search_eventid", text="", icon='VIEWZOOM')
        row.prop(events, "event_id", text="")

class War3BillboardPanel(Panel):  
    """Displays billboard settings in the Object panel"""
    bl_idname = "OBJECT_PT_billboard_panel"
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
            
        if obj.type == 'LAMP':
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
        
class War3MaterialPanel(Panel):
    """Creates a material editor Panel in the Material window"""
    bl_idname = "OBJECT_PT_material_panel"
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
            
            row.template_list("War3MaterialLayerList", "", mat, "mdl_layers", mat, "mdl_layer_index", rows=2)
            
            col = row.column(align=True)
            col.operator("custom.list_action", icon='ZOOMIN', text="").action = 'ADD'
            col.operator("custom.list_action", icon='ZOOMOUT', text="").action = 'REMOVE'
            col.separator()
            col.operator("custom.list_action", icon='TRIA_UP', text="").action = 'UP'
            col.operator("custom.list_action", icon='TRIA_DOWN', text="").action = 'DOWN'
            
            col = layout.column(align=True)
            
            if len(layers):
                active_layer = layers[index]
                print(active_layer)
                col.prop(active_layer, "name")
                col.separator()
                col.prop(active_layer, "texture_type")
                if active_layer.texture_type == '0': # Image texture
                    row = col.row()
                    row.label("Texture Path")
                    op = row.operator("object.search_textures", text="", icon='VIEWZOOM')
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
                
class War3ParticleEditorPanel(Panel):
    """Creates a particle editor Panel in the Particles window"""
    bl_idname = "OBJECT_PT_particle_editor_panel"
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
        
        layout.prop(psys, "emitter_type")
        
        if psys.emitter_type == 'ParticleEmitter':
            layout.prop(psys, "model_path")
            layout.prop(psys, "emission_rate")
            layout.prop(psys, "life_span")
            layout.prop(psys, "speed")
            layout.prop(psys, "gravity")
            
            layout.separator()
            
            layout.label("Emission Cone")
            layout.prop(psys, "longitude")
            layout.prop(psys, "latitude")
            
        elif psys.emitter_type == 'RibbonEmitter':
            layout.prop_search(psys, "ribbon_material", bpy.data, "materials")
            layout.prop(psys, "texture_path")
            layout.separator()
            
            layout.prop(psys, "ribbon_color")
            
            layout.separator()
            
            layout.prop(psys, "emission_rate")
            layout.prop(psys, "life_span")
            layout.prop(psys, "gravity")
            
            layout.label("Spritesheet Size")
            row = layout.row()
            col = row.column()
            col.label("Rows")
            col.prop(psys, "rows")
            col = row.column()
            col.label("Columns")
            col.prop(psys, "cols")
        else:
            layout.prop(psys, "texture_path")
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
            
            layout.label("Segments")
            row = layout.row()
            box = row.box()
            box.label("Color")
            box.prop(psys, "start_color")
            box.label("Alpha")
            box.prop(psys, "start_alpha")
            box.label("Scale")
            box.prop(psys, "start_scale")
            box = row.box()
            box.label("Color")
            box.prop(psys, "mid_color")
            box.label("Alpha")
            box.prop(psys, "mid_alpha")
            box.label("Scale")
            box.prop(psys, "mid_scale")
            box = row.box()
            box.label("Color")
            box.prop(psys, "end_color")
            box.label("Alpha")
            box.prop(psys, "end_alpha")
            box.label("Scale")
            box.prop(psys, "end_scale")
            
            layout.prop(psys, "time")
            
            layout.separator()
            
            layout.label("Spritesheet Size")
            row = layout.row()
            col = row.column()
            col.label("Rows")
            col.prop(psys, "rows")
            col = row.column()
            col.label("Columns")
            col.prop(psys, "cols")
            
            layout.separator()
            
            if psys.head and psys.rows * psys.cols > 1:
                layout.label("Head Sprite Settings")
                row = layout.row()
                col = row.column()
                col.label("Birth")
                box = col.box()
                box.label("Start")
                box.prop(psys, "head_life_start")
                box.label("End")
                box.prop(psys, "head_life_end")
                box.label("Repeat")
                box.prop(psys, "head_life_repeat")
            
            
                col = row.column()
                col.label("Decay")
                box = col.box()
                box.label("Start")
                box.prop(psys, "head_decay_start")
                box.label("End")
                box.prop(psys, "head_decay_end")
                box.label("Repeat")
                box.prop(psys, "head_decay_repeat")
                layout.separator()
            
            if psys.tail and psys.rows * psys.cols > 1:
                layout.label("Tail Sprite Settings")
                row = layout.row()
                col = row.column()
                col.label("Birth")
                box = col.box()
                box.label("Start")
                box.prop(psys, "tail_life_start")
                box.label("End")
                box.prop(psys, "tail_life_end")
                box.label("Repeat")
                box.prop(psys, "tail_life_repeat")
                
                
                col = row.column()
                col.label("Decay")
                box = col.box()
                box.label("Start")
                box.prop(psys, "tail_decay_start")
                box.label("End")
                box.prop(psys, "tail_decay_end")
                box.label("Repeat")
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
            
class War3LightPanel(Panel):  
    """Displays light properties in the lamp panel"""
    bl_idname = "OBJECT_PT_light_panel"
    bl_label = "MDL Light Settings"
    bl_region_type = 'WINDOW'
    bl_space_type = 'PROPERTIES'
    bl_context = 'data'
    
    @classmethod
    def register(cls):
        bpy.types.Lamp.mdl_light = PointerProperty(type=properties.War3LightSettings)
       
    @classmethod
    def unregister(cls):
        del bpy.types.Lamp.mdl_light
                    
    @classmethod
    def poll(self,context):
        obj = context.active_object
        return obj is not None and obj.type == 'LAMP'

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