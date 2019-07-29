import bpy
import bmesh
import math
import itertools

from collections import defaultdict
from operator import itemgetter

from mathutils import (
    Quaternion, 
    Matrix, 
    Euler, 
    Vector
    )
    
from .utils import *

class War3ExportSettings:
    def __init__(self):
        self.global_matrix = Matrix()
        self.use_selection = False
        self.optimize_animation = False
        self.optimize_tolerance = 0.05
    
class War3Model:

    default_texture = "Textures\white.blp"
    decimal_places = 5

    def __init__(self, context):
        self.objects = defaultdict(set)
        self.objects_all = []
        self.object_indices = {}
        self.geosets = []
        self.geoset_map = {}
        self.geoset_anims = []
        self.geoset_anim_map = {}
        self.materials = []
        self.sequences = []
        self.global_extents_min = 0
        self.global_extents_max = 0
        self.const_color_mats = set()
        self.global_seqs = set()
        self.cameras = []
        self.textures = []
        self.tvertex_anims = []
        
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
       
    @staticmethod
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
            root_parent = War3Model.get_parent(parent)
            if root_parent is not None:
                return root_parent
                
        return parent.name
        
    def get_visibility(self, obj):
        if obj.animation_data is not None:
            curve = War3AnimationCurve.get(obj.animation_data, 'hide_render', 1, self.sequences)
            if curve is not None:
                return curve
        if obj.parent is not None and obj.parent_type != 'BONE':
                return self.get_visibility(obj.parent)
        return None
        
    def from_scene(self, context, settings):
        
        scene = context.scene
        
        self.sequences = self.get_sequences(scene)
        
        objs = []
        mats = set()
        
        if settings.use_selection:
            objs = (obj for obj in scene.objects if obj.is_visible(scene) and obj.select)
        else:
            objs = (obj for obj in scene.objects if obj.is_visible(scene))
            
        for obj in objs:
            parent = War3Model.get_parent(obj)
            
            billboarded = False
            billboard_lock = (False, False, False)
            if hasattr(obj, "mdl_billboard"):
                bb = obj.mdl_billboard
                billboarded = bb.billboarded
                billboard_lock = (bb.billboard_lock_z, bb.billboard_lock_y, bb.billboard_lock_x) # NOTE: Axes are listed backwards (same as with colors)
                
            # Animations
            visibility = self.get_visibility(obj)
                
            anim_loc = War3AnimationCurve.get(obj.animation_data, 'location', 3, self.sequences) # get_curves(obj, 'location', (0, 1, 2))
            if anim_loc is not None and settings.optimize_animation:
                anim_loc.optimize(settings.optimize_tolerance, self.sequences)
                
            anim_rot = War3AnimationCurve.get(obj.animation_data, 'rotation_quaternion', 4, self.sequences) # get_curves(obj, 'rotation_quaternion', (0, 1, 2, 3))
            
            if anim_rot is None:
                anim_rot = War3AnimationCurve.get(obj.animation_data, 'rotation_euler', 3, self.sequences)
                
            if anim_rot is not None and settings.optimize_animation:
                anim_rot.optimize(settings.optimize_tolerance, self.sequences)
                
            anim_scale = War3AnimationCurve.get(obj.animation_data, 'scale', 3, self.sequences) # get_curves(obj, 'scale', (0, 1, 2))
            if anim_scale is not None and settings.optimize_animation:
                anim_scale.optimize(settings.optimize_tolerance, self.sequences)
                
            is_animated = any((anim_loc, anim_rot, anim_scale))
            
            # Particle Systems
            if len(obj.particle_systems):
                data = obj.particle_systems[0].settings
                
                if getattr(data, "mdl_particle_sys"):
                    psys = War3ParticleSystem(obj.name, obj, self)
                    
                    psys.pivot = settings.global_matrix * Vector(obj.location)
                    
                    # psys.dimensions = obj.matrix_world.to_quaternion() * Vector(obj.scale)
                    psys.dimensions = Vector(map(abs, settings.global_matrix * obj.dimensions))
                    
                    psys.parent = parent
                    psys.visibility = visibility
                    self.register_global_sequence(psys.visibility)
                    
                    if is_animated:
                        bone = War3Object(obj.name)
                        bone.parent = parent
                        bone.pivot = settings.global_matrix * Vector(obj.location)
                        bone.anim_loc = anim_loc
                        bone.anim_rot = anim_rot
                        bone.anim_scale = anim_scale
                        self.register_global_sequence(bone.anim_loc)
                        self.register_global_sequence(bone.anim_rot)
                        self.register_global_sequence(bone.anim_scale)
                        
                        if bone.anim_loc is not None:
                            bone.anim_loc.transform_vec(settings.global_matrix)
                            
                        if bone.anim_rot is not None:
                            bone.anim_rot.transform_rot(settings.global_matrix)
                        
                        bone.billboarded = billboarded
                        bone.billboard_lock = billboard_lock
                        self.objects['bone'].add(bone)
                        psys.parent = bone.name
                    
                    if psys.emitter.emitter_type == 'ParticleEmitter':
                        self.objects['particle'].add(psys)
                    elif psys.emitter.emitter_type == 'ParticleEmitter2':
                        self.objects['particle2'].add(psys)
                    else:
                        # Add the material to the list, in case it's unused
                        mat = psys.emitter.ribbon_material
                        mats.add(mat)
                        
                        self.objects['ribbon'].add(psys)
                        
            # Collision Shapes
            elif obj.type == 'EMPTY' and obj.name.startswith('Collision'):
                collider = War3Object(obj.name)
                collider.parent = parent
                collider.pivot = settings.global_matrix * Vector(obj.location)
                
                if 'Box' in obj.name:
                    collider.type = 'Box'
                    corners = []
                    for corner in ((0.5, 0.5, -0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (-0.5, 0.5, 0.5)):
                        mat = settings.global_matrix * obj.matrix_world
                        corners.append(mat.to_quaternion() * Vector(abs(x * obj.empty_draw_size * settings.global_matrix.median_scale) * y for x, y in zip(obj.scale, corner)))

                    vmin, vmax = calc_extents(corners)
                    
                    collider.verts = [vmin, vmax] # TODO: World space or relative to pivot??
                    self.objects['collisionshape'].add(collider)
                elif 'Sphere' in obj.name:
                    collider.type = 'Sphere'
                    collider.verts = [settings.global_matrix * Vector(obj.location)]
                    collider.radius = settings.global_matrix.median_scale * max(abs(x * obj.empty_draw_size) for x in obj.scale)
                    self.objects['collisionshape'].add(collider)
                    
            elif obj.type == 'MESH' or obj.type == 'CURVE':
                mesh = self.prepare_mesh(obj, context, settings.global_matrix * obj.matrix_world)
                
                # Geoset Animation
                vertexcolor_anim = War3AnimationCurve.get(obj.animation_data, 'color', 3, self.sequences)# get_curves(obj, 'color', (0, 1, 2))
                vertexcolor = reversed(obj.color[:3]) if any(i != 1 for i in obj.color[:3]) else None
                if vertexcolor is None and vertexcolor_anim is None:
                    mat = obj.active_material
                    if mat is not None and hasattr(mat, "node_tree"):
                        node = mat.node_tree.nodes.get("VertexColor")
                        if node is not None:
                            vertexcolor = reversed(tuple(node.inputs[0].default_value[:3]))
                            if hasattr(mat.node_tree, "animation_data"):
                                vertexcolor_anim = War3AnimationCurve.get(mat.node_tree.animation_data, 'nodes["VertexColor"].inputs[0].default_value', 3, self.sequences)
                geoset_anim = None
                geoset_anim_hash = 0
                if any((vertexcolor, vertexcolor_anim, visibility)):
                    geoset_anim = War3GeosetAnim(vertexcolor, vertexcolor_anim, visibility)
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
                    bone = War3Object(obj.name) # Object is animated or parent is missing - create a bone for it!
                    
                    bone.parent = parent # Remember to make it the parent - parent is added to matrices further down
                    bone.pivot = settings.global_matrix * Vector(obj.location)
                    bone.anim_loc = anim_loc
                    bone.anim_rot = anim_rot
                    bone.anim_scale = anim_scale
                    self.register_global_sequence(bone.anim_loc)
                    self.register_global_sequence(bone.anim_rot)
                    self.register_global_sequence(bone.anim_scale)
                    bone.matrix = settings.global_matrix * obj.matrix_world.inverted()
                    bone.billboarded = billboarded
                    bone.billboard_lock = billboard_lock
                    if geoset_anim is not None:
                        self.geoset_anim_map[bone] = geoset_anim
                    self.objects['bone'].add(bone)
                    parent = bone.name
                    
                    
                for f in mesh.tessfaces:
                    p = mesh.polygons[f.index]
                    # Textures and materials
                    mat_name = "default"
                    if obj.material_slots and len(obj.material_slots):
                        mat = obj.material_slots[p.material_index].material
                        if mat is not None:
                            mat_name = mat.name
                            mats.add(mat)
                                
                    geoset = None
                    if (mat_name, geoset_anim_hash) in self.geoset_map.keys():
                        geoset = self.geoset_map[(mat_name, geoset_anim_hash)]
                    else:
                        geoset = War3Geoset()
                        geoset.mat_name = mat_name
                        if geoset_anim is not None:
                            geoset.geoset_anim = geoset_anim
                            geoset_anim.geoset = geoset
                        self.geoset_map[(mat_name, geoset_anim_hash)] = geoset
                        
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
                                groups = list(obj.vertex_groups[vg.group].name for vg in vgroups if (obj.vertex_groups[vg.group].name in bone_names and vg.weight > 0.25))[:3]
                                if not len(groups):
                                    groups = [parent]
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
                    
                for geoset in mesh_geosets:
                    geoset.objects.append(obj)
                    if not len(geoset.matrices) and parent is not None:
                        geoset.matrices.append([parent])
                            
                bpy.data.meshes.remove(mesh)
                
                
            elif obj.type == 'EMPTY':
                if obj.name.startswith("SND") or obj.name.startswith("UBR") or obj.name.startswith("FTP") or obj.name.startswith("SPL"):
                    eventobj = War3Object(obj.name)
                    eventobj.pivot = settings.global_matrix * Vector(obj.location)
                    
                    for datapath in ('["event_track"]', '["eventtrack"]', '["EventTrack"]'):
                        eventobj.track = War3AnimationCurve.get(obj.animation_data, datapath, 1, self.sequences) # get_curve(obj, ['["eventtrack"]', '["EventTrack"]', '["event_track"]'])  
                        if eventobj.track is not None:
                            self.register_global_sequence(eventobj.track)
                            break;
                            
                    self.objects['eventobject'].add(eventobj)
                elif obj.name.endswith(" Ref"):
                    att = War3Object(obj.name)
                    att.pivot = settings.global_matrix * Vector(obj.location)
                    att.parent = parent
                    att.visibility = visibility
                    self.register_global_sequence(visibility)
                    att.billboarded = billboarded
                    att.billboard_lock = billboard_lock
                    self.objects['attachment'].add(att)
                elif obj.name.startswith("Bone_"):
                    bone = War3Object(obj.name)
                    if parent is not None:
                        bone.parent = parent
                    bone.pivot = settings.global_matrix * Vector(obj.location)
                    bone.anim_loc = anim_loc
                    bone.anim_scale = anim_scale
                    bone.anim_rot = anim_rot
                    
                    self.register_global_sequence(bone.anim_scale)
                    
                    if bone.anim_loc is not None:
                        self.register_global_sequence(bone.anim_loc)
                        bone.anim_loc.transform_vec(obj.matrix_world.inverted())
                        bone.anim_loc.transform_vec(settings.global_matrix)
                        
                    if bone.anim_rot is not None:
                        self.register_global_sequence(bone.anim_rot)
                        bone.anim_rot.transform_rot(obj.matrix_world.inverted())
                        bone.anim_rot.transform_rot(settings.global_matrix)
                        
                    bone.billboarded = billboarded
                    bone.billboard_lock = billboard_lock
                    self.objects['bone'].add(bone)
            elif obj.type == 'ARMATURE':
                root = War3Object(obj.name)
                if parent is not None:
                    root.parent = parent
                    
                root.pivot = settings.global_matrix * Vector(obj.location)
                
                root.anim_loc = anim_loc
                root.anim_scale = anim_scale
                root.anim_rot = anim_rot
                
                self.register_global_sequence(root.anim_scale)
                
                if root.anim_loc is not None:
                    self.register_global_sequence(root.anim_loc)
                    root.anim_loc.transform_vec(obj.matrix_world.inverted())
                    root.anim_loc.transform_vec(settings.global_matrix)
                    
                if root.anim_rot is not None:
                    self.register_global_sequence(root.anim_rot)
                    root.anim_rot.transform_rot(obj.matrix_world.inverted())
                    root.anim_rot.transform_rot(settings.global_matrix)
                
                root.visibility = visibility
                self.register_global_sequence(visibility)
                root.billboarded = billboarded
                root.billboard_lock = billboard_lock
                self.objects['bone'].add(root) 
                
                for b in obj.pose.bones:
                    bone = War3Object(b.name)
                    if b.parent is not None:
                        bone.parent = b.parent.name
                    else:
                        bone.parent = root.name
                        
                    bone.pivot = obj.matrix_world * Vector(b.bone.head_local) # Armature space to world space
                    bone.pivot = settings.global_matrix * Vector(bone.pivot) # Axis conversion
                    datapath = 'pose.bones[\"'+b.name+'\"].%s'
                    bone.anim_loc = War3AnimationCurve.get(obj.animation_data, datapath % 'location', 3, self.sequences) # get_curves(obj, datapath % 'location', (0, 1, 2))
                    # register_global_seq(bone.anim_loc, global_seqs, [('location', 0)])
                    if settings.optimize_animation and bone.anim_loc is not None:
                        bone.anim_loc.optimize(settings.optimize_tolerance, self.sequences)

                    bone.anim_rot = War3AnimationCurve.get(obj.animation_data, datapath % 'rotation_quaternion', 4, self.sequences) # get_curves(obj, datapath % 'rotation_quaternion', (0, 1, 2, 3))
                    if bone.anim_rot is None:
                        bone.anim_rot = War3AnimationCurve.get(obj.animation_data, datapath % 'rotation_euler', 3, self.sequences)
                    if settings.optimize_animation and bone.anim_rot is not None:
                        bone.anim_rot.optimize(settings.optimize_tolerance, self.sequences)

                    bone.anim_scale = War3AnimationCurve.get(obj.animation_data, datapath % 'scale', 3, self.sequences) # get_curves(obj, datapath % 'scale', (0, 1, 2))
                    if settings.optimize_animation and bone.anim_scale is not None:
                        bone.anim_scale.optimize(settings.optimize_tolerance, self.sequences)
                    
                    self.register_global_sequence(bone.anim_scale)
                    
                    if bone.anim_loc is not None:
                        m = obj.matrix_world * b.bone.matrix_local
                        bone.anim_loc.transform_vec(settings.global_matrix * m.to_3x3().to_4x4())
                        self.register_global_sequence(bone.anim_loc)
                        
                    if bone.anim_rot is not None:
                        mat_pose_ws = obj.matrix_world * b.bone.matrix_local
                        mat_rest_ws = obj.matrix_world * b.matrix
                        bone.anim_rot.transform_rot(mat_pose_ws)
                        bone.anim_rot.transform_rot(settings.global_matrix)
                        self.register_global_sequence(bone.anim_rot)
                    
                    self.objects['bone'].add(bone)
                    
            elif obj.type == 'LAMP':
                light = War3Object(obj.name)
                light.object = obj
                light.pivot = settings.global_matrix * Vector(obj.location)
                light.billboarded = billboarded
                light.billboard_lock = billboard_lock
                
                if hasattr(obj.data, "mdl_light"):
                    light_data = obj.data.mdl_light
                    light.type = light_data.light_type
                
                    light.intensity = light_data.intensity
                    light.intensity_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.intensity', 1, self.sequences) #get_curve(obj.data, ['mdl_light.intensity'])
                    self.register_global_sequence(light.intensity_anim)
                    # register_global_seq(light.intensity_anim, global_seqs)
                    
                    light.atten_start = light_data.atten_start
                    light.atten_start_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.atten_start', 1, self.sequences) # get_curve(obj.data, ['mdl_light.atten_start'])
                    self.register_global_sequence(light.atten_start_anim)
                    # register_global_seq(light.atten_start_anim, global_seqs)
                        
                    light.atten_end = light_data.atten_end
                    light.atten_end_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.atten_end', 1, self.sequences) # get_curve(obj.data, ['mdl_light.atten_end'])
                    self.register_global_sequence(light.atten_end_anim)
                    # register_global_seq(light.atten_end_anim, global_seqs)
                    
                    light.color = light_data.color
                    light.color_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.color', 3, self.sequences) # get_curve(obj.data, ['mdl_light.color'])
                    self.register_global_sequence(light.color_anim)
                    # register_global_seq(light.color_anim, global_seqs, [0])
                        
                    light.amb_color = light_data.amb_color
                    light.amb_color_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.amb_color', 3, self.sequences) # get_curve(obj.data, ['mdl_light.amb_color'])
                    self.register_global_sequence(light.amb_color_anim)
                    # register_global_seq(light.amb_color_anim, global_seqs, [0])
                        
                    light.amb_intensity = light_data.amb_intensity
                    light.amb_intensity_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.amb_intensity', 1, self.sequences) # get_curve(obj.data, ['obj.mdl_light.amb_intensity'])
                    self.register_global_sequence(light.amb_intensity_anim)
                    # register_global_seq(light.amb_intensity_anim, global_seqs)
                        
                light.visibility = visibility
                self.register_global_sequence(visibility)
                self.objects['light'].add(light)
                
            elif obj.type == 'CAMERA':
                self.cameras.append(obj)
          
            
        self.geosets = list(self.geoset_map.values())
        self.materials = [War3Material.get(mat, self) for mat in mats]
        # Add default material if no other materials present
        if any((x for x in self.geosets if x.mat_name == "default")):
            default_mat = War3Material("default")
            default_mat.layers.append(War3MaterialLayer())
            self.materials.append(default_mat)
            
        self.materials = sorted(self.materials, key=lambda x: x.priority_plane)

        layers = list(itertools.chain.from_iterable([material.layers for material in self.materials]))
        self.textures = list(set((layer.texture for layer in layers))) # Convert to set and back to list for unique entries
        
        # Demote bones to helpers if they have no attached geosets
        for bone in self.objects['bone']:
            if not any([g for g in self.geosets if bone.name in itertools.chain.from_iterable(g.matrices)]):
                self.objects['helper'].add(bone)
                
        self.objects['bone'] -= self.objects['helper']
        # We also need the textures used by emitters
        for psys in list(self.objects['particle']) + list(self.objects['particle2']) + list(self.objects['ribbon']):
            if psys.emitter.texture_path not in self.textures:
                self.textures.append(psys.emitter.texture_path)
             
        self.tvertex_anims = list(set((layer.texture_anim for layer in layers if layer.texture_anim is not None)))
        print('TVertex Anim Count: %d' % len(self.tvertex_anims))
        
        vertices_all = []
        
        self.objects_all = []
        self.object_indices = {}
        
        index = 0
        for tag in ('bone', 'light', 'helper', 'attachment', 'particle', 'particle2', 'ribbon', 'eventobject', 'collisionshape'):
            for object in self.objects[tag]:
                self.object_indices[object.name] = index
                self.objects_all.append(object)
                vertices_all.append(object.pivot)
                if tag == 'collisionshape':
                    for vert in object.verts:
                        vertices_all.append(vert)
                index = index+1
                
        for geoset in self.geosets:
            for vertex in geoset.vertices:
                vertices_all.append(vertex[0])
                
            geoset.min_extent, geoset.max_extent = calc_extents([x[0] for x in geoset.vertices])
            if geoset.geoset_anim is not None:
                self.register_global_sequence(geoset.geoset_anim.alpha_anim)
                self.register_global_sequence(geoset.geoset_anim.color_anim)

                for bone in itertools.chain.from_iterable(geoset.matrices):
                    self.geoset_anim_map[bone] = geoset.geoset_anim
         
        # Account for particle systems when calculating bounds 
        for psys in list(self.objects['particle']) + list(self.objects['particle2']) + list(self.objects['ribbon']):
            vertices_all.append(tuple(x + y/2 for x, y in zip(psys.pivot, psys.dimensions)))
            vertices_all.append(tuple(x - y/2 for x, y in zip(psys.pivot, psys.dimensions)))
        
        self.geoset_anims = list(set(g.geoset_anim for g in self.geosets if g.geoset_anim is not None))
        
        self.global_extents_min, self.global_extents_max = calc_extents(vertices_all) if len(vertices_all) else ((0, 0, 0), (0, 0, 0))
        self.global_seqs = sorted(self.global_seqs) 
           
        
    def to_scene(self, context):
        pass
        
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
        elif 'scale' in data_path:
            self.type = 'Scale'
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
                    if (frame >= sequence.start and frame <= sequence.end) or self.global_sequence > 0:
                        frames.add(keyframe.co[0])
                        break
         
        # We want start and end keyframes for each sequence. Make sure not to do this for events and global sequences, though!
        if self.global_sequence < 0 and self.type in {'Rotation', 'Translation', 'Scale'}:
            for sequence in sequences:
                frames.add(round(sequence.start / f2ms))
                frames.add(round(sequence.end / f2ms))
            
        if self.type == 'Boolean' or self.type == 'Event':
            self.interpolation == 'DontInterp'
         
        self.keyframes = {}
        self.handles_right = {}
        self.handles_left = {}
        self.curves = []
        
        for frame in frames:
            values = []
            handle_left = []
            handle_right = []
            
            keys = fcurves.keys()
            keys = sorted(keys, key=lambda x: x[1])
            for key in keys:
                self.curves.append(fcurves[key])
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
    
    def split_segment(self, start, end, tolerance):
        n = float(end[0] - start[0])
        error = -1
        frame = 0
        # print('Start: %d, End: %d, Range: %f' % (start[0], end[0], n))
        
        for i in (i for i in range(start[0], end[0]) if i in self.keyframes.keys()):
            middle = self.keyframes[i]
            distance = 0
            t = max(0, min(1, float(i - start[0]) / n)) # Interpolation factor
            if self.type == 'Translation' or self.type == 'Scale':
                a = Vector(start[1])
                b = Vector(middle)
                c = Vector(end[1])
                delta = b - a.lerp(c, t)
                distance = delta.magnitude # Just the linear distance, for now
            elif self.type == 'Rotation':
                distance = 1 - Quaternion(middle).dot(Quaternion(start[1]).slerp(Quaternion(end[1]), t)) # Spherical distance in the range of 0-2
                
            if distance > error:
                error = distance
                frame = i
                
        if error > 0 and error > tolerance:
            middle = (frame, self.keyframes[frame])
            result = [middle]
            if frame != start[0] and frame != end[0]: # Prevents infinite recursion
                result += self.split_segment(start, middle, tolerance)
                result += self.split_segment(middle, end, tolerance)
                return result
                
        return []
    
    def optimize(self, tolerance, sequences):
        
        f2ms = 1000 / bpy.context.scene.render.fps
        
        if self.interpolation == 'Bezier':
            self.interpolation = 'Linear' # This feature doesn't support bezier as of right now
           
        print('Before: %d' % len(self.keyframes))
        
        newKeys = []
        for sequence in sequences:
            start = int(round(sequence.start / f2ms))
            end = int(round(sequence.end / f2ms))
            newKeys += [(start, self.keyframes[start]), (end, self.keyframes[end])]
            newKeys += self.split_segment((start, self.keyframes[start]) , (end, self.keyframes[end]), tolerance)
        
        self.keyframes.clear()
        self.keyframes.update(newKeys)
        print('After: %d' % len(self.keyframes))

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
       
    def __ne__(self, other):
        return not self.__eq__(other)
       
    def __hash__(self):
        return hash((hash(self.translation), hash(self.rotation), hash(self.scale)))
      
    @staticmethod
    def get(anim_data, uv_node, sequences):
        anim = War3TextureAnim()
        if anim_data.action:
            anim.translation = War3AnimationCurve.get(anim_data, 'nodes["%s"].translation' % uv_node.name, 3, sequences)
            anim.rotation = War3AnimationCurve.get(anim_data, 'nodes["%s"].rotation' % uv_node.name, 3, sequences)
            anim.scale = War3AnimationCurve.get(anim_data, 'nodes["%s"].scale' % uv_node.name, 3, sequences)
                    
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
        for geoset in model.geosets:
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
                        print('Texture anim found!')
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