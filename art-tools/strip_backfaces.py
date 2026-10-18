# Takes out the reversed back-face copies add_backfaces.py made (a face whose corners are exactly the corners of another
# face, in reverse), so the mesh can be unwrapped again; add_backfaces adds them back at the end. Keeps seams, weights
# and everything else. Also leaves Edit Mode first.     blender -b fish.blend --python strip_backfaces.py   env: VDW_SAVE_TO
import bpy, bmesh, os
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o; bpy.ops.object.mode_set(mode='OBJECT')
mesh = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
bm = bmesh.new(); bm.from_mesh(mesh.data)
def key(f): return tuple(sorted(tuple(round(c, 6) for c in v.co) for v in f.verts))
seen = {}; dup = []
for f in bm.faces:            # copies come after their originals
    k = key(f)
    if k in seen and f.normal.dot(seen[k].normal) < -0.5: dup.append(f)
    else: seen.setdefault(k, f)
bmesh.ops.delete(bm, geom=dup, context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
n = len(bm.faces); bm.to_mesh(mesh.data); bm.free(); mesh.data.update()
print(f"  removed {len(dup)} back-face copies; {n} faces, {sum(e.use_seam for e in mesh.data.edges)} seam edges")
bpy.ops.wm.save_as_mainfile(filepath=os.environ["VDW_SAVE_TO"]); print("  saved", os.environ["VDW_SAVE_TO"])
