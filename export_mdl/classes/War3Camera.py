from .War3Object import War3Object

class War3Camera(War3Object):
    def __init__(self, name):
        War3Object.__init__(self, name)
        self.field_of_view = 120
        self.far_clip = 1200
        self.near_clip = 100