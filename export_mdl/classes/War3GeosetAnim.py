class War3GeosetAnim:
    def __init__(self, color, color_anim, alpha_anim):
        self.color = color
        self.color_anim = color_anim
        self.alpha_anim = alpha_anim
        self.geoset = None
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            if self.color != other.color and not any((self.color_anim, other.color_anim)): # Color doesn't matter if there is an animation
                return False
                
            if self.geoset is not other.geoset:
                return False
                
            if self.alpha_anim != other.alpha_anim:
                return False
                
            if self.color_anim != other.color_anim:
                return False
                
            return True
            
        return NotImplemented 
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        color_hash = 0 if self.color is None else hash(self.color)
        return hash((hash(self.color_anim), hash(self.alpha_anim), color_hash))