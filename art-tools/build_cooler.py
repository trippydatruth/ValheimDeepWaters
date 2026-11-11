# Builds the three coolers from the user's ice chest model (Mesh\cooler\ice chest.blend: one mesh, the box body and its
# lid, standing open), written to new files only:
#   - the lid (the smaller loose part) is swung shut about its hinge along the back top edge
#   - scaled to VDW_WIDTH metres across (default 0.6), standing on the origin, the lid's hinge at the back (+Y)
#   - rigged like the tackle box: "root" (the body) and "lid" (head on the hinge, pointing forward across the lid)
#   - per tier a colour map baked from a procedural material: c1 oak with dark straps, c2 tarred wood with iron, c3
#     frosted pale wood with silver (the model's two materials: the body, and its trim)
#   - exported per tier as <out>/cooler_cN/cooler_cN_model.fbx + cooler_Unity_Albedo.png, plus a preview
#   blender -b "ice chest.blend" --factory-startup --python build_cooler.py   env: VDW_OUT (new folder), VDW_WIDTH
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

OUT = os.environ["VDW_OUT"]
if os.path.exists(OUT): raise SystemExit("exists, kept: " + OUT)
os.makedirs(OUT)
WIDTH = float(os.environ.get("VDW_WIDTH", "0.6"))
SIZE = min(1024, int(os.environ.get("VDW_SIZE", "1024")))   # textures: 1K at most (low-poly game)

src = [o for o in bpy.data.objects if o.type == 'MESH'][0]
for o in list(bpy.data.objects):
    if o is not src: bpy.data.objects.remove(o)
src.data.transform(src.matrix_world); src.matrix_world = Matrix.Identity(4); src.name = "cooler"; src.data.name = "cooler"
me = src.data
mat_names = [m.name for m in me.materials]
# the model's red material is the cooler's body, its white one the lid and handles (the "trim" here)
trim_idx = next((i for i, m in enumerate(me.materials) if m and tuple(m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value)[1] >= 0.3), None)

# loose parts: the lid is the smaller one, above the body
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
seen = set(); parts = []
for v in bm.verts:
    if v.index in seen: continue
    st = [v]; idx = []; seen.add(v.index)
    while st:
        x = st.pop(); idx.append(x.index)
        for e in x.link_edges:
            w = e.other_vert(x)
            if w.index not in seen: seen.add(w.index); st.append(w)
    parts.append(idx)
parts.sort(key=len, reverse=True)
body_i = set(parts[0])
lid_i = set(i for p in parts[1:] for i in p)
# the lid has a few faces wound the wrong way (its handle): point them all outward (the lid is a closed shape)
bm.faces.ensure_lookup_table()
lid_faces = [f for f in bm.faces if f.verts[0].index in lid_i]
bmesh.ops.recalc_face_normals(bm, faces=lid_faces)
body_top = max(bm.verts[i].co.z for i in body_i)
body_back = max(bm.verts[i].co.y for i in body_i); body_front = min(bm.verts[i].co.y for i in body_i)

# swing the lid shut: turn it until its big flat top faces straight up (measured from the lid's own faces, area weighted)
lz = min(bm.verts[i].co.z for i in lid_i)
low = [bm.verts[i].co for i in lid_i if bm.verts[i].co.z < lz + 0.08]
hinge = sum(low, Vector()) / len(low)                  # roughly where the hinge is: tells which side is the back
bins = {}
for f in lid_faces:
    n = f.normal
    if abs(n.x) > 0.3: continue
    a = round(math.degrees(math.atan2(n.z, n.y)) / 4)
    bins.setdefault(a, []).append(f)
top_bin = max(bins.values(), key=lambda fs: sum(f.calc_area() for f in fs))
near = [f for f in lid_faces if abs(f.normal.x) <= 0.3 and abs(math.degrees(math.atan2(f.normal.z, f.normal.y)) - math.degrees(math.atan2(top_bin[0].normal.z, top_bin[0].normal.y))) < 8]
nsum = sum((f.normal * f.calc_area() for f in near), Vector())
a_top = math.atan2(nsum.z, nsum.y)
if math.sin(a_top) < 0: a_top += math.pi                # that face may be the underside: use the top side
ang = math.pi / 2 - a_top                              # turn about X taking the top's normal to straight up
Rm = Matrix.Rotation(ang, 4, 'X')
for i in lid_i: bm.verts[i].co = Rm @ bm.verts[i].co
# seat it: its underside on the body's top rim, centred over the rim front to back
rim = [bm.verts[i].co for i in body_i if bm.verts[i].co.z > body_top - 0.03]
rim_mid = (min(c.y for c in rim) + max(c.y for c in rim)) / 2
lid_ys = [bm.verts[i].co.y for i in lid_i]
t = Vector((0, rim_mid - (min(lid_ys) + max(lid_ys)) / 2, body_top - min(bm.verts[i].co.z for i in lid_i) - 0.003))
for i in lid_i: bm.verts[i].co += t
# the turn and the move together are one turn about a single point: the real hinge. Opening the lid that far about it
# puts it back exactly where the model has it. Solve (I - R) p = t in the YZ plane.
c, s_ = math.cos(ang), math.sin(ang)
a11, a12, a21, a22 = 1 - c, s_, -s_, 1 - c            # I - R for R = [[c, -s], [s, c]]
det = a11 * a22 - a12 * a21
pivot = Vector((0, (a22 * t.y - a12 * t.z) / det, (-a21 * t.y + a11 * t.z) / det))
print(f"COOLER lid turned {math.degrees(ang):.1f} deg shut; hinge pivot y {pivot.y:.3f} z {pivot.z:.3f}; rim y {min(c.y for c in rim):.3f}..{max(c.y for c in rim):.3f}, lid y {min(lid_ys)+t.y:.3f}..{max(lid_ys)+t.y:.3f}")

# size and place: WIDTH across, on the origin, back at +Y
xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
s = WIDTH / (max(xs) - min(xs))
off = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)))
flip = hinge.y < (body_back + body_front) / 2           # hinge at -Y: turn it round so the back is +Y
for v in bm.verts:
    c = (v.co - off) * s
    if flip: c = Vector((-c.x, -c.y, c.z))
    v.co = c
bm.to_mesh(me); bm.free(); me.update()
dims = [round(max(v.co[k] for v in me.vertices) - min(v.co[k] for v in me.vertices), 3) for k in range(3)]
seam = (body_top - off.z) * s
pv = (pivot - off) * s
if flip: pv = Vector((-pv.x, -pv.y, pv.z))
hinge_y, hinge_z = pv.y, pv.z
print(f"COOLER lid bone at y {hinge_y:.3f} z {hinge_z:.3f}")
print(f"COOLER size {dims} m, lid seam at z {seam:.3f}, hinge y {hinge_y:.3f}")

# UVs: whether they overlap much (a bake into overlapping UVs averages the parts)
uvl = me.uv_layers.active.data
print("COOLER uv range", round(min(l.uv.x for l in uvl), 2), round(max(l.uv.x for l in uvl), 2), round(min(l.uv.y for l in uvl), 2), round(max(l.uv.y for l in uvl), 2))

# rig
for g in src.vertex_groups: src.vertex_groups.remove(g)
vg_l = src.vertex_groups.new(name="lid"); vg_l.add(list(lid_i), 1.0, 'REPLACE')
vg_r = src.vertex_groups.new(name="root"); vg_r.add(list(body_i), 1.0, 'REPLACE')
arm_d = bpy.data.armatures.new("Cooler_Rig"); arm = bpy.data.objects.new("Cooler_Rig", arm_d)
bpy.context.scene.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects: o.select_set(o is arm)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_d.edit_bones
root = eb.new("root"); root.head = (0, 0, 0); root.tail = (0, 0, seam * 0.6)
lid = eb.new("lid"); lid.head = (0, hinge_y, hinge_z); lid.tail = (0, hinge_y - dims[1] * 0.5, hinge_z); lid.parent = root
lid.align_roll(Vector((0, 0, 1)))
bpy.ops.object.mode_set(mode='OBJECT')
src.parent = arm; src.matrix_parent_inverse = Matrix.Identity(4)
src.modifiers.new("Armature", 'ARMATURE').object = arm

# tiers: a procedural look per material, baked to one colour map
TIERS = {
    "c1": dict(body=((0.42, 0.26, 0.13), (0.30, 0.18, 0.09)), trim=((0.55, 0.38, 0.21), (0.40, 0.26, 0.14)), grain=True, trim_grain=True),
    "c2": dict(body=((0.20, 0.14, 0.09), (0.13, 0.09, 0.06)), trim=((0.34, 0.35, 0.37), (0.20, 0.21, 0.23)), grain=True, trim_grain=False),
    "c3": dict(body=((0.74, 0.84, 0.92), (0.55, 0.68, 0.80)), trim=((0.72, 0.74, 0.78), (0.50, 0.53, 0.58)), grain=False, trim_grain=False),
}
def lin(c):   # the tier colours are given as seen (sRGB); the shader works in linear
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def look(name, a, b, grain):
    a, b = lin(a), lin(b)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    tc = nt.nodes.new("ShaderNodeTexCoord"); ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*b, 1); ramp.color_ramp.elements[1].color = (*a, 1)
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 18 / WIDTH; noise.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    if grain:
        wave = nt.nodes.new("ShaderNodeTexWave"); wave.bands_direction = 'X'
        wave.inputs["Scale"].default_value = 9 / WIDTH; wave.inputs["Distortion"].default_value = 6; wave.inputs["Detail"].default_value = 4
        nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMath"); mix.operation = 'MULTIPLY_ADD'; mix.inputs[1].default_value = 0.6
        nt.links.new(wave.outputs["Fac"], mix.inputs[0]); nt.links.new(noise.outputs["Fac"], mix.inputs[2])
        nt.links.new(mix.outputs[0], ramp.inputs["Fac"])
    else:   # frost: speckled
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m

sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
orig = list(me.materials)
face_mat = [p.material_index for p in me.polygons]
src.modifiers["Armature"].show_render = False
for tier, cfg in TIERS.items():
    img = bpy.data.images.new(f"cooler_{tier}", SIZE, SIZE); img.generated_color = (*cfg["body"][1], 1)
    mats = []
    for i, m in enumerate(orig):
        a, b = cfg["trim"] if i == trim_idx else cfg["body"]
        lm = look(f"{tier}_{i}", a, b, cfg["trim_grain"] if i == trim_idx else cfg["grain"])
        tn = lm.node_tree.nodes.new("ShaderNodeTexImage"); tn.image = img; lm.node_tree.nodes.active = tn
        mats.append(lm)
    me.materials.clear()
    for lm in mats: me.materials.append(lm)
    for o in bpy.context.view_layer.objects: o.select_set(o is src)
    bpy.context.view_layer.objects.active = src
    bpy.ops.object.bake(type='EMIT', margin=16)
    folder = os.path.join(OUT, f"cooler_{tier}"); os.makedirs(folder)
    img.filepath_raw = os.path.join(folder, "cooler_Unity_Albedo.png"); img.file_format = 'PNG'; img.save()
    # the exported model: one plain material named after the model
    me.materials.clear()
    plain = bpy.data.materials.get("cooler") or bpy.data.materials.new("cooler"); me.materials.append(plain)
    for p in me.polygons: p.material_index = 0
    for o in bpy.data.objects: o.select_set(o in (src, arm))
    bpy.context.view_layer.objects.active = arm
    tri = src.modifiers.new("tri", 'TRIANGULATE')
    bpy.ops.export_scene.fbx(filepath=os.path.join(folder, f"cooler_{tier}_model.fbx"), use_selection=True, object_types={'ARMATURE', 'MESH'},
                             global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
                             bake_space_transform=False, add_leaf_bones=False, primary_bone_axis='Y', secondary_bone_axis='X',
                             mesh_smooth_type='FACE', use_mesh_modifiers=True, bake_anim=False, path_mode='COPY', embed_textures=False)
    src.modifiers.remove(tri)
    # restore the material slots for the next tier's bake (faces' material indices come back from the saved list)
    me.materials.clear()
    for m in orig: me.materials.append(m)
    for p, mi in zip(me.polygons, face_mat): p.material_index = mi
    print(f"COOLER exported {tier}")
src.modifiers["Armature"].show_render = True
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "cooler_rig.blend"))
print("SAVED", os.path.join(OUT, "cooler_rig.blend"))
