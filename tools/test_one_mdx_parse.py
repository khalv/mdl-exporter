import sys
from pathlib import Path

import bpy

REPO = Path(r"D:\code2\mdl-exporter")
FILE = Path(r"C:\Users\admin\Desktop\模型\55993a708d1557cd618bfeb40e6edd32.mdx")

sys.path.insert(0, str(REPO))

from export_mdl.classes.War3Model import War3Model
from export_mdl.import_mdx import MDXReader, _read_mdx

print("START", FILE, flush=True)
model = War3Model(bpy.context)
_read_mdx(model, MDXReader(str(FILE)))
print("DONE", len(model.geosets), len(model.materials), len(model.objects["bone"]), flush=True)
