from .War3Object import War3Object

class War3CollisionShape(War3Object):
    def __init__(self, name):
        War3Object.__init__(self, name)
        self.type = 'Sphere'
        self.radius = 1
        self.vertices = []