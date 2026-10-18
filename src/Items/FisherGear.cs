using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The Fisherman's gear, an armour set: a sou'wester (helmet), an oilskin coat over a striped shirt (chest - the body
    /// slot, so a cape such as Jörmungandr's Scale still goes over it) and bib overalls with rubber boots (legs).
    /// Their models (fisher_hat / fisher_chest / fisher_legs, build_fisher_gear.py) are made round the player's body in
    /// its rest pose, and each carries a copy of that body ("fitref"): it shows how the model lines up with the game's
    /// body mesh whatever the importer did, so every vertex can take its bone weights from the body under it - the gear
    /// is skinned to the player's own skeleton like Valheim's armour. A vertex colour (red) says how much a vertex moves
    /// rigidly with one bone instead: all of the hat with the head, the coat's skirt more and more with the hips.
    /// All four worn: rain can't soak you (no Wet), and a small fishing bonus.
    /// </summary>
    internal static class FisherGear
    {
        private sealed class Piece
        {
            public string Prefab = "", Clone = "", Model = "", Rigid = "", Name = "", Desc = "";
            public float Armor, Weight;
            public (string item, int amount)[] Recipe = Array.Empty<(string, int)>();
        }

        private static readonly Piece[] Pieces =
        {
            new Piece { Prefab = "VDW_FisherHat", Clone = "HelmetLeather", Model = "fisher_hat", Rigid = "Head",
                Name = "Sou'wester", Desc = "An oiled hat with a long brim at the back, so the rain runs off down your coat and not your neck.",
                Armor = 3f, Weight = 1f, Recipe = new[] { ("LeatherScraps", 4), ("Resin", 6) } },
            // the coat is a cape (shoulder slot), worn over the striped shirt, which is the tunic (chest slot)
            new Piece { Prefab = "VDW_FisherCoat", Clone = "CapeDeerHide", Model = "fisher_coat", Rigid = "Hips",
                Name = "Oilskin Coat", Desc = "A long waxed coat, worn open. It sheds rain and sea spray alike.",
                Armor = 3f, Weight = 4f, Recipe = new[] { ("DeerHide", 4), ("LeatherScraps", 4), ("Resin", 8) } },
            new Piece { Prefab = "VDW_FisherShirt", Clone = "ArmorLeatherChest", Model = "fisher_chest", Rigid = "Hips",
                Name = "Striped Fisher's Shirt", Desc = "A thick striped wool shirt. Warm when wet.",
                Armor = 2f, Weight = 2f, Recipe = new[] { ("LeatherScraps", 3), ("DeerHide", 1) } },
            new Piece { Prefab = "VDW_FisherOveralls", Clone = "ArmorLeatherLegs", Model = "fisher_legs", Rigid = "Hips",
                Name = "Oilskin Overalls", Desc = "Waxed bib overalls tucked into tall rubber boots. Wade in up to your knees and stay dry.",
                Armor = 4f, Weight = 5f, Recipe = new[] { ("DeerHide", 3), ("LeatherScraps", 6), ("Resin", 8) } },
        };

        private static StatusEffect? _setEffect;
        private static int _setHash;

        public static void Register()
        {
            var body = PrefabManager.Instance.GetPrefab("Player")?.GetComponent<VisEquipment>()?.m_bodyModel;
            if (body == null) Plugin.Log.LogWarning("Fisherman's gear: the player body wasn't found; the gear keeps the vanilla look.");

            var setDef = new BuffDefinition
            {
                Id = "set_fisherman", Name = "Fisherman's Oilskins", Kind = "Gear",
                Effects = new Dictionary<string, float> { [BuffStat.ReelStamina] = 0.15f, [BuffStat.HookWindow] = 0.1f },
            };
            _setEffect = FishingBuffs.MakeGearStatus(setDef, null);
            _setEffect.m_tooltip = "Rain can't soak you\n" + _setEffect.m_tooltip;
            _setHash = _setEffect.NameHash();

            foreach (var p in Pieces)
            {
                try { RegisterPiece(p, body); }
                catch (Exception ex) { Plugin.Log.LogError($"Fisherman's gear: '{p.Prefab}' failed: {ex}"); }
            }
        }

        private static void RegisterPiece(Piece p, SkinnedMeshRenderer? body)
        {
            var item = new CustomItem(p.Prefab, p.Clone, new ItemConfig
            {
                CraftingStation = "piece_workbench",
                MinStationLevel = 2,
                Requirements = p.Recipe.Select(r => new RequirementConfig(r.item, r.amount, r.amount / 2)).ToArray(),
            });
            if (item.ItemDrop == null) { Plugin.Log.LogWarning($"Fisherman's gear: couldn't clone '{p.Clone}'."); return; }
            var shared = item.ItemDrop.m_itemData.m_shared;
            shared.m_name = Loc.Token("vdw_" + p.Prefab.ToLowerInvariant(), p.Name);
            shared.m_description = Loc.Token("vdw_" + p.Prefab.ToLowerInvariant() + "_desc", p.Desc);
            shared.m_armor = p.Armor;
            shared.m_armorPerLevel = 1.5f;
            shared.m_weight = p.Weight;
            shared.m_movementModifier = 0f;
            shared.m_setName = "vdw_fisherman";
            shared.m_setSize = Pieces.Length;
            shared.m_setStatusEffect = _setEffect;
            if (p.Rigid == "Head") { shared.m_helmetHideHair = ItemDrop.ItemData.HelmetHairType.HiddenHat; shared.m_helmetHideBeard = ItemDrop.ItemData.HelmetHairType.Default; }

            var model = CustomModels.LoadBundleAsset<GameObject>(p.Model);
            if (model == null) Plugin.Log.LogWarning($"Fisherman's gear: no '{p.Model}' model in the bundles; '{p.Name}' keeps the vanilla look.");
            else if (body != null) Dress(item.ItemPrefab, model, body, p);

            ItemManager.Instance.AddItem(item);
            ItemIcons.ApplyHandMadeOnly(item.ItemPrefab, p.Model);
        }

        /// <summary>Puts the gear's skinned meshes in the item's "attach_skin" (what Valheim puts on the body when it's worn).</summary>
        private static void Dress(GameObject prefab, GameObject model, SkinnedMeshRenderer body, Piece p)
        {
            var parts = Build(model, body, p);
            if (parts.Count == 0) return;

            // A helmet is normally hung on the head (child "attach"); Valheim takes the first "attach" or "attach_skin"
            // child it finds, so the hat's rigid one goes and a skinned one takes its place.
            var skin = prefab.transform.Find("attach_skin");
            foreach (Transform child in prefab.transform.Cast<Transform>().ToList())
                if (child.name == "attach" || child.name == "attach_skin") UnityEngine.Object.DestroyImmediate(child.gameObject);
            // On the ground, the coat and overalls keep the vanilla leather armour's dropped model, retextured with the
            // oilskin (the main colour map swapped, vanilla's normal map kept for its folds); a model built round the body
            // looked odd lying on the ground.
            if (p.Rigid == "Head" || !Retexture(prefab, parts, p))
            {
            // The hat: our model (without its copy of the body) in place of the vanilla piece's - the helmet's ground
            // look lived in the "attach" just removed, which left a dropped hat invisible
            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
            if (ModelScale.TryGetValue(p.Model, out float toBodyScale))
            {
                var ground = new GameObject("vdw_ground");
                ground.transform.SetParent(prefab.transform, false);
                float s = toBodyScale * body.transform.lossyScale.x;          // model units -> metres, as worn
                var bounds = new Bounds(); bool first = true;
                var shapes = model.GetComponentsInChildren<MeshFilter>(true).Select(f => (tr: f.transform, mesh: f.sharedMesh, mats: f.GetComponent<MeshRenderer>()?.sharedMaterials))
                    .Concat(model.GetComponentsInChildren<SkinnedMeshRenderer>(true).Select(s => (tr: s.transform, mesh: s.sharedMesh, mats: (Material[]?)s.sharedMaterials)));
                foreach (var (tr, smesh, mats) in shapes)
                {
                    if (smesh == null || tr.name.StartsWith("fitref", StringComparison.OrdinalIgnoreCase)) continue;
                    var child = new GameObject(tr.name);
                    child.transform.SetParent(ground.transform, false);
                    var m = model.transform.worldToLocalMatrix * tr.localToWorldMatrix;
                    child.transform.localPosition = m.GetColumn(3); child.transform.localRotation = m.rotation; child.transform.localScale = m.lossyScale;
                    child.AddComponent<MeshFilter>().sharedMesh = smesh;
                    if (mats != null) child.AddComponent<MeshRenderer>().sharedMaterials = mats;
                    var b = GeometryUtility.CalculateBounds(smesh.vertices, m);
                    if (first) { bounds = b; first = false; } else bounds.Encapsulate(b);
                }
                ground.transform.localScale = Vector3.one * s;
                ground.transform.localPosition = -bounds.center * s;               // centred on the item
                // the helmet's collider lived in the "attach" removed above: without one a dropped hat fell through the
                // ground and couldn't be picked up. Any piece left with no solid collider gets a box round its model.
                if (!prefab.GetComponentsInChildren<Collider>(true).Any(c => !c.isTrigger && c.gameObject.activeSelf))
                {
                    var box = prefab.AddComponent<BoxCollider>();
                    box.center = Vector3.zero;
                    box.size = Vector3.Max(bounds.size * s, Vector3.one * 0.1f);
                }
            }
            }

            var go = new GameObject("attach_skin");
            go.SetActive(false);
            go.transform.SetParent(prefab.transform, false);
            foreach (var (mesh, mats) in parts)
            {
                var child = new GameObject(mesh.name);
                child.transform.SetParent(go.transform, false);
                var smr = child.AddComponent<SkinnedMeshRenderer>();
                smr.sharedMesh = mesh;
                smr.sharedMaterials = mats;
                smr.bones = body.bones;
                smr.rootBone = body.rootBone;
                smr.localBounds = body.localBounds;
                smr.updateWhenOffscreen = true;
                if (mesh.bindposes.Length > body.bones.Length) child.AddComponent<FisherSkirt>().HipsName = p.Rigid;
            }
        }

        /// <summary>
        /// The vanilla piece's own dropped model (what's left after the worn "attach_skin" went), with the gear's main
        /// colour map (the coat's / the overalls') on a copy of each of its materials. False if there's nothing to retexture.
        /// </summary>
        private static bool Retexture(GameObject prefab, List<(Mesh mesh, Material[] mats)> parts, Piece p)
        {
            string want = p.Model == "fisher_coat" ? "coat" : p.Model == "fisher_chest" ? "shirt" : "overall";
            var all = parts.SelectMany(x => x.mats).Where(m => m != null).ToList();
            var src = all.FirstOrDefault(m => m.name.IndexOf(want, StringComparison.OrdinalIgnoreCase) >= 0) ?? all.FirstOrDefault();
            var tex = src != null && src.HasProperty("_MainTex") ? src.GetTexture("_MainTex") : null;
            var rends = prefab.GetComponentsInChildren<Renderer>(true).Where(r => r is MeshRenderer || r is SkinnedMeshRenderer).ToList();
            if (tex == null || rends.Count == 0) return false;
            foreach (var r in rends)
            {
                r.enabled = true;
                r.sharedMaterials = r.sharedMaterials.Select(m =>
                {
                    if (m == null) return m;
                    var c = new Material(m) { name = m.name + "_vdw_" + want };
                    if (c.HasProperty("_MainTex")) c.SetTexture("_MainTex", tex);
                    if (c.HasProperty("_Color")) c.SetColor("_Color", Color.white);
                    return c;
                }).ToArray();
            }
            return true;
        }

        private static readonly Dictionary<string, List<(Mesh, Material[])>> Built = new();
        private static readonly Dictionary<string, float> ModelScale = new();   // model units -> body mesh units
        internal const int SkirtBones = 8;

        /// <summary>
        /// The weights painted in the file, re-pointed from the file's bones to the wearer's (by name; vdw_skirt0..7 to the
        /// skirt bones after the body's). Null if the mesh has none, or a bone of the file isn't on the body.
        /// </summary>
        private static BoneWeight[]? PaintedWeights(Mesh src, Transform[] fileBones, Transform[] bodyBones, out int skirtUsed)
        {
            skirtUsed = 0;
            var bw = src.boneWeights;
            if (bw == null || bw.Length != src.vertexCount || fileBones.Length == 0) return null;
            var map = new int[fileBones.Length];
            for (int i = 0; i < fileBones.Length; i++)
            {
                string n = fileBones[i] != null ? fileBones[i].name : "";
                if (n.StartsWith("vdw_skirt") && int.TryParse(n.Substring(9), out int k) && k >= 0 && k < SkirtBones) { map[i] = bodyBones.Length + k; continue; }
                map[i] = Array.FindIndex(bodyBones, b => b != null && b.name == n);
                if (map[i] < 0) { Plugin.Log.LogWarning($"Fisherman's gear: '{src.name}' is painted to '{n}', which the player has no bone for; weighting it here instead."); return null; }
            }
            var outW = new BoneWeight[bw.Length];
            for (int i = 0; i < bw.Length; i++)
            {
                var w = bw[i];
                outW[i] = new BoneWeight
                {
                    boneIndex0 = map[w.boneIndex0], weight0 = w.weight0, boneIndex1 = map[w.boneIndex1], weight1 = w.weight1,
                    boneIndex2 = map[w.boneIndex2], weight2 = w.weight2, boneIndex3 = map[w.boneIndex3], weight3 = w.weight3,
                };
                foreach (var b in new[] { outW[i].boneIndex0, outW[i].boneIndex1, outW[i].boneIndex2, outW[i].boneIndex3 })
                    if (b >= bodyBones.Length) skirtUsed = SkirtBones;
            }
            return outW;
        }
        internal static Vector2 SkirtHips;

        /// <summary>
        /// A gear vertex's bone weights: a distance-weighted blend of the body points within reach of it (the nearest
        /// counting most, falling off over a few centimetres). Only body points on the vertex's own side of the body's
        /// middle count (or on the middle itself), so cloth between the legs never follows the other leg.
        /// </summary>
        private static BoneWeight BodyWeights(Vector3 v, Vector3[] pts, BoneWeight[] wts, float cm, float sigmaCm)
        {
            float mid = 2f * cm;                       // the middle strip: either side may be used
            bool any = Mathf.Abs(v.x) < mid;
            const int K = 10;
            var best = new (float d, int i)[K];
            for (int k = 0; k < K; k++) best[k] = (float.MaxValue, -1);
            for (int i = 0; i < pts.Length; i++)
            {
                var q = pts[i];
                if (!any && Mathf.Abs(q.x) > mid && Mathf.Sign(q.x) != Mathf.Sign(v.x)) continue;
                float d = (q - v).sqrMagnitude;
                if (d >= best[K - 1].d) continue;
                int j = K - 1;
                while (j > 0 && best[j - 1].d > d) { best[j] = best[j - 1]; j--; }
                best[j] = (d, i);
            }
            if (best[0].i < 0) return new BoneWeight { boneIndex0 = 0, weight0 = 1f };
            float d0 = Mathf.Sqrt(best[0].d), sigma = sigmaCm * cm;
            var sum = new Dictionary<int, float>();
            foreach (var (d2, i) in best)
            {
                if (i < 0) continue;
                float f = Mathf.Exp(-Mathf.Pow((Mathf.Sqrt(d2) - d0) / sigma, 2f));
                var w = wts[i];
                void Add(int b, float x) { if (x > 0f) sum[b] = (sum.TryGetValue(b, out var y) ? y : 0f) + x * f; }
                Add(w.boneIndex0, w.weight0); Add(w.boneIndex1, w.weight1); Add(w.boneIndex2, w.weight2); Add(w.boneIndex3, w.weight3);
            }
            return WornSkinning.Top4(sum);
        }

        private static List<(Mesh, Material[])> Build(GameObject model, SkinnedMeshRenderer body, Piece p)
        {
            if (Built.TryGetValue(p.Model, out var done)) return done;
            var parts = new List<(Mesh, Material[])>();
            Built[p.Model] = parts;
            var bodyMesh = body.sharedMesh;
            if (bodyMesh == null || !bodyMesh.isReadable) { Plugin.Log.LogWarning("Fisherman's gear: the body mesh can't be read."); return parts; }
            var bodyV = bodyMesh.vertices;
            var bodyW = bodyMesh.boneWeights;

            var filters = model.GetComponentsInChildren<MeshFilter>(true);
            var fit = filters.FirstOrDefault(m => m.name.StartsWith("fitref", StringComparison.OrdinalIgnoreCase));
            if (fit == null || fit.sharedMesh == null || !fit.sharedMesh.isReadable) { Plugin.Log.LogWarning($"Fisherman's gear: '{p.Model}' has no fitref."); return parts; }
            Matrix4x4 ToRoot(Transform t) => model.transform.worldToLocalMatrix * t.localToWorldMatrix;
            var toBody = FitToBody(fit.sharedMesh.vertices.Select(v => ToRoot(fit.transform).MultiplyPoint3x4(v)).ToArray(), bodyV, out float err, out bool mirrored);
            // The body is left-right symmetric, so the fit above can't tell its sides apart: a model with its own skeleton
            // settles it - its LeftArm bone must land on the body's LeftArm, else the fit is mirrored across the body's middle
            var fileBones = model.GetComponentsInChildren<SkinnedMeshRenderer>(true).SelectMany(s => s.bones).Where(b => b != null).ToList();
            var fl = fileBones.FirstOrDefault(b => b.name == "LeftArm"); var fr = fileBones.FirstOrDefault(b => b.name == "RightArm");
            int bl = Array.FindIndex(body.bones, b => b != null && b.name == "LeftArm"), br = Array.FindIndex(body.bones, b => b != null && b.name == "RightArm");
            if (fl != null && fr != null && bl >= 0 && br >= 0)
            {
                Vector3 bodyL = bodyMesh.bindposes[bl].inverse.MultiplyPoint3x4(Vector3.zero), bodyR = bodyMesh.bindposes[br].inverse.MultiplyPoint3x4(Vector3.zero);
                Vector3 gearL = toBody.MultiplyPoint3x4(ToRoot(fl).MultiplyPoint3x4(Vector3.zero));
                if ((gearL - bodyR).sqrMagnitude < (gearL - bodyL).sqrMagnitude)
                {
                    // mirror across the plane halfway between the shoulders, square to the line between them
                    Vector3 c = (bodyL + bodyR) * 0.5f, ax = (bodyL - bodyR).normalized;
                    var reflect = Matrix4x4.identity;
                    for (int r = 0; r < 3; r++) for (int k = 0; k < 3; k++) reflect[r, k] = (r == k ? 1f : 0f) - 2f * ax[r] * ax[k];
                    toBody = Matrix4x4.Translate(c) * reflect * Matrix4x4.Translate(-c) * toBody;
                    mirrored = !mirrored;
                    Plugin.Log.LogDebug($"Fisherman's gear: '{p.Model}' was fitted to the body's other side - flipped so its left is the body's left.");
                }
            }
            int rigid = Array.FindIndex(body.bones, b => b != null && b.name == p.Rigid);
            if (rigid < 0) Plugin.Log.LogWarning($"Fisherman's gear: no '{p.Rigid}' bone in the body (bones: {string.Join(", ", body.bones.Where(b => b != null).Select(b => b.name))}).");
            var pts = bodyV;
            var wts = bodyW;
            // one centimetre in the body mesh's space (its height is the player's height)
            float bodyH = bodyV.Max(v => v.y) - bodyV.Min(v => v.y), bodyD = bodyV.Max(v => v.z) - bodyV.Min(v => v.z);
            float scale = Mathf.Max(bodyH, bodyD) / 200f;
            ModelScale[p.Model] = toBody.lossyScale.x;

            // the gear's parts: plain meshes (weighted here), or skinned meshes carrying weights painted in Blender on Valheim's
            // skeleton (build_gear_rig.py) - those are used as painted
            var sources = filters.Where(f => f != fit).Select(f => (tr: f.transform, mesh: f.sharedMesh, mats: f.GetComponent<MeshRenderer>()?.sharedMaterials, bones: (Transform[]?)null))
                .Concat(model.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(s => !s.name.StartsWith("fitref", StringComparison.OrdinalIgnoreCase))
                        .Select(s => (tr: s.transform, mesh: s.sharedMesh, mats: (Material[]?)s.sharedMaterials, bones: (Transform[]?)s.bones)))
                .ToList();
            foreach (var srcPart in sources)
            {
                if (srcPart.mesh == null || !srcPart.mesh.isReadable) continue;
                var src = srcPart.mesh;
                var m = toBody * ToRoot(srcPart.tr);
                var n = m.inverse.transpose;
                var verts = src.vertices.Select(v => m.MultiplyPoint3x4(v)).ToArray();
                var mesh = new Mesh { name = src.name.Replace("_model", "") + "_worn" };
                if (verts.Length > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                mesh.vertices = verts;
                var normals = src.normals;
                if (normals.Length == verts.Length) mesh.normals = normals.Select(v => n.MultiplyVector(v).normalized).ToArray();
                var tangents = src.tangents;
                if (tangents.Length == verts.Length)
                    mesh.tangents = tangents.Select(t => { Vector3 d = m.MultiplyVector(t).normalized; return new Vector4(d.x, d.y, d.z, mirrored ? -t.w : t.w); }).ToArray();
                var uv = new List<Vector2>(); src.GetUVs(0, uv); if (uv.Count == verts.Length) mesh.SetUVs(0, uv);
                mesh.subMeshCount = src.subMeshCount;
                for (int s = 0; s < src.subMeshCount; s++)
                {
                    var tris = src.GetTriangles(s);
                    if (mirrored) for (int i = 0; i + 2 < tris.Length; i += 3) (tris[i + 1], tris[i + 2]) = (tris[i + 2], tris[i + 1]);
                    mesh.SetTriangles(tris, s);
                }

                int skirtUsed = 0;
                var painted = srcPart.bones != null ? PaintedWeights(src, srcPart.bones, body.bones, out skirtUsed) : null;
                if (painted != null)
                {
                    mesh.boneWeights = painted;
                    var bp = bodyMesh.bindposes;
                    if (skirtUsed > 0 && rigid >= 0)
                    {
                        bp = bp.Concat(Enumerable.Repeat(bp[rigid], SkirtBones)).ToArray();     // the skirt bones start where the hips are
                        var hp = bodyMesh.bindposes[rigid].inverse.MultiplyPoint3x4(Vector3.zero); SkirtHips = new Vector2(hp.x, hp.y);
                    }
                    mesh.bindposes = bp;
                    mesh.RecalculateBounds();
                    parts.Add((mesh, srcPart.mats ?? new Material[0]));
                    Plugin.Log.LogDebug($"Fisherman's gear: '{src.name}' uses its painted weights ({srcPart.bones!.Length} bones in the file{(skirtUsed > 0 ? ", with the skirt bones" : "")}).");
                    continue;
                }
                // weights from the body near each vertex - averaged over space, not over this mesh's own edges, so the coat and
                // the shirt (or overalls) under it get the same weights where they overlap and move together; then a light
                // smoothing over the surface, then eased toward the rigid bone
                // how sharp: the boots follow their bones crisply (toe with the foot, top with the shin), the overalls nearly
                // so; the loose coat and the shirt under it share a softer blend
                string part = src.name.ToLowerInvariant();
                float sigma = part.Contains("boots") ? 1f : part.Contains("overalls") ? 2f : 4f;
                int passes = part.Contains("boots") ? 0 : part.Contains("overalls") ? 1 : 2;
                var raw = verts.Select(v => BodyWeights(v, pts, wts, scale, sigma)).ToArray();
                Vector3 hipsAt = rigid >= 0 ? bodyMesh.bindposes[rigid].inverse.MultiplyPoint3x4(Vector3.zero) : Vector3.zero;
                // cloth that spans both legs (the coat's skirt, the overalls' crotch) follows both thighs, more evenly the
                // nearer the middle it is: it moves with the legs without one side tearing away from the other
                bool skirt = part.Contains("coat"), crotch = part.Contains("overalls");
                if ((skirt || crotch) && rigid >= 0)
                    for (int i = 0; i < raw.Length; i++)
                    {
                        var v = verts[i];
                        if (v.z > hipsAt.z) continue;
                        if (crotch && v.z < hipsAt.z - 35f * scale) continue;
                        float reach = (skirt ? 15f : 6f) * scale;
                        float mix = 0.5f * (1f - Mathf.Clamp01(Mathf.Abs(v.x) / reach));
                        if (mix <= 0.01f) continue;
                        var other = BodyWeights(new Vector3(-v.x, v.y, v.z), pts, wts, scale, sigma);
                        var d = new Dictionary<int, float>();
                        void Add(int b, float w) { if (w > 0f) d[b] = (d.TryGetValue(b, out var x) ? x : 0f) + w; }
                        Add(raw[i].boneIndex0, raw[i].weight0 * (1f - mix)); Add(raw[i].boneIndex1, raw[i].weight1 * (1f - mix));
                        Add(raw[i].boneIndex2, raw[i].weight2 * (1f - mix)); Add(raw[i].boneIndex3, raw[i].weight3 * (1f - mix));
                        Add(other.boneIndex0, other.weight0 * mix); Add(other.boneIndex1, other.weight1 * mix);
                        Add(other.boneIndex2, other.weight2 * mix); Add(other.boneIndex3, other.weight3 * mix);
                        raw[i] = WornSkinning.Top4(d);
                    }
                // the boots: every point on one bone only (the shaft rigid with the shin, the foot with the foot)
                if (part.Contains("boots"))
                    for (int i = 0; i < raw.Length; i++) raw[i] = new BoneWeight { boneIndex0 = raw[i].boneIndex0, weight0 = 1f };
                var soft = passes > 0 ? WornSkinning.Soften(raw, verts, src.triangles, body.bones.Length, -1, 1f, passes) : raw;
                var colors = src.colors;
                if (colors.Length == verts.Length && rigid >= 0)
                    for (int i = 0; i < soft.Length; i++)
                    {
                        float r = Mathf.Clamp01(colors[i].r);
                        if (r <= 0.001f) continue;
                        var d = new Dictionary<int, float>();
                        void Add(int b, float w) { if (w > 0f) d[b] = (d.TryGetValue(b, out var x) ? x : 0f) + w * (1f - r); }
                        Add(soft[i].boneIndex0, soft[i].weight0); Add(soft[i].boneIndex1, soft[i].weight1);
                        Add(soft[i].boneIndex2, soft[i].weight2); Add(soft[i].boneIndex3, soft[i].weight3);
                        d[rigid] = (d.TryGetValue(rigid, out var y) ? y : 0f) + r;
                        soft[i] = WornSkinning.Top4(d);
                    }
                var bind = bodyMesh.bindposes;
                // the coat's skirt: below the hips it's handed over, more and more toward the hem, to SkirtBones extra bones
                // round the hips (FisherSkirt swings them: it trails behind as you move and blows in the wind)
                if (part.Contains("coat") && rigid >= 0)
                {
                    Vector3 hips = bind[rigid].inverse.MultiplyPoint3x4(Vector3.zero);
                    float hem = verts.Min(v => v.z);
                    for (int i = 0; i < soft.Length; i++)
                    {
                        var v = verts[i];
                        float s = 0.35f * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(hips.z - 6f * scale, hem, v.z));   // a share: the legs keep the rest
                        if (s <= 0.001f) continue;
                        float a = Mathf.Repeat(Mathf.Atan2(v.y - hips.y, v.x - hips.x) / (2f * Mathf.PI), 1f) * SkirtBones;
                        int b0 = Mathf.FloorToInt(a) % SkirtBones, b1 = (b0 + 1) % SkirtBones; float f1 = a - Mathf.Floor(a);
                        var d = new Dictionary<int, float>();
                        void Add(int b, float w) { if (w > 0f) d[b] = (d.TryGetValue(b, out var x) ? x : 0f) + w; }
                        Add(soft[i].boneIndex0, soft[i].weight0 * (1f - s)); Add(soft[i].boneIndex1, soft[i].weight1 * (1f - s));
                        Add(soft[i].boneIndex2, soft[i].weight2 * (1f - s)); Add(soft[i].boneIndex3, soft[i].weight3 * (1f - s));
                        Add(body.bones.Length + b0, s * (1f - f1)); Add(body.bones.Length + b1, s * f1);
                        soft[i] = WornSkinning.Top4(d);
                    }
                    bind = bind.Concat(Enumerable.Repeat(bind[rigid], SkirtBones)).ToArray();   // they start where the hips are
                    SkirtHips = new Vector2(hips.x, hips.y);
                }
                mesh.boneWeights = soft;
                mesh.bindposes = bind;
                mesh.RecalculateBounds();
                parts.Add((mesh, srcPart.mats ?? new Material[0]));
            }
            Plugin.Log.LogDebug($"Fisherman's gear: '{p.Model}' fitted to the body (mean error {err * 1e4f:0.00} cm{(mirrored ? ", mirrored" : "")}), " +
                               $"{parts.Count} part(s), {parts.Sum(x => x.Item1.vertexCount)} vertices skinned.");
            return parts;
        }

        /// <summary>
        /// The axis turn (any of the 48), scale and offset that lay the model's copy of the body onto the game's body mesh:
        /// matched by their bounding boxes, the right turn being the one whose points land nearest the body's.
        /// </summary>
        private static Matrix4x4 FitToBody(Vector3[] fit, Vector3[] body, out float error, out bool mirrored)
        {
            Bounds Box(IEnumerable<Vector3> pts) { var a = pts.ToArray(); var b = new Bounds(a[0], Vector3.zero); foreach (var v in a) b.Encapsulate(v); return b; }
            var bb = Box(body);
            var sample = Enumerable.Range(0, 80).Select(i => i * fit.Length / 80).ToArray();
            int[][] perms = { new[] { 0, 1, 2 }, new[] { 0, 2, 1 }, new[] { 1, 0, 2 }, new[] { 1, 2, 0 }, new[] { 2, 0, 1 }, new[] { 2, 1, 0 } };
            float best = float.MaxValue; Matrix4x4 bestM = Matrix4x4.identity; bool bestMirror = false;
            foreach (var perm in perms)
                for (int signs = 0; signs < 8; signs++)
                {
                    var rot = Matrix4x4.zero; rot[3, 3] = 1f;
                    for (int r = 0; r < 3; r++) rot[r, perm[r]] = ((signs >> r) & 1) == 0 ? 1f : -1f;
                    var turned = fit.Select(v => rot.MultiplyVector(v)).ToArray();
                    var fb = Box(turned);
                    float s = Mathf.Max(bb.size.x, bb.size.y, bb.size.z) / Mathf.Max(1e-9f, Mathf.Max(fb.size.x, fb.size.y, fb.size.z));
                    Vector3 off = bb.center - fb.center * s;
                    float e = 0f;
                    foreach (int i in sample)
                    {
                        Vector3 q = turned[i] * s + off; float dmin = float.MaxValue;
                        foreach (var b in body) { float d = (b - q).sqrMagnitude; if (d < dmin) dmin = d; }
                        e += Mathf.Sqrt(dmin);
                    }
                    e /= sample.Length;
                    if (e < best)
                    {
                        best = e; bestMirror = rot.determinant < 0f;
                        bestM = Matrix4x4.TRS(off, Quaternion.identity, Vector3.one * s) * rot;
                    }
                }
            error = best; mirrored = bestMirror;
            return bestM;
        }

        /// <summary>Wearing all three: the rain doesn't make you Wet.</summary>
        [HarmonyPatch(typeof(SEMan), nameof(SEMan.AddStatusEffect), new[] { typeof(int), typeof(bool), typeof(int), typeof(float), typeof(short) })]
        private static class KeepDry
        {
            private static readonly AccessTools.FieldRef<SEMan, Character> Owner = AccessTools.FieldRefAccess<SEMan, Character>("m_character");
            private static bool Prefix(SEMan __instance, int nameHash, ref StatusEffect? __result)
            {
                if (nameHash != SEMan.s_statusEffectWet || _setHash == 0) return true;
                if (!(Owner(__instance) is Player) || !__instance.HaveStatusEffect(_setHash)) return true;
                __result = null;
                return false;
            }
        }
    }
}
