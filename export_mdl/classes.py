import bpy
import math

from collections import defaultdict

from mathutils import (
    Quaternion, 
    Matrix, 
    Euler, 
    Vector
    )
    
class War3Model:

    default_texture = "Textures\white.blp"
    decimal_places = 5

    def __init__(self, context):
        self.objects = defaultdict(set)
        self.geosets = {}
        self.materials = set()
        self.sequences = None
        self.global_extents_min = 0
        self.global_extents_max = 0
        self.geoset_anims = []
        self.geoset_anim_map = {}
        self.const_color_mats = set()
        self.global_seqs = set()
        self.global_matrix = Matrix()
        
        self.f2ms = 1000 / context.scene.render.fps # Frame to milisecond conversion
        self.name = bpy.path.basename(context.blend_data.filepath)
        
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
        
        objs = []
        if use_selection:
            objs = (obj for obj in scene.objects if obj.is_visible(scene) and obj.select)
        else:
            objs = (obj for obj in scene.objects if obj.is_visible(scene))
            
            
        
        
       
    def get_sequences(self, scene):
        markers = [(s.name, s.frame) for s in scene.timeline_markers]
        markers.sort(key=lambda x:x[1])
        sequences = []
        
        for sequence in scene.mdl_sequences:
            start=min(tuple(m.frame*self.f2ms for m in scene.timeline_markers if m.name == sequence.name))
            end=max(tuple(m.frame*self.f2ms for m in scene.timeline_markers if m.name == sequence.name))
            
            sequences.append(War3AnimationSequence(sequence.name, start, end, sequence.non_looping, sequence.move_speed))
            
        return sequences
       
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
    pass
    
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
        
class War3Animation:
    def __init__(self, fcurves, data_path, model, scale=1):
        frames = set()
        
        self.interpolation = 'Linear'
        self.global_sequence = -1
        self.type = 'Default'
        
        for fcurve in fcurves.values():
            if len(fcurve.keyframe_points):
                if fcurve.keyframe_points[0].interpolation == 'BEZIER':
                    self.interpolation = 'Bezier'
                elif fcurve.keyframe_points[0].interpolation == 'CONSTANT':
                    self.interpolation = 'DontInterp'
                    
            for mod in fcurve.modifiers:
                if mod.type == 'CYCLES':
                    self.global_sequence = max(self.global_sequence, int(fcurve.range()[1] * model.f2ms)) # f2ms FIXME? GLOBAL?
                    
            for keyframe in fcurve.keyframe_points:
                frame = keyframe.co[0] * model.f2ms
                for sequence in model.sequencences:
                    if frame >= sequence[1] and frame <= sequence[2]:
                        frames.add(keyframe.co[0])
                        break

        if self.global_sequence > 0:
            sequence_list.add(self.global_sequence)
         
        if data_path in {'visibiliy'}:
            self.interpolation == 'DontInterp'
         
        self.keyframes = {}
        self.handles_right = {}
        self.handles_left = {}
        
        for frame in frames:
            value = []
            handle_left = []
            handle_right = []
            
            for key in fcurves.keys():
                value = fcurves[key].evaluate(frame)
                values.append(value * scale)
                
                if 'color' in data_path:
                    values = values[::-1] # Colors are stored in reverse
                
                if self.interpolation == 'Bezier':
                    hl = fcurves[key].evaluate(frame-1)
                    hr = fcurves[key].evaluate(frame+1)
                    handle_left.append(hl)
                    handle_right.append(hr)
            
            if data_path == 'rotation_euler':
                self.keyframes[frame] = tuple(Euler(math.radians(x) for x in values).to_quaternion())
            else:
                self.keyframes[frame] = tuple(values)
                
            if self.interpolation == 'Bezier':
                if data_path == 'rotation_euler':
                    self.handles_left[frame] = tuple(Euler(math.radians(x) for x in handle_left).to_quaternion())
                    self.handles_right[frame] = tuple(Euler(math.radians(x) for x in handle_right).to_quaternion())
                else:
                    self.handles_right[frame] = tuple(handle_right)
                    self.handles_left[frame] = tuple(handle_right)

    def transform(self, matrix):
        for frame in self.keyframes.keys():
            vec = Vector(self.keyframes[frame])
            self.keyframes[frame] = matrix.to_quaternion() * q * matrix.inverted().to_quaternion()
            
        
    def write_mdl(name, fw, global_seqs, indent="\t"):
    
        fw(indent+"%s %d {\n" % (name, len(self.keyframes)))
        
        fw(indent+"\t%s,\n" % self.interpolation)
        if self.global_sequence > 0:
            fw(indent+"\tGlobalSeqId %d,\n" % global_seqs.index(self.global_sequence))
            
        for frame in sorted(self.keyframes.keys()):
            fw(indent+"\t%d: { %s, %s, %s, %s },\n" % (f2ms * frame, *(f2s(rnd(x)) for x in self.keyframes[frame])))
            if self.interpolation == 'Bezier':
                fw(indent+"\t\tInTan { %s, %s, %s, %s },\n" % tuple(f2s(rnd(x)) for x in self.handles_left[frame]))
                fw(indent+"\t\tOutTan { %s, %s, %s, %s },\n" % tuple(f2s(rnd(x)) for x in self.handles_right[frame]))  
           
        fw(indent+"}\n")
        
    def write_mdx():
        pass
    
    @staticmethod
    def get_global_seq(fcurve):

        if fcurve is not None and fcurve.modifiers:
            for mod in fcurve.modifiers:
                if mod.type == 'CYCLES':
                    return int(fcurve.range()[1] * f2ms)
        return -1
        
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
    def get(obj, data_path, num_indices, sequences, scale):
        curves = {}
   
        if obj.animation_data and obj.animation_data.action:
            for index in range(num_indices):
                curve = obj.animation_data.action.fcurves.find(data_path, index)
                if curve is not None:
                    curves[(data_path.split('.')[-1], index)] = curve # For now, i'm just interested in the type, not the whole data path. Hence, the split returns the name after the last dot. 
            
        if len(curves):
            return War3Animation(curves, data_path, sequences, scale)
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
            
            if a.count(None) != b.count(None):
                return False
                
            for c1, c2 in zip(a, b):
                if c1 is not None and c2 is not None:
                    if c1.keys() != c2.keys():
                        return False
                    for key in c1.keys():
                        if not compare_curves(c1[key], c2[key]):
                            return False
            return True
            
        return NotImplemented
        
    def __hash__(self):
    
        value_list = []
        for c in (self.translation, self.rotation, self.scale):
            if c is not None:
                for key in c.keys():
                    curve = c[key]
                    value_list.append(get_global_seq(curve))
                    value_list.append((*k.co, *k.handle_left, *k.handle_right, k.interpolation) for k in curve.keyframe_points)

        return hash(tuple(value_list))
        
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
            if not self.geoset is other.geoset:
                return False
            if not compare_curves(self.alpha_anim, other.alpha_anim):
                return False
            if all((self.color_anim, other.color_anim)):
                if self.color_anim.keys() != other.color_anim.keys():
                    return False
                for key in self.color_anim.keys():
                    if not compare_curves(self.color_anim[key], other.color_anim[key]):
                        return False
            
            return not any((self.color_anim, other.color_anim))
        return NotImplemented 
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        # return hash(tuple(sorted(self.__dict__.items())))
        alpha_keys = None
        value_list = []
        if self.alpha_anim is not None:      
            value_list.append(get_global_seq(self.alpha_anim))
            value_list.append((*k.co, *k.handle_left, *k.handle_right, k.interpolation) for k in self.alpha_anim.keyframe_points)
        if self.color_anim is not None:
            for key in self.color_anim.keys():
                curve = self.color_anim[key]
                value_list.append(get_global_seq(curve))
                value_list.append((*k.co, *k.handle_left, *k.handle_right, k.interpolation) for k in curve.keyframe_points)

        return hash(tuple((self.color, *value_list)))
        
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
            return self.mat_name == other.mat_name and self.geoset_anim is other.geoset_anim
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        # return hash(tuple(sorted(self.__dict__.items())))
        return hash((self.mat_name, self.geoset_anim)) # Different geoset anims should split geosets
        
class War3MaterialLayer:
    def __init__(self):
        self.texture = default_texture
        self.filter_mode = "None"
        self.unshaded = False
        self.two_sided = False
        self.unfogged = False
        self.texture_anim = None
        self.alpha_anim = None
        self.alpha_value = 1
        self.no_depth_test = False
        self.no_depth_set = False
     
    @staticmethod
    def get_filter_mode(tag):
        if tag == 'ADD':
            return 'Additive'
        elif tag == 'MIX':
            return 'Blend'
        elif tag == 'MULTIPLY':
            return 'Modulate'
        elif tag == 'SOFT_LIGHT' or tag == 'SCREEN':
            return 'AddAlpha'
        
        return 'None'
        
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
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        # return hash(tuple(sorted(self.__dict__.items())))
        return hash(self.name)