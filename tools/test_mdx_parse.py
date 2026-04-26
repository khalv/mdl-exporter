import json
import sys
import traceback
from pathlib import Path

import bpy

REPO = Path(r"D:\code2\mdl-exporter")
MODEL_DIR = Path(r"C:\Users\admin\Desktop\模型")

sys.path.insert(0, str(REPO))

from export_mdl.classes.War3Model import War3Model
from export_mdl.import_mdx import MDXReader, _read_mdx


def main():
    results = []
    for path in sorted(MODEL_DIR.glob("*.mdx")):
        try:
            model = War3Model(bpy.context)
            _read_mdx(model, MDXReader(str(path)))
            results.append({
                "file": path.name,
                "ok": True,
                "geosets": len(model.geosets),
                "materials": len(model.materials),
                "textures": len(model.textures),
                "bones": len(model.objects["bone"]),
                "pivots": len(getattr(model, "pivots", [])),
            })
        except Exception as exc:
            results.append({
                "file": path.name,
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(limit=10),
            })
    print("MDX_PARSE_RESULTS_START")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("MDX_PARSE_RESULTS_END")


if __name__ == "__main__":
    main()
