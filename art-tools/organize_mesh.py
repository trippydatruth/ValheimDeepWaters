# Tidies Desktop\Valheim_DeepWaters\Mesh into one folder per asset with Blender Files / Models / Textures / Previews.
#   - In each asset folder, the version folders (v3, bake_v20, final_v2, Painted_coat_v11, ...) are emptied of their
#     CURRENT files into those four folders: every file the game uses (matched by content against the Unity project and the
#     installed mod), the newest copy of each working .blend, and the previews of each series' latest version. Then the
#     version folders themselves (with the old copies and intermediates left in them) move to _Archive\Mesh\<asset>\.
#   - Loose files in an asset folder go into the four folders by type; .blend1 backups go to the archive.
#   - Every asset folder gets the four folders. Nothing is deleted: every move is logged (moves.csv) with an undo script.
#   python organize_mesh.py [--go]        (without --go: a dry run that only writes the plan)
import os, re, sys, csv, json, shutil, hashlib, time

MESH = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\Mesh"
ARCH = r"C:\Users\tripp\Desktop\Valheim_DeepWaters\_Archive\Mesh"
USED_DIRS = [r"C:\Users\tripp\Desktop\Valheim_DeepWaters\ValheimDeepWatersUnity\Assets\DeepWaters",
             os.path.expandvars(r"%APPDATA%\Thunderstore Mod Manager\DataFolder\Valheim\profiles\Test\BepInEx\plugins\Trippy-Valheim_Deep_Waters\Models")]
GO = "--go" in sys.argv
OUT = os.path.join(os.path.dirname(ARCH), "_organize_log")
SKIP_TOPS = {"tools", "sourced", "assets"}                      # the old tools copy, the per-fish download folders, Mesh\Assets
STD = ["Blender Files", "Models", "Textures", "Previews"]
ALIAS = {"texture": "Textures", "textures": "Textures", "tex": "Textures", "preview": "Previews", "model": "Models", "blender files": "Blender Files"}
# version-named folders that are data, not versions (the in-game pose recordings)
DATA = {("fishermen gear", "game_poses_v1"), ("fishermen gear", "real_poses_v1")}
VER = re.compile(r"(^|[_ -])v\d+([_ -]|$)|(^|[_ -])(bake|final|build|export|edit|test|fix)([_ -]|$)|^v\d+$", re.I)
SER = re.compile(r"^(.*?)v(\d+)(.*)$", re.I)
MODEL_EXT = (".fbx", ".glb", ".gltf", ".obj", ".dae", ".stl", ".abc")
IMG_EXT = (".png", ".jpg", ".jpeg", ".tga", ".exr", ".tif", ".tiff", ".bmp", ".webp", ".hdr")
TEX_HINT = re.compile(r"_unity_|albedo|basecolor|base_color|normal|roughness|metallic|emission|occlusion|_orm|height|_ao[._]|diffuse|_col[._]|_nrm|_rough|specular|opacity|mask|paint", re.I)
PREV_HINT = re.compile(r"preview|compare|grid|tile|sheet|turn|render|_uv_layout|contact|montage|check|pose|icon", re.I)

cache = {}
def md5(p):
    if p not in cache:
        h = hashlib.md5()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
        cache[p] = h.hexdigest()
    return cache[p]

sizes, used = set(), set()
for U in USED_DIRS:
    for d, _, fs in os.walk(U):
        for f in fs:
            if f.lower().endswith(MODEL_EXT + IMG_EXT + (".ogg", ".wav")):
                p = os.path.join(d, f); sizes.add(os.path.getsize(p)); used.add(md5(p))
def is_used(p): return os.path.getsize(p) in sizes and md5(p) in used

def kind(p):
    n = os.path.basename(p).lower(); parts = [x.lower() for x in p.split(os.sep)]
    if n.endswith(".blend"): return "Blender Files"
    if n.endswith(MODEL_EXT): return "Models"
    if n.endswith(IMG_EXT):
        if "textures" in parts or "texture" in parts or "tex" in parts or TEX_HINT.search(n) and not PREV_HINT.search(n): return "Textures"
        return "Previews"
    if n.endswith(".json") and "blender files" in parts: return "Blender Files"   # a .blend's helper data stays beside it
    return None                                                    # other files: kept at the asset folder's top
def norm_blend(n): return re.sub(r"[_ -]?v\d+", "", n.lower())

plan, archive_dirs = [], []                                        # (src, dst, why), dirs to archive whole
for top in sorted(os.listdir(MESH)):
    tp = os.path.join(MESH, top)
    if not os.path.isdir(tp) or top.lower() in SKIP_TOPS: continue
    subs = [s for s in os.listdir(tp) if os.path.isdir(os.path.join(tp, s))]
    vers = [s for s in subs if VER.search(s) and (top.lower(), s.lower()) not in DATA]
    # the newest member of each series, for its previews and other files
    series = {}
    for s in vers:
        m = SER.match(s); key = (m.group(1).lower() + "#" + m.group(3).lower()) if m else s.lower()
        n = int(m.group(2)) if m else 0
        if key not in series or n > series[key][0]: series[key] = (n, s)
    latest = {v[1] for v in series.values()}
    taken = {}                                                     # dst path -> (src, mtime, used)
    blends = {}                                                    # normalized blend name -> (mtime, src)
    def offer(src, why):
        k = kind(src); n = os.path.basename(src)
        dst = os.path.join(tp, k, n) if k else os.path.join(tp, n)
        u = is_used(src) if k in ("Models", "Textures") else False
        t = os.path.getmtime(src)
        if dst in taken:
            o = taken[dst]
            if md5(o[0]) == md5(src): return                       # the same file twice: one copy is enough
            # the used one wins, then the newer one; a different file of the same name keeps both
            if (u, t) > (o[2], o[1]): taken[dst] = (src, t, u, why); return
            if u and o[2]:
                base, ext = os.path.splitext(n); dst = os.path.join(os.path.dirname(dst), f"{base}__{os.path.basename(os.path.dirname(src))}{ext}")
            else: return
        taken[dst] = (src, t, u, why)
    for s in vers:
        for d, _, fs in os.walk(os.path.join(tp, s)):
            for f in fs:
                p = os.path.join(d, f); fl = f.lower()
                if fl.endswith(".blend1"): continue
                if fl.endswith(".blend"):
                    k = norm_blend(f); t = os.path.getmtime(p)
                    if k not in blends or t > blends[k][0]: blends[k] = (t, p)
                elif fl.endswith(MODEL_EXT + IMG_EXT) and is_used(p): offer(p, "used by the game")
                elif s in latest and (kind(p) == "Previews" or kind(p) is None and not fl.endswith((".fbm",))): offer(p, "latest " + s)
    for t, p in blends.values(): offer(p, "newest working .blend")
    # files already in the asset folder's own non-version folders win over version copies of the same name
    for dst in list(taken):
        if os.path.exists(dst):
            src = taken[dst][0]
            if md5(dst) == md5(src) or not taken[dst][2]: del taken[dst]
    for dst, (src, t, u, why) in taken.items(): plan.append((src, dst, why))
    archive_dirs += [os.path.join(tp, s) for s in vers]
    # loose files at the asset folder's top, into the four folders; .blend1 backups anywhere outside versions, archived
    for f in os.listdir(tp):
        p = os.path.join(tp, f)
        if os.path.isfile(p) and kind(p) and not f.lower().startswith("readme"): plan.append((p, os.path.join(tp, kind(p), f), "loose file"))
    for d, ds, fs in os.walk(tp):
        if any(d.startswith(os.path.join(tp, s)) for s in vers): continue
        for f in fs:
            if f.lower().endswith(".blend1"): plan.append((os.path.join(d, f), os.path.join(ARCH, os.path.relpath(os.path.join(d, f), MESH)), "blender backup"))
    # alias folders (Texture, Preview, tex, Model) merge into the standard ones
    for s in subs:
        a = ALIAS.get(s.lower())
        if a and s != a:
            for d, _, fs in os.walk(os.path.join(tp, s)):
                for f in fs:
                    src = os.path.join(d, f); dst = os.path.join(tp, a, os.path.relpath(src, os.path.join(tp, s)))
                    if s.lower() == a.lower(): continue                # only a case difference (Windows): the same folder
                    plan.append((src, dst if not os.path.exists(dst) else dst + "__" + s, "merge " + s))

os.makedirs(OUT, exist_ok=True)
json.dump(dict(moves=plan, archive=archive_dirs), open(os.path.join(OUT, "plan.json"), "w"), indent=1)
mb = sum(os.path.getsize(s) for s, _, _ in plan) / 2**20
amb = sum(os.path.getsize(os.path.join(d, f)) for a in archive_dirs for d, _, fs in os.walk(a) for f in fs) / 2**20
print(f"PLAN {len(plan)} files into the asset folders ({mb:.0f} MB), {len(archive_dirs)} version folders to archive ({amb:.0f} MB incl. what moves out)")
if not GO: sys.exit()

log = open(os.path.join(OUT, "moves.csv"), "a", newline="", encoding="utf-8"); w = csv.writer(log)
moved_blends = []
for src, dst, why in plan:
    if not os.path.exists(src) or os.path.exists(dst): print("SKIP", src); continue
    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.move(src, dst); w.writerow([src, dst, why])
    if dst.lower().endswith(".blend") and not dst.startswith(ARCH): moved_blends.append(dst)
for a in archive_dirs:
    dst = os.path.join(ARCH, os.path.relpath(a, MESH))
    if os.path.exists(dst): dst += "__" + time.strftime("%H%M%S")
    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.move(a, dst); w.writerow([a, dst, "archived version folder"])
for top in os.listdir(MESH):
    tp = os.path.join(MESH, top)
    if os.path.isdir(tp) and top.lower() not in SKIP_TOPS:
        for s in STD: os.makedirs(os.path.join(tp, s), exist_ok=True)
        for s in os.listdir(tp):                                    # alias folders left empty by the merge
            sp = os.path.join(tp, s)
            if os.path.isdir(sp) and ALIAS.get(s.lower()) and s not in STD and not any(os.scandir(sp)): os.rmdir(sp)
log.close()
json.dump(moved_blends, open(os.path.join(OUT, "moved_blends.json"), "w"), indent=1)
print("DONE", len(moved_blends), "blend files moved")
