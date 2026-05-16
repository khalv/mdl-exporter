import sys
from pathlib import Path

import bpy
from mathutils import Matrix

REPO = Path(r"D:\code2\mdl-exporter")
FILE = Path(r"C:\Users\admin\Desktop\模型\55993a708d1557cd618bfeb40e6edd32.mdx")

sys.path.insert(0, str(REPO))

import export_mdl
from export_mdl.classes.War3ImportSettings import War3ImportSettings
from export_mdl import import_mdx


class Reporter:
    def report(self, kind, message):
        print("REPORT", kind, message, flush=True)


settings = War3ImportSettings()
settings.global_matrix = Matrix.Identity(4)
export_mdl.register()
print("IMPORT_START", FILE, flush=True)
import_mdx.load(Reporter(), bpy.context, settings, filepath=str(FILE))
meshes = [obj.name for obj in bpy.context.scene.objects if obj.type == "MESH"]
print("IMPORT_DONE", len(bpy.context.scene.objects), len(meshes), meshes[:10], flush=True)
