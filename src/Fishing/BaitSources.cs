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
    /// Where bait comes from in the world, so only baits with no natural source need recipes:
    ///   worms  - "wriggling soil" pickables wherever red mushrooms grow, regrowing over time
    ///   grubs  - sometimes inside a log when it's chopped up
    ///   leeches - dropped by swamp leeches
    ///   flies  - buzzing along shorelines on dry days; walk up and catch them (see FlySwarm)
    ///   minnows, baitfish, shrimp - caught as small fish (CatchBait in Fish.json)
    /// </summary>
    internal static class BaitSources
    {
        private const string WormMoundName = "VDW_Pickable_Worm";
        private const float GrubChance = 0.2f; // chance a chopped log turns up grubs

        public static void Register()
        {
            try { RegisterWormMounds(); }
            catch (Exception ex) { Plugin.Log.LogError($"Bait sources: worm mounds failed ({ex.Message})."); }

            try { AddLeechDrop(); }
            catch (Exception ex) { Plugin.Log.LogError($"Bait sources: leech drop failed ({ex.Message})."); }
        }

        private static GameObject? BaitPrefab(string id) => ContentRegistry.BaitItems.TryGetValue(id, out var p) ? p : null;

        public static GameObject? WormBait => BaitPrefab("worm");

        /// <summary>
        /// A clone of vanilla flint on the ground, turned into worms. Placed by world generation, so it appears in
        /// areas generated after installing (not in already-explored ground).
        /// </summary>
        private static void RegisterWormMounds()
        {
            var worm = BaitPrefab("worm");
            // Registered even when mounds are switched off, so mounds already in the world stay valid.
            if (worm == null) return;

            string basePrefab = PrefabManager.Instance.GetPrefab("Pickable_Flint") != null ? "Pickable_Flint" : "Pickable_Stone";
            var prefab = PrefabManager.Instance.CreateClonedPrefab(WormMoundName, basePrefab);
            var pickable = prefab.GetComponent<Pickable>();
            pickable.m_itemPrefab = worm;
            pickable.m_amount = 1; // rolled 1-3 on each pick, see MoundYieldPatch
            pickable.m_overrideName = Loc.Token("vdw_piece_worm_mound", "Wriggling soil");
            pickable.m_respawnTimeMinutes = 90f;

            bool custom = CustomModels.ApplyToPrefab(prefab, "pickable_worm");
            var anim = custom ? prefab.GetComponentInChildren<FishModelAnimator>(true) : null;

            if (anim != null)
            {
                // An animated mound (soil + a worm poking out of it, origin at ground level): the worm wriggles all the
                // time, and only the worm goes when picked - the soil stays until it regrows.
                anim.Driven = true;
                anim.Intensity = 0.15f;
                var wormMesh = anim.GetComponentInChildren<SkinnedMeshRenderer>(true);
                pickable.m_hideWhenPicked = wormMesh != null ? wormMesh.gameObject : anim.gameObject;
                GroundPose.FitCollider(prefab);
            }
            else
            {
                // Regrowing needs a child to hide while picked; move the visuals into one if they're on the root.
                pickable.m_hideWhenPicked = VisualsChild(prefab);

                if (custom)
                {
                    SettleOnGround(prefab);
                    GroundPose.FitCollider(prefab);
                }
            }

            // The game has to know the prefab to rebuild placed mounds from the save (and for other players).
            PrefabManager.Instance.AddPrefab(prefab);

            _wormMound = prefab;
            ZoneManager.OnVanillaVegetationAvailable -= AddWormMoundsLikeMushrooms;
            ZoneManager.OnVanillaVegetationAvailable += AddWormMoundsLikeMushrooms;
            // A server's mound settings arrive after the world is set up; redo the rules with them.
            SynchronizationManager.OnConfigurationSynchronized -= OnServerSettings;
            SynchronizationManager.OnConfigurationSynchronized += OnServerSettings;
        }

        private static GameObject? _wormMound;

        private static void OnServerSettings(object sender, Jotunn.Utils.ConfigurationSynchronizationEventArgs e) => AddWormMoundsLikeMushrooms();

        /// <summary>
        /// Worm mounds grow wherever and as often as vanilla red mushrooms do: every vanilla mushroom placement
        /// rule is copied for the mound (biomes, forest, altitude, density, groups). Runs each time a world's
        /// vegetation is set up, before any new ground is generated.
        /// </summary>
        private static void AddWormMoundsLikeMushrooms()
        {
            var zones = ZoneSystem.instance;
            if (zones == null || _wormMound == null) return;
            zones.m_vegetation.RemoveAll(v => v.m_name != null && v.m_name.StartsWith(WormMoundName));
            if (!VdwConfig.SpawnWormMounds.Value) return;

            var mushrooms = zones.m_vegetation.Where(v => v.m_prefab != null && v.m_prefab.name == "Pickable_Mushroom").ToList();
            foreach (var mushroom in mushrooms)
            {
                var veg = new ZoneSystem.ZoneVegetation();
                foreach (var field in typeof(ZoneSystem.ZoneVegetation).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance))
                    field.SetValue(veg, field.GetValue(mushroom));

                veg.m_name = WormMoundName;
                veg.m_prefab = _wormMound;
                veg.m_scaleMin = veg.m_scaleMax = 1f;
                // Lie along the slope of the ground rather than staying upright (and half floating) on a hillside.
                veg.m_chanceToUseGroundTilt = 1f;
                veg.m_randTilt = 0f;
                veg.m_groundOffset = 0f;
                ScaleDensity(veg, VdwConfig.WormMoundDensity.Value);
                zones.m_vegetation.Add(veg);
            }

            if (mushrooms.Count == 0)
                Plugin.Log.LogWarning("Bait sources: no vanilla mushroom placement found to copy; no worm mounds this world.");
        }

        /// <summary>A rule with m_max under 1 is a chance per zone; at 1 or more it's a count per zone.</summary>
        private static void ScaleDensity(ZoneSystem.ZoneVegetation veg, float density)
        {
            if (Mathf.Approximately(density, 1f) || density <= 0f) return;
            if (veg.m_max < 1f)
            {
                float chance = veg.m_max * density;
                if (chance < 1f) { veg.m_max = chance; return; }
                veg.m_min = 1f;
                veg.m_max = Mathf.Max(1f, chance);
                return;
            }
            veg.m_min = Mathf.Max(0f, veg.m_min * density);
            veg.m_max = Mathf.Max(1f, veg.m_max * density);
        }

        /// <summary>For "vdw_debug worms": what's around the player, and why flies or rain worms might not be out.</summary>
        public static string DescribeNearby()
        {
            var player = Player.m_localPlayer;
            if (player == null) return "No player.";
            var pos = player.transform.position;

            var mounds = UnityEngine.Object.FindObjectsByType<Pickable>(FindObjectsSortMode.None)
                .Where(p => p != null && p.name.StartsWith(WormMoundName))
                .Select(p => Vector3.Distance(pos, p.transform.position))
                .OrderBy(d => d).ToList();

            // Every mound in the save, loaded or not (single player / host only).
            var all = new List<ZDO>();
            int index = 0;
            if (ZDOMan.instance != null)
                while (!ZDOMan.instance.GetAllZDOsWithPrefabIterative(WormMoundName, all, ref index)) { }
            var nearestSaved = all.Count > 0 ? all.Min(z => Vector3.Distance(pos, z.GetPosition())) : -1f;

            string mound = (mounds.Count == 0
                ? "No worm mounds in loaded areas."
                : $"{mounds.Count} worm mound(s) loaded, nearest {mounds[0]:0} m away.")
                + (all.Count == 0
                    ? " None in this world's save yet (they only grow in ground generated since installing)."
                    : $" {all.Count} in the world in total, nearest {nearestSaved:0} m away.");

            var biome = WorldGenerator.instance != null ? WorldGenerator.instance.GetBiome(pos) : Heightmap.Biome.None;
            bool day = EnvMan.instance != null && EnvMan.IsDay();
            bool wet = EnvMan.instance != null && EnvMan.IsWet();
            return mound + $"\nBiome {biome}, {(day ? "day" : "night")}, {(wet ? "raining" : "dry")}. " +
                   $"Flies out: {FlySwarm.Count} (need dry weather and a shoreline within 25 m). Rain worms out: {RainWorms.Count} (need rain).";
        }

        /// <summary>
        /// The flint prefab this is cloned from keeps its model on a tilted, scaled child. Reset that so the mound
        /// lies flat, at its own size, centred, with its base just into the ground. Any extra copies of the model
        /// (flint can have more than one piece) are hidden.
        /// </summary>
        private static void SettleOnGround(GameObject prefab)
        {
            var filters = prefab.GetComponentsInChildren<MeshFilter>(true);
            if (filters.Length == 0 || filters[0].sharedMesh == null) return;

            var keep = filters[0];
            for (int i = 1; i < filters.Length; i++)
            {
                var r = filters[i].GetComponent<MeshRenderer>();
                if (r != null) r.enabled = false;
            }

            var t = keep.transform;
            t.rotation = prefab.transform.rotation;
            // A readable mesh already has its size baked in, so undo any scale the flint child carried.
            if (keep.sharedMesh.isReadable)
            {
                var parentScale = t.parent != null ? t.parent.lossyScale : Vector3.one;
                t.localScale = new Vector3(1f / parentScale.x, 1f / parentScale.y, 1f / parentScale.z);
            }

            var b = keep.sharedMesh.bounds;
            var s = t.lossyScale;
            t.position = prefab.transform.position + new Vector3(-b.center.x * s.x, -b.min.y * s.y + 0.01f, -b.center.z * s.z);
        }


        private static GameObject VisualsChild(GameObject prefab)
        {
            var rootFilter = prefab.GetComponent<MeshFilter>();
            var rootRenderer = prefab.GetComponent<MeshRenderer>();
            if (rootFilter == null || rootRenderer == null)
            {
                foreach (Transform child in prefab.transform)
                    if (child.GetComponentInChildren<Renderer>(true) != null) return child.gameObject;
            }

            var visual = new GameObject("visual");
            visual.transform.SetParent(prefab.transform, false);
            if (rootFilter != null && rootRenderer != null)
            {
                visual.AddComponent<MeshFilter>().sharedMesh = rootFilter.sharedMesh;
                visual.AddComponent<MeshRenderer>().sharedMaterials = rootRenderer.sharedMaterials;
                UnityEngine.Object.DestroyImmediate(rootRenderer);
                UnityEngine.Object.DestroyImmediate(rootFilter);
            }
            return visual;
        }

        private static void AddLeechDrop()
        {
            var leechBait = BaitPrefab("leech");
            var leech = PrefabManager.Instance.GetPrefab("Leech");
            var drops = leech != null ? leech.GetComponent<CharacterDrop>() : null;
            if (leechBait == null || drops == null) return;
            drops.m_drops.Add(new CharacterDrop.Drop { m_prefab = leechBait, m_amountMin = 1, m_amountMax = 2, m_chance = 0.6f, m_levelMultiplier = false });
        }

        /// <summary>
        /// Wriggling soil turns up 1 worm usually, 2 sometimes and 3 rarely; in the rain, one more (up to 3).
        /// </summary>
        [HarmonyPatch(typeof(Pickable), "RPC_Pick")]
        private static class MoundYieldPatch
        {
            private static void Prefix(Pickable __instance, out int __state)
            {
                __state = __instance.m_amount;
                if (!__instance.name.StartsWith(WormMoundName)) return;

                float roll = UnityEngine.Random.value;
                int worms = roll < 0.08f ? 3 : roll < 0.35f ? 2 : 1;
                if (RainWorms.Raining) worms = Mathf.Min(3, worms + 1);
                __instance.m_amount = worms;
            }

            private static void Postfix(Pickable __instance, int __state) => __instance.m_amount = __state;
        }

        /// <summary>Chopping a log sometimes turns up grubs. Runs on the log's owner only, like its normal drops.</summary>
        [HarmonyPatch(typeof(TreeLog), "Destroy")]
        private static class TreeLogGrubPatch
        {
            private static void Postfix(TreeLog __instance)
            {
                if (UnityEngine.Random.value >= GrubChance) return;
                var grub = BaitPrefab("grub");
                if (grub == null) return;

                var pos = __instance.transform.position + Vector3.up * 0.5f + UnityEngine.Random.insideUnitSphere * 0.5f;
                var drop = UnityEngine.Object.Instantiate(grub, pos, Quaternion.Euler(0f, UnityEngine.Random.Range(0f, 360f), 0f)).GetComponent<ItemDrop>();
                if (drop != null) drop.SetStack(UnityEngine.Random.Range(1, 3));
            }
        }
    }

    /// <summary>
    /// Flies along the shore near the local player on dry days. Each player gets their own (nothing is
    /// networked); walk up and press the use key to catch one as fly bait.
    /// </summary>
    internal static class FlySwarm
    {
        private const int MaxFlies = 8;
        private static readonly List<FlyCritter> Flies = new();
        private static float _nextSpawn;
        private static float _waterLevel = 30f;

        public static int Count => Flies.Count(f => f != null);

        private static readonly Heightmap.Biome FlyBiomes =
            Heightmap.Biome.Meadows | Heightmap.Biome.BlackForest | Heightmap.Biome.Swamp | Heightmap.Biome.Plains;

        public static void Update()
        {
            Flies.RemoveAll(f => f == null);
            var player = Player.m_localPlayer;
            if (player == null || !VdwConfig.Enabled.Value || !VdwConfig.SpawnFlies.Value)
            {
                Clear();
                return;
            }
            if (Time.time < _nextSpawn || Flies.Count >= MaxFlies) return;
            _nextSpawn = Time.time + UnityEngine.Random.Range(5f, 10f);

            if (EnvMan.instance == null || EnvMan.IsWet() || WorldGenerator.instance == null || ZoneSystem.instance == null) return;
            if ((WorldGenerator.instance.GetBiome(player.transform.position) & FlyBiomes) == 0) return;

            _waterLevel = ZoneSystem.instance.m_waterLevel;
            for (int tries = 0; tries < 24; tries++)
            {
                Vector2 r = UnityEngine.Random.insideUnitCircle.normalized * UnityEngine.Random.Range(5f, 25f);
                var p = player.transform.position + new Vector3(r.x, 0f, r.y);
                float ground = ZoneSystem.instance.GetGroundHeight(p);
                // Shoreline only: ground from just under the water to a few metres above it.
                if (ground < _waterLevel - 0.5f || ground > _waterLevel + 3f) continue;

                // A little cloud of them, so there's something to spot. Without a fly model it's Valheim's own
                // flies effect (fireflies at night), with the catchable flies inside it.
                float baseY = Mathf.Max(ground, _waterLevel) + UnityEngine.Random.Range(0.6f, 1.3f);
                var center = new Vector3(p.x, baseY, p.z);
                var cloud = FlyCritter.HasCustomModel ? null : FlyCloud.Create(center, night: !EnvMan.IsDay());
                int count = Mathf.Min(UnityEngine.Random.Range(2, 5), MaxFlies - Flies.Count);
                for (int i = 0; i < count; i++)
                {
                    var offset = UnityEngine.Random.insideUnitSphere * 0.6f;
                    Flies.Add(FlyCritter.Create(center + new Vector3(offset.x, offset.y * 0.5f, offset.z), cloud));
                }
                break;
            }
        }

        public static void Clear()
        {
            foreach (var f in Flies) if (f != null) UnityEngine.Object.Destroy(f.gameObject);
            Flies.Clear();
        }
    }

    /// <summary>
    /// Valheim's own ambient flies effect (or fireflies at night) around a swarm, with its wing buzz. It thins out
    /// as flies are caught or fly off, and fades away with the last one.
    /// </summary>
    internal sealed class FlyCloud : MonoBehaviour
    {
        private static GameObject? _flies, _fireflies;
        private static AudioClip? _wings;
        private static bool _loaded;

        private readonly List<FlyCritter> _members = new();
        private int _started;
        private ParticleSystem[] _systems = Array.Empty<ParticleSystem>();
        private float[] _rates = Array.Empty<float>();
        private AudioSource? _buzz;
        private float _buzzVolume;

        /// <summary>Null if the vanilla effect can't be loaded; the flies then show the built-in fly instead.</summary>
        public static FlyCloud? Create(Vector3 pos, bool night)
        {
            LoadAssets();
            var fx = night && _fireflies != null ? _fireflies : _flies;
            if (fx == null) return null;

            var go = new GameObject("VDW_FlyCloud");
            go.transform.position = pos;
            bool netInit = ZNetView.m_forceDisableInit;
            ZNetView.m_forceDisableInit = true; // a local copy only, never networked
            try
            {
                var effect = Instantiate(fx, pos, Quaternion.identity, go.transform);
                foreach (var timer in effect.GetComponentsInChildren<TimedDestruction>(true)) Destroy(timer);
            }
            finally { ZNetView.m_forceDisableInit = netInit; }

            var cloud = go.AddComponent<FlyCloud>();
            cloud._systems = go.GetComponentsInChildren<ParticleSystem>(true);
            foreach (var ps in cloud._systems) FitToSwarm(ps);
            cloud._rates = cloud._systems.Select(ps => ps.emission.rateOverTimeMultiplier).ToArray();

            if (_wings != null && fx == _flies)
            {
                var buzz = go.AddComponent<AudioSource>();
                buzz.clip = _wings;
                buzz.loop = true;
                buzz.spatialBlend = 1f;
                buzz.rolloffMode = AudioRolloffMode.Linear;
                buzz.minDistance = 1f;
                buzz.maxDistance = 12f;
                buzz.volume = cloud._buzzVolume = 0.5f;
                buzz.outputAudioMixerGroup = FishingFx.SfxGroup;
                buzz.time = UnityEngine.Random.Range(0f, _wings.length);
                buzz.Play();
                cloud._buzz = buzz;
            }
            return cloud;
        }

        /// <summary>Box the swarm fills (m). Vanilla's effect spreads over 4 x 2 x 4 m, far wider than the flies you can catch.</summary>
        private static readonly Vector3 SwarmSize = new Vector3(1.4f, 0.9f, 1.4f);

        /// <summary>
        /// Packs the vanilla effect into the swarm's box, at about the same density of specks, a little bigger so
        /// they read as flies.
        /// </summary>
        private static void FitToSwarm(ParticleSystem ps)
        {
            var shape = ps.shape;
            if (!shape.enabled) return;
            Vector3 old = shape.scale;
            float volume = Mathf.Max(0.01f, old.x * old.y * old.z);
            shape.scale = SwarmSize;
            float fraction = Mathf.Clamp(SwarmSize.x * SwarmSize.y * SwarmSize.z / volume, 0.15f, 1f);

            var emission = ps.emission;
            emission.rateOverTimeMultiplier *= fraction * 2.5f;
            var main = ps.main;
            main.startSizeMultiplier *= 1.5f;
            ps.Clear();
            ps.Play(true);
        }

        private static void LoadAssets()
        {
            if (_loaded) return;
            _loaded = true;
            _flies = LoadVanilla<GameObject>("Flies");
            _fireflies = LoadVanilla<GameObject>("FireFlies");
            _wings = LoadVanilla<AudioClip>("Insect_Wings");
        }

        private static T? LoadVanilla<T>(string name) where T : UnityEngine.Object
        {
            try
            {
                var asset = PrefabManager.Cache.GetPrefab<T>(name);
                if (asset != null) return asset;
                var reference = AssetManager.Instance.GetSoftReference<T>(name);
                if (!reference.IsValid) return null;
                reference.Load(); // held for the session
                return reference.Asset;
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Flies: couldn't load vanilla '{name}' ({ex.Message}).");
                return null;
            }
        }

        public void Add(FlyCritter fly)
        {
            _members.Add(fly);
            _started = _members.Count;
        }

        public void Remove(FlyCritter fly)
        {
            if (this == null || !_members.Remove(fly)) return;
            float left = _started > 0 ? (float)_members.Count / _started : 0f;
            for (int i = 0; i < _systems.Length; i++)
            {
                if (_systems[i] == null) continue;
                var emission = _systems[i].emission;
                emission.rateOverTimeMultiplier = _rates[i] * left;
                if (_members.Count == 0) _systems[i].Stop(true, ParticleSystemStopBehavior.StopEmitting);
            }
            if (_buzz != null) _buzz.volume = _buzzVolume * left;
            if (_members.Count == 0) Destroy(gameObject, 4f); // let the last particles fade out
        }

        private void Update()
        {
            var player = Player.m_localPlayer;
            if (player == null || Vector3.Distance(player.transform.position, transform.position) > 60f) Destroy(gameObject);
        }
    }

    internal sealed class FlyCritter : MonoBehaviour, Hoverable, Interactable
    {
        private Vector3 _anchor;
        private Vector3 _target;
        private float _nextTarget;
        private float _dieAt;
        private bool _fleeing;

        private static bool? _hasModel;

        /// <summary>True once a fly (or bait_fly) model is in the Models folder: flies then show it one by one.</summary>
        public static bool HasCustomModel => _hasModel ??=
            CustomModels.GetAnimated("bait_fly") != null ||
            CustomModels.TryGetCustom("fly", out _, out _) || CustomModels.TryGetCustom("bait_fly", out _, out _);

        /// <param name="cloud">The vanilla flies effect this fly belongs to; the fly itself is then invisible.</param>
        public static FlyCritter Create(Vector3 pos, FlyCloud? cloud = null)
        {
            var go = new GameObject("VDW_Fly");
            go.transform.position = pos;
            int layer = LayerMask.NameToLayer("item");
            if (layer >= 0) go.layer = layer;

            var fly = go.AddComponent<FlyCritter>();
            fly._cloud = cloud;
            if (cloud != null)
            {
                cloud.Add(fly);
            }
            else if (CustomModels.GetAnimated("bait_fly") is GameObject animated)
            {
                // A rigged fly hovers with its own Swim clip (wings beating) and buzzes frantically (Thrash) as it flees.
                fly._anim = CustomModels.SpawnAnimated(animated, go.transform);
                fly._anim.Driven = true;
                fly._anim.Intensity = 0.15f;
            }
            else if (CustomModels.TryGetCustom("fly", out var mesh, out var mat) || CustomModels.TryGetCustom("bait_fly", out mesh, out mat))
            {
                var body = new GameObject("body");
                body.AddComponent<MeshFilter>().sharedMesh = mesh;
                body.AddComponent<MeshRenderer>().sharedMaterial = mat;
                body.transform.SetParent(go.transform, false);
            }
            else
            {
                fly.BuildDefaultBody();
            }

            // A generous invisible collider so it's easy to aim at.
            var col = go.AddComponent<SphereCollider>();
            col.radius = cloud != null ? 0.6f : 0.45f; // inside a cloud, aiming anywhere at it catches one

            fly._anchor = fly._target = pos;
            fly._dieAt = Time.time + UnityEngine.Random.Range(90f, 150f);
            return fly;
        }

        private void Update()
        {
            var player = Player.m_localPlayer;
            if (player == null || Time.time > _dieAt || Vector3.Distance(player.transform.position, transform.position) > 45f)
            {
                Destroy(gameObject);
                return;
            }

            // Spooked: running or swinging close by sends it off; walking right up to it only rarely does; creeping
            // up (sneaking) never. You have to get within reach (about 2.5 m) to catch one.
            if (!_fleeing)
            {
                float dist = Vector3.Distance(player.transform.position, transform.position);
                bool loud = player.IsRunning() || player.InAttack();
                if ((loud && dist < 3f) || (!player.IsCrouching() && dist < 1.5f && UnityEngine.Random.value < 0.05f * Time.deltaTime))
                    FlyAway();
            }

            if (Time.time >= _nextTarget)
            {
                _target = _fleeing ? transform.position + (transform.position - player.transform.position).normalized * 6f + Vector3.up * 3f
                                   : _anchor + UnityEngine.Random.insideUnitSphere * (_cloud != null ? 0.4f : 0.8f);
                _nextTarget = Time.time + (_fleeing ? 10f : UnityEngine.Random.Range(0.4f, 1.1f));
            }

            float speed = _fleeing ? 8f : 1.6f;
            var next = Vector3.MoveTowards(transform.position, _target, speed * Time.deltaTime);
            next.y += Mathf.Sin(Time.time * 40f) * 0.004f; // wing buzz
            // Face where it's heading, level - hovering in place it only bobs up and down, and facing straight up (or a
            // near-zero direction) makes a broken rotation that Unity complains about every frame.
            var heading = next - transform.position;
            heading.y = 0f;
            if (heading.sqrMagnitude > 1e-6f) transform.rotation = Quaternion.LookRotation(heading.normalized, Vector3.up);
            transform.position = next;
        }

        private Transform? _wingL, _wingR;
        private FlyCloud? _cloud;
        private FishModelAnimator? _anim;

        private void OnDestroy() => _cloud?.Remove(this);

        /// <summary>No fly model: a dark body with two glassy wings that blur up and down.</summary>
        internal void BuildDefaultBody()
        {
            // Shared by every fly, so spawning them doesn't pile up materials.
            _bodyMat ??= Mat(new Color(0.06f, 0.07f, 0.05f));
            _eyeMat ??= Mat(new Color(0.35f, 0.08f, 0.05f));
            _wingMat ??= Mat(new Color(0.85f, 0.9f, 0.95f, 0.45f));

            var body = Part(PrimitiveType.Capsule, new Vector3(0.022f, 0.022f, 0.045f), Vector3.zero, _bodyMat);
            body.localRotation = Quaternion.Euler(90f, 0f, 0f);
            Part(PrimitiveType.Sphere, new Vector3(0.02f, 0.018f, 0.018f), new Vector3(0f, 0.002f, 0.026f), _eyeMat);
            _wingL = Part(PrimitiveType.Quad, new Vector3(0.035f, 0.018f, 1f), new Vector3(-0.02f, 0.012f, -0.004f), _wingMat);
            _wingR = Part(PrimitiveType.Quad, new Vector3(0.035f, 0.018f, 1f), new Vector3(0.02f, 0.012f, -0.004f), _wingMat);
        }

        private static Material? _bodyMat, _eyeMat, _wingMat;

        private static Material Mat(Color c) =>
            new Material(Shader.Find("Sprites/Default") ?? Shader.Find("Standard")) { color = c };

        private Transform Part(PrimitiveType type, Vector3 scale, Vector3 pos, Material mat)
        {
            var part = GameObject.CreatePrimitive(type);
            DestroyImmediate(part.GetComponent<Collider>());
            part.GetComponent<Renderer>().sharedMaterial = mat;
            part.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            part.transform.SetParent(transform, false);
            part.transform.localPosition = pos;
            part.transform.localScale = scale;
            return part.transform;
        }

        private void LateUpdate()
        {
            if (_wingL == null || _wingR == null) return;
            float flap = Mathf.Sin(Time.time * 90f) * 35f;
            _wingL.localRotation = Quaternion.Euler(90f, 0f, 20f + flap);
            _wingR.localRotation = Quaternion.Euler(90f, 0f, -20f - flap);
        }

        private void FlyAway()
        {
            _fleeing = true;
            _nextTarget = 0f;
            if (_anim != null) _anim.Intensity = 1f;
            _dieAt = Mathf.Min(_dieAt, Time.time + 1.5f);
        }

        public string GetHoverText() =>
            _fleeing ? "" : Localization.instance.Localize("Fly\n[<color=yellow><b>$KEY_Use</b></color>] Catch");

        public string GetHoverName() => "Fly";

        public float GetHoverOffset() => 0f;

        public bool Interact(Humanoid user, bool hold, bool alt)
        {
            if (hold || _fleeing || !(user is Player player)) return false;

            if (UnityEngine.Random.value > 0.7f)
            {
                player.Message(MessageHud.MessageType.Center, "Missed! It got away.");
                FlyAway();
                return true;
            }

            var bait = ContentRegistry.BaitItems.TryGetValue("fly", out var p) ? p : null;
            var data = bait != null ? bait.GetComponent<ItemDrop>()?.m_itemData : null;
            if (data == null) return false;

            if (player.GetInventory().CanAddItem(data, 1))
                player.GetInventory().AddItem(bait!.name, 1, 1, 0, 0L, "", false);
            else
                Drops.Spawn(bait!.GetComponent<ItemDrop>(), 1, transform.position);

            player.Message(MessageHud.MessageType.TopLeft, $"Caught a fly: {Loc.Text(data.m_shared.m_name)}", 1, data.GetIcon());
            Destroy(gameObject);
            return true;
        }

        public bool UseItem(Humanoid user, ItemDrop.ItemData item) => false;
    }

    /// <summary>
    /// When it rains, worms come up out of the ground around the local player, like real worms after a downpour.
    /// Each player gets their own (nothing is networked); they wriggle for a while and burrow back down when the
    /// rain stops. Walk up and use one to pick it up as worm bait.
    /// </summary>
    internal static class RainWorms
    {
        private const int MaxWorms = 6;
        private static readonly int GroundMask = LayerMask.GetMask("Default", "static_solid", "terrain", "piece");
        private static readonly List<WormCritter> Worms = new();
        private static float _nextSpawn;

        private static readonly Heightmap.Biome WormBiomes =
            Heightmap.Biome.Meadows | Heightmap.Biome.BlackForest | Heightmap.Biome.Swamp | Heightmap.Biome.Plains | Heightmap.Biome.Mistlands;

        public static int Count => Worms.Count(w => w != null);

        public static bool Raining => EnvMan.instance != null && EnvMan.IsWet();

        public static void Update()
        {
            Worms.RemoveAll(w => w == null);
            var player = Player.m_localPlayer;
            if (player == null || !VdwConfig.Enabled.Value || !VdwConfig.RainWorms.Value)
            {
                Clear();
                return;
            }
            if (Time.time < _nextSpawn || Worms.Count >= MaxWorms) return;
            _nextSpawn = Time.time + UnityEngine.Random.Range(3f, 7f);

            if (!Raining || WorldGenerator.instance == null || ZoneSystem.instance == null) return;
            if (BaitSources.WormBait == null) return;
            if ((WorldGenerator.instance.GetBiome(player.transform.position) & WormBiomes) == 0) return;

            float water = ZoneSystem.instance.m_waterLevel;
            for (int tries = 0; tries < 10; tries++)
            {
                Vector2 r = UnityEngine.Random.insideUnitCircle.normalized * UnityEngine.Random.Range(3f, 16f);
                var top = player.transform.position + new Vector3(r.x, 30f, r.y);
                if (!Physics.Raycast(top, Vector3.down, out var hit, 80f, GroundMask)) continue;
                // Bare ground only: not on floors, rocks or under a roof, and not in water or on a cliff.
                if (hit.collider.GetComponentInParent<Heightmap>() == null) continue;
                if (hit.point.y < water + 0.3f || hit.normal.y < 0.8f) continue;

                Worms.Add(WormCritter.Create(hit.point, hit.normal));
                break;
            }
        }

        public static void Clear()
        {
            foreach (var w in Worms) if (w != null) UnityEngine.Object.Destroy(w.gameObject);
            Worms.Clear();
        }
    }

    internal sealed class WormCritter : MonoBehaviour, Hoverable, Interactable
    {
        private const float Depth = 0.06f;

        private Vector3 _ground;
        private Vector3 _normal;
        private float _bornAt;
        private float _burrowAt;
        private float _burrowStart = -1f;
        private float _heading;
        private Transform[]? _segments;
        private Transform? _model;
        private bool _animated; // a rigged model wriggles itself; no extra sway

        public static WormCritter Create(Vector3 ground, Vector3 normal)
        {
            var go = new GameObject("VDW_RainWorm");
            int layer = LayerMask.NameToLayer("item");
            if (layer >= 0) go.layer = layer;

            var worm = go.AddComponent<WormCritter>();
            worm._ground = ground;
            worm._normal = normal;
            worm._heading = UnityEngine.Random.Range(0f, 360f);
            worm._bornAt = Time.time;
            worm._burrowAt = Time.time + UnityEngine.Random.Range(60f, 120f);

            if (CustomModels.GetAnimated("bait_worm") is GameObject animated)
            {
                // A rigged worm wriggles with its own Swim clip as it crawls.
                var anim = CustomModels.SpawnAnimated(animated, go.transform);
                anim.Driven = true;
                anim.Intensity = 0.15f;
                // The model's origin is its middle: lift it so it lies on the ground instead of half under it.
                var smr = anim.GetComponentInChildren<SkinnedMeshRenderer>();
                if (smr != null && smr.sharedMesh != null)
                    anim.transform.localPosition = Vector3.up * -smr.sharedMesh.bounds.min.y * smr.transform.lossyScale.y;
                worm._model = anim.transform;
                worm._animated = true;
            }
            else if (CustomModels.TryGetCustom("bait_worm", out var mesh, out var mat))
            {
                var body = new GameObject("body");
                body.AddComponent<MeshFilter>().sharedMesh = mesh;
                body.AddComponent<MeshRenderer>().sharedMaterial = mat;
                body.transform.SetParent(go.transform, false);
                // Sits on the ground at the model's own size.
                var b = mesh.bounds;
                body.transform.localPosition = new Vector3(-b.center.x, -b.min.y, -b.center.z);
                worm._model = body.transform;
            }
            else
            {
                worm.BuildDefaultBody();
            }

            var col = go.AddComponent<SphereCollider>();
            col.radius = 0.2f;
            col.center = new Vector3(0f, 0.05f, 0f);

            worm.Place(0f);
            return worm;
        }

        private static Material? _mat; // shared by every worm

        /// <summary>No worm model: a row of pinkish-brown beads that wriggles.</summary>
        private void BuildDefaultBody()
        {
            if (_mat == null)
            {
                _mat = new Material(Shader.Find("Standard")) { color = new Color(0.55f, 0.3f, 0.27f) };
                if (_mat.HasProperty("_Glossiness")) _mat.SetFloat("_Glossiness", 0.7f); // wet sheen
            }
            _segments = new Transform[7];
            for (int i = 0; i < _segments.Length; i++)
            {
                var seg = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                DestroyImmediate(seg.GetComponent<Collider>());
                seg.GetComponent<Renderer>().sharedMaterial = _mat;
                seg.transform.SetParent(transform, false);
                float taper = 1f - Mathf.Abs(i - 2.5f) / 6f;
                seg.transform.localScale = new Vector3(0.022f, 0.018f, 0.03f) * taper;
                _segments[i] = seg.transform;
            }
        }

        private void Place(float rise)
        {
            // Lie along the ground, poking up out of it as it emerges.
            var rot = Quaternion.FromToRotation(Vector3.up, _normal) * Quaternion.Euler(0f, _heading, 0f);
            transform.SetPositionAndRotation(_ground + _normal * Mathf.Lerp(-Depth, 0f, rise), rot);
        }

        private void Update()
        {
            var player = Player.m_localPlayer;
            if (player == null || Vector3.Distance(player.transform.position, transform.position) > 45f)
            {
                Destroy(gameObject);
                return;
            }

            // Burrows back down once the rain stops or it's been up a while.
            if (_burrowStart < 0f && (Time.time > _burrowAt || !RainWorms.Raining)) _burrowStart = Time.time;

            float rise = Mathf.Clamp01((Time.time - _bornAt) / 1.5f);
            if (_burrowStart >= 0f)
            {
                rise = Mathf.Min(rise, 1f - (Time.time - _burrowStart) / 2f);
                if (rise <= 0f)
                {
                    Destroy(gameObject);
                    return;
                }
            }

            // A slow crawl, turning now and then.
            _heading += Mathf.Sin(Time.time * 0.7f + _bornAt) * 20f * Time.deltaTime;
            var forward = Quaternion.FromToRotation(Vector3.up, _normal) * Quaternion.Euler(0f, _heading, 0f) * Vector3.forward;
            _ground += forward * 0.015f * Time.deltaTime * (0.5f + 0.5f * Mathf.Sin(Time.time * 3f));
            Place(rise);

            float t = Time.time * 4f + _bornAt;
            if (_segments != null)
            {
                for (int i = 0; i < _segments.Length; i++)
                {
                    float z = (i - (_segments.Length - 1) / 2f) * 0.02f;
                    _segments[i].localPosition = new Vector3(Mathf.Sin(t - i * 0.9f) * 0.012f, 0.008f, z);
                }
            }
            else if (_model != null && !_animated)
            {
                _model.localRotation = Quaternion.Euler(0f, Mathf.Sin(t) * 12f, 0f);
            }
        }

        private static string Name =>
            BaitSources.WormBait != null ? Loc.Text(BaitSources.WormBait.GetComponent<ItemDrop>().m_itemData.m_shared.m_name) : "Worm";

        public string GetHoverText() =>
            _burrowStart >= 0f ? "" : Localization.instance.Localize(Name + "\n[<color=yellow><b>$KEY_Use</b></color>] $inventory_pickup");

        public string GetHoverName() => Name;

        public float GetHoverOffset() => 0f;

        public bool Interact(Humanoid user, bool hold, bool alt)
        {
            if (hold || _burrowStart >= 0f || !(user is Player player)) return false;
            var bait = BaitSources.WormBait;
            var data = bait != null ? bait.GetComponent<ItemDrop>()?.m_itemData : null;
            if (data == null) return false;

            if (player.GetInventory().CanAddItem(data, 1))
                player.GetInventory().AddItem(bait!.name, 1, 1, 0, 0L, "", false);
            else
                Drops.Spawn(bait!.GetComponent<ItemDrop>(), 1, transform.position);

            player.Message(MessageHud.MessageType.TopLeft, "$msg_added " + Name, 1, data.GetIcon());
            Destroy(gameObject);
            return true;
        }

        public bool UseItem(Humanoid user, ItemDrop.ItemData item) => false;
    }
}
