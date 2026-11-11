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
    /// Shelters to fish the ice from (roadmap: Ice Fishing - Ice Shelter), three of them:
    ///   the Hide Lavvu - the far north's pole tent of sewn hides, open at the top for its smoke (the Mountain);
    ///   the Ice Shelter - an igloo of the game's own ice blocks, a vent at its top for a fire you build yourself;
    ///   the Ship-Tent - a Viking ship's tent, crossed gable boards crowned with the game's carved dragon heads, a smoke hood over a gap in
    ///     its ridge and the tops of its gables left open (the Deep North, the best of them).
    /// Each is walked into (its colliders are its shape, the door and the vent open), the tents come with Valheim's own campfire
    /// in the middle under the vent (placed with it, taken away with it), counts as shelter for resting, and fish bite
    /// sooner through a hole drilled inside it (BiteBonus: they don't see you against the sky).
    /// Valheim's smoke is physical - it rises and gathers under a roof and chokes the fire if it can't get out - so every
    /// shelter's roof rises to a real opening over the fire.
    /// </summary>
    internal static class IceShelters
    {
        public sealed class Kind
        {
            public string Prefab = "", Model = "", Key = "", Name = "", Desc = "";
            public RequirementConfig[] Reqs = Array.Empty<RequirementConfig>();
            public float Bite;                 // the bite bonus through a hole inside it
            public int Comfort;
            public Vector3 FireAt = Vector3.zero;   // where its campfire goes, in its own space
            public bool Fire = true;           // comes with a campfire (the igloo doesn't: build your own under its vent)
            public Func<Vector3, bool> Inside = _ => false;   // a point in the shelter's own space is inside it
            public Vector3[] Seats = Array.Empty<Vector3>();  // seats on its bench (the bench top, in its own space)
        }

        public static readonly Kind Lavvu = new()
        {
            Prefab = "VDW_Lavvu", Model = "piece_shelter_lavvu", Key = "vdw_piece_lavvu", Name = "Hide Lavvu",
            Desc = "The far north's tent: hides sewn over a cone of poles, pinned shut above the door and open at the top. Room in the middle for a hole: drill one inside and the fish bite sooner (+10%): they can't see you against the sky.",
            Reqs = new[] { new RequirementConfig("Wood", 20), new RequirementConfig("WolfPelt", 6), new RequirementConfig("LeatherScraps", 8) },
            Bite = 0.10f, Comfort = 1, Fire = false,
            Inside = p => new Vector2(p.x, p.z).magnitude < 2.55f && p.y > -0.5f && p.y < 4.0f,
        };
        public static readonly Kind Igloo = new()
        {
            Prefab = "VDW_IceShelter", Model = "piece_shelter_igloo", Key = "vdw_piece_ice_shelter", Name = "Ice Shelter",
            Desc = "A dome of ice blocks, snow packed in the joints, a vent at the top. Room in the middle for a hole: drill one inside and the fish bite sooner (+15%): it's dark in here.",
            Reqs = new[] { new RequirementConfig("Ice", 30), new RequirementConfig("Stone", 5) },
            Bite = 0.15f, Comfort = 1, Fire = false,
            Inside = p => new Vector2(p.x, p.z).magnitude < 2.35f && p.y > -0.5f && p.y < 2.9f,
            // the ice bench round the back wall (the user's, shelter_v14; an arc about (0, 0.2), its middle 1.86 m out, its
            // top 0.31 m): seats on its front edge, 1.62 m out - sat at its middle the wall was right behind you and the
            // camera went into it. The middle one under the hide. (The model's -Y in Blender is the game's +Z.)
            // Raised in shelter_v15 to the vanilla bench's seat height (0.55 m): at 0.31 m the sitting legs went through the floor.
            Seats = new[] { new Vector3(0f, 0.57f, 1.82f), new Vector3(-1.13f, 0.55f, 1.36f), new Vector3(1.13f, 0.55f, 1.36f) },
        };
        public static readonly Kind ShipTent = new()
        {
            Prefab = "VDW_ShipTent", Model = "piece_shelter_ship_tent", Key = "vdw_piece_ship_tent", Name = "Ship-Tent",
            Desc = "A Viking ship's tent: hide over a ridge pole between crossed gable boards crowned with carved dragon heads, Elaking hair along the ridge. A hood over a gap in the ridge. A campfire at the back comes with it (it doesn't smoke you out); the front is clear to drill a hole and the fish bite sooner (+20%). The north wind finds you; the fish don't.",
            Reqs = new[] { new RequirementConfig("FineWood", 12), new RequirementConfig("ElakingHairBundle", 4), new RequirementConfig("LoxPelt", 4), new RequirementConfig("Iron", 2), new RequirementConfig("Stone", 5) },
            Bite = 0.20f, Comfort = 2,
            Inside = p => Mathf.Abs(p.x) < 2.1f && Mathf.Abs(p.z) < 3.15f && p.y > -0.5f && p.y < 3.3f,
            FireAt = new Vector3(0f, 0f, 1.493f),   // back under its vent (the model's -Y in Blender is the game's +Z) (build_shelters.py VC), the front clear to walk and fish
        };
        public static readonly Kind[] All = { Lavvu, Igloo, ShipTent };

        public static void Register()
        {
            foreach (var k in All)
            {
                try
                {
                    var piece = new CustomPiece(k.Prefab, "wood_pole", new PieceConfig
                    {
                        Name = Loc.Token(k.Key, k.Name),
                        Description = Loc.Token(k.Key + "_desc", k.Desc),
                        PieceTable = "Hammer",
                        Category = "Furniture",
                        CraftingStation = "piece_workbench",
                        Requirements = k.Reqs,
                    });
                    Setup(piece.PiecePrefab, k);
                    PieceManager.Instance.AddPiece(piece);
                }
                catch (Exception ex) { Plugin.Log.LogError($"Ice shelters: couldn't register '{k.Prefab}' ({ex})"); }
            }
        }

        private static void Setup(GameObject prefab, Kind k)
        {
            CustomModels.ApplyToPrefab(prefab, k.Model);
            var model = prefab.transform.Find("vdw_model");
            if (model != null)
            {
                // walked into: its colliders are its own shape (the box round the model would shut the door), so the
                // door, the vent and the room inside stay open - to the angler and to the smoke
                foreach (var box in prefab.GetComponents<BoxCollider>()) UnityEngine.Object.DestroyImmediate(box);
                // (on objects of their own beside the model, not on the drawn ones), on a layer that stops the angler but
                // not Valheim's smoke - the smoke balls caught under the covers and smoked everyone inside
                int wallLayer = prefab.layer;   // (the piece layer: Valheim's camera collides with it - 'Water' let the smoke through but not the camera)
                int i = 0;
                foreach (var mf in model.GetComponentsInChildren<MeshFilter>(true).Where(m => m.sharedMesh != null).ToList())
                {
                    if (mf.name.StartsWith("fur", StringComparison.OrdinalIgnoreCase)) continue;   // (hair cards: nothing to bump into)
                    var col = new GameObject("vdw_collider_" + i++) { layer = wallLayer };
                    col.transform.SetParent(mf.transform, false);
                    col.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
                }
                // the hammer still finds it (repair, remove): a trigger box round it on the piece's own layer
                Bounds b = default; bool any = false;
                foreach (var r in model.GetComponentsInChildren<Renderer>(true))
                {
                    var lb = new Bounds(prefab.transform.InverseTransformPoint(r.bounds.center), r.bounds.size);
                    if (!any) { b = lb; any = true; } else b.Encapsulate(lb);
                }
                _ = any;   // (no box: the walls themselves are hit)
                // Off the terrain (on the lake ice) Valheim sets a piece down by the point of its colliders nearest the
                // ground - but it skips concave mesh colliders, and a shelter has only those: with none to use it put the
                // ghost at twice the cursor's position, 50 m up, and the shelter "placed" out there vanished. A tiny box
                // just under the floor's middle is that point, so it sits on the ice. (On the piece layer: the ghost turns
                // off any collider its placement ray can't hit - an 'Ignore Raycast' box was dropped.)
                var baseBox = new GameObject("vdw_base") { layer = prefab.layer };
                baseBox.transform.SetParent(prefab.transform, false);
                var bb = baseBox.AddComponent<BoxCollider>();
                bb.size = new Vector3(0.05f, 0.01f, 0.05f); bb.center = new Vector3(0f, -0.006f, 0f);
            }
            else Plugin.Log.LogWarning($"Ice shelters: no model for '{k.Prefab}' - it keeps the pole's shape.");
            // the pole's snap points (its top and bottom) are no use on a shelter: building tools would snap it by them
            foreach (var t in prefab.GetComponentsInChildren<Transform>(true).Where(t => t != null && t.CompareTag("snappoint")).ToList())
                UnityEngine.Object.DestroyImmediate(t.gameObject);
            // ...nor its LODGroup (it lists only the pole's own hidden parts)
            foreach (var lod in prefab.GetComponentsInChildren<LODGroup>(true)) UnityEngine.Object.DestroyImmediate(lod);
            var wnt = prefab.GetComponent<WearNTear>();
            if (wnt != null) { wnt.m_supports = false; wnt.m_noSupportWear = false; wnt.m_health = 1200f; }
            var p = prefab.GetComponent<Piece>();
            if (p != null) { p.m_comfort = k.Comfort; p.m_comfortGroup = Piece.ComfortGroup.None; }
            if (k.Seats.Length > 0) AddSeats(prefab, k);
            prefab.AddComponent<IceShelter>().KindName = k.Prefab;   // (a string: copied when the piece is cloned, a class isn't)
        }

        /// <summary>
        /// Seats on a shelter's bench (the igloo's ice bench along its back wall): each a Valheim chair - a thin box on the
        /// bench top to look at and use, and its attach point facing the middle of the room. Standing up puts you in front
        /// of the bench.
        /// </summary>
        private static void AddSeats(GameObject prefab, Kind k)
        {
            var bench = PrefabManager.Cache.GetPrefab<GameObject>("piece_bench01");
            var vc = bench != null ? bench.GetComponentInChildren<Chair>(true) : null;
            // Valheim's sitting animation lifts the body from the attach point to a seat's height: the vanilla bench's
            // attach point is at its foot, its seat top higher up. Ours goes the same distance below our bench top.
            float drop = 0.45f;
            if (vc != null && vc.m_attachPoint != null)
            {
                var root = bench!.transform;
                float attachY = root.InverseTransformPoint(vc.m_attachPoint.position).y, top = float.NegativeInfinity;
                foreach (var c in bench.GetComponentsInChildren<Collider>(true))
                {
                    if (c.isTrigger) continue;
                    Bounds lb = c is BoxCollider bc ? new Bounds(bc.center, bc.size) : c is MeshCollider mc && mc.sharedMesh != null ? mc.sharedMesh.bounds : default;
                    if (lb.size == Vector3.zero) continue;
                    for (int cx = -1; cx <= 1; cx += 2) for (int cz = -1; cz <= 1; cz += 2)
                        top = Mathf.Max(top, root.InverseTransformPoint(c.transform.TransformPoint(lb.center + Vector3.Scale(lb.extents, new Vector3(cx, 1f, cz)))).y);
                }
                if (!float.IsInfinity(top) && top - attachY > 0.2f && top - attachY < 0.8f) drop = top - attachY;
                Plugin.Log.LogInfo($"Ice shelters: the vanilla bench's attach point is {attachY:0.00} m up, its seat top {top:0.00} m: our seats' attach points {drop:0.00} m under the bench top (animation '{vc.m_attachAnimation}').");
            }
            for (int i = 0; i < k.Seats.Length; i++)
            {
                var at = k.Seats[i];
                var face = new Vector3(-at.x, 0f, -at.z);   // toward the middle
                var seat = new GameObject("vdw_seat_" + i) { layer = prefab.layer };
                seat.transform.SetParent(prefab.transform, false);
                seat.transform.localPosition = at;
                seat.transform.localRotation = Quaternion.LookRotation(face.sqrMagnitude > 1e-4f ? face.normalized : Vector3.forward, Vector3.up);
                var box = seat.AddComponent<BoxCollider>();   // over the bench top (behind the front edge the seat sits on)
                box.size = new Vector3(0.7f, 0.08f, 0.4f); box.center = new Vector3(0f, 0.02f, -0.18f);
                var attach = new GameObject("attach").transform;
                attach.SetParent(seat.transform, false);
                attach.localPosition = new Vector3(0f, -drop, 0f);
                var chair = seat.AddComponent<Chair>();
                chair.m_name = Loc.Token("vdw_ice_bench", "Ice Bench");
                chair.m_attachPoint = attach;
                chair.m_attachAnimation = vc != null ? vc.m_attachAnimation : "attach_chair";
                chair.m_detachOffset = new Vector3(0f, drop + 0.1f, 0.6f);   // up and forward, off the bench into the room
                chair.m_useDistance = 2f;
            }
        }

        private static int _wallLayer = -1;

        /// <summary>
        /// The layer for the shelters' walls: one that Valheim's physics lets the player bump into but its smoke pass
        /// through (read from the game's own collision matrix: piece_nonsolid, vehicle... whichever fits first).
        /// </summary>
        private static int WallLayer()
        {
            if (_wallLayer >= 0) return _wallLayer;
            int piece = LayerMask.NameToLayer("piece"), smoke = LayerMask.NameToLayer("smoke"), character = LayerMask.NameToLayer("character");
            _wallLayer = piece;
            if (smoke < 0 || character < 0) { Plugin.Log.LogWarning("Ice shelters: no smoke/character layer - the walls stay on the piece layer."); return _wallLayer; }
            var order = new[] { "piece_nonsolid", "vehicle", "Default_small", "static_solid", "Default" }.Select(LayerMask.NameToLayer)
                        .Concat(Enumerable.Range(0, 32)).Where(l => l >= 0).Distinct();
            foreach (int l in order)
                if (!Physics.GetIgnoreLayerCollision(character, l) && Physics.GetIgnoreLayerCollision(smoke, l)) { _wallLayer = l; break; }
            Plugin.Log.LogInfo($"Ice shelters: walls on layer '{LayerMask.LayerToName(_wallLayer)}' (stops the player{(_wallLayer == piece ? ", and the smoke - no layer lets it through" : ", lets the smoke through")}).");
            return _wallLayer;
        }

        /// <summary>
        /// Diagnostics: who removes a shelter (on the lake ice they went the moment they were placed) - the call that
        /// destroyed it, with its stack.
        /// </summary>
        [HarmonyLib.HarmonyPatch(typeof(ZNetScene), nameof(ZNetScene.Destroy))]
        private static class WhoRemoves
        {
            private static void Prefix(GameObject go)
            {
                if (go != null && go.GetComponent<IceShelter>() != null && !Player.IsPlacementGhost(go))
                    Plugin.Log.LogInfo($"Ice shelters: {go.name} being removed at {go.transform.position} by:\n{System.Environment.StackTrace}");
            }
        }

        /// <summary>Whether a point is inside any shelter.</summary>
        public static bool AnyContains(Vector3 at)
        {
            foreach (var s in IceShelter.Instances)
                if (s != null && s.Kind != null && (s.transform.position - at).sqrMagnitude < 25f && s.Kind.Inside(s.transform.InverseTransformPoint(at))) return true;
            return false;
        }

        /// <summary>
        /// A fire inside a shelter makes no smoke (its smoke balls caught under the cover and smoked everyone inside),
        /// and so it's never "blocked" and put out by its own smoke.
        /// </summary>
        [HarmonyLib.HarmonyPatch(typeof(SmokeSpawner), "Spawn")]
        private static class NoSmokeInside
        {
            private static bool Prefix(SmokeSpawner __instance) => __instance == null || !AnyContains(__instance.transform.position);
        }

        [HarmonyLib.HarmonyPatch(typeof(SmokeSpawner), nameof(SmokeSpawner.IsBlocked))]
        private static class NeverBlockedInside
        {
            private static void Postfix(SmokeSpawner __instance, ref bool __result)
            {
                if (__result && __instance != null && AnyContains(__instance.transform.position)) __result = false;
            }
        }

        /// <summary>
        /// Diagnostics (on the lake ice the shelters vanished without going through ZNetScene.Destroy): who deletes a
        /// shelter's world data.
        /// </summary>
        [HarmonyLib.HarmonyPatch(typeof(ZDOMan), nameof(ZDOMan.DestroyZDO))]
        private static class WhoDeletesData
        {
            private static readonly HashSet<int> Hashes = new(All.Select(k => k.Prefab.GetStableHashCode()));
            private static void Prefix(ZDO zdo)
            {
                if (zdo != null && Hashes.Contains(zdo.GetPrefab()))
                    Plugin.Log.LogInfo($"Ice shelters: world data of a shelter deleted at {zdo.GetPosition()} by:\n{System.Environment.StackTrace}");
            }
        }

        /// <summary>The ice shelter the player is inside, if any.</summary>
        public static IceShelter? Around(Player? player)
        {
            if (player == null) return null;
            var at = player.transform.position;
            foreach (var s in IceShelter.Instances)
                if (s != null && s.Kind != null && (s.transform.position - at).sqrMagnitude < 25f && s.Kind.Inside(s.transform.InverseTransformPoint(at))) return s;
            return null;
        }

        /// <summary>Fish bite sooner through an Ice Hole drilled inside a shelter (FishingBuffs.PlaceBite).</summary>
        public static float BiteBonus(Player? player) => Around(player)?.Kind?.Bite ?? 0f;

        // the Ship-Tent's dragon heads (build_shelters.py ship_tent): each neck socketed in its board's iron collar (0.25 to
        // 0.40 m up the board from the crossing: cross = (0, HR + 0.04), the board's direction (0.568, 0.823) out and up;
        // the gables at L + 0.02) - 0.32 m up, clear of the other board - tipped up 18 degrees, the neck's tipped base
        // wholly inside the collar
        private const float HeadX = 0.1435f, HeadY = 3.579f, HeadZ = 3.22f, HeadScale = 0.25f, HeadLift = 18f;
        // darkened to the tent's oak (the head's plank texture is lighter): the tent's wood / the texture's average
        private static readonly Color HeadTint = new(0.84f, 0.72f, 0.65f, 1f);
        private static Material[]? _headMats;

        /// <summary>
        /// The Ship-Tent's dragon heads: the game's own carved head (the Dragon Head piece, wood_dragon1 - its unworn
        /// mesh, its material tinted to the tent's oak) growing out of the upper end of each crossed gable board, four
        /// of them, each pair looking away from each other along their boards. Only the look: no collider, no piece of
        /// its own.
        /// </summary>
        internal static void AddDragonHeads(GameObject go)
        {
            if (go.transform.Find("vdw_dragon_0") != null) return;
            var src = ZNetScene.instance != null ? ZNetScene.instance.GetPrefab("wood_dragon1") : PrefabManager.Cache.GetPrefab<GameObject>("wood_dragon1");
            var r = src?.transform.Find("New")?.GetComponentInChildren<MeshRenderer>(true) ?? src?.GetComponentInChildren<MeshRenderer>(true);
            var mf = r != null ? r.GetComponent<MeshFilter>() : null;
            if (r == null || mf == null || mf.sharedMesh == null) { Plugin.Log.LogWarning("Ice shelters: no dragon head for the Ship-Tent."); return; }
            for (int i = 0; i < 4; i++)
            {
                float end = i < 2 ? 1f : -1f, side = i % 2 == 0 ? 1f : -1f;
                var h = new GameObject("vdw_dragon_" + i) { layer = go.layer };
                h.transform.SetParent(go.transform, false);
                h.transform.localPosition = new Vector3(side * HeadX, HeadY, end * HeadZ);
                h.transform.localRotation = Quaternion.Euler(-HeadLift, side * 90f, 0f);   // the head's +Z out to its board's side, tipped up
                h.transform.localScale = Vector3.one * HeadScale;
                h.AddComponent<MeshFilter>().sharedMesh = mf.sharedMesh;
                _headMats ??= r.sharedMaterials.Select(m =>
                {
                    if (m == null) return m!;
                    var t = new Material(m) { name = m.name + "_vdw_tent" };
                    if (t.HasProperty("_Color")) t.SetColor("_Color", m.GetColor("_Color") * HeadTint);
                    return t;
                }).ToArray();
                h.AddComponent<MeshRenderer>().sharedMaterials = _headMats;
            }
        }

        private static Material? _calmSnow;

        /// <summary>
        /// The game's own material for a part of the igloo: its ice blocks and snow are the Ice Cube piece's. The snow's
        /// a copy with its surface noise turned off (Valheim/Snow Mesh pushes the surface out by up to 0.25 m of noise:
        /// fine on a rock, it tore the igloo's thin packed snow apart).
        /// </summary>
        internal static void UseVanillaMaterials(GameObject go)
        {
            var cube = ZNetScene.instance != null ? ZNetScene.instance.GetPrefab("piece_icecube") : PrefabManager.Cache.GetPrefab<GameObject>("piece_icecube");
            if (cube == null) return;
            var mats = cube.GetComponentsInChildren<MeshRenderer>(true).Select(r => r.sharedMaterial).Where(m => m != null).ToList();
            var ice = mats.FirstOrDefault(m => m.name.StartsWith("ice", StringComparison.OrdinalIgnoreCase));
            var snow = mats.FirstOrDefault(m => m.name.StartsWith("snow", StringComparison.OrdinalIgnoreCase));
            if (snow != null)
            {
                if (_calmSnow == null)
                {
                    _calmSnow = new Material(snow) { name = snow.name + "_vdw_igloo" };
                    // Valheim/Snow Mesh moves its vertices: offset noise, and a "scale out" by the snow level it reads from
                    // UV.y. Our UVs are a packed sheet, so every face went its own way and the snow tore into flaps.
                    var was = new System.Text.StringBuilder();
                    foreach (var p in new[] { "_OffsetNoiseStrengthHigh", "_OffsetNoiseStrengthLow", "_ScaleOutFactor", "_SnowLevelStrength" })
                        if (_calmSnow.HasProperty(p)) { was.Append($" {p} {_calmSnow.GetFloat(p):0.###}"); _calmSnow.SetFloat(p, 0f); }
                    foreach (var p in new[] { "_ScaleOutPoint", "_ObjectCenterHeight", "_SnowLevel", "_TextureSize", "_OffsetNoiseSize" })
                        if (_calmSnow.HasProperty(p)) was.Append($" {p} {_calmSnow.GetFloat(p):0.###}");
                    Plugin.Log.LogInfo($"Ice shelters: the igloo's snow ({snow.shader?.name}) calmed - was{was}.");
                }
                snow = _calmSnow;
            }
            foreach (var r in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                var m = r.gameObject.name.StartsWith("ice", StringComparison.OrdinalIgnoreCase) ? ice : r.gameObject.name.StartsWith("snow", StringComparison.OrdinalIgnoreCase) ? snow : null;
                if (m != null) r.sharedMaterials = Enumerable.Repeat(m, r.sharedMaterials.Length).ToArray();
            }
        }
    }

    /// <summary>A placed ice shelter: its campfire (the Ship-Tent's), set when it's built and taken down with it.</summary>
    internal sealed class IceShelter : MonoBehaviour
    {
        internal static readonly List<IceShelter> Instances = new();
        public string KindName = "";
        public IceShelters.Kind? Kind;
        private ZNetView? _nview;
        private const string FireKey = "vdw_shelter_fire", FireSetKey = "vdw_shelter_fire_set";

        private void Awake()
        {
            _nview = GetComponent<ZNetView>();
            Kind = IceShelters.All.FirstOrDefault(k => k.Prefab == KindName);
            var wnt = GetComponent<WearNTear>();
            if (wnt != null) wnt.m_onDestroyed += TakeDownFire;
            if (Kind == IceShelters.Igloo) IceShelters.UseVanillaMaterials(gameObject);
            if (Kind == IceShelters.ShipTent) IceShelters.AddDragonHeads(gameObject);
            _report = Time.time + 1.5f; _born = Time.time;
        }

        private float _born;

        private void OnDestroy()
        {
            if (_nview != null && _nview.IsValid() || Time.time - _born < 5f)
                Plugin.Log.LogInfo($"Ice shelters: {KindName} removed after {Time.time - _born:0.0} s at {transform.position} (ghost {Player.IsPlacementGhost(gameObject)}, view {(_nview != null && _nview.IsValid())}, under {(transform.parent != null ? transform.parent.name : "-")}, scene {gameObject.scene.name}).");
        }

        // Diagnostics (the shelters didn't show in game, the build ghost nor placed): once per kind and per ghost/placed, a
        // second and a half in, what its renderers are doing.
        private float _report;
        private static readonly HashSet<string> Reported = new();

        private void Update()
        {
            if (_report <= 0f || Time.time < _report) return;
            _report = 0f;
            bool ghost = Player.IsPlacementGhost(gameObject);
            if (!Reported.Add(KindName + (ghost ? " ghost" : " placed"))) return;
            var sb = new System.Text.StringBuilder();
            sb.Append($"Ice shelters: {KindName} ({(ghost ? "build ghost" : "placed")}) at {transform.position}, scale {transform.lossyScale}, " +
                      $"active {gameObject.activeInHierarchy}, layer {LayerMask.LayerToName(gameObject.layer)}, nview {(_nview != null && _nview.IsValid())}");
            foreach (var r in GetComponentsInChildren<Renderer>(true))
            {
                var mf = r.GetComponent<MeshFilter>();
                var m = r.sharedMaterial;
                sb.Append($"\n   {r.name} [{r.GetType().Name}] enabled {r.enabled} active {r.gameObject.activeInHierarchy} visible {r.isVisible} " +
                          $"layer {LayerMask.LayerToName(r.gameObject.layer)} bounds {r.bounds.center}/{r.bounds.size} " +
                          $"mesh {(mf != null && mf.sharedMesh != null ? $"{mf.sharedMesh.name} v{mf.sharedMesh.vertexCount}" : "-")} " +
                          $"mat {(m != null ? $"{m.name} / {(m.shader != null ? m.shader.name : "no shader")} supported {m.shader?.isSupported} queue {m.renderQueue}" : "none")}");
            }
            // a known-good renderer to compare isVisible against (the player's body), the camera, and what's straight above the
            // shelter's base (is it under the ice?)
            var cam = Camera.main;
            var body = Player.m_localPlayer != null ? Player.m_localPlayer.GetComponent<VisEquipment>()?.m_bodyModel : null;
            sb.Append($"\n   control: player body visible {(body != null ? body.isVisible.ToString() : "-")}; camera {(cam != null ? $"{cam.name} at {cam.transform.position}, sees layer {((cam.cullingMask & (1 << gameObject.layer)) != 0)}, near {cam.nearClipPlane:0.##} far {cam.farClipPlane:0}" : "none")}");
            var up = transform.position + Vector3.up * 0.3f;
            foreach (var hit in Physics.RaycastAll(up, Vector3.up, 30f, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance).Take(4))
                if (!hit.collider.transform.IsChildOf(transform)) sb.Append($"\n   above the base: '{hit.collider.name}' (root '{hit.collider.transform.root.name}', layer {LayerMask.LayerToName(hit.collider.gameObject.layer)}) {hit.distance + 0.3f:0.00} m up");
            foreach (var lod in GetComponentsInChildren<LODGroup>(true))
                sb.Append($"\n   LODGroup on {lod.name}: enabled {lod.enabled}, size {lod.size}, {lod.lodCount} LODs, {string.Join(", ", lod.GetLODs().Select(l => $"{l.screenRelativeTransitionHeight:0.###}: {l.renderers.Length} renderers"))}");
            Plugin.Log.LogInfo(sb.ToString());
        }

        private void OnEnable() => Instances.Add(this);
        private void OnDisable() => Instances.Remove(this);

        private void Start()
        {
            // the campfire: once, by whoever owns the new shelter (not the build ghost - its view isn't live)
            if (Kind == null || !Kind.Fire || _nview == null || !_nview.IsValid() || !_nview.IsOwner()) return;
            var zdo = _nview.GetZDO();
            if (zdo.GetBool(FireSetKey)) return;
            zdo.Set(FireSetKey, true);
            var prefab = ZNetScene.instance?.GetPrefab("fire_pit");
            if (prefab == null) { Plugin.Log.LogWarning("Ice shelters: no campfire prefab to set in the shelter."); return; }
            var fire = Instantiate(prefab, transform.TransformPoint(Kind.FireAt) + Vector3.up * 0.02f, transform.rotation);

            if (Player.m_localPlayer != null && fire.GetComponent<ZNetView>() is ZNetView cv && cv.IsValid()) cv.GetZDO().Set(ZDOVars.s_creator, Player.m_localPlayer.GetPlayerID());   // (built by the shelter's builder)
            var fnv = fire.GetComponent<ZNetView>();
            if (fnv != null && fnv.IsValid()) zdo.Set(FireKey, fnv.GetZDO().m_uid);
        }

        private void TakeDownFire()
        {
            if (_nview == null || !_nview.IsValid()) return;
            var id = _nview.GetZDO().GetZDOID(FireKey);
            if (id == ZDOID.None) return;
            var fire = ZNetScene.instance?.FindInstance(id);
            if (fire != null)
            {
                var fnv = fire.GetComponent<ZNetView>();
                if (fnv != null && fnv.IsValid()) { fnv.ClaimOwnership(); ZNetScene.instance!.Destroy(fire); }
            }
        }
    }
}
