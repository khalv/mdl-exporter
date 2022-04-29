class War3MaterialLayer:
    def __init__(self):
        self.texture_id = 0
        self.texture_id_anim = None
        self.filter_mode = "None"
        self.unshaded = False
        self.two_sided = False
        self.unfogged = False
        self.texture_anim = None
        self.texture_anim_id = None
        self.alpha_anim = None
        self.alpha_value = 1
        self.no_depth_test = False
        self.no_depth_set = False
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        return hash(tuple(sorted(self.__dict__.items())))