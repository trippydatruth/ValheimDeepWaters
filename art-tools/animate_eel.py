# Swim / Thrash / Flop for an eel rig from rig_eel.py (Root, Head, Spine..SpineN, Pincer.L/R, Gill.L/R).
# Swim is a snake-like travelling wave: the body follows a sine wave that runs from the neck to the tail and grows
# toward the tail. Each bone gets the bend between its own direction on the wave and its parent's, so the chain
# traces the curve exactly. Every clip loops (last frame = first frame), keyed every frame with cyclic curves.
import bpy, math, os
from mathutils import Quaternion, Vector

SAVE_TO = os.environ.get("VDW_SAVE_TO", "")
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
scene = bpy.context.scene; scene.render.fps = 30
HAS = set(b.name for b in arm.data.bones)
SP = [n for n in ["Spine"] + [f"Spine{k}" for k in range(1, 40)] if n in HAS]
N = len(SP)
ys = [arm.data.bones[n].head_local.y for n in SP] + [arm.data.bones[SP[-1]].tail_local.y]
LS = ys[-1] - ys[0]                                    # spine length
u_mid = [((ys[k] + ys[k + 1]) / 2 - ys[0]) / LS for k in range(N)]
WZ, WX, WY = Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))
def q(name, axis, deg):
    if name not in HAS: return Quaternion()
    m = arm.data.bones[name].matrix_local.to_3x3()
    return Quaternion((m.inverted() @ axis).normalized(), math.radians(deg))

def wave_angles(phase, amp, wavelength, grow=0.85, curl=0.0, curl_phase=0.0):
    """Absolute heading (degrees) of each spine bone on the curve d(u) = A(u) sin(phase - 2pi u / wavelength)
    (+ an optional C-curl), measured from the straight body."""
    out = []
    for u in u_mid:
        A = amp * (1 - grow + grow * u); dA = amp * grow
        k = 2 * math.pi / wavelength
        slope = (dA * math.sin(phase - k * u) - A * k * math.cos(phase - k * u)) / LS * LS   # d(d)/du, in body lengths
        slope += curl * 2 * u * math.sin(phase + curl_phase)                                 # C-curl: d = curl*u^2
        out.append(math.degrees(math.atan(slope)))
    return out

def chain(abs_deg, axis=WZ, base=0.0):
    """Turn absolute headings into each bone's bend relative to its parent."""
    rel, prev = {}, base
    for name, a in zip(SP, abs_deg): rel[name] = (axis, a - prev); prev = a
    return rel

def pose_for(clip, phase):
    s = math.sin; out = {}
    def put(rels, extra=None):
        for name, (axis, deg) in rels.items():
            out[name] = q(name, axis, deg) @ (extra.get(name, Quaternion()) if extra else Quaternion())
    def pincers(open_deg):
        # open = swing outward (L is on +X) and spread the tips apart; 0 = the modelled pose
        out["Pincer.L"] = q("Pincer.L", WY, -open_deg) @ q("Pincer.L", WZ, 0.6 * open_deg)
        out["Pincer.R"] = q("Pincer.R", WY, open_deg) @ q("Pincer.R", WZ, -0.6 * open_deg)
    def gills(flare):
        out["Gill.L"] = q("Gill.L", WY, -flare); out["Gill.R"] = q("Gill.R", WY, flare)
    if clip == "Swim":
        a = wave_angles(phase, amp=0.10, wavelength=0.72)
        SA = WX if os.environ.get("VDW_SWIM_AXIS", "Z").upper() == "X" else WZ   # X: up-and-down wave (leeches)
        put(chain(a, axis=SA, base=a[0] * 0.6))           # the neck turns a little less than the wave: steadier head
        out["Head"] = q("Head", SA, -0.6 * a[0])
        pincers(5 + 5 * s(2 * phase)); gills(4 + 4 * s(phase + 1))
    elif clip == "Thrash":
        a = wave_angles(2 * phase, amp=0.10, wavelength=0.7, curl=0.28, curl_phase=0.0)
        vert = wave_angles(phase + 1.3, amp=0.03, wavelength=1.0)       # bucking up and down a little
        rel = chain(a, base=a[0] * 0.5); rv = chain(vert)
        put(rel, {n: q(n, WX, rv[n][1]) for n in SP})
        out["Head"] = q("Head", WZ, -0.5 * a[0] + 8 * s(phase + 0.4)) @ q("Head", WY, 12 * s(2 * phase + 0.9))
        snap = max(0.0, s(4 * phase)) ** 0.5               # snapping open and shut, twice per thrash
        pincers(-6 + 46 * snap); gills(10 + 14 * s(2 * phase))
    else:  # Flop: on land, slow writhing C- and S-curls that also arch the body up and down; never quite still
        a = wave_angles(phase, amp=0.09, wavelength=0.9, curl=0.3, curl_phase=0.6)
        a = [x + 5 * s(5 * phase - 7 * u) * u for x, u in zip(a, u_mid)]        # tail keeps flicking
        arch = [20 * s(phase + 1.2 - 5 * u) * math.sin(math.pi * u) for u in u_mid]   # rolling humps along the back
        put(chain(a, base=a[0] * 0.5), {n: q(n, WX, r[1]) for n, r in chain(arch).items()})
        out["Head"] = q("Head", WZ, -0.5 * a[0]) @ q("Head", WX, 10 * s(phase + 2))
        pincers(12 + 14 * s(3 * phase)); gills(6 + 6 * s(2 * phase + 0.5))
    return out

CLIPS = {"Swim": 30, "Thrash": 15, "Flop": 30}
if arm.animation_data is None: arm.animation_data_create()
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
ALL = [b.name for b in arm.data.bones if b.name != "Root"]
for clip, length in CLIPS.items():
    old = bpy.data.actions.get(clip)
    if old: bpy.data.actions.remove(old)
    act = bpy.data.actions.new(clip); act.use_fake_user = True; arm.animation_data.action = act
    for f in range(length + 1):
        pose = pose_for(clip, 2 * math.pi * f / length)
        for name in ALL:
            pb = arm.pose.bones[name]; pb.rotation_quaternion = pose.get(name, Quaternion())
            pb.keyframe_insert("rotation_quaternion", frame=f, group=name)
    act.use_frame_range = True; act.use_cyclic = True; act.frame_start, act.frame_end = 0, length
    for fc in act.fcurves:
        if not any(m.type == 'CYCLES' for m in fc.modifiers): fc.modifiers.new('CYCLES')
arm.animation_data.action = bpy.data.actions["Swim"]
scene.frame_start, scene.frame_end = 0, 29
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()

def verts(frame):
    scene.frame_set(frame); dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg); c = [v.co.copy() for v in ev.to_mesh().vertices]; ev.to_mesh_clear(); return c
print("\n===== ANIMATE EEL =====")
for clip in CLIPS:
    arm.animation_data.action = bpy.data.actions[clip]
    fr = [verts(f) for f in range(31)]
    steps = [max((p - r).length for p, r in zip(fr[f], fr[f + 1])) for f in range(30)]
    span = max(max(abs(p.x) for p in fr[f]) for f in range(30))
    print(f"  {clip}: smallest frame-to-frame movement {min(steps):.3f} m, largest {max(steps):.3f} m, widest sideways reach {span:.2f} m; loop seam {max((p - r).length for p, r in zip(fr[0], fr[30])):.5f} m")
arm.animation_data.action = bpy.data.actions["Swim"]
if SAVE_TO:
    scene.frame_set(0); bpy.ops.wm.save_as_mainfile(filepath=SAVE_TO, copy=True); print("  saved:", SAVE_TO)
print("===== END =====")



