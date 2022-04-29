from .War3Object import War3Object
from .War3AnimationCurve import War3AnimationCurve

class War3EventObject(War3Object):
    def __init__(self, name):
        War3Object.__init__(self, name)
        
        self.track: War3AnimationCurve