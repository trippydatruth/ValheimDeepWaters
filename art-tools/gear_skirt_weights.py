# Weights a long coat's skirt for Valheim's own movements, tuned against them: below the hip joints every point is shared
# between the Hips and the thigh on its side (more thigh further down; front and back panels set apart; a soft blend
# across the middle seam; optionally some shin at the front hem), above them it keeps its own weights, with a band to
# blend the two. The belt, buckle and the coat from the belt down to the hip joints take the game body's own waist weights
# (smooth all round), so they always move together and the belt never tears at the open front.
# VDW_GRID=1 tries the settings below against every sampled frame of Valheim's run, jog, sneak, chair/ground sit and
# crouch (gear_clip_test.py) and keeps the best; otherwise the VDW_* settings are used as given.
#   blender -b fisher_gear_ingame_v2.blend --python gear_skirt_weights.py
#   env: VDW_POSES (VdwPoseSampler json), VDW_SAVE_TO (new .blend), VDW_SKIRT (coat_collar_skirt), VDW_BELT (belt),
#        VDW_FOLLOW (buckle), VDW_FRONT, VDW_BACK, VDW_SEAM, VDW_KNEE, VDW_BAND, VDW_GRID, VDW_EVERY (frame step, 2)
import bpy, os, sys, itertools, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import valheim_pose, gear_clip_test
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SAVE_TO = os.environ["VDW_SAVE_TO"]
if os.path.exists(SAVE_TO): raise SystemExit("exists, kept: " + SAVE_TO)
for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
P = valheim_pose.Poses(os.environ["VDW_POSES"], arm); P.reset(); bpy.context.view_layer.update()
skirt = bpy.data.objects[os.environ.get("VDW_SKIRT", "coat_collar_skirt")]
belt = bpy.data.objects[os.environ.get("VDW_BELT", "belt")]
follow = [bpy.data.objects[n] for n in os.environ.get("VDW_FOLLOW", "buckle").split(",") if n]
body = bpy.data.objects["fitref"]
EVERY = int(os.environ.get("VDW_EVERY", "2"))

def smooth(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
B = lambda n: arm.matrix_world @ arm.data.bones[n].head_local
hipL, hipR = B("LeftUpLeg"), B("RightUpLeg"); top_z = min(hipL.z, hipR.z); mid_x = (hipL.x + hipR.x) / 2
left_sign = 1 if hipL.x > mid_x else -1
# VDW_INFLATE (m): the skirt below the hip joints stood that much further off the legs at the hem (none at the hips),
# along its normals - room for a thigh to move inside it
INFLATE = float(os.environ.get("VDW_INFLATE", "0"))
if INFLATE > 0:
    _mw = skirt.matrix_world; _inv = _mw.inverted()
    _rest = [_mw @ v.co for v in skirt.data.vertices]
    _top = min((arm.matrix_world @ arm.data.bones[b].head_local).z for b in ("LeftUpLeg", "RightUpLeg")); _hem = min(p.z for p in _rest)
    for v, p in zip(skirt.data.vertices, _rest):
        t = max(0.0, min(1.0, (_top - p.z) / max(_top - _hem, 0.05))); t = t * t * (3 - 2 * t)
        n = (_mw.to_3x3() @ v.normal).normalized()
        v.co = _inv @ (p + n * INFLATE * t)
    print(f"INFLATE skirt up to {INFLATE * 100:.1f} cm off the legs at the hem")
mw = skirt.matrix_world; rest = [mw @ v.co for v in skirt.data.vertices]
hem_z = min(p.z for p in rest)
names = {g.index: g.name for g in skirt.vertex_groups}
own = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-5} for v in skirt.data.vertices]
own = [{k: x / (sum(w.values()) or 1) for k, x in w.items()} for w in own]
hip_y = B("Hips").y

# the game body's own weights (fitref) at the nearest spot: smooth all round the waist (hips and spine), so a belt and
# the coat under it on these never tear apart at the open front (each front half follows its own leg below)
_fv, _fp = gear_clip_test._world(body); _ft = BVHTree.FromPolygons(_fv, _fp)
_fw = [{body.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 1e-5} for v in body.data.vertices]
def body_w(p):
    loc, n, idx, d = _ft.find_nearest(p); poly = _fp[idx]
    inv = [1.0 / max((loc - _fv[i]).length, 1e-5) for i in poly]; s = sum(inv); acc = {}
    for i, wi in zip(poly, inv):
        for k, x in _fw[i].items(): acc[k] = acc.get(k, 0) + x * wi / s
    top4 = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top4) or 1
    return {k: x / tot for k, x in top4}
_bz = [(belt.matrix_world @ v.co).z for v in belt.data.vertices]; belt_lo, belt_hi = min(_bz), max(_bz)
def base_w(p, mine):
    """above the belt the piece's own weights; from the belt down to the hip joints the body's waist weights"""
    t = smooth((belt_hi + 0.02 - p.z) / 0.04)                         # 0 above the belt, 1 from its middle down
    if t <= 0: return mine
    bw = body_w(p); acc = {k: (1 - t) * x for k, x in mine.items()}
    for k, x in bw.items(): acc[k] = acc.get(k, 0) + t * x
    return acc

def skirt_weights(front, back, seam, knee, band):
    out = []
    for p, mine0 in zip(rest, own):
        mine = base_w(p, mine0)
        d = smooth((top_z - p.z) / max(top_z - hem_z, 0.05))          # 0 at the hip joints, 1 at the hem
        if p.z > top_z:
            top4 = sorted(mine.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top4) or 1
            out.append({kk: x / tot for kk, x in top4}); continue
        fb = smooth((p.y - (hip_y - 0.02)) / 0.10)                    # 0 front (the body faces -Y), 1 back
        leg = d * (front * (1 - fb) + back * fb)
        sL = smooth((left_sign * (p.x - mid_x) + seam) / (2 * seam)) if seam > 0 else float(left_sign * (p.x - mid_x) > 0)
        k = knee * d * d * (1 - fb)                                    # the front hem partly on the shin
        w = {"Hips": 1 - leg}
        for side, share in (("Left", sL), ("Right", 1 - sL)):
            if share <= 0: continue
            w[side + "UpLeg"] = w.get(side + "UpLeg", 0) + leg * share * (1 - k)
            if k > 0: w[side + "Leg"] = w.get(side + "Leg", 0) + leg * share * k
        f = smooth((top_z - p.z) / band)                              # blend in from the piece's own weights
        acc = {kk: (1 - f) * x for kk, x in mine.items()}
        for kk, x in w.items(): acc[kk] = acc.get(kk, 0) + f * x
        top4 = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top4) or 1
        out.append({kk: x / tot for kk, x in top4 if x > 1e-4})
    return out

def set_weights(o, ws):
    for g in list(o.vertex_groups): o.vertex_groups.remove(g)
    for i, w in enumerate(ws):
        for k, x in w.items():
            g = o.vertex_groups.get(k) or o.vertex_groups.new(name=k); g.add([i], x, 'REPLACE')

def follow_skirt(o):
    """each point takes the weights of the nearest spot of the skirt (blended over that face's corners)"""
    sv = rest; sp = [tuple(p.vertices) for p in skirt.data.polygons]; t = BVHTree.FromPolygons(sv, sp)
    sw = [{skirt.vertex_groups[g.group].name: g.weight for g in v.groups} for v in skirt.data.vertices]
    ws = []
    for v in o.data.vertices:
        p = o.matrix_world @ v.co; loc, n, idx, d = t.find_nearest(p)
        poly = sp[idx]; cs = [sv[i] for i in poly]
        inv = [1.0 / max((loc - c).length, 1e-5) for c in cs]; s = sum(inv)
        acc = {}
        for i, wi in zip(poly, inv):
            for k, x in sw[i].items(): acc[k] = acc.get(k, 0) + x * wi / s
        top4 = sorted(acc.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top4) or 1
        ws.append({k: x / tot for k, x in top4})
    set_weights(o, ws)

# stretch and flip-ups, so a setting can't win by tearing the cloth
edges = [tuple(e.vertices) for e in skirt.data.edges]
rest_len = np.array([(rest[a] - rest[b]).length for a, b in edges])
def damage():
    stretch = 0.0; flips = 0; n = 0
    for clip in P.data["clips"]:
        for f in range(0, P.frames(clip), EVERY):
            P.apply(clip, f)
            vs, _ = gear_clip_test._world(skirt); bv, _ = gear_clip_test._world(belt)
            L = np.array([(vs[a] - vs[b]).length for a, b in edges]); r = L / np.maximum(rest_len, 1e-6)
            stretch += float(np.mean(np.abs(r - 1))); n += 1
            bz = min(p.z for p in bv); flips += sum(1 for i, p in enumerate(vs) if rest[i].z < top_z and p.z > bz)
    P.reset(); bpy.context.view_layer.update()
    return stretch / max(n, 1), flips

def on_body(o):
    set_weights(o, [body_w(o.matrix_world @ v.co) for v in o.data.vertices])

def evaluate(cfg):
    set_weights(skirt, skirt_weights(*cfg)); on_body(belt)
    for o in follow: on_body(o)
    bpy.context.view_layer.update()
    clips = list(P.data["clips"])
    s = gear_clip_test.score(_Sub(P, EVERY), skirt, body, belt)
    st, fl = damage()
    return s, st, fl

class _Sub:
    """the poses, every EVERY-th frame only (quicker grid)"""
    def __init__(self, P, every): self.P, self.every, self.data = P, every, P.data
    def frames(self, clip): return (P.frames(clip) + self.every - 1) // self.every
    def apply(self, clip, f): self.P.apply(clip, f * self.every)
    def reset(self): self.P.reset()

base = gear_clip_test.score(_Sub(P, EVERY), skirt, body, belt); st0, fl0 = damage()
print(f"BASE (its own weights): through {base['through']} ({base['depth_cm']:.0f} cm), belt {base['belt']}, stretch {st0:.3f}, flips {fl0}")
env = lambda k, d: float(os.environ.get(k, d))
if os.environ.get("VDW_GRID", "0") == "1":
    results = []
    for cfg in itertools.product((0.6, 0.75, 1.0), (0.3, 0.5), (0.04,), (0.0, 0.3), (0.10,)):
        s, st, fl = evaluate(cfg)
        cost = s["depth_cm"] + 4 * s["belt_cm"] + 3000 * max(0.0, st - st0) + 20 * fl
        results.append((cost, cfg, s, st, fl))
        print(f"GRID front {cfg[0]} back {cfg[1]} knee {cfg[3]}: through {s['through']} ({s['depth_cm']:.0f} cm), belt {s['belt']} ({s['belt_cm']:.0f} cm), stretch {st:.3f}, flips {fl} -> {cost:.0f}")
    results.sort(key=lambda r: r[0]); best = results[0][1]
else:
    best = (env("VDW_FRONT", "0.75"), env("VDW_BACK", "0.7"), env("VDW_SEAM", "0.04"), env("VDW_KNEE", "0"), env("VDW_BAND", "0.10"))
s, st, fl = evaluate(best)
print(f"BEST front {best[0]} back {best[1]} seam {best[2]} knee {best[3]} band {best[4]}: through {s['through']} ({s['depth_cm']:.0f} cm), "
      f"belt {s['belt']} ({s['belt_cm']:.0f} cm), stretch {st:.3f}, flips {fl}; worst per clip {s['worst']}")
P.reset(); bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True)
print("SAVED", SAVE_TO)
