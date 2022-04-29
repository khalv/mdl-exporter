class War3AnimationSequence:
    def __init__(self, name, start, end, non_looping=False, movement_speed=270):
        self.name = name
        self.start = start
        self.end = end
        self.non_looping = non_looping
        self.movement_speed = movement_speed
        self.rarity = 0