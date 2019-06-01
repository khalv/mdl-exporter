import bpy
import itertools
import math
import getpass
import datetime

from mathutils import Vector

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
  
def write_billboard(fw, billboarded, billboard_lock):
    for flag, axis in zip(billboard_lock, ('Z', 'Y', 'X')):
        if flag == True:
            fw("\tBillboardedLock%s,\n" % axis)
    if billboarded == True:
        fw("\tBillboarded,\n")
    
def save(operator, context, settings, filepath="", mdl_version=800):
        
    scene = context.scene
    
    current_frame = scene.frame_current
    scene.frame_set(0)
    
    model = War3Model(context)
    model.from_scene(context, settings)
    
    scene.frame_set(current_frame)
    
    with open(filepath, 'w') as output:
        fw = output.write
        
        date = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        fw("// Exported on %s by %s\n" % (date, getpass.getuser()))
        
        fw("Version {\n\tFormatVersion %d,\n}\n" % mdl_version)
        # HEADER
        fw("Model \"%s\" {\n" % model.name)
        if len(model.geosets):
            fw("\tNumGeosets %d,\n" % len(model.geosets))
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
        if len(model.geoset_anims):
            fw("\tNumGeosetAnims %d,\n" % len(model.geoset_anims))
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
        # global_seqs = sorted(model.global_seqs)
        if len(model.global_seqs):
            fw("GlobalSequences %d {\n" % len(model.global_seqs))
            for sequence in model.global_seqs:
                fw("\tDuration %d,\n" % sequence)
            fw("}\n")
        
        # TEXTURES
        if len(model.textures):
            fw("Textures %d {\n" % len(model.textures))
            for texture in model.textures:
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
        if len(model.materials):
            fw("Materials %d {\n" % len(model.materials))
            for material in model.materials:
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
                        fw("\t\t\tstatic TextureID %d,\n" % model.textures.index(layer.texture))    
                    else:
                        fw("\t\t\tstatic TextureID 0,\n")  
                        
                    if layer.texture_anim is not None:
                        fw("\t\t\tTVertexAnimId %d,\n" % model.tvertex_anims.index(layer.texture_anim))
                    if layer.alpha_anim is not None:
                        layer.alpha_anim.write_mdl("Alpha", fw, model.global_seqs, "\t\t") # write_anim(layer.alpha_anim, "Alpha", fw, global_seqs, "\t\t")
                    else:
                        fw("\t\t\tstatic Alpha %s,\n" % f2s(layer.alpha_value))
                        
                    fw("\t\t}\n")
                fw("\t}\n")
            fw("}\n")
        
        # TEXTURE ANIMATIONS
        if len(model.tvertex_anims):
            fw("TextureAnims %d {\n" % len(model.tvertex_anims))
            for uv_anim in model.tvertex_anims:
                fw("\tTVertexAnim {\n")
                if uv_anim.translation is not None:
                    uv_anim.translation.write_mdl("Translation", fw, model.global_seqs, "\t\t")
                    
                if uv_anim.rotation is not None:
                    uv_anim.rotation.write_mdl("Rotation", fw, model.global_seqs, "\t\t")
                    
                if uv_anim.scale is not None:
                    uv_anim.scaling.write_mdl("Scaling", fw, model.global_seqs, "\t\t")
                    
                fw("\t}\n")
            fw("}\n")
        
        material_names = [mat.name for mat in model.materials]
        
        # GEOSETS
        if len(model.geosets):
            for geoset in model.geosets:
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
                    fw("\t\tMatrices {%s},\n" % ','.join(str(model.object_indices[g]) for g in matrix))
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
        if len(model.geoset_anims):
            for anim in model.geoset_anims:
                fw("GeosetAnim {\n")
                alpha = anim.alpha_anim
                vertexcolor = anim.color
                vertexcolor_anim = anim.color_anim
                if alpha is not None:
                    alpha.write_mdl("Alpha", fw, model.global_seqs, "\t")
                else:
                    fw("\tstatic Alpha 1.0,\n")
                    
                if vertexcolor_anim is not None:
                    vertexcolor_anim.write_mdl("Color", fw, model.global_seqs, "\t")
                elif vertexcolor is not None:
                    fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(vertexcolor[:3]))))
                    
                fw("\tGeosetId %d,\n" % model.geosets.index(anim.geoset))

                fw("}\n")
            
        # BONES
        for bone in model.objects['bone']:
            name = bone.name.replace('.', '_')
            if not name.lower().startswith("bone"):
                name = "Bone_"+name
                
            fw("Bone \"%s\" {\n" % name)
            if len(model.object_indices) > 1:
                fw("\tObjectId %d,\n" % model.object_indices[bone.name])
            if bone.parent is not None:
                fw("\tParent %d,\n" % model.object_indices[bone.parent])
            
            if hasattr(bone, "billboarded"):
                write_billboard(fw, bone.billboarded, bone.billboard_lock)
            
            children = [g for g in model.geosets if bone.name in itertools.chain.from_iterable(g.matrices)]
            if len(children) == 1:
                fw("\tGeosetId %d,\n" % model.geosets.index(children[0]))
            else:
                fw("\tGeosetId -1,\n")
                
            if bone.name in model.geoset_anim_map.keys():
                fw("\tGeosetAnimId %d,\n" % model.geoset_anims.index(model.geoset_anim_map[bone.name]))
            else:
                fw("\tGeosetAnimId None,\n")
                
            if bone.anim_loc is not None:
                bone.anim_loc.write_mdl("Translation", fw, model.global_seqs, "\t")
                
            if bone.anim_rot is not None:
                bone.anim_rot.write_mdl("Rotation", fw, model.global_seqs, "\t")
                
            if bone.anim_scale is not None:
                bone.anim_scale.write_mdl("Scaling", fw, model.global_seqs, "\t")
                
            # Visibility
            fw("}\n")
            
        # LIGHTS
        for light in model.objects['light']:
            l = light.object
            fw("Light \"%s\" {\n" % light.name)
            if len(model.object_indices) > 1:
                fw("\tObjectId %d,\n" % model.object_indices[light.name])
                
            if light.parent is not None:
                fw("\tParent %d,\n" % model.object_indices[light.parent])
               
            write_billboard(fw, light.billboarded, light.billboard_lock)
            
            fw("\t%s,\n" % light.type)
            
            if light.atten_start_anim is not None:
                light.atten_start_anim.write_mdl("AttenuationStart", fw, model.global_seqs, "\t") # write_anim(light.atten_start_anim, "AttenuationStart", fw, global_seqs, "\t")
            else:
                fw("\tstatic AttenuationStart %s,\n" % f2s(light.atten_start))
                
            if light.atten_end_anim is not None:
                light.atten_end_anim.write_mdl("AttenuationEnd", fw, model.global_seqs, "\t") # write_anim(light.atten_end_anim, "AttenuationEnd", fw, global_seqs, "\t")
            else:
                fw("\tstatic AttenuationEnd %s,\n" % f2s(light.atten_end)) #TODO: Add animation support
               
            if light.color_anim is not None:
                light.color_anim.write_mdl("Color", fw, model.global_seqs, "\t") # write_anim_vec(light.color_anim, "Color", 'color', fw, global_seqs, Matrix(), Matrix())
            else:
                fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(light.color[:3]))))
               
            if light.intensity_anim is not None:
                light.intensity_anim.write_mdl("Intensity", fw, model.global_seqs, "\t") # write_anim(light.intensity_anim, "Intensity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Intensity %s,\n" % f2s(light.intensity))
                
            if light.amb_intensity_anim is not None:
                light.amb_intensity_anim.write_mdl("AmbIntensity", fw, model.global_seqs, "\t") # write_anim(light.amb_intensity_anim, "AmbIntensity", fw, global_seqs, "\t")
            else:
                fw("\tstatic AmbIntensity %s,\n" % f2s(light.amb_intensity))
               
            if light.amb_color_anim is not None:
                light.amb_color_anim.write_mdl("AmbColor", fw, model.global_seqs, "\t") # write_anim_vec(light.amb_color_anim, "Color", 'color', fw, global_seqs, Matrix(), Matrix())
            else:
                fw("\tstatic AmbColor {%s, %s, %s},\n" % tuple(map(f2s, reversed(light.amb_color[:3]))))
                
            if light.visibility is not None:
                light.visibility.write_mdl("Visibility", fw, model.global_seqs, "\t") # write_anim(light.visibility, "Visibility", fw, global_seqs, "\t", True)
            fw("}\n")
                
                
        # HELPERS
        for helper in model.objects['helper']:
            name = helper.name.replace('.', '_')
            
            if not name.lower().startswith("bone"):
                name = "Bone_"+name
        
            fw("Helper \"%s\" {\n" % name)
            if len(model.object_indices) > 1:
                fw("\tObjectId %d,\n" % model.object_indices[helper.name])
                
            if helper.parent is not None:
                fw("\tParent %d,\n" % model.object_indices[helper.parent])
            
            if hasattr(helper, "billboarded"):
                write_billboard(fw, helper.billboarded, helper.billboard_lock)
            
            if helper.anim_loc is not None:
                helper.anim_loc.write_mdl("Translation", fw, model.global_seqs, "\t")
                
            if helper.anim_rot is not None:
                helper.anim_rot.write_mdl("Rotation", fw, model.global_seqs, "\t")
                
            if helper.anim_scale is not None:
                helper.anim_scale.write_mdl("Scaling", fw, model.global_seqs, "\t")
            
            fw("}\n")

            
        # ATTACHMENT POINTS   
        if len(model.objects['attachment']):
            for i, attachment in enumerate(model.objects['attachment']):
                fw("Attachment \"%s\" {\n" % attachment.name)
                
                if len(model.object_indices) > 1:
                    fw("\tObjectId %d,\n" % model.object_indices[attachment.name])
                    
                if attachment.parent is not None:
                    fw("\tParent %d,\n" % model.object_indices[attachment.parent])
                    
                write_billboard(fw, attachment.billboarded, attachment.billboard_lock)
                
                fw("\tAttachmentID %d,\n" % i)
                
                visibility = attachment.visibility
                if visibility is not None:
                    visibility.write_mdl("Visibility", fw, model.global_seqs, "\t") # write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
                fw("}\n")
            
        # PIVOT POINTS
        if len(model.objects_all):
            fw("PivotPoints %d {\n" % len(model.objects_all))
            for object in model.objects_all:
                fw("\t{%s, %s, %s},\n" % tuple(map(f2s, object.pivot)))
            fw("}\n")
            
        # MODEL EMITTERS
        for psys in model.objects['particle']:
            emitter = psys.emitter
            fw("ParticleEmitter \"%s\" {\n" % psys.name)
            if len(model.object_indices) > 1:
                fw("\tObjectId %d,\n" % model.object_indices[psys.name])
            if psys.parent is not None:
                fw("\tParent %d,\n" % model.object_indices[psys.parent])
                
            fw("\tEmitterUsesMDL,\n")
            
            if psys.emission_rate_anim is not None:
                psys.emission_rate_anim.write_mdl("EmissionRate", fw, model.global_seqs, "\t") # write_anim(psys.emission_rate_anim, "EmissionRate", fw, global_seqs, "\t")
            else:
                fw("\tstatic EmissionRate %s,\n" % f2s(rnd(emitter.emission_rate)))
            
            if psys.gravity_anim is not None:
                psys.gravity_anim.write_mdl("Gravity", fw, model.global_seqs, "\t") # write_anim(psys.gravity_anim, "Gravity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Gravity %s,\n" % f2s(rnd(emitter.gravity)))
                
            if psys.longitude_anim is not None:
                psys.longitude_anim.write_mdl("Longitude", fw, model.global_seqs, "\t")# write_anim(psys.longitude_anim, "Longitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Longitude %s,\n" % f2s(rnd(emitter.latitude)))
            
            if psys.latitude_anim is not None:
                psys.latitude_anim.write_mdl("Latitude", fw, model.global_seqs, "\t") # write_anim(psys.latitude_anim, "Latitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Latitude %s,\n" % f2s(rnd(emitter.latitude)))
                
            visibility = psys.visibility
            if visibility is not None:
                visibility.write_mdl("Visibility", fw, model.global_seqs, "\t") # write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
            fw("\tParticle {\n")
            
            if psys.life_span_anim is not None:
                psys.life_span_anim.write_mdl("LifeSpan", fw, model.global_seqs, "\t")# write_anim(psys.life_span_anim, "LifeSpan", fw, global_seqs, "\t\t")
            else:
                fw("\t\tLifeSpan %s,\n" % f2s(rnd(emitter.life_span)))
              
            if psys.speed_anim is not None:
                psys.speed_anim.write_mdl("InitVelocity", fw, model.global_seqs, "\t") # write_anim(psys.speed_anim, "InitVelocity", fw, global_seqs, "\t\t")
            else:
                fw("\t\tstatic InitVelocity %s,\n" % f2s(rnd(emitter.speed)))

            fw("\t\tPath \"%s\",\n" % emitter.model_path)
            fw("\t}\n")
            fw("}\n")
         
        # PARTICLE EMITTERS
        for psys in model.objects['particle2']:
            emitter = psys.emitter
            fw("ParticleEmitter2 \"%s\" {\n" % psys.name)
            if len(model.object_indices) > 1:
                fw("\tObjectId %d,\n" % model.object_indices[psys.name])
            if psys.parent is not None:
                fw("\tParent %d,\n" % model.object_indices[psys.parent])
                
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
                psys.speed_anim.write_mdl("Speed", fw, model.global_seqs, "\t") # write_anim(psys.speed_anim, "Speed", fw, global_seqs, "\t")
            else:
                fw("\tstatic Speed %s,\n" % f2s(rnd(emitter.speed)))
                
            if psys.variation_anim is not None:
                psys.variation_anim.write_mdl("Variation", fw, model.global_seqs, "\t") # write_anim(psys.variation_anim, "Variation", fw, global_seqs, "\t")
            else:
                fw("\tstatic Variation %s,\n" % f2s(rnd(emitter.variation)))
                
            if psys.latitude_anim is not None:
                psys.latitude_anim.write_mdl("Latitude", fw, model.global_seqs, "\t") # write_anim(psys.latitude_anim, "Latitude", fw, global_seqs, "\t")
            else:
                fw("\tstatic Latitude %s,\n" % f2s(rnd(emitter.latitude)))
                
            if psys.gravity_anim is not None:
                psys.gravity_anim.write_mdl("Gravity", fw, model.global_seqs, "\t") # write_anim(psys.gravity_anim, "Gravity", fw, global_seqs, "\t")
            else:
                fw("\tstatic Gravity %s,\n" % f2s(rnd(emitter.gravity)))
                
            visibility = psys.visibility
            if visibility is not None:
                visibility.write_mdl("Visibility", fw, model.global_seqs, "\t") # write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
                
            fw("\tLifeSpan %s,\n" % f2s(rnd(emitter.life_span)))
                
            if psys.emission_rate_anim is not None:
                psys.emission_rate_anim.write_mdl("EmissionRate", fw, model.global_seqs, "\t") # write_anim(psys.emission_rate_anim, "EmissionRate", fw, global_seqs, "\t")
            else:
                fw("\tstatic EmissionRate %s,\n" % f2s(rnd(emitter.emission_rate)))
                
            # FIXME FIXME FIXME FIXME FIXME: Separate X and Y channels! New animation class won't handle this. 
            if psys.scale_anim is not None and ('scale', 1) in psys.scale_anim.keys():
                psys.scale_anim.write_mdl("Width", fw, model.global_seqs, "\t") # write_anim(psys.scale_anim[('scale', 1)], "Width", fw, global_seqs, "\t", scale=psys.dimensions[1])
            else:
                fw("\tstatic Width %s,\n" % f2s(rnd(psys.dimensions[1])))
               
            if psys.scale_anim is not None and ('scale', 0) in psys.scale_anim.keys():
                psys.scale_anim.write_mdl("Length", fw, model.global_seqs, "\t") # write_anim(psys.scale_anim[('scale', 0)], "Length", fw, global_seqs, "\t", scale=psys.dimensions[0])
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
            fw("\tTextureID %d,\n" % model.textures.index(emitter.texture_path))
            if emitter.priority_plane != 0:
                fw("\tPriorityPlane %d,\n" % emitter.priority_plane)
            fw("}\n")
           
        # RIBBON EMITTERS
        for psys in model.objects['ribbon']:
            emitter = psys.emitter
            fw("RibbonEmitter \"%s\" {\n" % psys.name)
            if len(model.object_indices) > 1:
                fw("\tObjectId %d,\n" % model.object_indices[psys.name])
            if psys.parent is not None:
                fw("\tParent %d,\n" % model.object_indices[psys.parent])
                
            fw("\tstatic HeightAbove %s,\n" % f2s(rnd(psys.dimensions[0]/2)))
            fw("\tstatic HeightBelow %s,\n" % f2s(rnd(psys.dimensions[0]/2)))
            
            if psys.alpha_anim is not None:
                psys.alpha_anim.write_mdl("Alpha", fw, model.global_seqs, "\t")
            else:
                fw("\tstatic Alpha %s,\n" % emitter.alpha)
            
            if psys.ribbon_color_anim is not None:
                psys.ribbon_color_anim.write_mdl("Color", fw, model.global_seqs, "\t")# write_anim_vec(psys.ribbon_color_anim, 'Color', 'ribbon_color', fw, global_seqs, Matrix(), Matrix(), "\t", (2, 1, 0))
            else:
                fw("\tstatic Color {%s, %s, %s},\n" % tuple(map(f2s, reversed(emitter.ribbon_color))))
                
            fw("\tstatic TextureSlot %d,\n" % model.textures.index(emitter.texture_path))
            visibility = psys.visibility
            if visibility is not None:
                visibility.write_mdl("Visibility", fw, model.global_seqs, "\t") # write_anim(visibility, "Visibility", fw, global_seqs, "\t", True)
            fw("\tEmissionRate %d,\n" % emitter.emission_rate)
            fw("\tLifeSpan %s,\n" % f2s(rnd(emitter.life_span)))
            fw("\tGravity %s,\n" % f2s(rnd(emitter.gravity)))
            fw("\tRows %d,\n" % emitter.rows)
            fw("\tColumns %d,\n" % emitter.cols)
            for material in model.materials:
                if material.name == emitter.ribbon_material.name:
                    fw("\tMaterialID %d,\n" % model.materials.index(material))
                    break
            fw("}\n")
            
        # CAMERAS    
        for camera in model.cameras:
            fw("Camera \"%s\" {\n" % camera.name)
            position = settings.global_matrix * Vector(camera.location)
            fw("\tPosition {%s, %s, %s},\n" % tuple(map(f2s, position)))
            fw("\tFieldOfView %f,\n" % camera.data.angle)
            fw("\tFarClip %f,\n" % (camera.data.clip_end*10))
            fw("\tNearClip %f,\n" % (camera.data.clip_start*10))
            matrix = settings.global_matrix * camera.matrix_world
            target = position + matrix.to_quaternion() * Vector((0.0, 0.0, -1.0)) # Target is just a point in front of the camera
            fw("\tTarget {\n\t\tPosition {%s, %s, %s},\n\t}\n" % tuple(map(f2s, target)))
            fw("}\n")
         
        # EVENT OBJECTS
        for event in model.objects['eventobject']:
            fw("EventObject \"%s\" {\n" % event.name)
            if len(model.object_indices) > 1:
                fw("\tObjectId %d,\n" % model.object_indices[event.name])
            if event.parent is not None:
                fw("\tParent %d,\n" % model.object_indices[event.parent])
            eventtrack = event.track
            if eventtrack is not None:
                eventtrack.write_mdl("EventTrack", fw, model.global_seqs, "\t")
                
            fw("}\n")
         
        # COLLISION SHAPES
        for collider in model.objects['collisionshape']:
            fw("CollisionShape \"%s\" {\n" % collider.name)
            fw("\tObjectId %d,\n" % model.object_indices[collider.name])
            if collider.parent is not None:
                fw("\tParent %d,\n" % model.object_indices[collider.parent])
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
                
                
    