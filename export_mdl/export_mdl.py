import itertools
import getpass
import datetime

from .classes.War3Model import War3Model
    
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

class MDLWriter:
    def __init__(self, path):
        self.indentation = 0
        self.file = open(path, 'w')
        pass

    def __del__(self):
        self.file.close()

    def comment(self, value):
        self.file.write("%s// %s\n" % ("\t" * self.indentation, value))

    def write(self, value):
        self.file.write("%s%s,\n" % ("\t" * self.indentation, value))

    def begin_scope(self, name, value = None):
        if (value is not None):
            self.file.write("%s%s %s {\n" % ("\t" * self.indentation, name, value))
        else:
            self.file.write("%s%s {\n" % ("\t" * self.indentation, name))
        
        self.indentation += 1

    def end_scope(self):
        self.indentation -= 1
        self.file.write("%s}\n" % ("\t" * self.indentation))
  
def write_billboard(writer, billboarded, billboard_lock):
    for flag, axis in zip(billboard_lock, ('Z', 'Y', 'X')):
        if flag == True:
            writer.write("BillboardedLock%s" % axis)
    if billboarded == True:
        writer.write("Billboarded")
    
def save(operator, context, settings, filepath="", mdl_version=800):
        
    scene = context.scene
    
    current_frame = scene.frame_current
    scene.frame_set(0)
    
    model = War3Model(context)
    model.from_scene(context, settings, operator.report)
    
    scene.frame_set(current_frame)

    writer = MDLWriter(filepath)
    
    date = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
    writer.comment("// Exported on %s by %s" % (date, getpass.getuser()))
    
    writer.begin_scope("Version")
    writer.write("FormatVersion %d" % mdl_version)
    writer.end_scope()

    # HEADER
    writer.begin_scope("Model", '"%s"' % model.name)
    if len(model.geosets):
        writer.write("NumGeosets %d" % len(model.geosets))
    if len(model.objects['bone']):
        writer.write("NumBones %d" % len(model.objects['bone']))
    if len(model.objects['attachment']):
        writer.write("NumAttachments %d" % len(model.objects['attachment']))
    if len(model.objects['particle']): 
        writer.write("NumParticleEmitters %d" % len(model.objects['particle']))
    if len(model.objects['particle2']): 
        writer.write("NumParticleEmitters2 %d" % len(model.objects['particle2']))
    if len(model.objects['ribbon']): 
        writer.write("NumRibbonEmitters %d" % len(model.objects['ribbon']))
    if len(model.objects['eventobject']):
        writer.write("NumEvents %d" % len(model.objects['eventobject']))
    if len(model.geoset_anims):
        writer.write("NumGeosetAnims %d" % len(model.geoset_anims))
    if len(model.objects['light']):
        writer.write("NumLights %d" % len(model.objects['light']))
    if len(model.objects['helper']):
        writer.write("NumHelpers %d" % len(model.objects['helper']))
    writer.write("BlendTime %d" % 150)
    writer.write("MinimumExtent {%s, %s, %s}" % tuple(map(f2s, model.global_extents_min)))
    writer.write("MaximumExtent {%s, %s, %s}" % tuple(map(f2s, model.global_extents_max)))
    writer.write("BoundsRadius %s" % f2s(calc_bounds_radius(model.global_extents_min, model.global_extents_max)))
    writer.end_scope()
    
    # SEQUENCES
    writer.begin_scope("Sequences", "%d" % len(model.sequences))

    for sequence in model.sequences:
        writer.begin_scope("Anim", "\"%s\"" % sequence.name)
        writer.write("Interval {%d, %d}" % (sequence.start, sequence.end))
        if sequence.non_looping:
            writer.write("NonLooping")
        if 'walk' in sequence.name.lower():
            writer.write("MoveSpeed %d" % sequence.movement_speed)
        
        writer.write("MinimumExtent {%s, %s, %s}" % tuple(map(f2s, model.global_extents_min)))
        writer.write("MaximumExtent {%s, %s, %s}" % tuple(map(f2s, model.global_extents_max)))
        writer.write("BoundsRadius %s" % f2s(calc_bounds_radius(model.global_extents_min, model.global_extents_max)))
        writer.end_scope()
    writer.end_scope()
    
    # GLOBAL SEQUENCES
    if len(model.global_seqs):
        writer.begin_scope("GlobalSequences", "%d" % len(model.global_seqs))
        for sequence in model.global_seqs:
            writer.write("Duration %d" % sequence)
        writer.end_scope()
    
    # TEXTURES
    if len(model.textures):
        writer.begin_scope("Textures", "%d" % len(model.textures))
        for texture in model.textures:
            writer.begin_scope("Bitmap")
            
            if texture.is_replaceable:
                writer.write("Image \"\"")
                writer.write("ReplaceableId %d" % texture.replaceable_id)
            else:
                writer.write("Image \"%s\"" % texture.image_path)

            writer.write("WrapHeight")
            writer.write("WrapWidth")
            writer.end_scope()
        writer.end_scope()
    
    # MATERIALS
    if len(model.materials):
        writer.begin_scope("Materials", "%d" % len(model.materials))
        for material in model.materials:
            writer.begin_scope("Material")
            
            if material.use_const_color is True:
                writer.write("ConstantColor")
                
            # SortPrimsFarZ,
            # FullResolution,
            
            if material.priority_plane != 0:
                writer.write("PriorityPlane %d" % material.priority_plane)
            
            for layer in material.layers:
                writer.begin_scope("Layer")
                writer.write("FilterMode %s" % layer.filter_mode)

                if layer.unshaded is True:
                    writer.write("Unshaded")
                    
                if layer.two_sided is True:
                    writer.write("TwoSided")
                
                if layer.unfogged is True:
                    writer.write("Unfogged")
                    
                if layer.no_depth_test is True:
                    writer.write("NoDepthTest")
                    
                if layer.no_depth_set is True:
                    writer.write("NoDepthSet")
                    
                if layer.texture_id is not None:
                    writer.write("static TextureID %d" % layer.texture_id)
                else:
                    writer.write("static TextureID 0")
                    
                if layer.texture_anim is not None:
                    writer.write("TVertexAnimId %d" % model.tvertex_anims.index(layer.texture_anim))
                if layer.alpha_anim is not None:
                    layer.alpha_anim.write_mdl("Alpha", writer, model)
                else:
                    writer.write("static Alpha %s" % f2s(layer.alpha_value))
                    
                writer.end_scope()
            writer.end_scope()
        writer.end_scope()
    
    # TEXTURE ANIMATIONS
    if len(model.tvertex_anims):
        writer.begin_scope("TextureAnims", "%d" % len(model.tvertex_anims))
        for uv_anim in model.tvertex_anims:
            writer.begin_scope("TVertexAnim")
            if uv_anim.translation is not None:
                uv_anim.translation.write_mdl("Translation", writer, model)
                
            if uv_anim.rotation is not None:
                uv_anim.rotation.write_mdl("Rotation", writer, model)
                
            if uv_anim.scale is not None:
                uv_anim.scaling.write_mdl("Scaling", writer, model)
                
            writer.end_scope()
        writer.end_scope()
    
    material_names = [mat.name for mat in model.materials]
    
    # GEOSETS
    if len(model.geosets):
        for geoset in model.geosets:
            writer.begin_scope("Geoset")
            # Vertices
            writer.begin_scope("Vertices", "%d" % len(geoset.vertices))
            for vertex in geoset.vertices:
                writer.write("{%s, %s, %s}" % tuple(map(f2s, vertex[0])))
            writer.end_scope()
            # Normals
            writer.begin_scope("Normals", "%d" % len(geoset.vertices))
            for normal in geoset.vertices:
                writer.write("{%s, %s, %s}" % tuple(map(f2s, normal[1])))
            writer.end_scope()
            
            # TVertices
            writer.begin_scope("TVertices", "%d" % len(geoset.vertices))
            for tvertex in geoset.vertices:
                writer.write("{%s, %s}" % tuple(map(f2s, tvertex[2])))
            writer.end_scope()
            
            # VertexGroups
            writer.begin_scope("VertexGroup")
            for vertgroup in geoset.vertices:
                writer.write("%d" % vertgroup[3])
            writer.end_scope()
            
            # Faces
            writer.begin_scope("Faces", "%d %d" % (len(geoset.triangles), len(geoset.triangles) * 3))
            writer.begin_scope("Triangles")
            for triangle in geoset.triangles:
                writer.write("{%d, %d, %d}" % triangle[:])
                
            writer.end_scope()
            writer.end_scope()
            
            writer.begin_scope("Groups", "%d %d" % (len(geoset.matrices), sum(len(mtrx) for mtrx in geoset.matrices)))
            for matrix in geoset.matrices:
                writer.write("Matrices {%s}" % ','.join(str(model.object_indices[g]) for g in matrix))
            writer.end_scope()
            
            writer.write("MinimumExtent {%s, %s, %s}" % tuple(map(f2s, geoset.min_extent)))
            writer.write("MaximumExtent {%s, %s, %s}" % tuple(map(f2s, geoset.max_extent)))
            writer.write("BoundsRadius %s" % f2s(calc_bounds_radius(geoset.min_extent, geoset.max_extent)))
            
            for sequence in model.sequences:
                writer.begin_scope("Anim")
                
                # As of right now, we just use the geoset bounds. 
                writer.write("MinimumExtent {%s, %s, %s}" % tuple(map(f2s, geoset.min_extent)))
                writer.write("MaximumExtent {%s, %s, %s}" % tuple(map(f2s, geoset.max_extent)))
                writer.write("BoundsRadius %s" % f2s(calc_bounds_radius(geoset.min_extent, geoset.max_extent)))
                
                writer.end_scope()
            
            writer.write("MaterialID %d" % material_names.index(geoset.mat_name))

            writer.end_scope()

        
    # GEOSET ANIMS
    if len(model.geoset_anims):
        for anim in model.geoset_anims:
            writer.begin_scope("GeosetAnim")
            alpha = anim.alpha_anim
            vertexcolor = anim.color
            vertexcolor_anim = anim.color_anim
            if alpha is not None:
                alpha.write_mdl("Alpha", writer, model)
            else:
                writer.write("static Alpha 1.0")
                
            if vertexcolor_anim is not None:
                vertexcolor_anim.write_mdl("Color", writer, model)
            elif vertexcolor is not None:
                writer.write("static Color {%s, %s, %s}" % tuple(map(f2s, reversed(vertexcolor[:3]))))
                
            writer.write("GeosetId %d" % model.geosets.index(anim.geoset))

            writer.end_scope()
        
    # BONES
    for bone in model.objects['bone']:
        name = bone.name.replace('.', '_')
        if not name.lower().startswith("bone"):
            name = "Bone_"+name
            
        writer.begin_scope("Bone", "\"%s\"" % name)
        if len(model.object_indices) > 1:
            writer.write("ObjectId %d" % model.object_indices[bone.name])
        if bone.parent is not None:
            writer.write("Parent %d" % model.object_indices[bone.parent])
        
        if hasattr(bone, "billboarded"):
            write_billboard(writer, bone.billboarded, bone.billboard_lock)
        
        children = [g for g in model.geosets if bone.name in itertools.chain.from_iterable(g.matrices)]
        if len(children) == 1:
            writer.write("GeosetId %d" % model.geosets.index(children[0]))
        else:
            writer.write("GeosetId -1")
            
        if bone.name in model.geoset_anim_map.keys():
            writer.write("GeosetAnimId %d" % model.geoset_anims.index(model.geoset_anim_map[bone.name]))
        else:
            writer.write("GeosetAnimId None")
            
        if bone.anim_loc is not None:
            bone.anim_loc.write_mdl("Translation", writer, model)
            
        if bone.anim_rot is not None:
            bone.anim_rot.write_mdl("Rotation", writer, model)
            
        if bone.anim_scale is not None:
            bone.anim_scale.write_mdl("Scaling", writer, model)
            
        # Visibility
        writer.end_scope()
        
    # LIGHTS
    for light in model.objects['light']:
        writer.begin_scope("Light", "\"%s\"" % light.name)
        if len(model.object_indices) > 1:
            writer.write("ObjectId %d" % model.object_indices[light.name])
            
        if light.parent is not None:
            writer.write("Parent %d" % model.object_indices[light.parent])
            
        write_billboard(writer, light.billboarded, light.billboard_lock)
        
        writer.write("%s" % light.type)
        
        if light.atten_start_anim is not None:
            light.atten_start_anim.write_mdl("AttenuationStart", writer, model)
        else:
            writer.write("static AttenuationStart %s" % f2s(light.atten_start))
            
        if light.atten_end_anim is not None:
            light.atten_end_anim.write_mdl("AttenuationEnd", writer, model)
        else:
            writer.write("static AttenuationEnd %s" % f2s(light.atten_end)) #TODO: Add animation support
            
        if light.color_anim is not None:
            light.color_anim.write_mdl("Color", writer, model)
        else:
            writer.write("static Color {%s, %s, %s}" % tuple(map(f2s, reversed(light.color[:3]))))
            
        if light.intensity_anim is not None:
            light.intensity_anim.write_mdl("Intensity", writer, model)
        else:
            writer.write("static Intensity %s" % f2s(light.intensity))
            
        if light.amb_intensity_anim is not None:
            light.amb_intensity_anim.write_mdl("AmbIntensity", writer, model)
        else:
            writer.write("static AmbIntensity %s" % f2s(light.amb_intensity))
            
        if light.amb_color_anim is not None:
            light.amb_color_anim.write_mdl("AmbColor", writer, model) 
        else:
            writer.write("static AmbColor {%s, %s, %s}" % tuple(map(f2s, reversed(light.amb_color[:3]))))
            
        if light.visibility is not None:
            light.visibility.write_mdl("Visibility", writer, model)
        writer.end_scope()
            
            
    # HELPERS
    for helper in model.objects['helper']:
        name = helper.name.replace('.', '_')
        
        if not name.lower().startswith("bone"):
            name = "Bone_"+name
    
        writer.begin_scope("Helper", "\"%s\"" % name)
        if len(model.object_indices) > 1:
            writer.write("ObjectId %d" % model.object_indices[helper.name])
            
        if helper.parent is not None:
            writer.write("Parent %d" % model.object_indices[helper.parent])
        
        if hasattr(helper, "billboarded"):
            write_billboard(writer, helper.billboarded, helper.billboard_lock)
        
        if helper.anim_loc is not None:
            helper.anim_loc.write_mdl("Translation", writer, model)
            
        if helper.anim_rot is not None:
            helper.anim_rot.write_mdl("Rotation", writer, model)
            
        if helper.anim_scale is not None:
            helper.anim_scale.write_mdl("Scaling", writer, model)
        
        writer.end_scope()

        
    # ATTACHMENT POINTS   
    if len(model.objects['attachment']):
        for i, attachment in enumerate(model.objects['attachment']):
            writer.begin_scope("Attachment", "\"%s\"" % attachment.name)
            
            if len(model.object_indices) > 1:
                writer.write("ObjectId %d" % model.object_indices[attachment.name])
                
            if attachment.parent is not None:
                writer.write("Parent %d" % model.object_indices[attachment.parent])
                
            write_billboard(writer, attachment.billboarded, attachment.billboard_lock)
            
            writer.write("AttachmentID %d" % i)
            
            visibility = attachment.visibility
            if visibility is not None:
                visibility.write_mdl("Visibility", writer, model)
            writer.end_scope()
        
    # PIVOT POINTS
    if len(model.objects_all):
        writer.begin_scope("PivotPoints", "%d" % len(model.objects_all))
        for object in model.objects_all:
            writer.write("{%s, %s, %s}" % tuple(map(f2s, object.pivot)))
        writer.end_scope()
        
    # MODEL EMITTERS
    for psys in model.objects['particle']:
        writer.begin_scope("ParticleEmitter", "\"%s\"" % psys.name)
        if len(model.object_indices) > 1:
            writer.write("ObjectId %d" % model.object_indices[psys.name])
        if psys.parent is not None:
            writer.write("Parent %d" % model.object_indices[psys.parent])
            
        writer.write("EmitterUsesMDL")
        
        if psys.emission_rate_anim is not None:
            psys.emission_rate_anim.write_mdl("EmissionRate", writer, model)
        else:
            writer.write("static EmissionRate %s" % f2s(rnd(psys.emission_rate)))
        
        if psys.gravity_anim is not None:
            psys.gravity_anim.write_mdl("Gravity", writer, model)
        else:
            writer.write("static Gravity %s" % f2s(rnd(psys.gravity)))
            
        if psys.longitude_anim is not None:
            psys.longitude_anim.write_mdl("Longitude", writer, model)
        else:
            writer.write("static Longitude %s" % f2s(rnd(psys.latitude)))
        
        if psys.latitude_anim is not None:
            psys.latitude_anim.write_mdl("Latitude", writer, model)
        else:
            writer.write("static Latitude %s" % f2s(rnd(psys.latitude)))
            
        visibility = psys.visibility
        if visibility is not None:
            visibility.write_mdl("Visibility", writer, model)
        writer.begin_scope("Particle")
        
        if psys.life_span_anim is not None:
            psys.life_span_anim.write_mdl("LifeSpan", writer, model)
        else:
            writer.write("LifeSpan %s" % f2s(rnd(psys.life_span)))
            
        if psys.speed_anim is not None:
            psys.speed_anim.write_mdl("InitVelocity", writer, model)
        else:
            writer.write("static InitVelocity %s" % f2s(rnd(psys.speed)))

        writer.write("Path \"%s\"" % psys.model_path)
        writer.end_scope()
        writer.end_scope()
        
    # PARTICLE EMITTERS
    for psys in model.objects['particle2']:
        writer.begin_scope("ParticleEmitter2", "\"%s\"" % psys.name)
        if len(model.object_indices) > 1:
            writer.write("ObjectId %d" % model.object_indices[psys.name])
        if psys.parent is not None:
            writer.write("Parent %d" % model.object_indices[psys.parent])
            
        if psys.sort_far_z:
            writer.write("SortPrimsFarZ")
            
        if psys.unshaded:
            writer.write("Unshaded")
            
        if psys.line_emitter:
            writer.write("LineEmitter")
        
        if psys.unfogged:
            writer.write("Unfogged")
            
        if psys.model_space:
            writer.write("ModelSpace")
            
        if psys.xy_quad:
            writer.write("XYQuad")
            
        if psys.speed_anim is not None:
            psys.speed_anim.write_mdl("Speed", writer, model)
        else:
            writer.write("static Speed %s" % f2s(rnd(psys.speed)))
            
        if psys.variation_anim is not None:
            psys.variation_anim.write_mdl("Variation", writer, model)
        else:
            writer.write("static Variation %s" % f2s(rnd(psys.variation)))
            
        if psys.latitude_anim is not None:
            psys.latitude_anim.write_mdl("Latitude", writer, model)
        else:
            writer.write("static Latitude %s" % f2s(rnd(psys.latitude)))
            
        if psys.gravity_anim is not None:
            psys.gravity_anim.write_mdl("Gravity", writer, model)
        else:
            writer.write("static Gravity %s" % f2s(rnd(psys.gravity)))
            
        visibility = psys.visibility
        if visibility is not None:
            visibility.write_mdl("Visibility", writer, model)
            
        writer.write("LifeSpan %s" % f2s(rnd(psys.life_span)))
            
        if psys.emission_rate_anim is not None:
            psys.emission_rate_anim.write_mdl("EmissionRate", writer, model)
        else:
            writer.write("static EmissionRate %s" % f2s(rnd(psys.emission_rate)))
            
        # FIXME FIXME FIXME FIXME FIXME: Separate X and Y channels! New animation class won't handle this. 
        if psys.scale_anim is not None and ('scale', 1) in psys.scale_anim.keys():
            psys.scale_anim.write_mdl("Width", writer, model)
        else:
            writer.write("static Width %s" % f2s(rnd(psys.dimensions[1])))
            
        if psys.scale_anim is not None and ('scale', 0) in psys.scale_anim.keys():
            psys.scale_anim.write_mdl("Length", writer, model)
        else:
            writer.write("static Length %s" % f2s(rnd(psys.dimensions[0])))
            
        writer.write(psys.filter_mode)
        writer.write("Rows %d" % psys.rows)
        writer.write("Columns %d" % psys.cols)
        if psys.head and psys.tail:
            writer.write("Both")
        elif psys.tail:
            writer.write("Tail")
        else:
            writer.write("Head")
            
        writer.write("TailLength %s" % f2s(rnd(psys.tail_length)))
        writer.write("Time %s" % f2s(rnd(psys.time)))
        writer.begin_scope("SegmentColor")
        writer.write("Color {%s, %s, %s}" % tuple(map(f2s, reversed(psys.start_color))))
        writer.write("Color {%s, %s, %s}" % tuple(map(f2s, reversed(psys.mid_color))))
        writer.write("Color {%s, %s, %s}" % tuple(map(f2s, reversed(psys.end_color))))
        writer.end_scope()
        alpha = (psys.start_alpha, psys.mid_alpha, psys.end_alpha)
        writer.write("Alpha {%s, %s, %s}" % tuple(map(f2s, alpha)))
        particle_scales = (psys.start_scale, psys.mid_scale, psys.end_scale)
        writer.write("ParticleScaling {%s, %s, %s}" % tuple(map(f2s, particle_scales)))
        writer.write("LifeSpanUVAnim {%d, %d, %d}" % (psys.head_life_start, psys.head_life_end, psys.head_life_repeat))
        writer.write("DecayUVAnim {%d, %d, %d}" % (psys.head_decay_start, psys.head_decay_end, psys.head_decay_repeat))
        writer.write("TailUVAnim {%d, %d, %d}" % (psys.tail_life_start, psys.tail_life_end, psys.tail_life_repeat))
        writer.write("TailDecayUVAnim {%d, %d, %d}" % (psys.tail_decay_start, psys.tail_decay_end, psys.tail_decay_repeat))
        writer.write("TextureID %d" % model.textures[psys.texture_id])
        if psys.priority_plane != 0:
            writer.write("PriorityPlane %d" % psys.priority_plane)
        writer.end_scope()
        
    # RIBBON EMITTERS
    for psys in model.objects['ribbon']:
        writer.begin_scope("RibbonEmitter", "\"%s\"" % psys.name)
        if len(model.object_indices) > 1:
            writer.write("ObjectId %d" % model.object_indices[psys.name])
        if psys.parent is not None:
            writer.write("Parent %d" % model.object_indices[psys.parent])
            
        writer.write("static HeightAbove %s" % f2s(rnd(psys.dimensions[0]/2)))
        writer.write("static HeightBelow %s" % f2s(rnd(psys.dimensions[0]/2)))
        
        if psys.alpha_anim is not None:
            psys.alpha_anim.write_mdl("Alpha", writer, model)
        else:
            writer.write("static Alpha %s" % psys.alpha)
        
        if psys.ribbon_color_anim is not None:
            psys.ribbon_color_anim.write_mdl("Color", writer, model)
        else:
            writer.write("static Color {%s, %s, %s}" % tuple(map(f2s, reversed(psys.ribbon_color))))
            
        writer.write("static TextureSlot %d" % model.textures[psys.texture_id])
        visibility = psys.visibility
        if visibility is not None:
            visibility.write_mdl("Visibility", writer, model)
        writer.write("EmissionRate %d" % psys.emission_rate)
        writer.write("LifeSpan %s" % f2s(rnd(psys.life_span)))
        writer.write("Gravity %s" % f2s(rnd(psys.gravity)))
        writer.write("Rows %d" % psys.rows)
        writer.write("Columns %d" % psys.cols)
        for material in model.materials:
            if material.name == psys.ribbon_material.name:
                writer.write("MaterialID %d" % model.materials.index(material))
                break
        writer.end_scope()
        
    # CAMERAS    
    for camera in model.cameras:
        writer.begin_scope("Camera", "\"%s\"" % camera.name)
        writer.write("Position {%s, %s, %s}" % tuple(map(f2s, camera.pivot)))
        writer.write("FieldOfView %f" % camera.field_of_view)
        writer.write("FarClip %f" % (camera.far_clip))
        writer.write("NearClip %f" % (camera.near_clip))
        writer.begin_scope("Target")
        writer.write("Position {%s, %s, %s}" % tuple(map(f2s, camera.target)))
        writer.end_scope()
        writer.end_scope()
        
    # EVENT OBJECTS
    for event in model.objects['eventobject']:
        writer.begin_scope("EventObject", "\"%s\"" % event.name)
        if len(model.object_indices) > 1:
            writer.write("ObjectId %d" % model.object_indices[event.name])
        if event.parent is not None:
            writer.write("Parent %d" % model.object_indices[event.parent])
        eventtrack = event.track
        if eventtrack is not None:
            eventtrack.write_mdl("EventTrack", writer, model)
            
        writer.end_scope()
        
    # COLLISION SHAPES
    for collider in model.objects['collisionshape']:
        writer.begin_scope("CollisionShape" ,"\"%s\"" % collider.name)
        writer.write("ObjectId %d" % model.object_indices[collider.name])
        if collider.parent is not None:
            writer.write("Parent %d" % model.object_indices[collider.parent])
        if collider.type == 'Box':
            writer.write("Box")
        else:
            writer.write("Sphere")
            
        writer.begin_scope("Vertices", "%d" % len(collider.verts))
        for vert in collider.verts:
            writer.write("{%s, %s, %s}" % tuple(f2s(rnd(x)) for x in vert))
        writer.end_scope()
        if collider.type == 'Sphere':
            writer.write("BoundsRadius %s" % f2s(rnd(collider.radius)))
        writer.end_scope()
                
                
    