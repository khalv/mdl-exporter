import bpy
import bmesh
import itertools
import math
import getpass
import datetime

from mathutils import Vector, Matrix, Quaternion, Euler
from operator import itemgetter
from collections import defaultdict

from .classes import (
    War3Model,
    War3Object,
    War3TextureAnim,
    War3AnimationSequence,
    War3AnimationCurve,
    War3ParticleSystem,
    War3GeosetAnim,
    War3Geoset,
    War3MaterialLayer,
    War3Material
    )
    
from .utils import *

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
    
def get_sequences(scene):
    markers = [(s.name, s.frame) for s in scene.timeline_markers]
    markers.sort(key=lambda x:x[1])
    f2ms = 1000 / scene.render.fps
    sequences = []
    
    for sequence in scene.mdl_sequences:
        start=min(tuple(m.frame*f2ms for m in scene.timeline_markers if m.name == sequence.name))
        end=max(tuple(m.frame*f2ms for m in scene.timeline_markers if m.name == sequence.name))
        
        sequences.append(War3AnimationSequence(sequence.name, start, end, sequence.non_looping, sequence.move_speed))
        
    return sequences
    
            
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
            
    return parent.name
  
def write_billboard(fw, billboarded, billboard_lock):
    for flag, axis in zip(billboard_lock, ('Z', 'Y', 'X')):
        if flag == True:
            fw("\tBillboardedLock%s,\n" % axis)
    if billboarded == True:
        fw("\tBillboarded,\n")
    
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
        
        
    scene = context.scene
    model = War3Model(context)
    model.sequences = model.get_sequences(scene)

    
    # geosets = {}
    # materials = set()
    # objects = defaultdict(set)
    # geoset_anims = []
    # geoset_anim_map = {}
    # const_color_mats = set()
    # global_seqs = set()
    
    # cameras = []
    
    # filename = bpy.path.basename(context.blend_data.filepath)
    
    objs = []
    
    current_frame = scene.frame_current
    scene.frame_set(1)
    
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
        visibility = War3AnimationCurve.get(obj.animation_data, 'hide_render', 1, model.sequences) # get_curve(obj, ['hide_render', 'hide_view', '["visibility"]'])
        # register_global_seq(visibility, global_seqs)
            
        anim_loc = War3AnimationCurve.get(obj.animation_data, 'location', 3, model.sequences) # get_curves(obj, 'location', (0, 1, 2))
        # register_global_seq(anim_loc, global_seqs, [('location', 0)])
            
        anim_rot = War3AnimationCurve.get(obj.animation_data, 'rotation_quaternion', 4, model.sequences) # get_curves(obj, 'rotation_quaternion', (0, 1, 2, 3))
        
        if anim_rot is None:
            anim_rot = War3AnimationCurve.get(obj.animation_data, 'rotation_euler', 3, model.sequences)
        # register_global_seq(anim_rot, global_seqs, [('rotation_quaternion', 0)])
            
        anim_scale = War3AnimationCurve.get(obj.animation_data, 'scale', 3, model.sequences) # get_curves(obj, 'scale', (0, 1, 2))
        
        # if anim_scale is not None:
        #     register_global_seq(anim_scale, global_seqs, anim_scale.keys()) # Special case to allow for particle systems to animate width/length individually
            
        is_animated = any((anim_loc, anim_rot, anim_scale))
        
        # Particle Systems
        if len(obj.particle_systems):
            settings = obj.particle_systems[0].settings
        
            if getattr(settings, "mdl_particle_sys"):
                psys = War3ParticleSystem(obj.name, obj, model)
                
                psys.pivot = global_matrix * Vector(obj.location)
                
                psys.dimensions = obj.matrix_world.to_quaternion() * Vector(obj.scale)
                psys.dimensions = Vector(map(abs, global_matrix * psys.dimensions))
                
                psys.parent = parent
                psys.visibility = visibility
                
                if psys.emitter.emitter_type == 'ParticleEmitter':
                    model.objects['particle'].add(psys)
                elif psys.emitter.emitter_type == 'ParticleEmitter2':
                    model.objects['particle2'].add(psys)
                else:
                    # Add the material to the list, in case it's unused
                    mat = psys.emitter.ribbon_material
                    model.materials.add(mat)
                    
                    model.objects['ribbon'].add(psys)
            
        # Meshes
        elif obj.type == 'EMPTY' and obj.name.startswith('Collision'):
            collider = War3Object(obj.name)
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
                model.objects['collisionshape'].add(collider)
            elif 'Sphere' in obj.name:
                collider.type = 'Sphere'
                collider.verts = [global_matrix * Vector(obj.location)]
                collider.radius = global_matrix.median_scale * max(abs(x * obj.empty_draw_size) for x in obj.scale)
                model.objects['collisionshape'].add(collider)

        elif obj.type == 'MESH':
            mesh = prepare_mesh(obj, context, global_matrix * obj.matrix_world)
            # mesh.transform(global_matrix * obj.matrix_world)
            
            # Geoset Animation
            vertexcolor_anim = War3AnimationCurve.get(obj.animation_data, 'color', 3, model.sequences)# get_curves(obj, 'color', (0, 1, 2))
            vertexcolor = obj.color if any(i != 1 for i in obj.color) else None
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
                if not obj.name.startswith("Bone_"):
                    bone.name = "Bone_"+obj.name
                
                bone.parent = parent # Remember to make it the parent - parent is added to matrices further down
                bone.pivot = global_matrix * Vector(obj.location)
                bone.anim_loc = anim_loc
                bone.anim_rot = anim_rot
                bone.anim_scale = anim_scale
                bone.matrix = global_matrix * obj.matrix_world.inverted()
                bone.billboarded = billboarded
                bone.billboard_lock = billboard_lock
                if geoset_anim is not None:
                    model.geoset_anim_map[bone] = geoset_anim
                model.objects['bone'].add(bone)
                parent = bone.name
            
            for f in mesh.tessfaces:
                p = mesh.polygons[f.index]
                # Textures and materials
                mat_name = "default"
                if obj.material_slots and len(obj.material_slots):
                    mat = obj.material_slots[p.material_index].material
                    if mat is not None:
                        mat_name = mat.name
                        model.materials.add(mat)
                            
                geoset = None
                if (mat_name, geoset_anim_hash) in model.geosets.keys():
                    geoset = model.geosets[(mat_name, geoset_anim_hash)]
                else:
                    geoset = War3Geoset()
                    geoset.mat_name = mat_name
                    if geoset_anim is not None:
                        geoset.geoset_anim = geoset_anim
                        geoset_anim.geoset = geoset
                    model.geosets[(mat_name, geoset_anim_hash)] = geoset
                  
                  
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
                    model.register_global_sequence(geoset.geoset_anim.alpha_anim) # register_global_seq(geoset.geoset_anim.alpha_anim, global_seqs)
                    model.register_global_sequence(geoset.geoset_anim.color_anim) # register_global_seq(geoset.geoset_anim.color_anim, global_seqs, [('color', 0)])

                    for bone in itertools.chain.from_iterable(geoset.matrices):
                        model.geoset_anim_map[bone] = geoset.geoset_anim
                        
                    
                    
            
            bpy.data.meshes.remove(mesh)
        elif obj.type == 'EMPTY':
            if obj.name.startswith("SND") or obj.name.startswith("UBR") or obj.name.startswith("FPT") or obj.name.startswith("SPL"):
                eventobj = War3Object(obj.name)
                eventobj.pivot = global_matrix * Vector(obj.location)
                
                for datapath in ('["event_track"]', '["eventtrack"]', '["EventTrack"]'):
                    eventobj.track = War3AnimationCurve.get(obj.animation_data, datapath, 1, model.sequences) # get_curve(obj, ['["eventtrack"]', '["EventTrack"]', '["event_track"]'])  
                    if eventobj.track is not None:
                        model.register_global_sequence(eventobj.track)
                        break;
                
                
                # register_global_seq(eventobj.track, global_seqs)
                model.objects['eventobject'].add(eventobj)
                # events.append({"object" : obj, "eventtrack" : eventtrack})
            elif obj.name.endswith(" Ref"):
                att = War3Object(obj.name)
                att.pivot = global_matrix * Vector(obj.location)
                att.parent = parent
                att.visibility = visibility
                att.billboarded = billboarded
                att.billboard_lock = billboard_lock
                model.objects['attachment'].add(att)
            elif obj.name.startswith("Bone_"):
                bone = War3Object(obj.name)
                if parent is not None:
                    bone.parent = parent
                bone.pivot = global_matrix * Vector(obj.location)
                bone.anim_loc = anim_loc
                if bone.anim_loc is not None:
                    bone.anim_loc.transform_vec(obj.matrix_world.inverted())
                    bone.anim_loc.transform_vec(global_matrix)
                bone.anim_rot = anim_rot
                if bone.anim_rot is not None:
                    bone.anim_rot.transform_rot(obj.matrix_world.inverted())
                    bone.anim_rot.transform_rot(global_matrix)
                bone.anim_scale = anim_scale
                bone.billboarded = billboarded
                bone.billboard_lock = billboard_lock
                model.objects['bone'].add(bone)
        elif obj.type == 'ARMATURE':
            for b in obj.pose.bones:
                bone = War3Object(b.name)
                if b.parent is not None:
                    bone.parent = b.parent.name
                bone.pivot = obj.matrix_world * Vector(b.bone.head_local) # Armature space to world space
                bone.pivot = global_matrix * Vector(bone.pivot) # Axis conversion
                datapath = 'pose.bones[\"'+b.name+'\"].%s'
                bone.anim_loc = War3AnimationCurve.get(obj.animation_data, datapath % 'location', 3, model.sequences) # get_curves(obj, datapath % 'location', (0, 1, 2))
                # register_global_seq(bone.anim_loc, global_seqs, [('location', 0)])

                bone.anim_rot = War3AnimationCurve.get(obj.animation_data, datapath % 'rotation_quaternion', 4, model.sequences) # get_curves(obj, datapath % 'rotation_quaternion', (0, 1, 2, 3))
                if bone.anim_rot is None:
                    bone.anim_rot = War3AnimationCurve.get(obj.animation_data, datapath % 'rotation_euler', 3, model.sequences)
                # register_global_seq(bone.anim_rot, global_seqs, [('rotation_quaternion', 0)])

                bone.anim_scale = War3AnimationCurve.get(obj.animation_data, datapath % 'scale', 3, model.sequences) # get_curves(obj, datapath % 'scale', (0, 1, 2))
                # register_global_seq(bone.anim_scale, global_seqs, [('scale', 0)])
                
                if bone.anim_loc is not None:
                    # m = obj.matrix_world * b.bone.matrix_local
                    m = obj.matrix_world * b.bone.matrix_local
                    bone.anim_loc.transform_vec(global_matrix * m.to_quaternion().to_matrix().to_4x4())
                    
                if bone.anim_rot is not None:
                    mat_pose_ws = obj.matrix_world * b.bone.matrix_local
                    mat_rest_ws = obj.matrix_world * b.matrix
                    bone.anim_rot.transform_rot(mat_pose_ws)
                    bone.anim_rot.transform_rot(global_matrix)
                    # bone.anim_rot.transform_rot(mat_rest_ws.inverted())
                
                model.objects['bone'].add(bone)
                # First add to a temporary list and later cross-check against the bones of each geoset? Pick only animated bones?    
        elif obj.type == 'LAMP':
            light = War3Object(obj.name)
            light.object = obj
            light.pivot = global_matrix * Vector(obj.location)
            light.billboarded = billboarded
            light.billboard_lock = billboard_lock
            
            if hasattr(obj.data, "mdl_light"):
                light_data = obj.data.mdl_light
                light.type = light_data.light_type
            
                light.intensity = light_data.intensity
                light.intensity_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.intensity', 1, model.sequences) #get_curve(obj.data, ['mdl_light.intensity'])
                model.register_global_sequence(light.intensity_anim)
                # register_global_seq(light.intensity_anim, global_seqs)
                
                light.atten_start = light_data.atten_start
                light.atten_start_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.atten_start', 1, model.sequences) # get_curve(obj.data, ['mdl_light.atten_start'])
                model.register_global_sequence(light.atten_start_anim)
                # register_global_seq(light.atten_start_anim, global_seqs)
                    
                light.atten_end = light_data.atten_end
                light.atten_end_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.atten_end', 1, model.sequences) # get_curve(obj.data, ['mdl_light.atten_end'])
                model.register_global_sequence(light.atten_end_anim)
                # register_global_seq(light.atten_end_anim, global_seqs)
                
                light.color = light_data.color
                light.color_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.color', 3, model.sequences) # get_curve(obj.data, ['mdl_light.color'])
                model.register_global_sequence(light.color_anim)
                # register_global_seq(light.color_anim, global_seqs, [0])
                    
                light.amb_color = light_data.amb_color
                light.amb_color_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.amb_color', 3, model.sequences) # get_curve(obj.data, ['mdl_light.amb_color'])
                model.register_global_sequence(light.amb_color_anim)
                # register_global_seq(light.amb_color_anim, global_seqs, [0])
                    
                light.amb_intensity = light_data.amb_intensity
                light.amb_intensity_anim = War3AnimationCurve.get(obj.data.animation_data, 'mdl_light.amb_intensity', 1, model.sequences) # get_curve(obj.data, ['obj.mdl_light.amb_intensity'])
                model.register_global_sequence(light.amb_intensity_anim)
                # register_global_seq(light.amb_intensity_anim, global_seqs)
                    
            light.visibility = visibility
            model.objects['light'].add(light)
        elif obj.type == 'CAMERA':
            model.cameras.append(obj)
    
    geosets = list(model.geosets.values())
    mdl_materials = [War3Material.get(mat, model) for mat in model.materials]# parse_materials(materials, const_color_mats, global_seqs)
    # Add default material if no other materials present
    if any((x for x in geosets if x.mat_name == "default")):
        default_mat = War3Material("default")
        default_mat.layers.append(War3MaterialLayer())
        mdl_materials.append(default_mat)
        operator.report({'WARNING'}, "Some geosets have no materials!")
    
    mdl_materials = sorted(mdl_materials, key=lambda x: x.priority_plane)
    material_names = [mat.name for mat in mdl_materials]

    mdl_layers = list(itertools.chain.from_iterable([material.layers for material in mdl_materials]))
    textures = list(set((layer.texture for layer in mdl_layers))) # Convert to set and back to list for unique entries

    
    # Demote bones to helpers if they have no attached geosets
    for bone in model.objects['bone']:
        if not any([g for g in geosets if bone.name in itertools.chain.from_iterable(g.matrices)]):
            model.objects['helper'].add(bone)
            
    model.objects['bone'] -= model.objects['helper']
    # We also need the textures used by emitters
    for psys in list(model.objects['particle']) + list(model.objects['particle2']) + list(model.objects['ribbon']):
        if psys.emitter.texture_path not in textures:
            textures.append(psys.emitter.texture_path)
            
    tvertex_anims = list(set((layer.texture_anim for layer in mdl_layers if layer.texture_anim is not None)))

    vertices_all = []
    objects_all = []
    object_indices = {}
    geoset_indices = {}
    
    index = 0
    for tag in ('bone', 'light', 'helper', 'attachment', 'particle', 'particle2', 'ribbon', 'eventobject', 'collisionshape'):
        for object in model.objects[tag]:
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
    for psys in list(model.objects['particle']) + list(model.objects['particle2']) + list(model.objects['ribbon']):
        vertices_all.append(tuple(x + y/2 for x, y in zip(psys.pivot, psys.dimensions)))
        vertices_all.append(tuple(x - y/2 for x, y in zip(psys.pivot, psys.dimensions)))
    
    geoset_anims = list(set(g.geoset_anim for g in geosets if g.geoset_anim is not None))
    
    model.global_extents_min, model.global_extents_max = calc_extents(vertices_all) if len(vertices_all) else ((0, 0, 0), (0, 0, 0))
    
    scene.frame_set(current_frame)
    
    with open(filepath, 'w') as output:
        fw = output.write
        
        date = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        fw("// Exported on %s by %s\n" % (date, getpass.getuser()))
        
        fw("Version {\n\tFormatVersion %d,\n}\n" % mdl_version)
        # HEADER
        fw("Model \"%s\" {\n" % model.name)
        if len(geosets):
            fw("\tNumGeosets %d,\n" % len(geosets))
        if len(model.objects['bone']):
            fw("\tNumBones %d,\n" % len(model.objects['bone']))
        if len(model.objects['attachment']):
            fw("\tNumAttachments %d,\n" % len(model.objects['attachment']))
        if len(model.objects['particle']): 
            fw("\tNumParticleEmitters %d,\n" % len(model.objects['particle']))
        if len(model.objects['particle2']): 
            fw("\tNumParticleEmitters2 %d,\n" % len(model.objects['particle2']))
        if len(model.objects['ribbon']): 
            fw("\tNumRibbonEmitters %d,\n" % len(model.objects['ribbon']))
        if len(model.objects['eventobject']):
            fw("\tNumEvents %d,\n" % len(model.objects['eventobject']))
        if len(geoset_anims):
            fw("\tNumGeosetAnims %d,\n" % len(geoset_anims))
        if len(model.objects['light']):
            fw("\tNumLights %d,\n" % len(model.objects['light']))
        if len(model.objects['helper']):
            fw("\tNumHelpers %d,\n" % len(model.objects['helper']))
        fw("\tBlendTime %d,\n" % 150)
        fw("\tMinimumExtent {%s, %s, %s},\n" % tuple(map(f2s, model.global_extents_min)))
        fw("\tMaximumExtent {%s, %s, %s},\n" % tuple(map(f2s, model.global_extents_max)))
        fw("\tBoundsRadius %s,\n" % f2s(calc_bounds_radius(model.global_extents_min, model.global_extents_max)))
        fw("}\n")
        
        # SEQUENCES
        fw("Sequences %d {\n" % len(model.sequences))
        for sequence in model.sequences:
            fw("\tAnim \"%s\" {\n" % sequence.name)
            fw("\t\tInterval {%d, %d},\n" % (sequence.start, sequence.end))
            if sequence.non_looping:
                fw("\t\tNonLooping,\n")
            if 'walk' in sequence.name.lower():
                fw("\t\tMoveSpeed %d,\n" % sequence.movement_speed)
            
            fw("\t\tMinimumExtent {%s, %s, %s},\n" % tuple(map(f2s, model.global_extents_min)))
            fw("\t\tMaximumExtent {%s, %s, %s},\n" % tuple(map(f2s, model.global_extents_max)))
            fw("\t\tBoundsRadius %s,\n" % f2s(calc_bounds_radius(model.global_extents_min, model.global_extents_max)))
            fw("\t}\n")
        fw("}\n")
        
        # GLOBAL SEQUENCES
        global_seqs = sorted(model.global_seqs)
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
        if len(mdl_materials):
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
                        layer.alpha_anim.write_mdl("Alpha", fw, global_seqs, "\t\t") # write_anim(layer.alpha_anim, "Alpha", fw, global_seqs, "\t\t")
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
                    # write_anim_vec(uv_anim.translation, "Translation", 'translation', fw, global_seqs, Matrix(), Matrix(), "\t\t")
                    uv_anim.translation.write_mdl("Translation", fw, global_seqs, "\t\t")
                if uv_anim.rotation is not None:
                    # write_anim_euler(uv_anim.rotation, "Rotation", 'rotation', fw, global_seqs, "\t\t")
                    uv_anim.rotation.write_mdl("Rotation", fw, global_seqs, "\t\t")
                if uv_anim.scale is not None:
                    # write_anim_vec(uv_anim.scale, "Scaling", 'scale', fw, global_seqs, Matrix(), Matrix(), "\t\t")
                    uv_anim.scaling.write_mdl("Scaling", fw, global_seqs, "\t\t")
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
                
                for sequence in model.sequences:
                    fw("\tAnim {\n")
                    
                    # As of right now, we just use the geoset bounds. 
                    fw("\t\tMinimumExtent {%s, %s, %s},\n" % tuple(map(f2s, geoset.min_extent)))
                    fw("\t\tMaximumExtent {%s, %s, %s},\n" % tuple(map(f2s, geoset.max_extent)))
                    fw("\t\tBoundsRadius %s,\n" % f2s(calc_bounds_radius(geoset.min_extent, geoset.max_extent)))
                    
                    fw("\t}\n")
                
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
                    # write_anim(alpha, "Alpha", fw, global_seqs, "\t", True)
                    alpha.write_mdl("Alpha", fw, global_seqs, "\t")
                else:
                    fw("\tstatic Alpha 1.0,\n")
                    
                if vertexcolor_anim is not None:
                    # write_anim_vec(vertexcolor_anim, 'Color', 'color', fw, global_seqs, Matrix(), Matrix(), "\t", (2, 1, 0))
                    vertexcolor_anim.write_mdl("Color", fw, global_seqs, "\t")
                elif vertexcolor is not None:
                    fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(vertexcolor[:3]))))
                    
                fw("\tGeosetId %d,\n" % geosets.index(anim.geoset))

                fw("}\n")
            
        # BONES
        for bone in model.objects['bone']:
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
                
            if bone.name in model.geoset_anim_map.keys():
                fw("\tGeosetAnimId %d,\n" % geoset_anims.index(model.geoset_anim_map[bone.name]))
            else:
                fw("\tGeosetAnimId None,\n")
                
            if bone.anim_loc is not None:
                bone.anim_loc.write_mdl("Translation", fw, global_seqs, "\t") # write_anim_vec(bone.anim_loc, 'Translation', 'location', fw, global_seqs, global_matrix, bone.matrix)
                
            if bone.anim_rot is not None:
                bone.anim_rot.write_mdl("Rotation", fw, global_seqs, "\t") # write_anim_rot(bone.anim_rot, 'Rotation', 'rotation_quaternion', fw, global_seqs, bone.matrix, global_matrix)
                
            if bone.anim_scale is not None:
                bone.anim_scale.write_mdl("Scaling", fw, global_seqs, "\t") # write_anim_vec(bone.anim_scale, 'Scaling', 'scale', fw, global_seqs, Matrix(), Matrix())
                
            # Visibility
            fw("}\n")
            
        # LIGHTS
        for light in model.objects['light']:
            l = light.object
            fw("Light \"%s\" {\n" % light.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[light.name])
                
            if light.parent is not None:
                fw("\tParent %d,\n" % object_indices[light.parent])
               
            write_billboard(fw, light.billboarded, light.billboard_lock)
            
            fw("\t%s,\n" % light.type)
            
            if light.atten_start_anim is not None:
                light.atten_start_anim.write_mdl("AttenuationStart", fw, global_seqs, "\t") # write_anim(light.atten_start_anim, "AttenuationStart", fw, global_seqs, "\t")
            else:
                fw("\tstatic AttenuationStart %s,\n" % f2s(light.atten_start))
                
            if light.atten_end_anim is not None:
                light.atten_end_anim.write_mdl("AttenuationEnd", fw, global_seqs, "\t") # write_anim(light.atten_end_anim, "AttenuationEnd", fw, global_seqs, "\t")
            else:
                fw("\tstatic AttenuationEnd %s,\n" % f2s(light.atten_end)) #TODO: Add animation support
               
            if light.color_anim is not None:
                light.color_anim.write_mdl("Color", fw, global_seqs, "\t") # write_anim_vec(light.color_anim, "Color", 'color', fw, global_seqs, Matrix(), Matrix())
            else:
                fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(light.color[:3]))))
               
            if light.intensity_anim is not None:
                light.intensity_anim.write_mdl("Intensity", fw, global_seqs, "\t") # write_anim(light.intensity_anim, "Intensity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Intensity %s,\n" % f2s(light.intensity))
                
            if light.amb_intensity_anim is not None:
                light.amb_intensity_anim.write_mdl("AmbIntensity", fw, global_seqs, "\t") # write_anim(light.amb_intensity_anim, "AmbIntensity", fw, global_seqs, "\t")
            else:
                fw("\tstatic AmbIntensity %s,\n" % f2s(light.amb_intensity))
               
            if light.amb_color_anim is not None:
                light.amb_color_anim.write_mdl("AmbColor", fw, global_seqs, "\t") # write_anim_vec(light.amb_color_anim, "Color", 'color', fw, global_seqs, Matrix(), Matrix())
            else:
                fw("\tstatic AmbColor {%s, %s, %s},\n" % tuple(map(f2s, reversed(light.amb_color[:3]))))
                
            if light.visibility is not None:
                light.visibility.write_mdl("Visibility", fw, global_seqs, "\t") # write_anim(light.visibility, "Visibility", fw, global_seqs, "\t", True)
            fw("}\n")
                
                
        # HELPERS
        for helper in model.objects['helper']:
            fw("Helper \"%s\" {\n" % helper.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[helper.name])
                
            if helper.parent is not None:
                fw("\tParent %d,\n" % object_indices[helper.parent])
            
            if hasattr(helper, "billboarded"):
                write_billboard(fw, helper.billboarded, helper.billboard_lock)
            
            if helper.anim_loc is not None:
                helper.anim_loc.write_mdl("Translation", fw, global_seqs, "\t") # write_anim_vec(helper.anim_loc, 'Translation', 'location', fw, global_seqs, global_matrix, helper.matrix)
                
            if helper.anim_rot is not None:
                helper.anim_rot.write_mdl("Rotation", fw, global_seqs, "\t")# write_anim_rot(helper.anim_rot, 'Rotation', 'rotation_quaternion', fw, global_seqs, helper.matrix, global_matrix)
                
            if helper.anim_scale is not None:
                helper.anim_scale.write_mdl("Scaling", fw, global_seqs, "\t") # write_anim_vec(helper.anim_scale, 'Scaling', 'scale', fw, global_seqs, Matrix(), Matrix())
            
            fw("}\n")

            
        # ATTACHMENT POINTS   
        if len(model.objects['attachment']):
            for i, attachment in enumerate(model.objects['attachment']):
                fw("Attachment \"%s\" {\n" % attachment.name)
                
                if len(object_indices) > 1:
                    fw("\tObjectId %d,\n" % object_indices[attachment.name])
                    
                if attachment.parent is not None:
                    fw("\tParent %d,\n" % object_indices[attachment.parent])
                    
                write_billboard(fw, attachment.billboarded, attachment.billboard_lock)
                
                fw("\tAttachmentID %d,\n" % i)
                
                visibility = attachment.visibility
                if visibility is not None:
                    visibility.write_mdl("Visibility", fw, global_seqs, "\t") # write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
                fw("}\n")
            
        # PIVOT POINTS
        if len(objects_all):
            fw("PivotPoints %d {\n" % len(objects_all))
            for object in objects_all:
                fw("\t{%s, %s, %s},\n" % tuple(map(f2s, object.pivot)))
            fw("}\n")
            
        # MODEL EMITTERS
        for psys in model.objects['particle']:
            emitter = psys.emitter
            fw("ParticleEmitter \"%s\" {\n" % psys.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[psys.name])
            if psys.parent is not None:
                fw("\tParent %d,\n" % object_indices[psys.parent])
                
            fw("\tEmitterUsesMDL,\n")
            
            if psys.emission_rate_anim is not None:
                psys.emission_rate_anim.write_mdl("EmissionRate", fw, global_seqs, "\t") # write_anim(psys.emission_rate_anim, "EmissionRate", fw, global_seqs, "\t")
            else:
                fw("\tstatic EmissionRate %s,\n" % f2s(rnd(emitter.emission_rate)))
            
            if psys.gravity_anim is not None:
                psys.gravity_anim.write_mdl("Gravity", fw, global_seqs, "\t") # write_anim(psys.gravity_anim, "Gravity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Gravity %s,\n" % f2s(rnd(emitter.gravity)))
                
            if psys.longitude_anim is not None:
                psys.longitude_anim.write_mdl("Longitude", fw, global_seqs, "\t")# write_anim(psys.longitude_anim, "Longitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Longitude %s,\n" % f2s(rnd(emitter.latitude)))
            
            if psys.latitude_anim is not None:
                psys.latitude_anim.write_mdl("Latitude", fw, global_seqs, "\t") # write_anim(psys.latitude_anim, "Latitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Latitude %s,\n" % f2s(rnd(emitter.latitude)))
                
            visibility = psys.visibility
            if visibility is not None:
                visibility.write_mdl("Visibility", fw, global_seqs, "\t") # write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
            fw("\tParticle {\n")
            
            if psys.life_span_anim is not None:
                psys.life_span_anim.write_mdl("LifeSpan", fw, global_seqs, "\t")# write_anim(psys.life_span_anim, "LifeSpan", fw, global_seqs, "\t\t")
            else:
                fw("\t\tLifeSpan %s,\n" % f2s(rnd(emitter.life_span)))
              
            if psys.speed_anim is not None:
                psys.speed_anim.write_mdl("InitVelocity", fw, global_seqs, "\t") # write_anim(psys.speed_anim, "InitVelocity", fw, global_seqs, "\t\t")
            else:
                fw("\t\tstatic InitVelocity %s,\n" % f2s(rnd(emitter.speed)))

            fw("\t\tPath \"%s\",\n" % emitter.model_path)
            fw("\t}\n")
            fw("}\n")
         
        # PARTICLE EMITTERS
        for psys in model.objects['particle2']:
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
                psys.speed_anim.write_mdl("Speed", fw, global_seqs, "\t") # write_anim(psys.speed_anim, "Speed", fw, global_seqs, "\t")
            else:
                fw("\tstatic Speed %s,\n" % f2s(rnd(emitter.speed)))
                
            if psys.variation_anim is not None:
                psys.variation_anim.write_mdl("Variation", fw, global_seqs, "\t") # write_anim(psys.variation_anim, "Variation", fw, global_seqs, "\t")
            else:
                fw("\tstatic Variation %s,\n" % f2s(rnd(emitter.variation)))
                
            if psys.latitude_anim is not None:
                psys.latitude_anim.write_mdl("Latitude", fw, global_seqs, "\t") # write_anim(psys.latitude_anim, "Latitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Latitude %s,\n" % f2s(rnd(emitter.latitude)))
                
            if psys.gravity_anim is not None:
                psys.gravity_anim.write_mdl("Gravity", fw, global_seqs, "\t") # write_anim(psys.gravity_anim, "Gravity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Gravity %s,\n" % f2s(rnd(emitter.gravity)))
                
            visibility = psys.visibility
            if visibility is not None:
                visibility.write_mdl("Visibility", fw, global_seqs, "\t") # write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
                
            # if psys.life_span_anim is not None:
            #    psys.life_span_anim.write_mdl("LifeSpan", fw, global_seqs, "\t") # write_anim(psys.life_span_anim, "LifeSpan", fw, global_seqs, "\t")
            #else:
            fw("\tLifeSpan %s,\n" % f2s(rnd(emitter.life_span)))
                
            if psys.emission_rate_anim is not None:
                psys.emission_rate_anim.write_mdl("EmissionRate", fw, global_seqs, "\t") # write_anim(psys.emission_rate_anim, "EmissionRate", fw, global_seqs, "\t")
            else:
                fw("\tstatic EmissionRate %s,\n" % f2s(rnd(emitter.emission_rate)))
                
            # FIXME FIXME FIXME FIXME FIXME: Separate X and Y channels! New animation class won't handle this. 
            if psys.scale_anim is not None and ('scale', 1) in psys.scale_anim.keys():
                psys.scale_anim.write_mdl("Width", fw, global_seqs, "\t") # write_anim(psys.scale_anim[('scale', 1)], "Width", fw, global_seqs, "\t", scale=psys.dimensions[1])
            else:
                fw("\tstatic Width %s,\n" % f2s(rnd(psys.dimensions[1])))
               
            if psys.scale_anim is not None and ('scale', 0) in psys.scale_anim.keys():
                psys.scale_anim.write_mdl("Length", fw, global_seqs, "\t") # write_anim(psys.scale_anim[('scale', 0)], "Length", fw, global_seqs, "\t", scale=psys.dimensions[0])
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
        for psys in model.objects['ribbon']:
            emitter = psys.emitter
            fw("RibbonEmitter \"%s\" {\n" % psys.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[psys.name])
            if psys.parent is not None:
                fw("\tParent %d,\n" % object_indices[psys.parent])
                
            fw("\tstatic HeightAbove %s,\n" % f2s(rnd(psys.dimensions[0]/2)))
            fw("\tstatic HeightBelow %s,\n" % f2s(rnd(psys.dimensions[0]/2)))
            
            if psys.alpha_anim is not None:
                psys.alpha_anim.write_mdl("Alpha", fw, global_seqs, "\t")
            else:
                fw("\tstatic Alpha %s,\n" % emitter.alpha)
            
            if psys.ribbon_color_anim is not None:
                psys.ribbon_color_anim.write_mdl("Color", fw, global_seqs, "\t")# write_anim_vec(psys.ribbon_color_anim, 'Color', 'ribbon_color', fw, global_seqs, Matrix(), Matrix(), "\t", (2, 1, 0))
            else:
                fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(emitter.ribbon_color))))
                
            fw("\tstatic TextureSlot %d,\n" % textures.index(emitter.texture_path))
            visibility = psys.visibility
            if visibility is not None:
                visibility.write_mdl("Visibility", fw, global_seqs, "\t") # write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
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
        for camera in model.cameras:
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
        for event in model.objects['eventobject']:
            fw("EventObject \"%s\" {\n" % event.name)
            if len(object_indices) > 1:
                fw("\tObjectId %d,\n" % object_indices[event.name])
            if event.parent is not None:
                fw("\tParent %d,\n" % object_indices[event.parent])
            eventtrack = event.track
            if eventtrack is not None:
                eventtrack.write_mdl("EventTrack", fw, global_seqs, "\t")
                
                #fw("\tEventTrack %d {\n" % len(eventtrack.keyframe_points))
                #for keyframe in eventtrack.keyframe_points:
                #    fw("\t\t%d,\n" % (f2ms * int(keyframe.co[0])))
                #fw("\t}\n")
            fw("}\n")
         
        # COLLISION SHAPES
        for collider in model.objects['collisionshape']:
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
                
                
    