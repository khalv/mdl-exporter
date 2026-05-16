import os.path
import struct

from .classes.War3AnimationCurve import War3AnimationCurve
from .classes.War3AnimationSequence import War3AnimationSequence
from .classes.War3Bone import War3Bone
from .classes.War3CollisionShape import War3CollisionShape
from .classes.War3EventObject import War3EventObject
from .classes.War3Geoset import War3Geoset
from .classes.War3GeosetAnim import War3GeosetAnim
from .classes.War3Light import War3Light
from .classes.War3Material import War3Material
from .classes.War3MaterialLayer import War3MaterialLayer
from .classes.War3Model import War3Model
from .classes.War3Object import War3Object
from .classes.War3ParticleSystem import War3ParticleSystem
from .classes.War3Texture import War3Texture
from .classes.War3TextureAnim import War3TextureAnim


FILTER_MODES = {
    0: "None",
    1: "Transparent",
    2: "Blend",
    3: "Additive",
    4: "AddAlpha",
    5: "Modulate",
    6: "Modulate2x",
}

INTERPOLATIONS = {
    0: "DontInterp",
    1: "Linear",
    2: "Hermite",
    3: "Bezier",
}

LIGHT_TYPES = {
    0: "Omnidirectional",
    1: "Directional",
    2: "Ambient",
}


class MDXReader:
    def __init__(self, path):
        with open(path, "rb") as file:
            self.data = file.read()
        self.offset = 0

    def tell(self):
        return self.offset

    def seek(self, offset):
        self.offset = offset

    def skip(self, size):
        self.offset += size

    def read(self, size):
        value = self.data[self.offset:self.offset + size]
        self.offset += size
        return value

    def tag(self):
        return self.read(4).decode("ascii", errors="replace")

    def u8(self):
        return self.unpack("<B")

    def u16(self):
        return self.unpack("<H")

    def u32(self):
        return self.unpack("<I")

    def i32(self):
        return self.unpack("<i")

    def f32(self):
        return self.unpack("<f")

    def vec2(self):
        return self.unpack("<2f")

    def vec3(self):
        return self.unpack("<3f")

    def vec4(self):
        return self.unpack("<4f")

    def unpack(self, fmt):
        size = struct.calcsize(fmt)
        values = struct.unpack_from(fmt, self.data, self.offset)
        self.offset += size
        return values[0] if len(values) == 1 else values

    def fixed_string(self, size):
        value = self.read(size).split(b"\0", 1)[0]
        return value.decode("utf-8", errors="replace")


def _read_extent(reader):
    reader.f32()
    minimum = reader.vec3()
    maximum = reader.vec3()
    return minimum, maximum


def _read_sized_end(reader):
    size_offset = reader.tell()
    size = reader.u32()
    return size_offset + size


def _color_rgb(value):
    return tuple(reversed(value[:3]))


def _rotation_wxyz(value):
    return (value[3], value[0], value[1], value[2])


def _read_track(reader, tag, model):
    curve = War3AnimationCurve()
    frame_count = reader.u32()
    curve.interpolation = INTERPOLATIONS.get(reader.u32(), "Linear")
    global_sequence_id = reader.i32()
    curve.global_sequence = list(model.global_seqs)[global_sequence_id] if global_sequence_id >= 0 and global_sequence_id < len(model.global_seqs) else -1
    dimensions = {
        "KGTR": 3, "KGRT": 4, "KGSC": 3,
        "KGAO": 1, "KGAC": 3, "KMTA": 1,
        "KTAT": 3, "KTAR": 4, "KTAS": 3,
        "KLAS": 1, "KLAE": 1, "KLAC": 3, "KLAI": 1, "KLBI": 1, "KLBC": 3, "KLAV": 1,
        "KATV": 1, "KPEE": 1, "KPEG": 1, "KPLN": 1, "KPLT": 1, "KPEV": 1, "KPEL": 1, "KPES": 1,
        "KP2S": 1, "KP2R": 1, "KP2L": 1, "KP2G": 1, "KP2V": 1, "KP2E": 1, "KP2W": 1, "KP2N": 1,
        "KRHA": 1, "KRHB": 1, "KRAL": 1, "KRCO": 3, "KRVS": 1,
    }.get(tag, 1)

    for _ in range(frame_count):
        frame = reader.u32()
        value = _read_track_value(reader, dimensions)
        if tag in {"KGRT", "KTAR"}:
            value = _rotation_wxyz(value)
        elif tag in {"KGAC", "KLAC", "KLBC", "KRCO"}:
            value = _color_rgb(value)
        curve.keyframes[frame] = value
        if curve.interpolation in {"Hermite", "Bezier"}:
            curve.handles_left[frame] = _read_track_value(reader, dimensions)
            curve.handles_right[frame] = _read_track_value(reader, dimensions)
    return curve


def _read_track_value(reader, dimensions):
    if dimensions == 1:
        return (reader.f32(),)
    if dimensions == 2:
        return reader.vec2()
    if dimensions == 3:
        return reader.vec3()
    if dimensions == 4:
        return reader.vec4()
    return ()


def _read_node_tracks(reader, end, node, model):
    while reader.tell() < end:
        if reader.tell() + 4 > end:
            break
        tag_offset = reader.tell()
        tag = reader.tag()
        if tag == "KGTR":
            node.anim_loc = _read_track(reader, tag, model)
        elif tag == "KGRT":
            node.anim_rot = _read_track(reader, tag, model)
        elif tag == "KGSC":
            node.anim_scale = _read_track(reader, tag, model)
        else:
            reader.seek(tag_offset)
            break


def _skip_track(reader):
    frame_count = reader.u32()
    interpolation = reader.u32()
    reader.i32()
    value_size = 4
    if interpolation in {2, 3}:
        value_size *= 3
    reader.skip(frame_count * (4 + value_size))


def _read_node(reader, model, node):
    node.name = reader.fixed_string(80)
    node.object_id = reader.u32()
    parent_id = reader.i32()
    node.parent_id = None if parent_id < 0 else parent_id
    flags = reader.u32()
    node.billboarded = bool(flags & 0x8)
    node.billboard_lock = (bool(flags & 0x10), bool(flags & 0x20), bool(flags & 0x40))
    return node


def _read_mdx(model, reader):
    if reader.tag() != "MDLX":
        raise ValueError("Not a Warcraft MDX file")

    while reader.tell() < len(reader.data):
        tag = reader.tag()
        size = reader.u32()
        end = reader.tell() + size
        if tag == "MODL":
            model.name = reader.fixed_string(80)
            reader.fixed_string(260)
            model.global_extents_min, model.global_extents_max = _read_extent(reader)
            reader.u32()
        elif tag == "SEQS":
            _read_sequences(model, reader, end)
        elif tag == "GLBS":
            while reader.tell() < end:
                model.global_seqs.add(reader.u32())
        elif tag == "TEXS":
            _read_textures(model, reader, end)
        elif tag == "MTLS":
            _read_materials(model, reader, end)
        elif tag == "TXAN":
            _read_texture_anims(model, reader, end)
        elif tag == "GEOS":
            _read_geosets(model, reader, end)
        elif tag == "GEOA":
            _read_geoset_anims(model, reader, end)
        elif tag == "BONE":
            _read_bones(model, reader, end)
        elif tag == "HELP":
            _read_helpers(model, reader, end)
        elif tag == "LITE":
            _read_lights(model, reader, end)
        elif tag == "ATCH":
            _read_attachments(model, reader, end)
        elif tag == "PIVT":
            model.pivots = []
            while reader.tell() < end:
                model.pivots.append(reader.vec3())
        elif tag == "PREM":
            _read_particle_emitters(model, reader, end)
        elif tag == "PRE2":
            _read_particle_emitters2(model, reader, end)
        elif tag == "RIBB":
            _read_ribbon_emitters(model, reader, end)
        elif tag == "EVTS":
            _read_event_objects(model, reader, end)
        elif tag == "CLID":
            _read_collision_shapes(model, reader, end)
        reader.seek(end)

    _finalize_model(model)


def _read_sequences(model, reader, end):
    while reader.tell() < end:
        name = reader.fixed_string(80)
        start = reader.u32()
        finish = reader.u32()
        movement_speed = reader.f32()
        flags = reader.u32()
        rarity = reader.f32()
        reader.u32()
        _read_extent(reader)
        sequence = War3AnimationSequence(name, start, finish, bool(flags & 1), movement_speed)
        sequence.rarity = rarity
        model.sequences.append(sequence)


def _read_textures(model, reader, end):
    while reader.tell() < end:
        replaceable_id = reader.u32()
        image_path = reader.fixed_string(260)
        reader.u32()
        texture = War3Texture(image_path)
        texture.replaceable_id = replaceable_id
        texture.is_replaceable = replaceable_id != 0
        if texture.is_replaceable:
            texture.image_path = None
        model.textures.append(texture)


def _read_materials(model, reader, end):
    material_index = 0
    while reader.tell() < end:
        material_end = _read_sized_end(reader)
        material = War3Material("Material %d" % material_index)
        material.priority_plane = reader.u32()
        material_flags = reader.u32()
        material.use_const_color = bool(material_flags & 0x1)
        if reader.tell() < material_end and reader.tag() == "LAYS":
            layer_count = reader.u32()
            for _ in range(layer_count):
                layer_end = _read_sized_end(reader)
                layer = War3MaterialLayer()
                layer.filter_mode = FILTER_MODES.get(reader.u32(), "None")
                flags = reader.u32()
                layer.unshaded = bool(flags & 0x1)
                layer.two_sided = bool(flags & 0x10)
                layer.unfogged = bool(flags & 0x20)
                layer.no_depth_test = bool(flags & 0x40)
                layer.no_depth_set = bool(flags & 0x80)
                layer.texture_id = reader.u32()
                texture_anim_id = reader.i32()
                layer.texture_anim_id = None if texture_anim_id < 0 else texture_anim_id
                reader.u32()
                layer.alpha_value = reader.f32()
                while reader.tell() < layer_end:
                    tag_offset = reader.tell()
                    tag = reader.tag()
                    if tag == "KMTA":
                        layer.alpha_anim = _read_track(reader, tag, model)
                    else:
                        reader.seek(tag_offset)
                        break
                material.layers.append(layer)
                reader.seek(layer_end)
        model.materials.append(material)
        material_index += 1
        reader.seek(material_end)


def _read_texture_anims(model, reader, end):
    while reader.tell() < end:
        anim_end = _read_sized_end(reader)
        anim = War3TextureAnim()
        while reader.tell() < anim_end:
            tag_offset = reader.tell()
            tag = reader.tag()
            if tag == "KTAT":
                anim.translation = _read_track(reader, tag, model)
            elif tag == "KTAR":
                anim.rotation = _read_track(reader, tag, model)
            elif tag == "KTAS":
                anim.scale = _read_track(reader, tag, model)
            else:
                reader.seek(tag_offset)
                break
        model.tvertex_anims.append(anim)
        reader.seek(anim_end)


def _read_geosets(model, reader, end):
    while reader.tell() < end:
        geoset_end = _read_sized_end(reader)
        geoset = War3Geoset()
        positions = []
        normals = []
        uvs = []
        vertex_groups = []
        counts = []
        while reader.tell() < geoset_end:
            tag = reader.tag()
            if tag == "VRTX":
                positions = [reader.vec3() for _ in range(reader.u32())]
            elif tag == "NRMS":
                normals = [reader.vec3() for _ in range(reader.u32())]
            elif tag == "PTYP":
                reader.skip(reader.u32() * 4)
            elif tag == "PCNT":
                reader.skip(reader.u32() * 4)
            elif tag == "PVTX":
                geoset.triangles = [reader.u16() for _ in range(reader.u32())]
            elif tag == "GNDX":
                vertex_groups = [reader.u8() for _ in range(reader.u32())]
            elif tag == "MTGC":
                counts = [reader.u32() for _ in range(reader.u32())]
            elif tag == "MATS":
                matrix_values = [reader.u32() for _ in range(reader.u32())]
                geoset.matrices = []
                offset = 0
                for count in counts:
                    geoset.matrices.append(tuple(matrix_values[offset:offset + count]))
                    offset += count
            elif tag == "UVAS":
                reader.u32()
            elif tag == "UVBS":
                uvs = [reader.vec2() for _ in range(reader.u32())]
            else:
                break
            if reader.tell() + 4 <= geoset_end:
                next_tag = reader.data[reader.tell():reader.tell() + 4]
                if next_tag not in {b"VRTX", b"NRMS", b"PTYP", b"PCNT", b"PVTX", b"GNDX", b"MTGC", b"MATS", b"UVAS", b"UVBS"}:
                    break

        if reader.tell() + 28 <= geoset_end:
            geoset.material_id = reader.u32()
            reader.u32()
            geoset.min_extent, geoset.max_extent = _read_extent(reader)
        if reader.tell() + 4 <= geoset_end:
            extent_count = reader.u32()
            for _ in range(extent_count):
                if reader.tell() + 28 > geoset_end:
                    break
                _read_extent(reader)

        while reader.tell() + 8 <= geoset_end:
            tag = reader.tag()
            if tag == "UVAS":
                reader.u32()
            elif tag == "UVBS":
                uvs = [reader.vec2() for _ in range(reader.u32())]
            else:
                break
        geoset.vertices = [
            (
                positions[i],
                normals[i] if i < len(normals) else (0, 0, 1),
                uvs[i] if i < len(uvs) else (0, 0),
                vertex_groups[i] if i < len(vertex_groups) else 0,
            )
            for i in range(len(positions))
        ]
        model.geosets.append(geoset)
        reader.seek(geoset_end)


def _read_geoset_anims(model, reader, end):
    while reader.tell() < end:
        anim_end = _read_sized_end(reader)
        alpha = reader.f32()
        reader.u32()
        color = _color_rgb(reader.vec3())
        geoset_id = reader.u32()
        anim = War3GeosetAnim(color, None, None)
        anim.geoset_id = geoset_id
        while reader.tell() < anim_end:
            tag_offset = reader.tell()
            tag = reader.tag()
            if tag == "KGAO":
                anim.alpha_anim = _read_track(reader, tag, model)
            elif tag == "KGAC":
                anim.color_anim = _read_track(reader, tag, model)
            else:
                reader.seek(tag_offset)
                break
        if 0 <= geoset_id < len(model.geosets):
            anim.geoset = model.geosets[geoset_id]
        if alpha < 1 and anim.alpha_anim is None:
            static_alpha = War3AnimationCurve()
            static_alpha.keyframes[0] = (alpha,)
            anim.alpha_anim = static_alpha
        model.geoset_anims.append(anim)
        reader.seek(anim_end)


def _read_bones(model, reader, end):
    while reader.tell() < end:
        bone_node_end = _read_sized_end(reader)
        bone = _read_node(reader, model, War3Bone(""))
        _read_node_tracks(reader, bone_node_end, bone, model)
        reader.seek(bone_node_end)
        bone.geoset_id = reader.i32() if reader.tell() + 4 <= end else -1
        geoset_anim_id = reader.i32() if reader.tell() + 4 <= end else -1
        bone.geoset_anim_id = None if geoset_anim_id < 0 else geoset_anim_id
        model.objects["bone"].add(bone)


def _read_helpers(model, reader, end):
    while reader.tell() < end:
        helper_end = _read_sized_end(reader)
        helper = _read_node(reader, model, War3Object(""))
        _read_node_tracks(reader, helper_end, helper, model)
        model.objects["helper"].add(helper)
        reader.seek(helper_end)


def _read_lights(model, reader, end):
    while reader.tell() < end:
        light_end = _read_sized_end(reader)
        light = _read_node(reader, model, War3Light(""))
        light.type = LIGHT_TYPES.get(reader.u32(), "Omnidirectional")
        light.atten_start = reader.f32()
        light.atten_end = reader.f32()
        light.color = _color_rgb(reader.vec3())
        light.intensity = reader.f32()
        light.amb_color = _color_rgb(reader.vec3())
        light.amb_intensity = reader.f32()
        while reader.tell() < light_end:
            tag_offset = reader.tell()
            tag = reader.tag()
            if tag == "KLAS":
                light.atten_start_anim = _read_track(reader, tag, model)
            elif tag == "KLAE":
                light.atten_end_anim = _read_track(reader, tag, model)
            elif tag == "KLAC":
                light.color_anim = _read_track(reader, tag, model)
            elif tag == "KLAI":
                light.intensity_anim = _read_track(reader, tag, model)
            elif tag == "KLBI":
                light.amb_intensity_anim = _read_track(reader, tag, model)
            elif tag == "KLBC":
                light.amb_color_anim = _read_track(reader, tag, model)
            elif tag == "KLAV":
                light.visibility = _read_track(reader, tag, model)
            else:
                reader.seek(tag_offset)
                break
        model.objects["light"].add(light)
        reader.seek(light_end)


def _read_attachments(model, reader, end):
    while reader.tell() < end:
        attachment_end = _read_sized_end(reader)
        attachment = _read_node(reader, model, War3Object(""))
        attachment.path = reader.fixed_string(260)
        attachment.attachment_id = reader.u32()
        while reader.tell() < attachment_end:
            tag_offset = reader.tell()
            tag = reader.tag()
            if tag == "KATV":
                attachment.visibility = _read_track(reader, tag, model)
            else:
                reader.seek(tag_offset)
                break
        model.objects["attachment"].add(attachment)
        reader.seek(attachment_end)


def _read_particle_emitters(model, reader, end):
    while reader.tell() < end:
        emitter_end = _read_sized_end(reader)
        emitter = _read_node(reader, model, War3ParticleSystem(""))
        emitter.emitter_type = "ParticleEmitter"
        emitter.emission_rate = reader.f32()
        emitter.gravity = reader.f32()
        emitter.longitude = reader.f32()
        emitter.latitude = reader.f32()
        emitter.model_path = reader.fixed_string(260)
        emitter.life_span = reader.f32()
        emitter.speed = reader.f32()
        model.objects["particle"].add(emitter)
        reader.seek(emitter_end)


def _read_particle_emitters2(model, reader, end):
    while reader.tell() < end:
        emitter_end = _read_sized_end(reader)
        emitter = _read_node(reader, model, War3ParticleSystem(""))
        emitter.emitter_type = "ParticleEmitter2"
        emitter.speed = reader.f32()
        emitter.variation = reader.f32()
        emitter.latitude = reader.f32()
        emitter.gravity = reader.f32()
        emitter.life_span = reader.f32()
        emitter.emission_rate = reader.f32()
        emitter.width = reader.f32()
        emitter.height = reader.f32()
        emitter.filter_mode = FILTER_MODES.get(reader.u32(), "Blend")
        emitter.rows = reader.u32()
        emitter.cols = reader.u32()
        head_tail = reader.u32()
        emitter.head = head_tail in {0, 2}
        emitter.tail = head_tail in {1, 2}
        emitter.tail_length = reader.f32()
        emitter.time = reader.f32()
        emitter.start_color = _color_rgb(reader.vec3())
        emitter.mid_color = _color_rgb(reader.vec3())
        emitter.end_color = _color_rgb(reader.vec3())
        emitter.start_alpha = reader.u8()
        emitter.mid_alpha = reader.u8()
        emitter.end_alpha = reader.u8()
        reader.u8()
        scales = reader.vec3()
        emitter.start_scale, emitter.mid_scale, emitter.end_scale = scales
        emitter.head_life_start, emitter.head_life_end, emitter.head_life_repeat = reader.u32(), reader.u32(), reader.u32()
        emitter.head_decay_start, emitter.head_decay_end, emitter.head_decay_repeat = reader.u32(), reader.u32(), reader.u32()
        emitter.tail_life_start, emitter.tail_life_end, emitter.tail_life_repeat = reader.u32(), reader.u32(), reader.u32()
        emitter.tail_decay_start, emitter.tail_decay_end, emitter.tail_decay_repeat = reader.u32(), reader.u32(), reader.u32()
        emitter.texture_id = reader.u32()
        emitter.priority_plane = reader.u32()
        flags = reader.u32()
        emitter.sort_far_z = bool(flags & 0x10000)
        emitter.unshaded = bool(flags & 0x8000)
        emitter.line_emitter = bool(flags & 0x20000)
        emitter.unfogged = bool(flags & 0x40000)
        emitter.model_space = bool(flags & 0x80000)
        emitter.xy_quad = bool(flags & 0x100000)
        model.objects["particle2"].add(emitter)
        reader.seek(emitter_end)


def _read_ribbon_emitters(model, reader, end):
    while reader.tell() < end:
        emitter_end = _read_sized_end(reader)
        emitter = _read_node(reader, model, War3ParticleSystem(""))
        emitter.emitter_type = "RibbonEmitter"
        height_above = reader.f32()
        height_below = reader.f32()
        emitter.dimensions = (height_above + height_below, height_above + height_below, 0)
        emitter.alpha = reader.f32()
        emitter.ribbon_color = _color_rgb(reader.vec3())
        emitter.life_span = reader.f32()
        emitter.texture_id = reader.u32()
        material_id = reader.u32()
        emitter.ribbon_material = model.materials[material_id] if material_id < len(model.materials) else 0
        emitter.rows = reader.u32()
        emitter.cols = reader.u32()
        emitter.emission_rate = reader.f32()
        emitter.gravity = reader.f32()
        model.objects["ribbon"].add(emitter)
        reader.seek(emitter_end)


def _read_event_objects(model, reader, end):
    while reader.tell() < end:
        event_end = _read_sized_end(reader)
        event = _read_node(reader, model, War3EventObject(""))
        while reader.tell() < event_end:
            tag_offset = reader.tell()
            tag = reader.tag()
            if tag == "KEVT":
                event.track = _read_track(reader, tag, model)
            else:
                reader.seek(tag_offset)
                break
        model.objects["eventobject"].add(event)
        reader.seek(event_end)


def _read_collision_shapes(model, reader, end):
    while reader.tell() < end:
        node_end = _read_sized_end(reader)
        collider = _read_node(reader, model, War3CollisionShape(""))
        _read_node_tracks(reader, node_end, collider, model)
        reader.seek(node_end)
        if reader.tell() + 4 > end:
            break
        shape_type = reader.u32()
        collider.type = "Box" if shape_type == 0 else "Sphere"
        if collider.type == "Box":
            collider.vertices = []
            if reader.tell() + 24 <= end:
                collider.vertices = [reader.vec3(), reader.vec3()]
        else:
            if reader.tell() + 12 <= end:
                collider.vertices = [reader.vec3()]
            if reader.tell() + 4 <= end:
                collider.radius = reader.f32()
        model.objects["collisionshape"].add(collider)


def _finalize_model(model):
    if not model.materials:
        material = War3Material("Material 0")
        material.layers.append(War3MaterialLayer())
        model.materials.append(material)
    if not model.textures:
        model.textures.append(War3Texture(War3Model.default_texture))

    for index, geoset in enumerate(model.geosets):
        if not geoset.matrices:
            geoset.matrices = [(0,)]
        if geoset.min_extent is None:
            points = [vertex[0] for vertex in geoset.vertices]
            geoset.min_extent = tuple(min(point[i] for point in points) for i in range(3)) if points else (0, 0, 0)
            geoset.max_extent = tuple(max(point[i] for point in points) for i in range(3)) if points else (0, 0, 0)
        if geoset.material_id >= len(model.materials):
            geoset.material_id = 0
        geoset.mat_name = model.materials[geoset.material_id].name

    if not model.objects["bone"] and model.geosets:
        bone = War3Bone("Bone_Root")
        bone.object_id = 0
        bone.parent_id = None
        bone.geoset_id = -1
        bone.geoset_anim_id = None
        model.objects["bone"].add(bone)

    model.objects_all = sorted(
        list(model.objects["bone"])
        + list(model.objects["helper"])
        + list(model.objects["light"])
        + list(model.objects["attachment"])
        + list(model.objects["particle"])
        + list(model.objects["particle2"])
        + list(model.objects["ribbon"])
        + list(model.objects["eventobject"])
        + list(model.objects["collisionshape"]),
        key=lambda node: node.object_id,
    )
    model.objects["bone"] = set(sorted(model.objects["bone"], key=lambda node: node.object_id))
    model.objects["helper"] = set(sorted(model.objects["helper"], key=lambda node: node.object_id))
    model.object_indices = {node.name: node.object_id for node in model.objects_all}

    if not hasattr(model, "pivots") or not model.pivots:
        max_id = max([node.object_id for node in model.objects_all], default=0)
        model.pivots = [(0, 0, 0)] * (max_id + 1)
    for node in model.objects_all:
        if node.object_id < len(model.pivots):
            node.pivot = model.pivots[node.object_id]


def load(operator, context, settings, filepath=""):
    print("Beginning MDX load of model %s" % filepath)
    model = War3Model(context)
    reader = MDXReader(filepath)
    _read_mdx(model, reader)
    print("Converting MDX to scene...")
    model.to_scene(context, settings.global_matrix, os.path.dirname(filepath))
