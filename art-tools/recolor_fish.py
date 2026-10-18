# Repaints a rigged fish as a new species. Every texel of the albedo is traced back to its spot on the body (rest pose,
# head toward -Y, up +Z), so the new pattern follows the fish whatever the UV layout:
#   back -> belly shading, 3-D spots / blotches, a lateral line, bars, fin tint, a frost crust on chosen parts.
# The painted light/dark detail of the old texture (scales, gill lines, fin rays) is kept by multiplying it back in.
# Eyes (small loose parts near the head) keep their original colours.
#   blender -b fish.blend --python recolor_fish.py
#   env: VDW_SPECIES (preset below), VDW_NAME (output map name), VDW_TEX_DIR, VDW_SAVE_TO, VDW_PREVIEW (png, optional)
# Writes <NAME>_Unity_Albedo / _MetallicSmoothness / _Normal (+ _Emission) - never overwrites.
import bpy, math, os
import numpy as np
# a file saved in Edit / Weight Paint mode: back to Object Mode first (edits in progress aren't in the mesh data)
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass

SPECIES = os.environ["VDW_SPECIES"]; NAME = os.environ["VDW_NAME"]; TEX = os.environ["VDW_TEX_DIR"]

# h: 0 belly .. 1 back (per slice of the body); t: 0 nose .. 1 tail
PRESETS = {
    "rimejaw_cod": dict(
        back=(0.38, 0.31, 0.18), belly=(0.86, 0.85, 0.78), split=(0.30, 0.60),
        spots=[dict(color=(0.17, 0.13, 0.07), scale=0.016, cut=0.58, soft=0.05, h=(0.35, 1.2), amount=0.85),
               dict(color=(0.46, 0.42, 0.27), scale=0.05, cut=0.6, soft=0.15, h=(0.3, 1.0), amount=0.4)],
        line=None,                   # the Tripo model has its own white lateral line (kept through `keep`)
        fin=dict(color=(0.30, 0.28, 0.18), amount=0.55, edge=(0.80, 0.80, 0.74)),
        frost=dict(color=(0.90, 0.95, 1.0), t=(-0.1, 0.17), h=(-0.6, 0.42), noise=0.02, cut=0.36, glow=(0.35, 0.7, 1.0)),
        source_eyes=dict(r=0.016, at=(-0.3576, 0.0393), search_t=(0.07, 0.14), search_h=(0.5, 0.95)),   # at: measured
        keep=0.5, smooth=0.6),
    "glacier_grayling": dict(
        back=(0.22, 0.27, 0.34), belly=(0.92, 0.92, 0.95), split=(0.4, 0.8), mid=(0.70, 0.64, 0.78),
        spots=[dict(color=(0.06, 0.06, 0.09), scale=0.006, cut=0.74, soft=0.03, h=(0.3, 0.95), t=(0.12, 0.55), amount=0.95)],
        line=None,
        fin=dict(color=(0.42, 0.30, 0.50), amount=0.7, edge=(0.95, 0.55, 0.70),
                 dots=dict(color=(0.35, 0.95, 0.95), scale=0.0035, cut=0.76, glow=(0.25, 0.85, 0.9))),
        frost=dict(color=(0.90, 0.95, 1.0), t=(-0.1, 0.17), h=(-0.6, 0.42), noise=0.02, cut=0.36, glow=(0.35, 0.7, 1.0)),
        source_eyes=dict(r=0.016, at=(-0.1941, -0.0009), search_t=(0.03, 0.12), search_h=(0.3, 0.95)),   # at: measured
        keep=0.5, smooth=0.6),
    "bass": dict(                  # largemouth bass: olive back, a dark blotchy band along the side, white belly
        back=(0.26, 0.30, 0.14), belly=(0.90, 0.89, 0.80), split=(0.25, 0.62), mid=(0.55, 0.58, 0.38),
        spots=[dict(color=(0.10, 0.13, 0.06), scale=0.022, cut=0.5, soft=0.06, h=(0.4, 0.62), t=(0.15, 0.85), amount=0.75)],
        line=dict(color=(0.14, 0.17, 0.08), h=0.5, width=0.05, t=(0.15, 0.85)),
        fin=dict(color=(0.42, 0.44, 0.26), amount=0.45, edge=(0.30, 0.32, 0.18)),
        frost=None,
        source_eyes=dict(r=0.019, at=(-0.1701, 0.0069), search_t=(0.06, 0.18), search_h=(0.3, 0.95)),   # at: measured
        keep=0.6, smooth=0.6),
    "bluegill": dict(              # bluegill: olive-blue back, dark vertical bars, orange breast, pale belly
        back=(0.18, 0.26, 0.22), belly=(0.92, 0.80, 0.55), split=(0.15, 0.6), mid=(0.50, 0.58, 0.45),
        spots=[dict(color=(0.85, 0.42, 0.12), scale=0.05, cut=0.45, soft=0.2, h=(-0.2, 0.25), t=(0.15, 0.6), amount=0.55)],
        line=None, bars=dict(color=(0.10, 0.14, 0.12), count=6, t=(0.25, 0.85), width=0.3, amount=0.4),
        fin=dict(color=(0.30, 0.36, 0.30), amount=0.7, edge=(0.12, 0.16, 0.20)),
        frost=None,
        source_eyes=dict(r=0.027, at=(-0.0857, -0.0029), search_t=(0.05, 0.17), search_h=(0.3, 0.95)),   # at: measured
        keep=0.6, smooth=0.6),
    "sea_bass": dict(              # european sea bass: steel-grey back, bright silver flanks, white belly, a few dark specks
        back=(0.24, 0.28, 0.31), belly=(0.92, 0.93, 0.94), split=(0.3, 0.7), mid=(0.70, 0.73, 0.76),
        spots=[dict(color=(0.16, 0.18, 0.20), scale=0.006, cut=0.8, soft=0.02, h=(0.5, 1.0), t=(0.15, 0.8), amount=0.6)],
        line=dict(color=(0.30, 0.33, 0.36), h=0.55, width=0.012, t=(0.15, 0.85)),
        fin=dict(color=(0.40, 0.44, 0.47), amount=0.55, edge=(0.20, 0.23, 0.26)),
        frost=None,
        source_eyes=dict(r=0.016, at=(-0.2555, 0.0014), search_t=(0.03, 0.13), search_h=(0.3, 0.95)),   # at: measured
        keep=0.6, smooth=0.6),
    "catfish": dict(               # channel catfish: slate blue-grey back, paler silvery sides with dark spots, white belly
        back=(0.22, 0.26, 0.30), belly=(0.88, 0.88, 0.85), split=(0.2, 0.6), mid=(0.55, 0.58, 0.60),
        spots=[dict(color=(0.08, 0.09, 0.10), scale=0.008, cut=0.78, soft=0.02, h=(0.3, 1.0), t=(0.12, 0.85), amount=0.8)],
        line=None,
        fin=dict(color=(0.30, 0.33, 0.36), amount=0.55, edge=(0.16, 0.18, 0.20)),
        frost=None,
        source_eyes=dict(r=0.014, at=(-0.3784, 0.0382), search_t=(0.03, 0.13), search_h=(0.3, 0.95)),   # at: measured
        keep=0.55, smooth=0.6),
    "lingcod": dict(               # a plain deep-ocean lingcod: mottled brown back, copper blotches, pale belly
        back=(0.30, 0.24, 0.18), belly=(0.86, 0.84, 0.80), split=(0.25, 0.6),
        spots=[dict(color=(0.16, 0.12, 0.09), scale=0.03, cut=0.56, soft=0.06, h=(0.35, 1.2), amount=0.6),
               dict(color=(0.62, 0.42, 0.20), scale=0.018, cut=0.64, soft=0.05, h=(0.3, 0.9), amount=0.45)],
        line=None,
        fin=dict(color=(0.20, 0.16, 0.14), amount=0.5, edge=(0.12, 0.10, 0.10)),
        frost=None,
        source_eyes=dict(r=0.014, at=(-0.4943, 0.0362), search_t=(0.04, 0.14), search_h=(0.3, 0.95)),   # at: measured
        keep=0.65, smooth=0.6),
    "mistfin": dict(               # a swamp / Mistlands fish that fades into the fog: pale grey-green, drifting mist wisps
        back=(0.30, 0.38, 0.40), belly=(0.86, 0.88, 0.86), split=(0.2, 0.75), mid=(0.62, 0.68, 0.70),
        spots=[dict(color=(0.88, 0.92, 0.94), scale=0.06, cut=0.58, soft=0.18, h=(0.2, 1.2), amount=0.55),
               dict(color=(0.70, 0.95, 0.90), glow=(0.25, 0.55, 0.50), scale=0.008, cut=0.84, soft=0.02, h=(0.3, 1.0), amount=0.7)],
        line=None,
        fin=dict(color=(0.55, 0.62, 0.64), amount=0.6, edge=(0.92, 0.96, 0.96)),
        frost=None,
        source_eyes=dict(r=0.028, at=(-0.2835, -0.0176), search_t=(0.04, 0.15), search_h=(0.3, 0.95)),   # at: measured
        keep=0.5, smooth=0.6),
    "frost_sculpin": dict(
        back=(0.24, 0.26, 0.28), belly=(0.70, 0.76, 0.84), split=(0.15, 0.5),
        spots=[dict(color=(0.14, 0.15, 0.18), scale=0.022, cut=0.55, soft=0.05, h=(0.25, 1.0), amount=0.85),
               dict(color=(0.36, 0.31, 0.24), scale=0.03, cut=0.6, soft=0.08, h=(0.3, 1.2), amount=0.7),
               dict(color=(0.85, 0.92, 1.0), scale=0.003, cut=0.84, soft=0.02, h=(0.2, 1.0), amount=0.6)],
        line=None, bars=dict(color=(0.12, 0.13, 0.16), count=5, t=(0.25, 0.9), width=0.3, amount=0.45),
        fin=dict(color=(0.30, 0.34, 0.40), amount=0.4, edge=(0.85, 0.92, 1.0), bands=6),
        frost=dict(color=(0.85, 0.93, 1.0), t=(0.0, 0.75), h=(0.95, 1.4), noise=0.012, cut=0.7, glow=(0.3, 0.7, 1.0)),
        source_eyes=dict(r=0.016, at=(-0.1372, 0.0159), search_t=(0.08, 0.14), search_h=(0.55, 0.95)),   # at: measured from the scan
        keep=0.5, smooth=0.55),      # half the scan's own mottling and detail under the frost
}
# Named fish (2026-10-12), styled to their names: veins = glowing cracks/arcs, iron = Mjolnir's head, eyes = painted
# glowing eyes, keep = how much of the species' own colouring shows through.
PRESETS.update({
    "surtling_sardine": dict(      # a sardine of Surtr's fire: charcoal and ash, ember cracks glowing through
        back=(0.10, 0.08, 0.07), belly=(0.42, 0.33, 0.27), split=(0.25, 0.65),
        spots=[dict(color=(0.20, 0.13, 0.09), scale=0.012, cut=0.6, soft=0.05, h=(0.3, 1.2), amount=0.6)],
        veins=[dict(color=(1.0, 0.42, 0.06), glow=(1.0, 0.38, 0.04), scale=0.018, width=0.035, amount=1.0),
               dict(color=(1.0, 0.75, 0.25), glow=(1.0, 0.6, 0.15), scale=0.008, width=0.02, amount=0.6, h=(0.0, 0.7))],
        line=dict(color=(1.0, 0.5, 0.1), h=0.5, width=0.03, t=(0.2, 0.85)),
        fin=dict(color=(0.35, 0.10, 0.04), amount=0.75, edge=(1.0, 0.55, 0.12)),
        frost=None, smooth=0.35),
    "bonemaw": dict(               # pale as old bone, with purple light in its photophores (Dead Raiser's glow)
        back=(0.70, 0.67, 0.60), belly=(0.90, 0.88, 0.82), split=(0.3, 0.8),
        spots=[dict(color=(0.42, 0.38, 0.33), scale=0.06, cut=0.62, soft=0.08, h=(0.4, 1.2), amount=0.45),
               dict(color=(0.85, 0.45, 1.0), glow=(0.75, 0.25, 1.0), scale=0.008, cut=0.8, soft=0.02, h=(-0.2, 0.35), amount=1.0)],
        line=dict(color=(0.75, 0.4, 0.95), h=0.3, width=0.02, t=(0.12, 0.9)),
        fin=dict(color=(0.55, 0.52, 0.5), amount=0.6, edge=(0.85, 0.6, 1.0)),
        frost=None, smooth=0.5),
    "jotunnperch": dict(           # a perch of the frost giants: slate blue, dark bars, rime on its back, keeps its stripes
        back=(0.22, 0.30, 0.38), belly=(0.80, 0.85, 0.90), split=(0.3, 0.75),
        spots=[], line=None,
        bars=dict(color=(0.07, 0.10, 0.15), count=7, t=(0.22, 0.85), width=0.28, amount=0.75),
        fin=dict(color=(0.45, 0.62, 0.80), amount=0.75, edge=(0.90, 0.95, 1.0)),
        frost=dict(color=(0.86, 0.93, 1.0), t=(0.05, 0.85), h=(0.88, 1.4), noise=0.05, cut=0.5, glow=(0.3, 0.7, 1.0)),
        keep=0.15, smooth=0.55),
    "odinfin": dict(               # Odin's cloak-blue, silver star spots, gold fins - and one blazing eye
        back=(0.05, 0.09, 0.26), belly=(0.30, 0.36, 0.55), split=(0.15, 0.7),
        spots=[dict(color=(0.92, 0.92, 0.98), glow=(0.25, 0.25, 0.3), scale=0.012, cut=0.78, soft=0.02, h=(-0.3, 1.3), amount=1.0)],
        line=None,
        fin=dict(color=(0.85, 0.62, 0.18), amount=0.85, edge=(1.0, 0.88, 0.45)),
        eyes=[dict(t=0.085, h=0.80, r=0.04, side=1, color=(1.0, 0.85, 0.35), ring=(1.0, 0.6, 0.1), glow=(1.0, 0.8, 0.3)),
              dict(t=0.085, h=0.80, r=0.035, side=-1, color=(0.55, 0.6, 0.65), ring=(0.3, 0.32, 0.36), glow=(0.0, 0.0, 0.0), pupil=(0.6, 0.62, 0.66))],
        frost=None, smooth=0.6),
    "thorhammerhead": dict(        # storm-grey shark, lightning crawling over it, Mjolnir for a head
        back=(0.24, 0.27, 0.32), belly=(0.82, 0.84, 0.88), split=(0.3, 0.7),
        spots=[], line=None,
        veins=[dict(color=(0.65, 0.88, 1.0), glow=(0.45, 0.78, 1.0), scale=0.35, width=0.012, amount=1.0, t=(-0.1, 1.1), fins=1.0),
               dict(color=(0.8, 0.95, 1.0), glow=(0.6, 0.9, 1.0), scale=0.12, width=0.008, amount=0.7, t=(-0.1, 1.1))],
        no_fin_before=0.25, no_detail_before=0.25,
        iron=dict(t=0.12, color=None,     # Mjolnir's shape only, in shark skin; eyes on the hammer's ends
                  eyes=dict(r=0.022, color=(0.75, 0.9, 1.0), glow=(0.45, 0.8, 1.0)),
                  mouth=dict(width=0.16, color=(0.10, 0.04, 0.05), teeth=(0.92, 0.90, 0.84), spacing=0.012, tooth=0.006),
                  engrave=dict(glyphs=7, height=0.7, stroke=0.0045, frame=0.12, darken=0.35, depth=4.0)),
        fin=dict(color=(0.16, 0.18, 0.22), amount=0.7, edge=(0.6, 0.82, 1.0)),
        frost=None, smooth=0.55),
    "serpentfin": dict(            # an oarfish that learned from Jormungandr: sea-serpent green scales, crimson crest
        back=(0.08, 0.26, 0.22), belly=(0.70, 0.66, 0.45), split=(0.25, 0.7),
        spots=[dict(color=(0.03, 0.14, 0.11), scale=0.03, cut=0.55, soft=0.04, h=(0.3, 1.2), amount=0.7),
               dict(color=(0.35, 0.9, 0.7), glow=(0.15, 0.6, 0.45), scale=0.01, cut=0.82, soft=0.02, h=(0.2, 1.0), amount=0.7)],
        line=dict(color=(0.75, 0.68, 0.35), h=0.45, width=0.02, t=(0.08, 0.95)),
        fin=dict(color=(0.75, 0.10, 0.08), amount=0.9, edge=(1.0, 0.45, 0.25)),
        frost=None, smooth=0.6),
    "frostchar": dict(             # an arctic char of the Deep North: blue-grey back, pale spots, orange belly, white-edged fins
        back=(0.20, 0.28, 0.35), belly=(0.92, 0.55, 0.40), split=(0.2, 0.55), mid=(0.70, 0.74, 0.80),
        spots=[dict(color=(0.88, 0.94, 1.0), scale=0.01, cut=0.7, soft=0.02, h=(0.3, 1.2), amount=0.9)],
        line=None,
        fin=dict(color=(0.80, 0.30, 0.22), amount=0.8, edge=(0.97, 0.98, 1.0)),
        frost=dict(color=(0.86, 0.93, 1.0), t=(-0.1, 0.22), h=(0.6, 1.4), noise=0.02, cut=0.45, glow=(0.3, 0.7, 1.0)),
        source_eyes=dict(r=0.016, at=(-0.2495, 0.0159), search_t=(0.06, 0.11), search_h=(0.55, 0.88)),   # at: measured from the scan
        keep=0.5, smooth=0.6),       # half the scan's own spotting and detail shows through, under the frost
})
P = PRESETS[SPECIES]
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
me = mesh.data
mat = me.materials[0]; nt = mat.node_tree
bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
alb_node = bs.inputs["Base Color"].links[0].from_node; src = alb_node.image
W, H = src.size
spx = np.empty(W * H * 4, np.float32); src.pixels.foreach_get(spx); spx = spx.reshape(H, W, 4)
print(f"\n===== RECOLOR {SPECIES} =====\n  source {src.name} {W}x{H}")

# ---- rest positions, loose parts (eyes)
co = np.array([(mesh.matrix_world @ v.co)[:] for v in me.vertices]); vn = np.array([v.normal[:] for v in me.vertices])
parent = np.arange(len(co))
def find(i):
    while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
    return i
for e in me.edges:
    a, b = find(e.vertices[0]), find(e.vertices[1])
    if a != b: parent[a] = b
roots = np.array([find(i) for i in range(len(co))])
ylo, yhi = co[:, 1].min(), co[:, 1].max(); L = yhi - ylo
eye_v = np.zeros(len(co), bool)
for r in np.unique(roots):
    m = roots == r
    ext = (co[m].max(0) - co[m].min(0)).max() / L
    if m.sum() < 0.05 * len(co) and ((co[m, 1].mean() - ylo) / L) < 0.3 and ext < 0.07: eye_v |= m
print(f"  loose parts {len(np.unique(roots))}, eye vertices {eye_v.sum()}")

# body or fin, per face (the same test as seam_unwrap): a ray shot backward hits the inside of a far wall -> body;
# a near wall -> a two-sided fin; nothing / the outside of something -> a one-layer fin
import bmesh
from mathutils.bvhtree import BVHTree
bm = bmesh.new(); bm.from_mesh(me); bm.transform(mesh.matrix_world); bm.faces.ensure_lookup_table(); bvh = BVHTree.FromBMesh(bm)
THIN = 0.035 * L / 2.0
fbody = np.zeros(len(bm.faces), bool)
for f in bm.faces:
    n = f.normal
    if n.length < 0.5: fbody[f.index] = True; continue
    loc, hn, _i, dist = bvh.ray_cast(f.calc_center_median() - n * 1e-5, -n)
    fbody[f.index] = loc is not None and hn.dot(n) <= 0 and dist >= THIN
for _ in range(1):   # speckle only: one pass (more spreads fin into a low-poly body where fins are welded on)
    nb = fbody.copy()
    for f in bm.faces:
        o = [fbody[x.index] for e in f.edges for x in e.link_faces if x != f]
        if len(o) >= 3 and sum(o) > 0.8 * len(o): nb[f.index] = True
        elif len(o) >= 3 and sum(o) == 0: nb[f.index] = False
    fbody = nb
fc = np.array([f.calc_center_median()[:] for f in bm.faces]); fa = np.array([f.calc_area() for f in bm.faces])
# fin weight per POINT, smoothed over the mesh, then interpolated across each triangle: colours blend over a few
# faces instead of switching at a polygon edge (which left jagged, stair-stepped colour borders)
vfin = np.zeros(len(bm.verts), np.float32)
for v in bm.verts:
    lf = v.link_faces
    vfin[v.index] = float(np.mean([0.0 if fbody[f.index] else 1.0 for f in lf])) if lf else 0.0
nbrs = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
for _ in range(int(os.environ.get("VDW_FIN_SOFT", "3"))):
    vfin = 0.5 * vfin + 0.5 * np.array([vfin[n].mean() if n else vfin[i] for i, n in enumerate(nbrs)], np.float32)
bm.free()
print(f"  body faces {fbody.sum()} of {len(fbody)} ({fa[fbody].sum() / fa.sum() * 100:.0f}% of the surface)")
# body slices from the body faces only: mid height, half height, half width
NB = 48; bins = np.clip(((fc[:, 1] - ylo) / L * NB).astype(int), 0, NB - 1)
zlo = np.zeros(NB); zhi = np.zeros(NB); xw = np.zeros(NB)
for b in range(NB):
    s = fc[(bins == b) & fbody]
    if len(s) < 6: s = fc[(np.abs(bins - b) <= 3) & fbody]
    if len(s) < 3: s = fc[np.abs(bins - b) <= 3]
    zlo[b], zhi[b] = np.percentile(s[:, 2], 3), np.percentile(s[:, 2], 97); xw[b] = max(np.percentile(np.abs(s[:, 0]), 97), 1e-3)
k_ = np.ones(9) / 9
zlo, zhi, xw = (np.convolve(np.pad(a, 4, mode='edge'), k_, 'valid') for a in (zlo, zhi, xw))

# UV islands (faces joined where they share an edge with the same UVs), so the pixelation below never averages two
# islands that happen to sit next to each other in the texture (that bled one part's colour into another)
uvl = me.uv_layers.active.data
_par = list(range(len(me.polygons)))
def _f(i):
    while _par[i] != i: _par[i] = _par[_par[i]]; i = _par[i]
    return i
_edge = {}
for p_ in me.polygons:
    li = list(p_.loop_indices)
    for k in range(len(li)):
        a_l, b_l = li[k], li[(k + 1) % len(li)]
        va, vb = me.loops[a_l].vertex_index, me.loops[b_l].vertex_index
        key_ = (min(va, vb), max(va, vb))
        uvk = tuple(sorted([(va, round(uvl[a_l].uv[0], 5), round(uvl[a_l].uv[1], 5)), (vb, round(uvl[b_l].uv[0], 5), round(uvl[b_l].uv[1], 5))]))
        if key_ in _edge:
            q_, uvq = _edge[key_]
            if uvq == uvk: _par[_f(p_.index)] = _f(q_)
        else: _edge[key_] = (p_.index, uvk)
poly_isl = np.array([_f(i) for i in range(len(me.polygons))], np.int64)
print(f"  UV islands: {len(np.unique(poly_isl))}")

# ---- rasterise: texel -> position, eye flag
finm = np.zeros((H, W), np.float32); pos = np.zeros((H, W, 3), np.float32); nor = np.zeros((H, W, 3), np.float32); cov = np.zeros((H, W), bool); eye = np.zeros((H, W), bool)
isl = np.full((H, W), -1, np.int64)
me.calc_loop_triangles()
for tri in me.loop_triangles:
    uv = np.array([uvl[l].uv[:] for l in tri.loops]) * (W, H); P3 = co[list(tri.vertices)]
    x0, y0 = np.floor(uv.min(0)).astype(int) - 1; x1, y1 = np.ceil(uv.max(0)).astype(int) + 1
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W - 1), min(y1, H - 1)
    if x1 < x0 or y1 < y0: continue
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    (ax_, ay), (bx, by), (cx, cy) = uv
    den = (by - cy) * (ax_ - cx) + (cx - bx) * (ay - cy)
    if abs(den) < 1e-9: continue
    l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den; l2 = ((cy - ay) * (xs - cx) + (ax_ - cx) * (ys - cy)) / den; l3 = 1 - l1 - l2
    ins = (l1 >= -0.02) & (l2 >= -0.02) & (l3 >= -0.02)
    if not ins.any(): continue
    p = l1[ins, None] * P3[0] + l2[ins, None] * P3[1] + l3[ins, None] * P3[2]
    yy, xx = (ys[ins] - 0.5).astype(int), (xs[ins] - 0.5).astype(int)
    F3 = vfin[list(tri.vertices)]
    pos[yy, xx] = p; cov[yy, xx] = True; finm[yy, xx] = l1[ins] * F3[0] + l2[ins] * F3[1] + l3[ins] * F3[2]
    N3 = vn[list(tri.vertices)]; nor[yy, xx] = l1[ins, None] * N3[0] + l2[ins, None] * N3[1] + l3[ins, None] * N3[2]
    if eye_v[list(tri.vertices)].all(): eye[yy, xx] = True
    isl[yy, xx] = poly_isl[tri.polygon_index]
print(f"  covered {cov.mean() * 100:.1f}% of the texture, eyes {eye.sum()} texels")
# grow into the padding so seams don't show (far enough for the pixelation blocks below not to pull in background)
PIX = int(os.environ.get("VDW_PIXEL", "8")); PBLUR = float(os.environ.get("VDW_PIXEL_BLUR", "2.5"))
for _ in range(6 + 2 * PIX):
    grow = ~cov
    if not grow.any(): break
    acc = np.zeros_like(pos); nacc = np.zeros_like(pos); facc = np.zeros((H, W)); n = np.zeros((H, W))
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sh = np.roll(np.roll(cov, dy, 0), dx, 1); acc += np.roll(np.roll(pos, dy, 0), dx, 1) * sh[..., None]; n += sh
        nacc = nacc + np.roll(np.roll(nor, dy, 0), dx, 1) * sh[..., None]; facc = facc + np.roll(np.roll(finm, dy, 0), dx, 1) * sh
        eye |= np.roll(np.roll(eye, dy, 0), dx, 1) & grow
        cand = np.roll(np.roll(isl, dy, 0), dx, 1); isl = np.where(grow & (isl < 0) & (cand >= 0), cand, isl)
    new = grow & (n > 0); pos[new] = acc[new] / n[new, None]; nor[new] = nacc[new] / n[new, None]; finm[new] = facc[new] / n[new]; cov |= new

def sm(e0, e1, x): q = np.clip((x - e0) / (e1 - e0), 0, 1); return q * q * (3 - 2 * q)
X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
t = np.clip((Y - ylo) / L, 0, 1); tc = (np.arange(NB) + 0.5) / NB
zl, zh, xwid = (np.interp(t, tc, a).astype(np.float32) for a in (zlo, zhi, xw))   # smooth along the body
h = np.clip((Z - zl) / np.maximum(zh - zl, 1e-4), -0.5, 1.5)
zm = (zl + zh) / 2; hh = np.maximum((zh - zl) / 2, 1e-4)
ell = (X / xwid) ** 2 + ((Z - zm) / hh) ** 2
nx = np.abs(nor[..., 0]) / np.maximum(np.linalg.norm(nor, axis=-1), 1e-6)
fin = finm * sm(0.05, 0.11, (Y - ylo) / L)
if P.get("no_fin_before"):   # e.g. a hammer and handle: ridges there aren't fins
    fin = fin * sm(P["no_fin_before"], P["no_fin_before"] + 0.02, (Y - ylo) / L)                                     # from the ray test above (not the lips)
if os.environ.get("VDW_DEBUG_FIN"):
    _d = bpy.data.images.new("finmask", W, H); _a = np.ones((H, W, 4), np.float32); _a[..., 0] = fin; _a[..., 1] = cov; _a[..., 2] = 0
    _d.pixels.foreach_set(_a.ravel()); _d.filepath_raw = os.environ["VDW_DEBUG_FIN"]; _d.file_format = 'PNG'; _d.save()
def band(x, a, b, soft=0.05): return sm(a - soft, a + soft, x) * (1 - sm(b - soft, b + soft, x))

rng = np.random.default_rng(5)
def noise3(scale, seed):
    """3-D value noise at `scale` metres per cell, sampled at every texel's body position."""
    r = np.random.default_rng(seed); n = int(math.ceil(L / scale)) + 4
    g = r.random((n, n, n)).astype(np.float32)
    q = (pos - (co.min(0) - scale)) / scale; i = np.floor(q).astype(int); f = q - i; f = f * f * (3 - 2 * f)
    i = np.clip(i, 0, n - 2); out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                out = out + w * g[i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz]
    return out
def fbm3(scale, seed): return 0.6 * noise3(scale, seed) + 0.3 * noise3(scale / 2.3, seed + 1) + 0.1 * noise3(scale / 5.1, seed + 2)
def mix(a, b, w): return a * (1 - w[..., None]) + np.asarray(b, np.float32) * w[..., None]

# ---- paint
col = np.zeros((H, W, 3), np.float32)
back, belly = np.array(P["back"]), np.array(P["belly"])
wsplit = sm(P["split"][0], P["split"][1], h + 0.06 * (fbm3(0.04, 1) - 0.5))
if "mid" in P:
    col = mix(mix(np.broadcast_to(belly, col.shape).copy(), P["mid"], sm(0.0, P["split"][0], h)), back, wsplit)
else:
    col = mix(np.broadcast_to(belly, col.shape).copy(), back, wsplit)
emit = np.zeros_like(col)
for k, s in enumerate(P.get("spots", [])):
    n = fbm3(s["scale"], 10 + k); m = sm(s["cut"] - s["soft"], s["cut"] + s["soft"], n)
    m *= band(h, *s["h"], 0.08)
    if "t" in s: m *= band(t, *s["t"], 0.04)
    col = mix(col, s["color"], m * s["amount"] * (1 - fin))
    if "glow" in s: emit += np.asarray(s["glow"], np.float32) * (m * s["amount"] * (1 - fin))[..., None]
if P.get("line"):
    ln = P["line"]; m = sm(ln["width"], 0, np.abs(h - ln["h"] - 0.02 * (noise3(0.03, 30) - 0.5))) * band(t, *ln["t"], 0.03)
    col = mix(col, ln["color"], m * (1 - fin))
if P.get("bars"):
    b_ = P["bars"]; ph = (t - b_["t"][0]) / (b_["t"][1] - b_["t"][0]) * b_["count"]
    m = sm(b_["width"], 0, np.abs(ph - np.round(ph)) + 0.15 * (fbm3(0.03, 40) - 0.5)) * band(t, *b_["t"], 0.03) * sm(0.2, 0.5, h)
    col = mix(col, b_["color"], m * b_["amount"])
fn = P["fin"]
fcol = mix(col, fn["color"], np.full((H, W), fn["amount"], np.float32))
if fn.get("bands"):
    rr = np.sqrt(ell); m = sm(0.25, 0.05, np.abs((rr * fn["bands"]) % 1 - 0.5)); fcol = mix(fcol, np.array(fn["color"]) * 0.5, m * 0.6)
if fn.get("dots"):
    d = fn["dots"]; m = sm(d["cut"] - 0.03, d["cut"] + 0.03, noise3(d["scale"], 50)); fcol = mix(fcol, d["color"], m)
    emit += np.asarray(d["glow"]) * (m * fin)[..., None] * 0.8
edge = sm(1.3, 2.4, np.sqrt(ell) + 2.5 * np.clip(t - 0.86, 0, 1)) * fin
fcol = mix(fcol, fn["edge"], edge * 0.7)
col = mix(col, fcol, fin)
if P.get("frost"):
    fr = P["frost"]; n = fbm3(fr["noise"], 60)
    m = band(t, *fr["t"], 0.04) * band(h, *fr["h"], 0.08) * sm(fr["cut"] - 0.05, fr["cut"] + 0.05, n + 0.15 * band(t, *fr["t"], 0.06))
    col = mix(col, fr["color"], m)
    emit += np.asarray(fr["glow"]) * (m * sm(0.6, 0.8, n))[..., None] * 0.5
    frost_m = m
else:
    frost_m = np.zeros((H, W), np.float32)
# veins: thin wandering lines (ember cracks, lightning) - the 0.5 crossing of 3-D noise - optionally glowing
for k, vn in enumerate(P.get("veins", [])):
    n = fbm3(vn["scale"], 70 + k)
    m = sm(vn["width"], 0.0, np.abs(n - 0.5)) * band(h, *vn.get("h", (-1, 2)), 0.08) * band(t, *vn.get("t", (-1, 2)), 0.03)
    m *= 1 - fin * (1 - vn.get("fins", 0.0))
    col = mix(col, vn["color"], m * vn.get("amount", 1.0))
    if "glow" in vn: emit += np.asarray(vn["glow"], np.float32) * (m * vn.get("amount", 1.0))[..., None]
# iron head (Mjolnir): everything ahead of t_end is forged iron, with glowing rune bands across it
metal = np.zeros((H, W), np.float32); engrave_h = None
crisp = np.zeros((H, W), np.float32)    # small details (eyes, mouth, teeth, runes) kept sharp through the pixelation
if P.get("iron"):
    ir = P["iron"]; m = 1 - sm(ir["t"] - 0.01, ir["t"] + 0.01, t)
    n = fbm3(0.05, 80)
    if ir.get("color") is not None:      # no colour: the hammer keeps the body's paint (shape only)
        col = mix(col, np.asarray(ir["color"]) * (0.8 + 0.4 * n[..., None]), m)
        metal = np.maximum(metal, m * ir.get("metal", 0.8))
    # eyes on the hammer's end faces (the domes mjolnir_head.py raised)
    if ir.get("eyes"):
        ey = ir["eyes"]; xm = np.abs(X); end = (m > 0.5) & (xm > xm[m > 0.5].max() * 0.97)
        if end.any():
            cy_, cz_ = float(np.median(Y[end])), float(np.median(Z[end]))
            d = np.sqrt((Y - cy_) ** 2 + (Z - cz_) ** 2) / L
            me_ = sm(ey["r"], ey["r"] * 0.6, d) * (xm > xm[m > 0.5].max() * 0.9) * m
            pu = sm(ey["r"] * 0.35, ey["r"] * 0.2, d) * me_
            col = mix(col, ey["color"], me_); col = mix(col, ey.get("pupil", (0.03, 0.03, 0.05)), pu)
            emit += np.asarray(ey["glow"], np.float32) * (me_ * (1 - pu))[..., None]; crisp = np.maximum(crisp, me_)
    hp = mesh.get("vdw_hammer")      # written by mjolnir_head.py: the hammer's place, as shares of the length
    if hp is not None and (ir.get("mouth") or ir.get("engrave")):
        t_yc, s_hd, s_hl, s_hh, sweep, m_back, m_curve, m_half = list(hp)
        yc_w = ylo + t_yc * L; hd_w, hl_w, hh_w = s_hd * L, s_hl * L, s_hh * L
        nn = nor / np.maximum(np.linalg.norm(nor, axis=-1, keepdims=True), 1e-6)
        hm = m > 0.5; zc_w = float(np.median(Z[hm])) if hm.any() else 0.0
        a_ = np.clip(np.abs(X) / hl_w, 0, 1)
        y_mid = yc_w + sweep * hd_w * np.maximum(0.0, (a_ - 0.3) / 0.7) ** 2          # the hammer's centre line, swept back
        if ir.get("mouth"):          # a dark crescent with teeth along the groove under the front
            mo = ir["mouth"]; under = m * sm(-0.55, -0.8, nn[..., 2])
            ym = yc_w + hd_w * (m_back + m_curve * (X / (m_half * hl_w)) ** 2)
            w = mo["width"] * hd_w; d = np.abs(Y - ym)
            span = sm(m_half * hl_w, (m_half - 0.08) * hl_w, np.abs(X))
            mouth = sm(w, w * 0.45, d) * under * span
            col = mix(col, mo["color"], mouth); crisp = np.maximum(crisp, sm(0, 0.3, mouth))
            frac = (X / (mo["spacing"] * L)) % 1.0; tri = 1 - np.abs(2 * frac - 1)
            teeth = sm(mo["tooth"] * L * tri + 1e-5, 0, np.abs(d - w)) * (d > w * 0.6) * under * span
            col = mix(col, mo["teeth"], teeth); crisp = np.maximum(crisp, teeth)
            print(f"  mouth: {int((mouth > 0.5).sum())} texels, teeth {int((teeth > 0.5).sum())}")
        if ir.get("engrave"):        # rune bands carved into the hammer's faces (height -> normal map + darker grooves)
            en = ir["engrave"]; rng_e = np.random.default_rng(en.get("seed", 7))
            front, back_, top = nn[..., 1] < -0.75, nn[..., 1] > 0.75, nn[..., 2] > 0.75
            inblock = (Y < y_mid + hd_w * 0.98) & (Y > y_mid - hd_w * 1.6)        # the hammer itself, not the handle
            face = (front | back_ | top) & hm & inblock & (a_ < 0.86)
            u = X / hl_w                                                # -1..1 along the hammer
            v = np.where(top, (Y - y_mid) / hd_w, (Z - zc_w) / hh_w)  # across the face
            su, sv = hl_w, np.where(top, hd_w, hh_w)                     # back to metres, so strokes are even
            # glyphs: a stave plus two branches, in slots along the hammer; a framing line above and below the band
            BR = [((0, .5), (.32, .18)), ((0, .5), (-.32, .18)), ((0, .1), (.32, -.22)), ((0, .1), (-.32, -.22)),
                  ((0, -.5), (.3, -.2)), ((0, -.5), (-.3, -.2)), ((-.3, .3), (.3, -.3)), ((0, .25), (.3, .25))]
            nslot = en["glyphs"]; gw = 1.6 / nslot; gh = en["height"]; sw = en["stroke"] * L
            dmin = np.full(u.shape, 9.0, np.float32)
            for k in range(nslot):
                cu = -0.8 + gw * (k + 0.5)
                segs = [((0, -.5), (0, .5))] + [BR[i] for i in rng_e.choice(len(BR), 2, replace=False)]
                for (x1, y1), (x2, y2) in segs:
                    ax_, ay_ = cu + x1 * gw * 0.8, y1 * gh; bx_, by_ = cu + x2 * gw * 0.8, y2 * gh
                    dx, dy = bx_ - ax_, by_ - ay_; ln2 = dx * dx + dy * dy + 1e-9
                    tt = np.clip(((u - ax_) * dx * su * su + (v - ay_) * dy * sv * sv) / (dx * dx * su * su + dy * dy * sv * sv + 1e-12), 0, 1)
                    dmin = np.minimum(dmin, np.hypot((u - (ax_ + tt * dx)) * su, (v - (ay_ + tt * dy)) * sv))
            for yy_ in (-0.5 * gh - en["frame"], 0.5 * gh + en["frame"]):
                dmin = np.minimum(dmin, np.abs(v - yy_) * sv + np.maximum(0, np.abs(u) - 0.82) * su)
            carve = (sm(sw, sw * 0.4, dmin) * face).astype(np.float32)
            col = col * (1 - en["darken"] * carve[..., None]); crisp = np.maximum(crisp, sm(0, 0.4, carve))
            engrave_h = -carve * en["depth"]; engrave_face = face
            print(f"  engravings: {nslot} runes per face, {int((carve > 0.5).sum())} carved texels")
    if ir.get("grip"):     # the handle (neck): dark leather with a spiral wrap
        gp = ir["grip"]; g_ = band(t, gp["t"][0], gp["t"][1], 0.012)
        zc_ = float(np.median(Z[g_ > 0.5])) if (g_ > 0.5).any() else 0.0
        spiral = (t * gp["turns"] / (gp["t"][1] - gp["t"][0]) + np.arctan2(Z - zc_, X) / (2 * math.pi)) % 1.0
        wrap = sm(0.12, 0.0, np.abs(spiral - 0.5) - 0.32)
        col = mix(col, gp["color"], g_); col = mix(col, gp["wrap"], g_ * wrap)
    if ir.get("runes"):
        rn = ir["runes"]; xa = np.abs(X) / max(np.abs(X[m > 0.5]).max() if (m > 0.5).any() else 1.0, 1e-4)
        bands_ = sum(band(xa, c - rn["width"], c + rn["width"], 0.01) for c in rn["at"])
        strokes = sm(0.72, 0.76, noise3(rn["scale"], 90)) * band(xa, 0.12, 0.9, 0.02)
        rm = np.clip(bands_ + strokes * 0.8, 0, 1) * m
        col = mix(col, rn["color"], rm); emit += np.asarray(rn["glow"], np.float32) * rm[..., None]

# old painted detail back in: luminance against its local average
lum = spx[..., :3].mean(-1)
def blur(a, r):
    c = np.cumsum(np.cumsum(np.pad(a, ((r + 1, r), (r + 1, r)), mode='edge'), 0), 1)
    return (c[2 * r + 1:, 2 * r + 1:] - c[:-2 * r - 1, 2 * r + 1:] - c[2 * r + 1:, :-2 * r - 1] + c[:-2 * r - 1, :-2 * r - 1]) / (2 * r + 1) ** 2
det = np.clip(lum / np.maximum(blur(lum, 12), 0.03), 0.55, 1.5) ** 0.8
if P.get("no_detail_before"):   # built-on parts (hammer, neck blend) map to a few stretched texels: no old detail there
    nd_ = sm(P["no_detail_before"], P["no_detail_before"] + 0.03, t); det = det * nd_ + (1 - nd_)
col = np.clip(col * det[..., None], 0, 1)
if P.get("keep"):     # let some of the species' own colours through
    col = mix(col, spx[..., :3], (P["keep"] * (1 - frost_m)).astype(np.float32))   # the frost stays on top
col[eye] = spx[eye, :3]
emit[eye] = 0
# source_eyes: keep the source texture's own eyes, where the source has them. On each side, the darkest small spot high
# on the head (luminance blurred over about an eye's width) is the eye; a circle of radius r (share of the length)
# round it shows the source texture untouched, feathered at the rim.
if P.get("source_eyes"):
    se = P["source_eyes"]; lum_s = spx[..., :3].mean(-1)
    valid = cov & (spx[..., :3].max(-1) > 0.03)       # real paint, not the black padding between islands
    lb = blur(np.where(valid, lum_s, 1.0).astype(np.float32), 3)
    # an eye in the texture: a small dark pupil inside a lighter ring - the spot darkest compared with its surroundings
    # (fine blur minus wide blur), searched where the eye sits on this species
    fine = blur(np.where(valid, lum_s, 0.5).astype(np.float32), 2); wide = blur(np.where(valid, lum_s, 0.5).astype(np.float32), 12)
    dog = fine - wide
    for sgn in (1, -1):
        cand = valid & (fin < 0.3) & (X * sgn > 0) & (t > se["search_t"][0]) & (t < se["search_t"][1]) & (h > se["search_h"][0]) & (h < se["search_h"][1])
        if not cand.any(): continue
        if "at" in se:   # measured by hand (y, z in the mesh): the outermost texel on that side at that spot
            near_yz = np.hypot(Y - se["at"][0], Z - se["at"][1])
            side_ok = valid & (X * sgn > 0) & (near_yz < 0.006 * L)
            if not side_ok.any(): continue
            iy, ix = np.unravel_index(np.argmax(np.where(side_ok, np.abs(X), -1.0)), X.shape)
        else:
            iy, ix = np.unravel_index(np.argmin(np.where(cand, dog, 9.0)), dog.shape)
        c3 = pos[iy, ix]
        d = np.linalg.norm(pos - c3, axis=-1) / L
        m = sm(se["r"], se["r"] * 0.7, d) * (X * sgn > 0) * valid
        col = mix(col, spx[..., :3], m); emit *= (1 - m)[..., None]; crisp = np.maximum(crisp, m)
        print(f"  source eye ({'+X' if sgn > 0 else '-X'}): at {t[iy, ix]:.3f} of the length, height {h[iy, ix]:.2f}, contrast {dog[iy, ix]:.2f}, {int((m > 0.5).sum())} texels kept")
# a painted, glowing eye placed by body position (for models whose eyes aren't separate parts); side +1/-1 = only
# that side's eye (+X / -X), 0 = both
for ey in P.get("eyes", []):
    dt = (t - ey["t"]) * L; dh = (h - ey["h"]) * np.maximum(zh - zl, 1e-4)
    d = np.sqrt(dt ** 2 + dh ** 2) / L
    m = sm(ey["r"], ey["r"] * 0.55, d) * (1 - fin)
    if ey.get("side", 0): m *= (X * ey["side"] > 0)
    ring = m * sm(ey["r"] * 0.35, ey["r"] * 0.6, d)
    col = mix(col, ey["color"], m); col = mix(col, ey.get("ring", ey["color"]), ring * 0.6)
    pupil = sm(ey["r"] * 0.22, ey["r"] * 0.12, d) * m
    col = mix(col, ey.get("pupil", (0.05, 0.03, 0.02)), pupil)
    emit += np.asarray(ey["glow"], np.float32) * (m * (1 - pupil))[..., None]; crisp = np.maximum(crisp, m)

# ---- write
def save(arr, name, nc=False):
    path = os.path.join(TEX, f"{NAME}_Unity_{name}.png")
    if os.path.exists(path): print("  exists, kept:", path); return bpy.data.images.load(path)
    im = bpy.data.images.new(f"{NAME}_Unity_{name}", W, H, alpha=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    rgba = np.ones((H, W, 4), np.float32); rgba[..., :arr.shape[-1]] = arr
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); print("  saved", path); return im
# Valheim look: the paint is pixelated into PIX-texel blocks (block average), then lightly blurred so the block
# edges soften the way Valheim's low-res textures read in game. VDW_PIXEL=0 turns it off.
def pixel_soft(a):
    """Block average within each UV island (a block straddling two islands averages each island's texels apart),
    then a soft blur that only mixes neighbours of the same island."""
    if PIX <= 1: return a
    hh_, ww_ = a.shape[0], a.shape[1]; c = a.shape[2]
    by_, bx_ = np.meshgrid(np.arange(hh_) // PIX, np.arange(ww_) // PIX, indexing='ij')
    block = (by_ * ((ww_ + PIX - 1) // PIX) + bx_).astype(np.int64)
    _, key = np.unique(block * (int(isl.max()) + 2) + (isl + 1), return_inverse=True); key = key.reshape(hh_, ww_)
    cnt = np.bincount(key.ravel())
    out = np.empty_like(a)
    for ch in range(c):
        out[..., ch] = (np.bincount(key.ravel(), weights=a[..., ch].ravel()) / cnt)[key]
    for _ in range(max(1, int(round(PBLUR * 1.5)))):
        acc = out.copy(); n = np.ones((hh_, ww_, 1), np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            same = (np.roll(np.roll(isl, dy, 0), dx, 1) == isl)[..., None]
            acc += np.roll(np.roll(out, dy, 0), dx, 1) * same; n += same
        out = acc / n
    return out
if PIX > 1:
    cm_ = crisp[..., None]
    col = np.clip(pixel_soft(col) * (1 - cm_) + col * cm_, 0, 1); emit = np.clip(pixel_soft(emit) * (1 - cm_) + emit * cm_, 0, None)
    print(f"  pixelated in {PIX}-texel blocks, blur {PBLUR}")
alb = save(col, "Albedo")
ms = np.zeros((H, W, 4), np.float32); ms[..., 3] = np.clip(P["smooth"] + 0.2 * (det - 1) - 0.3 * frost_m, 0.2, 0.9)
ms[..., 0] = ms[..., 1] = ms[..., 2] = metal
msi = save(ms, "MetallicSmoothness", True)
nrm_node = next((n for n in nt.nodes if n.type == 'NORMAL_MAP'), None)
if nrm_node and nrm_node.inputs["Color"].links:
    nimg = nrm_node.inputs["Color"].links[0].from_node.image
    npx = np.empty(nimg.size[0] * nimg.size[1] * 4, np.float32); nimg.pixels.foreach_get(npx)
    npx = npx.reshape(nimg.size[1], nimg.size[0], 4)
    if P.get("no_detail_before") and npx.shape[:2] == t.shape:    # the stretched old normal detail goes flat there too
        nd_ = sm(P["no_detail_before"], P["no_detail_before"] + 0.03, t)[..., None]
        npx = npx.copy(); npx[..., :3] = npx[..., :3] * nd_ + np.array([0.5, 0.5, 1.0], np.float32) * (1 - nd_)
    if engrave_h is not None and npx.shape[:2] == engrave_h.shape:
        # carved height -> tangent-space slopes (texture u/v follow the tangent/bitangent), added to the baked normal
        gy_, gx_ = np.gradient(engrave_h)
        # only on the hammer's own faces: other islands packed next to them in the texture must not pick up the slope
        inner = engrave_face & np.roll(engrave_face, 1, 0) & np.roll(engrave_face, -1, 0) & np.roll(engrave_face, 1, 1) & np.roll(engrave_face, -1, 1)
        gx_ = gx_ * inner; gy_ = gy_ * inner
        nv = npx[..., :3] * 2 - 1; nv[..., 0] -= gx_; nv[..., 1] -= gy_
        nv /= np.maximum(np.linalg.norm(nv, axis=-1, keepdims=True), 1e-6)
        npx = npx.copy(); npx[..., :3] = nv * 0.5 + 0.5
        print(f"  engravings carved into the normal map (steepest slope {np.hypot(gx_, gy_).max():.2f})")
    newn = save(npx, "Normal", True); nrm_node.inputs["Color"].links[0].from_node.image = newn
alb_node.image = alb
for n in nt.nodes:
    if n.type == 'TEX_IMAGE' and n.image and "MetallicSmoothness" in n.image.name: n.image = msi
if emit.max() > 0.01:
    em = save(np.clip(emit, 0, 1), "Emission")
    e = nt.nodes.new("ShaderNodeTexImage"); e.image = em; nt.links.new(e.outputs["Color"], bs.inputs["Emission Color"]); bs.inputs["Emission Strength"].default_value = 1.5
for img in list(bpy.data.images):
    if img.users == 0: bpy.data.images.remove(img)
mat.name = NAME
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])

R = os.environ.get("VDW_PREVIEW")
if R:
    sc = bpy.context.scene; sc.render.use_border = False; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24
    sc.view_settings.view_transform = 'Standard'; sc.render.resolution_x, sc.render.resolution_y = 900, 450
    wd = bpy.data.worlds.new("w"); wd.use_nodes = True; sc.world = wd; wd.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.38, 0.42, 1)
    ld = bpy.data.lights.new("k", 'SUN'); ld.energy = 3; lo = bpy.data.objects.new("k", ld); sc.collection.objects.link(lo); lo.rotation_euler = (0.5, 0.3, 0.6)
    cd = bpy.data.cameras.new("C"); cd.type = 'ORTHO'; cd.ortho_scale = L * 1.1; cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    arm.data.pose_position = 'REST'
    from mathutils import Vector
    for nm_, d in (("side", Vector((1, 0, 0.12))), ("top", Vector((0.5, 0.15, 1.0)))):
        cam.location = d.normalized() * 3; cam.rotation_euler = (-cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f"{R}_{nm_}.png"; bpy.ops.render.render(write_still=True)
print("===== END =====")
