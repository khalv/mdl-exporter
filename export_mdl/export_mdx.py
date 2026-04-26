import io
import struct

import bpy

from .classes.War3Model import War3Model
from .utils import calc_bounds_radius


INTERPOLATIONS = {
    "DontInterp": 0,
    "None": 0,
    "Linear": 1,
    "Hermite": 2,
    "Bezier": 3,
}

FILTER_MODES = {
    "None": 0,
    "Transparent": 1,
    "Blend": 2,
    "Additive": 3,
    "AddAlpha": 4,
    "Modulate": 5,
    "Modulate2x": 6,
}

LIGHT_TYPES = {
    "Omnidirectional": 0,
    "Directional": 1,
    "Ambient": 2,
}

NODE_FLAGS = {
    "helper": 0x000,
    "bone": 0x100,
    "light": 0x200,
    "eventobject": 0x400,
    "attachment": 0x800,
    "particle": 0x1000,
    "collisionshape": 0x2000,
    "ribbon": 0x4000,
}


class MDXWriter:
    def __init__(self):
        self.buffer = io.BytesIO()

    def tell(self):
        return self.buffer.tell()

    def write(self, data):
        self.buffer.write(data)

    def u32(self, value):
        self.write(struct.pack("<I", int(value)))

    def u16(self, value):
        self.write(struct.pack("<H", int(value)))

    def i32(self, value):
        self.write(struct.pack("<i", int(value)))

    def f32(self, value):
        self.write(struct.pack("<f", float(value)))

    def vec2(self, value):
        self.write(struct.pack("<2f", float(value[0]), float(value[1])))

    def vec3(self, value):
        self.write(struct.pack("<3f", float(value[0]), float(value[1]), float(value[2])))

    def vec4(self, value):
        self.write(struct.pack("<4f", float(value[0]), float(value[1]), float(value[2]), float(value[3])))

    def fixed_string(self, value, size):
        encoded = (value or "").encode("utf-8")[: size - 1]
        self.write(encoded)
        self.write(b"\0" * (size - len(encoded)))

    def chunk(self, name):
        return SizedBlock(self, name.encode("ascii"), include_tag=True)

    def sized(self):
        return SizedBlock(self, None, include_tag=False)

    def save(self, filepath):
        with open(filepath, "wb") as file:
            file.write(self.buffer.getvalue())


class SizedBlock:
    def __init__(self, writer, tag, include_tag):
        self.writer = writer
        self.tag = tag
        self.include_tag = include_tag
        self.size_position = None
        self.data_position = None

    def __enter__(self):
        if self.include_tag:
            self.writer.write(self.tag)
        self.size_position = self.writer.tell()
        self.writer.u32(0)
        self.data_position = self.writer.tell()
        return self

    def __exit__(self, exc_type, exc, traceback):
        end_position = self.writer.tell()
        size = end_position - self.data_position
        current = self.writer.tell()
        self.writer.buffer.seek(self.size_position)
        self.writer.u32(size)
        self.writer.buffer.seek(current)


def _ms_frame(frame):
    return int(frame * 1000 / bpy.context.scene.render.fps)


def _object_id(model, obj):
    return model.object_indices.get(obj.name, obj.object_id)


def _parent_id(model, obj):
    if obj.parent is None:
        return -1
    return model.object_indices[obj.parent]


def _node_flags(kind, obj):
    flags = NODE_FLAGS[kind]
    if getattr(obj, "billboarded", False):
        flags |= 0x008
    lock_x, lock_y, lock_z = getattr(obj, "billboard_lock", (False, False, False))
    if lock_x:
        flags |= 0x010
    if lock_y:
        flags |= 0x020
    if lock_z:
        flags |= 0x040
    return flags


def _write_extent(writer, minimum, maximum):
    writer.f32(calc_bounds_radius(minimum, maximum))
    writer.vec3(minimum)
    writer.vec3(maximum)


def _write_track(writer, tag, curve, model, dimensions=None, transform=None, index=None, base_value=1):
    if curve is None:
        return

    writer.write(tag.encode("ascii"))
    writer.u32(len(curve.keyframes))
    writer.u32(INTERPOLATIONS.get(curve.interpolation, 1))
    writer.i32(model.global_seqs.index(curve.global_sequence) if curve.global_sequence > 0 else -1)

    for frame in sorted(curve.keyframes.keys()):
        writer.u32(_ms_frame(frame))
        if dimensions == 0:
            continue
        value = curve.keyframes[frame]
        if index is not None:
            value = (value[index] * base_value,)
        elif transform is not None:
            value = transform(value)
        _write_track_value(writer, value, dimensions)

        if curve.interpolation in {"Hermite", "Bezier"}:
            in_tan = curve.handles_left[frame]
            out_tan = curve.handles_right[frame]
            if index is not None:
                in_tan = (in_tan[index] * base_value,)
                out_tan = (out_tan[index] * base_value,)
            elif transform is not None:
                in_tan = transform(in_tan)
                out_tan = transform(out_tan)
            _write_track_value(writer, in_tan, dimensions)
            _write_track_value(writer, out_tan, dimensions)


def _write_track_value(writer, value, dimensions=None):
    if dimensions == 1 or len(value) == 1:
        writer.f32(value[0])
    elif dimensions == 2:
        writer.vec2(value)
    elif dimensions == 3:
        writer.vec3(value)
    elif dimensions == 4:
        writer.vec4(value)
    else:
        writer.write(struct.pack("<%df" % len(value), *[float(v) for v in value]))


def _rotation_xyzw(value):
    return tuple(value[1:]) + (value[0],)


def _color_bgr(value):
    return tuple(reversed(value[:3]))


def _write_node(writer, model, obj, kind, display_name=None):
    writer.fixed_string(display_name or obj.name, 80)
    writer.u32(_object_id(model, obj))
    writer.i32(_parent_id(model, obj))
    writer.u32(_node_flags(kind, obj))
    _write_track(writer, "KGTR", obj.anim_loc, model, 3)
    _write_track(writer, "KGRT", obj.anim_rot, model, 4, transform=_rotation_xyzw)
    _write_track(writer, "KGSC", obj.anim_scale, model, 3)


def _write_model(writer, model, mdl_version):
    writer.write(b"MDLX")

    with writer.chunk("VERS"):
        writer.u32(mdl_version)

    with writer.chunk("MODL"):
        writer.fixed_string(model.name, 80)
        writer.fixed_string("", 260)
        _write_extent(writer, model.global_extents_min, model.global_extents_max)
        writer.u32(150)

    if model.sequences:
        with writer.chunk("SEQS"):
            for sequence in model.sequences:
                writer.fixed_string(sequence.name, 80)
                writer.u32(sequence.start)
                writer.u32(sequence.end)
                writer.f32(sequence.movement_speed if "walk" in sequence.name.lower() else 0)
                writer.u32(1 if sequence.non_looping else 0)
                writer.f32(sequence.rarity)
                writer.u32(0)
                _write_extent(writer, model.global_extents_min, model.global_extents_max)

    if model.global_seqs:
        with writer.chunk("GLBS"):
            for sequence in model.global_seqs:
                writer.u32(sequence)

    if model.textures:
        with writer.chunk("TEXS"):
            for texture in model.textures:
                writer.u32(texture.replaceable_id if texture.is_replaceable else 0)
                writer.fixed_string("" if texture.is_replaceable else texture.image_path, 260)
                writer.u32(0x3)

    if model.materials:
        with writer.chunk("MTLS"):
            for material in model.materials:
                with writer.sized():
                    writer.u32(material.priority_plane)
                    flags = 0x1 if material.use_const_color else 0
                    writer.u32(flags)
                    writer.write(b"LAYS")
                    writer.u32(len(material.layers))
                    for layer in material.layers:
                        with writer.sized():
                            flags = 0
                            flags |= 0x1 if layer.unshaded else 0
                            flags |= 0x10 if layer.two_sided else 0
                            flags |= 0x20 if layer.unfogged else 0
                            flags |= 0x40 if layer.no_depth_test else 0
                            flags |= 0x80 if layer.no_depth_set else 0
                            writer.u32(FILTER_MODES.get(layer.filter_mode, 0))
                            writer.u32(flags)
                            writer.u32(layer.texture_id or 0)
                            writer.u32(model.tvertex_anims.index(layer.texture_anim) if layer.texture_anim in model.tvertex_anims else -1)
                            writer.u32(0)
                            writer.f32(layer.alpha_value)
                            _write_track(writer, "KMTA", layer.alpha_anim, model, 1)

    if model.tvertex_anims:
        with writer.chunk("TXAN"):
            for anim in model.tvertex_anims:
                with writer.sized():
                    _write_track(writer, "KTAT", anim.translation, model, 3)
                    _write_track(writer, "KTAR", anim.rotation, model, 4, transform=_rotation_xyzw)
                    _write_track(writer, "KTAS", anim.scale, model, 3)

    if model.geosets:
        with writer.chunk("GEOS"):
            for geoset in model.geosets:
                _write_geoset(writer, model, geoset)

    if model.geoset_anims:
        with writer.chunk("GEOA"):
            for anim in model.geoset_anims:
                with writer.sized():
                    writer.f32(1.0)
                    writer.u32(0)
                    writer.vec3(_color_bgr(anim.color) if anim.color is not None else (1, 1, 1))
                    writer.u32(model.geosets.index(anim.geoset))
                    _write_track(writer, "KGAO", anim.alpha_anim, model, 1)
                    _write_track(writer, "KGAC", anim.color_anim, model, 3, transform=_color_bgr)

    _write_objects(writer, model)


def _write_geoset(writer, model, geoset):
    with writer.sized():
        writer.write(b"VRTX")
        writer.u32(len(geoset.vertices))
        for vertex in geoset.vertices:
            writer.vec3(vertex[0])

        writer.write(b"NRMS")
        writer.u32(len(geoset.vertices))
        for vertex in geoset.vertices:
            writer.vec3(vertex[1])

        writer.write(b"PTYP")
        writer.u32(1)
        writer.u32(4)

        writer.write(b"PCNT")
        writer.u32(1)
        writer.u32(len(geoset.triangles) * 3)

        writer.write(b"PVTX")
        writer.u32(len(geoset.triangles) * 3)
        for triangle in geoset.triangles:
            for index in triangle:
                writer.u16(index)

        writer.write(b"GNDX")
        writer.u32(len(geoset.vertices))
        for vertex in geoset.vertices:
            writer.write(struct.pack("<B", int(vertex[3])))

        writer.write(b"MTGC")
        writer.u32(len(geoset.matrices))
        for matrix in geoset.matrices:
            writer.u32(len(matrix))

        writer.write(b"MATS")
        matrix_indices = [model.object_indices[name] for matrix in geoset.matrices for name in matrix]
        writer.u32(len(matrix_indices))
        for index in matrix_indices:
            writer.u32(index)

        writer.u32(model.materials.index(next(mat for mat in model.materials if mat.name == geoset.mat_name)))
        writer.u32(0)
        _write_extent(writer, geoset.min_extent, geoset.max_extent)
        writer.u32(len(model.sequences))
        for _sequence in model.sequences:
            _write_extent(writer, geoset.min_extent, geoset.max_extent)

        writer.write(b"UVAS")
        writer.u32(1)
        writer.write(b"UVBS")
        writer.u32(len(geoset.vertices))
        for vertex in geoset.vertices:
            writer.vec2(vertex[2])


def _write_objects(writer, model):
    if model.objects["bone"]:
        with writer.chunk("BONE"):
            for bone in model.objects["bone"]:
                display_name = bone.name.replace(".", "_")
                if not display_name.lower().startswith("bone"):
                    display_name = "Bone_" + display_name
                with writer.sized():
                    _write_node(writer, model, bone, "bone", display_name)
                    children = [g for g in model.geosets if bone.name in [n for matrix in g.matrices for n in matrix]]
                    writer.i32(model.geosets.index(children[0]) if len(children) == 1 else -1)
                    writer.i32(model.geoset_anims.index(model.geoset_anim_map[bone.name]) if bone.name in model.geoset_anim_map else -1)

    if model.objects["light"]:
        with writer.chunk("LITE"):
            for light in model.objects["light"]:
                with writer.sized():
                    _write_node(writer, model, light, "light")
                    writer.u32(LIGHT_TYPES.get(light.type, 0))
                    writer.f32(light.atten_start)
                    writer.f32(light.atten_end)
                    writer.vec3(_color_bgr(light.color))
                    writer.f32(light.intensity)
                    writer.vec3(_color_bgr(light.amb_color))
                    writer.f32(light.amb_intensity)
                    _write_track(writer, "KLAS", light.atten_start_anim, model, 1)
                    _write_track(writer, "KLAE", light.atten_end_anim, model, 1)
                    _write_track(writer, "KLAC", light.color_anim, model, 3, transform=_color_bgr)
                    _write_track(writer, "KLAI", light.intensity_anim, model, 1)
                    _write_track(writer, "KLBI", light.amb_intensity_anim, model, 1)
                    _write_track(writer, "KLBC", light.amb_color_anim, model, 3, transform=_color_bgr)
                    _write_track(writer, "KLAV", light.visibility, model, 1)

    if model.objects["helper"]:
        with writer.chunk("HELP"):
            for helper in model.objects["helper"]:
                display_name = helper.name.replace(".", "_")
                if not display_name.lower().startswith("bone"):
                    display_name = "Bone_" + display_name
                with writer.sized():
                    _write_node(writer, model, helper, "helper", display_name)

    if model.objects["attachment"]:
        with writer.chunk("ATCH"):
            for index, attachment in enumerate(model.objects["attachment"]):
                with writer.sized():
                    _write_node(writer, model, attachment, "attachment")
                    writer.fixed_string("", 260)
                    writer.u32(index)
                    _write_track(writer, "KATV", attachment.visibility, model, 1)

    if model.objects_all:
        with writer.chunk("PIVT"):
            for obj in model.objects_all:
                writer.vec3(obj.pivot)

    if model.objects["particle"]:
        with writer.chunk("PREM"):
            for psys in model.objects["particle"]:
                with writer.sized():
                    _write_node(writer, model, psys, "particle")
                    writer.f32(psys.emission_rate)
                    writer.f32(psys.gravity)
                    writer.f32(psys.longitude)
                    writer.f32(psys.latitude)
                    writer.fixed_string(psys.model_path, 260)
                    writer.f32(psys.life_span)
                    writer.f32(psys.speed)
                    _write_track(writer, "KPEE", psys.emission_rate_anim, model, 1)
                    _write_track(writer, "KPEG", psys.gravity_anim, model, 1)
                    _write_track(writer, "KPLN", psys.longitude_anim, model, 1)
                    _write_track(writer, "KPLT", psys.latitude_anim, model, 1)
                    _write_track(writer, "KPEV", psys.visibility, model, 1)
                    _write_track(writer, "KPEL", psys.life_span_anim, model, 1)
                    _write_track(writer, "KPES", psys.speed_anim, model, 1)

    if model.objects["particle2"]:
        with writer.chunk("PRE2"):
            for psys in model.objects["particle2"]:
                with writer.sized():
                    _write_node(writer, model, psys, "particle")
                    writer.f32(psys.speed)
                    writer.f32(psys.variation)
                    writer.f32(psys.latitude)
                    writer.f32(psys.gravity)
                    writer.f32(psys.life_span)
                    writer.f32(psys.emission_rate)
                    writer.f32(psys.dimensions[1])
                    writer.f32(psys.dimensions[0])
                    writer.u32(FILTER_MODES.get(psys.filter_mode, 2))
                    writer.u32(psys.rows)
                    writer.u32(psys.cols)
                    writer.u32(2 if psys.head and psys.tail else 1 if psys.tail else 0)
                    writer.f32(psys.tail_length)
                    writer.f32(psys.time)
                    writer.vec3(_color_bgr(psys.start_color))
                    writer.vec3(_color_bgr(psys.mid_color))
                    writer.vec3(_color_bgr(psys.end_color))
                    writer.write(struct.pack("<3B", int(psys.start_alpha), int(psys.mid_alpha), int(psys.end_alpha)))
                    writer.write(b"\0")
                    writer.vec3((psys.start_scale, psys.mid_scale, psys.end_scale))
                    for values in (
                        (psys.head_life_start, psys.head_life_end, psys.head_life_repeat),
                        (psys.head_decay_start, psys.head_decay_end, psys.head_decay_repeat),
                        (psys.tail_life_start, psys.tail_life_end, psys.tail_life_repeat),
                        (psys.tail_decay_start, psys.tail_decay_end, psys.tail_decay_repeat),
                    ):
                        writer.u32(values[0])
                        writer.u32(values[1])
                        writer.u32(values[2])
                    writer.u32(psys.texture_id)
                    writer.u32(psys.priority_plane)
                    flags = 0
                    flags |= 0x10000 if psys.sort_far_z else 0
                    flags |= 0x8000 if psys.unshaded else 0
                    flags |= 0x20000 if psys.line_emitter else 0
                    flags |= 0x40000 if psys.unfogged else 0
                    flags |= 0x80000 if psys.model_space else 0
                    flags |= 0x100000 if psys.xy_quad else 0
                    writer.u32(flags)
                    _write_track(writer, "KP2S", psys.speed_anim, model, 1)
                    _write_track(writer, "KP2R", psys.variation_anim, model, 1)
                    _write_track(writer, "KP2L", psys.latitude_anim, model, 1)
                    _write_track(writer, "KP2G", psys.gravity_anim, model, 1)
                    _write_track(writer, "KP2V", psys.visibility, model, 1)
                    _write_track(writer, "KP2E", psys.emission_rate_anim, model, 1)
                    _write_track(writer, "KP2W", psys.scale_anim, model, 1, index=1, base_value=psys.dimensions[1])
                    _write_track(writer, "KP2N", psys.scale_anim, model, 1, index=0, base_value=psys.dimensions[0])

    if model.objects["ribbon"]:
        with writer.chunk("RIBB"):
            for psys in model.objects["ribbon"]:
                with writer.sized():
                    _write_node(writer, model, psys, "ribbon")
                    writer.f32(psys.dimensions[0] / 2)
                    writer.f32(psys.dimensions[0] / 2)
                    writer.f32(psys.alpha)
                    writer.vec3(_color_bgr(psys.ribbon_color))
                    writer.f32(psys.life_span)
                    writer.u32(psys.texture_id)
                    for material in model.materials:
                        if material.name == psys.ribbon_material.name:
                            writer.u32(model.materials.index(material))
                            break
                    else:
                        writer.u32(0)
                    writer.u32(psys.rows)
                    writer.u32(psys.cols)
                    writer.f32(psys.emission_rate)
                    writer.f32(psys.gravity)
                    _write_track(writer, "KRHA", None, model, 1)
                    _write_track(writer, "KRHB", None, model, 1)
                    _write_track(writer, "KRAL", psys.alpha_anim, model, 1)
                    _write_track(writer, "KRCO", psys.ribbon_color_anim, model, 3, transform=_color_bgr)
                    _write_track(writer, "KRVS", psys.visibility, model, 1)

    if model.cameras:
        with writer.chunk("CAMS"):
            for camera in model.cameras:
                with writer.sized():
                    writer.fixed_string(camera.name, 80)
                    writer.vec3(camera.pivot)
                    writer.f32(camera.field_of_view)
                    writer.f32(camera.far_clip)
                    writer.f32(camera.near_clip)
                    writer.vec3(camera.target)

    if model.objects["eventobject"]:
        with writer.chunk("EVTS"):
            for event in model.objects["eventobject"]:
                with writer.sized():
                    _write_node(writer, model, event, "eventobject")
                    _write_track(writer, "KEVT", event.track, model, 0)

    if model.objects["collisionshape"]:
        with writer.chunk("CLID"):
            for collider in model.objects["collisionshape"]:
                with writer.sized():
                    _write_node(writer, model, collider, "collisionshape")
                    writer.u32(0 if collider.type == "Box" else 2)
                    if collider.type == "Box":
                        for vertex in collider.verts:
                            writer.vec3(vertex)
                    else:
                        writer.vec3(collider.verts[0])
                        writer.f32(collider.radius)

def save(operator, context, settings, filepath="", mdl_version=800):
    scene = context.scene
    current_frame = scene.frame_current
    scene.frame_set(0)

    model = War3Model(context)
    model.from_scene(context, settings, operator.report)

    scene.frame_set(current_frame)

    writer = MDXWriter()
    _write_model(writer, model, mdl_version)
    writer.save(filepath)
