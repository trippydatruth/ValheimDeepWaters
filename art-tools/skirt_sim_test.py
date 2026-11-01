# Tests the coat skirt as the mod moves it (FisherSkirt.cs: 8 skirt bones round the hips; a thigh swinging toward a
# bone's side pushes that part of the skirt out with it) in Valheim's own poses (valheim_pose.py), and builds the weights
# for it: the belt, buckle and the coat from the belt down on the game body's waist weights (so the belt can't tear or
# twist off the coat), and below the hips a growing share on the skirt bones (as export_coat_skirt.py's VDW_WIND).
# VDW_GRID=1 scores share x push combinations (gear_clip_test.py); the best (or VDW_SHARE / VDW_PUSH) is saved.
#   blender -b fisher_gear_ingame_v2.blend --python skirt_sim_test.py
#   env: VDW_POSES, VDW_SAVE_TO (new .blend), VDW_GRID, VDW_SHARE (0.8), VDW_PUSH (1.1), VDW_PREVIEW (folder, optional)
import bpy, os, sys, math, itertools, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import valheim_pose, gear_clip_test
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

SAVE_TO = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE_TO): raise SystemExit("exists, kept: " + SAVE_TO)
for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]; AW = arm.matrix_world
P = valheim_pose.Poses(os.environ["VDW_POSES"], arm); P.reset(); bpy.context.view_layer.update()
skirt, belt, body = bpy.data.objects["coat_collar_skirt"], bpy.data.objects["belt"], bpy.data.objects["fitref"]
follow = [bpy.data.objects["buckle"]]
NSK = 8
def smooth(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)

# ---------------------------------------------------------------- weights
rest = [skirt.matrix_world @ v.co for v in skirt.data.vertices]
names = {g.index: g.name for g in skirt.vertex_groups}
own = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-5 and not names[g.group].startswith("vdw_skirt")} for v in skirt.data.vertices]
_fv, _fp = gear_clip_test._world(body); _ft = BVHTree.FromPolygons(_fv, _fp)
_fw = [{body.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 1e-5} for v in body.data.vertices]
def body_w(p):
    loc, n, idx, d = _ft.find_nearest(p); poly = _fp[idx]
    inv = [1.0 / max((loc - _fv[i]).length, 1e-5) for i in poly]; s = sum(inv); acc = {}
    for i, wi in zip(poly, inv):
        for k, x in _fw[i].items(): acc[k] = acc.get(k, 0) + x * wi / s
    return acc
def top4(acc):
    t = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in t) or 1
    return {k: x / tot for k, x in t if x > 1e-4}
_bz = [(belt.matrix_world @ v.co).z for v in belt.data.vertices]; belt_hi = max(_bz)
hip_c = AW @ arm.data.bones["Hips"].head_local
def set_weights(o, ws):
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    for i, w in enumerate(ws):
        for k, x in w.items():
            g = o.vertex_groups.get(k) or o.vertex_groups.new(name=k); g.add([i], x, 'REPLACE')
pivot_z = sum((AW @ arm.data.bones[b].head_local).z for b in ("LeftUpLeg", "RightUpLeg")) / 2
hem_z = min(p.z for p in rest)
TOPOFF = [0.08]
def build(share):
    ws = []
    ramp_top = pivot_z - TOPOFF[0]
    for p, mine in zip(rest, own):
        mine = {k: x / (sum(mine.values()) or 1) for k, x in mine.items()}
        t = smooth((belt_hi + 0.02 - p.z) / 0.04)                    # the belt and below: the body's waist weights...
        acc = {k: (1 - t) * x for k, x in mine.items()}
        if t > 0:
            bw = body_w(p)
            # ...fading back to the piece's own weights from the hips down (its thigh shares)
            u = smooth((hip_c.z + 0.02 - p.z) / 0.14)
            for k, x in bw.items(): acc[k] = acc.get(k, 0) + t * (1 - u) * x
            for k, x in mine.items(): acc[k] = acc.get(k, 0) + t * u * x
        acc = top4(acc)
        # the skirt bones: none until TOPOFF below the thigh joints, growing to the full share at the hem (cloth near the
        # joints, in front of them, swung about them would flip up over the belt)
        s = share * smooth((ramp_top - p.z) / max(ramp_top - hem_z, 0.05))
        if s > 0.001:
            acc = {k: x * (1 - s) for k, x in acc.items()}
            a = (math.atan2(p.y - hip_c.y, p.x - hip_c.x) / (2 * math.pi)) % 1.0 * NSK
            b0 = int(a) % NSK; f1 = a - int(a)
            for k, x in ((f"vdw_skirt{b0}", s * (1 - f1)), (f"vdw_skirt{(b0 + 1) % NSK}", s * f1)): acc[k] = acc.get(k, 0) + x
            acc = top4(acc)
        ws.append(acc)
    set_weights(skirt, ws)
    for o in [belt] + follow: set_weights(o, [top4(body_w(o.matrix_world @ v.co)) for v in o.data.vertices])
    bpy.context.view_layer.update()

# ---------------------------------------------------------------- the mod's skirt bones (FisherSkirt.LateUpdate, legs only)
hips_rest = AW @ arm.data.bones["Hips"].matrix_local
def bone_dirs():
    """each skirt bone's direction out from the hips at rest: its skirt points' average (FisherSkirt._dirs)"""
    sums = [Vector() for _ in range(NSK)]; ws = [0.0] * NSK
    for v, p in zip(skirt.data.vertices, rest):
        for g in v.groups:
            n = skirt.vertex_groups[g.group].name
            if n.startswith("vdw_skirt"): k = int(n[9:]); sums[k] += (p - hip_c) * g.weight; ws[k] += g.weight
    return [s / w if w > 0 else Vector() for s, w in zip(sums, ws)]
PUSH = [1.1]; SIDE = [1.0]
PIVOT = os.environ.get("VDW_PIVOT", "thighs")
def drive(dirs):
    pb = arm.pose.bones; H = AW @ pb["Hips"].matrix; Hdef = H @ hips_rest.inverted()
    down = Vector((0, 0, -1))
    legs = [(AW @ pb[s + "UpLeg"].head, AW @ pb[s + "Leg"].head) for s in ("Left", "Right")]
    # the skirt turns about the thigh joints' height (VDW_PIVOT=hips: about the hips bone, 11 cm lower, as the mod did:
    # a panel swung up about a point under the thigh ended up under it)
    h = H.translation.copy() if PIVOT == "hips" else (legs[0][0] + legs[1][0]) / 2
    for k in range(NSK):
        name = f"vdw_skirt{k}"
        if name not in pb: continue
        d = dirs[k]
        if d.length < 1e-6: continue
        out = Hdef.to_3x3() @ d; out.z = 0
        if out.length < 1e-6: continue
        out.normalize(); leg = 0.0
        for a, b in legs:
            td = (b - a).normalized(); flat = Vector((td.x, td.y, 0))
            if flat.length < 1e-3: continue
            toward = flat.normalized().dot(out)
            if toward <= 0: continue
            toward = toward ** SIDE[0]                               # >1: panels to the side of the swing pushed less
            ang = math.degrees(down.angle(td)); leg = max(leg, ang * toward * PUSH[0])
        total = min(leg, 110.0)
        axis = down.cross(out).normalized()
        R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(total), 4, axis) @ Matrix.Translation(-h)
        rest_k = AW @ arm.data.bones[name].matrix_local
        pb[name].matrix = AW.inverted() @ (R @ Hdef @ rest_k)
    bpy.context.view_layer.update()

class Sim:
    def __init__(self, dirs, every=1): self.dirs, self.every, self.data = dirs, every, P.data
    def frames(self, c): return (P.frames(c) + self.every - 1) // self.every
    def apply(self, c, f): P.apply(c, f * self.every); drive(self.dirs)
    def reset(self): P.reset()

edges = [tuple(e.vertices) for e in skirt.data.edges]; rest_len = np.array([(rest[a] - rest[b]).length for a, b in edges])
low = [i for i, p in enumerate(rest) if p.z < pivot_z]
def stretch(sim):
    """mean stretch of the skirt's edges, and flips: skirt points from below the thigh joints that end up above the belt"""
    tot = 0.0; n = 0; flips = 0
    for c in P.data["clips"]:
        for f in range(sim.frames(c)):
            sim.apply(c, f); vs, _ = gear_clip_test._world(skirt); bv, _ = gear_clip_test._world(belt); bz = min(p.z for p in bv)
            L = np.array([(vs[a] - vs[b]).length for a, b in edges]); tot += float(np.mean(np.abs(L / np.maximum(rest_len, 1e-6) - 1))); n += 1
            flips += sum(1 for i in low if vs[i].z > bz)
    sim.reset(); bpy.context.view_layer.update(); return tot / max(n, 1), flips

base = gear_clip_test.score(Sim([Vector()] * NSK, 2), skirt, body, belt); st0, fl0 = stretch(Sim([Vector()] * NSK, 2))
print(f"BASE (your weights, no skirt bones): through {base['through']} ({base['depth_cm']:.0f} cm), belt {base['belt']}, stretch {st0:.3f}, flips {fl0}")
def run(cfg, every=2):
    share, push, topoff, side = cfg
    TOPOFF[0] = topoff; build(share); PUSH[0] = push; SIDE[0] = side; dirs = bone_dirs()
    s = gear_clip_test.score(Sim(dirs, every), skirt, body, belt); st, fl = stretch(Sim(dirs, every))
    return s, st, fl, dirs
def label(cfg): return f"share {cfg[0]} push {cfg[1]} from {cfg[2] * 100:.0f} cm under the joints, side falloff {cfg[3]}"
if os.environ.get("VDW_GRID", "0") == "1":
    res = []
    for cfg in itertools.product((0.8, 1.0), (1.1, 1.3), (0.04, 0.12), (1.0, 2.0)):
        s, st, fl, _ = run(cfg)
        cost = s["depth_cm"] + 4 * s["belt_cm"] + 3000 * max(0.0, st - st0) + 15 * max(0, fl - fl0)
        res.append((cost, cfg)); print(f"GRID {label(cfg)}: through {s['through']} ({s['depth_cm']:.0f} cm), belt {s['belt']}, stretch {st:.3f}, flips {fl} -> {cost:.0f}")
    res.sort(); cfg = res[0][1]
else:
    cfg = tuple(float(os.environ.get(k, d)) for k, d in (("VDW_SHARE", "0.8"), ("VDW_PUSH", "1.1"), ("VDW_TOPOFF", "0.08"), ("VDW_SIDE", "2")))
s, st, fl, dirs = run(cfg, 1)
print(f"BEST {label(cfg)}: through {s['through']} ({s['depth_cm']:.0f} cm), belt {s['belt']}, stretch {st:.3f}, flips {fl}; worst per clip {s['worst']}")
P.reset(); bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True); print("SAVED", SAVE_TO)

# previews in Valheim's poses with the skirt bones driven
PREV = os.environ.get("VDW_PREVIEW", "")
if PREV:
    os.makedirs(PREV, exist_ok=True); sim = Sim(dirs, 1)
    bpy.data.objects["body_painted"].hide_render = True; body.hide_set(False); body.hide_render = False
    bm = bpy.data.materials.new("overalls_look"); bm.use_nodes = True; bs = bm.node_tree.nodes["Principled BSDF"]; bs.inputs["Base Color"].default_value = (0.25, 0.22, 0.05, 1); bs.inputs["Roughness"].default_value = 0.8
    body.data.materials.clear(); body.data.materials.append(bm)
    sc = bpy.context.scene
    for e in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE'):
        try: sc.render.engine = e; break
        except Exception: pass
    sc.world = sc.world or bpy.data.worlds.new("w"); sc.world.use_nodes = True; sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.37, 0.4, 1)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sun.data.energy = 3.5; sun.rotation_euler = (0.8, 0.3, 2.4); sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.7
    sc.render.resolution_x, sc.render.resolution_y = 480, 620
    for clip, fr in (("run", 7), ("sit_chair", 4), ("crouch", 4), ("sneak", 6)):
        sim.apply(clip, fr); hips = AW @ arm.pose.bones["Hips"].head
        for vname, ang in (("side", 90), ("back", 150), ("front", 330)):
            a = math.radians(ang); cam.location = (hips.x + 5 * math.sin(a), hips.y - 5 * math.cos(a), hips.z - 0.05); cam.rotation_euler = (math.radians(90), 0, a)
            sc.render.filepath = os.path.join(PREV, f"{clip}_{vname}.png"); bpy.ops.render.render(write_still=True)
