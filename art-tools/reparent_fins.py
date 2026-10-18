# Parents every fin bone (dorsal, pectoral, pelvic - the first of each chain) to the body bone it sits over: the Head or
# the Spine bone whose span along the fish (y) holds the fin's root. A fin hung from a bone in another part of the body
# swings wildly as that bone bends (a dorsal fin under the tail bone), or stays behind as the body bends past it (pelvic
# fins under Root). Weights and bone positions are kept.   blender -b fish.blend --python reparent_fins.py
#   env: VDW_SAVE_TO (default: in place), VDW_DRY=1 (only report)
import bpy, os
for _o in list(bpy.data.objects):
    if _o.mode != 'OBJECT' and _o.name in bpy.context.view_layer.objects:
        bpy.context.view_layer.objects.active = _o
        try: bpy.ops.object.mode_set(mode='OBJECT')
        except RuntimeError: pass
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
B = arm.data.bones
body = [b for b in B if b.name == "Head" or (b.name.startswith("Spine") and b.name[5:].isdigit() or b.name == "Spine")]
def span(b): return min(b.head_local.y, b.tail_local.y), max(b.head_local.y, b.tail_local.y)
def host(y):
    inside = [b for b in body if span(b)[0] <= y <= span(b)[1]]
    if inside: return min(inside, key=lambda b: span(b)[1] - span(b)[0]).name
    return min(body, key=lambda b: min(abs(y - span(b)[0]), abs(y - span(b)[1]))).name
fins = [b for b in B if ("Fin" in b.name and "Tail" not in b.name) and not (b.parent and "Fin" in b.parent.name and "Tail" not in b.parent.name)]
moves = {}
for b in fins:
    h = host(b.head_local.y)
    if b.parent is None or b.parent.name != h: moves[b.name] = h
    print(f"  {b.name:22s} at y {b.head_local.y:+.3f}: {b.parent.name if b.parent else '-'} -> {h}{'' if b.name in moves else ' (kept)'}")
if moves and os.environ.get("VDW_DRY") != "1":
    for o in bpy.data.objects: o.select_set(o == arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT'); eb = arm.data.edit_bones
    for n, h in moves.items(): eb[n].use_connect = False; eb[n].parent = eb[h]
    bpy.ops.object.mode_set(mode='OBJECT')
if os.environ.get("VDW_DRY") != "1":
    bpy.ops.wm.save_as_mainfile(filepath=os.environ.get("VDW_SAVE_TO") or bpy.data.filepath); print(f"  {len(moves)} fin bones re-parented, saved")
