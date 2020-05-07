import bpy
import os 
from bl_operators.presets import AddPresetBase

from bpy.types import (
        Menu, 
        Operator
        )

from bpy.props import (
        FloatProperty,
        IntProperty,
        EnumProperty,
        BoolProperty,
        StringProperty,
        FloatVectorProperty,
        IntVectorProperty,
        PointerProperty,
        )

from .properties import War3EventTypesContainer
from .classes import War3ExportSettings

from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        axis_conversion,
        orientation_helper,
        )
        
from mathutils import Matrix 

@orientation_helper(axis_forward='-X', axis_up='Z')
class WAR3_OT_export_mdl(Operator, ExportHelper):
    """MDL Exporter"""
    bl_idname = 'export.mdl_exporter'
    bl_description = 'Warctaft 3 MDL Exporter'
    bl_label = 'Export .MDL'
    filename_ext = ".mdl"
    
    filter_glob : StringProperty(
            default="*.mdl", options={'HIDDEN'}
            )
    
    filepath : StringProperty(
            subtype="FILE_PATH"
            )
    
    use_selection : BoolProperty(
            name="Selected Objects",
            description="Export only selected objects on visible layers",
            default=False,
            )
            
    global_scale : FloatProperty(
            name="Scale",
            min=0.01, 
            max=1000.0,
            default=60.0,
            )
            
    optimize_animation : BoolProperty(
            name="Optimize Keyframes",
            description="Remove keyframes if the resulting motion deviates less than the tolerance value."
            )
            
    optimize_tolerance : FloatProperty(
            name="Tolerance",
            min=0.001, 
            soft_max=0.1,
            default=0.05,
            subtype='DISTANCE',
            unit='LENGTH'
            )
    
    def execute(self, context):                                   
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
        
        settings = War3ExportSettings()
        settings.global_matrix = axis_conversion(to_forward=self.axis_forward,
                                 to_up=self.axis_up,
                                 ).to_4x4() @ Matrix.Scale(self.global_scale, 4)
                                 
        settings.use_selection = self.use_selection
        settings.optimize_animation = self.optimize_animation
        settings.optimize_tolerance = self.optimize_tolerance
        
        from . import export_mdl
        export_mdl.save(self, context, settings, filepath=filepath, mdl_version=800)
        
        return {'FINISHED'}
       
    def draw(self, context):
        layout = self.layout
        
        layout.prop(self, "use_selection")
        layout.prop(self, "global_scale")
        layout.prop(self, "axis_forward")
        layout.prop(self, "axis_up")
        layout.separator()
        layout.prop(self, 'optimize_animation')
        if self.optimize_animation:
            box = layout.box()
            box.label(text="EXPERIMENTAL", icon='ERROR')
            layout.prop(self, 'optimize_tolerance')
  
war3_event_types = War3EventTypesContainer() 

def event_items(self, context):
    return war3_event_types.enums[context.window_manager.events.event_type]

class WAR3_OT_search_event_type(Operator):
    bl_idname = "object.search_eventtype"
    bl_label = "Search"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_property = "types"
    
    types : EnumProperty(
                name = "Event Type",
                items = [('SND', "Sound", ""),
                         ('FTP', "Footprint", ""),
                         ('SPN', "Spawned Object", ""),
                         ('SPL', "Splat", ""),
                         ('UBR', "UberSplat", "")],
                default = 'SND',
            )
    
    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}
        
    def execute(self, context):
        context.window_manager.events.event_type = self.types;
        return {'FINISHED'}
        
class WAR3_OT_search_event_id(Operator):
    bl_idname = "object.search_eventid"
    bl_label = "Search"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_property = "ids"
    
    ids : EnumProperty(
                name = "Event ID",
                items = event_items,
            )
    
    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}
        
    def execute(self, context):
        context.window_manager.events.event_id = self.ids;
        return {'FINISHED'}
     
def load_texture_list():
    directory = os.path.dirname(__file__)
        
    path = os.path.join(directory, "textures.txt")
    l = []
    with open(path, 'r') as f:
        l = [(line[:-1], os.path.basename(line[:-1]), os.path.basename(line[:-1])) for line in f.readlines()]
        
    return l
    
texture_paths = load_texture_list()
     
class WAR3_OT_search_texture(Operator):
    bl_idname = "object.search_texture"
    bl_label = "Search"
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_property = "path"
    
    target : EnumProperty(
                name = "Target Type",
                items = [('Emitter', 'Emitter', ''),
                         ('Material', 'Material', '')]
            )
    
    path : EnumProperty(
                name = "Path",
                items = texture_paths
            )
    
    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}
        
    def execute(self, context):
        try:
            if self.target == 'Material':
                mat = context.active_object.active_material
                i = mat.mdl_layer_index
                item = mat.mdl_layers[i]
                item.path = self.path
            else:
                psys = context.active_object.particle_systems.active.settings.mdl_particle_sys
                psys.texture_path = self.path
                
        except IndexError:
            pass
            
        return {'FINISHED'}
        
  
class WAR3_OT_create_eventobject(Operator):
    bl_idname = "object.create_eventobject"
    bl_label = "Add MDL Event Object"
    
    def invoke(self, context, event):
        bpy.ops.object.empty_add(type='PLAIN_AXES',radius=0.25,location=context.scene.cursor.location)
            
        obj = context.active_object   
        
        obj['event_type'] = 'SND'
                            
        obj['event_id']   = war3_event_types.enums[obj['event_type']][0][0]
        
        obj['event_track'] = 0
        
        events = context.window_manager.events
        events.event_type = 'SND'
        events.event_id = obj['event_id']
        
        counter = 0
        while True:
            if bpy.data.objects.get("%s%d%s" % (obj['event_type'], counter, obj['event_id'])) is None:
                obj.name = "%s%d%s" % (obj['event_type'], counter, obj['event_id'])
                break
            counter += 1
        
        return {'FINISHED'}
    
class WAR3_OT_create_collision_shape(Operator):
    bl_idname = "object.create_collision_shape"
    bl_label = "Add MDL Collision Shape"
    
    shape : EnumProperty(
            name = "Type",
            items = [('SPHERE', "Collision Sphere", ""),
                     ('CUBE', "Collision Box", "")],
            default = 'SPHERE'
        )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
        
    def execute(self, context):
        bpy.ops.object.empty_add(type=self.shape, radius=1.0, align='WORLD', location=context.scene.cursor.location)
            
        obj = context.active_object
        counter = 0
        
        while True:
            if not any((bpy.data.objects.get("Collision%s%d" % (name, counter)) for name in ('Box', 'Sphere'))):
                obj.name = "Collision%s%d" % ('Sphere' if self.shape == 'SPHERE' else 'Box', counter)
                break
            counter += 1
        
        return {'FINISHED'}
        
class WAR3_OT_add_anim_sequence(Operator):
    bl_idname = "custom.add_anim_sequence"
    bl_label = "Add Sequence"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    name : StringProperty(
        name = "Name",
        default = "Stand"
        )
    
    start : IntProperty(
        name = "Start Frame",
        default = 1
        )
    
    end : IntProperty(
        name = "End Frame",
        default = 100
        )
    
    rarity : IntProperty(
        name = "Rarity",
        default = 0
        )
    
    non_looping : BoolProperty(
        name = "Non Looping",
        default = False
        )

    def invoke(self, context, event):
        for name in ["Stand", "Birth", "Death"]:
            if name not in (s.name for s in context.window.scene.mdl_sequences):
                self.name = name
    
        return context.window_manager.invoke_props_dialog(self, width = 400)
        
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "name")
        layout.prop(self, "start")
        layout.prop(self, "end")
        layout.prop(self, "rarity")
        layout.prop(self, "non_looping")

    def execute(self, context):
        scene = context.window.scene
        sequences = scene.mdl_sequences

        scene.timeline_markers.new(self.name, frame=self.start)
        scene.timeline_markers.new(self.name, frame=self.end)
        
        s = sequences.add()
        s.name = self.name
        s.rarity = self.rarity
        s.non_looping = self.non_looping
        
        scene.mdl_sequence_index = len(sequences) - 1
        
        return {'FINISHED'}
        
class WAR3_OT_material_list_action(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "custom.list_action"
    bl_label = "List Actions"
    bl_description = "Move items up and down, add and remove"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    name_counter = 0

    action : EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", "")))
            
    @classmethod
    def poll(self,context):
        return context.active_object is not None and context.active_object.active_material is not None

    def invoke(self, context, event):

        try:
            mat = context.active_object.active_material
            i = mat.mdl_layer_index
            item = mat.mdl_layers[i]
        except IndexError:
            pass
        else:
            if self.action == 'DOWN' and i < len(mat.mdl_layers) - 1:
                mat.mdl_layers.move(i, i+1)
                mat.mdl_layer_index += 1
            elif self.action == 'UP' and i >= 1:
                mat.mdl_layers.move(i, i-1)
                mat.mdl_layer_index -= 1

            elif self.action == 'REMOVE':
                if i > 0:
                    mat.mdl_layer_index -= 1
                if len(mat.mdl_layers):
                    mat.mdl_layers.remove(i)

        if self.action == 'ADD':
            if context.active_object:
                item = mat.mdl_layers.add()
                item.name = "Layer %d" % self.name_counter
                WAR3_OT_material_list_action.name_counter += 1
                mat.mdl_layer_index = len(mat.mdl_layers)-1
            else:
                self.report({'INFO'}, "Nothing selected in the Viewport")
                
        return {"FINISHED"}
   
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
        