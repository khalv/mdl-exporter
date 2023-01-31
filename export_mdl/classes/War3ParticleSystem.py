from .War3AnimationCurve import War3AnimationCurve
from .War3Texture import War3Texture
from .War3Object import War3Object

class War3ParticleSystem(War3Object):
    def __init__(self, name):
        War3Object.__init__(self, name)
        
        self.emission_rate_anim = None
        self.speed_anim = None
        self.life_span_anim = None
        self.gravity_anim = None
        self.variation_anim = None
        self.latitude_anim = None
        self.longitude_anim = None
        self.alpha_anim = None
        self.ribbon_color_anim = None

        self.emitter_type = "ParticleEmitter2"
        self.filter_mode = "Blend"
        self.unshaded = False
        self.unfogged = False
        self.line_emitter = False
        self.sort_far_z = False
        self.model_space = False
        self.xy_quad = False
        self.head = True
        self.tail = False
        self.emission_rate = 100
        self.speed = 100
        self.latitude = 0
        self.longitude = 0
        self.variation = 0
        self.gravity = 0
        self.width = 100
        self.height = 100
        self.start_color = (1.0, 1.0, 1.0)
        self.mid_color = (1.0, 1.0, 1.0)
        self.end_color = (1.0, 1.0, 1.0)
        self.start_alpha = 255
        self.mid_alpha = 255
        self.end_alpha = 255
        self.start_scale = 1
        self.mid_scale = 1
        self.end_scale = 1
        self.rows = 1
        self.cols = 1
        self.life_span = 1.0
        self.tail_length = 0
        self.time = 0.5
        self.priority_plane = 0
        self.ribbon_material = 0
        self.ribbon_color = (1.0, 1.0, 1.0)
        self.texture_id = 0
        self.model_path = ""
        self.head_life_start = 0
        self.head_life_end = 0
        self.head_life_repeat = 1
        self.head_decay_start = 0
        self.head_decay_end = 0
        self.head_decay_repeat = 1
        self.tail_life_start = 0
        self.tail_life_end = 0
        self.tail_life_repeat = 1
        self.tail_decay_start = 0
        self.tail_decay_end = 0
        self.tail_decay_repeat = 1
        self.alpha = 0

    def from_object(self, obj, model):
        settings = obj.particle_systems[0].settings
        
        emitter = settings.mdl_particle_sys
        self.scale_anim = War3AnimationCurve.get(obj.animation_data, 'scale', 2, model.sequences)
        model.register_global_sequence(self.scale_anim)

        if len(emitter.texture_path):
            texture = War3Texture(emitter.texture_path)

            if texture in model.textures:
                self.texture_id = model.textures.index(texture)
            else:
                model.textures.append(texture)
                self.texture_id = len(model.textures) - 1

        self.width = obj.dimensions[0]
        self.height = obj.dimensions[1]
        self.emitter_type = emitter.emitter_type
        self.filter_mode = emitter.filter_mode
        self.unshaded = emitter.unshaded
        self.unfogged = emitter.unfogged
        self.line_emitter = emitter.line_emitter
        self.sort_far_z = emitter.sort_far_z
        self.model_space = emitter.model_space
        self.xy_quad = emitter.xy_quad
        self.head = emitter.head
        self.tail = emitter.tail
        self.emission_rate = emitter.emission_rate
        self.speed = emitter.speed
        self.latitude = emitter.latitude
        self.longitude = emitter.longitude
        self.variation = emitter.variation
        self.gravity = emitter.gravity
        self.start_color = emitter.start_color
        self.mid_color = emitter.mid_color
        self.end_color = emitter.end_color
        self.start_alpha = emitter.start_alpha
        self.mid_alpha = emitter.mid_alpha
        self.end_alpha = emitter.end_alpha
        self.start_scale = emitter.start_scale
        self.mid_scale = emitter.mid_scale
        self.end_scale = emitter.end_scale
        self.rows = emitter.rows
        self.cols = emitter.cols
        self.life_span = emitter.life_span
        self.tail_length = emitter.tail_length
        self.time = emitter.time
        self.priority_plane = emitter.priority_plane
        self.ribbon_material = emitter.ribbon_material
        self.ribbon_color = emitter.ribbon_color
        self.model_path = emitter.model_path
        self.head_life_start = emitter.head_life_start
        self.head_life_end = emitter.head_life_end
        self.head_life_repeat = emitter.head_life_repeat
        self.head_decay_start = emitter.head_decay_start
        self.head_decay_end = emitter.head_decay_end
        self.head_decay_repeat = emitter.head_decay_repeat
        self.tail_life_start = emitter.tail_life_start
        self.tail_life_end = emitter.tail_life_end
        self.tail_life_repeat = emitter.tail_life_repeat
        self.tail_decay_start = emitter.tail_decay_start
        self.tail_decay_end = emitter.tail_decay_end
        self.tail_decay_repeat = emitter.tail_decay_repeat
        self.alpha = emitter.alpha

        # Animated properties
        
        if settings.animation_data is not None:
            self.emission_rate_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.emission_rate', 1, model.sequences)
            model.register_global_sequence(self.emission_rate_anim)
                
            self.speed_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.speed', 1, model.sequences)
            model.register_global_sequence(self.speed_anim)
                
            self.life_span_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.life_span', 1, model.sequences)
            model.register_global_sequence(self.life_span_anim)
                
            self.gravity_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.gravity', 1, model.sequences)
            model.register_global_sequence(self.gravity_anim)
                
            self.variation_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.variation', 1, model.sequences)
            model.register_global_sequence(self.variation_anim)
                
            self.latitude_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.latitude', 1, model.sequences)
            model.register_global_sequence(self.latitude_anim)
                
            self.longitude_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.longitude', 1, model.sequences)
            model.register_global_sequence(self.longitude_anim)
                
            self.alpha_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.alpha', 1, model.sequences)
            model.register_global_sequence(self.alpha_anim)
                
            self.ribbon_color_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.ribbon_color', 3, model.sequences)
            model.register_global_sequence(self.ribbon_color_anim)