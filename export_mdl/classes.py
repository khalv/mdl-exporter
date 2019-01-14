import bpy
import math

from collections import defaultdict

from mathutils import (
    Quaternion, 
    Matrix, 
    Euler, 
    Vector
    )
    
from .utils import *
    
class War3Model:

    default_texture = "Textures\white.blp"
    decimal_places = 5

    def __init__(self, context):
        self.objects = defaultdict(set)
        self.geosets = {}
        self.materials = set()
        self.sequences = []
        self.global_extents_min = 0
        self.global_extents_max = 0
        self.geoset_anims = []
        self.geoset_anim_map = {}
        self.const_color_mats = set()
        self.global_seqs = set()
        self.global_matrix = Matrix()
        self.cameras = []
        
        self.f2ms = 1000 / context.scene.render.fps # Frame to milisecond conversion
        self.name = bpy.path.basename(context.blend_data.filepath).replace(".blend","")
        
    @staticmethod
    def prepare_mesh(obj, context, matrix):
        mod = None
        if obj.data.use_auto_smooth:
            mod = obj.modifiers.new("EdgeSplitExport", 'EDGE_SPLIT')
            mod.split_angle = obj.data.auto_smooth_angle
            # mod.use_edge_angle = True
            
        mesh = obj.to_mesh(context.scene, apply_modifiers=True, settings='RENDER')
        
        if obj.data.use_auto_smooth:
            obj.modifiers.remove(mod)

        # Triangulate for web export
        bm = bmesh.new()
        bm.from_mesh(mesh)
        # If an object has had a negative scale applied, normals will be inverted. This will fix that. 
        if any(s < 0 for s in obj.scale):
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
        bm.to_mesh(mesh)
        bm.free()
        del bm

        mesh.calc_normals_split()
        mesh.calc_tessface()

        return mesh
        
    def from_scene(self, context, use_selection):
        
        scene = context.scene
        
        self.sequences = self.get_sequences(scene)
        
        objs = []
        if use_selection:
            objs = (obj for obj in scene.objects if obj.is_visible(scene) and obj.select)
        else:
            objs = (obj for obj in scene.objects if obj.is_visible(scene))
            
            
        
        
       
    def get_sequences(self, scene):
        sequences = []
        
        for sequence in scene.mdl_sequences:
            sequences.append(War3AnimationSequence(sequence.name, sequence.start * self.f2ms, sequence.end * self.f2ms, sequence.non_looping, sequence.move_speed))
          
          
        if len(sequences) == 0:
            sequences.append(War3AnimationSequence("Stand", 0, 3333))
            
        sequences.sort(key=lambda x:x.start)
        
        return sequences
        
    def register_global_sequence(self, curve):
        if curve is not None and curve.global_sequence > 0:
            self.global_seqs.add(curve.global_sequence)
       
    @staticmethod
    def calc_bounds_radius(min_ext, max_ext):
        x = (max_ext[0] - min_ext[0])/2
        y = (max_ext[1] - min_ext[1])/2
        z = (max_ext[2] - min_ext[2])/2
        return math.sqrt(math.pow(x, 2) + math.pow(y, 2) + math.pow(z, 2))
    
    @staticmethod    
    def calc_extents(vertices):
        max_extents = tuple(max(vertices,key=itemgetter(i))[i] for i in range(3))
        min_extents = tuple(min(vertices,key=itemgetter(i))[i] for i in range(3))
        
        return min_extents, max_extents
       
    def generate(self, context):
        pass
        
        

class War3Object: # Stores information about an MDL object (not a blender object!)
    def __init__(self, name):
        self.parent = None
        self.name = name
        self.pivot = None #TODO
        self.anim_loc = None
        self.anim_rot = None
        self.anim_scale = None
        self.billboarded = False
        self.billboard_lock = (False, False, False)
        
    def set_billboard(billboard):
        bb = obj.mdl_billboard
        self.billboarded = bb.billboarded
        self.billboard_lock = (bb.billboard_lock_z, bb.billboard_lock_y, bb.billboard_lock_x)
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        # return hash(tuple(sorted(self.__dict__.items())))
        return hash(self.name)

class War3ParticleSystem(War3Object):
    def __init__(self, name, obj, model):
        War3Object.__init__(self, name)
        
        settings = obj.particle_systems[0].settings
        
        self.emitter = settings.mdl_particle_sys
        self.scale_anim = War3AnimationCurve.get(obj.animation_data, 'scale', 2, model.sequences)
        model.register_global_sequence(self.scale_anim)
        
        self.emission_rate_anim = None
        self.speed_anim = None
        self.life_span_anim = None
        self.gravity_anim = None
        self.variation_anim = None
        self.latitude_anim = None
        self.longitude_anim = None
        self.alpha_anim = None
        self.ribbon_color_anim = None
        
        # Animated properties
        
        if settings.animation_data is not None:
            # curve = fcurves.find("mdl_particle_sys.emission_rate")
            self.emission_rate_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.emission_rate', 1, model.sequences)
            model.register_global_sequence(self.emission_rate_anim)
            
            #register_global_seq(psys.emission_rate_anim, global_seqs)
                
            # curve = fcurves.find("mdl_particle_sys.speed")
            self.speed_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.speed', 1, model.sequences)
            model.register_global_sequence(self.speed_anim)
            #register_global_seq(psys.speed_anim, global_seqs)
                
            # curve = fcurves.find("mdl_particle_sys.life_span")
            self.life_span_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.life_span', 1, model.sequences)
            model.register_global_sequence(self.life_span_anim)
            #register_global_seq(psys.life_span_anim, global_seqs)
                
            # curve = fcurves.find("mdl_particle_sys.gravity")
            self.gravity_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.gravity', 1, model.sequences)
            model.register_global_sequence(self.gravity_anim)
            #register_global_seq(psys.gravity_anim, global_seqs)
                
            # curve = fcurves.find("mdl_particle_sys.variation")
            self.variation_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.variation', 1, model.sequences)
            model.register_global_sequence(self.variation_anim)
            #register_global_seq(psys.variation_anim, global_seqs)
                
            # curve = fcurves.find("mdl_particle_sys.latitude")
            self.latitude_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.latitude', 1, model.sequences)
            model.register_global_sequence(self.latitude_anim)
            #register_global_seq(psys.latitude_anim, global_seqs)
                
            # curve = fcurves.find("mdl_particle_sys.longitude")
            self.longitude_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.longitude', 1, model.sequences)
            model.register_global_sequence(self.longitude_anim)
            #register_global_seq(psys.longitude_anim, global_seqs)
                
            # curve = fcurves.find("mdl_particle_sys.alpha")
            self.alpha_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.alpha', 1, model.sequences)
            model.register_global_sequence(self.alpha_anim)
            #register_global_seq(psys.alpha_anim, global_seqs)
                
            # curves = get_curves(settings, "mdl_particle_sys.ribbon_color", (0, 1, 2))
            self.ribbon_color_anim = War3AnimationCurve.get(settings.animation_data, 'mdl_particle_sys.ribbon_color', 3, model.sequences)
            model.register_global_sequence(self.ribbon_color_anim)
            #register_global_seq(psys.ribbon_color_anim, global_seqs, [0])
    
class War3CollisionShape(War3Object):
    pass
    
class War3EventObject(War3Object):
    pass
        
class War3AnimationSequence:
    def __init__(self, name, start, end, non_looping=False, movement_speed=270):
        self.name = name
        self.start = start
        self.end = end
        self.non_looping = non_looping
        self.movement_speed = movement_speed
        
class War3AnimationCurve:
    def __init__(self, fcurves, data_path, sequences, scale=1):
        frames = set()
        
        self.interpolation = 'Linear'
        self.global_sequence = -1
        self.type = 'Default'

        if 'rotation' in data_path:
            self.type = 'Rotation'
        elif 'location' in data_path:
            self.type = 'Translation'
        elif 'color' in data_path:
            self.type = 'Color'
        elif 'event' in data_path.lower():
            self.type = 'Event'
        elif 'visibility' in data_path.lower() or 'hide_render' in data_path.lower():
            self.type = 'Boolean'
        
        f2ms = 1000 / bpy.context.scene.render.fps
        
        for fcurve in fcurves.values():
            if len(fcurve.keyframe_points):
                if fcurve.keyframe_points[0].interpolation == 'BEZIER' and self.type != 'Rotation': # Nonlinear interpolation for rotations is disabled for now
                    self.interpolation = 'Bezier'
                elif fcurve.keyframe_points[0].interpolation == 'CONSTANT':
                    self.interpolation = 'DontInterp'
                    
            for mod in fcurve.modifiers:
                if mod.type == 'CYCLES':
                    self.global_sequence = max(self.global_sequence, int(fcurve.range()[1] * f2ms))
                    
            for keyframe in fcurve.keyframe_points:
                frame = keyframe.co[0] * f2ms
                for sequence in sequences:
                    if frame >= sequence.start and frame <= sequence.end or self.global_sequence > 0:
                        frames.add(keyframe.co[0])
                        break
         
        if self.type == 'Boolean' or self.type == 'Event':
            self.interpolation == 'DontInterp'
         
        self.keyframes = {}
        self.handles_right = {}
        self.handles_left = {}
        
        for frame in frames:
            values = []
            handle_left = []
            handle_right = []
            
            keys = fcurves.keys()
            keys = sorted(keys, key=lambda x: x[1])
            for key in keys:
                value = fcurves[key].evaluate(frame)
                values.append(value * scale)
                
                if 'color' in data_path:
                    values = values[::-1] # Colors are stored in reverse
                    
                if 'hide_render' in data_path:
                    values = [1 - v for v in values] # Hide_Render is the opposite of visibility!
                
                if self.interpolation == 'Bezier':
                    hl = fcurves[key].evaluate(frame-1)
                    hr = fcurves[key].evaluate(frame+1)
                    handle_left.append(hl)
                    handle_right.append(hr)
            
            if 'rotation' in data_path and 'quaternion' not in data_path: # Warcraft 3 only uses quaternions!
                self.keyframes[frame] = tuple(Euler(values).to_quaternion())
            else:
                self.keyframes[frame] = tuple(values)
                
            if self.interpolation == 'Bezier':
                if 'rotation' in data_path and 'quaternion' not in data_path:
                    self.handles_left[frame] = tuple(Euler(math.radians(x) for x in handle_left).to_quaternion())
                    self.handles_right[frame] = tuple(Euler(math.radians(x) for x in handle_right).to_quaternion())
                else:
                    self.handles_right[frame] = tuple(handle_right)
                    self.handles_left[frame] = tuple(handle_right)

    def transform_rot(self, matrix):
        for frame in self.keyframes.keys():
            axis, angle = Quaternion(self.keyframes[frame]).to_axis_angle()
            
            axis.rotate(matrix)
            quat = Quaternion(axis, angle)
            quat.normalize()
            
            self.keyframes[frame] = tuple(quat)
            
    def transform_vec(self, matrix):
        for frame in self.keyframes.keys():
            self.keyframes[frame] = tuple(matrix * Vector(self.keyframes[frame]))
            if self.interpolation == 'Bezier':
                self.handles_right[frame] = tuple(matrix * Vector(self.handles_right[frame]))
                self.handles_left[frame] = tuple(matrix * Vector(self.handles_left[frame]))
            
        
    def write_mdl(self, name, fw, global_seqs, indent="\t"):
    
        f2ms = 1000 / bpy.context.scene.render.fps
    
        fw(indent+"%s %d {\n" % (name, len(self.keyframes)))
        
        if self.type != 'Event':
            fw(indent+"\t%s,\n" % self.interpolation)
        if self.global_sequence > 0:
            fw(indent+"\tGlobalSeqId %d,\n" % global_seqs.index(self.global_sequence))
            
        for frame in sorted(self.keyframes.keys()):
            line = ""
            n = len(self.keyframes[frame])
            
            if n > 1:
                line += "{ "
            
            line += '%s, '*(n-1)
            line += '%s'
            
            if n > 1:
                line += ' },\n'
            else:
                line += ',\n'
            
            if self.type == 'Event':
                fw(indent+"\t%d,\n" % (frame * f2ms))
            else:
                keyframe = self.keyframes[frame]
                
                if self.type == 'Rotation':
                    keyframe = keyframe[1:] + keyframe[:1] # MDL quaternions must be on the form XYZW
                
                s = "\t%d: " % (frame * f2ms)
                fw(indent+s+line % tuple(f2s(rnd(x)) for x in keyframe))

                    
                if self.interpolation == 'Bezier':
                    hl = self.handles_left[frame]
                    hr = self.handles_right[frame]
                    
                    if self.type == 'Rotation':
                        hl = hl[1:]+hl[:1]
                        hr = hr[1:]+hr[:1]
                
                    fw(indent+"\t\tInTan "+line % tuple(f2s(rnd(x)) for x in hl))
                    fw(indent+"\t\tOutTan "+line % tuple(f2s(rnd(x)) for x in hr))  
           
        fw(indent+"}\n")
        
    def write_mdx(self):
        pass
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            if self.interpolation != other.interpolation:
                return False
            if self.global_sequence != other.global_sequence:
                return False
            if len(self.keyframes) != len(other.keyframes):
                return False
                
            return self.keyframes == other.keyframes and self.handles_left == other.handles_left and self.handles_right == other.handles_right
            
        return NotImplemented
    
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        values = [self.interpolation, self.global_sequence, self.type]
        values.append(tuple(self.keyframes.items()))
        values.append(tuple(self.handles_left.items()))
        values.append(tuple(self.handles_right.items()))
        return hash(tuple(values))
                
    @staticmethod
    def get(anim_data, data_path, num_indices, sequences, scale=1):
        curves = {}
   
        if anim_data and anim_data.action:
            for index in range(num_indices):
                curve = anim_data.action.fcurves.find(data_path, index)
                if curve is not None:
                    curves[(data_path.split('.')[-1], index)] = curve # For now, i'm just interested in the type, not the whole data path. Hence, the split returns the name after the last dot. 
            
        if len(curves):
            return War3AnimationCurve(curves, data_path, sequences, scale)
        return None
        
class War3TextureAnim:
    def __init__(self):
        self.translation = None
        self.rotation = None
        self.scale = None
                
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            a = [self.translation, self.rotation, self.scale]
            b = [other.translation, other.rotation, other.scale]
                
            for x, y in zip(a, b):
                if x != y:
                    return False
                
            return True
            
        return NotImplemented
        
    def __hash__(self):
        return hash(tuple(hash(self.translation), hash(self.rotation), hash(self.scale)))
      
    @staticmethod
    def get(anim_data, uv_node, sequences):
        anim = War3TextureAnim()
        if anim_data.action:
            anim.translation = War3AnimationCurve.get(anim_data, 'translation', 3, sequences)
            anim.rotation = War3AnimationCurve.get(anim_data, 'rotation', 3, sequences)
            anim.scale = War3AnimationCurve.get(anim_data, 'scale', 3, sequences)
                    
        return anim if any((anim.translation, anim.rotation, anim.scale)) else None
        
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
        return hash((self.color, hash(self.color_anim), hash(self.alpha_anim), hash(self.color)))
        
class War3Geoset:
    def __init__(self):
        self.vertices = []
        self.triangles = []
        self.matrices = []
        self.objects = []
        self.min_extent = None
        self.max_extent = None
        self.mat_name = None
        self.geoset_anim = None
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.mat_name == other.mat_name and self.geoset_anim == other.geoset_anim
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        # return hash(tuple(sorted(self.__dict__.items())))
        return hash((self.mat_name, hash(self.geoset_anim))) # Different geoset anims should split geosets
        
class War3MaterialLayer:
    def __init__(self):
        self.texture = "Textures\white.blp"
        self.filter_mode = "None"
        self.unshaded = False
        self.two_sided = False
        self.unfogged = False
        self.texture_anim = None
        self.alpha_anim = None
        self.alpha_value = 1
        self.no_depth_test = False
        self.no_depth_set = False
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        return hash(tuple(sorted(self.__dict__.items())))
    
class War3Material:
    def __init__(self, name):
        self.name = name
        self.layers = []
        self.use_const_color = False
        self.priority_plane = 0
        
    @staticmethod    
    def get(mat, model):
        material = War3Material(mat.name)
        
        # Should we use vertex color?
        for geoset in model.geosets.values():
            if geoset.geoset_anim is not None and geoset.mat_name == mat.name:
                if any((geoset.geoset_anim.color, geoset.geoset_anim.color_anim)):
                    material.use_const_color = True
                
        
        material.priority_plane = mat.priority_plane
        material.layers = []
        
        for i, layer_settings in enumerate(mat.mdl_layers):    
            layer = War3MaterialLayer()
            
            layer.texture = layer_settings.path if layer_settings.texture_type == '0' else "ReplaceableId %s" % layer_settings.texture_type
            if layer_settings.texture_type == '36':
                layer.texture = "ReplaceableId %s" % layer_settings.replaceable_id
                
            layer.filter_mode   = layer_settings.filter_mode
            layer.unshaded      = layer_settings.unshaded
            layer.two_sided     = layer_settings.two_sided
            layer.no_depth_test = layer_settings.no_depth_test
            layer.no_depth_set  = layer_settings.no_depth_set
            layer.alpha_value   = layer_settings.alpha
            layer.alpha_anim    = War3AnimationCurve.get(mat.animation_data, 'mdl_layers[%d].alpha' % i, 1, model.sequences) # get_curve(mat, {'mdl_layers[%d].alpha' % i})
            
            if mat.use_nodes:
                uv_node = mat.node_tree.nodes.get(layer_settings.name, None)
                if uv_node is not None and mat.node_tree.animation_data is not None:
                    layer.texture_anim = War3TextureAnim.get(mat.node_tree.animation_data, uv_node, model.sequences)
                    if layer.texture_anim is not None:
                        model.register_global_sequence(layer.texture_anim.translation)
                        model.register_global_sequence(layer.texture_anim.rotation)
                        model.register_global_sequence(layer.texture_anim.scale)
    
            material.layers.append(layer)
                
        
        if not len(material.layers):
            material.layers.append(War3MaterialLayer())
        
        return material
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        # return hash(tuple(sorted(self.__dict__.items())))
        return hash(self.name)
        
    def write_mdl(fw):
        pass