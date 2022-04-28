import bpy
import bmesh
import math
import itertools
import os.path

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

class War3ImportSettings:
    def __init__(self):
        self.global_matrix = Matrix()
    
class War3Model:

    default_texture = "Textures\white.blp"
    decimal_places = 5

    def __init__(self, context):
        self.objects = defaultdict(set)
        self.objects_all = []
        self.object_indices = {}
        self.geosets = []
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
        
        depsgraph = context.evaluated_depsgraph_get()
        mesh =  bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
        
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
        mesh.calc_loop_triangles()

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
        
    def from_scene(self, context, settings, report):
        
        scene = context.scene
        
        self.sequences = self.get_sequences(scene)
        
        objs = []
        mats = set()
        geoset_map = {}
        
        if settings.use_selection:
            objs = (obj for obj in scene.objects if obj.select_get() and obj.visible_get())
        else:
            objs = (obj for obj in scene.objects if obj.visible_get())
            
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
                
            anim_loc = War3AnimationCurve.get(obj.animation_data, 'location', 3, self.sequences)
            if anim_loc is not None and settings.optimize_animation:
                anim_loc.optimize(settings.optimize_tolerance, self.sequences)
                
            anim_rot = War3AnimationCurve.get(obj.animation_data, 'rotation_quaternion', 4, self.sequences)
            
            if anim_rot is None:
                anim_rot = War3AnimationCurve.get(obj.animation_data, 'rotation_euler', 3, self.sequences)
                
            if anim_rot is not None and settings.optimize_animation:
                anim_rot.optimize(settings.optimize_tolerance, self.sequences)
                
            anim_scale = War3AnimationCurve.get(obj.animation_data, 'scale', 3, self.sequences)
            if anim_scale is not None and settings.optimize_animation:
                anim_scale.optimize(settings.optimize_tolerance, self.sequences)
                
            is_animated = any((anim_loc, anim_rot, anim_scale))
            
            # Particle Systems
            if len(obj.particle_systems):
                data = obj.particle_systems[0].settings
                
                if getattr(data, "mdl_particle_sys"):
                    psys = War3ParticleSystem(obj.name)
                    psys.from_object(obj, self)
                    
                    psys.pivot = settings.global_matrix @ Vector(obj.location)
                    
                    # psys.dimensions = obj.matrix_world.to_quaternion() * Vector(obj.scale)
                    psys.dimensions = Vector(map(abs, settings.global_matrix @ obj.dimensions))
                    
                    psys.parent = parent
                    psys.visibility = visibility
                    self.register_global_sequence(psys.visibility)
                    
                    if is_animated:
                        bone = War3Bone(obj.name)
                        bone.parent = parent
                        bone.pivot = settings.global_matrix @ Vector(obj.location)
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
                collider.pivot = settings.global_matrix @ Vector(obj.location)
                
                if 'Box' in obj.name:
                    collider.type = 'Box'
                    corners = []
                    for corner in ((0.5, 0.5, -0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (-0.5, 0.5, 0.5)):
                        mat = settings.global_matrix @ obj.matrix_world
                        corners.append(mat.to_quaternion() @ Vector(abs(x * obj.empty_display_size * settings.global_matrix.median_scale) * y for x, y in zip(obj.scale, corner)))

                    vmin, vmax = calc_extents(corners)
                    
                    collider.verts = [vmin, vmax] # TODO: World space or relative to pivot??
                    self.objects['collisionshape'].add(collider)
                elif 'Sphere' in obj.name:
                    collider.type = 'Sphere'
                    collider.verts = [settings.global_matrix @ Vector(obj.location)]
                    collider.radius = settings.global_matrix.median_scale * max(abs(x * obj.empty_display_size) for x in obj.scale)
                    self.objects['collisionshape'].add(collider)
                    
            elif obj.type == 'MESH' or obj.type == 'CURVE':
                mesh = self.prepare_mesh(obj, context, settings.global_matrix @ obj.matrix_world)
                
                # Geoset Animation
                vertexcolor_anim = War3AnimationCurve.get(obj.animation_data, 'color', 3, self.sequences)
                vertexcolor = None
                
                if any(i < 0.999 for i in obj.color[:3]):
                    vertexcolor = tuple(obj.color[:3])
                    
                if not any((vertexcolor, vertexcolor_anim)):
                    mat = obj.active_material
                    if mat is not None and hasattr(mat, "node_tree") and mat.node_tree is not None:
                        node = mat.node_tree.nodes.get("VertexColor")
                        if node is not None:
                            attr = "outputs" if node.bl_idname == 'ShaderNodeRGB' else "inputs"
                            vertexcolor = tuple(getattr(node, attr)[0].default_value[:3])
                            if hasattr(mat.node_tree, "animation_data"):
                                vertexcolor_anim = War3AnimationCurve.get(mat.node_tree.animation_data, 'nodes["VertexColor"].%s[0].default_value' % attr, 3, self.sequences)
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
                    if armature.object is None:
                        report({'ERROR'}, "Armature modifier on %s has no object set!" % obj.name)
                    else:
                        bone_names = set(b.name for b in armature.object.data.bones)
                    
                bone = None
                if (armature is None and parent is None) or is_animated:
                    bone = War3Object(obj.name) # Object is animated or parent is missing - create a bone for it!
                    
                    bone.parent = parent # Remember to make it the parent - parent is added to matrices further down
                    bone.pivot = settings.global_matrix @ Vector(obj.location)
                    bone.anim_loc = anim_loc
                    bone.anim_rot = anim_rot
                    bone.anim_scale = anim_scale
                    
                    if bone.anim_loc is not None:
                        self.register_global_sequence(bone.anim_loc)
                        bone.anim_loc.transform_vec(obj.matrix_world.inverted())
                        bone.anim_loc.transform_vec(settings.global_matrix)
                        
                    if bone.anim_rot is not None:
                        self.register_global_sequence(bone.anim_rot)
                        bone.anim_rot.transform_rot(obj.matrix_world.inverted())
                        bone.anim_rot.transform_rot(settings.global_matrix)
                        
                    self.register_global_sequence(bone.anim_scale)
                    bone.billboarded = billboarded
                    bone.billboard_lock = billboard_lock
                    if geoset_anim is not None:
                        self.geoset_anim_map[bone] = geoset_anim
                    self.objects['bone'].add(bone)
                    parent = bone.name
                    
                    
                for tri in mesh.loop_triangles:
                    # p = mesh.polygons[f.index]
                    # Textures and materials
                    mat_name = "default"
                    if obj.material_slots and len(obj.material_slots):
                        mat = obj.material_slots[tri.material_index].material
                        if mat is not None:
                            mat_name = mat.name
                            mats.add(mat)
                                
                    geoset = None
                    if (mat_name, geoset_anim_hash) in geoset_map.keys():
                        geoset = geoset_map[(mat_name, geoset_anim_hash)]
                    else:
                        geoset = War3Geoset()
                        geoset.mat_name = mat_name
                        if geoset_anim is not None:
                            geoset.geoset_anim = geoset_anim
                            geoset_anim.geoset = geoset
                        geoset_map[(mat_name, geoset_anim_hash)] = geoset
                        
                    # Vertices, faces, and matrices  
                    vertexmap = {}
                    for vert, loop in zip(tri.vertices, tri.loops):
                        co = mesh.vertices[vert].co
                        coord = (rnd(co.x), rnd(co.y), rnd(co.z))
                        n = mesh.vertices[vert].normal if tri.use_smooth else tri.normal
                        norm = (rnd(n.x), rnd(n.y), rnd(n.z))
                        uv = mesh.uv_layers.active.data[loop].uv if len(mesh.uv_layers) else Vector((0.0, 0.0))
                        uv[1] = 1 - uv[1] # For some reason, uv Y coordinates appear flipped. This should fix that. 
                        tvert = (rnd(uv.x), rnd(uv.y))
                        groups = None
                        matrix = 0
                        
                        if armature is not None:
                            vgroups = sorted(mesh.vertices[vert].groups[:], key=lambda x:x.weight, reverse=True) # Sort bones by descending weight
                            if len(vgroups):
                                # Warcraft does not support vertex weights, so we exclude groups with too small influence
                                groups = list(obj.vertex_groups[vg.group].name for vg in vgroups if (obj.vertex_groups[vg.group].name in bone_names and vg.weight > 0.25))[:3]
                                if not len(groups):
                                    for vg in vgroups:
                                        # If we didn't find a group, just take the best match (the list is already sorted by weight)
                                        if obj.vertex_groups[vg.group].name in bone_names:
                                            groups = [obj.vertex_groups[vg.group].name]
                                            break
                            
                        if parent is not None and (groups is None or len(groups) == 0):
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
                    geoset.triangles.append((vertexmap[tri.vertices[0]], vertexmap[tri.vertices[1]], vertexmap[tri.vertices[2]]))
                    
                    mesh_geosets.add(geoset)
                    
                for geoset in mesh_geosets:
                    geoset.objects.append(obj)
                    if not len(geoset.matrices) and parent is not None:
                        geoset.matrices.append([parent])
                            
                # obj.to_mesh_clear()
                bpy.data.meshes.remove(mesh)
                
                
            elif obj.type == 'EMPTY':
                if obj.name.startswith("SND") or obj.name.startswith("UBR") or obj.name.startswith("FTP") or obj.name.startswith("SPL"):
                    eventobj = War3Object(obj.name)
                    eventobj.pivot = settings.global_matrix @ Vector(obj.location)
                    
                    for datapath in ('["event_track"]', '["eventtrack"]', '["EventTrack"]'):
                        eventobj.track = War3AnimationCurve.get(obj.animation_data, datapath, 1, self.sequences) # get_curve(obj, ['["eventtrack"]', '["EventTrack"]', '["event_track"]'])  
                        if eventobj.track is not None:
                            self.register_global_sequence(eventobj.track)
                            break
                            
                    self.objects['eventobject'].add(eventobj)
                elif obj.name.endswith(" Ref"):
                    att = War3Object(obj.name)
                    att.pivot = settings.global_matrix @ Vector(obj.location)
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
                    bone.pivot = settings.global_matrix @ Vector(obj.location)
                    bone.anim_loc = anim_loc
                    bone.anim_scale = anim_scale
                    bone.anim_rot = anim_rot
                    
                    self.register_global_sequence(bone.anim_scale)
                    
                    if bone.anim_loc is not None:
                        self.register_global_sequence(bone.anim_loc)
                        bone.anim_loc.transform_vec(obj.matrix_world.inverted())
                        # if obj.parent is not None:
                        #     bone.anim_loc.transform_vec(obj.parent.matrix_world.inverted())
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
                    
                root.pivot = settings.global_matrix @ Vector(obj.location)
                
                root.anim_loc = anim_loc
                root.anim_scale = anim_scale
                root.anim_rot = anim_rot
                
                self.register_global_sequence(root.anim_scale)
                
                if root.anim_loc is not None:
                    self.register_global_sequence(root.anim_loc)
                    if obj.parent is not None:
                        root.anim_loc.transform_vec(obj.parent.matrix_world.inverted())
                    root.anim_loc.transform_vec(settings.global_matrix)
                    
                if root.anim_rot is not None:
                    self.register_global_sequence(root.anim_rot)
                    if obj.parent is not None:
                        root.anim_rot.transform_rot(obj.parent.matrix_world.inverted())
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
                        
                    bone.pivot = obj.matrix_world @ Vector(b.bone.head_local) # Armature space to world space
                    bone.pivot = settings.global_matrix @ Vector(bone.pivot) # Axis conversion
                    datapath = 'pose.bones[\"'+b.name+'\"].%s'
                    bone.anim_loc = War3AnimationCurve.get(obj.animation_data, datapath % 'location', 3, self.sequences) # get_curves(obj, datapath % 'location', (0, 1, 2))

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
                        m = obj.matrix_world @ b.bone.matrix_local
                        bone.anim_loc.transform_vec(settings.global_matrix @ m.to_3x3().to_4x4())
                        self.register_global_sequence(bone.anim_loc)
                        
                    if bone.anim_rot is not None:
                        mat_pose_ws = obj.matrix_world @ b.bone.matrix_local
                        mat_rest_ws = obj.matrix_world @ b.matrix
                        bone.anim_rot.transform_rot(mat_pose_ws)
                        bone.anim_rot.transform_rot(settings.global_matrix)
                        self.register_global_sequence(bone.anim_rot)
                    
                    self.objects['bone'].add(bone)
                    
            elif obj.type in ('LAMP', 'LIGHT'):
                light = War3Light(obj.name)
                light.object = obj
                light.pivot = settings.global_matrix @ Vector(obj.location)
                light.billboarded = billboarded
                light.billboard_lock = billboard_lock
                
                if hasattr(obj.data, "mdl_light"):
                    light_data = obj.data.mdl_light
                    light.type = light_data.light_type
                
                    light.intensity = light_data.intensity
                    light.intensity_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.intensity', 1, self.sequences) #get_curve(obj.data, ['mdl_light.intensity'])
                    self.register_global_sequence(light.intensity_anim)
                    
                    light.atten_start = light_data.atten_start
                    light.atten_start_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.atten_start', 1, self.sequences) # get_curve(obj.data, ['mdl_light.atten_start'])
                    self.register_global_sequence(light.atten_start_anim)
                        
                    light.atten_end = light_data.atten_end
                    light.atten_end_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.atten_end', 1, self.sequences) # get_curve(obj.data, ['mdl_light.atten_end'])
                    self.register_global_sequence(light.atten_end_anim)
                    
                    light.color = light_data.color
                    light.color_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.color', 3, self.sequences) # get_curve(obj.data, ['mdl_light.color'])
                    self.register_global_sequence(light.color_anim)
                        
                    light.amb_color = light_data.amb_color
                    light.amb_color_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.amb_color', 3, self.sequences) # get_curve(obj.data, ['mdl_light.amb_color'])
                    self.register_global_sequence(light.amb_color_anim)
                        
                    light.amb_intensity = light_data.amb_intensity
                    light.amb_intensity_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.amb_intensity', 1, self.sequences) # get_curve(obj.data, ['obj.mdl_light.amb_intensity'])
                    self.register_global_sequence(light.amb_intensity_anim)
                        
                light.visibility = visibility
                self.register_global_sequence(visibility)
                self.objects['light'].add(light)
                
            elif obj.type == 'CAMERA':
                camera = War3Camera(obj.name)
                camera.field_of_view = obj.data.angle
                camera.near_clip = obj.data.clip_start*10
                camera.far_clip = obj.data.clip_end*10
                camera.pivot = settings.global_matrix @ Vector(obj.location)

                matrix = settings.global_matrix @ obj.matrix_world
                camera.target = camera.pivot + matrix.to_quaternion() @ Vector((0.0, 0.0, -1.0)) # Target is just a point in front of the camera

                self.cameras.append(obj)
          
            
        self.geosets = list(geoset_map.values())
        self.materials = [War3Material.get(mat, self) for mat in mats]
        # Add default material if no other materials present
        if any((x for x in self.geosets if x.mat_name == "default")):
            default_mat = War3Material("default")
            default_mat.layers.append(War3MaterialLayer())
            self.materials.append(default_mat)

            if len(self.textures) == 0:
                default_texture = War3Texture("Textures/white.blp")
                self.textures.append(default_texture)
            
        self.materials = sorted(self.materials, key=lambda x: x.priority_plane)

        layers = list(itertools.chain.from_iterable([material.layers for material in self.materials]))
        
        # Demote bones to helpers if they have no attached geosets
        for bone in self.objects['bone']:
            if not any([g for g in self.geosets if bone.name in itertools.chain.from_iterable(g.matrices)]):
                self.objects['helper'].add(bone)
                
        self.objects['bone'] -= self.objects['helper']
             
        self.tvertex_anims = list(set((layer.texture_anim for layer in layers if layer.texture_anim is not None)))
        
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
           
        
    def to_scene(self, context, global_matrix, folder):
        
        objects = {}
        materials = {}
        bone_armature = {}
        pivots = [global_matrix @ Vector(pivot) for pivot in self.pivots]

        # Sequences
        scene = context.window.scene
        sequences = scene.mdl_sequences
        for sequence in self.sequences:

            ms2f = bpy.context.scene.render.fps / 1000

            start = int(sequence.start * ms2f)
            end = int(sequence.end * ms2f)

            scene.timeline_markers.new(sequence.name, frame=start)
            scene.timeline_markers.new(sequence.name, frame=end)

            scene.frame_end = max(scene.frame_end, end)

            s = sequences.add()
            s.name = sequence.name
            s.rarity = int(sequence.rarity)
            s.movement_speed = int(sequence.movement_speed)
            s.non_looping = sequence.non_looping

        scene.mdl_sequence_index = len(self.sequences) - 1

        # Materials
        for material_id, material in enumerate(self.materials):
            mat = bpy.data.materials.new(name=material.name)

            # Generate preview nodes
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            nodes.remove(nodes.get('Principled BSDF'))

            output = nodes.get('Material Output')
            output.location = Vector((0, 0))

            mix_node = nodes.new('ShaderNodeMixShader')
            mix_node.location = Vector((-(mix_node.width + 100), 0))
            mix_node.inputs['Fac'].default_value = 1.0

            shader = nodes.new('ShaderNodeBsdfDiffuse')
            shader.location = Vector((mix_node.location[0] - (shader.width + 100), 0))

            transparency_node = nodes.new('ShaderNodeBsdfTransparent')
            transparency_node.location = Vector((shader.location[0], -180))

            links.new(mix_node.inputs[1], transparency_node.outputs[0])
            links.new(mix_node.inputs[2], shader.outputs[0])
            links.new(output.inputs[0], mix_node.outputs[0])

            input_socket = shader.inputs['Color']

            x_offset = transparency_node.location[0]

            material_geoset_ids = [i for i, geoset in enumerate(self.geosets) if geoset.material_id == material_id]
            geoset_anims = set(anim for anim in self.geoset_anims if anim.geoset_id in material_geoset_ids)

            if len(geoset_anims) and material.use_const_color:
                # There can be multiple animations - but most likely they will only differ in visibility, and not in color.
                geoset_anim = next(iter(geoset_anims)) 

                join = nodes.new('ShaderNodeMixRGB')
                join.location = Vector((x_offset - (join.width + 100), 0))
                join.inputs['Fac'].default_value = 1
                join.blend_type = 'MULTIPLY'

                x_offset = join.location[0]

                vertex_color_node = nodes.new('ShaderNodeRGB')
                vertex_color_node.name = 'VertexColor'
                vertex_color_node.location = Vector((x_offset - (vertex_color_node.width + 200), 320))

                links.new(join.inputs['Color2'], vertex_color_node.outputs[0])
                links.new(input_socket, join.outputs[0])
                input_socket = join.inputs['Color1']

                if geoset_anim.color is not None:
                    c = tuple(reversed(geoset_anim.color))
                    vertex_color_node.outputs[0].default_value = Vector((c[0], c[1], c[2], 1))
                if geoset_anim.color_anim is not None:
                    geoset_anim.color_anim.to_fcurves(mat.node_tree.nodes["VertexColor"].outputs[0], mat.node_tree, 'default_value', 'nodes["VertexColor].outputs[0]')

            for layer_index, layer in enumerate(material.layers):
                item = mat.mdl_layers.add()
                item.name = "Layer %d" % layer_index
                item.filter_mode = layer.filter_mode
                item.unshaded = layer.unshaded
                item.unfogged = layer.unfogged
                item.no_depth_test = layer.no_depth_test
                item.no_depth_set = layer.no_depth_set
                item.two_sided = layer.two_sided
                item.alpha = layer.alpha_value

            def create_node(index, offset):
                mdl_layer = mat.mdl_layers[index]
                source_layer = material.layers[index]
                node = None

                texture = self.textures[source_layer.texture_id]
                if texture.is_replaceable:
                    mdl_layer.texture_type = '36'
                    if texture.replaceable_id in {1, 2, 11, 31, 32, 33, 34, 35, 36}:
                        mdl_layer.texture_type = str(texture.replaceable_id)
                    mdl_layer.replaceable_id = texture.replaceable_id

                    uv_node = None
                    mapping_node = None
                    color_node = None
                    if mdl_layer.replaceable_id > 1:
                        uv_node = nodes.new('ShaderNodeTexCoord')

                    if mdl_layer.replaceable_id < 3:
                        color_node = nodes.new('ShaderNodeRGB')
                        color_node.outputs[0].default_value = (1.0, 0.0, 0.0, 1.0) # Teamcolor
                        color_node.name = "TeamColor"

                    if mdl_layer.replaceable_id == 1:
                        color_node.location = offset
                        node = color_node
                    elif mdl_layer.replaceable_id == 2:
                        glow_node = nodes.new('ShaderNodeTexGradient')
                        glow_node.name = "TeamGlow"
                        glow_node.gradient_type = "QUADRATIC_SPHERE"
                        glow_node.location = offset - Vector((glow_node.width + 100, 180))

                        color_node.location = offset - Vector((color_node.width + 100, -50))

                        mapping_node = nodes.new('ShaderNodeMapping')
                        mapping_node.inputs['Location'].default_value = Vector((-1, -1, 0))
                        mapping_node.inputs['Scale'].default_value = Vector((2, 2, 1))
                        mapping_node.location = glow_node.location - Vector((mapping_node.width + 100, 0))

                        uv_node.location = mapping_node.location - Vector((uv_node.width + 100, 0))

                        links.new(uv_node.outputs['UV'], mapping_node.inputs['Vector'])
                        links.new(mapping_node.outputs[0], glow_node.inputs['Vector'])

                        join = nodes.new('ShaderNodeMixRGB')
                        join.blend_type = 'MULTIPLY'
                        join.inputs['Fac'].default_value = 1.0
                        join.location = offset

                        links.new(color_node.outputs[0], join.inputs['Color1'])
                        links.new(glow_node.outputs[0], join.inputs['Color2'])

                        node = join
                    else:
                        checker_node = nodes.new('ShaderNodeTexChecker')
                        checker_node.name = "ReplaceableTexture"
                        checker_node.location = offset

                        links.new(uv_node.outputs['UV'], checker_node.inputs['Vector'])

                        uv_node.location = offset - Vector((uv_node.width + 100, 0))

                        node = checker_node

                else:
                    mdl_layer.texture_type = '0'
                    mdl_layer.path = texture.image_path

                    image_name = os.path.basename(texture.image_path.replace('.blp', '.png'))
                    import_path = os.path.join(folder, image_name)

                    node = nodes.new('ShaderNodeTexImage')
                    node.name = image_name

                    if image_name in bpy.data.images:
                        node.image = bpy.data.images[image_name]
                    else:
                        print("Loading image: %s" % import_path)
                        if os.path.exists(import_path):
                            img = bpy.data.images.load(import_path)
                            node.image = img
                        else:
                            print("Image at path %s does not exist!" % import_path)

                node.location = offset

                if source_layer.texture_anim_id is not None:
                    texture_anim = self.tvertex_anims[source_layer.texture_anim_id]
                    mapping_node = nodes.new('ShaderNodeMapping')
                    mapping_node.name = mdl_layer.name
                    mapping_node.location = offset + Vector((0, -300))
                    if len(node.inputs): # No inputs on RGB node
                        links.new(node.inputs[0], mapping_node.outputs[0])

                    if texture_anim.location is not None:
                        texture_anim.location.to_fcurves(mapping_node.inputs["Location"], mat.node_tree, 'default_value', 'mapping_node.inputs["Location"]')
                    if texture_anim.rotation is not None: # TODO: Needs to convert from quaternion to euler!
                        texture_anim.rotation.to_fcurves(mapping_node.inputs["Rotation"], mat.node_tree, 'default_value', 'mapping_node.inputs["Rotation"]')
                    if texture_anim.scale is not None:
                        texture_anim.scale.to_fcurves(mapping_node.inputs["Scale"], mat.node_tree, 'default_value', 'mapping_node.inputs["Scale"]')

                return node

            def create_join(top_index, bottom_index, offset):
                if bottom_index < 0:
                    return create_node(top_index, offset)
                
                top_node = create_node(top_index, offset + Vector((-300, -200)))
                bottom_node = None
                if bottom_index > 0:
                    bottom_node = create_join(bottom_index, bottom_index - 1, offset + Vector((-300, 200)))
                else:
                    bottom_node = create_node(bottom_index, offset + Vector((-300, 200)))

                join = nodes.new('ShaderNodeMixRGB')
                join.location = offset
                filter_mode = material.layers[top_index].filter_mode
                use_alpha = filter_mode in {'AddAlpha', 'Blend', 'Transparent'}
                has_alpha = top_node.outputs.get('Alpha') is not None
                if filter_mode == 'Additive':
                    join.blend_type = 'ADD'
                elif filter_mode in {'Modulate', 'Modulate2X'}:
                    join.blend_type = 'MULTIPLY'
                else:
                    join.blend_type = 'MIX'

                links.new(join.inputs['Color1'], bottom_node.outputs['Color'])
                links.new(join.inputs['Color2'], top_node.outputs['Color'])
                if use_alpha and has_alpha:
                    links.new(join.inputs['Fac'], top_node.outputs['Alpha'])

                return join

            last_index = len(material.layers) - 1
            last_node = create_join(last_index, last_index-1, Vector((x_offset - 400, 0)))
            links.new(last_node.outputs[0], input_socket)

            if any(True for layer in material.layers if layer.filter_mode == 'None'):
                mat.blend_method = 'OPAQUE'
                mat.shadow_method = 'OPAQUE'
            elif any(True for layer in material.layers if layer.filter_mode == 'Transparent'):
                mat.blend_method = 'CLIP'
                mat.shadow_method = 'CLIP'
            else:
                mat.blend_method = 'BLEND'
                mat.shadow_method = 'NONE'

            if len([True for layer in material.layers if layer.filter_mode == 'None']) == 0:
                if last_node.outputs.get('Alpha') is not None:
                    links.new(mix_node.inputs['Fac'], last_node.outputs.get('Alpha'))
                elif material.layers[-1].filter_mode in {'Additive', 'AddBlend'}:
                    # Use color as alpha
                    links.new(mix_node.inputs['Fac'], last_node.outputs[0])

            mat.mdl_layer_index = len(mat.mdl_layers)-1

            materials[material_id] = mat


        edit_bones = {}
        node_map = {node.object_id:node for node in list(self.objects['bone']) + list(self.objects['helper'])}
        skinned_matrices = [geoset.matrices for geoset in self.geosets if len(geoset.matrices) > 1]
        skinned_bone_ids = set(itertools.chain.from_iterable([b for matrix in skinned_matrices for b in matrix]))
        armature_obj = None
        armature = None

        def create_bone(node):
            if node.object_id in edit_bones:
                # Bone was already created
                return edit_bones[node.object_id]

            bone_name = node.name

            parent = None
            if node.parent_id is not None and node.parent_id in node_map:
                parent = create_bone(node_map[node.parent_id])

            edit_bone = armature.edit_bones.new(bone_name)
            edit_bone.head = pivots[node.object_id]
            edit_bone.tail = edit_bone.head + Vector((0.0, 0.0, 0.1))

            if parent is not None:
                edit_bone.parent = parent

            edit_bones[node.object_id] = edit_bone

            objects[node.object_id] = edit_bone.name
            bone_armature[bone_name] = armature_obj

            return edit_bone

        def orient_bone(bone):
            n = len(bone.children)
            if n == 1:
                bone.tail = bone.children[0].head
            elif n > 1:
                pos = Vector((0, 0, 0))
                pos.x = sum([b.head.x for b in bone.children]) / len(bone.children)
                pos.y = sum([b.head.y for b in bone.children]) / len(bone.children)
                pos.z = sum([b.head.z for b in bone.children]) / len(bone.children)
                bone.tail = pos



        def animate_bone(node):
            pose_bone = armature_obj.pose.bones[node.name]
            matrix = pose_bone.bone.matrix_local.inverted()
            if node.anim_loc is not None:
                matrix = matrix.to_3x3().to_4x4() @ global_matrix
                node.anim_loc.to_fcurves(pose_bone, armature_obj, 'location', 'pose.bones["%s"].location' % node.name, matrix)
            if node.anim_rot is not None:
                node.anim_rot.transform_rot(global_matrix)
                node.anim_rot.transform_rot(matrix)
                node.anim_rot.to_fcurves(pose_bone, armature_obj, 'rotation_quaternion', 'pose.bones["%s"].rotation_quaternion' % node.name)
            if node.anim_scale is not None:
                node.anim_scale.to_fcurves(pose_bone, armature_obj, 'scale', 'pose.bones["%s"].scale' % node.name)

        if len(skinned_bone_ids):
            armature = bpy.data.armatures.new('Armature')
            armature_obj = bpy.data.objects.new('Armature', armature)
            context.collection.objects.link(armature_obj)

            # Enter edit mode so that we can create bones
            context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

            for bone_id in skinned_bone_ids:
                create_bone(node_map[bone_id])
            for edit_bone in armature.edit_bones:
                orient_bone(edit_bone)

            context.view_layer.update()

            bpy.ops.object.mode_set(mode='POSE', toggle=False)
            # Create animations
            armature_bones = [node_map[id] for id in node_map if node_map[id].name in armature.bones]
            for bone in armature_bones:
                animate_bone(bone)
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Geosets
        for geoset_id, geoset in enumerate(self.geosets):
            mesh = bpy.data.meshes.new("Mesh")
            material = materials[geoset.material_id]
                    
            verts = [vertex[0] for vertex in geoset.vertices]
            faces = [tuple(geoset.triangles[i:i + 3]) for i in range(0, len(geoset.triangles), 3)] # Group triangles into tuples of 3
            normals = [Vector(vertex[1]) for vertex in geoset.vertices]
            mesh.from_pydata(verts, [], faces)
            mesh.transform(global_matrix)

            is_skinned = len(geoset.matrices) > 1

            # Mesh will already have split nornals, rest should be smooth
            for f in mesh.polygons:
                f.use_smooth = True

            # UVs
            uvs = mesh.uv_layers.new(name='UV')
            for face in mesh.polygons:
                for loop_index in range(face.loop_start, face.loop_start + face.loop_total):
                    loop = mesh.loops[loop_index]
                    uv = geoset.vertices[loop.vertex_index][2]
                    uvs.data[loop_index].uv = (uv[0], 1 - uv[1]) # UV Y is flipped in MDL source

            # Normals
            mesh.normals_split_custom_set_from_vertices(normals)
            mesh_obj = None

            if is_skinned:

                mesh_obj = bpy.data.objects.new("Geoset %d" % geoset_id, mesh)
                context.collection.objects.link(mesh_obj)

                bone_groups = {}
                geoset_bones = set(itertools.chain.from_iterable(geoset.matrices))

                for bone_id in geoset_bones:
                    bone = node_map[bone_id]
                    if bone.object_id in skinned_bone_ids:
                        bone_groups[bone_id] = mesh_obj.vertex_groups.new(name=bone.name)

                for vertex_index, vertex in enumerate(geoset.vertices):
                    matrix = geoset.matrices[vertex[3]]
                    weight = 1.0 / len(matrix)
                    for bone_id in matrix:
                        bone_groups[bone_id].add([vertex_index], weight, 'ADD')

                armature_mod = mesh_obj.modifiers.new(name='Armature', type='ARMATURE')
                armature_mod.object = armature_obj
            else:
                # Create bone using empty

                def set_origin(obj, global_origin=Vector()):
                    matrix = obj.matrix_world
                    o = matrix.inverted() @ Vector(global_origin)
                    obj.data.transform(Matrix.Translation(-o))
                    matrix.translation = global_origin

                bone_id = geoset.matrices[0][0]
                bone = next(b for b in self.objects['bone'] if b.object_id == bone_id)
                bone_obj = None
                pivot = pivots[bone_id]

                bone_name = bone.name
                if not bone_name.startswith("Bone_"):
                    bone_name = "Bone_%s" % bone_name

                if bone_id in objects:
                    bone_obj = objects[bone_id]
                else: 
                    bone_obj = bpy.data.objects.new( bone_name, None )
                    bone_obj.empty_display_size = 0.5
                    bone_obj.empty_display_type = 'PLAIN_AXES'
                    bone_obj.location = pivot
                    context.collection.objects.link(bone_obj)
                    objects[bone_id] = bone_obj

                if bone.geoset_anim_id is not None:
                    geoset_anim = self.geoset_anims[bone.geoset_anim_id]
                    if geoset_anim.alpha_anim is not None:
                        if bone_obj in bone_armature:
                            pass # WTF do we do here... bones don't have hide_render!
                        else:
                            geoset_anim.alpha_anim.to_fcurves(bone_obj, bone_obj, 'hide_render', 'hide_render')
                
                mesh_obj = bpy.data.objects.new(bone_name.replace('Bone_', 'Geoset_'), mesh)
                context.collection.objects.link(mesh_obj)

                set_origin(mesh_obj, pivot)
                if bone_obj in bone_armature:
                    mesh_obj.parent = bone_armature[bone_obj]
                    mesh_obj.parent_type = 'BONE'
                    mesh_obj.parent_bone = bone_obj
                else:
                    mesh_obj.parent = bone_obj

                mesh_obj.location = (0, 0, 0)

            # Add material slot to mesh
            mesh_obj.data.materials.append(material)
            # Convert triangles to quads for convenience
            context.view_layer.objects.active = mesh_obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.tris_convert_to_quads()
            bpy.ops.object.mode_set(mode='OBJECT')

        # Nodes
        for node_type in self.objects:
            for node in self.objects[node_type]:
                if node.object_id in objects:
                    continue # Already created in previous step

                pivot = pivots[node.object_id]

                emitter_mesh = bpy.data.meshes.new("Particle Emitter")
                emitter_mesh.from_pydata([(-0.5, -0.5, 0.0), (-0.5, 0.5, 0.0), (0.5, 0.5, 0.0), (0.5, -0.5, 0.0)], [], [(0, 1, 2, 3)])

                obj = None
                if node_type in {'helper', 'bone', 'attachment', 'eventobject', 'collisionshape'}: # There shouldn't be any bones left... but just in case
                    node_name = node.name

                    if node_type == 'helper' and not node_name.startswith('Bone_'):
                        node_name = "Bone_%s" % node_name
                    
                    obj = bpy.data.objects.new( node_name, None )
                    obj.empty_display_size = 0.5
                    obj.empty_display_type = 'PLAIN_AXES'

                    if node_type == 'collisionshape':
                        obj.empty_display_size = 1
                        obj.empty_display_type = {'Sphere':'SPHERE', 'Box':'CUBE'}[node.type]

                        if node.type == 'Sphere':
                            obj.scale = global_matrix.to_3x3() @ Vector((node.radius, node.radius, node.radius))
                        else:
                            pmin = global_matrix @ Vector(obj.vertices[0])
                            pmax = global_matrix @ Vector(obj.vertices[1])
                            obj.scale = (abs(pmax[0] - pmin[0]), abs(pmax[1] - pmin[1]), abs(pmax[2] - pmin[2]))

                elif node_type == 'light':
                    bpy.ops.object.light_add(type='POINT', radius=1.0, align='WORLD', location=pivot)
                    obj = context.active_object
                    light_data = obj.data.mdl_data
                    light_data.atten_start = node.atten_start
                    light_data.atten_end = node.atten_end
                    if node.color is not None:
                        light_data.color = tuple(reversed(node.color))
                    if node.amb_color is not None:
                        light_data.amb_color = tuple(reversed(node.amb_color))
                    light_data.intensity = node.intensity
                    light_data.amb_intensity = node.amb_intensity
                elif node_type == 'camera':
                    camera = bpy.data.cameras.new(name='Camera')
                    obj = bpy.data.objects.new(node.name, camera)

                    print("Camera FOV: %d" % node.field_of_view)
                    scale = global_matrix.to_scale()[0]
                    camera.angle = node.field_of_view
                    camera.clip_start = node.near_clip * scale
                    camera.clip_end = node.far_clip * scale

                    if node.target:
                        target = global_matrix @ Vector(node.target)
                        delta = target - pivot
                        rot = delta.to_track_quat('-Z', 'Y')
                        obj.rotation_euler = rot.to_euler()

                elif node_type == 'particle2':
                    obj = bpy.data.objects.new(node.name, emitter_mesh)
                    obj.display_type = 'WIRE'
                    obj.scale = global_matrix @ Vector((node.width, node.height, 1.0))
                    obj.modifiers.new(node.name, type='PARTICLE_SYSTEM')

                    settings = obj.particle_systems[0].settings
                    psys = settings.mdl_particle_sys
                    psys.emitter_type = 'ParticleEmitter2'
                    psys.filter_mode = node.filter_mode
                    psys.unshaded = node.unshaded
                    psys.unfogged = node.unfogged
                    psys.line_emitter = node.line_emitter
                    psys.sort_far_z = node.sort_far_z
                    psys.model_space = node.model_space
                    psys.xy_quad = node.xy_quad
                    psys.head = node.head
                    psys.tail = node.tail
                    psys.emission_rate = node.emission_rate
                    psys.speed = node.speed
                    psys.latitude = node.latitude
                    psys.longitude = node.longitude
                    psys.variation = node.variation
                    psys.gravity = node.gravity
                    psys.start_color = tuple(reversed(node.start_color))
                    psys.mid_color = tuple(reversed(node.mid_color))
                    psys.end_color = tuple(reversed(node.end_color))
                    psys.start_alpha = node.start_alpha
                    psys.mid_alpha = node.mid_alpha
                    psys.end_alpha = node.mid_alpha
                    psys.start_scale = node.start_scale
                    psys.mid_scale = node.mid_scale
                    psys.end_scale = node.end_scale
                    psys.rows = node.rows
                    psys.cols = node.cols
                    psys.life_span = node.life_span
                    psys.tail_length = node.tail_length
                    psys.time = node.time
                    psys.priority_plane = node.priority_plane
                    psys.head_life_start = node.head_life_start
                    psys.head_life_end = node.head_life_end
                    psys.head_life_repeat = node.head_life_repeat
                    psys.head_decay_start = node.head_decay_start
                    psys.head_decay_end = node.head_decay_end
                    psys.head_decay_repeat = node.head_decay_repeat
                    psys.tail_life_start = node.tail_life_start
                    psys.tail_life_end = node.tail_life_end
                    psys.tail_life_repeat = node.tail_life_repeat
                    psys.tail_decay_start = node.tail_decay_start
                    psys.tail_decay_end = node.tail_decay_end
                    psys.tail_decay_repeat = node.tail_decay_repeat
                    psys.alpha = node.alpha

                    if node.speed_anim is not None:
                        node.speed_anim.to_fcurves(psys, settings, 'speed', 'mdl_particle_sys.speed')
                    if node.variation_anim is not None:
                        node.variation_anim.to_fcurves(psys, settings, 'variation', 'mdl_particle_sys.variation')
                    if node.emission_rate_anim is not None:
                        node.emission_rate_anim.to_fcurves(psys, settings, 'emission_rate', 'mdl_particle_sys.emission_rate')
                    if node.gravity_anim is not None:
                        node.gravity_anim.to_fcurves(psys, settings, 'gravity', 'mdl_particle_sys.gravity')
                    if node.latitude_anim is not None:
                        node.latitude_anim.to_fcurves(psys, settings, 'latitude', 'mdl_particle_sys.latitude')

                    texture = self.textures[node.texture_id]
                    if not texture.is_replaceable:
                        psys.texture_path = texture.image_path

                else: 
                    obj = bpy.data.objects.new(node.name, None)

                if node_type == "eventobject":
                    obj['event_type'] = obj.name[:3]
                    obj['event_id'] = obj.name[-4:]
                    obj['event_track'] = 0
                    if node.track is not None:
                        node.track.to_fcurves(obj, obj, '["event_track"]', '["event_track"]')

                obj.location = pivot

                context.collection.objects.link(obj)

                if node.anim_loc is not None:
                    node.anim_loc.to_fcurves(obj, obj, 'location', 'location', global_matrix)
                if node.anim_rot is not None:
                    node.anim_rot.to_fcurves(obj, obj, 'rotation_quaternion', 'rotation_quaternion')
                if node.anim_scale is not None:
                    node.anim_scale.to_fcurves(obj, obj, 'scale', 'scale')
                if node.visibility is not None:
                    node.visibility.to_fcurves(obj, obj, 'hide_render', 'hide_render')
                

                objects[node.object_id] = obj

        # Once all nodes are created, create their parenting relationships
        context.view_layer.update()
        for node_type in self.objects:
            for node in self.objects[node_type]:
                child = objects[node.object_id]
                if child in bone_armature:
                    continue # Parenting of armature bones already handled - plus, the object will be a string
                if node.parent_id is not None:
                    if objects[node.parent_id] in bone_armature:
                        bone_name = objects[node.parent_id]
                        armature = bone_armature[bone_name]
                        child.parent = armature
                        child.parent_type = 'BONE'
                        child.parent_bone = bone_name
                        child.matrix_parent_inverse = armature.data.bones[bone_name].matrix_local.inverted()
                    else:
                        parent = objects[node.parent_id]
                        child.parent_type = 'OBJECT'
                        child.parent = parent
                        child.matrix_parent_inverse = parent.matrix_world.inverted()

        
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
        self.parent_id = None
        self.name = name
        self.pivot = None #TODO
        self.anim_loc = None
        self.anim_rot = None
        self.anim_scale = None
        self.billboarded = False
        self.billboard_lock = (False, False, False)
        self.object_id = 0
        self.visibility = None
        
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

class War3Bone(War3Object):
    def __init__(self, name):
        War3Object.__init__(self, name)
        self.geoset_id = 0
        self.geoset_anim_id = None


class War3Camera(War3Object):
    def __init__(self, name):
        War3Object.__init__(self, name)
        self.field_of_view = 120
        self.far_clip = 1200
        self.near_clip = 100

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
        self.ribbon_material_id = 0
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
        self.ribbon_material_id = emitter.ribbon_material_id
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
        self.rarity = 0
        
class War3AnimationCurve:
    def __init__(self):
        self.interpolation = 'Linear'
        self.global_sequence = -1
        self.type = 'Default'
        self.keyframes = {}
        self.handles_right = {}
        self.handles_left = {}
    
    @staticmethod
    def from_fcurve(fcurves, data_path, sequences, scale=1):
        curve = War3AnimationCurve()

        frames = set()

        if 'rotation' in data_path:
            curve.type = 'Rotation'
        elif 'location' in data_path:
            curve.type = 'Translation'
        elif 'scale' in data_path:
            curve.type = 'Scaling'
        elif 'color' in data_path or 'default_value' in data_path:
            curve.type = 'Color'
        elif 'event' in data_path.lower():
            curve.type = 'EventTrack'
        elif 'visibility' in data_path.lower() or 'hide_render' in data_path.lower():
            curve.type = 'Boolean'

        f2ms = 1000 / bpy.context.scene.render.fps
        
        for fcurve in fcurves.values():
            if len(fcurve.keyframe_points):
                if fcurve.keyframe_points[0].interpolation == 'BEZIER' and curve.type != 'Rotation': # Nonlinear interpolation for rotations is disabled for now
                    curve.interpolation = 'Bezier'
                elif fcurve.keyframe_points[0].interpolation == 'CONSTANT':
                    curve.interpolation = 'DontInterp'
                    
            for mod in fcurve.modifiers:
                if mod.type == 'CYCLES':
                    curve.global_sequence = max(curve.global_sequence, int(fcurve.range()[1] * f2ms))
                    
            for keyframe in fcurve.keyframe_points:
                frame = keyframe.co[0] * f2ms
                for sequence in sequences:
                    if (frame >= sequence.start and frame <= sequence.end) or curve.global_sequence > 0:
                        frames.add(keyframe.co[0])
                        break
         
        # We want start and end keyframes for each sequence. Make sure not to do this for events and global sequences, though!
        if curve.global_sequence < 0 and curve.type in {'Rotation', 'Translation', 'Scaling'}:
            for sequence in sequences:
                frames.add(round(sequence.start / f2ms))
                frames.add(round(sequence.end / f2ms))
            
        if curve.type == 'Boolean' or curve.type == 'EventTrack':
            curve.interpolation = 'DontInterp'
         
        curve.curves = []
        
        for frame in frames:
            values = []
            handle_left = []
            handle_right = []
            
            keys = fcurves.keys()
            keys = sorted(keys, key=lambda x: x[1])
            for key in keys:
                curve.curves.append(fcurves[key])
                value = fcurves[key].evaluate(frame)
                values.append(value * scale)
                
                if 'color' in data_path:
                    values = values[::-1] # Colors are stored in reverse
                    
                if 'hide_render' in data_path:
                    values = [1 - v for v in values] # Hide_Render is the opposite of visibility!
                
                if curve.interpolation == 'Bezier':
                    hl = fcurves[key].evaluate(frame-1)
                    hr = fcurves[key].evaluate(frame+1)
                    handle_left.append(hl)
                    handle_right.append(hr)
            
            if 'rotation' in data_path and 'quaternion' not in data_path: # Warcraft 3 only uses quaternions!
                curve.keyframes[frame] = tuple(Euler(values).to_quaternion())
            else:
                curve.keyframes[frame] = tuple(values)
                
            if curve.interpolation == 'Bezier':
                if 'rotation' in data_path and 'quaternion' not in data_path:
                    curve.handles_left[frame] = tuple(Euler(math.radians(x) for x in handle_left).to_quaternion())
                    curve.handles_right[frame] = tuple(Euler(math.radians(x) for x in handle_right).to_quaternion())
                else:
                    curve.handles_right[frame] = tuple(handle_right)
                    curve.handles_left[frame] = tuple(handle_right)

        return curve

    def bezier_curve(p0, p0_out, p1_in, p1, t):
        nt = (1 - t)
        return nt*nt*nt*p0 + 3 * t * nt*nt * p0_out + 3*t*t*nt * p1_in + t*t*t*p1

    def to_fcurves(self, target, anim_data_obj, data_path, full_data_path, matrix=None):
        num_channels = 1
        for keyframe in self.keyframes:
            frame = int(round(keyframe * bpy.context.scene.render.fps / 1000))
            value = self.keyframes[keyframe]

            num_channels = len(value)

            if 'color' in data_path:
                value = tuple(reversed(value))
            if 'hide_render' in data_path:
                # Invert from 'visibility' to 'hidden'
                value = [not v for v in value]

            if matrix is not None:
                value = matrix @ Vector(value)

            if len(value) == 1:
                value = value[0]

            setattr(target, data_path, value)
            target.keyframe_insert(data_path, frame=frame)

        for channel in range(num_channels):
            curve = anim_data_obj.animation_data.action.fcurves.find(full_data_path, index=channel)

            if curve is None:
                print("Missing curve for object %s, data path %s, channel %d" % (anim_data_obj.name, data_path, channel))
                continue
            if self.global_sequence != -1:
                curve.modifiers.new('CYCLES')
            i = 0
            for frame in self.keyframes:
                frame_num = frame * bpy.context.scene.render.fps / 1000.0
                # Sometimes blender fails to create another frame (for instance, millisecond rounding error might cause two frames to overlap).
                # Because of this, we have to search for the right frame.
                while abs(curve.keyframe_points[i].co[0] - frame_num) > 0.001 and i < len(curve.keyframe_points)-1:
                    i +=1
                curve_frame = curve.keyframe_points[i]
                curve_frame.interpolation = {
                    'DontInterp':'CONSTANT',
                    'Bezier':'BEZIER',
                    'Hermite':'LINEAR',
                    'Linear':'LINEAR'
                }[self.interpolation]

                if self.interpolation in {'Bezier', 'Hermite'}:
                    hl = self.handles_left[frame]
                    hr = self.handles_right[frame]

                    if matrix is not None and self.type != 'Rotation':
                        hl = matrix @ Vector(hl)
                        hr = matrix @ Vector(hr)

                    if self.interpolation == 'Hermite':
                        continue # Not supported yet, should convert to bezier handles

                    def lerp(a, b, t):
                        return a + (b - a) * t

                    if i == 0:
                        curve_frame.handle_left = (curve_frame.co[0] - 20, hl[channel]) 
                    else:
                        hl_frame = lerp(curve.keyframe_points[i-1].co[0], curve_frame.co[0], 0.5)
                        curve_frame.handle_left = (hl_frame, hl[channel])

                    if i+1 < len(curve.keyframe_points):
                        hr_frame = lerp(curve_frame.co[0], curve.keyframe_points[i+1].co[0], 0.5)
                        curve_frame.handle_right = (hr_frame, hr[channel])
                    else:
                        curve_frame.handle_right = (curve_frame.co[0] + 20, hr[channel])

    def split_segment(self, start, end, tolerance):
        n = float(end[0] - start[0])
        error = -1
        frame = 0
        # print('Start: %d, End: %d, Range: %f' % (start[0], end[0], n))
        
        for i in (i for i in range(start[0], end[0]) if i in self.keyframes.keys()):
            middle = self.keyframes[i]
            distance = 0
            t = max(0, min(1, float(i - start[0]) / n)) # Interpolation factor
            if self.type == 'Translation' or self.type == 'Scaling':
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
            self.keyframes[frame] = tuple(matrix @ Vector(self.keyframes[frame]))
            if self.interpolation == 'Bezier':
                self.handles_right[frame] = tuple(matrix @ Vector(self.handles_right[frame]))
                self.handles_left[frame] = tuple(matrix @ Vector(self.handles_left[frame]))
            
        
    def write_mdl(self, name, writer, model):
    
        f2ms = 1000 / bpy.context.scene.render.fps
    
        writer.begin_scope(name, "%d" % len(self.keyframes))
        if self.type != 'EventTrack':
            writer.write(self.interpolation)
        if self.global_sequence > 0:
            writer.write("GlobalSeqId %d" % model.global_seqs.index(self.global_sequence))
            
        for frame in sorted(self.keyframes.keys()):
            n = len(self.keyframes[frame])
            line = "%s"
            if n > 1:
                line = "{ %s" % ('%s, ' * (n-1))
                line += "%s }"
            
            if self.type == 'EventTrack':
                writer.write("%d" % (frame * f2ms))
            else:
                keyframe = self.keyframes[frame]
                
                if self.type == 'Rotation':
                    keyframe = keyframe[1:] + keyframe[:1] # MDL quaternions must be on the form XYZW
                
                value = line % tuple(f2s(rnd(x)) for x in keyframe)
                writer.write("%d: %s" % (frame * f2ms, value))

                    
                if self.interpolation == 'Bezier':
                    hl = self.handles_left[frame]
                    hr = self.handles_right[frame]
                    
                    if self.type == 'Rotation':
                        hl = hl[1:]+hl[:1]
                        hr = hr[1:]+hr[:1]
                
                    writer.write("\tInTan %s" % (line % tuple(f2s(rnd(x)) for x in hl)))
                    writer.write("\tOutTan %s" % (line % tuple(f2s(rnd(x)) for x in hr)))
           
        writer.end_scope()
        
    def write_mdx(self, model, writer):
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
        values.append(tuple(sorted(self.keyframes.items())))
        values.append(tuple(sorted(self.handles_left.items())))
        values.append(tuple(sorted(self.handles_right.items())))
        return hash(tuple(values))
                
    @staticmethod
    def get(anim_data, data_path, num_indices, sequences, scale=1):
        curves = {}
   
        if anim_data and anim_data.action:
            for index in range(num_indices):
                curve = anim_data.action.fcurves.find(data_path, index=index)
                if curve is not None:
                    curves[(data_path.split('.')[-1], index)] = curve # For now, i'm just interested in the type, not the whole data path. Hence, the split returns the name after the last dot. 
            
        if len(curves):
            return War3AnimationCurve.from_fcurve(curves, data_path, sequences, scale)
        return None

class War3Texture:
    def __init__(self, image_path):
        self.image_path = image_path
        self.is_replaceable = False
        self.replaceable_id = 0   

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            a = [self.image_path, self.is_replaceable, self.replaceable_id]
            b = [other.image_path, other.is_replaceable, other.replaceable_id]

            for x, y in zip(a, b):
                if x != y:
                    return False
                
            return True
            
        return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((hash(self.image_path), hash(self.is_replaceable), hash(self.replaceable_id)))


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
    def read_mdl(model, parser):
        pass

    @staticmethod
    def read_mdx(model, parser):
        pass

    def write_mdl(self, model, writer):
        pass

    def write_mdx(self, model, writer):
        pass
      
    @staticmethod
    def get(anim_data, uv_node, sequences):
        anim = War3TextureAnim()
        if anim_data.action:
            if len(uv_node.inputs) > 1: # 2.81 Mapping Node
                anim.translation = War3AnimationCurve.get(anim_data, 'nodes["%s"].inputs["Location"].default_value' % uv_node.name, 3, sequences)
                anim.rotation = War3AnimationCurve.get(anim_data, 'nodes["%s"].inputs["Rotation"].default_value' % uv_node.name, 3, sequences)
                anim.scale = War3AnimationCurve.get(anim_data, 'nodes["%s"].inputs["Scale"].default_value' % uv_node.name, 3, sequences)
            else:
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
        color_hash = 0 if self.color is None else hash(self.color)
        return hash((hash(self.color_anim), hash(self.alpha_anim), color_hash))
        
class War3Geoset:
    def __init__(self):
        self.vertices = []
        self.triangles = []
        self.matrices = []
        self.objects = []
        self.min_extent = None
        self.max_extent = None
        self.mat_name = None
        self.material_id = 0
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
        self.texture_id = 0
        self.texture_id_anim = None
        self.filter_mode = "None"
        self.unshaded = False
        self.two_sided = False
        self.unfogged = False
        self.texture_anim = None
        self.texture_anim_id = None
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
            
            texture = War3Texture(layer_settings.path)
            if layer_settings.texture_type != '0':
                texture.replaceable_id = int(layer_settings.texture_type)
                texture.is_replaceable = True
                texture.image_path = None

                if layer_settings.texture_type == '36':
                    layer.replaceable_id = layer_settings.replaceable_id

            if texture in model.textures:
                layer.texture_id = model.textures.index(texture)
            else:
                model.textures.append(texture)
                layer.texture_id = len(model.textures) - 1
                
            layer.filter_mode   = layer_settings.filter_mode
            layer.unshaded      = layer_settings.unshaded
            layer.two_sided     = layer_settings.two_sided
            layer.no_depth_test = layer_settings.no_depth_test
            layer.no_depth_set  = layer_settings.no_depth_set
            layer.alpha_value   = layer_settings.alpha
            layer.alpha_anim    = War3AnimationCurve.get(mat.animation_data, 'mdl_layers[%d].alpha' % i, 1, model.sequences) # get_curve(mat, {'mdl_layers[%d].alpha' % i})
            
            if layer.alpha_anim is not None:
                model.register_global_sequence(layer.alpha_anim)

            if mat.use_nodes:
                uv_node = mat.node_tree.nodes.get(layer_settings.name)
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