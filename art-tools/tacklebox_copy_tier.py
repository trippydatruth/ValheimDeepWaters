# Carries one tier's edits in a tackle box edit blend (make_tacklebox_edit.py) over to the other tiers:
#   - the settings changed on it (the Sanctus wood/leather and Grungit Dirt inputs that differ from VDW_ORIG's bake) go
#     to the same nodes on the other tiers (by node group and input; colours are left as each tier's own)
#   - faces given a new material on it: the lip round the seam -> each other tier's metal (an iron lip), the handle's
#     mounts -> each tier's handle material (metal on the tiers with a metal handle)
# Saves a new blend; bake the tiers with bake_tacklebox.py VDW_EDITED=1 VDW_BANDS=0 (the lip is real faces now, so
# the old painted straps and rim are left off).
#   blender -b tacklebox_edit_vN.blend --python tacklebox_copy_tier.py
#   env: VDW_OUT (new .blend), VDW_FROM (t1), VDW_ORIG (the original bake of that tier, e.g. bake_v3\tacklebox_t1_baked.blend),
#        VDW_COPY_GROUPS (Wood_Planks,Grungit Dirt,pu_leather), VDW_MOUNT_Z (faces this far above the seam are the
#        handle's mounts, default 0.1 m), VDW_LIP (metal: the lip faces become each tier's metal; none: they stay as
#        they were - for a painted rim from bake_tacklebox.py VDW_BANDS=rim instead)
import bpy, os
import numpy as np
OUT, FROM, ORIG = os.environ["VDW_OUT"], os.environ.get("VDW_FROM", "t1"), os.environ["VDW_ORIG"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
GROUPS = os.environ.get("VDW_COPY_GROUPS", "Wood_Planks,Grungit Dirt,pu_leather").split(",")
MOUNT = float(os.environ.get("VDW_MOUNT_Z", "0.1")); LIP = os.environ.get("VDW_LIP", "metal")
TIERS = [o.name.split("_")[1] for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("tacklebox_")]
def kind_of(tree): return next((g for g in GROUPS if tree.name.startswith(g)), None)
with bpy.data.libraries.load(ORIG) as (src, dst): dst.materials = ["tb_wood", "tb_metal", "tb_handle"]
orig = {m.name.split(".")[0].replace("tb_", ""): m for m in dst.materials}

# 1. the settings that changed on FROM
changes = {}   # (material kind, group kind) -> {input identifier: value}
for mk in ("wood", "metal", "handle"):
    ed = bpy.data.materials[f"tb_{mk}_{FROM}"]; og = orig[mk]
    for n in ed.node_tree.nodes:
        if n.type != 'GROUP' or not n.node_tree or not kind_of(n.node_tree): continue
        on = next((x for x in og.node_tree.nodes if x.type == 'GROUP' and x.node_tree and kind_of(x.node_tree) == kind_of(n.node_tree)), None)
        if on is None: continue
        for s in n.inputs:
            if s.is_linked or not hasattr(s, "default_value") or s.type in ('RGBA',): continue
            o = next((x for x in on.inputs if x.identifier == s.identifier), None)
            a = s.default_value; b = o.default_value if o else None
            same = np.allclose(np.array(a, float).ravel(), np.array(b, float).ravel(), atol=1e-4) if b is not None else False
            if not same: changes.setdefault((mk, kind_of(n.node_tree)), {})[s.identifier] = (s.name, a if not hasattr(a, "__len__") else tuple(a))
for k, v in changes.items(): print("CHANGED on", FROM, k, {i: (nm, round(x, 3) if isinstance(x, float) else x) for i, (nm, x) in v.items()})
for t in TIERS:
    if t == FROM: continue
    for (mk, gk), vals in changes.items():
        m = bpy.data.materials[f"tb_{mk}_{t}"]
        n = next((x for x in m.node_tree.nodes if x.type == 'GROUP' and x.node_tree and kind_of(x.node_tree) == gk), None)
        if n is None: print(f"  {t} {mk}: no {gk} node (its {mk} is another material) - skipped"); continue
        for ident, (nm, v) in vals.items():
            s = next((x for x in n.inputs if x.identifier == ident), None)
            if s is not None: s.default_value = v
        print(f"  {t} {mk} {gk}: {len(vals)} settings copied")

# 2. the newly assigned faces on FROM (handle material on faces that were wood in the original)
src_ob = bpy.data.objects[f"tacklebox_{FROM}"]; me = src_ob.data
with bpy.data.libraries.load(ORIG) as (s2, d2): d2.meshes = [m for m in s2.meshes]
orig_me = next(m for m in d2.meshes if len(m.polygons) == len(me.polygons))
co = np.array([v.co[:] for v in me.vertices]); lo, hi = co.min(0), co.max(0); k = (hi[2] - lo[2]) / 1.249; seam = lo[2] + 0.497 * k
newf = [i for i, (p, q) in enumerate(zip(me.polygons, orig_me.polygons)) if p.material_index != q.material_index]
lip = [i for i in newf if me.polygons[i].center.z < seam + MOUNT]
mounts = [i for i in newf if me.polygons[i].center.z >= seam + MOUNT]
print(f"NEW on {FROM}: {len(newf)} faces - lip {len(lip)}, handle mounts {len(mounts)}")
for t in TIERS:
    if t == FROM: continue
    tm = bpy.data.objects[f"tacklebox_{t}"].data
    handle_faces = [p.material_index for p in tm.polygons if p.material_index == 2]
    handle_slot = 2 if handle_faces else 1                     # tiers with a metal handle have no handle faces
    if LIP == "metal":
        for i in lip: tm.polygons[i].material_index = 1
    for i in mounts: tm.polygons[i].material_index = handle_slot
    print(f"  {t}: lip -> {LIP}, mounts -> {'handle' if handle_slot == 2 else 'metal'}")
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True, relative_remap=True); print("SAVED", OUT)
