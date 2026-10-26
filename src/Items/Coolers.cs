using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Coolers: a box for your catch, in three tiers. Not worn: it's carried in the inventory and set down where you fish.
    ///   - right-click it in the inventory to set it down as a chest; on a set-down cooler, E opens it, Shift+E picks it
    ///     back up, contents and all (what's inside is saved on the item, like a tackle box)
    ///   - it holds fish, raw fish, fillets, roe and dried fish only
    ///   - fish kept in a cooler stay fresh while they're in it and for a while after (longer for a better cooler); a fresh
    ///     raw fish sells for more and gives one more material at the Cleaning Table. Nothing ever spoils - fresh is a bonus.
    /// Until the cooler's own model exists (cooler_c1..c3), it borrows the tackle box's, tinted.
    /// </summary>
    internal static class Coolers
    {
        internal sealed class Tier
        {
            public string Id = "", Name = "", Desc = "", Station = "", Biome = "", Fallback = "", ColdText = "";
            public int W, H, Level;
            public float FreshMinutes;
            public Color Tint = Color.white;
            public (string item, int amount)[] Recipe = Array.Empty<(string, int)>();
            public string ItemPrefab => "VDW_Cooler_" + Id;
            public string PlacedPrefab => "VDW_CoolerPlaced_" + Id;
            public string ModelKey => "cooler_" + Id;
        }

        internal static readonly Tier[] Tiers =
        {
            new Tier { Id = "c1", Name = "Wooden Cooler", Biome = "Black Forest", W = 4, H = 3, Station = "piece_workbench", Level = 2,
                FreshMinutes = 10, Fallback = "tacklebox_t1", Tint = new Color(0.78f, 0.86f, 0.95f),
                Desc = "A sealed wooden box packed with damp moss. Your catch keeps cool in it.",
                Recipe = new[] { ("FineWood", 8), ("Resin", 6), ("LeatherScraps", 4) } },
            new Tier { Id = "c2", Name = "Iron-Banded Cooler", Biome = "Swamp", W = 5, H = 3, Station = "forge", Level = 2,
                FreshMinutes = 20, Fallback = "tacklebox_t2", Tint = new Color(0.72f, 0.82f, 0.92f),
                Desc = "Tarred planks banded with iron, tight against the warm and the wet.",
                Recipe = new[] { ("FineWood", 10), ("Iron", 4), ("Guck", 4), ("VDW_Mat_oil", 4) } },
            new Tier { Id = "c3", Name = "Frost Cooler", Biome = "Mountain", W = 6, H = 4, Station = "forge", Level = 4,
                FreshMinutes = 45, Fallback = "tacklebox_t3", Tint = new Color(0.70f, 0.88f, 1.0f),
                Desc = "Lined with freeze glands and packed with mountain ice. Fish come out of it as cold as they went in.",
                Recipe = new[] { ("FineWood", 10), ("Silver", 4), ("FreezeGland", 4), ("Crystal", 2) } },
        };

        public const float SellBonus = 0.25f;         // a fresh raw fish sells for this much more
        public const int CleanBonus = 1;              // and gives this many more at the Cleaning Table
        private const string DataKey = "vdw_cooler", FreshKey = "vdw_fresh_until";
        private const float PlacedScale = 1.6f, TickSeconds = 5f;

        private static readonly Dictionary<string, Tier> ByItemName = new();
        private static readonly Dictionary<string, Tier> ByPlaced = new();
        private static readonly ConditionalWeakTable<ItemDrop.ItemData, Inventory> Cache = new();
        internal static readonly HashSet<Inventory> CoolerInventories = new();
        internal static readonly List<CoolerChill> Placed = new();
        private static readonly MethodInfo? ChangedMethod = AccessTools.Method(typeof(Inventory), "Changed");

        public static Tier? TierOf(ItemDrop.ItemData? item) =>
            item?.m_shared?.m_name != null && ByItemName.TryGetValue(item.m_shared.m_name, out var t) ? t : null;
        internal static Tier? TierOfPlaced(Component c) => ByPlaced.TryGetValue(Utils.GetPrefabName(c.gameObject), out var t) ? t : null;

        // ------------------------------------------------------------------ registration

        public static void Register()
        {
            foreach (var t in Tiers)
            {
                try { RegisterItem(t); RegisterPlaced(t); }
                catch (Exception ex) { Plugin.Log.LogError($"Cooler '{t.Id}' failed: {ex}"); }
            }
        }

        /// <summary>The cooler's own model, or the tackle box's standing in for it.</summary>
        private static string ModelFor(Tier t, out bool standIn)
        {
            standIn = CustomModels.GetBundlePrefab(t.ModelKey) == null;
            return standIn ? t.Fallback : t.ModelKey;
        }

        private static void RegisterItem(Tier t)
        {
            var item = new CustomItem(t.ItemPrefab, "BeltStrength", new ItemConfig
            {
                CraftingStation = t.Station,
                MinStationLevel = t.Level,
                Requirements = t.Recipe.Select(r => new RequirementConfig(r.item, r.amount)).ToArray()
            });
            var s = item.ItemDrop.m_itemData.m_shared;
            s.m_name = Loc.Token("vdw_cooler_item_" + t.Id, t.Name);
            s.m_description = Loc.Token("vdw_cooler_item_" + t.Id + "_desc",
                $"{t.Desc} Holds {t.W * t.H} stacks of fish, raw fish, fillets, roe and dried fish. Right-click it to set it down; " +
                $"E opens it and Shift+E picks it up again, catch and all. Fish kept in it stay fresh while they're in it and for " +
                $"{t.FreshMinutes:0} minutes after: a fresh fish sells for {SellBonus:P0} more and gives one more material at the Cleaning Table.");
            s.m_itemType = ItemDrop.ItemData.ItemType.Misc;            // not worn
            s.m_equipStatusEffect = null; s.m_setStatusEffect = null; s.m_setName = ""; s.m_setSize = 0;
            s.m_movementModifier = 0f; s.m_weight = 4f; s.m_maxStackSize = 1; s.m_teleportable = true; s.m_value = 0;
            s.m_useDurability = false;
            var skin = item.ItemPrefab.transform.Find("attach_skin");
            if (skin != null) UnityEngine.Object.DestroyImmediate(skin.gameObject);
            var key = ModelFor(t, out bool standIn);
            if (CustomModels.ApplyToPrefab(item.ItemPrefab, key))
            {
                if (standIn) Tint(item.ItemPrefab, t.Tint);
                GroundPose.FitCollider(item.ItemPrefab);
            }
            ItemManager.Instance.AddItem(item);
            ByItemName[s.m_name] = t;
        }

        private static void RegisterPlaced(Tier t)
        {
            var key = ModelFor(t, out bool standIn);
            var model = CustomModels.GetBundlePrefab(key);
            if (model == null) { Plugin.Log.LogWarning($"Cooler '{t.Id}': no {key} model; it can't be set down."); return; }
            var go = PrefabManager.Instance.CreateClonedPrefab(t.PlacedPrefab, "piece_chest_wood");
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
            var wnt = go.GetComponent<WearNTear>(); if (wnt != null) UnityEngine.Object.DestroyImmediate(wnt);
            var inst = UnityEngine.Object.Instantiate(model, go.transform, false);
            inst.name = "vdw_model"; inst.transform.localScale = Vector3.one * PlacedScale;
            foreach (var c in inst.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
            if (standIn) Tint(inst, t.Tint);
            var b = TackleBoxes.Bounds(inst);
            var col = go.AddComponent<BoxCollider>(); col.center = go.transform.InverseTransformPoint(b.center); col.size = b.size;
            var cont = go.GetComponent<Container>();
            cont.m_name = Loc.Token("vdw_cooler_item_" + t.Id, t.Name);
            cont.m_width = t.W; cont.m_height = t.H;
            cont.m_privacy = Container.PrivacySetting.Public; cont.m_checkGuardStone = true; cont.m_autoDestroyEmpty = false;
            cont.m_open = null; cont.m_closed = null;
            cont.m_defaultItems = new DropTable();
            var piece = go.GetComponent<Piece>();
            if (piece != null) { piece.m_name = cont.m_name; piece.m_canBeRemoved = false; }
            go.AddComponent<CoolerChill>();
            PrefabManager.Instance.AddPrefab(go);
            ByPlaced[t.PlacedPrefab] = t;
        }

        /// <summary>A cool tint on the tackle box model standing in for the cooler's own.</summary>
        private static void Tint(GameObject g, Color c)
        {
            foreach (var r in g.GetComponentsInChildren<Renderer>(true))
                r.sharedMaterials = r.sharedMaterials.Select(m =>
                {
                    if (m == null) return m;
                    var copy = new Material(m) { name = m.name + "_cooler" };
                    if (copy.HasProperty("_Color")) copy.SetColor("_Color", copy.GetColor("_Color") * c);
                    return copy;
                }).ToArray();
        }

        // ------------------------------------------------------------------ what goes in, what's inside

        /// <summary>The catch: fish, Raw fish, fillets, roe and dried fish.</summary>
        public static bool IsCatch(ItemDrop.ItemData? item)
        {
            if (item?.m_dropPrefab == null) return false;
            string n = item.m_dropPrefab.name;
            return RareFish.IsFishItem(item) || n == "FishRaw" || n == FishDishes.Fillet || n == FishDishes.Roe || n == FishDishes.Dried;
        }

        public static Inventory? Contents(ItemDrop.ItemData? item)
        {
            var t = TierOf(item);
            if (item == null || t == null) return null;
            if (Cache.TryGetValue(item, out var inv)) return inv;
            inv = new Inventory(Loc.Text(item.m_shared.m_name), null, t.W, t.H);
            if (item.m_customData.TryGetValue(DataKey, out var data) && !string.IsNullOrEmpty(data))
            {
                try { inv.Load(new ZPackage(data)); }
                catch (Exception ex) { Plugin.Log.LogWarning($"Cooler: couldn't read its contents ({ex.Message})."); }
            }
            var owner = item;
            inv.m_onChanged += () => { var pkg = new ZPackage(); inv.Save(pkg); owner.m_customData[DataKey] = pkg.GetBase64(); };
            Cache.Add(item, inv); CoolerInventories.Add(inv);
            return inv;
        }

        // ------------------------------------------------------------------ freshness

        private static double Now => ZNet.instance != null ? ZNet.instance.GetTimeSeconds() : 0;

        /// <summary>A raw fish that's been in a cooler recently (or still is).</summary>
        public static bool IsFresh(ItemDrop.ItemData? item) =>
            item?.m_customData != null && RareFish.IsFishItem(item) && item.m_customData.TryGetValue(FreshKey, out var raw)
            && double.TryParse(raw, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var until) && until > Now;

        public static float FreshMinutesLeft(ItemDrop.ItemData item) =>
            item.m_customData.TryGetValue(FreshKey, out var raw) && double.TryParse(raw, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var until)
                ? (float)Math.Max(0, (until - Now) / 60.0) : 0f;

        /// <summary>
        /// Keeps the fish in a cooler fresh: each one's "fresh until" is pushed on to now plus the cooler's minutes. Only
        /// written once it's a minute stale, so a set-down cooler isn't saved over the network every few seconds.
        /// </summary>
        internal static bool Chill(Inventory inv, Tier t)
        {
            double now = Now, until = now + t.FreshMinutes * 60.0;
            bool changed = false;
            foreach (var it in inv.GetAllItems())
            {
                if (!RareFish.IsFishItem(it)) continue;
                double had = it.m_customData.TryGetValue(FreshKey, out var raw) && double.TryParse(raw, System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var u) ? u : 0;
                if (had > until - 60.0) continue;
                it.m_customData[FreshKey] = until.ToString("0", System.Globalization.CultureInfo.InvariantCulture);
                changed = true;
            }
            if (changed) ChangedMethod?.Invoke(inv, new object[] { false, false });
            return changed;
        }

        private static float _nextTick;

        /// <summary>Every frame for the local player (Plugin.LateUpdate): the coolers in your inventory and the set-down ones you own.</summary>
        public static void UpdateLocal()
        {
            if (Time.time < _nextTick || ZNet.instance == null) return;
            _nextTick = Time.time + TickSeconds;
            var p = Player.m_localPlayer;
            if (p != null)
                foreach (var it in p.GetInventory().GetAllItems())
                    if (TierOf(it) is Tier t && Contents(it) is Inventory inv) Chill(inv, t);
            foreach (var c in Placed.ToList()) c.Tick();
        }

        // ------------------------------------------------------------------ setting down, picking up

        private static readonly int GroundMask = LayerMask.GetMask("Default", "static_solid", "terrain", "piece");

        private static void SetDown(Player p, ItemDrop.ItemData box, Tier t)
        {
            if (p.IsSwimming() || p.IsAttached() || p.GetStandingOnShip() != null) { p.Message(MessageHud.MessageType.Center, "Find solid ground to set it down."); return; }
            var prefab = ZNetScene.instance?.GetPrefab(t.PlacedPrefab);
            if (prefab == null) { p.Message(MessageHud.MessageType.Center, "This cooler can't be set down (its model is missing)."); return; }
            Vector3 at = p.transform.position + p.transform.forward * 1.0f;
            if (Physics.Raycast(at + Vector3.up * 1.5f, Vector3.down, out var hit, 4f, GroundMask)) at = hit.point;
            else { p.Message(MessageHud.MessageType.Center, "There's no room to set it down there."); return; }
            var go = UnityEngine.Object.Instantiate(prefab, at, Quaternion.LookRotation(-p.transform.forward, Vector3.up));
            var dst = go.GetComponent<Container>().GetInventory(); var src = Contents(box)!;
            foreach (var it in src.GetAllItems().ToList()) { src.RemoveItem(it); dst.AddItem(it, it.m_gridPos); }
            p.GetInventory().RemoveItem(box);
            p.Message(MessageHud.MessageType.Center, $"You set the {Loc.Text(box.m_shared.m_name)} down.");
        }

        private static bool PickUp(Container c, Player p, Tier t)
        {
            var nview = c.GetComponent<ZNetView>();
            if (nview == null || !nview.IsValid()) return true;
            if (!nview.IsOwner() && nview.GetZDO().GetInt("inUse".GetStableHashCode()) == 1) { p.Message(MessageHud.MessageType.Center, "Someone's using it."); return true; }
            if (!p.GetInventory().HaveEmptySlot()) { p.Message(MessageHud.MessageType.Center, "No room in your inventory."); return true; }
            var item = p.GetInventory().AddItem(t.ItemPrefab, 1, 1, 0, 0L, "", false);
            if (item == null) return true;
            var dst = Contents(item)!; var src = c.GetInventory();
            foreach (var it in src.GetAllItems().ToList()) { src.RemoveItem(it); dst.AddItem(it, it.m_gridPos); }
            nview.ClaimOwnership(); ZNetScene.instance.Destroy(c.gameObject);
            p.Message(MessageHud.MessageType.Center, $"You pick up the {Loc.Text(item.m_shared.m_name)}.");
            return true;
        }

        // ------------------------------------------------------------------ patches

        /// <summary>Right-click a cooler in the inventory: it's set down in front of you.</summary>
        [HarmonyPatch(typeof(Humanoid), nameof(Humanoid.UseItem))]
        private static class UsePatch
        {
            private static bool Prefix(Humanoid __instance, Inventory inventory, ItemDrop.ItemData item)
            {
                if (!(__instance is Player p) || p != Player.m_localPlayer || TierOf(item) is not Tier t) return true;
                if (inventory != null && inventory != p.GetInventory()) return true;   // in a chest: leave it to the chest
                if (InventoryGui.IsVisible()) InventoryGui.instance.Hide();
                SetDown(p, item, t);
                return false;
            }
        }

        [HarmonyPatch(typeof(Container), nameof(Container.Interact))]
        private static class PickUpPatch
        {
            private static bool Prefix(Container __instance, Humanoid character, bool hold, bool alt, ref bool __result)
            {
                if (hold || !alt || !(character is Player p) || TierOfPlaced(__instance) is not Tier t) return true;
                __result = PickUp(__instance, p, t); return false;
            }
        }

        [HarmonyPatch(typeof(Container), nameof(Container.GetHoverText))]
        private static class HoverPatch
        {
            private static void Postfix(Container __instance, ref string __result)
            {
                if (TierOfPlaced(__instance) is not Tier t) return;
                __result += Localization.instance.Localize($"\n[<color=yellow><b>$KEY_AltPlace + $KEY_Use</b></color>] Pick up\n<color=#9fd3ff>Keeps fish fresh</color>");
            }
        }

        private static bool Refuse(Inventory into, ItemDrop.ItemData item)
        {
            if (!CoolerInventories.Contains(into) || IsCatch(item)) return false;
            Player.m_localPlayer?.Message(MessageHud.MessageType.Center, "Only your catch goes in a cooler.");
            return true;
        }

        [HarmonyPatch(typeof(Inventory), nameof(Inventory.MoveItemToThis), new[] { typeof(Inventory), typeof(ItemDrop.ItemData), typeof(int), typeof(int), typeof(int) })]
        private static class FilterMove
        {
            private static bool Prefix(Inventory __instance, ItemDrop.ItemData item, ref bool __result) { if (!Refuse(__instance, item)) return true; __result = false; return false; }
        }

        [HarmonyPatch(typeof(Inventory), nameof(Inventory.MoveItemToThis), new[] { typeof(Inventory), typeof(ItemDrop.ItemData) })]
        private static class FilterMoveAny
        {
            private static bool Prefix(Inventory __instance, ItemDrop.ItemData item) => !Refuse(__instance, item);
        }

        [HarmonyPatch(typeof(Inventory), nameof(Inventory.AddItem), new[] { typeof(ItemDrop.ItemData) })]
        private static class FilterAdd
        {
            private static bool Prefix(Inventory __instance, ItemDrop.ItemData item, ref bool __result) { if (!Refuse(__instance, item)) return true; __result = false; return false; }
        }

        /// <summary>A carried cooler weighs what's in it.</summary>
        [HarmonyPatch(typeof(ItemDrop.ItemData), nameof(ItemDrop.ItemData.GetWeight))]
        private static class WeightPatch
        {
            private static void Postfix(ItemDrop.ItemData __instance, ref float __result)
            {
                if (TierOf(__instance) != null && Contents(__instance) is Inventory inv) __result += inv.GetTotalWeight();
            }
        }

        [HarmonyPatch(typeof(ItemDrop.ItemData), nameof(ItemDrop.ItemData.GetTooltip),
            new[] { typeof(ItemDrop.ItemData), typeof(int), typeof(bool), typeof(float), typeof(int), typeof(bool) })]
        private static class FreshTooltip
        {
            private static void Postfix(ItemDrop.ItemData item, ref string __result)
            {
                if (!IsFresh(item)) return;
                __result += $"\n<color=#9fd3ff>Fresh</color> ({FreshMinutesLeft(item):0} min): sells for {SellBonus:P0} more, +{CleanBonus} when cleaned";
            }
        }

        /// <summary>A fresh fish cleaned at the Cleaning Table gives one more of its material.</summary>
        [HarmonyPatch(typeof(InventoryGui), "DoCrafting")]
        private static class FreshCleaning
        {
            private static readonly FieldInfo? RecipeField = AccessTools.Field(typeof(InventoryGui), "m_craftRecipe");

            private static void Prefix(InventoryGui __instance, Player player, out (string item, int had)? __state)
            {
                __state = null;
                if (!(RecipeField?.GetValue(__instance) is Recipe r) || r.m_item == null || !r.name.StartsWith("Recipe_VDW_Clean_")) return;
                var used = player.GetFirstRequiredItem(player.GetInventory(), r, 1, out _, out _);
                if (!IsFresh(used)) return;
                string name = r.m_item.m_itemData.m_shared.m_name;
                __state = (r.m_item.gameObject.name, player.GetInventory().CountItems(name));
            }

            private static void Postfix(InventoryGui __instance, Player player, (string item, int had)? __state)
            {
                if (__state == null || !(RecipeField?.GetValue(__instance) is Recipe r)) return;
                if (player.GetInventory().CountItems(r.m_item.m_itemData.m_shared.m_name) <= __state.Value.had) return;   // nothing was made
                var added = player.GetInventory().AddItem(__state.Value.item, CleanBonus, 1, 0, 0L, "", false);
                if (added != null) player.Message(MessageHud.MessageType.TopLeft, $"Fresh catch: +{CleanBonus} {Loc.Text(r.m_item.m_itemData.m_shared.m_name)}");
            }
        }
    }

    /// <summary>
    /// On a set-down cooler: keeps its fish fresh (the owner's client does it, so it's saved once for everyone) and opens
    /// the lid while anyone uses it.
    /// </summary>
    internal sealed class CoolerChill : MonoBehaviour
    {
        private Container? _cont; private ZNetView? _nview; private LidDriver? _lid; private Coolers.Tier? _tier;
        public const float OpenDeg = 68.3f;   // build_cooler.py: how far the ice chest's lid stood open as modelled
        private static readonly int InUse = "inUse".GetStableHashCode();

        private void Start()
        {
            _cont = GetComponent<Container>(); _nview = GetComponent<ZNetView>(); _tier = Coolers.TierOfPlaced(this);
            var model = transform.Find("vdw_model"); if (model != null) _lid = new LidDriver(model.gameObject, OpenDeg);   // open: as the model was made (its lid swung shut by this much)
            if (_cont != null && _cont.GetInventory() != null) Coolers.CoolerInventories.Add(_cont.GetInventory());
            Coolers.Placed.Add(this);
        }

        private void OnDestroy()
        {
            if (_cont != null && _cont.GetInventory() != null) Coolers.CoolerInventories.Remove(_cont.GetInventory());
            Coolers.Placed.Remove(this);
        }

        public void Tick()
        {
            if (_cont == null || _tier == null || _nview == null || !_nview.IsValid() || !_nview.IsOwner()) return;
            var inv = _cont.GetInventory(); if (inv == null) return;
            Coolers.Chill(inv, _tier);
        }

        private void Update()
        {
            if (_nview == null || !_nview.IsValid() || _cont == null) return;
            bool open = _nview.IsOwner() ? _cont.IsInUse() : _nview.GetZDO().GetInt(InUse) == 1;
            _lid?.Update(open, Time.deltaTime);
            SetChill(open);
        }

        // ------------------------------------------------------------------ the cold inside

        private GameObject? _cold; private bool _coldOn;
        private static GameObject[]? _coldPrefabs;

        /// <summary>
        /// The visual effect a player shows when Cold (the game's own "Cold" status effect, its start effects), played
        /// inside the cooler while it's open: frost breath rising out of the box.
        /// </summary>
        private void SetChill(bool open)
        {
            if (open == _coldOn) return;
            _coldOn = open;
            if (open && _cold == null) _cold = BuildCold();
            if (_cold == null) return;
            foreach (var ps in _cold.GetComponentsInChildren<ParticleSystem>(true))
            {
                if (open) ps.Play(true);
                else ps.Stop(true, ParticleSystemStopBehavior.StopEmitting);   // what's in the air drifts away
            }
        }

        private GameObject? BuildCold()
        {
            _coldPrefabs ??= ColdEffects();
            if (_coldPrefabs.Length == 0) return null;
            var model = transform.Find("vdw_model");
            var b = TackleBoxes.Bounds(model != null ? model.gameObject : gameObject);
            var holder = new GameObject("vdw_cold");
            holder.transform.SetParent(transform, false);
            // inside, just above the floor of the box
            holder.transform.position = new Vector3(b.center.x, b.min.y + b.size.y * 0.35f, b.center.z);
            Vector3 inner = new Vector3(b.size.x * 0.7f, b.size.y * 0.3f, b.size.z * 0.6f);
            bool was = ZNetView.m_forceDisableInit;
            ZNetView.m_forceDisableInit = true;            // effect prefabs with a net view mustn't register as world objects
            try
            {
                foreach (var prefab in _coldPrefabs)
                {
                    var fx = Instantiate(prefab, holder.transform, false);
                    fx.transform.localPosition = Vector3.zero; fx.transform.localRotation = Quaternion.identity;
                    foreach (var nv in fx.GetComponentsInChildren<ZNetView>(true)) DestroyImmediate(nv);
                    foreach (var tf in fx.GetComponentsInChildren<TimedDestruction>(true)) DestroyImmediate(tf);
                    foreach (var ps in fx.GetComponentsInChildren<ParticleSystem>(true))
                    {
                        var main = ps.main; main.scalingMode = ParticleSystemScalingMode.Hierarchy; main.loop = true;
                        main.simulationSpace = ParticleSystemSimulationSpace.World;
                        var shape = ps.shape;
                        if (shape.enabled && (shape.shapeType == ParticleSystemShapeType.SkinnedMeshRenderer || shape.shapeType == ParticleSystemShapeType.MeshRenderer
                            || shape.shapeType == ParticleSystemShapeType.Mesh))
                        { shape.shapeType = ParticleSystemShapeType.Box; shape.scale = inner; shape.position = Vector3.zero; }
                        ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                    }
                    // the body-sized effect, shrunk to the box
                    fx.transform.localScale = Vector3.one * Mathf.Clamp(inner.x / 0.8f, 0.3f, 1f);
                }
            }
            finally { ZNetView.m_forceDisableInit = was; }
            return holder;
        }

        private static GameObject[] ColdEffects()
        {
            var se = ObjectDB.instance?.GetStatusEffect("Cold".GetStableHashCode());
            var list = se?.m_startEffects?.m_effectPrefabs?.Where(e => e != null && e.m_enabled && e.m_prefab != null)
                .Select(e => e.m_prefab).Where(p => p.GetComponentsInChildren<ParticleSystem>(true).Length > 0).ToArray() ?? Array.Empty<GameObject>();
            if (list.Length == 0) Plugin.Log.LogWarning("Coolers: the game's Cold effect wasn't found; coolers open without their frost.");
            else Plugin.Log.LogDebug($"Coolers: cold effect from {string.Join(", ", list.Select(p => p.name))}.");
            return list;
        }
    }
}
