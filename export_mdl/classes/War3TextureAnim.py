from .War3AnimationCurve import War3AnimationCurve

class War3TextureAnim:
    def __init__(self):
        self.translation = None
        self.rotation = None
        self.scale = None
                
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            a = [self.translation, self.rotation, self.scale]
            b = [other.translation, other.rotation, other.scale]
                
            for x, y in zip(a, b):
                if x != y:
                    return False
                
            return True
            
        return NotImplemented
       
    def __ne__(self, other):
        return not self.__eq__(other)
       
    def __hash__(self):
        return hash((hash(self.translation), hash(self.rotation), hash(self.scale)))

    @staticmethod
    def read_mdl(model, parser):
        pass

    @staticmethod
    def read_mdx(model, parser):
        pass

    def write_mdl(self, model, writer):
        pass

    def write_mdx(self, model, writer):
        pass
      
    @staticmethod
    def get(anim_data, uv_node, sequences):
        anim = War3TextureAnim()
        if anim_data.action:
            if len(uv_node.inputs) > 1: # 2.81 Mapping Node
                anim.translation = War3AnimationCurve.get(anim_data, 'nodes["%s"].inputs["Location"].default_value' % uv_node.name, 3, sequences)
                anim.rotation = War3AnimationCurve.get(anim_data, 'nodes["%s"].inputs["Rotation"].default_value' % uv_node.name, 3, sequences)
                anim.scale = War3AnimationCurve.get(anim_data, 'nodes["%s"].inputs["Scale"].default_value' % uv_node.name, 3, sequences)
            else:
                anim.translation = War3AnimationCurve.get(anim_data, 'nodes["%s"].translation' % uv_node.name, 3, sequences)
                anim.rotation = War3AnimationCurve.get(anim_data, 'nodes["%s"].rotation' % uv_node.name, 3, sequences)
                anim.scale = War3AnimationCurve.get(anim_data, 'nodes["%s"].scale' % uv_node.name, 3, sequences)
                    
        return anim if any((anim.translation, anim.rotation, anim.scale)) else None