using HarmonyLib;
using Jotunn.Managers;
using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Chum isn't drunk: using a chum bucket sets it down on the ground in front of you. The bucket is a networked
    /// object everyone sees, and the water within its radius is chummed for anyone fishing there, until it runs out
    /// (the end time is kept on the bucket, so every player sees it go at the same moment) and sinks away.
    /// Only on ground with water close enough for it to reach.
    /// </summary>
    internal static class ChumBuckets
    {
        private static readonly int GroundMask = LayerMask.GetMask("Default", "static_solid", "terrain", "piece");
        private static readonly Dictionary<string, GameObject> Placed = new();       // chum id -> placed prefab
        private static readonly Dictionary<string, BuffDefinition> Defs = new();     // placed prefab name -> chum
        internal static readonly List<ChumBucket> Active = new();
        internal const string EndKey = "vdw_chum_end";

        public static string PlacedName(string id) => "VDW_ChumPlaced_" + id;

        public static bool IsChum(ItemDrop.ItemData? item) =>
            item?.m_shared?.m_consumeStatusEffect is SE_FishingBuff se &&
            FishingBuffs.ByStatusName(se.m_name) is BuffDefinition def && def.Kind.Equals("Chum", System.StringComparison.OrdinalIgnoreCase);

        public static BuffDefinition? DefFor(string prefabName) => Defs.TryGetValue(prefabName, out var d) ? d : null;

        /// <summary>
        /// The placed bucket: a copy of the chum item (its model, contents and garnish) with no pickup or physics, kept
        /// in the world and synced like any placed object.
        /// </summary>
        public static void RegisterPlaced(BuffDefinition b, GameObject itemPrefab)
        {
            var go = PrefabManager.Instance.CreateClonedPrefab(PlacedName(b.Id), itemPrefab);
            var attach = go.transform.Find("attach");
            if (attach != null) Object.DestroyImmediate(attach.gameObject);
            foreach (var c in go.GetComponentsInChildren<MonoBehaviour>(true))
                if (c is ItemDrop || c is ZSyncTransform || c is Floating || c is global::Fish) Object.DestroyImmediate(c);
            foreach (var rb in go.GetComponentsInChildren<Rigidbody>(true)) Object.DestroyImmediate(rb);
            var nview = go.GetComponent<ZNetView>() ?? go.AddComponent<ZNetView>();
            nview.m_persistent = true;
            nview.m_syncInitialScale = false;
            go.AddComponent<ChumBucket>();
            PrefabManager.Instance.AddPrefab(go);
            Placed[b.Id] = go;
            Defs[go.name] = b;
        }

        [HarmonyPatch(typeof(Player), nameof(Player.ConsumeItem))]
        private static class ConsumePatch
        {
            private static bool Prefix(Player __instance, Inventory inventory, ItemDrop.ItemData item, ref bool __result)
            {
                if (!IsChum(item)) return true;
                __result = SetDown(__instance, inventory, item);
                return false; // never drunk
            }
        }

        private static bool SetDown(Player player, Inventory inventory, ItemDrop.ItemData item)
        {
            var se = (SE_FishingBuff)item.m_shared.m_consumeStatusEffect;
            var def = FishingBuffs.ByStatusName(se.m_name)!;
            if (!Placed.TryGetValue(def.Id, out var prefab)) return false;

            // A spot on the ground just in front.
            var fwd = player.transform.forward; fwd.y = 0f; fwd.Normalize();
            var top = player.transform.position + fwd * 1.1f + Vector3.up * 2f;
            if (!Physics.Raycast(top, Vector3.down, out var hit, 4f, GroundMask) || hit.normal.y < 0.6f)
            {
                player.Message(MessageHud.MessageType.Center, "No flat ground here to set it down.");
                return false;
            }
            if (Floating.GetLiquidLevel(hit.point) > hit.point.y + 0.05f)
            {
                player.Message(MessageHud.MessageType.Center, "Set it down on the bank, not in the water.");
                return false;
            }
            float water = ZoneSystem.instance != null ? ZoneSystem.instance.m_waterLevel : 30f;
            if (!WaterWithin(hit.point, def.Radius * 0.8f, water))
            {
                player.Message(MessageHud.MessageType.Center, "There's no water close enough for the chum to reach.");
                return false;
            }

            var bucket = Object.Instantiate(prefab, hit.point, Quaternion.LookRotation(-fwd, Vector3.up));
            var nview = bucket.GetComponent<ZNetView>();
            if (nview != null && nview.IsValid() && ZNet.instance != null)
                nview.GetZDO().Set(EndKey, (float)(ZNet.instance.GetTimeSeconds() + def.Duration));

            inventory.RemoveOneItem(item);
            player.Message(MessageHud.MessageType.Center,
                $"You set down the {Loc.Text(item.m_shared.m_name)}. Fish gather within {def.Radius:0} m of it for {def.Duration / 60f:0.#} min.");
            return true;
        }

        /// <summary>
        /// One stat from the chum buckets out near <paramref name="at"/> (the line in the water), whoever set them down.
        /// The same kind of chum doesn't stack: each kind counts once, its nearest bucket.
        /// </summary>
        public static float Total(string stat, Vector3 at)
        {
            float total = 0f;
            var counted = new HashSet<string>();
            foreach (var b in Active)
            {
                if (b == null || !b.Running) continue;
                var def = b.Def;
                if (def == null || counted.Contains(def.Id) || !def.Effects.TryGetValue(stat, out var v)) continue;
                if (Vector3.Distance(b.transform.position, at) > def.Radius) continue;
                counted.Add(def.Id);
                total += v;
            }
            return total;
        }

        /// <summary>Open water somewhere within <paramref name="radius"/> of the spot.</summary>
        private static bool WaterWithin(Vector3 p, float radius, float water)
        {
            if (ZoneSystem.instance == null) return true;
            for (float r = 2f; r <= radius; r += 2.5f)
                for (int i = 0; i < 16; i++)
                {
                    float a = i * Mathf.PI / 8f;
                    var q = p + new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)) * r;
                    if (ZoneSystem.instance.GetGroundHeight(q) < water - 0.3f) return true;
                }
            return false;
        }
    }

    /// <summary>
    /// A set-down chum bucket, on every client: chums the water around it until its end time, sinks away over its
    /// last few seconds, and is then removed by whoever owns it.
    /// </summary>
    internal sealed class ChumBucket : MonoBehaviour, Hoverable
    {
        private ZNetView? _nview;
        private Vector3 _start;
        private bool _hasStart;
        public BuffDefinition? Def { get; private set; }

        /// <summary>Still full of chum (not yet sinking).</summary>
        public bool Running => Left() > 3f;

        private void Awake()
        {
            _nview = GetComponent<ZNetView>();
            Def = ChumBuckets.DefFor(gameObject.name.Replace("(Clone)", "").Trim());
        }

        private void OnEnable() => ChumBuckets.Active.Add(this);
        private void OnDisable() => ChumBuckets.Active.Remove(this);

        private float Left()
        {
            if (_nview == null || !_nview.IsValid() || ZNet.instance == null) return 0f;
            float end = _nview.GetZDO().GetFloat(ChumBuckets.EndKey, 0f);
            return end <= 0f ? 999f : end - (float)ZNet.instance.GetTimeSeconds();   // 999: just set down, end not synced yet
        }

        private void Update()
        {
            if (_nview == null || !_nview.IsValid()) return;
            if (!_hasStart) { _start = transform.position; _hasStart = true; }
            float left = Left();
            if (left < 3f) transform.position = _start + Vector3.down * Mathf.Clamp01(1f - left / 3f) * 0.5f; // sinks away
            if (left <= 0f && _nview.IsOwner()) _nview.Destroy();
        }

        public string GetHoverText()
        {
            if (Def == null) return "";
            float left = Mathf.Max(0f, Left());
            if (left > 900f) return Loc.Text(Def.Name);
            return $"{Loc.Text(Def.Name)}\nChumming the water for {Mathf.FloorToInt(left / 60f)}:{Mathf.FloorToInt(left % 60f):00}";
        }

        public string GetHoverName() => Def != null ? Loc.Text(Def.Name) : "";

        public float GetHoverOffset() => 0f;
    }
}
