class War3Texture:
    def __init__(self, image_path):
        self.image_path = image_path
        self.is_replaceable = False
        self.replaceable_id = 0   

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            a = [self.image_path, self.is_replaceable, self.replaceable_id]
            b = [other.image_path, other.is_replaceable, other.replaceable_id]

            for x, y in zip(a, b):
                if x != y:
                    return False
                
            return True
            
        return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((hash(self.image_path), hash(self.is_replaceable), hash(self.replaceable_id)))