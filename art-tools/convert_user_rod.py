# Turns a hand-modelled rod .blend (several objects, tiled PBR materials, subdivision modifiers) into what rig_rod2.py
# takes: one mesh in centimetres along +Z, guides toward +Y, with one packed UV atlas and baked maps. Never saves over
# the source .blend. For the Allfather's Rod (Fishing+Rod.blend) it also carves glowing runes into the blank, lights the
# reel's gem and the guide inserts, and gives the spear-point tip a faint glow.
#   blender -b <rod.blend> --python convert_user_rod.py
# env: VDW_NAME, VDW_OUT (folder: Models/, Textures/, Blender Files/ made in it), VDW_TEX_DIR (where the material
#      textures really are, matched by file name), VDW_TURNING (object names that turn with the reel, comma list; the
#      first is the spool), VDW_BLANK (the blank object), VDW_GLOW_BLUE / VDW_GLOW_TIP / VDW_GEM (object names),
#      VDW_SUBSURF (1), VDW_TRIS (35000, total after decimating), VDW_RES (2048), VDW_RUNES (1)
import bpy, bmesh, os, math, json
import numpy as np
from mathutils import Matrix, Vector
import functools
print = functools.partial(print, flush=True)

NAME = os.environ["VDW_NAME"]; OUT = os.environ["VDW_OUT"]; TEXDIR = os.environ.get("VDW_TEX_DIR", "")
RES = int(os.environ.get("VDW_RES", "2048")); LEVEL = int(os.environ.get("VDW_SUBSURF", "1")); TRIS = int(os.environ.get("VDW_TRIS", "35000"))
def names(key): return [s.strip() for s in os.environ.get(key, "").split(",") if s.strip()]
TURNING = names("VDW_TURNING"); BLANK = os.environ["VDW_BLANK"]
GLOW_BLUE = set(names("VDW_GLOW_BLUE")); GLOW_TIP = set(names("VDW_GLOW_TIP")); GEM = set(names("VDW_GEM"))
for d in ("Models", "Textures", "Blender Files"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
TEX = os.path.join(OUT, "Textures")

# ---------------------------------------------------------------- textures found again, everything but meshes gone
for img in bpy.data.images:
    p = os.path.join(TEXDIR, os.path.basename(img.filepath.replace("\\", "/")))
    if TEXDIR and os.path.exists(p): img.filepath = p; img.reload()
# curves with a bevel (the fishing line from the reel up through the guides) become meshes, the rest goes
dg = bpy.context.evaluated_depsgraph_get()
for o in list(bpy.data.objects):
    if o.type == 'CURVE' and (o.data.bevel_depth > 0 or o.data.bevel_object):
        print(f"  line {o.name}: extrude {o.data.extrude:.4f} -> 0 (a round line, not a ribbon)"); o.data.extrude = 0.0; dg.update()
        me_ = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        if not me_.uv_layers: me_.uv_layers.new(name="UVMap")
        if not any(me_.materials):
            line_mat = bpy.data.materials.new("VDW_Line"); line_mat.use_nodes = True
            b = line_mat.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.86, 0.86, 0.82, 1); b.inputs["Roughness"].default_value = 0.45
            me_.materials.clear(); me_.materials.append(line_mat)
        line = bpy.data.objects.new("VDW_Line", me_); line.matrix_world = o.matrix_world.copy()
        bpy.context.scene.collection.objects.link(line)
        print(f"  line kept: {o.name} -> {len(me_.vertices)} verts, bevel {o.data.bevel_depth:.4f} m")
for o in list(bpy.data.objects):
    if o.type != 'MESH': bpy.data.objects.remove(o)
objs = [o for o in bpy.data.objects]
src_of = {o.name: i + 1 for i, o in enumerate(objs)}          # 0 = nothing baked there

# ---------------------------------------------------------------- one subdivision level applied, then decimated
dg = bpy.context.evaluated_depsgraph_get()
for o in objs:
    for m in o.modifiers:
        if m.type == 'SUBSURF': m.levels = min(m.levels, LEVEL)
dg.update()
for o in objs:
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    o.modifiers.clear(); old = o.data; o.data = me; bpy.data.meshes.remove(old)
total = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
ratio = min(1.0, TRIS / total)
print(f"CONVERT {NAME}: {len(objs)} objects, {total} tris at subdivision {LEVEL}; decimating to {ratio:.2f}")
if ratio < 1.0:
    for o in objs:
        if sum(len(p.vertices) - 2 for p in o.data.polygons) < 600 or o.name in (BLANK, "VDW_Line"): continue   # small parts, the blank and the line keep their shape (decimated long strips tear when the rod bends)
        m = o.modifiers.new("dec", 'DECIMATE'); m.ratio = ratio
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if not o.modifiers: continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        o.modifiers.clear(); old = o.data; o.data = me; bpy.data.meshes.remove(old)
for o in objs:                                                # which object each face came from (kept through the join)
    a = o.data.attributes.new("vdw_src", 'INT', 'FACE'); a.data.foreach_set("value", [src_of[o.name]] * len(o.data.polygons))
    for p in o.data.polygons: p.use_smooth = p.use_smooth or len(o.data.polygons) > 40

# ---------------------------------------------------------------- joined: the turning parts first (rig_rod2 finds them by index)
def join(group, active):
    bpy.ops.object.select_all(action='DESELECT')
    for o in group: o.select_set(True)
    bpy.context.view_layer.objects.active = active
    if len(group) > 1: bpy.ops.object.join()
    return bpy.context.view_layer.objects.active
turn_objs = [bpy.data.objects[n] for n in TURNING]
rest = [o for o in objs if o.name not in TURNING]
T = join(turn_objs, turn_objs[0]); n_turn = len(T.data.vertices)
for o in (T,): o.data.transform(o.matrix_world); o.matrix_world = Matrix()
S = join(rest, rest[0]); S.data.transform(S.matrix_world); S.matrix_world = Matrix()
rod = join([T, S], T); rod.name = NAME; me = rod.data
print(f"  joined: {len(me.vertices)} verts, {sum(len(p.vertices) - 2 for p in me.polygons)} tris; turning verts first: {n_turn}")

# ---------------------------------------------------------------- squared up: blank axis on Z through the origin, guides toward +Y
src = np.zeros(len(me.polygons), np.int32); me.attributes["vdw_src"].data.foreach_get("value", src)
co = np.array([v.co[:] for v in me.vertices])
blank_v = np.unique(np.concatenate([list(p.vertices) for p in me.polygons if src[p.index] == src_of[BLANK]]))
bz = co[blank_v]; zlo, zhi = co[:, 2].min(), co[:, 2].max()
mid = bz[bz[:, 2] > zlo + 0.25 * (zhi - zlo)]   # the blank above the reel
print("  blank verts", len(blank_v), "in the upper band", len(mid), "src counts", np.bincount(src).tolist())
axis = np.array([np.median(mid[:, 0]), np.median(mid[:, 1])])
guide_names = [TURNING[0]]                                  # the reel (and its line) on the +Y side, like the other rods
gv = np.unique(np.concatenate([list(p.vertices) for p in me.polygons if src[p.index] in [src_of[n] for n in guide_names]]))
off = co[gv][:, :2].mean(0) - axis
turn = math.atan2(off[0], off[1])                             # turn so the reel sits toward +Y
R = Matrix.Rotation(turn, 4, 'Z') @ Matrix.Translation((-axis[0], -axis[1], 0))
me.transform(R); me.update(); co = np.array([v.co[:] for v in me.vertices])
print(f"  blank axis was at {axis.round(3)}, turned {math.degrees(turn):.0f} deg so the reel faces +Y")
if os.environ.get("VDW_MIRROR_X") == "1":                     # the reel's crank on the other side: the whole rod mirrored left-right
    me.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free(); me.update()
    co = np.array([v.co[:] for v in me.vertices]); print("  mirrored left-right (crank on the other side)")

# the blank's long faces cut into 25 cm pieces, so its UV islands can be packed (and it bends smoothly)
bm = bmesh.new(); bm.from_mesh(me); fl = bm.faces.layers.int["vdw_src"]
long_e = {e for f in bm.faces if f[fl] == src_of[BLANK] for e in f.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.25}
groups = {}
for e in long_e: groups.setdefault(int(abs(e.verts[0].co.z - e.verts[1].co.z) // 0.25), []).append(e)
for cuts, edges in sorted(groups.items(), reverse=True):
    edges = [e for e in edges if e.is_valid]
    if edges: bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
bm.to_mesh(me); bm.free(); me.update()
print(f"  blank cut into 25 cm pieces: {len(me.vertices)} verts")
# ---------------------------------------------------------------- the atlas: per-object islands, the blank cut in 30 cm pieces
atlas = me.uv_layers.new(name="Atlas"); me.uv_layers.active = atlas
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
def arrays():
    """The mesh's per-loop / per-face arrays, read again (an edit-mode round trip can change the loops)."""
    me.update()
    s = np.zeros(len(me.polygons), np.int32); me.attributes["vdw_src"].data.foreach_get("value", s)
    lf = np.zeros(len(me.loops), np.int32)
    for p in me.polygons: lf[p.loop_start:p.loop_start + p.loop_total] = p.index
    a = me.uv_layers["Atlas"]; u = np.zeros(len(me.loops) * 2); a.data.foreach_get("uv", u)
    return s, lf, a, u.reshape(-1, 2)
src, loop_face, atlas, uv = arrays()
fz = np.array([p.center.z for p in me.polygons])
# the wood of the blank unrolled as one strip per 25 cm (seam at the back, -Y): runes stay whole, no seams through them
wood_slots = [i for i, m in enumerate(me.materials) if m and m.name == os.environ.get("VDW_WOOD_MAT", "RedWood")]
fmat = np.array([p.material_index for p in me.polygons])
wood_f = (src == src_of[BLANK]) & np.isin(fmat, wood_slots)
vco_ = np.array([v.co[:] for v in me.vertices]); lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
phi_v = np.arctan2(vco_[:, 0], vco_[:, 1]); rad_v = np.hypot(vco_[:, 0], vco_[:, 1])
bk = np.floor(fz / 0.25).astype(int)
for b in np.unique(bk[wood_f]):
    faces = np.where(wood_f & (bk == b))[0]
    loops = np.concatenate([np.arange(me.polygons[i].loop_start, me.polygons[i].loop_start + me.polygons[i].loop_total) for i in faces])
    R = float(np.median(rad_v[lv[loops]]))
    for i in faces:
        p = me.polygons[i]; ls = np.arange(p.loop_start, p.loop_start + p.loop_total); ph = phi_v[lv[ls]].copy()
        if ph.max() - ph.min() > math.pi: ph[ph < 0] += 2 * math.pi            # a face across the seam
        uv[ls, 0] = ph * R; uv[ls, 1] = vco_[lv[ls], 2]
print(f"  wood unrolled: {int(wood_f.sum())} faces in {len(np.unique(bk[wood_f]))} strips")
bucket = np.floor(fz / 0.25).astype(int)
lb = (src == src_of[BLANK])[loop_face]
uv[lb] += np.stack([bucket[loop_face][lb] * 3.1, np.zeros(lb.sum())], 1)      # each piece its own island
atlas.data.foreach_set("uv", uv.ravel())
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.select_all(action='SELECT'); bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode='OBJECT')
# detail weighting: the reel, guides and tip get more of the atlas than the plain blank
src, loop_face, atlas, uv = arrays()
uv[src[loop_face] != src_of[BLANK]] *= 1.5
atlas.data.foreach_set("uv", uv.ravel())
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')
src, loop_face, atlas, uv = arrays()
me.uv_layers.active = atlas; atlas.active_render = True

# ---------------------------------------------------------------- materials read their textures from the old UVs
for mat in me.materials:
    if not mat or not mat.use_nodes: continue
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type == 'NORMAL_MAP': n.uv_map = "UVMap"
        if n.type == 'TEX_COORD':
            for l in list(n.outputs["UV"].links):
                u = nt.nodes.new("ShaderNodeUVMap"); u.uv_map = "UVMap"; nt.links.new(u.outputs["UV"], l.to_socket)   # replaces the old link
    for n in list(nt.nodes):
        if n.type in ('TEX_IMAGE', 'MAPPING') and not n.inputs["Vector"].is_linked:
            u = nt.nodes.new("ShaderNodeUVMap"); u.uv_map = "UVMap"; nt.links.new(u.outputs["UV"], n.inputs["Vector"])
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
    for l in list(out.inputs["Displacement"].links): nt.links.remove(l)

# ---------------------------------------------------------------- baking
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 8
sc.render.bake.margin = 8; sc.render.bake.use_clear = True
bpy.ops.object.select_all(action='DESELECT'); rod.select_set(True); bpy.context.view_layer.objects.active = rod
def new_image(kind, color=True, floats=False):
    im = bpy.data.images.new(f"{NAME}_{kind}", RES, RES, alpha=True, float_buffer=floats)
    if not color: im.colorspace_settings.name = "Non-Color"
    return im
def targets(im):
    for mat in me.materials:
        nt = mat.node_tree; t = nt.nodes.get("VDW_Target") or nt.nodes.new("ShaderNodeTexImage")
        t.name = "VDW_Target"; t.image = im; nt.nodes.active = t
def emit_bake(im, source):
    """Bakes source(mat, nt) -> socket or value through an emission shader (no lighting)."""
    saved = []
    for mat in me.materials:
        nt = mat.node_tree; out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        old = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].is_linked else None
        em = nt.nodes.new("ShaderNodeEmission"); em.name = "VDW_Emit"
        s = source(mat, nt)
        if isinstance(s, (int, float)): em.inputs["Color"].default_value = (s, s, s, 1)
        elif isinstance(s, tuple): em.inputs["Color"].default_value = s
        else: nt.links.new(s, em.inputs["Color"])
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"]); saved.append((nt, out, old, em))
    targets(im); bpy.ops.object.bake(type='EMIT')
    for nt, out, old, em in saved:
        nt.nodes.remove(em)
        if old: nt.links.new(old, out.inputs["Surface"])
def bsdf_input(name):
    def f(mat, nt):
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None: return 0.0
        i = b.inputs[name]
        if i.is_linked: return i.links[0].from_socket
        v = i.default_value
        return tuple(v) if hasattr(v, "__len__") else float(v)
    return f
def px(im): return np.array(im.pixels[:], np.float32).reshape(RES, RES, 4)

alb = new_image("albedo"); emit_bake(alb, bsdf_input("Base Color")); A = px(alb)
met = new_image("metal", False); emit_bake(met, bsdf_input("Metallic")); M = px(met)[..., 0]
rou = new_image("rough", False); emit_bake(rou, bsdf_input("Roughness")); Rg = px(rou)[..., 0]
def rasterize():
    """Which part, and where on the rod, each atlas texel is - drawn straight from the triangles (exact, no bake margins)."""
    me.calc_loop_triangles()
    uvs = np.zeros(len(me.loops) * 2); me.uv_layers["Atlas"].data.foreach_get("uv", uvs); uvs = uvs.reshape(-1, 2) * RES - 0.5
    vco = np.array([v.co[:] for v in me.vertices], np.float32)
    sid = np.zeros((RES, RES), np.int32); pos = np.zeros((RES, RES, 3), np.float32)
    for tri in me.loop_triangles:
        l = list(tri.loops); q = uvs[l]; vv = vco[list(tri.vertices)]
        x0, y0 = np.floor(q.min(0)).astype(int); x1, y1 = np.ceil(q.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, RES - 1), min(y1, RES - 1)
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        (ax, ay), (bx, by), (cx, cy) = q
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12: continue
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
        if not inside.any(): continue
        yy, xx = gy[inside], gx[inside]
        sid[yy, xx] = src[tri.polygon_index]
        pos[yy, xx] = w0[inside, None] * vv[0] + w1[inside, None] * vv[1] + w2[inside, None] * vv[2]
    return sid, pos
SID, P = rasterize()
nrm =new_image("normal", False); targets(nrm)
sc.render.bake.normal_space = 'TANGENT'; bpy.ops.object.bake(type='NORMAL'); N = px(nrm)
print("  baked albedo, metal, roughness, normal (+ position and part maps)")

# ---------------------------------------------------------------- the Allfather's marks: runes, gem, guide inserts, Gungnir's point
E = np.zeros((RES, RES, 3), np.float32)
BLUE = np.array([0.32, 0.62, 1.0], np.float32)
def part(names_): return np.isin(SID, [src_of[n] for n in names_ if n in src_of])
m = part(GLOW_BLUE); E[m] = BLUE * 0.75; A[m, :3] = A[m, :3] * 0.4 + np.array([0.55, 0.75, 1.0]) * 0.6; Rg[m] = 0.2
m = part(GEM); E[m] = BLUE * 1.0; A[m, :3] = np.array([0.45, 0.7, 1.0]); M[m] = 0.0; Rg[m] = 0.05
m = part(GLOW_TIP); E[m] = A[m, :3] * 0.3
if os.environ.get("VDW_RUNES", "1") == "1":
    sane = SID > 0
    wood = (SID == src_of[BLANK]) & (M < 0.3) & (A[..., 0] > A[..., 2] * 1.1) & sane
    wz = P[wood][:, 2]; wr = np.hypot(P[wood][:, 0], P[wood][:, 1])
    # rune-free zones: the guides and reel, and a little either side
    busy = []
    for n in list(GLOW_BLUE) + [o for o in src_of if o not in (BLANK, "VDW_Line")]:
        sel = SID == src_of[n]
        if sel.any():
            z = P[sel][:, 2]; z = z[(z > -0.1) & (z < 6)]
            if len(z): busy.append((np.percentile(z, 2) - 0.05, np.percentile(z, 98) + 0.05))
    RUNES = {   # Elder Futhark, strokes in a 0.6 x 1 box (y toward the tip)
        "f": [((0, 0), (0, 1)), ((0, .75), (.5, 1)), ((0, .5), (.5, .75))],
        "u": [((0, 0), (0, 1)), ((0, 1), (.5, .7)), ((.5, .7), (.5, 0))],
        "th": [((0, 0), (0, 1)), ((0, .7), (.45, .5)), ((.45, .5), (0, .3))],
        "a": [((0, 0), (0, 1)), ((0, 1), (.5, .75)), ((0, .7), (.5, .45))],
        "r": [((0, 0), (0, 1)), ((0, 1), (.45, .78)), ((.45, .78), (0, .55)), ((0, .55), (.5, 0))],
        "k": [((.5, 1), (0, .5)), ((0, .5), (.5, 0))],
        "g": [((0, 0), (.6, 1)), ((0, 1), (.6, 0))],
        "t": [((.3, 0), (.3, 1)), ((.3, 1), (0, .7)), ((.3, 1), (.6, .7))],
        "z": [((.3, 0), (.3, 1)), ((.3, .6), (0, 1)), ((.3, .6), (.6, 1))],
        "o": [((.3, 1), (.55, .65)), ((.55, .65), (.3, .3)), ((.3, .3), (.05, .65)), ((.05, .65), (.3, 1)), ((.3, .3), (0, 0)), ((.3, .3), (.6, 0))],
        "d": [((0, 0), (0, 1)), ((.6, 0), (.6, 1)), ((0, 1), (.6, 0)), ((0, 0), (.6, 1))],
    }
    WORD = ["o", "d", "th", "a", "z", "g", "t", "f", "u", "r", "k", "a"]     # cycled along the rod
    zs = np.sort(wz); lo, hi = zs[int(len(zs) * 0.01)], zs[int(len(zs) * 0.99)]
    segs = []; zc = lo + 0.05; k = 0
    while zc < hi - 0.05:
        r_here = np.median(wr[np.abs(wz - zc) < 0.03]) if (np.abs(wz - zc) < 0.03).any() else 0.01
        h = float(np.clip(r_here * 2.4, 0.016, 0.06)); w = 0.6 * h
        if any(a <= zc <= b or a <= zc + h <= b for a, b in busy): zc += 0.02; continue
        glyph = RUNES[WORD[k % len(WORD)]]; k += 1
        for side in (math.pi / 2, -math.pi / 2):           # two columns, facing +X and -X
            for (x0, y0), (x1, y1) in glyph:
                segs.append((side * r_here + (x0 - 0.3) * h, zc + y0 * h, side * r_here + (x1 - 0.3) * h, zc + y1 * h, 0.11 * h))
        zc += h * 1.45
    print("  rune debug: wood texels", int(wood.sum()), "z", round(float(lo), 2), round(float(hi), 2), "busy", [(round(a, 2), round(b, 2)) for a, b in busy])
    segs = np.array(segs, np.float32)
    idx = np.argwhere(wood); pw = P[wood]
    s_arc = np.arctan2(pw[:, 0], pw[:, 1]) * np.hypot(pw[:, 0], pw[:, 1])   # arc length round the blank (0 = +Y)
    d_best = np.full(len(pw), 9.0, np.float32); w_best = np.full(len(pw), 1.0, np.float32)
    for c0 in range(0, len(segs), 64):
        S_ = segs[c0:c0 + 64]
        ax_, ay_, bx_, by_, ww = [S_[:, i][None, :] for i in range(5)]
        px_, py_ = s_arc[:, None], pw[:, 2][:, None]
        dx, dy = bx_ - ax_, by_ - ay_
        t = np.clip(((px_ - ax_) * dx + (py_ - ay_) * dy) / np.maximum(dx * dx + dy * dy, 1e-12), 0, 1)
        d = np.hypot(px_ - (ax_ + t * dx), py_ - (ay_ + t * dy)) / ww
        j = d.argmin(1); dmin = d[np.arange(len(d)), j]
        better = dmin < d_best; d_best[better] = dmin[better]
    glow = np.clip((1.3 - d_best) * 2.5, 0, 1)    # inside the stroke, crisp-edged
    groove = np.clip((2.2 - d_best) * 1.5, 0, 1)  # the dark carved edge round it
    ii, jj = idx[:, 0], idx[:, 1]
    A[ii, jj, :3] *= (1 - 0.75 * groove)[:, None]
    A[ii, jj, :3] = A[ii, jj, :3] * (1 - glow[:, None]) + np.array([0.10, 0.38, 1.0]) * glow[:, None]
    E[ii, jj] = np.maximum(E[ii, jj], np.array([0.18, 0.5, 1.0], np.float32)[None, :] * glow[:, None])
    print(f"  carved {k} runes in two columns ({(glow > 0.5).sum()} texels glowing)")

# ---------------------------------------------------------------- written out for rig_rod2.py
def save(arr, kind, color=True):
    im = bpy.data.images.new(f"{NAME}_{kind}_out", RES, RES, alpha=True)
    if not color: im.colorspace_settings.name = "Non-Color"
    im.pixels[:] = arr.ravel(); p = os.path.join(TEX, f"{NAME}_{kind}.png")
    im.filepath_raw = p; im.file_format = 'PNG'; im.save(); return p
M = np.minimum(M, float(os.environ.get("VDW_MAX_METAL", "0.5")))
grey = A[..., :3].mean(2, keepdims=True); A[..., :3] = np.clip(grey + (A[..., :3] - grey) * float(os.environ.get("VDW_SATURATE", "1.2")), 0, 1)
A[..., 3] = 1
save(A, "src_albedo"); save(np.dstack([M, M, M, np.ones_like(M)]), "src_metal", False)
save(np.dstack([Rg, Rg, Rg, np.ones_like(Rg)]), "src_rough", False); save(N, "src_normal", False)
save(np.dstack([E, np.ones((RES, RES), np.float32)]), "Unity_Emission")

# loose parts, the same way rig_rod2.py counts them: the turning ones are those among the first n_turn verts
me.uv_layers.remove(me.uv_layers["UVMap"])
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); comp = np.full(len(bm.verts), -1); c = 0
for v in bm.verts:
    if comp[v.index] >= 0: continue
    st = [v]; comp[v.index] = c
    while st:
        u = st.pop()
        for e in u.link_edges:
            w_ = e.other_vert(u)
            if comp[w_.index] < 0: comp[w_.index] = c; st.append(w_)
    c += 1
bm.free()
spool_parts = sorted(set(comp[:n_turn].tolist()))
co = np.array([v.co[:] for v in me.vertices])
sp_src = np.unique(np.concatenate([list(p.vertices) for p in me.polygons if src[p.index] == src_of[TURNING[0]]]))
pivot = (co[sp_src].min(0) + co[sp_src].max(0)) / 2 * 100
rig = {"spool_parts": spool_parts, "pivot_cm": pivot.round(2).tolist(), "parts": c, "turning_verts": n_turn,
       "z_cm": [round(float(co[:, 2].min() * 100), 1), round(float(co[:, 2].max() * 100), 1)]}
json.dump(rig, open(os.path.join(TEX, f"{NAME}_rig.json"), "w"))
print("  rig", rig)
for mat in list(me.materials): pass
me.materials.clear()
bpy.ops.object.select_all(action='DESELECT'); rod.select_set(True)
obj_path = os.path.join(OUT, "Models", f"{NAME}_source.obj")
bpy.ops.wm.obj_export(filepath=obj_path, export_selected_objects=True, global_scale=100.0, export_materials=False,
                      export_uv=True, export_normals=True, apply_modifiers=False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Blender Files", f"{NAME}_converted.blend"), copy=True)
print("EXPORTED", obj_path)
