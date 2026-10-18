# Rigs any rod model (OBJ in centimetres, rod along +Z, guides on the +Y side) the same way as the wooden rod, so the
# mod bends it and turns its reel:
#   - scaled evenly by VDW_THICK (handle and reel in proportion), then only the blank above the reel lengthened so the
#     whole rod is VDW_LENGTH metres; guides slide up with it without stretching
#   - bones: Root > Rod.Handle (butt to just past the reel, stiff) > Rod.1..N up the blank; Reel.Spool (the turning
#     part of the reel) with the marker Reel.Axis along its axle; markers Rod.Tip, Rod.BendDir (+Y) and Rod.Grip
#   - Unity maps <name>_Unity_Albedo / MetallicSmoothness / Normal
# env: VDW_OBJ, VDW_NAME, VDW_SAVE_TO, VDW_TEX_OUT, VDW_ALB, VDW_NRM, and VDW_ORM (Occlusion/Roughness/Metallic) or
#      VDW_METAL + VDW_ROUGH; VDW_SPOOL_PARTS (loose-part indices that turn, comma list), VDW_SPOOL_AXIS (x|y|z),
#      VDW_SPOOL_PIVOT (x,y,z in the OBJ's cm; default the turning parts' centre), VDW_GRIP_Z (cm, where the hand
#      holds), VDW_SEAT_Z (cm, top of the stiff handle - past the reel and any grip above it), VDW_LENGTH (2.85),
#      VDW_THICK (2.0), VDW_SEGMENTS (8)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Matrix, Vector

NAME = os.environ["VDW_NAME"]; L = float(os.environ.get("VDW_LENGTH", "2.85")); K = float(os.environ.get("VDW_THICK", "2.0"))
NSEG = int(os.environ.get("VDW_SEGMENTS", "8")); OUT = os.environ["VDW_TEX_OUT"]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.wm.obj_import(filepath=os.environ["VDW_OBJ"])
mesh = next(o for o in bpy.data.objects if o.type == 'MESH'); mesh.name = NAME; me = mesh.data; me.name = NAME
me.transform(mesh.matrix_world); mesh.matrix_world = Matrix()
# A low-poly blank has rings far apart: skinned, each long section stays straight and the bend kinks at the rings.
# Cut every long lengthwise edge into ~2 cm pieces (before scaling) so the blank curves smoothly.
bm = bmesh.new(); bm.from_mesh(me)
groups = {}
for e in bm.edges:
    dz = abs(e.verts[0].co.z - e.verts[1].co.z)
    if dz > 2.0: groups.setdefault(int(dz // 2.0), []).append(e)
for cuts, edges in sorted(groups.items(), reverse=True):
    edges = [e for e in edges if e.is_valid]
    if edges: bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
bm.to_mesh(me); bm.free(); me.update()
co_cm = np.array([v.co[:] for v in me.vertices]); n = len(co_cm)

# loose parts (same order as the inspection script)
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); comp = np.full(n, -1); c = 0
for v in bm.verts:
    if comp[v.index] >= 0: continue
    st = [v]; comp[v.index] = c
    while st:
        u = st.pop()
        for e in u.link_edges:
            w = e.other_vert(u)
            if comp[w.index] < 0: comp[w.index] = c; st.append(w)
    c += 1
bm.free()
spool_parts = [int(x) for x in os.environ.get("VDW_SPOOL_PARTS", "").split(",") if x.strip()]
spool = np.isin(comp, spool_parts)
print(f"RIG {NAME}: {n} verts, {c} parts; turning parts {spool_parts} = {[int((comp == p).sum()) for p in spool_parts]} verts")

# reel zone: every part that isn't long (blank, line) and sits low on the rod
zlo, zhi = co_cm[:, 2].min(), co_cm[:, 2].max(); Lcm = zhi - zlo
span = np.array([np.ptp(co_cm[comp == k][:, 2]) for k in range(c)])
long_parts = [k for k in range(c) if span[k] > 0.4 * Lcm]
low = [k for k in range(c) if k not in long_parts and co_cm[comp == k][:, 2].max() < zlo + 0.45 * Lcm]
seat_cm = max(co_cm[comp == k][:, 2].max() for k in low) + 0.8 if low else zlo + 0.25 * Lcm
if os.environ.get("VDW_SEAT_Z"): seat_cm = float(os.environ["VDW_SEAT_Z"])     # where the stiff handle ends (cm)
print(f"  long parts (blank, line) {long_parts}; handle and reel up to {seat_cm - zlo:.1f} cm from the butt")

# --- scale: evenly by K, then the blank above the seat stretched so the rod is L long
co = (co_cm - np.array([0, 0, zlo])) * 0.01 * K
seat = (seat_cm - zlo) * 0.01 * K; top = Lcm * 0.01 * K
stretch = (L - seat) / (top - seat)
def zmap(z): return np.where(z > seat, seat + (z - seat) * stretch, z)
new = co.copy()
for k in range(c):
    m = comp == k
    if k in long_parts: new[m, 2] = zmap(co[m, 2])                         # blank, line: stretched
    elif co[m, 2].min() > seat:                                           # guides: slide up, keep their shape
        zc = co[m, 2].mean(); new[m, 2] = co[m, 2] + (zmap(np.array([zc]))[0] - zc)
me.vertices.foreach_set("co", new.ravel()); me.update(); co = new
print(f"  scaled x{K} evenly, blank stretched x{stretch:.2f}: {np.ptp(co[:, 2]):.2f} m long, handle {seat:.2f} m, "
      f"{np.ptp(co[:, 0]) * 100:.1f} x {np.ptp(co[:, 1]) * 100:.1f} cm across")

# --- armature
blank_k = max(long_parts, key=lambda k: (comp == k).sum())
def axis_xy(z):
    s = co[(comp == blank_k) & (np.abs(co[:, 2] - z) < 0.03)]
    return (float(np.median(s[:, 0])), float(np.median(s[:, 1]))) if len(s) else (0.0, 0.0)
def P(z): x, y = axis_xy(z); return (x, y, z)
arm_data = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_data)
bpy.context.scene.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT'); eb = arm_data.edit_bones
def bone(name, h, t, parent=None, connect=False):
    b = eb.new(name); b.head = Vector(h); b.tail = Vector(t)
    if parent: b.parent = eb[parent]; b.use_connect = connect
    return b
bone("Root", (0, 0, 0), (0, 0, 0.1))
bone("Rod.Handle", P(0.0), P(seat), "Root")
zs = np.linspace(seat, L, NSEG + 1); names = [f"Rod.{i + 1}" for i in range(NSEG)]
for i, nm in enumerate(names): bone(nm, P(zs[i]), P(zs[i + 1]), "Rod.Handle" if i == 0 else names[i - 1], connect=True)
tip = np.array(P(L))
bone("Rod.Tip", tuple(tip), tuple(tip + [0, 0, 0.03]), names[-1])
bone("Rod.BendDir", tuple(tip + [0, 0.1, 0]), tuple(tip + [0, 0.13, 0]), names[-1])
gz = (float(os.environ["VDW_GRIP_Z"]) - zlo) * 0.01 * K if os.environ.get("VDW_GRIP_Z") else seat * 0.45
g = np.array(P(gz)); bone("Rod.Grip", tuple(g), tuple(g + [0, 0, 0.03]), "Rod.Handle")
if spool.any():
    S = co[spool]
    if os.environ.get("VDW_SPOOL_PIVOT"):
        pv = (np.array([float(x) for x in os.environ["VDW_SPOOL_PIVOT"].split(",")]) - np.array([0, 0, zlo])) * 0.01 * K
    else:
        pv = (S.min(0) + S.max(0)) / 2
    ax = {"x": np.array([1, 0, 0]), "y": np.array([0, 1, 0]), "z": np.array([0, 0, 1])}[os.environ.get("VDW_SPOOL_AXIS", "x")]
    bone("Reel.Spool", tuple(pv - ax * 0.01), tuple(pv + ax * 0.01), "Rod.Handle")
    bone("Reel.Axis", tuple(pv + ax * 0.01), tuple(pv + ax * 0.03), "Reel.Spool", connect=True)
bpy.ops.object.mode_set(mode='OBJECT')

# --- weights: handle and reel stiff, the blank (and line, guides) blended up the chain, the turning reel on its bone
mesh.parent = arm; mod = mesh.modifiers.new("Armature", 'ARMATURE'); mod.object = arm
vg = {b.name: mesh.vertex_groups.new(name=b.name) for b in arm_data.bones if b.name != "Root"}
chain = [("Rod.Handle", seat - 0.02)] + [(nm, (zs[i] + zs[i + 1]) / 2) for i, nm in enumerate(names)]
for i in range(n):
    if spool[i]: vg["Reel.Spool"].add([i], 1.0, 'REPLACE'); continue
    z = co[i, 2]
    if z <= chain[0][1]: vg["Rod.Handle"].add([i], 1.0, 'REPLACE'); continue
    if z >= chain[-1][1]: vg[chain[-1][0]].add([i], 1.0, 'REPLACE'); continue
    for j in range(len(chain) - 1):
        (a, za), (b, zb) = chain[j], chain[j + 1]
        if za <= z <= zb:
            t = (z - za) / (zb - za)
            if 1 - t > 0.001: vg[a].add([i], 1 - t, 'REPLACE')
            if t > 0.001: vg[b].add([i], t, 'REPLACE')
            break
print("  bones", [b.name for b in arm_data.bones])
print(f"  grip {gz:.2f} m up from the butt; tip at {L:.2f} m; reel turns: {bool(spool.any())}")

# --- Unity maps
def load(p):
    im = bpy.data.images.load(p); w, h = im.size; return np.array(im.pixels[:], np.float32).reshape(h, w, 4), w, h
def save(px, w, h, kind):
    im = bpy.data.images.new(f"{NAME}_Unity_{kind}", w, h, alpha=True); im.pixels[:] = px.ravel()
    path = os.path.join(OUT, f"{NAME}_Unity_{kind}.png"); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); return path
os.makedirs(OUT, exist_ok=True)
a, w, h = load(os.environ["VDW_ALB"]); a[..., 3] = 1; p_alb = save(a, w, h, "Albedo")
if os.environ.get("VDW_ORM"):
    o, w2, h2 = load(os.environ["VDW_ORM"]); met, rough = o[..., 2], o[..., 1]
else:
    m_, w2, h2 = load(os.environ["VDW_METAL"]); r_, _, _ = load(os.environ["VDW_ROUGH"])
    if r_.shape != m_.shape:
        ri = bpy.data.images.load(os.environ["VDW_ROUGH"]); ri.scale(w2, h2); r_ = np.array(ri.pixels[:], np.float32).reshape(h2, w2, 4)
    met, rough = m_[..., 0], r_[..., 0]
ms = np.zeros((h2, w2, 4), np.float32); ms[..., 0] = ms[..., 1] = ms[..., 2] = met; ms[..., 3] = 1 - rough
p_ms = save(ms, w2, h2, "MetallicSmoothness")
nn, w3, h3 = load(os.environ["VDW_NRM"]); p_n = save(nn, w3, h3, "Normal")
print(f"  maps: metallic {met.mean():.2f}, smoothness {(1 - rough).mean():.2f}")
mat = bpy.data.materials.new(NAME); mat.use_nodes = True; nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]; Lk = nt.links.new
def img(p, color=True):
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(p)
    if not color: t.image.colorspace_settings.name = "Non-Color"
    return t
Lk(img(p_alb).outputs["Color"], bsdf.inputs["Base Color"])
t = img(p_ms, False); sep = nt.nodes.new("ShaderNodeSeparateColor"); Lk(t.outputs["Color"], sep.inputs["Color"]); Lk(sep.outputs["Red"], bsdf.inputs["Metallic"])
inv = nt.nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1; Lk(t.outputs["Alpha"], inv.inputs[1]); Lk(inv.outputs[0], bsdf.inputs["Roughness"])
t = img(p_n, False); nm_ = nt.nodes.new("ShaderNodeNormalMap"); Lk(t.outputs["Color"], nm_.inputs["Color"]); Lk(nm_.outputs["Normal"], bsdf.inputs["Normal"])
me.materials.clear(); me.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])
print("SAVED", os.environ["VDW_SAVE_TO"])
