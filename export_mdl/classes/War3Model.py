import bpy
import bmesh
import math
import itertools
import os.path

from mathutils import Quaternion, Matrix, Vector

from collections import defaultdict
from operator import itemgetter

from .War3AnimationSequence import War3AnimationSequence
from .War3AnimationCurve import War3AnimationCurve
from .War3ParticleSystem import War3ParticleSystem
from .War3MaterialLayer import War3MaterialLayer
from .War3Material import War3Material
from .War3GeosetAnim import War3GeosetAnim
from .War3Geoset import War3Geoset
from .War3TextureAnim import War3TextureAnim
from .War3Texture import War3Texture
from .War3Light import War3Light
from .War3Object import War3Object
from .War3Camera import War3Camera
from .War3CollisionShape import War3CollisionShape
from .War3EventObject import War3EventObject

from ..utils import *

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
                    
                    psys.dimensions = Vector(map(abs, settings.global_matrix @ obj.dimensions))
                    
                    psys.parent = parent
                    psys.visibility = visibility
                    self.register_global_sequence(psys.visibility)
                    
                    if is_animated:
                        bone = War3Object(obj.name)
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
                collider = War3CollisionShape(obj.name)
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
                    eventobj = War3EventObject(obj.name)
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
                    # I would make this a War3Bone... but i realize that we don't know 
                    # whether it is actually a bone until we know if any vertices are skinned to it.
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