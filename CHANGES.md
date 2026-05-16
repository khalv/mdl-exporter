# MDL Exporter - Blender 5.1 兼容性升级文档

## 概述

将 Warcraft MDL 导入/导出插件从 Blender 2.80 适配到 **Blender 5.1.1**，同时新增 **BLP 贴图直接加载** 功能。

- 仓库来源：`https://github.com/qq200774491/mdl-exporter`（分支 `2.8`）
- 目标版本：Blender 5.1.1（Python 3.13.9）
- 工作分支：`blender-5.1-compat`

---

## 修改文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `export_mdl/__init__.py` | 修改 | `bl_info` 版本号更新 |
| `export_mdl/blp_reader.py` | **新增** | BLP 贴图解码器（支持 BLP1/BLP2） |
| `export_mdl/classes/War3AnimationCurve.py` | 修改 | 适配 Blender 5.x 分层 Action 系统 |
| `export_mdl/classes/War3Model.py` | 修改 | Mesh/Material/Normals API 适配 + BLP 加载 + 原始 bug 修复 |
| `export_mdl/ui/WAR3_MT_add_object.py` | 修改 | Menu `bl_options` 修复 |
| `export_mdl/ui/WAR3_PT_billboard_panel.py` | 修改 | LAMP 类型检查更新 |

统计：**6 个文件，275 行新增，46 行删除**

---

## 详细修改内容

### 1. `export_mdl/__init__.py` — 版本号更新

- `"blender": (2, 80, 0)` → `"blender": (4, 0, 0)`

### 2. `export_mdl/blp_reader.py` — BLP 贴图解码器（新增）

新增 223 行的 BLP 格式读取模块，支持：

| 格式 | 压缩类型 | 状态 |
|------|----------|------|
| BLP2 | Palette（调色板） | 支持，含 1/4/8 位 alpha |
| BLP2 | DXT1 | 支持 |
| BLP2 | DXT3 | 支持 |
| BLP2 | DXT5 | 支持 |
| BLP2 | 无压缩 BGRA | 支持 |
| BLP1 | JPEG | 支持，自动修复 CMYK 通道顺序 |
| BLP1 | Palette（调色板） | 支持 |

导入时自动查找：先找 `.png`，找不到则自动解码同目录下的 `.blp` 文件。

### 3. `export_mdl/classes/War3AnimationCurve.py` — Action 系统适配

**问题**：Blender 5.x 将 Action 重构为分层系统（Layered Actions），`action.fcurves` 属性不再直接存在于 Action 对象上。

**修复**：新增 `_find_fcurve()` 辅助函数，遍历 `action.layers → strips → channelbags → fcurves` 来查找 FCurve。影响两处：
- 导入时写入动画后查找 FCurve（`to_fcurves` 方法，第 144 行）
- 导出时读取动画数据（`get` 方法，第 378 行）

### 4. `export_mdl/classes/War3Model.py` — 核心 API 适配

#### 4.1 Mesh API 适配（Blender 4.0+ 移除的 API）

| 旧 API | 新 API | 原因 |
|--------|--------|------|
| `obj.data.use_auto_smooth` | 删除 | Blender 4.1 移除，自动平滑现在始终启用 |
| `obj.data.auto_smooth_angle` | 删除 | 同上 |
| `EDGE_SPLIT` modifier | 删除 | 已废弃，由 `sharp_edge` 属性替代 |
| `mesh.calc_normals_split()` | 删除 | Blender 4.1 移除，法线数据自动可用 |
| `tri.use_smooth` / `mesh.vertices[v].normal` | `mesh.corner_normals[loop].vector` | 逐角法线，自动处理平滑/锐边 |
| `mesh.uv_layers.active.data[loop].uv` | `mesh.uv_layers.active.uv[loop].vector` | UV 访问新 API |
| `polygon.use_smooth = True` | 删除 | 网格默认平滑着色 |
| `mesh.loops[i].vertex_index` | 保持不变 | 验证仍可用 |
| `uvs.data[i].uv = (...)` | `uvs.uv[i].vector = (...)` | UV 写入新 API |

#### 4.2 Material API 适配（Blender 4.0 EEVEE-Next）

| 旧 API | 处理 |
|--------|------|
| `mat.blend_method` | 删除（EEVEE-Next 移除） |
| `mat.shadow_method` | 删除（EEVEE-Next 移除） |

#### 4.3 节点查找国际化兼容

| 旧方式 | 新方式 | 原因 |
|--------|--------|------|
| `nodes.get('Principled BSDF')` | `next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')` | 中文界面下节点名为"原理化 BSDF" |
| `nodes.get('Material Output')` | `next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')` | 中文界面下节点名为"材质输出" |

#### 4.4 其他修复

| 修改 | 说明 |
|------|------|
| `obj.type in ('LAMP', 'LIGHT')` → `obj.type == 'LIGHT'` | `LAMP` 在 2.80 已重命名 |
| `obj.data.mdl_data` → `obj.data.mdl_light` | 原始代码 bug：属性名拼写错误 |
| `context.collection.objects.link(obj)` | 添加重复链接检查，防止 `light_add` 操作符重复链接 |
| BLP 贴图加载 | 新增 `.blp` 自动解码，含 CMYK→RGB 通道修复 |

### 5. `export_mdl/ui/WAR3_MT_add_object.py` — Menu 选项修复

- `bl_options = {'REGISTER', 'UNDO'}` → `bl_options = {'SEARCH_ON_KEY_PRESS'}`
- Blender 5.x 不再允许 Menu 类使用 `REGISTER`/`UNDO` 选项

### 6. `export_mdl/ui/WAR3_PT_billboard_panel.py` — 类型检查更新

- `obj.type in ('LAMP', 'LIGHT')` → `obj.type == 'LIGHT'`

---

## 安装方法

将 `export_mdl` 文件夹复制到：
```
<Blender安装目录>\5.1\scripts\addons_core\export_mdl\
```

在 Blender 中启用：**编辑 → 偏好设置 → 插件 → 搜索 "MDL" → 勾选启用**

---

## 使用方法

- **导入**：文件 → 导入 → Warcraft MDL (.mdl)
- **导出**：文件 → 导出 → Warcraft MDL (.mdl)
- 导入时自动加载同目录下的 `.blp` 贴图，无需手动转换为 `.png`

---

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 插件注册（Blender 5.1.1） | 通过 |
| MDL 导出（简单模型） | 通过 |
| MDL 导入（简单模型） | 通过 |
| MDL 导入（真实模型，50 骨骼 2873 顶点） | 通过 |
| 导入→导出往返测试（59884 行 MDL） | 通过 |
| BLP1 JPEG 贴图加载 | 通过 |
| BLP 颜色通道修复 | 通过 |

---

## 不需要修改的部分（已验证兼容）

- `export_mdl.py`（MDL 文件写入）
- `import_mdl.py`（MDL 文件解析）
- `utils.py`
- 所有 `operators/*.py`
- 所有 `properties/*.py`
- 其余 `ui/*.py` 面板
- `mesh.calc_loop_triangles()` — glTF 插件仍在使用
- `normals_split_custom_set_from_vertices()` — glTF 插件仍在使用
- `register_class/unregister_class` 注册模式
- `TOPBAR_MT_file_export/import` 菜单钩子
- `orientation_helper` 装饰器
