# A lip of ice bricks round the inside of the igloo's tunnel mouth: a frame following the tunnel's arch where it comes
# through the dome's inside wall, hugging the wall, from just inside the tunnel's own face to 0.30 m out over the dome -
# it covers the cut ends of the dome's blocks and the tunnel's (they clipped there). Its own object "lip" on the igloo's
# "ice" material (the export joins it into the "ice" mesh: Valheim's ice in game), UVs at the igloo's ice density.
# The shapes are build_shelters.py's igloo (A, B, DOOR_W, DOOR_WALL; the tunnel along +Y).
#   blender -b <igloo.blend> --factory-startup --python igloo_tunnel_lip.py      env: VDW_SAVE_TO (a new .blend)
import bpy, bmesh, math, os, random
from mathutils import Vector

A, B = 2.4, 2.75
DOOR_W, DOOR_WALL = 0.65, 1.4
GAP = 0.022
IN_OFF, OUT_OFF = -0.03, 0.30     # the lip from just inside the tunnel's face to this far out over the dome
DEPTH, BACK = 0.10, 0.06          # out from the wall into the room; back into the wall
BRICKS, SUB = 9, 4

def arch(u, off):
    wall, arc = DOOR_WALL, math.pi * DOOR_W; L = 2 * wall + arc; d = u * L
    if d < wall: return Vector((-DOOR_W - off, d))
    if d > wall + arc: return Vector((DOOR_W + off, L - d))
    a = math.pi - (d - wall) / DOOR_W
    return Vector(((DOOR_W + off) * math.cos(a), DOOR_WALL + (DOOR_W + off) * math.sin(a)))

def y_meet(x, z):
    rr = A * A * max(0.0, 1 - (min(z, B) / B) ** 2) - x * x
    return math.sqrt(max(0.0, rr))

dst = os.environ["VDW_SAVE_TO"]
if os.path.exists(dst): raise SystemExit("exists, kept: " + dst)
for o in bpy.data.objects:
    if o.mode != 'OBJECT':
        bpy.context.view_layer.objects.active = o; bpy.ops.object.mode_set(mode='OBJECT')
igloo = bpy.data.objects["bait"]
ice = next(m for m in igloo.data.materials if m and m.name.split(".")[0] == "ice")
old = bpy.data.objects.get("lip")
if old: bpy.data.objects.remove(old)

L = 2 * DOOR_WALL + math.pi * DOOR_W
du = GAP / L
rng = random.Random(5)
bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
for b in range(BRICKS):
    u0, u1 = b / BRICKS + du / 2, (b + 1) / BRICKS - du / 2
    us = [u0 + (u1 - u0) * i / SUB for i in range(SUB + 1)]
    grid = {}   # (i, edge 0 inner / 1 outer, layer 0 back / 1 front) -> vert
    for i, u in enumerate(us):
        for e, off in enumerate((IN_OFF, OUT_OFF)):
            p = arch(u, off); yw = y_meet(p.x, max(0.0, p.y))
            for l, y in enumerate((yw + BACK, yw - DEPTH)):
                grid[i, e, l] = bm.verts.new((p.x, y, max(-0.02, p.y)))
    def q(vs):
        try: return bm.faces.new(vs)
        except ValueError: return None
    made = []
    for i in range(SUB):
        made += [q([grid[i, 0, 1], grid[i + 1, 0, 1], grid[i + 1, 1, 1], grid[i, 1, 1]]),   # front, in the room
                 q([grid[i, 0, 0], grid[i, 1, 0], grid[i + 1, 1, 0], grid[i + 1, 0, 0]]),   # back, in the wall
                 q([grid[i, 0, 0], grid[i + 1, 0, 0], grid[i + 1, 0, 1], grid[i, 0, 1]]),   # inner side, facing the tunnel
                 q([grid[i, 1, 0], grid[i, 1, 1], grid[i + 1, 1, 1], grid[i + 1, 1, 0]])]   # outer side, on the dome
    for i in (0, SUB):   # the brick's ends
        made.append(q([grid[i, 0, 0], grid[i, 0, 1], grid[i, 1, 1], grid[i, 1, 0]]))
    made = [f for f in made if f]
    bmesh.ops.recalc_face_normals(bm, faces=made)
    ox, oy = rng.uniform(0.05, 0.9), rng.uniform(0.05, 0.9)
    for f in made:
        n = f.normal; ax = max(range(3), key=lambda k: abs(n[k])); o2 = [k for k in range(3) if k != ax]
        for lp in f.loops:
            lp[uvl].uv = (ox + lp.vert.co[o2[0]] * 0.0233, oy + lp.vert.co[o2[1]] * 0.0233)
me = bpy.data.meshes.new("lip"); bm.to_mesh(me); bm.free()
me.materials.append(ice)
lip = bpy.data.objects.new("lip", me); lip.matrix_world = igloo.matrix_world.copy()
(igloo.users_collection[0] if igloo.users_collection else bpy.context.scene.collection).objects.link(lip)
os.makedirs(os.path.dirname(dst), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=dst)
print("LIP", len(me.polygons), "faces, saved", dst)
