# Rigs the wooden fishing rod (rod.obj, modelled in centimetres, rod along the OBJ's up axis) for Valheim:
#   - converts cm -> m (true size), keeps the OBJ's origin so it sits in the hand exactly where it does now
#   - Rod.Handle (butt + reel seat, stiff) then Rod.1..Rod.N up the blank to the tip; guides and the modelled line
#     ride along with the blank
#   - Reel.Spool: the turning drum of the centre-pin reel (both side plates, the wound line and the crank handle)
#   - marker bones (no mesh weight) the mod reads in game: Rod.Tip (where the line leaves the rod),
#     Rod.BendDir (which side the rod bends toward: the guide side), Reel.Axis (the drum's axle)
#   - Unity maps from the Substance export: Albedo = rod.png, MetallicSmoothness from OcclusionRoughnessMetallic.png
#     (metal = B, smoothness = 1 - G), Normal = normal.png
#   - preview clips: Rest, Bend (straight -> fully loaded), Reel (one turn of the drum)
#   env: VDW_OBJ, VDW_TEX_DIR, VDW_SAVE_TO, VDW_SEGMENTS (default 8), VDW_CHECK (png prefix)
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector, Quaternion

OBJ = os.environ["VDW_OBJ"]; TEX = os.environ["VDW_TEX_DIR"]; SAVE_TO = os.environ["VDW_SAVE_TO"]
NSEG = int(os.environ.get("VDW_SEGMENTS", "8"))
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
bpy.ops.wm.obj_import(filepath=OBJ)
mesh = next(o for o in bpy.data.objects if o.type == 'MESH'); mesh.name = "rod"; me = mesh.data
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
mesh.scale = tuple(s * 0.01 for s in mesh.scale)                     # centimetres -> metres
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
co = np.array([v.co[:] for v in me.vertices]); n = len(co)
lo, hi = co.min(0), co.max(0)
print(f"\n===== RIG ROD =====\n  size {tuple((hi - lo).round(3))} m (x, y, z), butt at z {lo[2]:.3f}, tip at z {hi[2]:.3f}")

# pieces
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
comp = np.full(n, -1); c = 0
for v in bm.verts:
    if comp[v.index] >= 0: continue
    st = [v]; comp[v.index] = c
    while st:
        u = st.pop()
        for e in u.link_edges:
            w = e.other_vert(u)
            if comp[w.index] < 0: comp[w.index] = c; st.append(w)
    c += 1
sizes = np.bincount(comp)
# the wound line on the reel: the piece that is wide in x and sits around the reel height, the modelled fishing line:
# the long thin piece; the blank: the piece spanning the whole length
span = np.array([co[comp == k][:, 2].ptp() for k in range(c)])
blank_k = int(np.argmax([span[k] * (sizes[k] < 2000) for k in range(c)]))
line_k = int(np.argmax([span[k] if k != blank_k else 0 for k in range(c)]))
wound_k = int(np.argmax([sizes[k] if k not in (blank_k, line_k) else 0 for k in range(c)]))
W = co[comp == wound_k]
# reel zone: around the wound line; the side plates are the flat faces of the blank piece out past the wound line
zone = (co[:, 2] > W[:, 2].min() - 0.01) & (co[:, 2] < W[:, 2].max() + 0.01) & (np.hypot(co[:, 0], co[:, 1]) > 0.016)
wx_lo, wx_hi = W[:, 0].min(), W[:, 0].max()
plates = zone & (comp == blank_k) & (((co[:, 0] < wx_lo + 0.002) & (co[:, 0] > wx_lo - 0.006)) | ((co[:, 0] > wx_hi - 0.002) & (co[:, 0] < wx_hi + 0.006)))
P_ = co[plates]
axle_c = np.array([(wx_lo + wx_hi) / 2, (P_[:, 1].min() + P_[:, 1].max()) / 2, (P_[:, 2].min() + P_[:, 2].max()) / 2])
R = max(P_[:, 1].ptp(), P_[:, 2].ptp()) / 2
plate_out = P_[:, 0].max()
print(f"  pieces: blank {blank_k} ({sizes[blank_k]} v), line {line_k} ({sizes[line_k]} v), wound line {wound_k} ({sizes[wound_k]} v)")
print(f"  reel axle (along x) through y {axle_c[1]:.4f} z {axle_c[2]:.4f} (from the side plates), plate radius {R:.4f}")
# turning part: the wound line and the crank handle (out past the outer side plate); the plates/frame stay put
handle = zone & (comp == blank_k) & (co[:, 0] > plate_out + 0.001) & (np.abs(co[:, 1] - axle_c[1]) < 0.012)
spool = (comp == wound_k) | handle
print(f"  crank handle: {handle.sum()} vertices (x {co[handle][:, 0].min():.3f}..{co[handle][:, 0].max():.3f})")
print(f"  turning drum: {spool.sum()} vertices (x {co[spool][:, 0].min():.3f}..{co[spool][:, 0].max():.3f})")

# armature
z_seat = axle_c[2] + R * 1.1                                         # stiff handle + reel seat up to just above the reel
z0, z1 = lo[2], hi[2]
arm_data = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_data)
bpy.context.scene.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects: o.select_set(False)
arm.select_set(True); bpy.ops.object.mode_set(mode='EDIT'); eb = arm_data.edit_bones
def axis_xy(z):   # the blank's centre at height z
    s = co[(comp == blank_k) & (np.abs(co[:, 2] - z) < 0.02) & ~spool]
    return (float(np.median(s[:, 0])), float(np.median(s[:, 1]))) if len(s) else (0.0, 0.0)
def P(z): x, y = axis_xy(z); return (x, y, z)
def bone(name, h, t, parent=None, connect=False, deform=True, roll=0.0):
    b = eb.new(name); b.head = Vector(h); b.tail = Vector(t); b.use_deform = deform; b.roll = roll
    if parent: b.parent = eb[parent]; b.use_connect = connect
    return b
bone("Root", (0, 0, 0), (0, 0, 0.1), deform=False)
bone("Rod.Handle", P(z0), P(z_seat), "Root")
zs = np.linspace(z_seat, z1, NSEG + 1)
names = [f"Rod.{k + 1}" for k in range(NSEG)]
for k, nm in enumerate(names):
    bone(nm, P(zs[k]), P(zs[k + 1]), "Rod.Handle" if k == 0 else names[k - 1], connect=True)
tip = np.array(P(z1))
bone("Rod.Tip", tuple(tip), tuple(tip + [0, 0, 0.03]), names[-1])                       # marker: line leaves here
bone("Rod.BendDir", tuple(tip + [0, 0.1, 0]), tuple(tip + [0, 0.13, 0]), names[-1])      # marker: bend toward +y (guide side)
xs = co[spool][:, 0]
bone("Reel.Spool", (xs.min(), axle_c[1], axle_c[2]), (xs.max(), axle_c[1], axle_c[2]), "Rod.Handle")
bone("Reel.Axis", (xs.max(), axle_c[1], axle_c[2]), (xs.max() + 0.02, axle_c[1], axle_c[2]), "Reel.Spool", connect=True)  # marker
bpy.ops.object.mode_set(mode='OBJECT')

# weights
for o in bpy.context.view_layer.objects: o.select_set(False)
mesh.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_NAME')
vg = mesh.vertex_groups
chain = [("Rod.Handle", z_seat - 0.02)] + [(nm, (zs[k] + zs[k + 1]) / 2) for k, nm in enumerate(names)]
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
for mk in ("Rod.Tip", "Rod.BendDir", "Reel.Axis"):     # markers stay in the export but move no vertices
    if mk not in vg: vg.new(name=mk)
cnt = {g.name: sum(1 for v in me.vertices for gg in v.groups if gg.group == g.index and gg.weight > 0.05) for g in vg}
print("  bones:", [b.name for b in arm_data.bones]); print("  weighted vertices per bone:", cnt)

# Unity maps from the Substance export
def load(name):
    p = os.path.join(TEX, name); return bpy.data.images.load(p) if os.path.exists(p) else None
alb, orm, nrm = load(os.environ.get("VDW_ALB", "rod.png")), load("OcclusionRoughnessMetallic.png"), load(os.environ.get("VDW_NRM", "normal.png"))
ms = None
if orm:
    orm.colorspace_settings.name = 'Non-Color'
    w, h = orm.size; px = np.empty(w * h * 4, dtype=np.float32); orm.pixels.foreach_get(px); px = px.reshape(-1, 4)
    out = np.empty_like(px); out[:, 0] = out[:, 1] = out[:, 2] = px[:, 2]; out[:, 3] = 1.0 - px[:, 1]
    path = os.path.join(TEX, "rod_Unity_MetallicSmoothness.png")
    ms = bpy.data.images.new("rod_Unity_MetallicSmoothness", w, h, alpha=True); ms.colorspace_settings.name = 'Non-Color'
    ms.pixels.foreach_set(out.ravel()); ms.filepath_raw = path; ms.file_format = 'PNG'
    if not os.path.exists(path): ms.save(); print("  saved", path)
    else: print("  exists, not overwritten:", path)
mat = bpy.data.materials.new("rod"); mat.use_nodes = True; nt = mat.node_tree; nodes, links = nt.nodes, nt.links
bsdf = next(nn for nn in nodes if nn.type == 'BSDF_PRINCIPLED')
def tex(img, x, y, nc=False):
    t = nodes.new("ShaderNodeTexImage"); t.image = img; t.location = (x, y)
    if nc: img.colorspace_settings.name = 'Non-Color'
    return t
if alb: links.new(tex(alb, -700, 300).outputs["Color"], bsdf.inputs["Base Color"])
if ms:
    sn = tex(ms, -700, 0, True); links.new(sn.outputs["Color"], bsdf.inputs["Metallic"])
    inv = nodes.new("ShaderNodeMath"); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    links.new(sn.outputs["Alpha"], inv.inputs[1]); links.new(inv.outputs["Value"], bsdf.inputs["Roughness"])
if nrm:
    nm_ = tex(nrm, -700, -320, True); nmap = nodes.new("ShaderNodeNormalMap")
    links.new(nm_.outputs["Color"], nmap.inputs["Color"]); links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
me.materials.clear(); me.materials.append(mat)

# preview clips: Rest, Bend (0 -> loaded), Reel (one turn)
WX, WY, WZ = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
def q(name, axis, deg):
    m = arm.data.bones[name].matrix_local.to_3x3(); return Quaternion((m.inverted() @ axis).normalized(), math.radians(deg))
if arm.animation_data is None: arm.animation_data_create()
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
BEND_TOTAL = 75.0                                       # degrees the tip turns at full load
weights = [((k + 1) / NSEG) ** 1.6 for k in range(NSEG)]; weights = [w / sum(weights) for w in weights]
def pose(bend, spin):
    out = {}
    for k, nm in enumerate(names): out[nm] = q(nm, WX, -bend * BEND_TOTAL * weights[k])   # -x rotation: tip toward +y (guide side)
    out["Reel.Spool"] = q("Reel.Spool", WX, spin)
    return out
for clip, frames in (("Rest", [(0, 0, 0), (1, 0, 0)]), ("Bend", [(0, 0, 0), (20, 1, 0)]), ("Reel", [(f, 0, 360 * f / 24) for f in range(25)])):
    old = bpy.data.actions.get(clip)
    if old: bpy.data.actions.remove(old)
    act = bpy.data.actions.new(clip); act.use_fake_user = True; arm.animation_data.action = act
    for f, bend, spin in frames:
        p = pose(bend, spin)
        for pb in arm.pose.bones:
            if pb.name == "Root": continue
            pb.rotation_quaternion = p.get(pb.name, Quaternion()); pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    act.use_frame_range = True; act.frame_start, act.frame_end = frames[0][0], frames[-1][0]
    if clip == "Reel": act.use_cyclic = True
arm.animation_data.action = bpy.data.actions["Rest"]
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()

# check: tip movement at full bend, drum turning
def verts():
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); c_ = np.array([v.co[:] for v in ev.to_mesh().vertices]); ev.to_mesh_clear(); return c_
a = verts()
for nm, pq in pose(1, 0).items(): arm.pose.bones[nm].rotation_quaternion = pq
bpy.context.view_layer.update(); b = verts()
ti = int(np.argmax(co[:, 2]))
print(f"  full bend: tip moves {np.linalg.norm(b[ti] - a[ti]) * 100:.0f} cm (toward +y: {(b[ti] - a[ti])[1] * 100:+.0f} cm), handle unmoved: {np.abs(b[co[:, 2] < z_seat - 0.03] - a[co[:, 2] < z_seat - 0.03]).max() < 1e-6}")
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()
arm.pose.bones["Reel.Spool"].rotation_quaternion = q("Reel.Spool", WX, 90); bpy.context.view_layer.update(); d = verts()
moved = np.linalg.norm(d - a, axis=1) > 1e-5
print(f"  reel quarter turn moves {moved.sum()} vertices (all on the drum: {bool((moved <= spool).all())})")
arm.pose.bones["Reel.Spool"].rotation_quaternion = Quaternion()

CHECK = os.environ.get("VDW_CHECK")
if CHECK:
    s = bpy.context.scene; s.render.use_border = False; s.render.resolution_percentage = 100
    s.render.engine = 'BLENDER_WORKBENCH'; s.display.shading.light = 'STUDIO'; s.display.shading.color_type = 'TEXTURE'
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'
    cam = bpy.data.objects.new("C", cd); s.collection.objects.link(cam); s.camera = cam
    r90 = math.radians(90)
    keep_action = arm.animation_data.action; arm.animation_data.action = None   # manual poses for the shots
    def shot(name, loc, rot, scale, res, bend=0.0, spin=0.0):
        for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()
        for nm, pq in pose(bend, spin).items(): arm.pose.bones[nm].rotation_quaternion = pq
        s.render.resolution_x, s.render.resolution_y = res; cd.ortho_scale = scale
        cam.location = loc; cam.rotation_euler = rot
        s.render.filepath = f"{CHECK}_{name}.png"; bpy.ops.render.render(write_still=True)
    mid = (z0 + z1) / 2
    for bend in (0.0, 0.5, 1.0):   # side view: looking along x, rod vertical, bending toward +y
        shot(f"bend{int(bend * 100)}", (5, 0.3, mid), (r90, 0, r90), 2.6, (600, 1100), bend)
    tgt = Vector((axle_c[0], axle_c[1], axle_c[2]))
    for k, spin in enumerate((0, 60, 120)):
        cam_loc = tgt + Vector((1, 0.4, 0.25)).normalized() * 3
        rot = (tgt - cam_loc).to_track_quat('-Z', 'Y').to_euler()
        shot(f"reel{k}", cam_loc, rot, 0.16, (500, 500), 0, spin)
    for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()
    arm.animation_data.action = keep_action
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO)
print("  saved", SAVE_TO)
print("===== END =====")




