import json
import sys
import traceback
from pathlib import Path

import bpy

REPO = Path(r"D:\code2\mdl-exporter")
MODEL_DIR = Path(r"C:\Users\admin\Desktop\模型")

sys.path.insert(0, str(REPO))

import export_mdl
from export_mdl.classes.War3ImportSettings import War3ImportSettings
from export_mdl import import_mdx


def clear_scene():
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in list(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.images,
        bpy.data.armatures,
        bpy.data.lights,
        bpy.data.cameras,
    ):
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)


class Reporter:
    def report(self, kind, message):
        print("REPORT", kind, message)


def main():
    settings = War3ImportSettings()
    settings.global_matrix = bpy.mathutils.Matrix.Identity(4) if hasattr(bpy, "mathutils") else None
    from mathutils import Matrix

    settings.global_matrix = Matrix.Identity(4)
    export_mdl.register()
    results = []
    for path in sorted(MODEL_DIR.glob("*.mdx")):
        clear_scene()
        try:
            import_mdx.load(Reporter(), bpy.context, settings, filepath=str(path))
            mesh_count = len([obj for obj in bpy.context.scene.objects if obj.type == "MESH"])
            object_count = len(bpy.context.scene.objects)
            results.append({"file": path.name, "ok": True, "objects": object_count, "meshes": mesh_count})
        except Exception as exc:
            results.append({
                "file": path.name,
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(limit=8),
            })
    print("MDX_IMPORT_RESULTS_START")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("MDX_IMPORT_RESULTS_END")


if __name__ == "__main__":
    main()
