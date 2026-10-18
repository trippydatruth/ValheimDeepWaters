# Rigs and animates the low-poly house fly (Sketchfab "Fly.001": separate loose parts for body, head, abdomen,
# two wings and six legs, each doubled). Parts are sorted by shape, every part follows one bone 100%:
#   Body (root, thorax) > Head, Abdomen, Wing.L/R, Leg.F/M/B.L/R
# Scaled to VDW_LENGTH (default 4.5 cm, ~3x a real fly), origin at the thorax centre, head toward -Y.
# The wings get their own material slot (see-through in Unity), the body stays opaque.
# Clips (30 fps, looping): Swim = hovering flight, Thrash = frantic buzzing, Flop = on its back kicking (on the
# ground as an item), Hooked = pinned through the thorax, legs kicking, buzzing in bursts.
# env: VDW_SAVE_TO (new .blend), VDW_LENGTH (m), VDW_TEX_DIR (where the Fly_01_* textures are)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Matrix, Quaternion, Vector

LENGTH = float(os.environ.get("VDW_LENGTH", "0.045"))
sc = bpy.context.scene
sc.render.fps = 30

mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
for o in [o for o in bpy.data.objects if o is not mesh]:
    bpy.data.objects.remove(o)

tex_dir = os.environ.get("VDW_TEX_DIR")
if tex_dir:
    for img in bpy.data.images:
        f = os.path.join(tex_dir, os.path.basename(img.filepath.replace("\\", "/")))
        if img.filepath and os.path.exists(f):
            img.filepath = f; img.reload()

# bake the object transform into the mesh
mesh.data.transform(mesh.matrix_world); mesh.matrix_world = Matrix()
me = mesh.data
co = np.array([v.co[:] for v in me.vertices])

# loose parts
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
part_of = np.full(len(co), -1); parts = []
for v in bm.verts:
    if part_of[v.index] >= 0: continue
    st = [v]; part_of[v.index] = len(parts); comp = []
    while st:
        x = st.pop(); comp.append(x.index)
        for e in x.link_edges:
            w = e.other_vert(x)
            if part_of[w.index] < 0: part_of[w.index] = len(parts); st.append(w)
    parts.append(np.array(comp))
bm.free()

L0 = co[:, 1].max() - co[:, 1].min()
groups = {}
def add(name, p): groups.setdefault(name, []).append(p)
for p in parts:
    c = co[p]; lo, hi = c.min(0), c.max(0); xc = (lo[0] + hi[0]) / 2
    side = "L" if xc < 0 else "R"
    if hi[2] - lo[2] < 0.03 * L0:                               # flat: wing (and its root piece)
        add("Wing." + side, p)
    elif abs(xc) > 0.1 * L0 and np.abs(c[:, 0]).min() > 0.08 * L0:   # off to the side: a leg
        yc = (lo[1] + hi[1]) / 2
        add("Leg." + ("F" if yc < -0.19 * L0 else "M" if yc < -0.03 * L0 else "B") + "." + side, p)
    elif hi[1] < -0.25 * L0:                                    # out front: head, eyes, mouthparts
        add("Head", p)
    elif lo[1] > -0.06 * L0:                                    # behind the thorax: abdomen
        add("Abdomen", p)
    else:
        add("Body", p)
print("PARTS", {k: len(v) for k, v in sorted(groups.items())})
assert len([k for k in groups if k.startswith("Leg.")]) == 6 and "Wing.L" in groups and "Wing.R" in groups

# origin at the thorax centre, scaled to LENGTH
th = co[np.concatenate(groups["Body"])]
origin = (th.min(0) + th.max(0)) / 2; origin[0] = 0
s = LENGTH / L0
co = (co - origin) * s
me.vertices.foreach_set("co", co.ravel()); me.update()
L = LENGTH

def pts(name): return co[np.concatenate(groups[name])]

# wings get their own material
body_mat = me.materials[0]; body_mat.name = "bait_fly"
wing_mat = body_mat.copy(); wing_mat.name = "bait_fly_wings"
me.materials.append(wing_mat)
wing_v = np.zeros(len(co), bool); wing_v[np.concatenate(groups["Wing.L"] + groups["Wing.R"])] = True
for poly in me.polygons:
    poly.material_index = 1 if wing_v[poly.vertices[0]] else 0

# bones
arm_data = bpy.data.armatures.new("Armature"); arm = bpy.data.objects.new("Armature", arm_data)
sc.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones
def bone(name, head, tail, parent=None):
    b = eb.new(name); b.head = Vector(head); b.tail = Vector(tail)
    if (b.tail - b.head).length < 1e-5: b.tail = b.head + Vector((0, 0.1 * L, 0))
    if parent: b.parent = eb[parent]
    return b
bone("Body", (0, 0, 0), (0, -0.25 * L, 0))
h = pts("Head"); bone("Head", (0, h[:, 1].max(), (h[:, 2].min() + h[:, 2].max()) / 2), (0, h[:, 1].min(), (h[:, 2].min() + h[:, 2].max()) / 2), "Body")
a = pts("Abdomen"); bone("Abdomen", (0, a[:, 1].min(), (a[:, 2].min() + a[:, 2].max()) / 2), (0, a[:, 1].max(), (a[:, 2].min() + a[:, 2].max()) / 2), "Body")
for side in "LR":
    w = pts("Wing." + side)
    root_piece = co[min(groups["Wing." + side], key=len)]          # the small piece at the wing's root
    pv = root_piece.mean(0)
    tip = w[np.argmax(np.linalg.norm(w - pv, axis=1))]
    bone("Wing." + side, pv, tip, "Body")
    for pos in "FMB":
        g = pts(f"Leg.{pos}.{side}")
        ax = np.abs(g[:, 0]); near = g[ax < ax.min() + 0.04 * L]
        hip = near[np.argmax(near[:, 2])]                             # where the leg meets the body
        foot = g[np.argmax(np.linalg.norm(g - hip, axis=1))]
        bone(f"Leg.{pos}.{side}", hip, foot, "Body")
bpy.ops.object.mode_set(mode='OBJECT')

# skin: each part follows its bone fully
for name, ps in groups.items():
    vg = mesh.vertex_groups.new(name=name)
    vg.add([int(i) for i in np.concatenate(ps)], 1.0, 'REPLACE')
mesh.parent = arm
mod = mesh.modifiers.new("Armature", 'ARMATURE'); mod.object = arm

# ---------------------------------------------------------------- animation
WX, WY, WZ = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
def q(name, axis, deg):
    m = arm.data.bones[name].matrix_local.to_3x3()
    return Quaternion((m.inverted() @ axis).normalized(), math.radians(deg))
SIG = {"L": -1, "R": 1}
LEGS = [f"Leg.{p}.{s}" for p in "FMB" for s in "LR"]

def wing(side, spread, flap):
    """spread: degrees swung out from the folded rest pose; flap: degrees up (+) / down (-)."""
    sg = SIG[side]
    return q("Wing." + side, WY, -sg * flap) @ q("Wing." + side, WZ, -sg * spread)

def leg(n, back, lift):
    """back: swing the foot backward (+) / forward (-); lift: raise the foot (+)."""
    sg = SIG[n[-1]]
    return q(n, WY, -sg * lift) @ q(n, WZ, sg * back)

def env(f, a, b, n):
    """1 inside frames [a, b) of an n-frame loop, easing in and out over 3 frames."""
    f = f % n; d = min(f - a, b - f)
    return 0.0 if f < a or f >= b else min(1.0, (d + 0.5) / 3.0)

def swim(f, n):          # hovering flight: wings out, fast beat, legs hanging back, a little bob
    p = 2 * math.pi * f / n
    o = {"Body": q("Body", WX, 3 * math.sin(2 * p)) @ q("Body", WY, 4 * math.sin(p)),
         "Head": q("Head", WZ, 6 * math.sin(p + 1)),
         "Abdomen": q("Abdomen", WX, -6 + 4 * math.sin(2 * p + 0.6))}
    for sd in "LR":
        o["Wing." + sd] = wing(sd, 58, 28 + 42 * math.sin(6 * p))        # 4-frame beat
    for k, ln in enumerate(LEGS):
        o[ln] = leg(ln, 18 + 4 * math.sin(2 * p + k), -12 + 3 * math.sin(2 * p + k * 0.7))
    return o

def thrash(f, n):        # frantic: faster, bigger beat, the body twisting, legs scrabbling
    p = 2 * math.pi * f / n
    o = {"Body": q("Body", WZ, 18 * math.sin(2 * p)) @ q("Body", WY, 22 * math.sin(3 * p + 0.5)) @ q("Body", WX, 10 * math.sin(4 * p)),
         "Head": q("Head", WZ, 14 * math.sin(4 * p + 1)),
         "Abdomen": q("Abdomen", WX, -10 + 12 * math.sin(4 * p + 0.6)) @ q("Abdomen", WZ, 10 * math.sin(2 * p))}
    for sd in "LR":
        o["Wing." + sd] = wing(sd, 62, 24 + 52 * math.sin(8 * p))        # 3-frame beat
    for k, ln in enumerate(LEGS):
        o[ln] = leg(ln, 25 * math.sin(4 * p + k * 1.1), 18 * math.sin(4 * p + k * 1.1 + 1.6))
    return o

def flop(f, n):          # knocked down on its back: legs bicycling, spinning a little, a buzz now and then
    p = 2 * math.pi * f / n
    bz = env(f, 26, 40, n)
    o = {"Body": q("Body", WZ, 10 * math.sin(p) + 25 * bz * math.sin(16 * p)) @ q("Body", WY, 180 + 6 * math.sin(2 * p)),
         "Head": q("Head", WZ, 8 * math.sin(2 * p)),
         "Abdomen": q("Abdomen", WX, 8 * math.sin(4 * p))}
    for sd in "LR":
        o["Wing." + sd] = wing(sd, 20 + 25 * bz, -10 * bz + 25 * bz * math.sin(16 * p))
    for k, ln in enumerate(LEGS):
        o[ln] = leg(ln, 30 * math.sin(4 * p + k * 1.3), 15 + 25 * math.sin(4 * p + k * 1.3 + 1.6))
    return o

def hooked(f, n):        # pinned through the thorax: nose down, legs kicking, buzzing in bursts
    p = 2 * math.pi * f / n
    bz = env(f, 0, 20, n)
    o = {"Body": q("Body", WX, 22 + 5 * math.sin(p)) @ q("Body", WZ, 8 * math.sin(p + 0.8) + 6 * bz * math.sin(16 * p)) @ q("Body", WY, 7 * math.sin(2 * p)),
         "Head": q("Head", WZ, 12 * math.sin(3 * p)) @ q("Head", WX, 6 * math.sin(2 * p + 1)),
         "Abdomen": q("Abdomen", WX, -14 + 12 * math.sin(4 * p + 0.5))}
    for sd in "LR":
        o["Wing." + sd] = wing(sd, 22 + 36 * bz, 8 + bz * (16 + 46 * math.sin(16 * p)) + (1 - bz) * 4 * math.sin(4 * p))  # 3-frame buzz
    for k, ln in enumerate(LEGS):
        o[ln] = leg(ln, 28 * math.sin(4 * p + k * 1.05), 10 + 22 * math.sin(4 * p + k * 1.05 + 1.5))
    return o

arm.animation_data_create()
names = [b.name for b in arm.data.bones]
CLIPS = (("Swim", swim, 24), ("Thrash", thrash, 24), ("Flop", flop, 48), ("Hooked", hooked, 48))
for cname, fn, n in CLIPS:
    act = bpy.data.actions.new(cname); act.use_fake_user = True
    arm.animation_data.action = act
    for f in range(n + 1):
        pose = fn(f, n)
        for bn in names:
            pb = arm.pose.bones[bn]; pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = pose.get(bn, Quaternion())
            pb.keyframe_insert("rotation_quaternion", frame=f, group=bn)
    act.use_frame_range = True; act.use_cyclic = True; act.frame_start, act.frame_end = 0, n
    for fc in act.fcurves:
        fc.modifiers.new('CYCLES')

# check: every clip moves, loops cleanly, nothing flies apart
def verts():
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); m = ev.to_mesh()
    c = np.array([v.co[:] for v in m.vertices]); ev.to_mesh_clear(); return c
for cname, fn, n in CLIPS:
    arm.animation_data.action = bpy.data.actions[cname]
    fr = []
    for f in range(n + 1):
        sc.frame_set(f); fr.append(verts())
    ext = np.array([x.max(0) - x.min(0) for x in fr]).max(0)
    print(f"CLIP {cname}: {n} frames, loop seam {np.abs(fr[0] - fr[n]).max() * 1000:.3f} mm, "
          f"largest step {max(np.linalg.norm(fr[i + 1] - fr[i], axis=1).max() for i in range(n)) * 1000:.1f} mm, "
          f"widest {ext.round(4)}")

arm.animation_data.action = bpy.data.actions["Swim"]; sc.frame_set(0)
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()
print("BONES", [(b.name, tuple(round(x, 4) for x in b.head_local)) for b in arm.data.bones])
print("SIZE", (co.max(0) - co.min(0)).round(4))
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])
print("SAVED", os.environ["VDW_SAVE_TO"])
