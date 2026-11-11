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
    /// Ice fishing (roadmap #34): in the Deep North the rivers and lakes are frozen over with walkable ice (the IceSheet
    /// and Icepond props). Nothing can be cast onto the ice; drill a hole in it with the Ice Auger and fish down the hole.
    /// Some fish (IceOnly) live only under the ice and bite only there; the cold-water fish of the place bite there too.
    /// The Ice Fishing Rod (IceRod) fishes only through a hole, with a longer hook window; any other rod works in a hole
    /// at half the hook window. A hole freezes over again after a while.
    /// What counts as ice: a solid collider over the water that's slippery (no friction, as Valheim's own skating and
    /// slipping read it) or whose object is named for ice. `vdw_debug ice` shows what's under you, to check in game.
    /// </summary>
    internal static class IceFishing
    {
        public const string AugerPrefab = "VDW_IceAuger", HolePrefab = "VDW_IceHole";
        public const float RefreezeSeconds = 20f * 60f;
        internal const float MinWaterUnderIce = 1f;     // m of water under the ice for a hole to fish
        private const float DrillReach = 1.6f;         // the hole goes this far in front of you
        private const float CastToHoleReach = 4f;      // a hole this close in front of you takes your cast

        public static void Register()
        {
            try
            {
                var auger = new CustomItem(AugerPrefab, "SpearFlint", new ItemConfig
                {
                    Amount = 1,
                    CraftingStation = "forge",
                    MinStationLevel = 3,
                    Requirements = new[] { new RequirementConfig("Iron", 4), new RequirementConfig("FineWood", 2), new RequirementConfig("Silver", 2) }
                });
                var shared = auger.ItemDrop.m_itemData.m_shared;
                shared.m_name = Loc.Token("vdw_ice_auger", "Ice Auger");
                shared.m_description = Loc.Token("vdw_ice_auger_desc",
                    "A long spiral bit with a T-handle. Drill a hole through the ice of a frozen lake or river and fish down it - some fish live only under the ice. The hole freezes over again after a while.");
                // a tool for ice only, carried like the spear it's made from (held halfway up the shaft): no damage, no
                // throw, not a spear for fish; its attack drills instead (IceDrill)
                shared.m_damages = new HitData.DamageTypes();
                shared.m_damagesPerLevel = new HitData.DamageTypes();
                shared.m_toolTier = 0;
                shared.m_skillType = Skills.SkillType.Pickaxes;
                foreach (var a in new[] { shared.m_attack, shared.m_secondaryAttack })
                    if (a != null) { a.m_hitTerrain = false; a.m_spawnOnTrigger = null; a.m_harvest = false; a.m_attackProjectile = null; }
                if (shared.m_secondaryAttack != null) shared.m_secondaryAttack.m_attackAnimation = "";
                CustomModels.ApplyToPrefab(auger.ItemPrefab, IceDrill.AugerModel);
                ItemManager.Instance.AddItem(auger);

                var hole = PrefabManager.Instance.CreateEmptyPrefab(HolePrefab, true);
                foreach (var c in hole.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                foreach (var r in hole.GetComponentsInChildren<Renderer>(true)) UnityEngine.Object.DestroyImmediate(r);
                foreach (var m in hole.GetComponentsInChildren<MeshFilter>(true)) UnityEngine.Object.DestroyImmediate(m);
                var nview = hole.GetComponent<ZNetView>();
                if (nview != null) nview.m_persistent = true;
                hole.AddComponent<IceHole>();
                PrefabManager.Instance.AddPrefab(new CustomPrefab(hole, false));
            }
            catch (Exception ex) { Plugin.Log.LogError($"Ice fishing: couldn't register ({ex})"); }
        }

        // ------------------------------------------------------------------ what's ice

        private static readonly RaycastHit[] Hits = new RaycastHit[16];

        /// <summary>A collider that's the frozen surface of water: slippery, or an object named for ice.</summary>
        public static bool IsIce(Collider c)
        {
            if (c == null || c.isTrigger) return false;
            if (c.GetComponentInParent<Heightmap>() != null || c.GetComponentInParent<Character>() != null || c.GetComponentInParent<Piece>() != null) return false;
            var mat = c.sharedMaterial;
            if (mat != null && mat.dynamicFriction <= 0.02f && mat.staticFriction <= 0.05f) return true;
            for (var t = c.transform; t != null; t = t.parent)
                if (t.name.IndexOf("ice", StringComparison.OrdinalIgnoreCase) >= 0 && t.name.IndexOf("price", StringComparison.OrdinalIgnoreCase) < 0) return true;
            return false;
        }

        /// <summary>
        /// The ice at a spot (straight down from above it): its top, and how much water lies under it (water level down
        /// to the lake bed). False if the first thing down there isn't ice.
        /// </summary>
        public static bool IceAt(Vector3 at, out float iceY, out float waterUnder)
        {
            iceY = 0f; waterUnder = 0f;
            int n = Physics.RaycastNonAlloc(new Vector3(at.x, at.y + 6f, at.z), Vector3.down, Hits, 14f, ~0, QueryTriggerInteraction.Ignore);
            Collider? first = null; float best = float.MaxValue;
            for (int i = 0; i < n; i++)
            {
                var h = Hits[i];
                if (h.collider == null || h.collider.GetComponentInParent<Character>() != null || h.collider.GetComponentInParent<ItemDrop>() != null || h.collider.GetComponentInParent<IceHole>() != null
                    || h.collider.GetComponentInParent<IceShelter>() != null) continue;   // (drilled inside a shelter: through its roof)
                if (h.distance < best) { best = h.distance; first = h.collider; iceY = h.point.y; }
            }
            if (first == null || !IsIce(first)) return false;
            float water = ZoneSystem.instance != null ? WaterLevel() : 30f;
            float ground = ZoneSystem.instance != null ? ZoneSystem.instance.GetGroundHeight(at) : iceY - 2f;
            // the water under it: from the ice (or the sea level, if the ice sits above it) down to the bed
            waterUnder = Mathf.Min(iceY, Mathf.Max(water, iceY - 0.2f)) - ground;
            return true;
        }

        private static float WaterLevel()
        {
            try { return (float)AccessTools.Field(typeof(ZoneSystem), "m_waterLevel").GetValue(ZoneSystem.instance); }
            catch { return 30f; }
        }

        /// <summary>The water at this spot is frozen over (a cast can't go into it - only down an Ice Hole).</summary>
        public static bool FrozenAt(Vector3 at, float waterLevel)
        {
            if (IceHole.Near(at, 0.8f) != null) return false;
            return IceAt(at, out float iceY, out _) && iceY > waterLevel - 0.6f;
        }

        // ------------------------------------------------------------------ casting down a hole

        /// <summary>
        /// An Ice Hole just in front of the player takes the cast: straight down it, with the water under the ice for depth.
        /// </summary>
        public static bool HoleInFront(Player player, out Vector3 dir, out Vector3 spot, out float distance, out float depth)
        {
            dir = player.transform.forward; spot = player.transform.position; distance = 0f; depth = 0f;
            var look = player.GetLookDir(); look.y = 0f;
            if (look.sqrMagnitude < 0.01f) look = player.transform.forward;
            look.Normalize();
            IceHole? best = null; float bestD = float.MaxValue;
            foreach (var h in IceHole.All)
            {
                if (h == null) continue;
                var v = h.transform.position - player.transform.position; v.y = 0f;
                float d = v.magnitude;
                if (d > CastToHoleReach || (d > 0.6f && Vector3.Angle(look, v) > 55f)) continue;
                if (d < bestD) { bestD = d; best = h; }
            }
            if (best == null) return false;
            var to = best.transform.position - player.transform.position; to.y = 0f;
            dir = to.sqrMagnitude > 0.01f ? to.normalized : look;
            spot = best.transform.position;
            distance = Mathf.Max(0.5f, bestD);
            depth = Mathf.Max(MinWaterUnderIce, best.Depth);
            return true;
        }

        /// <summary>The hook window down a hole: an ice rod's is longer, any other rod's is halved.</summary>
        public static float WindowFactor(FishingSession s) => !s.IceHole ? 1f : s.Rod.IceRod ? 1.25f : 0.5f;

        // ------------------------------------------------------------------ drilling

        public static bool IsAuger(ItemDrop.ItemData? item) => item?.m_dropPrefab != null && item.m_dropPrefab.name == AugerPrefab;

        /// <summary>The auger breaks through (IceDrill): the hole opens where it stood, <paramref name="at"/> on the ice's top.</summary>
        internal static void MakeHole(Player player, Vector3 at)
        {
            if (!IceAt(at, out float iceY, out float under) || under < MinWaterUnderIce || IceHole.Near(at, 0.9f) != null) return;
            var prefab = ZNetScene.instance?.GetPrefab(HolePrefab);
            if (prefab == null) return;
            var go = UnityEngine.Object.Instantiate(prefab, new Vector3(at.x, iceY + 0.01f, at.z), Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 360f), 0f));
            var hole = go.GetComponent<IceHole>();
            hole?.Init(under);
            foreach (var fx in new[] { "fx_icefloor_destruction", "vfx_iceblocker_destroyed" })
            {
                var e = PrefabManager.Cache.GetPrefab<GameObject>(fx);
                if (e != null) { UnityEngine.Object.Instantiate(e, go.transform.position, Quaternion.identity); break; }
            }
            player.RaiseSkill(Skills.SkillType.Fishing, 0.5f);
            player.Message(MessageHud.MessageType.Center, $"You drill through the ice. {under:0.#} m of water under it.");
        }

        /// <summary>For `vdw_debug ice`: what's under you and in front of you, to see how the ice is made.</summary>
        public static string Describe(Player player)
        {
            var lines = new List<string>();
            foreach (var (label, at) in new[] { ("under you", player.transform.position), ("in front", player.transform.position + player.transform.forward * DrillReach) })
            {
                int n = Physics.RaycastNonAlloc(new Vector3(at.x, at.y + 6f, at.z), Vector3.down, Hits, 14f, ~0, QueryTriggerInteraction.Ignore);
                var hits = Hits.Take(n).Where(h => h.collider != null && h.collider.GetComponentInParent<Character>() == null).OrderBy(h => h.distance).Take(3).ToList();
                float ground = ZoneSystem.instance != null ? ZoneSystem.instance.GetGroundHeight(at) : 0f;
                string first = string.Join(" | ", hits.Select(h =>
                {
                    var c = h.collider; var m = c.sharedMaterial;
                    var root = c.transform.root != null ? c.transform.root.name : c.name;
                    return $"{root}/{c.name} layer={LayerMask.LayerToName(c.gameObject.layer)} y={h.point.y:0.00} friction={(m != null ? $"{m.dynamicFriction:0.00}/{m.staticFriction:0.00}" : "none")} ice={IsIce(c)}";
                }));
                bool ice = IceAt(at, out float iceY, out float under);
                lines.Add($"{label}: {first}");
                lines.Add($"   ground {ground:0.00}, water level {WaterLevel():0.00}, ice {(ice ? $"yes at {iceY:0.00}, {under:0.0} m of water under it" : "no")}, biome {WorldGenerator.instance?.GetBiome(at)}");
            }
            return string.Join("\n", lines);
        }
    }

    /// <summary>
    /// A hole drilled in the ice: dark water in a ring of slush and ice chips. It freezes over after a while - skinning
    /// over the last two minutes - unless someone clears the slush out of it ([E]), which keeps it open as long again.
    /// </summary>
    internal sealed class IceHole : MonoBehaviour, Hoverable, Interactable
    {
        internal static readonly List<IceHole> All = new();
        private ZNetView? _nview;
        private Transform? _skin;
        private Renderer? _skinRenderer;
        private const string ModelKey = "piece_ice_hole";
        private const float WaterRadius = 0.25f;   // the open water's (the auger's bit is as wide)

        public float Depth => _nview != null && _nview.IsValid() ? _nview.GetZDO().GetFloat("vdw_depth", 2f) : 2f;

        public static IceHole? Near(Vector3 at, float within)
        {
            IceHole? best = null; float bestD = within;
            foreach (var h in All)
            {
                if (h == null) continue;
                var v = h.transform.position - at; v.y = 0f;
                if (v.magnitude <= bestD) { bestD = v.magnitude; best = h; }
            }
            return best;
        }

        public void Init(float depth)
        {
            if (_nview == null || !_nview.IsValid()) return;
            _nview.GetZDO().Set("vdw_depth", depth);
            _nview.GetZDO().Set("vdw_made", Now);
        }

        private static float Now => ZNet.instance != null ? (float)ZNet.instance.GetTimeSeconds() : 0f;

        /// <summary>Seconds until it freezes over.</summary>
        private float Left => _nview != null && _nview.IsValid() ? IceFishing.RefreezeSeconds - (Now - _nview.GetZDO().GetFloat("vdw_made", Now)) : IceFishing.RefreezeSeconds;

        private void Awake()
        {
            _nview = GetComponent<ZNetView>();
            if (_nview == null || _nview.GetZDO() == null) return;
            All.Add(this);
            _nview.Register("vdw_clear", RPC_Clear);
            BuildLook();
        }

        private void OnDestroy()
        {
            All.Remove(this);
            // the ice it was cut into gets its own mesh back (or keeps only the other holes)
            if (_cut) try { IceCut.Refresh(transform.position, out _, out _); } catch { }
        }

        // ------------------------------------------------------------------ clearing the slush

        public string GetHoverName() => "Ice Hole";

        public string GetHoverText()
        {
            float left = Left;
            string when = left > 60f ? $"{Mathf.CeilToInt(left / 60f)} min" : $"{Mathf.Max(0, Mathf.CeilToInt(left))} s";
            return Localization.instance.Localize($"Ice Hole\n<color=#9fd3ff>Freezes over in {when}</color>\n[<color=yellow><b>$KEY_Use</b></color>] Clear the slush");
        }

        public float GetHoverOffset() => 0f;

        public bool Interact(Humanoid user, bool hold, bool alt)
        {
            if (hold || _nview == null || !_nview.IsValid()) return false;
            _nview.InvokeRPC("vdw_clear");
            user.Message(MessageHud.MessageType.Center, "You scoop the slush out of the hole. It'll stay open a while longer.");
            return true;
        }

        public bool UseItem(Humanoid user, ItemDrop.ItemData item) => false;

        private void RPC_Clear(long sender)
        {
            if (_nview == null || !_nview.IsOwner()) return;
            _nview.GetZDO().Set("vdw_made", Now);
        }

        // ------------------------------------------------------------------ the look

        private static Material? _waterMat, _slushMat, _chipMat, _skinMat;

        private static Shader? _lit;

        /// <summary>
        /// A plain material. Valheim strips Unity's Standard shader (Shader.Find gave null and the whole hole was never
        /// drawn): the shader comes from the hole's own model's material or the vanilla ice's.
        /// </summary>
        private static Material Mat(Color c, float smooth)
        {
            var m = new Material(Shader.Find("Standard") ?? _lit ?? Shader.Find("Sprites/Default")) { color = c };
            m.SetFloat("_Glossiness", smooth);
            return m;
        }

        private void BuildLook()
        {
            bool haveModel = CustomModels.TryGetCustom(ModelKey, out var mesh, out var mat);
            var ice = VanillaIce();
            _lit ??= (haveModel ? mat?.shader : null) ?? ice?.shader;
            _skinMat ??= Mat(new Color(0.62f, 0.74f, 0.82f), 0.85f);
            GameObject Part(PrimitiveType type, Vector3 pos, Vector3 scale, Material mat, Quaternion? rot = null)
            {
                var g = GameObject.CreatePrimitive(type);
                Destroy(g.GetComponent<Collider>());
                g.transform.SetParent(transform, false);
                g.transform.localPosition = pos; g.transform.localScale = scale; g.transform.localRotation = rot ?? Quaternion.identity;
                var r = g.GetComponent<Renderer>(); r.sharedMaterial = mat; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                return g;
            }
            _ice = ice;
            _water = new GameObject("vdw_water");
            _water.transform.SetParent(transform, false);
            if (TryCut()) { }   // a real hole in the ice: the game's own water shows through it
            else if (haveModel)
            {
                // (ice that can't be cut: the old model, with its own water - swapped out if the ice turns up)
                var g = new GameObject("vdw_model");
                g.transform.SetParent(_water.transform, false);
                g.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = g.AddComponent<MeshRenderer>(); r.sharedMaterial = mat; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            else
            {
                // a stand-in until the model's there: dark water in a slush ring, chips of ice round it
                _waterMat ??= Mat(new Color(0.02f, 0.05f, 0.08f), 0.95f);
                _slushMat ??= Mat(new Color(0.72f, 0.80f, 0.86f), 0.35f);
                _chipMat ??= Mat(new Color(0.78f, 0.88f, 0.95f), 0.8f);
                Part(PrimitiveType.Cylinder, new Vector3(0f, 0.005f, 0f), new Vector3(1.0f, 0.012f, 1.0f), _slushMat).transform.SetParent(_water.transform, true);
                Part(PrimitiveType.Cylinder, new Vector3(0f, 0.012f, 0f), new Vector3(WaterRadius * 2f, 0.01f, WaterRadius * 2f), _waterMat).transform.SetParent(_water.transform, true);
                var rng = new System.Random(GetInstanceID());
                for (int i = 0; i < 9; i++)
                {
                    float a = (float)rng.NextDouble() * Mathf.PI * 2f, rr = 0.45f + (float)rng.NextDouble() * 0.3f, s = 0.05f + (float)rng.NextDouble() * 0.09f;
                    Part(PrimitiveType.Cube, new Vector3(Mathf.Cos(a) * rr, s * 0.3f, Mathf.Sin(a) * rr), new Vector3(s * 1.4f, s * 0.6f, s),
                         _chipMat, Quaternion.Euler((float)rng.NextDouble() * 30f, (float)rng.NextDouble() * 360f, (float)rng.NextDouble() * 30f)).transform.SetParent(_water.transform, true);
                }
            }
            // the rim, in the vanilla ice's own material: the ice it's drilled through, or else the Deep North's ice sheet
            BuildRim(ice ?? _skinMat!);
            // the skin of new ice that closes over the water as it refreezes (hidden until then)
            _skin = Part(PrimitiveType.Cylinder, new Vector3(0f, 0.016f, 0f), Vector3.zero, ice ?? _skinMat!).transform;
            _skinRenderer = _skin.GetComponent<Renderer>(); _skinRenderer.enabled = false;
            // something to look at for the [E] prompt: a thin slab over the hole, on a layer you walk through
            var hit = new GameObject("vdw_hover");
            hit.transform.SetParent(transform, false);
            hit.layer = LayerMask.NameToLayer("piece_nonsolid");
            var box = hit.AddComponent<BoxCollider>();
            box.size = new Vector3(0.9f, 0.04f, 0.9f); box.center = new Vector3(0f, 0.02f, 0f);
        }

        private bool _cut;
        private float _cutTries, _nextCutTry;
        private Material? _ice;
        private GameObject? _water;

        /// <summary>
        /// Cuts the hole through the ice it's in (IceCut) and dresses it: an ice wall down through the slab, a little grey
        /// slush and ice bits floating on the real water, a few small chips round it. False: no cuttable ice here (yet -
        /// a hole loaded with its area can come before the ice does; Update tries again for a while).
        /// </summary>
        private bool TryCut()
        {
            if (_cut) return true;
            if (!IceCut.Refresh(transform.position, out float top, out float bottom)) return false;
            _cut = true;
            if (_water != null) foreach (Transform c in _water.transform) Destroy(c.gameObject);
            BuildCut(top - transform.position.y, bottom - transform.position.y);
            return true;
        }

        private void BuildCut(float top, float bottom)
        {
            var ice = _ice ?? _skinMat!;
            var parent = _water!.transform;
            // the wall of the hole, in the ice's own material: from the top of the ice down past its underside
            const int seg = 28;
            float r = WaterRadius, y0 = top + 0.035f, y1 = Mathf.Min(bottom, top - 0.12f) - 0.08f;
            var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
            for (int j = 0; j <= seg; j++)
            {
                float th = 2f * Mathf.PI * j / seg, rr = r * (1f + 0.04f * Mathf.Sin(th * 5f + 0.7f));
                foreach (float y in new[] { y0, y1 })
                {
                    verts.Add(new Vector3(rr * Mathf.Cos(th), y, rr * Mathf.Sin(th)));
                    uvs.Add(new Vector2(th * r, y));
                }
            }
            for (int j = 0; j < seg; j++)
            {
                int a = j * 2;
                tris.AddRange(new[] { a, a + 2, a + 1, a + 1, a + 2, a + 3 });
            }
            var wall = new Mesh { name = "vdw_ice_hole_wall" };
            wall.SetVertices(verts); wall.SetUVs(0, uvs); wall.SetTriangles(tris, 0);
            wall.RecalculateNormals();
            // facing in, toward the middle of the hole
            if (wall.normals[0].x * verts[0].x + wall.normals[0].z * verts[0].z > 0f) { tris.Reverse(); wall.SetTriangles(tris, 0); wall.RecalculateNormals(); }
            wall.RecalculateTangents(); wall.RecalculateBounds();
            var w = new GameObject("vdw_wall");
            w.transform.SetParent(parent, false);
            w.AddComponent<MeshFilter>().sharedMesh = wall;
            w.AddComponent<MeshRenderer>().sharedMaterial = ice;

            // the water comes up the hole nearly to the top of the ice, as it does in a real hole: a disc of the lake's own
            // water (its WaterVolume's material, so it moves and shines with the rest) - or, with none to borrow, the
            // water level as it is
            float water = (ZoneSystem.instance != null ? ZoneSystem.instance.m_waterLevel : transform.position.y - 0.1f) - transform.position.y;
            if (RaisedWater(parent, top - 0.06f)) water = top - 0.06f;
            // slush and little bits of broken ice floating on the water in the hole, and a few chips on the ice round it
            _slushMat ??= Mat(new Color(0.60f, 0.66f, 0.70f), 0.3f);
            var rng = new System.Random(GetInstanceID());
            float Rnd(float lo, float hi) => lo + (float)rng.NextDouble() * (hi - lo);
            for (int i = 0; i < 6; i++)
            {
                float a = Rnd(0f, Mathf.PI * 2f), rr = Rnd(0.05f, 0.19f), sz = Rnd(0.04f, 0.09f);
                Piece(parent, new Vector3(Mathf.Cos(a) * rr, water + 0.004f, Mathf.Sin(a) * rr), new Vector3(sz, 0.008f, sz * Rnd(0.6f, 1f)),
                      i % 2 == 0 ? _slushMat : ice, Quaternion.Euler(Rnd(-6f, 6f), Rnd(0f, 360f), Rnd(-6f, 6f)));
            }
            for (int i = 0; i < 5; i++)
            {
                float a = Rnd(0f, Mathf.PI * 2f), rr = Rnd(0.34f, 0.55f), sz = Rnd(0.025f, 0.055f);
                Piece(parent, new Vector3(Mathf.Cos(a) * rr, top + sz * 0.2f, Mathf.Sin(a) * rr), new Vector3(sz * 1.3f, sz * 0.5f, sz), ice,
                      Quaternion.Euler(Rnd(0f, 25f), Rnd(0f, 360f), Rnd(0f, 25f)));
            }
        }

        /// <summary>A disc of the lake's own water in the hole at a height (local). False: no water surface to borrow here.</summary>
        private bool RaisedWater(Transform parent, float y)
        {
            try
            {
                var at = transform.position;
                WaterVolume? best = null;
                foreach (var wv in WaterVolume.Instances)
                {
                    if (wv == null || wv.m_waterSurface == null) continue;
                    var b = wv.m_waterSurface.bounds;
                    if (at.x < b.min.x || at.x > b.max.x || at.z < b.min.z || at.z > b.max.z) continue;
                    best = wv; break;
                }
                if (best == null) return false;
                var surf = best.m_waterSurface;
                var mat = surf.material;   // (the volume's own instance, which it keeps up to date: waves, time, depth)
                if (mat == null) return false;
                // a disc, its UVs where it sits on the volume's surface (the depth across the surface is read by them)
                const int seg = 24;
                float r = WaterRadius * 1.04f;
                var sb = surf.bounds;
                var verts = new List<Vector3> { new Vector3(0f, y, 0f) };
                for (int j = 0; j < seg; j++) { float th = 2f * Mathf.PI * j / seg; verts.Add(new Vector3(r * Mathf.Cos(th), y, r * Mathf.Sin(th))); }
                var uvs = verts.Select(v => { var w = transform.TransformPoint(v); return new Vector2((w.x - sb.min.x) / Mathf.Max(0.01f, sb.size.x), (w.z - sb.min.z) / Mathf.Max(0.01f, sb.size.z)); }).ToList();
                var tris = new List<int>();
                for (int j = 0; j < seg; j++) { tris.Add(0); tris.Add(1 + (j + 1) % seg); tris.Add(1 + j); }
                var mesh = new Mesh { name = "vdw_ice_hole_water" };
                mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
                mesh.RecalculateNormals();
                if (mesh.normals[0].y < 0f) { tris.Reverse(); mesh.SetTriangles(tris, 0); mesh.RecalculateNormals(); }
                mesh.RecalculateBounds();
                var g = new GameObject("vdw_raised_water");
                g.transform.SetParent(parent, false);
                g.layer = surf.gameObject.layer;
                g.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = g.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                return true;
            }
            catch (Exception ex) { Plugin.Log.LogDebug($"Ice holes: no raised water ({ex.Message})."); return false; }
        }

        private static void Piece(Transform parent, Vector3 pos, Vector3 scale, Material mat, Quaternion rot)
        {
            var g = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Destroy(g.GetComponent<Collider>());
            g.transform.SetParent(parent, false);
            g.transform.localPosition = pos; g.transform.localScale = scale; g.transform.localRotation = rot;
            var r = g.GetComponent<Renderer>(); r.sharedMaterial = mat; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        private static Material? _sheetIce;

        /// <summary>The material of the ice under the hole (its renderer), or of the vanilla IceSheet prop.</summary>
        private Material? VanillaIce()
        {
            try
            {
                var from = transform.position + Vector3.up * 3f;
                foreach (var h in Physics.RaycastAll(from, Vector3.down, 8f, ~0, QueryTriggerInteraction.Ignore).OrderBy(h => h.distance))
                {
                    if (h.collider == null || h.collider.GetComponentInParent<IceHole>() != null || h.collider.GetComponentInParent<Character>() != null) continue;
                    if (!IceFishing.IsIce(h.collider)) break;
                    var r = h.collider.GetComponent<Renderer>() ?? h.collider.GetComponentInParent<Renderer>() ?? h.collider.GetComponentInChildren<Renderer>();
                    if (r != null && r.sharedMaterial != null) return r.sharedMaterial;
                    break;
                }
                if (_sheetIce == null)
                {
                    var sheet = PrefabManager.Cache.GetPrefab<GameObject>("IceSheet");
                    _sheetIce = sheet?.GetComponentsInChildren<MeshRenderer>(true).Select(r => r.sharedMaterial).FirstOrDefault(m => m != null);
                }
                return _sheetIce;
            }
            catch (Exception ex) { Plugin.Log.LogDebug($"Ice hole: no vanilla ice material ({ex.Message})"); return null; }
        }

        /// <summary>
        /// The rim: broken ice heaved up at the water's edge, sloping away on the outside back down into the ice, its outer
        /// edge uneven and just under the ice's top (the hole sits 1 cm over it) so it meets the ice without a seam.
        /// </summary>
        private void BuildRim(Material mat)
        {
            const int seg = 56;
            // a mound of drilled-out ice heaped round the hole, as in photos of ice holes
            float[] d = { -0.01f, 0.01f, 0.04f, 0.09f, 0.16f, 0.25f, 0.34f, 0.44f, 0.52f };
            float[] h = { 0.03f, 0.075f, 0.105f, 0.11f, 0.085f, 0.05f, 0.022f, 0.004f, -0.022f };
            int n = d.Length;
            var verts = new Vector3[seg * n]; var uvs = new Vector2[seg * n];
            for (int j = 0; j < seg; j++)
            {
                float th = 2f * Mathf.PI * j / seg;
                float wob = 0.025f * Mathf.Sin(th * 5f + 1.3f) + 0.015f * Mathf.Sin(th * 11f + 0.4f);
                for (int i = 0; i < n; i++)
                {
                    float r = WaterRadius + d[i] * (1f + 2.5f * wob * Mathf.Max(0f, d[i]) / 0.52f);
                    // lumpy, as heaped chips are: bumps round the ring, bigger on the high part
                    float lump = 0.018f * Mathf.Sin(th * 7f + i * 1.3f) + 0.012f * Mathf.Sin(th * 13f + i * 2.1f) + 0.008f * Mathf.Sin(th * 23f + 0.5f);
                    float y = h[i] + (d[i] > 0f && d[i] < 0.44f ? lump * Mathf.Clamp01(h[i] / 0.06f) : 0f);
                    var v = new Vector3(r * Mathf.Cos(th), y, r * Mathf.Sin(th));
                    verts[j * n + i] = v; uvs[j * n + i] = new Vector2(v.x, v.z) * 0.5f;
                }
            }
            var tris = new List<int>();
            for (int j = 0; j < seg; j++)
            {
                int a = j * n, b = ((j + 1) % seg) * n;
                for (int i = 0; i < n - 1; i++)   // (wound to face up)
                {
                    tris.Add(a + i); tris.Add(b + i); tris.Add(a + i + 1);
                    tris.Add(a + i + 1); tris.Add(b + i); tris.Add(b + i + 1);
                }
            }
            var mesh = new Mesh { name = "vdw_ice_hole_rim", vertices = verts, uv = uvs, triangles = tris.ToArray() };
            mesh.RecalculateNormals();
            if (mesh.normals[n + 2].y < 0f) { tris.Reverse(); mesh.triangles = tris.ToArray(); mesh.RecalculateNormals(); }
            mesh.RecalculateTangents(); mesh.RecalculateBounds();
            var g = new GameObject("vdw_rim");
            g.transform.SetParent(transform, false);
            g.AddComponent<MeshFilter>().sharedMesh = mesh;
            g.AddComponent<MeshRenderer>().sharedMaterial = mat;
        }

        private void Update()
        {
            if (_nview == null || !_nview.IsValid() || ZNet.instance == null) return;
            // the ice not there yet when the hole loaded: try again for a while
            if (!_cut && _cutTries < 8f && Time.time >= _nextCutTry) { _nextCutTry = Time.time + 1f; _cutTries += 1f; TryCut(); }
            float made = _nview.GetZDO().GetFloat("vdw_made", 0f);
            float age = Now - made;
            // the water skins over as it refreezes: new ice closing in over the last two minutes
            float skin = Mathf.Clamp01((age - (IceFishing.RefreezeSeconds - 120f)) / 120f);
            if (_skin != null && _skinRenderer != null)
            {
                _skinRenderer.enabled = skin > 0f;
                float d = WaterRadius * 2f * Mathf.Sqrt(skin);
                _skin.localScale = new Vector3(d, 0.004f, d);
            }
            if (made > 0f && age > IceFishing.RefreezeSeconds && _nview.IsOwner()) ZNetScene.instance.Destroy(gameObject);
        }
    }
}
