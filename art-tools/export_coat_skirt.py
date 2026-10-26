# Exports a hand-edited coat collar+skirt (coat_edit_*.blend) as the worn model, exactly as shaped: no push, no extra
# room. Tidies it (Object mode, rest pose, back-face copies removed, unweighted points weighted from their neighbours),
# hands the skirt below the hips more and more to the vdw_skirt0..7 bones the mod swings in the wind (FisherSkirt),
# then exports skirt + fitref + skeleton in centimetres, smooth-shaded and two-sided.
#   blender -b coat_edit_v1.blend --python export_coat_skirt.py
#   env: VDW_OUT (fbx path, never overwrites), VDW_EDITED (object, default coat_collar_skirt),
#        VDW_WIND (0..1: share on the skirt bones at the hem, default 0.6)
import bpy, bmesh, os, math
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
SKIRT = 8
WIND = float(os.environ.get("VDW_WIND", "0"))   # wind physics off by default (0 = the skirt follows the legs by its weights alone); SKIRT = 8
for o in list(bpy.data.objects):
    if o.mode != 'OBJECT' and o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
arm = bpy.data.objects["Armature"]
for pb in arm.pose.bones: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)
bpy.context.view_layer.update()
ed = bpy.data.objects[os.environ.get("VDW_EDITED", "coat_collar_skirt")]
# into world space on the main armature
mw = ed.matrix_world.copy(); ed.parent = None; ed.data.transform(mw); ed.matrix_world = Matrix.Identity(4)
for m in [m for m in ed.modifiers if m.type == 'ARMATURE']: ed.modifiers.remove(m)
missing = [g.name for g in ed.vertex_groups if g.name not in arm.data.bones]
if missing: raise SystemExit(f"vertex groups with no bone in the Armature: {missing}")

# back-face copies (a face duplicated facing the other way): keep the one facing away from the body
fit = bpy.data.objects["fitref"]; fb = bmesh.new(); fb.from_mesh(fit.data); fb.transform(fit.matrix_world); ft = BVHTree.FromBMesh(fb)
b = bmesh.new(); b.from_mesh(ed.data)
groups = {}
for f in b.faces: groups.setdefault(frozenset(v.co.to_tuple(5) for v in f.verts), []).append(f)
drop = []
for g in groups.values():
    if len(g) != 2 or g[0].normal.dot(g[1].normal) >= 0: continue
    c = g[0].calc_center_median(); loc, n, _i, d = ft.find_nearest(c)
    out = (c - loc).normalized() if loc is not None and d > 1e-5 else n
    drop.append(g[0] if g[0].normal.dot(out) < g[1].normal.dot(out) else g[1])
bmesh.ops.delete(b, geom=drop, context='FACES')
bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-6)
b.to_mesh(ed.data); b.free(); ed.data.update()
me = ed.data
print(f"EXPORT removed {len(drop)} back-face copies; {len(me.vertices)} points, {len(me.polygons)} faces")

# unweighted points take their neighbours' weights
names = lambda: {g.index: g.name for g in ed.vertex_groups}
adj = {v.index: set() for v in me.vertices}
for e in me.edges: a, c = e.vertices; adj[a].add(c); adj[c].add(a)
todo = [v.index for v in me.vertices if sum(g.weight for g in v.groups) < 0.01]
nm = names()
for _ in range(10):
    left = []
    for i in todo:
        nb = [j for j in adj[i] if j not in todo]
        if not nb: left.append(i); continue
        acc = {}
        for j in nb:
            for g in me.vertices[j].groups: acc[nm[g.group]] = acc.get(nm[g.group], 0) + g.weight / len(nb)
        for k, x in acc.items(): ed.vertex_groups[k].add([i], x, 'REPLACE')
    if not left or len(left) == len(todo): todo = left; break
    todo = left
print(f"EXPORT {len(todo)} points still unweighted")

# --- reweighting from the body (VDW_REWEIGHT=1): every point takes the weights of the skin under it, so it moves
# exactly like the body (and the paint on it). The collar: the skin under it, the head's share on the neck instead.
# The skirt: the skin of its own side (hips and that thigh); the back follows the thighs only lightly.
if os.environ.get("VDW_REWEIGHT", "1") == "1":
    from mathutils.interpolate import poly_3d_calc
    dg = bpy.context.evaluated_depsgraph_get(); fe = fit.evaluated_get(dg); fme = fe.to_mesh()
    fv = [fe.matrix_world @ v.co for v in fme.vertices]; fpolys = [tuple(p.vertices) for p in fme.polygons]
    fnames = {g.index: g.name for g in fit.vertex_groups}
    fw = [{fnames[g.group]: g.weight for g in fit.data.vertices[i].groups if g.weight > 0.001} for i in range(len(fv))]
    fe.to_mesh_clear()
    def armish(n): return any(k in n for k in ("Arm", "Hand"))
    def poly_ok(p, side):
        if any(sum(x for k, x in fw[i].items() if armish(k)) > 0.5 for i in p): return False
        if side == 0: return True
        cx = sum(fv[i].x for i in p) / len(p)
        return cx * side > -0.01
    trees = {sd: (lambda ps: (BVHTree.FromPolygons(fv, ps), ps))([p for p in fpolys if poly_ok(p, sd)]) for sd in (0, 1, -1)}
    def skin_weights(p, side):
        t, ps = trees[side]; loc, n, idx, d = t.find_nearest(p)
        poly = ps[idx]; ws = poly_3d_calc([fv[i] for i in poly], loc); out = {}
        for i, w in zip(poly, ws):
            for k, x in fw[i].items(): out[k] = out.get(k, 0) + x * w
        return out
    shoulder = min((arm.matrix_world @ arm.data.bones[s_ + "Arm"].head_local).z for s_ in ("Left", "Right"))
    neck = arm.matrix_world @ arm.data.bones["Neck"].head_local
    hips = arm.matrix_world @ arm.data.bones["Hips"].head_local
    ys = [p.y for p in fv]; mid_y = (min(ys) + max(ys)) / 2
    COLLAR_Z = float(os.environ.get("VDW_COLLAR_Z", "1.3"))
    TH_FRONT = float(os.environ.get("VDW_THIGH_FRONT", "0.75")); TH_BACK = float(os.environ.get("VDW_THIGH_BACK", "0.6"))
    _sk = [v.co.z for v in me.vertices if v.co.z <= COLLAR_Z]; SKIRT_TOP, SKIRT_HEM = max(_sk), min(_sk)
    TH_FULL = float(os.environ.get("VDW_THIGH_FULL", "0.15"))
    BACK_LEG = float(os.environ.get("VDW_BACK_LEG_KEEP", "0.3"))
    LEGS = ("LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg")
    def smooth(a, b_, x):
        t = min(1.0, max(0.0, (x - a) / (b_ - a))); return t * t * (3 - 2 * t)
    nc = nk = 0
    for v in me.vertices:
        p = v.co
        collar = p.z > COLLAR_Z             # everything above the skirt (the tips reach ~20 cm out from the neck)
        if collar:
            w = skin_weights(p, 0)
            if os.environ.get("VDW_COLLAR_NO_HEAD", "0") == "1":     # exact skin weights by default: it moves like the paint
                hj = sum(w.pop(k, 0) for k in ("Head", "Jaw"))
                if hj: w["Neck"] = w.get("Neck", 0) + hj
            nc += 1
        else:                                   # the skirt (everything below COLLAR_Z)
            side = 1 if p.x > 0.02 else (-1 if p.x < -0.02 else 0)
            w = skin_weights(p, side)
            back = smooth(mid_y - 0.03, mid_y + 0.05, p.y)           # the body's back is +y
            # the skin's thigh weights out (they're patchy off the body), then a clean share on the thigh of this side,
            # growing from the hips to full TH_FULL below them; the back a little less; the middle split between both
            legs = sum(w.pop(k, 0) for k in LEGS)
            if legs: w["Hips"] = w.get("Hips", 0) + legs
            # evenly from the belt (none) down the whole panel to the hem (the most): no fold half way down
            lin = min(1.0, max(0.0, (SKIRT_TOP - p.z) / max(SKIRT_TOP - SKIRT_HEM, 1e-6)))
            # rising faster near the top (a curve, not a straight line): the middle of the front panels and the back
            # just under the belt get more (with too little the legs and the seat pushed through)
            curve = float(os.environ.get("VDW_THIGH_CURVE_FRONT", "0.6")) * (1 - back) + float(os.environ.get("VDW_THIGH_CURVE_BACK", "0.5")) * back
            th = (lin ** curve) * (TH_FRONT * (1 - back) + TH_BACK * back)
            right = smooth(-0.05, 0.05, p.x)                          # +x carries the Right* weights
            tot0 = sum(w.values()) or 1
            w = {k: x / tot0 * (1 - th) for k, x in w.items()}
            for nmL, part in (("RightUpLeg", right), ("LeftUpLeg", 1 - right)):
                if part > 0: w[nmL] = w.get(nmL, 0) + th * part
            nk += 1
        w = {k: x for k, x in w.items() if k in arm.data.bones and not k.startswith("vdw_skirt")}
        top4 = sorted(w.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top4) or 1
        for g in list(v.groups): ed.vertex_groups[g.group].remove([v.index])
        for k, x in top4:
            (ed.vertex_groups.get(k) or ed.vertex_groups.new(name=k)).add([v.index], x / tot, 'REPLACE')
    print(f"EXPORT reweighted from the body: {nc} collar points, {nk} skirt points")
    # the collar's weights evened out over its neighbours (a lone point - the tip - took odd weights from the skin
    # nearest it and stretched away from the rest)
    cidx = {v.index for v in me.vertices if v.co.z > COLLAR_Z}
    gn = {g.index: g.name for g in ed.vertex_groups}
    cw = {i: {gn[g.group]: g.weight for g in me.vertices[i].groups} for i in cidx}
    for _ in range(int(os.environ.get("VDW_COLLAR_SMOOTH", "0"))):
        new = {}
        for i in cidx:
            nb = [j for j in adj[i] if j in cidx]
            acc = {k: x * 0.5 for k, x in cw[i].items()}
            for j in nb:
                for k, x in cw[j].items(): acc[k] = acc.get(k, 0) + x * 0.5 / len(nb)
            if not nb: acc = dict(cw[i])
            new[i] = acc
        cw = new
    # a point whose weights don't match its neighbours' (the collar tip) takes their average instead
    ODD = float(os.environ.get("VDW_COLLAR_ODD", "0.6")); fixed = []
    for i in cidx:
        nb = [j for j in adj[i] if j in cidx]
        if not nb: continue
        avg = {}
        for j in nb:
            for k, x in cw[j].items(): avg[k] = avg.get(k, 0) + x / len(nb)
        diff = sum(abs(cw[i].get(k, 0) - avg.get(k, 0)) for k in set(cw[i]) | set(avg))
        if diff > ODD: fixed.append((i, avg, round(diff, 2)))
    for i, avg, _d in fixed: cw[i] = avg
    print(f"EXPORT collar points given their neighbours' weights: {[(i, d) for i, _a, d in fixed]}")
    for i, w in cw.items():
        top4 = sorted(w.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top4) or 1
        for g in list(me.vertices[i].groups): ed.vertex_groups[g.group].remove([i])
        for k, x in top4: ed.vertex_groups[k].add([i], x / tot, 'REPLACE')
    print(f"EXPORT collar weights smoothed over {len(cidx)} points")

# wind: below the hips, a growing share on the skirt bones (by direction round the hips, like the original rig)
hip_c = arm.matrix_world @ arm.data.bones["Hips"].head_local
for i in range(SKIRT):
    if f"vdw_skirt{i}" not in ed.vertex_groups: ed.vertex_groups.new(name=f"vdw_skirt{i}")
hem = min(v.co.z for v in me.vertices)
top = hip_c.z + float(os.environ.get("VDW_WIND_TOP", "0.02"))           # from just below the belt...
FULL = hip_c.z - float(os.environ.get("VDW_WIND_FULL", "0.12"))         # ...to the full share 12 cm below the hips
nm = names(); windy = 0
for v in me.vertices:
    t = min(1.0, max(0.0, (top - v.co.z) / max(top - FULL, 1e-6)))   # the whole skirt rides the swing bones, not just the hem
    s = WIND * t * t * (3 - 2 * t)
    if s <= 0.001: continue
    w = {nm[g.group]: g.weight for g in v.groups if g.weight > 0}
    w = {k: (x if k.startswith("vdw_skirt") else x * (1 - s)) for k, x in w.items()}
    a = (math.atan2(v.co.y - hip_c.y, v.co.x - hip_c.x) / (2 * math.pi)) % 1.0 * SKIRT
    b0 = int(a) % SKIRT; f1 = a - int(a)
    for k, x in ((f"vdw_skirt{b0}", s * (1 - f1)), (f"vdw_skirt{(b0 + 1) % SKIRT}", s * f1)): w[k] = w.get(k, 0) + x
    top4 = sorted(w.items(), key=lambda kv: -kv[1])[:4]; tot = sum(x for _, x in top4) or 1
    for g in list(v.groups): ed.vertex_groups[g.group].remove([v.index])
    for k, x in top4: ed.vertex_groups[k].add([v.index], x / tot, 'REPLACE')
    windy += 1
print(f"EXPORT wind: {windy} skirt points on the skirt bones, up to {WIND:.0%} at the hem")

# VDW_SAVE_BLEND: save the tidied, weighted coat as a work file (metres, rest pose) instead of exporting
SAVE_BLEND = os.environ.get("VDW_SAVE_BLEND", "")
if SAVE_BLEND:
    if os.path.exists(SAVE_BLEND): raise SystemExit("exists, kept: " + SAVE_BLEND)
    ed.parent = arm; ed.modifiers.new("Armature", 'ARMATURE').object = arm
    for o in bpy.data.objects:
        if o.name == "fitref": o.hide_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=SAVE_BLEND, copy=True)
    print("SAVED", SAVE_BLEND); raise SystemExit(0)
# centimetres (like gear_split_for_export.py), smooth, two-sided, then out
for o in list(bpy.data.objects):
    if o not in (arm, ed, fit): bpy.data.objects.remove(o)
for m in [m for m in fit.modifiers if m.type == 'ARMATURE']: fit.modifiers.remove(m)
fit.data.transform(fit.matrix_world); fit.parent = None; fit.matrix_world = Matrix.Identity(4)
S = Matrix.Scale(100.0, 4)
for o in bpy.data.objects: o.select_set(o == arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for bn in arm.data.edit_bones: bn.head = S @ bn.head; bn.tail = S @ bn.tail
bpy.ops.object.mode_set(mode='OBJECT')
fit.data.transform(S); me.transform(S)
for p in me.polygons: p.use_smooth = True
b = bmesh.new(); b.from_mesh(me)
dup = bmesh.ops.duplicate(b, geom=list(b.faces))
bmesh.ops.reverse_faces(b, faces=[g for g in dup["geom"] if isinstance(g, bmesh.types.BMFace)])
b.to_mesh(me); b.free(); me.update()
ed.name = "coat"; me.name = "coat"
if me.materials: me.materials[0].name = "coat"
ed.parent = arm; ed.modifiers.new("Armature", 'ARMATURE').object = arm
for o in bpy.data.objects: o.hide_set(False); o.hide_viewport = False; o.hide_select = False; o.select_set(True)   # hidden objects aren't exported
bpy.context.view_layer.objects.active = ed
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={'MESH', 'ARMATURE'}, global_scale=1.0, apply_unit_scale=True,
                         add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
                         apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         mesh_smooth_type='FACE', bake_anim=False, path_mode='STRIP', embed_textures=False, colors_type='LINEAR')
print("EXPORTED", OUT, len(me.polygons), "faces")
