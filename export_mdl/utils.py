import bpy
import bpy
import bmesh
import math
from operator import itemgetter

decimal_places = 5

def rnd(val):
    return round(val, decimal_places)
    
def f2s(value):
    return ('%.6f' % value).rstrip('0').rstrip('.')
    
def calc_bounds_radius(min_ext, max_ext):
    x = (max_ext[0] - min_ext[0])/2
    y = (max_ext[1] - min_ext[1])/2
    z = (max_ext[2] - min_ext[2])/2
    return math.sqrt(math.pow(x, 2) + math.pow(y, 2) + math.pow(z, 2))
    
def calc_extents(vertices):
    max_extents = tuple(max(vertices,key=itemgetter(i))[i] for i in range(3))
    min_extents = tuple(min(vertices,key=itemgetter(i))[i] for i in range(3))
    
    return min_extents, max_extents

def prepare_mesh(obj, context, matrix):
    mod = None
    if hasattr(obj.data, "use_auto_smooth") and obj.data.use_auto_smooth:
        mod = obj.modifiers.new("EdgeSplitExport", 'EDGE_SPLIT')
        mod.split_angle = obj.data.auto_smooth_angle
        # mod.use_edge_angle = True
        
    mesh = obj.to_mesh(context.scene, apply_modifiers=True, settings='RENDER')
    
    if mod is not None:
        obj.modifiers.remove(mod)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    # If an object has had a negative scale applied, normals will be inverted. This will fix that. 
    if any(s < 0 for s in obj.scale):
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    del bm

    mesh.calc_normals_split()
    mesh.calc_tessface()

    return mesh
	
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
