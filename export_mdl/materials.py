import bpy

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       EnumProperty,
                       CollectionProperty
                       )    
            
class MaterialLayerSettings(bpy.types.PropertyGroup):
    name = StringProperty(
        name = "Name",
        description = "Name of this layer - this value is not exported.",
        default = "Layer",
        maxlen = 16
        )
        
    texture_type = EnumProperty(
        name = "Texture Type",
        items = [('0', "Image", "", 0, 0),
                 ('1', "Team Color", "", 0, 1),
                 ('2', "Team Glow", "", 0, 2),
                 ('11', "Cliff", "", 0, 11),
                 ('31', "Lordaeron Tree", "", 0, 31),
                 ('32', "Ashenvale Tree", "", 0, 32),
                 ('33', "Barrens Tree", "", 0, 33),
                 ('34', "Northrend Tree", "", 0, 34),
                 ('35', "Mushroom Tree", "", 0, 35)],
        default = '0'
        )
    filter_mode = EnumProperty(
        name = "Filter Mode",
        items = [('None', "Opaque", ""),
                 ('Blend', "Blend", ""),
                 ('Transparent', "Transparent", ""),
                 ('Additive', "Additive", ""),
                 ('AddAlpha', "Additive Alpha", ""),
                 ('Modulate', "Modulate", ""),
                 ('Modulate2x', "Modulate 2X", "")],
        default = 'None'
        )
    unshaded = BoolProperty(
        name = "Unshaded",
        description = "Whether or not to apply shadows to this layer.",
        default = False
        )
    two_sided = BoolProperty(
        name = "Two Sided",
        description = "Whether or not to render backfaces.",
        default = False
        )
        
    no_depth_test = BoolProperty(
        name = "No Depth Test",
        description = "If true, this layer will always render, even if it's occluded.",
        default = False    
        )
        
    no_depth_set = BoolProperty(
        name = "No Depth Set",
        description = "If true, this layer will never occlude other objects which are rendered afterwards.",
        default = False    
        )
        
    alpha = FloatProperty(
        name = "Alpha",
        description = "Alpha factor used with the blend filter mode. Can be animated.",
        default = 1.0,
        options = {'ANIMATABLE'},
        min = 0.0,
        max = 1.0
        )
    path = StringProperty(
        name = "Texture Path",
        default = "",
        maxlen = 256
        )
     
    @classmethod
    def register(cls):
        bpy.types.Material.mdl_layers = CollectionProperty(type=MaterialLayerSettings, options={'HIDDEN'})
        bpy.types.Material.mdl_layer_index = IntProperty(name="Layer index", description="", default=0, options={'HIDDEN'}) 
        bpy.types.Material.priority_plane = IntProperty(name="Priority Plane", description="Order at which this material will be rendered", default=0, options={'HIDDEN'})
     
    @classmethod    
    def unregister(cls):
        del bpy.types.Material.mdl_layers
        del bpy.types.Material.mdl_layer_index
        del bpy.types.Material.priority_plane

class MATERIAL_UL_mdl_layer(bpy.types.UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        icons = {'0' : 'IMAGE_DATA', '1' : 'TEXTURE', '2' : 'POTATO', '11' : 'FACESEL', 'Tree' : 'MESH_CONE'}
        icon = icons[item.texture_type] if item.texture_type in icons.keys() else icons['Tree']
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon=icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
        
class CUSTOM_OT_actions(bpy.types.Operator):
    """Move items up and down, add and remove"""
    bl_idname = "custom.list_action"
    bl_label = "List Actions"
    bl_description = "Move items up and down, add and remove"
    bl_options = {'REGISTER'}
    
    name_counter = 0

    action = bpy.props.EnumProperty(
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
                CUSTOM_OT_actions.name_counter += 1
                mat.mdl_layer_index = len(mat.mdl_layers)-1
            else:
                self.report({'INFO'}, "Nothing selected in the Viewport")
                
        return {"FINISHED"}
        
class CUSTOM_PT_MaterialPanel(bpy.types.Panel):
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
            
            row.template_list("MATERIAL_UL_mdl_layer", "", mat, "mdl_layers", mat, "mdl_layer_index", rows=2)
            
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
                    col.prop(active_layer, "path")
                col.separator()
                col.prop(active_layer, "filter_mode")
                if active_layer.filter_mode in {'Blend', 'Transparent', 'AddAlpha'}:
                    col.prop(active_layer, "alpha")
                col.separator()
                col.prop(active_layer, "unshaded")
                col.prop(active_layer, "two_sided")
                col.prop(active_layer, "no_depth_test")
                col.prop(active_layer, "no_depth_set")
                
    