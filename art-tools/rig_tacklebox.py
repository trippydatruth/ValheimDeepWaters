# Rigs the tackle box (the user's tacklebox.blend) for a lid that opens and closes, written to a new file.
#   - the old armature (parented to the mesh, nothing bound to it) is removed
#   - the box's object scale is applied, so bones aren't skewed by it
#   - a new armature: "root" (the base, at the bottom centre) and "lid" (its head on the hinge line along the back top
#     edge, pointing forward across the lid; it turns about its own X axis, the hinge)
#   - weights by material: lid -> lid, base -> root; each lock piece goes with the part it sits on mostly (the hasp
#     that reaches higher goes with the lid, the catch with the base) - VDW_LOCK_SWAP=1 swaps them
#   - the box is parented to the armature with an Armature modifier
#   - actions "TackleBox_Open" (closed -> open, VDW_OPEN_DEG, 105) and "TackleBox_Close" (open -> closed), 20 frames
#     each at 24 fps, eased; both kept with fake users and as NLA strips; plus previews of closed / half / open
#   blender -b <tacklebox.blend> --factory-startup --python rig_tacklebox.py   env: VDW_SAVE_TO, VDW_PREVIEW (png prefix)
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector, Matrix

SAVE = os.environ["VDW_SAVE_TO"]; OPEN_DEG = float(os.environ.get("VDW_OPEN_DEG", "105")); FRAMES = 20
box = bpy.data.objects["tacklebox"]
for o in list(bpy.data.objects):
    if o.type == 'ARMATURE': bpy.data.objects.remove(o)
for a in list(bpy.data.actions): bpy.data.actions.remove(a)

# apply the box's transform: its mesh in world space, the object at the origin unscaled
box.data.transform(box.matrix_world); box.matrix_world = Matrix.Identity(4)
me = box.data
co = np.array([v.co[:] for v in me.vertices])
names = [m.name for m in me.materials]; mat_of = np.full(len(co), -1)
for p in me.polygons:
    for vi in p.vertices: mat_of[vi] = p.material_index
lid_c, base_c = co[mat_of == names.index("lid")], co[mat_of == names.index("base")]
seam = (lid_c[:, 2].min() + base_c[:, 2].max()) / 2
front_y = co[mat_of == names.index("lock")][:, 1].mean()                    # the lock is on the front
back = 1.0 if front_y < 0 else -1.0                                          # +Y is the back when the lock is at -Y
hinge_y = lid_c[:, 1].max() if back > 0 else lid_c[:, 1].min()
print(f"RIG seam z {seam:.3f}, front at y {front_y:.3f}, hinge at y {hinge_y:.3f}")

# loose parts, for the lock pieces
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
seen = set(); groups = {"lid": [], "root": []}
for v in bm.verts:
    if v.index in seen: continue
    stack = [v]; idx = []; seen.add(v.index)
    while stack:
        x = stack.pop(); idx.append(x.index)
        for e in x.link_edges:
            w = e.other_vert(x)
            if w.index not in seen: seen.add(w.index); stack.append(w)
    m = names[mat_of[idx[0]]]
    if m == "lid": groups["lid"] += idx
    elif m == "base": groups["root"] += idx
    else:   # a lock piece: the one reaching higher above the seam is the hasp on the lid
        c = co[idx]; up, down = c[:, 2].max() - seam, seam - c[:, 2].min()
        to_lid = up > down
        if os.environ.get("VDW_LOCK_SWAP") == "1": to_lid = not to_lid
        groups["lid" if to_lid else "root"] += idx
        print(f"RIG lock piece {len(idx)} verts (z {c[:, 2].min():.3f}..{c[:, 2].max():.3f}) -> {'lid' if to_lid else 'base'}")
bm.free()
for g in box.vertex_groups: box.vertex_groups.remove(g)
for name, idx in groups.items():
    vg = box.vertex_groups.new(name=name); vg.add(idx, 1.0, 'REPLACE')
print(f"RIG weights: lid {len(groups['lid'])} verts, base {len(groups['root'])} verts")

# the armature
arm_d = bpy.data.armatures.new("TackleBox_Rig"); arm = bpy.data.objects.new("TackleBox_Rig", arm_d)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
for o in bpy.context.view_layer.objects: o.select_set(o is arm)
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_d.edit_bones
root = eb.new("root"); root.head = (0, 0, 0); root.tail = (0, 0, seam * 0.6)
lid = eb.new("lid"); lid.head = (0, hinge_y, seam); lid.tail = (0, hinge_y - back * (lid_c[:, 1].max() - lid_c[:, 1].min()) * 0.5, seam)
lid.parent = root
lid.align_roll(Vector((0, 0, 1)))            # bone Z up, so its X axis lies along the hinge (world X)
bpy.ops.object.mode_set(mode='OBJECT')
for b in arm_d.bones: b.use_deform = True
box.parent = arm; box.matrix_parent_inverse = Matrix.Identity(4)
mod = box.modifiers.new("Armature", 'ARMATURE'); mod.object = arm

# which way opens: the lid's front edge must rise
pb = arm.pose.bones["lid"]; pb.rotation_mode = 'XYZ'
front_vert = int(np.argmin(np.abs(co[:, 1] - (lid_c[:, 1].min() if back > 0 else lid_c[:, 1].max())) + np.abs(co[:, 2] - seam) * 0.1 + (mat_of != names.index("lid")) * 9))
def front_z(deg):
    pb.rotation_euler = (math.radians(deg), 0, 0); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); ev = box.evaluated_get(dg).data
    return ev.vertices[front_vert].co.z
sign = 1.0 if front_z(30) > front_z(0) else -1.0
pb.rotation_euler = (0, 0, 0)
print(f"RIG lid opens with {'+' if sign > 0 else '-'}X rotation")

def make_action(name, start_deg, end_deg):
    arm.animation_data_create(); act = bpy.data.actions.new(name); arm.animation_data.action = act
    for f, deg in ((1, start_deg), (FRAMES, end_deg)):
        pb.rotation_euler = (math.radians(deg) * sign, 0, 0); pb.keyframe_insert("rotation_euler", index=0, frame=f)
    act.use_fake_user = True
    return act
opn = make_action("TackleBox_Open", 0, OPEN_DEG)
cls = make_action("TackleBox_Close", OPEN_DEG, 0)
ad = arm.animation_data; ad.action = None
for act in (opn, cls):
    tr = ad.nla_tracks.new(); tr.name = act.name; st = tr.strips.new(act.name, 1, act); tr.mute = True
pb.rotation_euler = (0, 0, 0)
sc = bpy.context.scene; sc.frame_start, sc.frame_end = 1, FRAMES; sc.render.fps = 24
bpy.ops.wm.save_as_mainfile(filepath=SAVE); print("RIG saved", SAVE)

R = os.environ.get("VDW_PREVIEW")
if R:
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
    sc.render.resolution_x, sc.render.resolution_y = 600, 450
    cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
    cd.type = 'ORTHO'; cd.ortho_scale = 3.6
    tgt = Vector((0, 0, 0.75)); cam.location = tgt + Vector((2.2, -3.2 * (1 if back > 0 else -1), 1.9)); cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    for deg, tag in ((0, "closed"), (OPEN_DEG / 2, "half"), (OPEN_DEG, "open")):
        pb.rotation_euler = (math.radians(deg) * sign, 0, 0); bpy.context.view_layer.update()
        sc.render.filepath = f"{R}_{tag}.png"; bpy.ops.render.render(write_still=True)
print("===== END =====")
