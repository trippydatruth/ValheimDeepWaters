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
    /// Tackle boxes: a utility item that holds tackle (bait, hooks, lures, weights, leaders, floats), in four tiers. What's
    /// inside is saved on the item itself, so it stays inside wherever the box goes - inventory, chest, grave.
    ///   - worn (utility slot), it's carried by the handle in the right hand when that hand is free, at the hip otherwise
    ///   - the Tackle Box key opens it; Shift + the key sets it down as a chest, whose lid opens when anyone uses it
    ///   - on a set-down box, E opens it and Shift+E picks it back up, contents and all
    ///   - the bait, hook, weight and leader slots refill from the box you're wearing
    /// The model is the user's box (Mesh\tacklebox), rigged: the "lid" bone is turned here.
    /// </summary>
    internal static class TackleBoxes
    {
        internal sealed class Tier
        {
            public string Id = "", Name = "", Desc = "", Station = "", Biome = "";
            public int W, H, Level;
            public (string item, int amount)[] Recipe = Array.Empty<(string, int)>();
            public string ItemPrefab => "VDW_TackleChest_" + Id;
            public string PlacedPrefab => "VDW_TackleChestPlaced_" + Id;
            public string ModelKey => "tacklebox_" + Id;
        }

        internal static readonly Tier[] Tiers =
        {
            new Tier { Id = "t1", Name = "Tackle Box", Biome = "Black Forest", W = 4, H = 2, Station = "piece_workbench", Level = 2,
                Desc = "A wooden box of little compartments for your tackle.",
                Recipe = new[] { ("FineWood", 6), ("LeatherScraps", 4), ("BronzeNails", 10) } },
            new Tier { Id = "t2", Name = "Iron-Bound Tackle Box", Biome = "Swamp", W = 4, H = 3, Station = "forge", Level = 2,
                Desc = "Stained wood strapped with iron, made for the wet of the swamp.",
                Recipe = new[] { ("FineWood", 8), ("Iron", 4), ("LeatherScraps", 2), ("VDW_Mat_oil", 4) } },
            new Tier { Id = "t3", Name = "Silver Tackle Box", Biome = "Mountain", W = 4, H = 4, Station = "forge", Level = 4,
                Desc = "Pale birch bound in silver, with a silver handle.",
                Recipe = new[] { ("FineWood", 8), ("Silver", 4), ("WolfPelt", 2), ("VDW_Mat_fins", 4) } },
            new Tier { Id = "t4", Name = "Dvergr Tackle Box", Biome = "Mistlands", W = 6, H = 4, Station = "blackforge", Level = 1,
                Desc = "Dvergr work: blue-grey wood, hammered copper, and a faint rune line that glows round the lid.",
                Recipe = new[] { ("YggdrasilWood", 8), ("Copper", 4), ("Carapace", 4), ("VDW_Mat_ink", 4) } },
        };

        private const string DataKey = "vdw_box";
        private const float PlacedScale = 1.4f;   // the model is 0.6 m long; carried sizes in TackleBoxesScale

        private static readonly Dictionary<string, Tier> ByItemName = new();      // shared m_name -> tier
        private static readonly Dictionary<int, Tier> ByItemHash = new();         // item prefab hash -> tier (others' utility slot)
        private static readonly Dictionary<string, Tier> ByPlaced = new();        // placed prefab name -> tier
        private static readonly ConditionalWeakTable<ItemDrop.ItemData, Inventory> Cache = new();
        internal static readonly HashSet<Inventory> BoxInventories = new();       // carried and set-down: tackle only

        public static Tier? TierOf(ItemDrop.ItemData? item) =>
            item?.m_shared?.m_name != null && ByItemName.TryGetValue(item.m_shared.m_name, out var t) ? t : null;
        private static Tier? TierOfPlaced(Component c) => ByPlaced.TryGetValue(Utils.GetPrefabName(c.gameObject), out var t) ? t : null;

        // ------------------------------------------------------------------ registration

        public static void Register()
        {
            foreach (var t in Tiers)
            {
                try { RegisterItem(t); RegisterPlaced(t); }
                catch (Exception ex) { Plugin.Log.LogError($"Tackle box '{t.Id}' failed: {ex}"); }
            }
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
            s.m_name = Loc.Token("vdw_tacklebox_item_" + t.Id, t.Name);
            s.m_description = Loc.Token("vdw_tacklebox_item_" + t.Id + "_desc",
                $"{t.Desc} Holds {t.W * t.H} stacks of tackle: bait, hooks, lures, weights, leaders and floats - and keeps them when you put it away. " +
                "Wear it (utility slot) and press the Tackle Box key to open it, or Shift + the key to set it down as a chest (Shift+E picks it up again). " +
                "Your bait, hook, weight and leader slots refill from the box you're wearing.");
            s.m_itemType = ItemDrop.ItemData.ItemType.Utility;
            s.m_equipStatusEffect = null; s.m_setStatusEffect = null; s.m_setName = ""; s.m_setSize = 0;
            s.m_movementModifier = 0f; s.m_weight = 2f; s.m_maxStackSize = 1; s.m_teleportable = true; s.m_value = 0;
            s.m_useDurability = false;
            // Megingjord's worn belt (a skinned model the body puts on when it's equipped): the box is shown by TackleBoxCarry instead
            var skin = item.ItemPrefab.transform.Find("attach_skin");
            if (skin != null) UnityEngine.Object.DestroyImmediate(skin.gameObject);
            if (CustomModels.ApplyToPrefab(item.ItemPrefab, t.ModelKey)) GroundPose.FitCollider(item.ItemPrefab);
            ItemManager.Instance.AddItem(item);
            ByItemName[s.m_name] = t;
            ByItemHash[t.ItemPrefab.GetStableHashCode()] = t;
        }

        /// <summary>A set-down box: Valheim's wooden chest (container, saving, networking) wearing the box model.</summary>
        private static void RegisterPlaced(Tier t)
        {
            var model = CustomModels.GetBundlePrefab(t.ModelKey);
            if (model == null) { Plugin.Log.LogWarning($"Tackle box '{t.Id}': no {t.ModelKey} model; it can't be set down."); return; }
            var go = PrefabManager.Instance.CreateClonedPrefab(t.PlacedPrefab, "piece_chest_wood");
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
            var wnt = go.GetComponent<WearNTear>(); if (wnt != null) UnityEngine.Object.DestroyImmediate(wnt);   // picked up, never broken
            var inst = UnityEngine.Object.Instantiate(model, go.transform, false);
            inst.name = "vdw_model"; inst.transform.localScale = Vector3.one * PlacedScale;
            foreach (var c in inst.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
            // a box collider round the model, to stand it on the ground and look at it
            var b = Bounds(inst);
            var col = go.AddComponent<BoxCollider>(); col.center = go.transform.InverseTransformPoint(b.center); col.size = b.size;
            var cont = go.GetComponent<Container>();
            cont.m_name = Loc.Token("vdw_tacklebox_item_" + t.Id, t.Name);
            cont.m_width = t.W; cont.m_height = t.H;
            cont.m_privacy = Container.PrivacySetting.Public; cont.m_checkGuardStone = true; cont.m_autoDestroyEmpty = false;
            cont.m_open = null; cont.m_closed = null;
            cont.m_defaultItems = new DropTable();
            var piece = go.GetComponent<Piece>();
            if (piece != null) { piece.m_name = cont.m_name; piece.m_canBeRemoved = false; }
            go.AddComponent<TackleBoxLid>();
            PrefabManager.Instance.AddPrefab(go);
            ByPlaced[t.PlacedPrefab] = t;
        }

        internal static Bounds Bounds(GameObject g)
        {
            var rs = g.GetComponentsInChildren<Renderer>(true);
            if (rs.Length == 0) return new Bounds(g.transform.position, Vector3.one * 0.3f);
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); return b;
        }

        // ------------------------------------------------------------------ what's inside

        /// <summary>The box's contents, loaded from the item the first time and saved back to it on every change.</summary>
        public static Inventory? Contents(ItemDrop.ItemData? item)
        {
            var t = TierOf(item);
            if (item == null || t == null) return null;
            if (Cache.TryGetValue(item, out var inv)) return inv;
            inv = new Inventory(Loc.Text(item.m_shared.m_name), null, t.W, t.H);
            if (item.m_customData.TryGetValue(DataKey, out var data) && !string.IsNullOrEmpty(data))
            {
                try { inv.Load(new ZPackage(data)); }
                catch (Exception ex) { Plugin.Log.LogWarning($"Tackle box: couldn't read its contents ({ex.Message})."); }
            }
            var owner = item;
            inv.m_onChanged += () => { var pkg = new ZPackage(); inv.Save(pkg); owner.m_customData[DataKey] = pkg.GetBase64(); };
            Cache.Add(item, inv); BoxInventories.Add(inv);
            return inv;
        }

        private static readonly FieldInfo? UtilityField = AccessTools.Field(typeof(Humanoid), "m_utilityItem");

        /// <summary>The tackle box the player is wearing, if any.</summary>
        public static ItemDrop.ItemData? WornBox(Player? p) => p != null && UtilityField?.GetValue(p) is ItemDrop.ItemData it && TierOf(it) != null ? it : null;
        public static Inventory? WornContents(Player? p) => Contents(WornBox(p));

        /// <summary>Tackle: bait, lures, hooks, weights, leaders (not rods), and floats.</summary>
        public static bool IsTackle(ItemDrop.ItemData? item)
        {
            if (item == null) return false;
            int slot = Tackle.SlotFor(item);
            if (slot >= 0 && slot != Tackle.RodSlot) return true;
            var prefab = item.m_dropPrefab != null ? item.m_dropPrefab.name : "";
            return prefab.StartsWith("VDW_Buff_") && FishingBuffs.Buffs.TryGetValue(prefab.Substring(9), out var b) && !string.IsNullOrWhiteSpace(b.FloatModel);
        }

        // ------------------------------------------------------------------ opening the worn box, setting it down

        private static Container? _view;            // a hidden chest on the player, showing the worn box's contents
        private static ItemDrop.ItemData? _viewing;
        private static readonly FieldInfo? InventoryField = AccessTools.Field(typeof(Container), "m_inventory");

        private static bool Blocked() =>
            (Chat.instance != null && Chat.instance.HasFocus()) || Console.IsVisible() || Menu.IsVisible() || TextInput.IsVisible() ||
            StoreGui.IsVisible() || Minimap.IsOpen();

        /// <summary>Every frame for the local player (Plugin.LateUpdate).</summary>
        public static void UpdateLocal()
        {
            var p = Player.m_localPlayer;
            if (p == null || !VdwConfig.Enabled.Value) return;
            // the box went (put away, moved, dropped) while it was open: close it
            if (_viewing != null && WornBox(p) != _viewing && InventoryGui.instance != null && InventoryGui.IsVisible()) { InventoryGui.instance.Hide(); _viewing = null; }
            if (_viewing != null && (InventoryGui.instance == null || !InventoryGui.IsVisible())) _viewing = null;
            if (Blocked() || p.IsDead()) return;
            if (VdwConfig.TackleBoxSetDownKey.Value.IsDown()) { SetDown(p); return; }
            if (VdwConfig.TackleBoxKey.Value.IsDown()) Toggle(p);
        }

        private static void Toggle(Player p)
        {
            var box = WornBox(p);
            if (box == null) { p.Message(MessageHud.MessageType.Center, "You're not wearing a tackle box (it goes in the utility slot)."); return; }
            var gui = InventoryGui.instance; if (gui == null) return;
            if (_viewing == box && InventoryGui.IsVisible()) { gui.Hide(); _viewing = null; return; }
            var view = View(p); if (view == null) return;
            var inv = Contents(box)!; var t = TierOf(box)!;
            view.m_width = t.W; view.m_height = t.H; view.m_name = box.m_shared.m_name;
            InventoryField?.SetValue(view, inv);
            _viewing = box;
            gui.Show(view);
        }

        private static Container? View(Player p)
        {
            if (_view != null && _view.transform.parent == p.transform) return _view;
            var nview = p.GetComponent<ZNetView>(); if (nview == null || !nview.IsValid()) return null;
            var go = new GameObject("VDW_TackleBoxView"); go.SetActive(false);
            go.transform.SetParent(p.transform, false);
            var c = go.AddComponent<Container>();
            c.m_rootObjectOverride = nview; c.m_checkGuardStone = false; c.m_autoDestroyEmpty = false; c.m_privacy = Container.PrivacySetting.Public;
            c.m_defaultItems = new DropTable(); c.m_open = null; c.m_closed = null;
            go.SetActive(true);
            return _view = c;
        }

        private static readonly int GroundMask = LayerMask.GetMask("Default", "static_solid", "terrain", "piece");

        private static void SetDown(Player p)
        {
            var box = WornBox(p); var t = TierOf(box);
            if (box == null || t == null) { p.Message(MessageHud.MessageType.Center, "You're not wearing a tackle box."); return; }
            if (p.IsSwimming() || p.IsAttached() || p.GetStandingOnShip() != null) { p.Message(MessageHud.MessageType.Center, "Find solid ground to set it down."); return; }
            var prefab = ZNetScene.instance?.GetPrefab(t.PlacedPrefab);
            if (prefab == null) { p.Message(MessageHud.MessageType.Center, "This box can't be set down (its model is missing)."); return; }
            Vector3 at = p.transform.position + p.transform.forward * 0.9f;
            if (Physics.Raycast(at + Vector3.up * 1.5f, Vector3.down, out var hit, 4f, GroundMask)) at = hit.point;
            else { p.Message(MessageHud.MessageType.Center, "There's no room to set it down there."); return; }
            if (InventoryGui.IsVisible() && _viewing == box) InventoryGui.instance.Hide();
            var go = UnityEngine.Object.Instantiate(prefab, at, Quaternion.LookRotation(-p.transform.forward, Vector3.up));
            var cont = go.GetComponent<Container>(); var dst = cont.GetInventory(); var src = Contents(box)!;
            foreach (var it in src.GetAllItems().ToList()) { src.RemoveItem(it); dst.AddItem(it, it.m_gridPos); }
            p.UnequipItem(box); p.GetInventory().RemoveItem(box);
            p.Message(MessageHud.MessageType.Center, $"You set the {Loc.Text(box.m_shared.m_name)} down.");
        }

        /// <summary>Shift+E on a set-down box: it goes back in your inventory, contents and all.</summary>
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
                if (TierOfPlaced(__instance) == null) return;
                __result += Localization.instance.Localize("\n[<color=yellow><b>$KEY_AltPlace + $KEY_Use</b></color>] Pick up");
            }
        }

        /// <summary>Only tackle goes in a tackle box (carried or set down).</summary>
        private static bool Refuse(Inventory into, ItemDrop.ItemData item)
        {
            if (!BoxInventories.Contains(into) || IsTackle(item)) return false;
            Player.m_localPlayer?.Message(MessageHud.MessageType.Center, "Only tackle goes in a tackle box.");
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

        /// <summary>A box weighs what's in it too.</summary>
        [HarmonyPatch(typeof(ItemDrop.ItemData), nameof(ItemDrop.ItemData.GetWeight))]
        private static class WeightPatch
        {
            private static void Postfix(ItemDrop.ItemData __instance, ref float __result)
            {
                if (TierOf(__instance) != null && Contents(__instance) is Inventory inv) __result += inv.GetTotalWeight();
            }
        }

        /// <summary>Every player carries their worn box visibly (TackleBoxCarry), the local one and everyone else.</summary>
        [HarmonyPatch(typeof(Player), "Awake")]
        private static class CarryPatch
        {
            private static void Postfix(Player __instance) { if (__instance.GetComponent<TackleBoxCarry>() == null) __instance.gameObject.AddComponent<TackleBoxCarry>(); }
        }

        internal static Tier? TierByItemHash(int hash) => ByItemHash.TryGetValue(hash, out var t) ? t : null;
        internal static bool IsViewing(ItemDrop.ItemData? box) => box != null && _viewing == box && InventoryGui.IsVisible();
    }

    /// <summary>Turns a box model's "lid" bone open or shut, easing.</summary>
    internal sealed class LidDriver
    {
        private readonly Transform? _lid; private readonly Quaternion _rest; private readonly float _sign = 1f;
        private float _angle;
        public const float OpenDeg = 105f;

        public LidDriver(GameObject model)
        {
            _lid = model.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "lid");
            if (_lid == null) return;
            _rest = _lid.localRotation;
            // whichever way raises the lid's far end opens it (the bone points from the hinge across the lid)
            Vector3 tip(float deg) { _lid.localRotation = _rest * Quaternion.AngleAxis(deg, Vector3.right); return _lid.position + _lid.up * 0.1f; }
            _sign = tip(20f).y >= tip(-20f).y ? 1f : -1f;
            _lid.localRotation = _rest;
        }

        public void Update(bool open, float dt)
        {
            if (_lid == null) return;
            _angle = Mathf.MoveTowards(_angle, open ? OpenDeg : 0f, dt * 260f);
            _lid.localRotation = _rest * Quaternion.AngleAxis(_sign * Mathf.SmoothStep(0f, OpenDeg, _angle / OpenDeg), Vector3.right);
        }
    }

    /// <summary>On a set-down box: the lid opens while anyone has it open (Valheim's own in-use flag, shared by all).</summary>
    internal sealed class TackleBoxLid : MonoBehaviour
    {
        private Container? _cont; private ZNetView? _nview; private LidDriver? _lid;
        private static readonly int InUse = "inUse".GetStableHashCode();

        private void Start()
        {
            _cont = GetComponent<Container>(); _nview = GetComponent<ZNetView>();
            var model = transform.Find("vdw_model"); if (model != null) _lid = new LidDriver(model.gameObject);
            if (_cont != null && _cont.GetInventory() != null) TackleBoxes.BoxInventories.Add(_cont.GetInventory());
        }

        private void OnDestroy() { if (_cont != null && _cont.GetInventory() != null) TackleBoxes.BoxInventories.Remove(_cont.GetInventory()); }

        private void Update()
        {
            if (_lid == null || _nview == null || !_nview.IsValid() || _cont == null) return;
            bool open = _nview.IsOwner() ? _cont.IsInUse() : _nview.GetZDO().GetInt(InUse) == 1;
            _lid.Update(open, Time.deltaTime);
        }
    }

    /// <summary>
    /// A player's worn tackle box, shown: hanging from the right hand by its handle when that hand is free, at the right
    /// hip when it's holding something (or sitting, swimming). Read from what the body shows, so it works for everyone.
    /// </summary>
    internal sealed class TackleBoxCarry : MonoBehaviour
    {
        private Player? _p; private VisEquipment? _vis;
        private GameObject? _model; private TackleBoxes.Tier? _tier;
        private Quaternion _turn = Quaternion.identity; private float _top, _bottom;
        private static readonly FieldInfo? UtilityHash = AccessTools.Field(typeof(VisEquipment), "m_currentUtilityItemHash");
        private static readonly FieldInfo? RightHash = AccessTools.Field(typeof(VisEquipment), "m_currentRightItemHash");

        private void Awake() { _p = GetComponent<Player>(); _vis = GetComponent<VisEquipment>(); }

        private void OnDestroy() { if (_model != null) Destroy(_model); }

        private void LateUpdate()
        {
            if (_p == null || _vis == null) return;
            var tier = UtilityHash?.GetValue(_vis) is int h && h != 0 ? TackleBoxes.TierByItemHash(h) : null;
            if (tier != _tier) Rebuild(tier);
            if (_model == null) return;
            bool show = !_p.IsDead() && _p.gameObject.activeInHierarchy;
            if (_model.activeSelf != show) _model.SetActive(show);
            if (!show) return;

            bool rightFree = !(RightHash?.GetValue(_vis) is int r && r != 0);
            bool inHand = rightFree && !_p.IsAttached() && !_p.IsSwimming() && _vis.m_rightHand != null;
            var face = Quaternion.LookRotation(Vector3.ProjectOnPlane(_p.transform.forward, Vector3.up).normalized, Vector3.up);
            if (inHand)
            {
                float s = TackleBoxesScale.Held;
                var hand = _vis.m_rightHand;
                _model.transform.localScale = Vector3.one * s;
                // hanging straight down by the handle...
                var rot = face * _turn; var pos = hand.position - Vector3.up * (_top * s - 0.03f);
                // ...recorded once against the hand while standing still, then kept in the hand's own frame so the box
                // turns with it (swings, tips when you jump) instead of staying level
                if (_gripRot == null && _p == Player.m_localPlayer && Time.time > _builtAt + 0.5f && _p.IsOnGround() && !_p.IsCrouching()
                    && !_p.InAttack() && _p.GetVelocity().magnitude < 0.15f)
                {
                    _gripRot = Quaternion.Inverse(hand.rotation) * rot;
                    _gripPos = Quaternion.Inverse(hand.rotation) * (pos - hand.position);
                }
                if (_gripRot is Quaternion gr && _gripPos is Vector3 gp) { rot = hand.rotation * gr; pos = hand.position + hand.rotation * gp; }
                _model.transform.rotation = rot;
                _model.transform.position = pos;
            }
            else
            {
                float s = TackleBoxesScale.Hip;
                var hips = FishingBoatOars.Bone(_p, "Hips");
                Vector3 hip = hips != null ? hips.position : _p.transform.position + Vector3.up * 1f;
                _model.transform.localScale = Vector3.one * s;
                _model.transform.rotation = face * _turn;
                _model.transform.position = hip + _p.transform.right * 0.27f - Vector3.up * ((_top - _bottom) * s * 0.55f) - _p.transform.forward * 0.02f;
            }
        }

        // the grip, recorded once (every character has the same hand), for the same box size
        private static Quaternion? _gripRot; private static Vector3? _gripPos;
        private float _builtAt;

        private void Rebuild(TackleBoxes.Tier? tier)
        {
            if (_model != null) Destroy(_model);
            _model = null; _tier = tier; _builtAt = Time.time;
            if (tier == null) return;
            var src = CustomModels.GetBundlePrefab(tier.ModelKey); if (src == null) return;
            _model = Instantiate(src); _model.name = "VDW_CarriedTackleBox";
            foreach (var c in _model.GetComponentsInChildren<Collider>(true)) Destroy(c);
            foreach (var rb in _model.GetComponentsInChildren<Rigidbody>(true)) Destroy(rb);
            foreach (var smr in _model.GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = true;
            // measure it at rest: its height, and which way its length runs (turned to run along the player's forward)
            _model.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity); _model.transform.localScale = Vector3.one;
            var b = TackleBoxes.Bounds(_model);
            _top = b.max.y; _bottom = b.min.y;
            _turn = b.size.x > b.size.z ? Quaternion.Euler(0f, 90f, 0f) : Quaternion.identity;
            // (the lid stays shut while it's carried; it only opens on a set-down box)
        }
    }

    internal static class TackleBoxesScale { public const float Held = 0.75f, Hip = 0.55f; }
}
