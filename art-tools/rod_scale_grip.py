# Scales a rigged rod (rig_rod.py output) and adds the Rod.Grip marker bone: where the hand holds the rod, on the
# handle's centre line at VDW_GRIP_Z (metres up from the butt, before scaling). The mod puts this point in the
# player's hand. Markers are deform bones with no weights, like Rod.Tip.
# env: VDW_SCALE (default 1.3), VDW_GRIP_Z (default 0.27), VDW_SAVE_TO
import bpy, os
import numpy as np
from mathutils import Vector

S = float(os.environ.get("VDW_SCALE", "1.3"))
GZ = float(os.environ.get("VDW_GRIP_Z", "0.27"))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)

# grip point: the handle's centre at GZ, measured on the unscaled mesh
co = np.array([mesh.matrix_world @ v.co for v in mesh.data.vertices])
sl = co[np.abs(co[:, 2] - GZ) < 0.01]
grip = (sl.min(0) + sl.max(0)) / 2; grip[2] = GZ
print("GRIP (unscaled)", grip.round(4), "handle width", (sl.max(0) - sl.min(0)).round(4)[:2])

# scale everything about the origin
for o in bpy.data.objects: o.select_set(o in (arm, mesh))
bpy.context.view_layer.objects.active = arm
arm.scale = tuple(x * S for x in arm.scale)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
for a in bpy.data.actions:          # location keys (if any) scale with the rod
    for fc in a.fcurves:
        if fc.data_path.endswith("location"):
            for k in fc.keyframe_points: k.co[1] *= S; k.handle_left[1] *= S; k.handle_right[1] *= S

# marker
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
g = Vector((grip * S).tolist())
b = eb.new("Rod.Grip"); b.head = g; b.tail = g + Vector((0, 0, 0.03)); b.use_deform = True
b.parent = eb["Rod.Handle"]
bpy.ops.object.mode_set(mode='OBJECT')
if "Rod.Grip" not in mesh.vertex_groups: mesh.vertex_groups.new(name="Rod.Grip")

co2 = np.array([mesh.matrix_world @ v.co for v in mesh.data.vertices])
print("EXTENT", co2.min(0).round(3), co2.max(0).round(3), "length", round(float(co2[:, 2].max() - co2[:, 2].min()), 3))
for n in ("Rod.Grip", "Rod.Tip", "Reel.Spool"):
    print("BONE", n, tuple(round(x, 3) for x in arm.matrix_world @ arm.data.bones[n].head_local))
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"])
print("SAVED", os.environ["VDW_SAVE_TO"])
