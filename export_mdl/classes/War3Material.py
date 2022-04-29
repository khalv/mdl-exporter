from .War3AnimationCurve import War3AnimationCurve
from .War3MaterialLayer import War3MaterialLayer
from .War3Texture import War3Texture
from .War3TextureAnim import War3TextureAnim

class War3Material:
    def __init__(self, name):
        self.name = name
        self.layers = []
        self.use_const_color = False
        self.priority_plane = 0
        
    @staticmethod    
    def get(mat, model):
        material = War3Material(mat.name)
        
        # Should we use vertex color?
        for geoset in model.geosets:
            if geoset.geoset_anim is not None and geoset.mat_name == mat.name:
                if any((geoset.geoset_anim.color, geoset.geoset_anim.color_anim)):
                    material.use_const_color = True
                
        
        material.priority_plane = mat.priority_plane
        material.layers = []
        
        for i, layer_settings in enumerate(mat.mdl_layers):    
            layer = War3MaterialLayer()
            
            texture = War3Texture(layer_settings.path)
            if layer_settings.texture_type != '0':
                texture.replaceable_id = int(layer_settings.texture_type)
                texture.is_replaceable = True
                texture.image_path = None

                if layer_settings.texture_type == '36':
                    layer.replaceable_id = layer_settings.replaceable_id

            if texture in model.textures:
                layer.texture_id = model.textures.index(texture)
            else:
                model.textures.append(texture)
                layer.texture_id = len(model.textures) - 1
                
            layer.filter_mode   = layer_settings.filter_mode
            layer.unshaded      = layer_settings.unshaded
            layer.two_sided     = layer_settings.two_sided
            layer.no_depth_test = layer_settings.no_depth_test
            layer.no_depth_set  = layer_settings.no_depth_set
            layer.alpha_value   = layer_settings.alpha
            layer.alpha_anim    = War3AnimationCurve.get(mat.animation_data, 'mdl_layers[%d].alpha' % i, 1, model.sequences) # get_curve(mat, {'mdl_layers[%d].alpha' % i})
            
            if layer.alpha_anim is not None:
                model.register_global_sequence(layer.alpha_anim)

            if mat.use_nodes:
                uv_node = mat.node_tree.nodes.get(layer_settings.name)
                if uv_node is not None and mat.node_tree.animation_data is not None:
                    layer.texture_anim = War3TextureAnim.get(mat.node_tree.animation_data, uv_node, model.sequences)
                    if layer.texture_anim is not None:
                        model.register_global_sequence(layer.texture_anim.translation)
                        model.register_global_sequence(layer.texture_anim.rotation)
                        model.register_global_sequence(layer.texture_anim.scale)
    
            material.layers.append(layer)
                
        
        if not len(material.layers):
            material.layers.append(War3MaterialLayer())
        
        return material
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        return hash(self.name)
        
    def write_mdl(fw):
        pass