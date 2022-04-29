from .classes.War3Model import War3Model
from .classes.War3Bone import War3Bone
from .classes.War3Object import War3Object
from .classes.War3Material import War3Material
from .classes.War3AnimationSequence import War3AnimationSequence
from .classes.War3AnimationCurve import War3AnimationCurve
from .classes.War3Geoset import War3Geoset
from .classes.War3MaterialLayer import War3MaterialLayer
from .classes.War3Texture import War3Texture
from .classes.War3Camera import War3Camera
from .classes.War3TextureAnim import War3TextureAnim
from .classes.War3Light import War3Light
from .classes.War3ParticleSystem import War3ParticleSystem
from .classes.War3CollisionShape import War3CollisionShape
from .classes.War3EventObject import War3EventObject
from .classes.War3GeosetAnim import War3GeosetAnim

import os.path

def parse_vector(str, as_int = False):
    values = str.rstrip('},').lstrip('{').split(',')
    return tuple(map(lambda x: int(x) if as_int else float(x), values))

class MDLParser:
    def __init__(self, path):
         self.file = open(path, 'r')
         self.scope = 0

    def __del__(self):
        self.file.close()

    def readline(self):
        line = self.file.readline().strip().rstrip(',')
        if line.endswith("{"):
            self.scope += 1
        elif line.startswith("}"):
            self.scope -= 1
        return line

    def parse_header(self):
        pass

    def parse_geoset(self):
        print("Parsing geoset")
        geoset = War3Geoset()

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ')
            if token == 'Vertices':
                count = int(values[0])
                print("Parsing %d vertices" % count)
                for i in range(count):
                    vertex = parse_vector(self.readline())
                    geoset.vertices.append((vertex, (0, 1, 0), (0, 0), 0))
            elif token == 'Normals':
                count = int(values[0])
                print("Parsing %d normals" % count)
                for i in range(count):
                    vertex = list(geoset.vertices[i])
                    vertex[1] = parse_vector(self.readline())
                    geoset.vertices[i] = tuple(vertex)
            elif token == 'TVertices':
                count = int(values[0])
                print("Parsing %d UVs" %count)
                for i in range(count):
                    vertex = list(geoset.vertices[i])
                    vertex[2] = parse_vector(self.readline())
                    geoset.vertices[i] = tuple(vertex)
            elif token == 'VertexGroup':
                line = self.readline().strip()
                i = 0
                print ("Parsing vertex groups")
                while line != '}':
                    vertex = list(geoset.vertices[i])
                    vertex[3] = int(line)
                    geoset.vertices[i] = tuple(vertex)
                    i += 1
                    line = self.readline().strip()
            elif token == 'Faces':
                print("Parsing triangles")
                geoset.triangles = []
                tri_count = int(values[0].split(' ')[0])
                self.readline() # One line is for the Triangles block - ignore this
                for i in range(tri_count):
                    # Triangle indices are stored in a giant vector
                    geoset.triangles += list(parse_vector(self.readline(), True))
            elif token == 'Groups':
                count = int(values[0])
                for i in range(count):
                    group = self.readline().split(' ', 1)
                    if group[0].strip() == "Matrices":
                        geoset.matrices.append(parse_vector(group[1], True))
            elif token == 'MaterialID':
                geoset.material_id = int(values[0])

        self.model.geosets.append(geoset)

    def parse_geoset_anim(self):
        print("Parsing geoset animation")
        base_scope = self.scope
        geoset_anim = War3GeosetAnim((1, 1, 1), None, None)

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)

            if token == "GeosetId":
                geoset_anim.geoset_id = int(values[0])
            elif token == "Alpha":
                frame_count = int(values[0].split(' ')[0])
                geoset_anim.alpha_anim = self.parse_animation(token, frame_count)
            elif token == "Color":
                frame_count = int(values[0].split(' ')[0])
                geoset_anim.color_anim = self.parse_animation(token, frame_count)
            elif token == "static":
                token, *values = values[0].split(' ', 1)
                if token == "Alpha":
                    geoset_anim.alpha = float(values[0])
                elif token == "Color":
                    geoset_anim.color = parse_vector(values[0])

        self.model.geoset_anims.append(geoset_anim)

    def parse_animation(self, type, num_frames):
        print("Parsing '%s' animation with %d frames" % (type, num_frames))
        curve = War3AnimationCurve()
        curve.type = type

        has_tangents = False
        if type != "EventTrack":
            curve.interpolation = self.readline()
            has_tangents = curve.interpolation in {'Bezier', 'Hermite'}

        line = self.readline()
        if "GlobalSeqId" in line:
            curve.global_sequence = int(line.split(' ')[1])
            line = self.readline()

        for i in range(num_frames):
            token, *values = line.split(' ', 1)
            frame = int(token.rstrip(':'))

            if type != 'EventTrack':
                value = None
                if type in {'Visibility'}:
                    value = parse_vector(values[0], True)
                else:
                    value = parse_vector(values[0])

                if type == 'Rotation':
                    # Blender quaternions have the form WXYZ, while MDL has XYZW
                    value = (value[3], value[0], value[1], value[2])

                curve.keyframes[frame] = value
            else:
                curve.keyframes[frame] = (1,)

            if has_tangents:
                in_tan = parse_vector(self.readline().split(' ', 1)[1])
                out_tan = parse_vector(self.readline().split(' ', 1)[1])

                if type == 'Rotation':
                    in_tan = (in_tan[3], in_tan[0], in_tan[1], in_tan[2])
                    out_tan = (out_tan[3], out_tan[0], out_tan[1], out_tan[2])

                curve.handles_left[frame] = in_tan
                curve.handles_right[frame] = out_tan

            line = self.readline()

        return curve

    def parse_node(self, node, token, values):
        if token == 'ObjectId':
            node.object_id = int(values[0])
            return True
        elif token == 'Parent':
            node.parent_id = int(values[0])
            return True
        elif token.startswith('BillboardedLock'):
            axis = token[-1]
            billboarded = list(node.billboard_lock)
            if axis == 'X':
                billboarded[0] = True
            elif axis == 'Y':
                billboarded[1] = True
            elif axis == 'Z':
                billboarded[2] = True
            node.billboard_lock = tuple(billboarded)
            return True
        elif token == 'Billboarded':
            node.billboarded = True
            return True
        elif token == "Visibility":
            frame_count = int(values[0].split(' ')[0])
            node.visibility = self.parse_animation(token, frame_count)
            return True
        elif token == "Scale":
            frame_count = int(values[0].split(' ')[0])
            node.anim_scale = self.parse_animation(token, frame_count)
            return True
        elif token == "Rotation":
            frame_count = int(values[0].split(' ')[0])
            node.anim_rot = self.parse_animation(token, frame_count)
            return True
        elif token == "Translation":
            frame_count = int(values[0].split(' ')[0])
            node.anim_loc = self.parse_animation(token, frame_count)
            return True

        return False

    def parse_bone(self, name):
        print("Parsing bone %s" % name)
        bone = War3Bone(name)

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)
            if self.parse_node(bone, token, values):
                pass
            elif token == "GeosetId":
                if values[0] == "Multiple":
                    bone.geoset_id = -1
                else:
                    bone.geoset_id = int(values[0])
            elif token == "GeosetAnimId":
                bone.geoset_anim_id = None if values[0] == "None" else int(values[0])

        self.model.objects["bone"].add(bone)

    def parse_light(self, name):
        light = War3Light(name)

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)
            if self.parse_node(light, token, values):
                pass
            elif token in {"Omnidirectional", "Directional", "Ambient"}:
                light.type = token
            elif token == "Intensity":
                frame_count = int(values[0].split(' ')[0])
                light.intensity_anim = self.parse_animation(token, frame_count)
            elif token == "AmbIntensity":
                frame_count = int(values[0].split(' ')[0])
                light.amb_intensity_anim = self.parse_animation(token, frame_count)
            elif token == "AttenuationStart":
                frame_count = int(values[0].split(' ')[0])
                light.atten_start_anim = self.parse_animation(token, frame_count)
            elif token == "AttenuationEnd":
                frame_count = int(values[0].split(' ')[0])
                light.atten_end_anim = self.parse_animation(token, frame_count)
            elif token == "Color":
                frame_count = int(values[0].split(' ')[0])
                light.color_anim = self.parse_animation(token, frame_count)
            elif token == "AmbColor":
                frame_count = int(values[0].split(' ')[0])
                light.amb_color_anim = self.parse_animation('Color', frame_count)
            elif token == "static":
                token, *values = values[0].split(' ', 1)
                if token == "AttenuationStart":
                    light.atten_start = float(values[0])
                elif token == "AttenuationEnd":
                    light.atten_end = float(values[0])
                elif token == "Intensity":
                    light.intensity = float(values[0])
                elif token == "Color":
                    light.color = parse_vector(values[0])
                elif token == "AmbColor":
                    light.amb_color = parse_vector(values[0])

        self.model.objects['light'].add(light)


    def parse_helper(self, name):
        print("Parsing helper %s" % name)
        helper = War3Object(name)

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)
            if self.parse_node(helper, token, values):
                pass

        self.model.objects["helper"].add(helper)

    def parse_attachment(self, name):
        print("Parsing attachment %s" % name)
        attachment = War3Object(name)

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)
            if self.parse_node(attachment, token, values):
                pass
            elif token == "AttachmentId":
                # Currently not used
                attachment.attachment_id = int(values[0])

        self.model.objects["attachment"].add(attachment)

    def parse_event_object(self, name):
        print("Parsing event object %s" % name)
        event = War3EventObject(name)

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)
            if self.parse_node(event, token, values):
                pass
            elif token == "EventTrack":
                frame_count = int(values[0].split(' ')[0])
                event.track = self.parse_animation(token, frame_count)

        self.model.objects["eventobject"].add(event)

    def parse_particle_emitter(self, name):
        pass

    def parse_particle_emitter_2(self, name):
        print("Parsing ParticleEmitter2 %s" % name)
        emitter = War3ParticleSystem(name)
        line = self.readline()

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = line.split(' ', 1)
            if self.parse_node(emitter, token, values):
                pass
            elif token == "SortPrimsFarZ":
                emitter.sort_far_z = True
            elif token == "Unshaded":
                emitter.unshaded = True
            elif token == "LineEmitter":
                emitter.line_emitter = True
            elif token == "Unfogged":
                emitter.unfogged = True
            elif token == "ModelSpace":
                emitter.model_space = True
            elif token == "XYQuad":
                emitter.xy_quad = True
            elif token == "LifeSpan":
                emitter.life_span = float(values[0])
            elif token == "Rows":
                emitter.rows = int(values[0])
            elif token == "Columns":
                emitter.cols = int(values[0])
            elif token == "Head":
                emitter.head = True
            elif token == "Tail":
                emitter.tail = True
            elif token == "Both":
                emitter.tail = True
                emitter.head = True
            elif token == "TailLength":
                emitter.tail_length = float(values[0])
            elif token == "Time":
                emitter.time = float(values[0])
            elif token == "SegmentColor":
                emitter.start_color = parse_vector(self.readline().split(' ', 1)[1])
                emitter.mid_color = parse_vector(self.readline().split(' ', 1)[1])
                emitter.end_color = parse_vector(self.readline().split(' ', 1)[1])
            elif token == "Alpha":
                alpha = parse_vector(values[0], True)
                emitter.start_alpha = alpha[0]
                emitter.mid_alpha = alpha[1]
                emitter.end_alpha = alpha[2]
            elif token == "ParticleScaling":
                scale = parse_vector(values[0])
                emitter.start_scale = scale[0]
                emitter.mid_scale = scale[1]
                emitter.end_scale = scale[2]
            elif token == "LifespanUVAnim":
                uv = parse_vector(values[0], True)
                emitter.head_life_start = uv[0]
                emitter.head_life_end = uv[1]
                emitter.head_life_repeat = uv[2]
            elif token == "DecayUVAnim":
                uv = parse_vector(values[0], True)
                emitter.head_decay_start = uv[0]
                emitter.head_decay_end = uv[1]
                emitter.head_decay_repeat = uv[2]
            elif token == "TailUVAnim":
                uv = parse_vector(values[0], True)
                emitter.tail_life_start = uv[0]
                emitter.tail_life_end = uv[1]
                emitter.tail_life_repeat = uv[2]
            elif token == "TailDecayUVAnim":
                uv = parse_vector(values[0], True)
                emitter.tail_decay_start = uv[0]
                emitter.tail_decay_end = uv[1]
                emitter.tail_decay_repeat = uv[2]
            elif token == "TextureID":
                emitter.texture_id = int(values[0])
            elif token == "ReplaceableId":
                pass
            elif token == "PriorityPlane":
                emitter.priority_plane = int(values[0])
            elif token == "Speed":
                frame_count = int(values[0].split(' ')[0])
                emitter.speed_anim = self.parse_animation(token, frame_count)
            elif token == "Variation":
                frame_count = int(values[0].split(' ')[0])
                emitter.variation_anim = self.parse_animation(token, frame_count)
            elif token == "EmissionRate":
                frame_count = int(values[0].split(' ')[0])
                emitter.emission_rate_anim = self.parse_animation(token, frame_count)
            elif token == "Width":
                frame_count = int(values[0].split(' ')[0])
                emitter.width_anim = self.parse_animation(token, frame_count)
            elif token == "Height":
                frame_count = int(values[0].split(' ')[0])
                emitter.height_anim = self.parse_animation(token, frame_count)
            elif token == "Gravity":
                frame_count = int(values[0].split(' ')[0])
                emitter.gravity_anim = self.parse_animation(token, frame_count)
            elif token == "Latitude":
                frame_count = int(values[0].split(' ')[0])
                emitter.latitude_anim = self.parse_animation(token, frame_count)
            elif token == "static":
                token, *values = values[0].split(' ', 1)
                if token == "Speed":
                    emitter.speed = float(values[0])
                elif token == "Variation":
                    emitter.variation = float(values[0])
                elif token == "Latitude":
                    emitter.latitude = float(values[0])
                elif token == "Gravity":
                    emitter.gravity = float(values[0])
                elif token == "EmissionRate":
                    emitter.emission_rate = float(values[0])
                elif token == "Width":
                    emitter.width = float(values[0])
                elif token == "Height":
                    emitter.height = float(values[0])

            line = self.readline()

        self.model.objects['particle2'].add(emitter)

    def parse_ribbon_emitter(self, name):
        pass

    def parse_collision_shape(self, name):
        print("Parsing collision shape %s" % name)
        shape = War3CollisionShape(name)

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)
            if self.parse_node(shape, token, values):
                pass
            elif token in {'Box', 'Sphere'}:
                shape.type = token
            elif token == "BoundsRadius":
                shape.radius = float(values[0])
            elif token == "Vertices":
                count = int(values[0].split(' ')[0])
                shape.vertices = []
                for i in range(count):
                    shape.vertices.append(parse_vector(self.readline()))

        self.model.objects['collisionshape'].add(shape)

    def parse_camera(self, name):
        print("Parsing camera %s" % name)
        camera = War3Camera(name)

        base_scope = self.scope

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)
            if self.parse_node(camera, token, values):
                pass
            elif token == "FieldOfView":
                camera.field_of_view = float(values[0])
            elif token == "FarClip":
                camera.far_clip = float(values[0])
            elif token == "NearClip":
                camera.near_clip = float(values[0])
            elif token == "Target":
                child_scope = self.scope
                while self.scope >= child_scope:
                    token, *values = self.readline().split(' ', 1)
                    if token == "Position":
                        camera.target = parse_vector(values[0])

        self.model.objects['camera'].add(camera)

    def parse_pivot_poins(self, count):
        print("Parsing %d materials" % count)
        pivots = []
        for i in range(count):
            pivots.append(parse_vector(self.readline()))
        self.model.pivots = pivots

    def parse_textures(self, count):
        print("Parsing %d textures" % count)

        for i in range(count):
            self.readline() # Enter scope of first bitmap
            texture = War3Texture(None)
            child_scope = self.scope
            while self.scope >= child_scope:
                token, *values = self.readline().split(' ', 1)
                if token == 'Image':
                    texture.image_path = values[0].strip('"')
                elif token == 'ReplaceableId':
                    texture.image_path = None
                    texture.is_replaceable = True
                    texture.replaceable_id = int(values[0])

            self.model.textures.append(texture)

        

    def parse_material_layer(self, material):
        base_scope = self.scope

        layer = War3MaterialLayer()

        while self.scope >= base_scope:
            token, *values = self.readline().split(' ', 1)
            if token == 'FilterMode':
                layer.filter_mode = values[0]
            elif token == 'Unshaded':
                layer.unshaded = True
            elif token == 'TwoSided':
                layer.two_sided = True
            elif token == 'Unfogged':
                layer.unfogged = True
            elif token == 'NoDepthTest':
                layer.no_depth_test = True
            elif token == 'NoDepthSet':
                layer.no_depth_set = True
            elif 'TextureID' in token:
                frame_count = int(values[0].split(' ')[0])
                layer.texture_id_anim = self.parse_animation(token, frame_count)
            elif token == 'TVertexAnimId':
                layer.texture_anim_id = int(values[0])
            elif token == 'Alpha':
                frame_count = int(values[0].split(' ')[0])
                layer.alpha_anim = self.parse_animation(token, frame_count)
            elif token == 'static':
                token, *values = values[0].split(' ', 1)
                if token == 'Alpha':
                    layer.alpha_value = float(values[0])
                if token == 'TextureID':
                    layer.texture_id = int(values[0])

        material.layers.append(layer)


    def parse_materials(self, count):
        print("Parsing %d materials" % count)
        for i in range(count):
            material = War3Material("Material %d" % i)
            self.readline()
            base_scope = self.scope
            while self.scope >= base_scope:
                token, *values = self.readline().split(' ', 1)
                if token == 'ConstantColor':
                    material.use_const_color = True
                elif token == 'SortPrimsFarZ':
                    pass
                elif token == 'FullResolution':
                    pass
                elif token == 'PriorityPlane':
                    material.priority_plane = int(values[0])
                elif token == 'Layer':
                    self.parse_material_layer(material)

            self.model.materials.append(material)


    def parse_sequences(self, count):
        print("Parsing %d sequences" % count)
        for i in range(count):
            token, *values = self.readline().rstrip(' {').split(' ', 1)
            name = values[0].strip('"')

            print ("Parsing sequence %s" % name)

            interval = parse_vector(self.readline().split(' ', 1)[1], True)
            non_looping = False
            rarity = 0
            movement_speed = 0

            base_scope = self.scope

            while self.scope >= base_scope:
                token, *values = self.readline().split(' ', 1)
                if token == 'NonLooping':
                    non_looping = True
                elif token == 'MoveSpeed':
                    movement_speed = float(values[0])
                elif token == 'Rarity':
                    rarity = float(values[0])

            sequence = War3AnimationSequence(name, interval[0], interval[1], non_looping, movement_speed)
            sequence.rarity = rarity

            self.model.sequences.append(sequence)

    def parse_global_sequences(self, count):
        print("Parsing global sequences")
        for i in range(count):
            token, *values = self.readline().split(' ', 1)
            if token == 'Duration':
                self.model.global_seqs.add(int(values[0]))

    def parse_texture_anims(self, count):
        for i in range(count):
            self.readline() # Enter scope
            base_scope = self.scope

            uv_anim = War3TextureAnim()

            while self.scope >= base_scope:
                token, *values = self.readline().split(' ', 1)
                if token == "Translation":
                    frame_count = int(values[0].split(' ')[0])
                    uv_anim.translation = self.parse_animation(token, frame_count)
                elif token == "Rotation":
                    frame_count = int(values[0].split(' ')[0])
                    uv_anim.rotation = self.parse_animation(token, frame_count)
                elif token == "Scale":
                    frame_count = int(values[0].split(' ')[0])
                    uv_anim.scale = self.parse_animation(token, frame_count)

            self.model.tvertex_anims.append(uv_anim)
                    

    def parse_token(self, token, data):
        if token == "Version":
            pass
        elif token == "Model":
            self.model.name = data[0].replace('"', "")
            self.parse_header()
        elif token == "Geoset":
            self.parse_geoset()
        elif token == "GeosetAnim":
            self.parse_geoset_anim()
        elif token == "Textures":
            self.parse_textures(int(data[0].split(' ')[0]))
        elif token == "Materials":
            self.parse_materials(int(data[0].split(' ')[0]))
        elif token == "Sequences":
            self.parse_sequences(int(data[0].split(' ')[0]))
        elif token == "GlobalSequences":
            self.parse_global_sequences(int(data[0].split(' ')[0]))
        elif token == "TextureAnims":
            self.parse_texture_anims(int(data[0].split(' ')[0]))
        elif token == "PivotPoints":
            self.parse_pivot_poins(int(data[0].split(' ')[0]))
        elif token == "Bone":
            self.parse_bone(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "Helper":
            self.parse_helper(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "Light":
            self.parse_light(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "Attachment":
            self.parse_attachment(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "EventObject":
            self.parse_event_object(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "Camera":
            self.parse_camera(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "ParticleEmitter":
            self.parse_particle_emitter(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "ParticleEmitter2":
            self.parse_particle_emitter_2(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "RibbonEmitter":
            self.parse_ribbon_emitter(data[0].rsplit(' ', 1)[0].strip('" '))
        elif token == "CollisionShape":
            self.parse_collision_shape(data[0].rsplit(' ', 1)[0].strip('" '))

    def parse(self, model):
        self.model = model
        line = self.readline()

        while (line):
            if line.startswith("//"):
                # Ignore comments
                line = self.readline()
                continue

            token, *values = line.split(' ', 1)
            self.parse_token(token, values)
            line = self.readline()




def load(operator, context, settings, filepath=""):
    print("Beginning load of model %s" % filepath)
    model = War3Model(context)
    parser = MDLParser(filepath)

    print("Parsing...")
    parser.parse(model)
    print("Converting to scene...")
    model.to_scene(context, settings.global_matrix, os.path.dirname(filepath))
    



