from .War3Object import War3Object

class War3Light(War3Object):
    def __init__(self, name):
        War3Object.__init__(self, name)

        self.type = 'Omnidirectional'
        self.intensity = 1        
        self.atten_start = 80
        self.atten_end = 200
        self.color = (1, 1, 1)
        self.amb_color = (0, 0, 0)
        self.amb_intensity = 0