import bpy
import bmesh
import itertools
import math
from mathutils import Vector, Matrix, Quaternion, Euler
from operator import itemgetter
from collections import defaultdict

# -- Object types -- #
# Bone
# Light
# Helper
# Attachment
# Particle Emitter
# Particle Emitter 2
# Ribbon Emitter
# Event Object
# Collision shape
# ------------------ #

class Object: # Stores information about an MDL object (not a blender object!)
    def __init__(self, name):
        self.parent = None
        self.name = name
        self.pivot = None #TODO
        self.anim_loc = None
        self.anim_rot = None
        self.anim_scale = None
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        # return hash(tuple(sorted(self.__dict__.items())))
        return hash(self.name)

class TextureAnim:
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
        
class GeosetAnim:
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
        
class Geoset:
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
        
class MaterialLayer:
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
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented
        
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        return hash(tuple(sorted(self.__dict__.items())))
    
class Material:
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
        
def rnd(val):
    return round(val, decimal_places)
    
def f2s(value):
    return ('%.6f' % value).rstrip('0').rstrip('.')
    
def get_interp(interp):
    if interp == 'BEZIER':
        return 'Bezier'
    elif interp == 'LINEAR':
        return 'Linear'
    return 'DontInterp'
    
def get_curve(obj, data_paths):
    if obj.animation_data and obj.animation_data.action:
        for path in data_paths:
            curve = obj.animation_data.action.fcurves.find(path)
            if curve is not None:
                return curve
    return None
    
def get_curves(obj, data_path, indices):
    curves = {}
    if obj.animation_data and obj.animation_data.action:
        for index in indices:
            curve = obj.animation_data.action.fcurves.find(data_path, index)
            if curve is not None:
                curves[(data_path.split('.')[-1], index)] = curve # For now, i'm just interested in the type, not the whole data path. Hence, the split returns the name after the last dot. 
    if len(curves):
        return curves
    return None
    
def compare_curves(c1, c2):
    if not any((c1, c2)):
        return True
        
    if not all((c1, c2)):
        return False
        
    if len(c1.keyframe_points) != len(c2.keyframe_points):
        return False
        
    for k1, k2 in zip(c1.keyframe_points, c2.keyframe_points):
        if k1.co != k2.co or k1.handle_left != k2.handle_left or k1.handle_right != k2.handle_right:
            return False
        if k1.interpolation != k2.interpolation:
            return False
        if get_global_seq(c1) != get_global_seq(c2):
            return False
    return True
    
def get_sequences(scene):
    markers = [(s.name, s.frame) for s in scene.timeline_markers]
    markers.sort(key=lambda x:x[1])
    f2ms = 1000 / scene.render.fps
    sequences = []
    
    i = 0
    while i < len(markers):
        assert (markers[i+1] is not None and markers[i][0] == markers[i+1][0]), "Missing end frame for sequence %s!" % markers[i][0]
        sequences.append((markers[i][0], f2ms * int(markers[i][1]), f2ms * int(markers[i+1][1]))) # Name, start, end
        i += 2
        
    return sequences
    
def get_node_of_type(node, type):
    for input in node.inputs:
        link = None 
        if len(input.links):
            link = input.links[0]
        if link is not None:
            if link.from_node.bl_static_type == type:
                return link.from_node
            else:
                return get_node_of_type(link.from_node, type)

def get_texture_node(node):
    textures = []
    for input in node.inputs:
        link = input.links[0]
        if link is not None:
            if link.from_node.bl_static_type == 'TEX_IMAGE':
                if link.from_node.image is not None:
                    textures.append(link.from_node)
            else:
                texture = get_texture_node(link.from_node)
                if texture is not None:
                    textures.append(texture)
    
    if len(textures):
        return textures[0]
    else:
        return None

def get_texture_anim(animdata, uv_node):
    anim = TextureAnim()
    if animdata.action:
        for tag in ('translation', 'rotation', 'scale'):
            curves = {}
            for i in (0, 1, 2):
                fcurve = animdata.action.fcurves.find('nodes[\"%s\"].%s' % (uv_node.name, tag), i)    
                if fcurve is not None:
                    curves[(tag, i)] = fcurve
            if len(curves):
                setattr(anim, tag, curves)
                
    return anim if any((anim.translation, anim.rotation, anim.scale)) else None
  
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
    
def get_layers_cycles(node, anim_data):
    layers = []
    
    if node is None:
        return layers
        
    if node.bl_static_type == 'MIX_SHADER':
        # Mix shader creates a layer split
        for input in node.inputs:
            if len(input.links):
                layers += get_layers_cycles(input.links[0].from_node, anim_data)
    elif node.bl_static_type in ('BSDF_DIFFUSE', 'BSDF_TRANSPARENT', 'BSDF_EMISSION'):
        tex_node = get_node_of_type(node, 'TEX_IMAGE')
        if tex_node is not None:
            layer = MaterialLayer()
            layer.texture = tex_node.image.name
            
            mapping_node = get_node_of_type(tex_node, 'MAPPING')
            if (mapping_node is not None):
                layer.texture_anim = get_texture_anim(anim_data, mapping_node)
            
            if node.bl_static_type == 'BSDF_EMISSION':
                layer.unshaded = True

            if node.bl_static_type == 'BSDF_TRANSPARENT':
                layer.filter_mode = 'Transparent'
                
            layers.append(layer)
    elif node.bl_static_type == 'ADD_SHADER':
        pass
    
    return layers
    
def get_layers_bi(node, anim_data):
    layers = []
    
    if node is None:
        return layers
    
    return layers
    
def get_layers_from_slots(texture_slots):
    layers = []
    for slot in texture_slots:
        if slot and slot.texture:
            if slot.texture.type == 'IMAGE':
                layer = MaterialLayer()
                if slot.texture.image is not None:
                    layer.texture = slot.texture.image.name
                layer.filter_mode = get_filter_mode(slot.blend_type)
                layer.alpha_value = slot.alpha_factor
                if slot.use_map_emit and (slot.emit_factor > 0 or slot.emission_factor > 0):
                    layer.unshaded = True
                    
                layers.append(layer)
                
    return layers
  
def parse_materials(materials, const_color_mats, global_seqs):
    result = []
    
    for mat in materials:
        material = Material(mat.name)
        
        if mat in const_color_mats:
            material.use_const_color = True
            
            
        if hasattr(mat, "mdl_layers"):
            if hasattr(mat, "priority_plane"):
                material.priority_plane = mat.priority_plane
            material.layers = []
            # Use the stored layers from the layer editor
            for i, layer_settings in enumerate(mat.mdl_layers):    
                layer = MaterialLayer()
                layer.texture = layer_settings.path if layer_settings.texture_type == '0' else "ReplaceableId %s" % layer_settings.texture_type
                if layer_settings.texture_type == '36':
                    layer.texture = "ReplaceableId %s" % layer_settings.replaceable_id
                layer.filter_mode = layer_settings.filter_mode
                layer.unshaded = layer_settings.unshaded
                layer.two_sided = layer_settings.two_sided
                layer.no_depth_test = layer_settings.no_depth_test
                layer.no_depth_set = layer_settings.no_depth_set
                layer.alpha_value = layer_settings.alpha
                layer.alpha_anim = get_curve(mat, {'mdl_layers[%d].alpha' % i})
                
                if mat.use_nodes:
                    uv_node = mat.node_tree.nodes.get(layer_settings.name, None)
                    if uv_node is not None and mat.node_tree.animation_data is not None:
                        layer.texture_anim = get_texture_anim(mat.node_tree.animation_data, uv_node)
                        if layer.texture_anim is not None:
                            if layer.texture_anim.translation is not None:
                                global_seq = get_global_seq(list(layer.texture_anim.translation.values())[0])
                                if global_seq > 0:
                                    global_seqs.add(global_seq)
                            if layer.texture_anim.rotation is not None:
                                global_seq = get_global_seq(list(layer.texture_anim.rotation.values())[0])
                                if global_seq > 0:
                                    global_seqs.add(global_seq)
                            if layer.texture_anim.scale is not None:
                                global_seq = get_global_seq(list(layer.texture_anim.scale.values())[0])
                                if global_seq > 0:
                                    global_seqs.add(global_seq)
                        
        
                material.layers.append(layer)

        else:
            # Try to derive the material from its setup. This is a legacy method.
            if mat.use_nodes:
                output = mat.node_tree.nodes.get("Material Output")
                animdata = mat.node_tree.animation_data
                if output is not None:
                    # Cycles material
                    link = output.inputs[0].links[0]
                    if link is not None:
                        material.layers = get_layers_cycles(link.from_node, animdata)
                else:
                    output = mat.node_tree.nodes.get("Output")
                    if output is not None:
                        # Blender Internal material
                        link = output.inputs[0].links[0]
                        if link is not None:
                            material.layers = get_layers_bi(link.from_node, animdata)
            
            else: 
                material.layers = get_layers_from_slots(mat.texture_slots)
            
        if not len(material.layers):
            material.layers = [MaterialLayer()] # Default layer
            
        result.append(material)
        
    return result
    
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
    
def calc_bounds_radius(min_ext, max_ext):
    x = (max_ext[0] - min_ext[0])/2
    y = (max_ext[1] - min_ext[1])/2
    z = (max_ext[2] - min_ext[2])/2
    return math.sqrt(math.pow(x, 2) + math.pow(y, 2) + math.pow(z, 2))
    
def calc_extents(vertices):
    max_extents = tuple(max(vertices,key=itemgetter(i))[i] for i in range(3))
    min_extents = tuple(min(vertices,key=itemgetter(i))[i] for i in range(3))
    
    return min_extents, max_extents
    
# Cycles modifier is used to create looping sequences
def get_global_seq(fcurve):

    if fcurve is not None and fcurve.modifiers:
        for mod in fcurve.modifiers:
            if mod.type == 'CYCLES':
                return int(fcurve.range()[1] * f2ms)
    return -1
    
def register_global_seq(fcurve, global_seqs, keys=None):
    if fcurve is None:
        return
    if keys != None:
        for key in keys:
            if key in fcurve.keys():
                sequence = get_global_seq(fcurve[key])
                if sequence > 0:
                    global_seqs.add(sequence)
    else:
        sequence = get_global_seq(fcurve)
        if sequence > 0:
            global_seqs.add(sequence)
            
def get_parent(obj):
    parent = obj.parent
   
    if parent is None:
        return None # Instead return object name??
        
    if obj.parent_type == 'BONE': #TODO: Check if animated - otherwise, make it a helper
        return obj.parent_bone if obj.parent_bone != "" else None
        
    if parent.type == 'EMPTY' and parent.name.startswith("Bone_"):
        return parent.name
        
    anim_loc = get_curves(parent, 'location', (1, 2, 3))
    anim_rot = get_curves(parent, 'rotation_quaternion', (1, 2, 3, 4))
    anim_scale = get_curves(parent, 'scale', (1, 2, 3))
    animations = (anim_loc, anim_rot, anim_scale)
    
    if not any(animations):
        root_parent = get_parent(parent)
        if root_parent is not None:
            return root_parent
            
    return get_parent(parent)
  
def write_billboard(fw, billboarded, billboard_lock):
    for flag, axis in zip(billboard_lock, ('Z', 'Y', 'X')):
        if flag == True:
            fw("\tBillboardedLock%s,\n" % axis)
    if billboarded == True:
        fw("\tBillboarded,\n")
  
def write_anim(curve, name, fw, global_seqs, indent="", no_interp=False, scale=1):
    fw(indent+"%s %d {\n" % (name, len(curve.keyframe_points)))
    
    interp = get_interp(curve.keyframe_points[0].interpolation)
    if no_interp == True:
        interp = 'DontInterp'
    
    fw(indent+"\t%s,\n" % interp)
    
    global_seq = get_global_seq(curve)
    if global_seq > 0:
        fw(indent+"\tGlobalSeqId %d,\n" % global_seqs.index(global_seq))
        
    for frame in curve.keyframe_points:
        handle_l = frame.handle_left[1] * scale
        handle_r = frame.handle_right[1] * scale
        
        fw(indent+"\t%d: %s,\n" % (f2ms * frame.co[0], f2s(rnd(frame.co[1] * scale))))
        if interp == 'Bezier':
            fw(indent+"\t\tInTan %s,\n" % f2s(rnd(handle_l)))
            fw(indent+"\t\tOutTan %s,\n" % f2s(rnd(handle_r)))
    fw(indent+"}\n")    

    
def transform_rot(q, bone_matrix, global_matrix):
    rot = global_matrix.to_quaternion() * q * global_matrix.inverted().to_quaternion() 
    rot.normalize()
    return rot
    
# TODO: Add axis correction and recycle this function to support euler bone animations.
def write_anim_euler(anim, name, data_path, fw, global_seqs, indent="\t"):
    xcurve = anim[(data_path, 0)]
    ycurve = anim[(data_path, 1)]
    zcurve = anim[(data_path, 2)]
    
    fw(indent+"%s %d {\n" % (name, len(xcurve.keyframe_points)))
    
    interp = get_interp(xcurve.keyframe_points[0].interpolation)
    if (interp == 'Bezier'):
        fw(indent+"\tHermite,\n") # Rotations use hermite interpolation
    else:
        fw(indent+"\t%s,\n" % interp) # Interpolation mode 
    
    if get_global_seq(xcurve) > 0:
        fw(indent+"\tGlobalSeqId %d,\n" % global_seqs.index(get_global_seq(xcurve)))
        
    for x, y, z in zip(xcurve.keyframe_points, ycurve.keyframe_points, zcurve.keyframe_points):
        frame = [k.co[0] for k in (x, y, z) if k is not None][0]
        
        q = Euler(tuple(math.radians(x) for x in (x.co[1], y.co[1], z.co[1]))).to_quaternion()
        q_hl = Euler(tuple(math.radians(x) for x in (x.handle_left[1], y.handle_left[1], z.handle_left[1]))).to_quaternion()
        q_hr = Euler(tuple(math.radians(x) for x in (x.handle_right[1], y.handle_right[1], z.handle_right[1]))).to_quaternion()
        
        fw(indent+"\t%d: { %s, %s, %s, %s },\n" % (f2ms * int(frame), f2s(rnd(q.x)), f2s(rnd(q.y)), f2s(rnd(q.z)), f2s(rnd(q.w))))
        
        if interp == 'Bezier':
            fw(indent+"\t\tInTan { %s, %s, %s, %s },\n" % tuple(f2s(rnd(x)) for x in q_hl))
            fw(indent+"\t\tOutTan { %s, %s, %s, %s },\n" % tuple(f2s(rnd(x)) for x in q_hr))
            
    fw(indent+"}\n")
        
def write_anim_rot(anim, name, data_path, fw, global_seqs, bone_matrix, global_matrix):
    xcurve = anim[(data_path, 0)]
    ycurve = anim[(data_path, 1)]
    zcurve = anim[(data_path, 2)]
    wcurve = anim[(data_path, 3)]
    
    fw("\t%s %d {\n" % (name, len(xcurve.keyframe_points)))

    interp = get_interp(xcurve.keyframe_points[0].interpolation)
    
    if (interp == 'Bezier'):
        fw("\t\tHermite,\n") # Rotations use hermite interpolation
    else:
        fw("\t\t%s,\n" % interp) # Interpolation mode 
    
    if get_global_seq(xcurve) > 0:
        fw("\t\tGlobalSeqId %d,\n" % global_seqs.index(get_global_seq(xcurve)))
       
    for x, y, z, w in zip(xcurve.keyframe_points, ycurve.keyframe_points, zcurve.keyframe_points, wcurve.keyframe_points):
        # At some point i plan to use itertools.zip_longest and evaluate missing frames... this is for that
        frame = [k.co[0] for k in (x, y, z, w) if k is not None][0]
        
        # bone_matrix is currently unused. Still trying to figure out the correct conversion.
        rot = transform_rot(Quaternion((x.co[1], y.co[1], z.co[1], w.co[1])), bone_matrix, global_matrix)
        rot_hl = transform_rot(Quaternion((x.handle_left[1], y.handle_left[1], z.handle_left[1], w.handle_left[1])), bone_matrix, global_matrix)
        rot_hr = transform_rot(Quaternion((x.handle_right[1], y.handle_right[1], z.handle_right[1], w.handle_right[1])), bone_matrix, global_matrix)
        # rot = global_matrix.to_quaternion() * rot * global_matrix.inverted().to_quaternion() 
        # rot.normalize()
        fw("\t\t%d: { %s, %s, %s, %s },\n" % (f2ms * int(frame), f2s(rnd(rot.x)), f2s(rnd(rot.y)), f2s(rnd(rot.z)), f2s(rnd(rot.w))))
            
        if interp == 'Bezier':
            fw("\t\t\tInTan { %s, %s, %s, %s },\n" % tuple(f2s(rnd(x)) for x in rot_hl)) # Approximated by simply using the frame rotation values... from studying MDL files, these seem to be related. WIP. 
            fw("\t\t\tOutTan { %s, %s, %s, %s },\n" % tuple(f2s(rnd(x)) for x in rot_hr))

    fw("\t}\n")
    
def write_anim_vec(anim, name, data_path, fw, global_seqs, global_matrix = Matrix(), world_matrix = Matrix(), indent = "\t", order = (0, 1, 2)):
    
    xcurve = anim[(data_path, order[0])]
    ycurve = anim[(data_path, order[1])]
    zcurve = anim[(data_path, order[2])]

    fw(indent+"%s %d {\n" % (name, len(xcurve.keyframe_points)))
    
    interp = get_interp(xcurve.keyframe_points[0].interpolation)
    
    fw(indent+"\t%s,\n" % interp) # Interpolation mode 
    
    if get_global_seq(xcurve) > 0:
        fw(indent+"\tGlobalSeqId %d,\n" % global_seqs.index(get_global_seq(xcurve)))    
       
    for x, y, z in zip(xcurve.keyframe_points, ycurve.keyframe_points, zcurve.keyframe_points):
        # At some point i plan to use itertools.zip_longest and evaluate missing frames... this is for that
        frame = [k.co[0] for k in (x, y, z) if k is not None][0]
        
        handle_l = world_matrix.inverted() * Vector((x.handle_left[1], y.handle_left[1], z.handle_left[1])) 
        handle_r = world_matrix.inverted() * Vector((x.handle_right[1], y.handle_right[1] , z.handle_right[1])) 
        vec = global_matrix * world_matrix.inverted() * Vector((x.co[1], y.co[1], z.co[1]))
        
        fw(indent+"\t%d: { %s, %s, %s },\n" % (f2ms * int(frame), f2s(rnd(vec.x)), f2s(rnd(vec.y)), f2s(rnd(vec.z))))
            
        if interp == 'Bezier':
            fw(indent+"\t\tInTan { %s, %s, %s },\n" % tuple(f2s(rnd(x)) for x in handle_l))
            fw(indent+"\t\tOutTan { %s, %s, %s },\n" % tuple(f2s(rnd(x)) for x in handle_r))

    fw(indent+"}\n")
    
def save(operator, context, filepath="", mdl_version=800, global_matrix=None, use_selection=False, **kwargs):

    # -- Global constants -- #
    global f2ms
    global default_texture
    global decimal_places
    
    f2ms = 1000 / context.scene.render.fps # Frame to milisecond conversion
    default_texture = "Textures\white.blp"
    decimal_places = 5
    # ------------- #

    if global_matrix is None:
        global_matrix = Matrix()

    geosets = {}
    materials = set()
    objects = defaultdict(set)
    geoset_anims = []
    geoset_anim_map = {}
    const_color_mats = set()
    global_seqs = set()
    
    cameras = []
    
    filename = bpy.path.basename(context.blend_data.filepath)
    
    objs = []
    scene = context.scene
    
    current_frame = scene.frame_current
    scene.frame_current = 1
    
    if use_selection:
        objs = (obj for obj in scene.objects if obj.is_visible(scene) and obj.select)
    else:
        objs = (obj for obj in scene.objects if obj.is_visible(scene))
    
    for obj in objs:
        parent = get_parent(obj)
        
        billboarded = False
        billboard_lock = (False, False, False)
        if hasattr(obj, "mdl_billboard"):
            bb = obj.mdl_billboard
            billboarded = bb.billboarded
            billboard_lock = (bb.billboard_lock_z, bb.billboard_lock_y, bb.billboard_lock_x) # NOTE: Axes are listed backwards (same as with colors)
        
        # Animations
        visibility = get_curve(obj, ['hide_render', 'hide_view', '["visibility"]'])
        register_global_seq(visibility, global_seqs)
            
        anim_loc = get_curves(obj, 'location', (0, 1, 2))
        register_global_seq(anim_loc, global_seqs, [('location', 0)])
            
        anim_rot = get_curves(obj, 'rotation_quaternion', (0, 1, 2, 3))
        register_global_seq(anim_rot, global_seqs, [('rotation_quaternion', 0)])
            
        anim_scale = get_curves(obj, 'scale', (0, 1, 2))
        if anim_scale is not None:
            register_global_seq(anim_scale, global_seqs, anim_scale.keys()) # Special case to allow for particle systems to animate width/length individually
            
        is_animated = any((anim_loc, anim_rot, anim_scale))
        
        if get_curves(obj, 'rotation_euler', (0, 1, 2)) is not None:
            operator.report({'WARNING'}, "Euler rotations are not supported!")
        
        # Particle Systems
        if len(obj.particle_systems):
            settings = obj.particle_systems[0].settings
        
            if getattr(settings, "mdl_particle_sys"):
                psys = Object(obj.name)
                psys.emitter = settings.mdl_particle_sys
                psys.pivot = global_matrix * Vector(obj.location)
                
                psys.dimensions = obj.matrix_world.to_quaternion() * Vector(obj.scale)
                psys.dimensions = Vector(map(abs, global_matrix * psys.dimensions))
                psys.parent = parent
                psys.visibility = visibility
                
                psys.emission_rate_anim = None
                psys.speed_anim = None
                psys.life_span_anim = None
                psys.gravity_anim = None
                psys.variation_anim = None
                psys.latitude_anim = None
                psys.longitude_anim = None
                psys.ribbon_color_anim = None
                psys.alpha_anim = None
                
                psys.scale_anim = get_curves(obj, 'scale', (0, 1))
                
                if settings.animation_data is not None:
                    # Animated properties
                    fcurves = settings.animation_data.action.fcurves
                    
                    curve = fcurves.find("mdl_particle_sys.emission_rate")
                    psys.emission_rate_anim = curve
                    register_global_seq(psys.emission_rate_anim, global_seqs)
                        
                    curve = fcurves.find("mdl_particle_sys.speed")
                    psys.speed_anim = curve
                    register_global_seq(psys.speed_anim, global_seqs)
                        
                    curve = fcurves.find("mdl_particle_sys.life_span")
                    psys.life_span_anim = curve
                    register_global_seq(psys.life_span_anim, global_seqs)
                        
                    curve = fcurves.find("mdl_particle_sys.gravity")
                    psys.gravity_anim = curve
                    register_global_seq(psys.gravity_anim, global_seqs)
                        
                    curve = fcurves.find("mdl_particle_sys.variation")
                    psys.variation_anim = curve
                    register_global_seq(psys.variation_anim, global_seqs)
                        
                    curve = fcurves.find("mdl_particle_sys.latitude")
                    psys.latitude_anim = curve
                    register_global_seq(psys.latitude_anim, global_seqs)
                        
                    curve = fcurves.find("mdl_particle_sys.longitude")
                    psys.longitude_anim = curve
                    register_global_seq(psys.longitude_anim, global_seqs)
                        
                    curve = fcurves.find("mdl_particle_sys.alpha")
                    psys.alpha_anim = curve
                    register_global_seq(psys.alpha_anim, global_seqs)
                        
                    curves = get_curves(settings, "mdl_particle_sys.ribbon_color", (0, 1, 2))
                    psys.ribbon_color_anim = curves
                    register_global_seq(psys.ribbon_color_anim, global_seqs, [0])
                
                if psys.emitter.emitter_type == 'ParticleEmitter':
                    objects['particle'].add(psys)
                elif psys.emitter.emitter_type == 'ParticleEmitter2':
                    objects['particle2'].add(psys)
                else:
                    # Add the material to the list, in case it's unused
                    mat = psys.emitter.ribbon_material
                    materials.add(mat)
                    
                    objects['ribbon'].add(psys)
            
        # Meshes
        elif obj.type == 'EMPTY' and obj.name.startswith('Collision'):
            collider = Object(obj.name)
            collider.parent = parent
            collider.pivot = global_matrix * Vector(obj.location)
            
            if 'Box' in obj.name:
                collider.type = 'Box'
                corners = []
                for corner in ((0.5, 0.5, -0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (-0.5, 0.5, 0.5)):
                    mat = global_matrix * obj.matrix_world
                    corners.append(mat.to_quaternion() * Vector(abs(x * obj.empty_draw_size * global_matrix.median_scale) * y for x, y in zip(obj.scale, corner)))

                vmin, vmax = calc_extents(corners)
                
                collider.verts = [vmin, vmax] # TODO: World space or relative to pivot??
                objects['collisionshape'].add(collider)
            elif 'Sphere' in obj.name:
                collider.type = 'Sphere'
                collider.verts = [global_matrix * Vector(obj.location)]
                collider.radius = global_matrix.median_scale * max(abs(x * obj.empty_draw_size) for x in obj.scale)
                objects['collisionshape'].add(collider)

        elif obj.type == 'MESH':
            mesh = prepare_mesh(obj, context, global_matrix * obj.matrix_world)
            # mesh.transform(global_matrix * obj.matrix_world)
            
            # Geoset Animation
            vertexcolor_anim = get_curves(obj, 'color', (0, 1, 2))
            vertexcolor = obj.color if any(i != 1 for i in obj.color) else None
            geoset_anim = None
            geoset_anim_hash = 0
            if any((vertexcolor, vertexcolor_anim, visibility)):
                geoset_anim = GeosetAnim(vertexcolor, vertexcolor_anim, visibility)
                geoset_anim_hash = hash(geoset_anim) # The hash is a bit complex, so we precompute it
            mesh_geosets = set()
            
            armature = None
            for m in obj.modifiers:
                if m.type == 'ARMATURE':
                    armature = m
            
            bone_names = set()
            if armature is not None:
                bone_names = set(b.name for b in armature.object.data.bones)
                
            bone = None
            if (armature is None and parent is None) or is_animated:
                bone = Object(obj.name) # Object is animated or parent is missing - create a bone for it!
                if not obj.name.startswith("Bone_"):
                    bone.name = "Bone_"+obj.name
                
                bone.parent = parent # Remember to make it the parent - parent is added to matrices further down
                bone.pivot = global_matrix * Vector(obj.location)
                bone.anim_loc = anim_loc
                bone.anim_rot = anim_rot
                bone.anim_scale = anim_scale
                bone.matrix = obj.matrix_world
                bone.billboarded = billboarded
                bone.billboard_lock = billboard_lock
                if geoset_anim is not None:
                    geoset_anim_map[bone] = geoset_anim
                objects['bone'].add(bone)
                parent = bone.name
            
            for f in mesh.tessfaces:
                p = mesh.polygons[f.index]
                # Textures and materials
                mat_name = "default"
                if obj.material_slots and len(obj.material_slots):
                    mat = obj.material_slots[p.material_index].material
                    if mat is not None:
                        mat_name = mat.name
                        materials.add(mat)
                            
                geoset = None
                if (mat_name, geoset_anim_hash) in geosets.keys():
                    geoset = geosets[(mat_name, geoset_anim_hash)]
                else:
                    geoset = Geoset()
                    geoset.mat_name = mat_name
                    if geoset_anim is not None:
                        geoset.geoset_anim = geoset_anim
                        geoset_anim.geoset = geoset
                    geosets[(mat_name, geoset_anim_hash)] = geoset
                  
                  
                # Vertices, faces, and matrices  
                vertexmap = {}
                for vert, loop in zip(p.vertices, p.loop_indices):
                    co = mesh.vertices[vert].co
                    coord = (rnd(co.x), rnd(co.y), rnd(co.z))
                    n = mesh.vertices[vert].normal if f.use_smooth else f.normal
                    norm = (rnd(n.x), rnd(n.y), rnd(n.z))
                    uv = mesh.uv_layers.active.data[loop].uv if len(mesh.uv_layers) else Vector((0.0, 0.0))
                    uv[1] = 1 - uv[1] # For some reason, uv Y coordinates appear flipped. This should fix that. 
                    tvert = (rnd(uv.x), rnd(uv.y))
                    groups = None
                    matrix = 0
                    
                    if armature is not None:
                        vgroups = sorted(mesh.vertices[vert].groups[:], key=lambda x:x.weight, reverse=True) # Sort bones by descending weight
                        if len(vgroups):
                            groups = list(obj.vertex_groups[vg.group].name for vg in vgroups if obj.vertex_groups[vg.group].name in bone_names)[:3]
                    elif parent is not None:
                        groups = [parent]
                                
                    if groups is not None:
                        if groups not in geoset.matrices:
                            geoset.matrices.append(groups)
                        matrix = geoset.matrices.index(groups)

                    
                    vertex = (coord, norm, tvert, matrix)
                    if vertex not in geoset.vertices:
                        geoset.vertices.append(vertex)
                        
                    vertexmap[vert] = geoset.vertices.index(vertex)
                        
                # Triangles, normals, vertices, and UVs
                geoset.triangles.append((vertexmap[p.vertices[0]], vertexmap[p.vertices[1]], vertexmap[p.vertices[2]]))
                
                mesh_geosets.add(geoset)
            
            # 
            for geoset in mesh_geosets:
                geoset.objects.append(obj)
                geoset.min_extent, geoset.max_extent = calc_extents([x[0] for x in geoset.vertices])
                if not len(geoset.matrices) and parent is not None:
                    geoset.matrices.append([parent])

                if geoset.geoset_anim is not None:
                    register_global_seq(geoset.geoset_anim.alpha_anim, global_seqs)
                    register_global_seq(geoset.geoset_anim.color_anim, global_seqs, [('color', 0)])
                    if any((geoset.geoset_anim.color, geoset.geoset_anim.color_anim)):
                        const_color_mats.add(geoset.mat_name)
                    for bone in itertools.chain.from_iterable(geoset.matrices):
                        geoset_anim_map[bone] = geoset.geoset_anim
                        
                    
                    
            
            bpy.data.meshes.remove(mesh)
        elif obj.type == 'EMPTY':
            if obj.name.startswith("SND") or obj.name.startswith("UBR") or obj.name.startswith("FPT") or obj.name.startswith("SPL"):
                eventobj = Object(obj.name)
                eventobj.pivot = global_matrix * Vector(obj.location)
                eventobj.track = get_curve(obj, ['["eventtrack"]', '["EventTrack"]', '["event_track"]'])  
                register_global_seq(eventobj.track, global_seqs)
                objects['eventobject'].add(eventobj)
                # events.append({"object" : obj, "eventtrack" : eventtrack})
            elif obj.name.endswith(" Ref"):
                att = Object(obj.name)
                att.pivot = global_matrix * Vector(obj.location)
                att.parent = parent
                att.visibility = visibility
                att.billboarded = billboarded
                att.billboard_lock = billboard_lock
                objects['attachment'].add(att)
            elif obj.name.startswith("Bone_"):
                bone = Object(obj.name)
                if parent is not None:
                    bone.parent = parent
                bone.pivot = global_matrix * Vector(obj.location)
                bone.anim_loc = anim_loc
                bone.anim_rot = anim_rot
                bone.anim_scale = anim_scale
                bone.matrix = obj.matrix_world
                bone.billboarded = billboarded
                bone.billboard_lock = billboard_lock
                objects['bone'].add(bone)
        elif obj.type == 'ARMATURE':
            for b in obj.pose.bones:
                bone = Object(b.name)
                if b.parent is not None:
                    bone.parent = b.parent.name
                bone.pivot = obj.matrix_world * Vector(b.bone.head_local) # Armature space to world space
                bone.pivot = global_matrix * Vector(bone.pivot) # Axis conversion
                datapath = 'pose.bones[\"'+b.name+'\"].%s'
                bone.anim_loc = get_curves(obj, datapath % 'location', (0, 1, 2))
                register_global_seq(bone.anim_loc, global_seqs, [('location', 0)])

                bone.anim_rot = get_curves(obj, datapath % 'rotation_quaternion', (0, 1, 2, 3))
                register_global_seq(bone.anim_rot, global_seqs, [('rotation_quaternion', 0)])

                bone.anim_scale = get_curves(obj, datapath % 'scale', (0, 1, 2))
                register_global_seq(bone.anim_scale, global_seqs, [('scale', 0)])
                
                bone.matrix = b.bone.matrix_local
                objects['bone'].add(bone)
                # First add to a temporary list and later cross-check against the bones of each geoset? Pick only animated bones?    
        elif obj.type == 'LAMP':
            light = Object(obj.name)
            light.object = obj
            light.pivot = global_matrix * Vector(obj.location)
            light.billboarded = billboarded
            light.billboard_lock = billboard_lock
            
            if hasattr(obj.data, "mdl_light"):
                light_data = obj.data.mdl_light
                light.type = light_data.light_type
            
                light.intensity = light_data.intensity
                light.intensity_anim = get_curve(obj.data, ['mdl_light.intensity'])
                register_global_seq(light.intensity_anim, global_seqs)
                
                light.atten_start = light_data.atten_start
                light.atten_start_anim = get_curve(obj.data, ['mdl_light.atten_start'])
                register_global_seq(light.atten_start_anim, global_seqs)
                    
                light.atten_end = light_data.atten_end
                light.atten_end_anim = get_curve(obj.data, ['mdl_light.atten_end'])
                register_global_seq(light.atten_end_anim, global_seqs)
                
                light.color = light_data.color
                light.color_anim = get_curve(obj.data, ['mdl_light.color'])
                register_global_seq(light.color_anim, global_seqs, [0])
                    
                light.amb_color = light_data.amb_color
                light.amb_color_anim = get_curve(obj.data, ['mdl_light.amb_color'])
                register_global_seq(light.amb_color_anim, global_seqs, [0])
                    
                light.amb_intensity = light_data.amb_intensity
                light.amb_intensity_anim = get_curve(obj.data, ['obj.mdl_light.amb_intensity'])
                register_global_seq(light.amb_intensity_anim, global_seqs)
                    
            light.visibility = visibility
            objects['light'].add(light)
        elif obj.type == 'CAMERA':
            cameras.append(obj)
    
    geosets = list(geosets.values())
    mdl_materials = parse_materials(materials, const_color_mats, global_seqs)
    # Add default material if no other materials present
    if any((x for x in geosets if x.mat_name == "default")):
        default_mat = Material("default")
        default_mat.layers.append(MaterialLayer())
        mdl_materials.append(default_mat)
        operator.report({'WARNING'}, "Some geosets have no materials!")
    
    mdl_materials = sorted(mdl_materials, key=lambda x: x.priority_plane)
    material_names = [mat.name for mat in mdl_materials]

    mdl_layers = list(itertools.chain.from_iterable([material.layers for material in mdl_materials]))
    textures = list(set((layer.texture for layer in mdl_layers))) # Convert to set and back to list for unique entries

    
    # Degrade bones to helpers if they have no attached geosets
    for bone in objects['bone']:
        if not any([g for g in geosets if bone.name in itertools.chain.from_iterable(g.matrices)]):
            objects['helper'].add(bone)
            
    objects['bone'] -= objects['helper']
    # We also need the textures used by emitters
    for psys in list(objects['particle']) + list(objects['particle2']) + list(objects['ribbon']):
        if psys.emitter.texture_path not in textures:
            textures.append(psys.emitter.texture_path)
            
    tvertex_anims = list(set((layer.texture_anim for layer in mdl_layers if layer.texture_anim is not None)))
    
    sequences = get_sequences(context.scene)
    if len(sequences) == 0:
        sequences.append(("Stand", 0, 3333)) # Default anim

    vertices_all = []
    objects_all = []
    object_indices = {}
    geoset_indices = {}
    
    index = 0
    for tag in ('bone', 'light', 'helper', 'attachment', 'particle', 'particle2', 'ribbon', 'eventobject', 'collisionshape'):
        for object in objects[tag]:
            object_indices[object.name] = index
            objects_all.append(object)
            vertices_all.append(object.pivot)
            if tag == 'collisionshape':
                for vert in object.verts:
                    vertices_all.append(vert)
            index = index+1
            
    for geoset in geosets:
        for vertex in geoset.vertices:
            vertices_all.append(vertex[0])
     
    # Account for particle systems when calculating bounds 
    for psys in list(objects['particle']) + list(objects['particle2']) + list(objects['ribbon']):
        vertices_all.append(tuple(x + y/2 for x, y in zip(psys.pivot, psys.dimensions)))
        vertices_all.append(tuple(x - y/2 for x, y in zip(psys.pivot, psys.dimensions)))
    
    geoset_anims = list(set(g.geoset_anim for g in geosets if g.geoset_anim is not None))
    
    global_extents_min, global_extents_max = calc_extents(vertices_all) if len(vertices_all) else ((0, 0, 0), (0, 0, 0))
    
    scene.frame_current = current_frame
    
    with open(filepath, 'w') as output:
        fw = output.write
        fw("Version {\n\tFormatVersion %d,\n}\n" % mdl_version)
        # HEADER
        fw("Model \"%s\" {\n" % filename.replace(".blend",""))
        if len(geosets):
            fw("\tNumGeosets %d,\n" % len(geosets))
        if len(objects['bone']):
            fw("\tNumBones %d,\n" % len(objects['bone']))
        if len(objects['attachment']):
            fw("\tNumAttachments %d,\n" % len(objects['attachment']))
        if len(objects['eventobject']):
            fw("\tNumEvents %d,\n" % len(objects['eventobject']))
        if len(geoset_anims):
            fw("\tNumGeosetAnims %d,\n" % len(geoset_anims))
        if len(objects['light']):
            fw("\tNumLights %d,\n" % len(objects['light']))
        if len(objects['helper']):
            fw("\tNumHelpers %d,\n" % len(objects['helper']))
        fw("\tBlendTime %d,\n" % 150)
        fw("\tMinimumExtent {%s, %s, %s},\n" % tuple(map(f2s, global_extents_min)))
        fw("\tMaximumExtent {%s, %s, %s},\n" % tuple(map(f2s, global_extents_max)))
        fw("\tBoundsRadius %s,\n" % f2s(calc_bounds_radius(global_extents_min, global_extents_max)))
        fw("}\n")
        
        # SEQUENCES
        fw("Sequences %d {\n" % len(sequences))
        for (name, start, end) in sequences:
            fw("\tAnim \"%s\" {\n" % name)
            fw("\t\tInterval {%d, %d},\n" % (start, end))
            fw("\t}\n")
        fw("}\n")
        
        # GLOBAL SEQUENCES
        global_seqs = sorted(global_seqs)
        if len(global_seqs):
            fw("GlobalSequences %d {\n" % len(global_seqs))
            for sequence in global_seqs:
                fw("\tDuration %d,\n" % sequence)
            fw("}\n")
        
        # TEXTURES
        if len(textures):
            fw("Textures %d {\n" % len(textures))
            for texture in textures:
                fw("\tBitmap {\n")
                
                if texture.startswith("ReplaceableId"):
                    fw("\t\tImage \"\",\n")
                    fw("\t\t%s,\n" % texture)
                else:
                    fw("\t\tImage \"%s\",\n" % texture)

                fw("\t\tWrapHeight,\n")
                fw("\t\tWrapWidth,\n")
                fw("\t}\n")
            fw("}\n")
        
        # MATERIALS
        if len(materials):
            fw("Materials %d {\n" % len(mdl_materials))
            for material in mdl_materials:
                fw("\tMaterial {\n")
                
                if material.use_const_color is True:
                    fw("\t\tConstantColor,\n")
                    
                # SortPrimsFarZ,
                # FullResolution,
                
                if material.priority_plane != 0:
                    fw("\t\tPriorityPlane %d,\n" % material.priority_plane)
                
                for layer in material.layers:
                    fw("\t\tLayer {\n")
                    fw("\t\t\tFilterMode %s,\n" % layer.filter_mode)
                    if layer.unshaded is True:
                        fw("\t\t\tUnshaded,\n")
                        
                    if layer.two_sided is True:
                        fw("\t\t\tTwoSided,\n")
                    
                    if layer.unfogged is True:
                        fw("\t\t\tUnfogged,\n")
                        
                    if layer.no_depth_test:
                        fw("\t\t\tNoDepthTest,\n")
                        
                    if layer.no_depth_set:
                        fw("\t\t\tNoDepthSet,\n")
                        
                    if layer.texture is not None:
                        fw("\t\t\tstatic TextureID %d,\n" % textures.index(layer.texture))    
                    else:
                        fw("\t\t\tstatic TextureID 0,\n")  
                        
                    if layer.texture_anim is not None:
                        fw("\t\t\tTVertexAnimId %d,\n" % tvertex_anims.index(layer.texture_anim))
                    if layer.alpha_anim is not None:
                        write_anim(layer.alpha_anim, "Alpha", fw, global_seqs, "\t\t")
                    else:
                        fw("\t\t\tstatic Alpha %s,\n" % f2s(layer.alpha_value))
                        
                    fw("\t\t}\n")
                fw("\t}\n")
            fw("}\n")
        
        # TEXTURE ANIMATIONS
        if len(tvertex_anims):
            fw("TextureAnims %d {\n" % len(tvertex_anims))
            for uv_anim in tvertex_anims:
                fw("\tTVertexAnim {\n")
                if uv_anim.translation is not None:
                    write_anim_vec(uv_anim.translation, "Translation", 'translation', fw, global_seqs, Matrix(), Matrix(), "\t\t")
                if uv_anim.rotation is not None:
                    write_anim_euler(uv_anim.rotation, "Rotation", 'rotation', fw, global_seqs, "\t\t")
                if uv_anim.scale is not None:
                    write_anim_vec(uv_anim.scale, "Scaling", 'scale', fw, global_seqs, Matrix(), Matrix(), "\t\t")
                fw("\t}\n")
            fw("}\n")
        
        # GEOSETS
        if len(geosets):
            for geoset in geosets:
                fw("Geoset {\n")
                # Vertices
                fw("\tVertices %d {\n" % len(geoset.vertices))
                for vertex in geoset.vertices:
                    fw("\t\t{%s, %s, %s},\n" % tuple(map(f2s, vertex[0])))
                fw("\t}\n")
                # Normals
                fw("\tNormals %d {\n" % len(geoset.vertices))
                for normal in geoset.vertices:
                    fw("\t\t{%s, %s, %s},\n" % tuple(map(f2s, normal[1])))
                fw("\t}\n")
                
                # TVertices
                fw("\tTVertices %d {\n" % len(geoset.vertices))
                for tvertex in geoset.vertices:
                    fw("\t\t{%s, %s},\n" % tuple(map(f2s, tvertex[2])))
                fw("\t}\n")
                
                # VertexGroups
                fw("\tVertexGroup {\n")
                for vertgroup in geoset.vertices:
                    fw("\t\t%d,\n" % vertgroup[3])
                fw("\t}\n")
                
                # Faces
                fw("\tFaces %d %d {\n" % (len(geoset.triangles), len(geoset.triangles) * 3))
                fw("\t\tTriangles {\n")
                for triangle in geoset.triangles:
                    fw("\t\t\t{%d, %d, %d},\n" % triangle[:])
                    
                fw("\t\t}\n")
                fw("\t}\n")
                
                fw("\tGroups %d %d {\n" % (len(geoset.matrices), sum(len(mtrx) for mtrx in geoset.matrices)))         
                for matrix in geoset.matrices:
                    fw("\t\tMatrices {%s},\n" % ','.join(str(object_indices[g]) for g in matrix))
                fw("\t}\n")
                
                fw("\tMinimumExtent {%s, %s, %s},\n" % tuple(map(f2s, geoset.min_extent)))
                fw("\tMaximumExtent {%s, %s, %s},\n" % tuple(map(f2s, geoset.max_extent)))
                fw("\tBoundsRadius %s,\n" % f2s(calc_bounds_radius(geoset.min_extent, geoset.max_extent)))
                fw("\tMaterialID %d,\n" % material_names.index(geoset.mat_name))

                fw("}\n")

            
        # GEOSET ANIMS
        if len(geoset_anims):
            for anim in geoset_anims:
                fw("GeosetAnim {\n")
                alpha = anim.alpha_anim
                vertexcolor = anim.color
                vertexcolor_anim = anim.color_anim
                if alpha is not None:
                    write_anim(alpha, "Alpha", fw, global_seqs, "\t", True)
                else: 
                    fw("\tstatic Alpha 1.0,\n")
                    
                if vertexcolor_anim is not None:
                    write_anim_vec(vertexcolor_anim, 'Color', 'color', fw, global_seqs, Matrix(), Matrix(), "\t", (2, 1, 0))
                elif vertexcolor is not None:
                    fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(vertexcolor[:3]))))
                    
                fw("\tGeosetId %d,\n" % geosets.index(anim.geoset))

                fw("}\n")
            
        # BONES
        for bone in objects['bone']:
            name = bone.name.replace('.', '_')
            if not name.lower().startswith("bone"):
                name = "Bone_"+name
                
            fw("Bone \"%s\" {\n" % name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[bone.name])
            if bone.parent is not None:
                fw("\tParent %d,\n" % object_indices[bone.parent])
            
            if hasattr(bone, "billboarded"):
                write_billboard(fw, bone.billboarded, bone.billboard_lock)
            
            children = [g for g in geosets if bone.name in itertools.chain.from_iterable(g.matrices)]
            if len(children) == 1:
                fw("\tGeosetId %d,\n" % geosets.index(children[0]))
            else:
                fw("\tGeosetId -1,\n")
                
            if bone.name in geoset_anim_map.keys():
                fw("\tGeosetAnimId %d,\n" % geoset_anims.index(geoset_anim_map[bone.name]))
            else:
                fw("\tGeosetAnimId None,\n")
                
            if bone.anim_loc is not None:
                write_anim_vec(bone.anim_loc, 'Translation', 'location', fw, global_seqs, global_matrix, bone.matrix)
                
            if bone.anim_rot is not None:
                write_anim_rot(bone.anim_rot, 'Rotation', 'rotation_quaternion', fw, global_seqs, bone.matrix, global_matrix)
                
            if bone.anim_scale is not None:
                write_anim_vec(bone.anim_scale, 'Scaling', 'scale', fw, global_seqs, Matrix(), Matrix())
                
            # Visibility
            fw("}\n")
            
        # LIGHTS
        for light in objects['light']:
            l = light.object
            fw("Light \"%s\" {\n" % light.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[light.name])
                
            if light.parent is not None:
                fw("\tParent %d,\n" % object_indices[light.parent])
               
            write_billboard(fw, light.billboarded, light.billboard_lock)
            
            fw("\t%s,\n" % light.type)
            
            if light.atten_start_anim is not None:
                write_anim(light.atten_start_anim, "AttenuationStart", fw, global_seqs, "\t")
            else:
                fw("\tstatic AttenuationStart %s,\n" % f2s(light.atten_start))
                
            if light.atten_end_anim is not None:
                write_anim(light.atten_end_anim, "AttenuationEnd", fw, global_seqs, "\t")
            else:
                fw("\tstatic AttenuationEnd %s,\n" % f2s(light.atten_end)) #TODO: Add animation support
               
            if light.color_anim is not None:
                write_anim_vec(light.color_anim, "Color", 'color', fw, global_seqs, Matrix(), Matrix())
            else:
                fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(light.color[:3]))))
               
            if light.intensity_anim is not None:
                write_anim(light.intensity_anim, "Intensity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Intensity %s,\n" % f2s(light.intensity))
               
            if light.amb_color_anim is not None:
                write_anim_vec(light.amb_color_anim, "Color", 'color', fw, global_seqs, Matrix(), Matrix())
            else:
                fw("\tstatic AmbColor {%s, %s, %s},\n" % tuple(map(f2s, reversed(light.amb_color[:3]))))
                
            if light.amb_intensity_anim is not None:
                write_anim(light.amb_intensity_anim, "AmbIntensity", fw, global_seqs, "\t")
            else:
                fw("\tstatic AmbIntensity %s,\n" % f2s(light.amb_intensity))
                
            if light.visibility is not None:
                write_anim(light.visibility, "Visibility", fw, global_seqs, "\t", True)
            fw("}\n")
                
                
        # HELPERS
        for helper in objects['helper']:
            fw("Helper \"%s\" {\n" % helper.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[helper.name])
                
            if helper.parent is not None:
                fw("\tParent %d,\n" % object_indices[helper.parent])
            
            if hasattr(helper, "billboarded"):
                write_billboard(fw, helper.billboarded, helper.billboard_lock)
            
            if helper.anim_loc is not None:
                write_anim_vec(helper.anim_loc, 'Translation', 'location', fw, global_seqs, global_matrix, helper.matrix)
                
            if helper.anim_rot is not None:
                write_anim_rot(helper.anim_rot, 'Rotation', 'rotation_quaternion', fw, global_seqs, helper.matrix, global_matrix)
                
            if helper.anim_scale is not None:
                write_anim_vec(helper.anim_scale, 'Scaling', 'scale', fw, global_seqs, Matrix(), Matrix())
            
            fw("}\n")

            
        # ATTACHMENT POINTS   
        if len(objects['attachment']):
            for i, attachment in enumerate(objects['attachment']):
                fw("Attachment \"%s\" {\n" % attachment.name)
                
                if len(object_indices) > 1:
                    fw("\tObjectId %d,\n" % object_indices[attachment.name])
                    
                if attachment.parent is not None:
                    fw("\tParent %d,\n" % object_indices[attachment.parent])
                    
                write_billboard(fw, attachment.billboarded, attachment.billboard_lock)
                
                fw("\tAttachmentID %d,\n" % i)
                
                visibility = attachment.visibility
                if visibility is not None:
                    write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
                fw("}\n")
            
        # PIVOT POINTS
        if len(objects_all):
            fw("PivotPoints %d {\n" % len(objects_all))
            for object in objects_all:
                fw("\t{%s, %s, %s},\n" % tuple(map(f2s, object.pivot)))
            fw("}\n")
            
        # MODEL EMITTERS
        for psys in objects['particle']:
            emitter = psys.emitter
            fw("ParticleEmitter \"%s\" {\n" % psys.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[psys.name])
            if psys.parent is not None:
                fw("\tParent %d,\n" % object_indices[psys.parent])
                
            fw("\tEmitterUsesMDL,\n")
            
            if psys.emission_rate_anim is not None:
                write_anim(psys.emission_rate_anim, "EmissionRate", fw, global_seqs, "\t")
            else:
                fw("\tstatic EmissionRate %s,\n" % f2s(rnd(emitter.emission_rate)))
            
            if psys.gravity_anim is not None:
                write_anim(psys.gravity_anim, "Gravity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Gravity %s,\n" % f2s(rnd(emitter.gravity)))
                
            if psys.longitude_anim is not None:
                write_anim(psys.longitude_anim, "Longitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Longitude %s,\n" % f2s(rnd(emitter.latitude)))
            
            if psys.latitude_anim is not None:
                write_anim(psys.latitude_anim, "Latitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Latitude %s,\n" % f2s(rnd(emitter.latitude)))
                
            visibility = psys.visibility
            if visibility is not None:
                write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
            fw("\tParticle {\n")
            
            if psys.life_span_anim is not None:
                write_anim(psys.life_span_anim, "LifeSpan", fw, global_seqs, "\t\t")
            else:
                fw("\t\tLifeSpan %s,\n" % f2s(rnd(emitter.life_span)))
              
            if psys.speed_anim is not None:
                write_anim(psys.speed_anim, "InitVelocity", fw, global_seqs, "\t\t")
            else:
                fw("\t\tstatic InitVelocity %s,\n" % f2s(rnd(emitter.speed)))

            fw("\t\tPath \"%s\",\n" % emitter.model_path)
            fw("\t}\n")
            fw("}\n")
         
        # PARTICLE EMITTERS
        for psys in objects['particle2']:
            emitter = psys.emitter
            fw("ParticleEmitter2 \"%s\" {\n" % psys.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[psys.name])
            if psys.parent is not None:
                fw("\tParent %d,\n" % object_indices[psys.parent])
                
            if emitter.sort_far_z:
                fw("\tSortPrimsFarZ,\n")
                
            if emitter.unshaded:
                fw("\tUnshaded,\n")
                
            if emitter.line_emitter:
                fw("\tLineEmitter,\n")
            
            if emitter.unfogged:
                fw("\tUnfogged,\n")
                
            if emitter.model_space:
                fw("\tModelSpace,\n")
                
            if emitter.xy_quad:
                fw("\tXYQuad,\n")
                
            if psys.speed_anim is not None:
                write_anim(psys.speed_anim, "Speed", fw, global_seqs, "\t")
            else:
                fw("\tstatic Speed %s,\n" % f2s(rnd(emitter.speed)))
                
            if psys.variation_anim is not None:
                write_anim(psys.variation_anim, "Variation", fw, global_seqs, "\t")
            else:
                fw("\tstatic Variation %s,\n" % f2s(rnd(emitter.variation)))
                
            if psys.latitude_anim is not None:
                write_anim(psys.latitude_anim, "Latitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Latitude %s,\n" % f2s(rnd(emitter.latitude)))
                
            if psys.gravity_anim is not None:
                write_anim(psys.gravity_anim, "Gravity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Gravity %s,\n" % f2s(rnd(emitter.gravity)))
                
            visibility = psys.visibility
            if visibility is not None:
                write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
                
            if psys.life_span_anim is not None:
                write_anim(psys.life_span_anim, "LifeSpan", fw, global_seqs, "\t")
            else:
                fw("\tLifeSpan %s,\n" % f2s(rnd(emitter.life_span)))
                
            if psys.emission_rate_anim is not None:
                write_anim(psys.emission_rate_anim, "EmissionRate", fw, global_seqs, "\t")
            else:
                fw("\tstatic EmissionRate %s,\n" % f2s(rnd(emitter.emission_rate)))
                
            if psys.scale_anim is not None and ('scale', 1) in psys.scale_anim.keys():
                write_anim(psys.scale_anim[('scale', 1)], "Width", fw, global_seqs, "\t", scale=psys.dimensions[1])
            else:
                fw("\tstatic Width %s,\n" % f2s(rnd(psys.dimensions[1])))
               
            if psys.scale_anim is not None and ('scale', 0) in psys.scale_anim.keys():
                write_anim(psys.scale_anim[('scale', 0)], "Length", fw, global_seqs, "\t", scale=psys.dimensions[0])
            else:
                fw("\tstatic Length %s,\n" % f2s(rnd(psys.dimensions[0])))
                
            fw("\t%s,\n" % emitter.filter_mode)
            fw("\tRows %d,\n" % emitter.rows)
            fw("\tColumns %d,\n" % emitter.cols)
            if emitter.head and emitter.tail:
                fw("\tBoth,\n")
            elif emitter.tail:
                fw("\tTail,\n")
            else:
                fw("\tHead,\n")
                
            fw("\tTailLength %s,\n" % f2s(rnd(emitter.tail_length)))
            fw("\tTime %s,\n" % f2s(rnd(emitter.time)))
            fw("\tSegmentColor {\n")
            fw("\t\tColor {%s, %s, %s},\n" % tuple(map(f2s, reversed(emitter.start_color))))
            fw("\t\tColor {%s, %s, %s},\n" % tuple(map(f2s, reversed(emitter.mid_color))))
            fw("\t\tColor {%s, %s, %s},\n" % tuple(map(f2s, reversed(emitter.end_color))))
            fw("\t},\n")
            alpha = (emitter.start_alpha, emitter.mid_alpha, emitter.end_alpha)
            fw("\tAlpha {%s, %s, %s},\n" % tuple(map(f2s, alpha)))
            particle_scales = (emitter.start_scale, emitter.mid_scale, emitter.end_scale)
            fw("\tParticleScaling {%s, %s, %s},\n" % tuple(map(f2s, particle_scales)))
            fw("\tLifeSpanUVAnim {%d, %d, %d},\n" % (emitter.head_life_start, emitter.head_life_end, emitter.head_life_repeat))
            fw("\tDecayUVAnim {%d, %d, %d},\n" % (emitter.head_decay_start, emitter.head_decay_end, emitter.head_decay_repeat))
            fw("\tTailUVAnim {%d, %d, %d},\n" % (emitter.tail_life_start, emitter.tail_life_end, emitter.tail_life_repeat))
            fw("\tTailDecayUVAnim {%d, %d, %d},\n" % (emitter.tail_decay_start, emitter.tail_decay_end, emitter.tail_decay_repeat))
            fw("\tTextureID %d,\n" % textures.index(emitter.texture_path))
            if emitter.priority_plane != 0:
                fw("\tPriorityPlane %d,\n" % emitter.priority_plane)
            fw("}\n")
           
        # RIBBON EMITTERS
        for psys in objects['ribbon']:
            emitter = psys.emitter
            fw("RibbonEmitter \"%s\" {\n" % psys.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[psys.name])
            if psys.parent is not None:
                fw("\tParent %d,\n" % object_indices[psys.parent])
                
            fw("\tstatic HeightAbove %s,\n" % f2s(rnd(psys.dimensions[0]/2)))
            fw("\tstatic HeightBelow %s,\n" % f2s(rnd(psys.dimensions[0]/2)))
            
            if psys.alpha_anim is not None:
                write_anim(psys.alpha_anim, "Width", fw, global_seqs, "\t")
            else:
                fw("\tstatic Alpha %s,\n" % emitter.alpha)
            
            if psys.ribbon_color_anim is not None:
                write_anim_vec(psys.ribbon_color_anim, 'Color', 'ribbon_color', fw, global_seqs, Matrix(), Matrix(), "\t", (2, 1, 0))
            else:
                fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(emitter.ribbon_color))))
                
            fw("\tstatic TextureSlot %d,\n" % textures.index(emitter.texture_path))
            visibility = psys.visibility
            if visibility is not None:
                write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
            fw("\tEmissionRate %d,\n" % emitter.emission_rate)
            fw("\tLifeSpan %s,\n" % f2s(rnd(emitter.life_span)))
            fw("\tGravity %s,\n" % f2s(rnd(emitter.gravity)))
            fw("\tRows %d,\n" % emitter.rows)
            fw("\tColumns %d,\n" % emitter.cols)
            for material in mdl_materials:
                if material.name == emitter.ribbon_material.name:
                    fw("\tMaterialID %d,\n" % mdl_materials.index(material))
                    break
            fw("}\n")
            
        # CAMERAS    
        for camera in cameras:
            fw("Camera \"%s\" {\n" % camera.name)
            position = global_matrix * Vector(camera.location)
            fw("\tPosition {%s, %s, %s},\n" % tuple(map(f2s, position)))
            fw("\tFieldOfView %f,\n" % camera.data.angle)
            fw("\tFarClip %f,\n" % (camera.data.clip_end*10))
            fw("\tNearClip %f,\n" % (camera.data.clip_start*10))
            matrix = global_matrix * camera.matrix_world
            target = position + matrix.to_quaternion() * Vector((0.0, 0.0, -1.0)) # Target is just a point in front of the camera
            fw("\tTarget {\n\t\tPosition {%s, %s, %s},\n\t}\n" % tuple(map(f2s, target)))
            fw("}\n")
         
        # EVENT OBJECTS
        for event in objects['eventobject']:
            fw("EventObject \"%s\" {\n" % event.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[event.name])
            if event.parent is not None:
                fw("\tParent %d,\n" % object_indices[event.parent])
            eventtrack = event.track
            if eventtrack is not None:
                fw("\tEventTrack %d {\n" % len(eventtrack.keyframe_points))
                for keyframe in eventtrack.keyframe_points:
                    fw("\t\t%d,\n" % (f2ms * int(keyframe.co[0])))
                fw("\t}\n")
            fw("}\n")
         
        # COLLISION SHAPES
        for collider in objects['collisionshape']:
            fw("CollisionShape \"%s\" {\n" % collider.name)
            fw("\tObjectId %d,\n" % object_indices[collider.name])
            if collider.parent is not None:
                fw("\tParent %d,\n" % object_indices[collider.parent])
            if collider.type == 'Box':
                fw("\tBox,\n")
            else:
                fw("\tSphere,\n")
                
            fw("\tVertices %d {\n" % len(collider.verts))
            for vert in collider.verts:
                fw("\t\t{%s, %s, %s},\n" % tuple(f2s(rnd(x)) for x in vert))
            fw("\t}\n")
            if collider.type == 'Sphere':
                fw("\tBoundsRadius %s,\n" % f2s(rnd(collider.radius)))
            fw("}\n")
                
                
    