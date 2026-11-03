# After organize_mesh.py: opens each moved .blend and points images whose files moved at their new place, then saves it.
# Looks in the asset folder (Mesh\<asset>\, Textures first), then the archive copy of the asset; an image found only in
# the archive is copied into the asset's Textures so the .blend doesn't depend on the archive.
#   blender --factory-startup -b --python relink_moved_blends.py -- <moved_blends.json>
import bpy, os, sys, json, shutil, hashlib

MESH = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\Mesh"
ARCH = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\_Archive\Mesh"
files = json.load(open(sys.argv[sys.argv.index("--") + 1]))
bpy.context.preferences.filepaths.save_version = 0          # no .blend1 backups beside them

index = {}
# the texture-library add-ons' own images (Grungit's grunge maps, Sanctus), linked by absolute path
ADDONS = os.path.expandvars(r"%APPDATA%\Blender Foundation\Blender\5.2\scripts\addons")
addon_idx = {}
for d, _, fs in os.walk(ADDONS):
    for f in fs:
        if f.lower().endswith((".png", ".jpg", ".exr", ".hdr", ".tif")): addon_idx.setdefault(f.lower(), os.path.join(d, f))
def find(asset, name):
    if asset not in index:
        idx = {}
        for root in (os.path.join(MESH, asset), os.path.join(ARCH, asset)):
            for d, _, fs in os.walk(root):
                for f in fs: idx.setdefault(f.lower(), []).append(os.path.join(d, f))
        index[asset] = idx
    c = index[asset].get(name.lower(), [])
    # the asset folder's Textures first, then anywhere in it, then the archive
    c.sort(key=lambda p: (not p.startswith(MESH), "\\textures\\" not in p.lower()))
    return c[0] if c else None

fixed = missing = saved = 0
for i, path in enumerate(files):
    if not os.path.exists(path): continue
    try: bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    except Exception as e: print("OPEN FAILED", path, e); continue
    asset = os.path.relpath(path, MESH).split(os.sep)[0]
    changed = False
    for im in bpy.data.images:
        if im.packed_file or im.source not in ("FILE", "SEQUENCE", "TILED") or not im.filepath: continue
        cur = bpy.path.abspath(im.filepath)
        if os.path.exists(cur): continue
        hit = find(asset, os.path.basename(cur))
        if hit and hit.startswith(ARCH):
            dst = os.path.join(MESH, asset, "Textures", os.path.basename(hit))
            if os.path.exists(dst) and open(dst, "rb").read() != open(hit, "rb").read():
                dst = os.path.join(MESH, asset, "Textures", os.path.splitext(os.path.basename(path))[0], os.path.basename(hit))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not os.path.exists(dst): shutil.copy2(hit, dst)
            hit = dst; index.pop(asset, None)
        if hit:
            im.filepath = bpy.path.relpath(hit); changed = True; fixed += 1
        elif os.path.basename(cur).lower() in addon_idx:
            im.filepath = addon_idx[os.path.basename(cur).lower()]; changed = True; fixed += 1
        else:
            missing += 1; print("MISSING", os.path.basename(path), "->", os.path.basename(cur))
    if changed:
        bpy.ops.wm.save_mainfile(filepath=path, compress=False); saved += 1
    if i % 20 == 0: print(f"PROGRESS {i}/{len(files)}", flush=True)
print(f"RELINK images fixed {fixed}, still missing {missing}, blends saved {saved}")
