import os

class War3EventTypesContainer:

    def __init__(self):
        self.enums = {}
        
        directory = os.path.dirname(__file__)
        
        path = os.path.join(directory, "../sound_types.txt")
        l = []
        
        with open(path, 'r') as f:
            for i in f.readlines():
                enum = i.split(" ")
                l.append((enum[0], enum[1][:-1], ""))
        
        self.enums['SND'] = l

        path = os.path.join(directory, "../splat_types.txt")
        l = []
        
        with open(path, 'r') as f:
            for i in f.readlines():
                enum = i.split(" ")
                l.append((enum[0], enum[1][:-1], ""))
        
        self.enums['SPL'] = l
        self.enums['FTP'] = l

        path = os.path.join(directory, "../ubersplat_types.txt")
        l = []
        
        with open(path, 'r') as f:
            for i in f.readlines():
                enum = i.split(" ")
                l.append((enum[0], enum[1][:-1], ""))
        
        self.enums['UBR'] = l
        
        path = os.path.join(directory, "../spawnobject_types.txt")
        l = []
        
        with open(path, 'r') as f:
            for i in f.readlines():
                enum = i.split(" ")
                l.append((enum[0], enum[1][:-1].split("\\")[-1], ""))
        
        self.enums['SPN'] = l

war3_event_types = War3EventTypesContainer()    
        
def update_event_type(self, context):
    obj = context.active_object

    counter = 0
    
    self.event_id = war3_event_types.enums[self.event_type][0][0]
    
    while True:
        if not any([ob for ob in context.scene.objects if ob.name.startswith("%s%d" % (self.event_type, counter))]):
            obj.name = "%s%d%s" % (self.event_type, counter, self.event_id)
            break
        counter += 1
    
    obj['event_type'] = self.event_type
    obj['event_id'] = self.event_id

war3_event_types = War3EventTypesContainer()

def get_event_items(self, context):
    return war3_event_types.enums[self.event_type]

def event_items(self, context):
    return war3_event_types.enums[context.window_manager.events.event_type]