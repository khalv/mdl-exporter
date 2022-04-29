from .War3Object import War3Object

class War3Bone(War3Object):
    def __init__(self, name):
        War3Object.__init__(self, name)
        self.geoset_id = None
        self.geoset_anim_id = None