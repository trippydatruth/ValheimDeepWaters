using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Two dedicated tackle slots, bait and hook, next to the player inventory. Fishing casts with whatever is
    /// in them. The slots are a real Inventory (2x1) shown with a clone of Valheim's own inventory grid, so
    /// drag and drop, split, tooltips and right-click all behave like any other slot. Its contents are saved
    /// in the player's custom data and go into the tombstone on death, like the rest of the inventory.
    /// </summary>
    internal static class Tackle
    {
        public const int RodSlot = 0, BaitSlot = 1, HookSlot = 2, WeightSlot = 3, LeaderSlot = 4, Slots = 5;
        private const string SaveKey = "vdw_tackle2";
        private const string OldSaveKey = "vdw_tackle";      // before the rod slot: bait at 0, hook at 1

        private static Inventory? _inv;
        private static Player? _owner;

        /// <summary>The tackle inventory of this player, loaded from their saved data on first use.</summary>
        public static Inventory Get(Player player)
        {
            if (_inv == null || _owner != player) Load(player);
            return _inv!;
        }

        public static ItemDrop.ItemData? ItemIn(Player player, int slot) => Get(player).GetItemAt(slot, 0);

        /// <summary>Which slot an item belongs in: bait (or a lure's trailer), hook (or a lure), or -1 for anything else.</summary>
        public static int SlotFor(ItemDrop.ItemData? item)
        {
            string? name = item?.m_shared?.m_name;
            if (name == null) return -1;
            if (ContentRegistry.RodByItemName.ContainsKey(name)) return RodSlot;
            if (ContentRegistry.TackleByItemName.TryGetValue(name, out var gear)) return gear.IsLeader ? LeaderSlot : WeightSlot;
            if (ContentRegistry.BaitByItemName.TryGetValue(name, out var bait)) return bait.IsLure ? HookSlot : BaitSlot;
            if (ContentRegistry.HookByItemName.ContainsKey(name)) return HookSlot;
            return -1;
        }

        /// <summary>The lure in the hook slot, if it holds a lure rather than a plain hook.</summary>
        public static BaitDefinition? LureOn(Player player)
        {
            var name = ItemIn(player, HookSlot)?.m_shared?.m_name;
            return name != null && ContentRegistry.BaitByItemName.TryGetValue(name, out var b) && b.IsLure ? b : null;
        }

        /// <summary>
        /// Puts a stack from the player's inventory into its tackle slot. Whatever was there goes back to the
        /// inventory (if there's room), so this is also how bait and hooks get swapped.
        /// </summary>
        public static bool Equip(Player player, ItemDrop.ItemData item)
        {
            int slot = SlotFor(item);
            if (slot < 0) return false;
            if (slot == RodSlot) return PutRodInSlot(player, item, hold: true);

            var inv = Get(player);
            var pack = player.GetInventory();
            var box = TackleBoxes.WornContents(player);
            // it may come from the inventory or the tackle box you're wearing
            var from = pack.ContainsItem(item) ? pack : box != null && box.ContainsItem(item) ? box : pack;
            var current = inv.GetItemAt(slot, 0);
            if (current != null && current.m_shared.m_name != item.m_shared.m_name)
            {
                // what was in the slot goes back to the inventory, or into the box when the inventory's full
                var back = pack.CanAddItem(current) ? pack : box != null && box.CanAddItem(current) ? box : null;
                if (back == null)
                {
                    player.Message(MessageHud.MessageType.Center, "No room in your inventory to swap it out.");
                    return false;
                }
                back.MoveItemToThis(inv, current);
            }
            return inv.MoveItemToThis(from, item, item.m_stack, slot, 0);
        }

        /// <summary>Everything that could go in this slot, from the inventory and the tackle box you're wearing.</summary>
        private static IEnumerable<ItemDrop.ItemData> Carried(Player player) =>
            player.GetInventory().GetAllItems().Concat(TackleBoxes.WornContents(player)?.GetAllItems() ?? Enumerable.Empty<ItemDrop.ItemData>());

        /// <summary>Moves a tackle item back into the player's inventory.</summary>
        public static bool Unequip(Player player, ItemDrop.ItemData item)
        {
            if (!player.GetInventory().CanAddItem(item)) return false;
            if (SlotFor(item) == RodSlot)
            {
                // the very same item moves, so a rod in hand stays in hand
                Get(player).RemoveItem(item);
                player.GetInventory().AddItem(item);
                return true;
            }
            player.GetInventory().MoveItemToThis(Get(player), item);
            return true;
        }

        // ------------------------------------------------------------------ the rod slot

        public static ItemDrop.ItemData? RodIn(Player player) => ItemIn(player, RodSlot);

        // ------------------------------------------------------------------ weight and leader

        public static TackleDefinition? WeightOn(Player player) => GearIn(player, WeightSlot);
        public static TackleDefinition? LeaderOn(Player player) => GearIn(player, LeaderSlot);

        private static TackleDefinition? GearIn(Player player, int slot)
        {
            var name = ItemIn(player, slot)?.m_shared?.m_name;
            return name != null && ContentRegistry.TackleByItemName.TryGetValue(name, out var g) ? g : null;
        }

        /// <summary>Leader lengths you can set, in metres.</summary>
        public static readonly float[] LeaderLengths = { 0.5f, 1f, 1.5f, 2f, 2.5f, 3f, 4f, 5f, 6f, 8f, 10f, 12f, 15f, 20f, 25f, 30f, 40f };
        private const string LeaderKey = "vdw_leader_len";

        /// <summary>How long the leader is set (saved with the character), 2 m to start with.</summary>
        public static float LeaderLength(Player player) =>
            player.m_customData.TryGetValue(LeaderKey, out var s) && float.TryParse(s, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float v)
                ? Mathf.Clamp(v, LeaderLengths[0], LeaderLengths[LeaderLengths.Length - 1]) : 2f;

        /// <summary>One step longer (+1) or shorter (-1).</summary>
        public static void StepLeader(Player player, int dir)
        {
            float now = LeaderLength(player);
            int i = 0;
            while (i < LeaderLengths.Length - 1 && LeaderLengths[i] < now - 0.01f) i++;
            i = Mathf.Clamp(i + dir, 0, LeaderLengths.Length - 1);
            player.m_customData[LeaderKey] = LeaderLengths[i].ToString(System.Globalization.CultureInfo.InvariantCulture);
        }

        /// <summary>
        /// Puts a rod from the inventory into the rod slot (the rod already there goes back to the inventory), and takes
        /// it in hand if asked. The items themselves move, not copies, so whatever is held stays held.
        /// </summary>
        public static bool PutRodInSlot(Player player, ItemDrop.ItemData rod, bool hold)
        {
            var inv = Get(player);
            var pack = player.GetInventory();
            var current = inv.GetItemAt(RodSlot, 0);
            if (current != rod)
            {
                if (current != null)
                {
                    if (!pack.ContainsItem(rod) && !pack.HaveEmptySlot())
                    {
                        player.Message(MessageHud.MessageType.Center, "No room in your inventory to swap it out.");
                        return false;
                    }
                    inv.RemoveItem(current);
                    pack.RemoveItem(rod);
                    pack.AddItem(current);
                }
                else pack.RemoveItem(rod);
                inv.AddItem(rod, new Vector2i(RodSlot, 0));
            }
            if (hold && !player.IsItemEquiped(rod)) player.EquipItem(rod);
            return true;
        }

        /// <summary>The rod key (and right-clicking the rod slot): takes the rod in the slot in hand, or puts it away.</summary>
        public static void ToggleRod(Player player)
        {
            var rod = RodIn(player);
            if (rod == null)
            {
                // a rod still carried in the inventory is put in the slot and taken in hand
                var carried = player.GetInventory().GetAllItems().FirstOrDefault(i => SlotFor(i) == RodSlot);
                if (carried != null) { PutRodInSlot(player, carried, hold: true); return; }
                player.Message(MessageHud.MessageType.Center, "No rod in your tackle. Put one in the rod slot (right-click it in your inventory).");
                return;
            }
            if (player.IsItemEquiped(rod)) player.UnequipItem(rod);
            else player.EquipItem(rod);
        }

        /// <summary>
        /// Vanilla's own moves (dragging between grids, into chests) copy the item, which would leave the old copy of
        /// a rod held. A held rod that's in neither the inventory nor the tackle is put down, and the copy that was
        /// moved (still marked as held) is taken up instead.
        /// </summary>
        public static void CheckHeldRod(Player player)
        {
            var held = player.GetCurrentWeapon();
            if (held == null || SlotFor(held) != RodSlot) return;
            var inv = Get(player);
            if (inv.ContainsItem(held) || player.GetInventory().ContainsItem(held)) return;
            player.UnequipItem(held, false);
            var moved = inv.GetAllItems().Concat(player.GetInventory().GetAllItems()).FirstOrDefault(i => i.m_equipped && SlotFor(i) == RodSlot);
            if (moved != null) { moved.m_equipped = false; player.EquipItem(moved, false); }
        }

        /// <summary>B / H: swap the slot to the next kind of bait or hook in the inventory.</summary>
        public static void CycleSlot(Player player, int slot)
        {
            string noun = slot == BaitSlot ? (LureOn(player) != null ? "trailer" : "bait") : "hook or lure";
            var current = ItemIn(player, slot)?.m_shared.m_name;
            var candidates = Carried(player)
                .Where(i => SlotFor(i) == slot)
                .GroupBy(i => i.m_shared.m_name)
                .OrderBy(g => g.Key)
                .ToList();
            if (candidates.Count == 0)
            {
                player.Message(MessageHud.MessageType.Center, current == null ? $"You have no {noun} to put in your tackle." : $"No other {noun} in your inventory.");
                return;
            }

            // Next name after the current one, wrapping around.
            var next = candidates.FirstOrDefault(g => string.CompareOrdinal(g.Key, current ?? "") > 0) ?? candidates[0];
            var stack = next.OrderByDescending(i => i.m_stack).First();
            if (Equip(player, stack))
                player.Message(MessageHud.MessageType.Center, $"{char.ToUpper(noun[0]) + noun.Substring(1)}: {Loc.Text(stack.m_shared.m_name)} x{ItemIn(player, slot)?.m_stack ?? 0}");
        }

        /// <summary>Uses up one item from a slot, topping it up from the inventory when it runs out.</summary>
        public static void UseOne(Player player, int slot)
        {
            var inv = Get(player);
            var item = inv.GetItemAt(slot, 0);
            if (item == null) return;

            string name = item.m_shared.m_name;
            inv.RemoveItem(item, 1);
            if (inv.GetItemAt(slot, 0) != null) return;

            // the inventory first, then the tackle box you're wearing
            var refill = player.GetInventory().GetAllItems().Where(i => i.m_shared.m_name == name).OrderByDescending(i => i.m_stack).FirstOrDefault()
                ?? TackleBoxes.WornContents(player)?.GetAllItems().Where(i => i.m_shared.m_name == name).OrderByDescending(i => i.m_stack).FirstOrDefault();
            if (refill != null) Equip(player, refill);
        }

        // ------------------------------------------------------------------ saving

        private static void Load(Player player)
        {
            _owner = player;
            _inv = new Inventory("Tackle", null, Slots, 1);
            if (player.m_customData.TryGetValue(SaveKey, out var data) && !string.IsNullOrEmpty(data))
            {
                try { _inv.Load(new ZPackage(data)); }
                catch (Exception ex) { Plugin.Log.LogWarning($"Tackle: could not load saved slots ({ex.Message})."); }
            }
            else if (player.m_customData.TryGetValue(OldSaveKey, out var old) && !string.IsNullOrEmpty(old))
            {
                // saved before the rod slot: everything moves one slot along
                try
                {
                    var was = new Inventory("Tackle", null, 2, 1);
                    was.Load(new ZPackage(old));
                    foreach (var item in was.GetAllItems().ToList())
                        _inv.AddItem(item, new Vector2i(item.m_gridPos.x + 1, 0));
                    player.m_customData.Remove(OldSaveKey);
                }
                catch (Exception ex) { Plugin.Log.LogWarning($"Tackle: could not load saved slots ({ex.Message})."); }
            }
            Tidy(player, _inv);
            _inv.m_onChanged += () => { Save(player); CheckHeldRod(player); };

            // the rod was in hand when the game was saved: take it up again
            var rod = _inv.GetItemAt(RodSlot, 0);
            if (rod != null && rod.m_equipped)
            {
                rod.m_equipped = false;
                player.EquipItem(rod, false);
            }
        }

        // ------------------------------------------------------------------ the rod in the slot counts as carried

        [ThreadStatic] private static bool _equippingFromTackle;

        /// <summary>Valheim only lets you hold what's in your inventory; a rod in the rod slot can be held too.</summary>
        [HarmonyPatch(typeof(Humanoid), nameof(Humanoid.EquipItem))]
        private static class EquipFromTacklePatch
        {
            private static void Prefix(Humanoid __instance, ItemDrop.ItemData item) =>
                _equippingFromTackle = item != null && __instance == _owner && _inv != null && _inv.ContainsItem(item);

            private static void Finalizer() => _equippingFromTackle = false;
        }

        [HarmonyPatch(typeof(Inventory), nameof(Inventory.ContainsItem))]
        private static class ContainsTackleRodPatch
        {
            private static void Postfix(Inventory __instance, ItemDrop.ItemData item, ref bool __result)
            {
                if (!__result && _equippingFromTackle && _owner != null && __instance == _owner.GetInventory() && _inv != null && _inv.ContainsItem(item))
                    __result = true;
            }
        }

        /// <summary>A worn rod in the slot can be repaired at its station like one in the inventory.</summary>
        [HarmonyPatch(typeof(Inventory), nameof(Inventory.GetWornItems))]
        private static class RepairTackleRodPatch
        {
            private static void Postfix(Inventory __instance, List<ItemDrop.ItemData> worn)
            {
                if (_owner == null || _inv == null || __instance != _owner.GetInventory()) return;
                foreach (var item in _inv.GetAllItems())
                    if (item.m_shared.m_useDurability && item.m_shared.m_canBeReparied && item.m_durability < item.GetMaxDurability() && !worn.Contains(item))
                        worn.Add(item);
            }
        }

        /// <summary>The rod in the slot shows up for upgrading at its station...</summary>
        [HarmonyPatch(typeof(Inventory), nameof(Inventory.GetAllItems), new[] { typeof(string), typeof(List<ItemDrop.ItemData>) })]
        private static class UpgradeListsTackleRodPatch
        {
            private static void Postfix(Inventory __instance, string name, List<ItemDrop.ItemData> items)
            {
                if (_owner == null || _inv == null || __instance != _owner.GetInventory()) return;
                var rod = _inv.GetItemAt(RodSlot, 0);
                if (rod != null && rod.m_shared.m_name == name && !items.Contains(rod)) items.Add(rod);
            }
        }

        /// <summary>
        /// ...and moves into the inventory just before it's upgraded: upgrading takes the old item out of the inventory
        /// and puts the new one in, and from the slot the old one would have stayed (two rods).
        /// </summary>
        [HarmonyPatch(typeof(InventoryGui), "DoCrafting")]
        private static class UpgradeFromSlotPatch
        {
            private static readonly FieldInfo? UpgradeItem = AccessTools.Field(typeof(InventoryGui), "m_craftUpgradeItem");

            private static bool Prefix(InventoryGui __instance, Player player)
            {
                if (_owner != player || _inv == null || !(UpgradeItem?.GetValue(__instance) is ItemDrop.ItemData item) || !_inv.ContainsItem(item)) return true;
                if (!player.GetInventory().HaveEmptySlot())
                {
                    player.Message(MessageHud.MessageType.Center, "Make room in your inventory to upgrade the rod.");
                    return false;
                }
                _inv.RemoveItem(item);
                player.GetInventory().AddItem(item);
                return true;
            }
        }

        /// <summary>
        /// Anything saved in the wrong slot (a lure left in the bait slot from before lures went on the hook slot)
        /// moves to its own slot if that's free, or back to the inventory.
        /// </summary>
        private static void Tidy(Player player, Inventory inv)
        {
            foreach (var item in inv.GetAllItems().ToList())
            {
                int want = SlotFor(item);
                if (want == item.m_gridPos.x) continue;
                if (want >= 0 && inv.GetItemAt(want, 0) == null) { item.m_gridPos = new Vector2i(want, 0); continue; }
                var pack = player.GetInventory();
                if (pack != null && pack.CanAddItem(item)) pack.MoveItemToThis(inv, item);
            }
        }

        private static void Save(Player player)
        {
            if (_inv == null || _owner != player) return;
            var pkg = new ZPackage();
            _inv.Save(pkg);
            player.m_customData[SaveKey] = pkg.GetBase64();
        }

        [HarmonyPatch(typeof(Player), nameof(Player.Load))]
        private static class PlayerLoadPatch
        {
            // Saved data arrives after spawn: load the slots now (also takes up a rod that was in hand when saved).
            private static void Postfix(Player __instance) => Load(__instance);
        }

        [HarmonyPatch(typeof(Player), nameof(Player.Save))]
        private static class PlayerSavePatch
        {
            private static void Prefix(Player __instance) => Save(__instance);
        }

        [HarmonyPatch(typeof(Player), nameof(Player.CreateTombStone))]
        private static class TombstonePatch
        {
            // Tackle goes into the tombstone with everything else: move it into the inventory first (that also makes
            // sure there is a tombstone when the tackle is all you carried).
            private static void Prefix(Player __instance)
            {
                if (_owner != __instance || _inv == null) return;
                foreach (var item in _inv.GetAllItems().ToList())
                    __instance.GetInventory().MoveItemToThis(_inv, item);
            }
        }

        /// <summary>
        /// Tackle that didn't fit in a full inventory goes into the grave on a row of its own (it stayed in the tackle
        /// slots, so it survived death).
        /// </summary>
        [HarmonyPatch(typeof(Inventory), nameof(Inventory.MoveInventoryToGrave))]
        private static class GravePatch
        {
            private static void Postfix(Inventory __instance, Inventory original)
            {
                var player = Player.m_localPlayer;
                if (player == null || _owner != player || _inv == null || original != player.GetInventory()) return;
                var left = _inv.GetAllItems().ToList();
                if (left.Count == 0) return;
                if (HeightField == null || ItemsField == null || !(ItemsField.GetValue(__instance) is List<ItemDrop.ItemData> items)) return;
                int row = (int)HeightField.GetValue(__instance);
                HeightField.SetValue(__instance, row + 1);
                for (int i = 0; i < left.Count; i++)
                {
                    _inv.RemoveItem(left[i]);
                    left[i].m_gridPos = new Vector2i(i, row);
                    items.Add(left[i]);
                }
                ChangedMethod?.Invoke(__instance, new object[] { false, false });
            }

            private static readonly FieldInfo? HeightField = AccessTools.Field(typeof(Inventory), "m_height");
            private static readonly FieldInfo? ItemsField = AccessTools.Field(typeof(Inventory), "m_inventory");
            private static readonly MethodInfo? ChangedMethod = AccessTools.Method(typeof(Inventory), "Changed");
        }
    }

    /// <summary>
    /// Lets the tackle panel be dragged anywhere by its wood (a drag that starts on a slot is left alone). Where it's put
    /// is kept in the config; a double-click on it hands it back to following the inventory.
    /// </summary>
    internal sealed class TacklePanelDrag : MonoBehaviour, UnityEngine.EventSystems.IBeginDragHandler, UnityEngine.EventSystems.IDragHandler,
        UnityEngine.EventSystems.IEndDragHandler, UnityEngine.EventSystems.IPointerClickHandler
    {
        private RectTransform? _panel;
        private Transform? _slots;
        private bool _dragging;

        /// <summary>A drag is under way: the panel isn't placed by TackleUi.Position meanwhile (it put it back every frame).</summary>
        public static bool Dragging { get; private set; }
        private Vector2 _grab;

        public void Init(RectTransform panel, Transform slots) { _panel = panel; _slots = slots; }

        private bool OnSlots(UnityEngine.EventSystems.PointerEventData e)
        {
            var hit = e.pointerPressRaycast.gameObject ?? e.pointerCurrentRaycast.gameObject;
            return hit != null && ((_slots != null && hit.transform.IsChildOf(_slots)) || hit.GetComponentInParent<Button>() != null);
        }

        private bool Local(UnityEngine.EventSystems.PointerEventData e, out Vector2 p)
        {
            p = default;
            return _panel != null && _panel.parent is RectTransform parent &&
                   RectTransformUtility.ScreenPointToLocalPointInRectangle(parent, e.position, e.pressEventCamera, out p);
        }

        public void OnBeginDrag(UnityEngine.EventSystems.PointerEventData e)
        {
            _dragging = _panel != null && !OnSlots(e) && Local(e, out var p);
            if (_dragging && Local(e, out var at)) _grab = at - _panel!.anchoredPosition;
            Dragging = _dragging;
        }

        public void OnDrag(UnityEngine.EventSystems.PointerEventData e)
        {
            if (_dragging && Local(e, out var p)) _panel!.anchoredPosition = p - _grab;
        }

        public void OnEndDrag(UnityEngine.EventSystems.PointerEventData e)
        {
            if (!_dragging || _panel == null) return;
            _dragging = Dragging = false;
            TackleUi.CustomPosition = _panel.anchoredPosition;
            Plugin.Log.LogDebug($"Tackle panel moved to {_panel.anchoredPosition}.");
        }

        public void OnPointerClick(UnityEngine.EventSystems.PointerEventData e)
        {
            if (e.clickCount == 2 && !OnSlots(e)) TackleUi.CustomPosition = null;
        }
    }

    /// <summary>The tackle panel inside the inventory screen.</summary>
    internal static class TackleUi
    {
        public static InventoryGrid? Grid;

        private static readonly FieldInfo? DragItemField = AccessTools.Field(typeof(InventoryGui), "m_dragItem");
        private static bool _failed;

        private static RectTransform? _panel;
        private static TextMeshProUGUI? _baitLabel, _hookLabel, _stats, _leaderLen, _rigLabel;

        /// <summary>
        /// Builds the panel from a copy of Valheim's chest panel, so the wood background, title and slot cells
        /// look exactly like the rest of the inventory screen. Its buttons and weight readout are removed and
        /// it's shrunk to two slots.
        /// </summary>
        private static void Build(InventoryGui gui)
        {
            try
            {
                float space = gui.m_playerGrid.m_elementSpace;
                const float padX = 18f, top = 46f, labelH = 22f, rowH = 26f, statsH = 58f, padBottom = 10f;
                float w = space * Tackle.Slots + padX * 2f, h = top + space + labelH + rowH + statsH + padBottom;

                var panelGo = UnityEngine.Object.Instantiate(gui.m_container.gameObject, gui.m_player);
                panelGo.name = "VDW_Tackle";
                var prt = (RectTransform)panelGo.transform;

                string titleName = gui.m_containerName.gameObject.name;
                string weightName = gui.m_containerWeight != null ? gui.m_containerWeight.gameObject.name : "";

                // The panel's own UI groups would fight InventoryGui's; the grid uses the player grid's instead.
                foreach (var handler in panelGo.GetComponentsInChildren<UIGroupHandler>(true)) UnityEngine.Object.DestroyImmediate(handler);
                foreach (var cg in panelGo.GetComponentsInChildren<CanvasGroup>(true)) { cg.alpha = 1f; cg.interactable = true; cg.blocksRaycasts = true; }
                foreach (var btn in panelGo.GetComponentsInChildren<Button>(true)) UnityEngine.Object.DestroyImmediate(btn.gameObject);
                foreach (var tmp in panelGo.GetComponentsInChildren<TMP_Text>(true))
                {
                    if (tmp.gameObject.name != weightName) continue;
                    // The weight readout and the icon grouped with it.
                    var group = tmp.transform.parent != prt ? tmp.transform.parent : tmp.transform;
                    UnityEngine.Object.DestroyImmediate(group.gameObject);
                    break;
                }

                var grid = panelGo.GetComponentInChildren<InventoryGrid>(true);
                var title = panelGo.GetComponentsInChildren<TMP_Text>(true).FirstOrDefault(t => t.gameObject.name == titleName);

                prt.anchorMin = prt.anchorMax = gui.m_player.pivot;
                prt.pivot = Vector2.zero;
                prt.sizeDelta = new Vector2(w, h + Tuck);
                // First child = drawn first, so the inventory's own art covers the tucked-in top edge.
                prt.SetAsFirstSibling();
                panelGo.SetActive(true);

                // Grid: emptied, two cells, under the title.
                foreach (Transform child in grid.m_gridRoot) UnityEngine.Object.Destroy(child.gameObject);
                foreach (var scroll in grid.GetComponentsInChildren<Scrollbar>(true)) scroll.gameObject.SetActive(false);
                var grt = (RectTransform)grid.transform;
                grt.anchorMin = grt.anchorMax = new Vector2(0f, 1f);
                grt.pivot = new Vector2(0f, 1f);
                grt.anchoredPosition = new Vector2(padX, -(top + Tuck));
                grt.sizeDelta = new Vector2(space * Tackle.Slots, space);

                if (title != null)
                {
                    var trt = title.rectTransform;
                    trt.anchorMin = new Vector2(0f, 1f);
                    trt.anchorMax = new Vector2(1f, 1f);
                    trt.pivot = new Vector2(0.5f, 1f);
                    trt.anchoredPosition = new Vector2(0f, -(10f + Tuck));
                    trt.sizeDelta = new Vector2(0f, 32f);
                    title.alignment = TextAlignmentOptions.Center;
                    title.text = "Tackle";
                }

                // Same handlers the vanilla grids use, so dragging, splitting and right-click work as usual.
                var t = typeof(InventoryGui);
                grid.m_onSelected = (Action<InventoryGrid, ItemDrop.ItemData, Vector2i, InventoryGrid.Modifier>)Delegate.CreateDelegate(
                    typeof(Action<InventoryGrid, ItemDrop.ItemData, Vector2i, InventoryGrid.Modifier>), gui, AccessTools.Method(t, "OnSelectedItem"));
                grid.m_onReleased = (Action<InventoryGrid, ItemDrop.ItemData, Vector2i>)Delegate.CreateDelegate(
                    typeof(Action<InventoryGrid, ItemDrop.ItemData, Vector2i>), gui, AccessTools.Method(t, "OnReleasedItem"));
                grid.m_onRightClick = (Action<InventoryGrid, ItemDrop.ItemData, Vector2i>)Delegate.CreateDelegate(
                    typeof(Action<InventoryGrid, ItemDrop.ItemData, Vector2i>), gui, AccessTools.Method(t, "OnRightClickItem"));
                grid.m_onEnter = (Action<InventoryGrid, Vector2i>)Delegate.CreateDelegate(
                    typeof(Action<InventoryGrid, Vector2i>), gui, AccessTools.Method(t, "OnEnterElement"));
                grid.CanDropDragOntoItem = (Func<ItemDrop.ItemData, bool>)Delegate.CreateDelegate(
                    typeof(Func<ItemDrop.ItemData, bool>), gui, AccessTools.Method(t, "CanDropDragOntoItem"));
                grid.m_uiGroup = gui.m_playerGrid.m_uiGroup;
                grid.OnMoveToLowerInventoryGrid = null;
                grid.OnMoveToUpperInventoryGrid = null;
                grid.OnSetTouchSelection = null;

                // Slot captions in the panel's own font.
                var font = title != null ? title.font : gui.m_containerName.font;
                var caption = new Color(0.93f, 0.82f, 0.62f);
                float labelY = -(top + Tuck + space + 2f);
                AddLabel(prt, "Rod", font, 15f, caption, new Vector2(padX + space * Tackle.RodSlot, labelY), new Vector2(space, labelH));
                _baitLabel = AddLabel(prt, "Bait", font, 15f, caption, new Vector2(padX + space * Tackle.BaitSlot, labelY), new Vector2(space, labelH));
                _hookLabel = AddLabel(prt, "Hook", font, 15f, caption, new Vector2(padX + space * Tackle.HookSlot, labelY), new Vector2(space, labelH));
                AddLabel(prt, "Weight", font, 15f, caption, new Vector2(padX + space * Tackle.WeightSlot, labelY), new Vector2(space, labelH));
                AddLabel(prt, "Leader", font, 15f, caption, new Vector2(padX + space * Tackle.LeaderSlot, labelY), new Vector2(space, labelH));

                // the leader's length: - [length] +, under the leader slot
                float rowY = labelY - labelH - 2f, cx = padX + space * Tackle.LeaderSlot;
                AddButton(prt, "-", font, new Vector2(cx - 14f, rowY), new Vector2(24f, 22f), () => { if (Player.m_localPlayer != null) Tackle.StepLeader(Player.m_localPlayer, -1); });
                _leaderLen = AddLabel(prt, "", font, 14f, Color.white, new Vector2(cx + 10f, rowY), new Vector2(space - 20f, 22f));
                AddButton(prt, "+", font, new Vector2(cx + space - 10f, rowY), new Vector2(24f, 22f), () => { if (Player.m_localPlayer != null) Tackle.StepLeader(Player.m_localPlayer, 1); });
                _rigLabel = AddLabel(prt, "", font, 13f, new Color(0.62f, 0.86f, 0.93f), new Vector2(padX - 6f, rowY), new Vector2(space * Tackle.LeaderSlot - 18f, 22f));
                _rigLabel.alignment = TextAlignmentOptions.MidlineLeft;

                // the rod in the slot: its name and level, then its line, cast and wear
                _stats = AddLabel(prt, "", font, 13f, new Color(0.85f, 0.8f, 0.7f), new Vector2(padX - 6f, rowY - rowH), new Vector2(space * Tackle.Slots + 12f, statsH));
                _stats.alignment = TextAlignmentOptions.Top;

                // dragged anywhere by its wood (not its slots); double-click the title to put it back. The chest panel's
                // wood doesn't catch the mouse, so an invisible layer under the slots does.
                var catcher = new GameObject("VDW_DragArea", typeof(RectTransform));
                var crt = (RectTransform)catcher.transform;
                crt.SetParent(prt, false);
                crt.SetAsFirstSibling();
                crt.anchorMin = Vector2.zero; crt.anchorMax = Vector2.one;
                crt.offsetMin = Vector2.zero; crt.offsetMax = new Vector2(0f, -Tuck);   // not the part tucked under the inventory
                var img = catcher.AddComponent<Image>();
                img.color = new Color(0f, 0f, 0f, 0f);
                img.raycastTarget = true;
                panelGo.AddComponent<TacklePanelDrag>().Init(prt, grid.transform);

                _panel = prt;
                Grid = grid;
            }
            catch (Exception ex)
            {
                _failed = true;
                Plugin.Log.LogError($"Tackle: could not build the tackle slots ({ex}). Bait and hooks still work from the B and H keys.");
            }
        }

        private const float Tuck = 14f; // how far the panel slides up under the inventory's bottom border

        /// <summary>
        /// Hangs under the inventory's bottom-right corner, tucked behind its border so it reads as part of it.
        /// A chest opens in that spot, so while one is open it steps out beside the inventory instead, past the
        /// armor and weight readouts. Re-done every frame since the inventory grows with extra rows.
        /// </summary>
        private static void Position(InventoryGui gui)
        {
            if (_panel == null || TacklePanelDrag.Dragging) return;
            var player = gui.m_player;
            if (CustomPosition is Vector2 custom) { _panel.anchoredPosition = custom; return; }

            if (!gui.IsContainerOpen())
            {
                float x = player.rect.xMax - _panel.sizeDelta.x;
                _panel.anchoredPosition = new Vector2(x, DrawnBottom(player, x, player.rect.xMax) - _panel.sizeDelta.y + Tuck);
                return;
            }

            float right = player.rect.xMax;
            var corners = new Vector3[4];
            foreach (var text in new TMP_Text?[] { gui.m_armor, gui.m_weight })
            {
                if (text == null) continue;
                var rt = text.transform.parent is RectTransform parent && parent != player ? parent : text.rectTransform;
                rt.GetWorldCorners(corners);
                foreach (var corner in corners) right = Mathf.Max(right, player.InverseTransformPoint(corner).x);
            }
            _panel.anchoredPosition = new Vector2(right + 8f, player.rect.yMin);
        }

        // ------------------------------------------------------------------ where the player put it

        /// <summary>Where the panel was dragged to (in the inventory's own space), or null to follow the inventory.</summary>
        internal static Vector2? CustomPosition
        {
            get
            {
                var parts = (VdwConfig.TacklePanelPosition.Value ?? "").Split(',');
                var inv = System.Globalization.CultureInfo.InvariantCulture;
                var num = System.Globalization.NumberStyles.Float;
                return parts.Length == 2 && float.TryParse(parts[0], num, inv, out float x) && float.TryParse(parts[1], num, inv, out float y)
                    ? new Vector2(x, y) : (Vector2?)null;
            }
            set => VdwConfig.TacklePanelPosition.Value = value is Vector2 v
                ? string.Format(System.Globalization.CultureInfo.InvariantCulture, "{0:0},{1:0}", v.x, v.y) : "";
        }

        /// <summary>The rod in the slot, for the panel: its name and level over its line, cast and wear.</summary>
        private static string RodStats(Player player)
        {
            var item = Tackle.RodIn(player);
            var def = ContentRegistry.GetRod(item);
            if (item == null || def == null)
                return $"<color=#9a8d78>No rod: put one in the rod slot.\nRight-click it or press {VdwConfig.RodKey.Value} to use it.</color>";
            var rod = RodUpgrades.Scaled(def, item.m_quality);
            string level = item.m_shared.m_maxQuality > 1 ? $"  <color=#c9a85c>level {item.m_quality}</color>" : "";
            string held = player.IsItemEquiped(item) ? "  <color=#8fd18f>in hand</color>" : "";
            string wear = item.m_shared.m_useDurability ? $" · Wear {Mathf.CeilToInt(item.m_durability)}/{Mathf.CeilToInt(item.GetMaxDurability())}" : "";
            return $"<b>{Loc.Text(item.m_shared.m_name)}</b>{level}{held}\nLine {rod.LineCapacity:0} m · Cast {rod.CastDistance:0} m{wear}";
        }

        private static float _bottom, _nextMeasure;

        /// <summary>
        /// The lowest point of what's drawn in the inventory over the panel's width. Usually the inventory's own bottom,
        /// but mods that add rows or slots (quick-slot and extra-slot mods) stretch its art below that, which hid the
        /// panel's slots. Measured twice a second.
        /// </summary>
        private static float DrawnBottom(RectTransform player, float xMin, float xMax)
        {
            if (Time.unscaledTime < _nextMeasure) return _bottom;
            _nextMeasure = Time.unscaledTime + 0.5f;
            float bottom = player.rect.yMin;
            var corners = new Vector3[4];
            foreach (var g in player.GetComponentsInChildren<UnityEngine.UI.Graphic>(false))
            {
                if (g == null || !g.enabled || g.color.a < 0.05f || (_panel != null && g.transform.IsChildOf(_panel))) continue;
                g.rectTransform.GetWorldCorners(corners);
                Vector3 lo = player.InverseTransformPoint(corners[0]), hi = player.InverseTransformPoint(corners[2]);
                if (hi.x < xMin || lo.x > xMax) continue;               // not above the panel
                if (lo.y < bottom - 400f) continue;                     // a tooltip or something far off, not the inventory
                bottom = Mathf.Min(bottom, lo.y);
            }
            return _bottom = bottom;
        }

        /// <summary>A small wooden-dark button with a label, for the leader length.</summary>
        private static void AddButton(RectTransform parent, string text, TMP_FontAsset? font, Vector2 topLeft, Vector2 size, Action onClick)
        {
            var go = new GameObject("VDW_Button_" + text, typeof(RectTransform));
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = new Vector2(0f, 1f);
            rt.pivot = new Vector2(0f, 1f);
            rt.anchoredPosition = topLeft;
            rt.sizeDelta = size;
            var img = go.AddComponent<Image>();
            img.color = new Color(0.25f, 0.17f, 0.1f, 0.95f);
            var btn = go.AddComponent<Button>();
            btn.targetGraphic = img;
            var colors = btn.colors; colors.highlightedColor = new Color(1f, 0.85f, 0.6f); btn.colors = colors;
            btn.onClick.AddListener(() => onClick());
            var label = AddLabel(rt, text, font, 18f, new Color(0.95f, 0.85f, 0.6f), Vector2.zero, size);
            label.alignment = TextAlignmentOptions.Center;
        }

        private static TextMeshProUGUI AddLabel(RectTransform parent, string text, TMP_FontAsset? font, float size, Color color, Vector2 topLeft, Vector2 box)
        {
            // Built inactive so TextMeshPro doesn't go looking for its default font before ours is set.
            var go = new GameObject("VDW_Label_" + text, typeof(RectTransform));
            go.SetActive(false);
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.anchorMin = rt.anchorMax = new Vector2(0f, 1f);
            rt.pivot = new Vector2(0f, 1f);
            rt.anchoredPosition = topLeft;
            rt.sizeDelta = box;
            var label = go.AddComponent<TextMeshProUGUI>();
            if (font != null) label.font = font;
            label.text = text;
            label.fontSize = size;
            label.color = color;
            label.alignment = TextAlignmentOptions.Center;
            label.raycastTarget = false;
            go.SetActive(true);
            return label;
        }

        [HarmonyPatch(typeof(InventoryGui), "UpdateInventory")]
        private static class UpdatePatch
        {
            private static void Postfix(InventoryGui __instance, Player player)
            {
                if (_failed || !VdwConfig.Enabled.Value || player == null) return;
                if (Grid == null) Build(__instance);
                if (Grid == null) return;
                Position(__instance);
                var drag = DragItemField?.GetValue(__instance) as ItemDrop.ItemData;
                Grid.UpdateInventory(Tackle.Get(player), null, drag);
                // With a lure on, the hook slot holds the lure and the bait slot takes an optional trailer.
                bool lure = Tackle.LureOn(player) != null;
                if (_baitLabel != null) _baitLabel.text = lure ? "Trailer" : "Bait";
                if (_hookLabel != null) _hookLabel.text = lure ? "Lure" : "Hook";
                if (_stats != null) _stats.text = RodStats(player);
                if (_leaderLen != null) _leaderLen.text = $"{Tackle.LeaderLength(player):0.#} m";
                if (_rigLabel != null) _rigLabel.text = FishingController.RigSummary(player);
                Tackle.CheckHeldRod(player);
            }
        }

        /// <summary>Only bait goes in the bait slot and only hooks in the hook slot; nothing else can be swapped in.</summary>
        [HarmonyPatch(typeof(InventoryGrid), nameof(InventoryGrid.DropItem))]
        private static class DropPatch
        {
            private static bool Prefix(InventoryGrid __instance, Inventory fromInventory, ItemDrop.ItemData item, Vector2i pos, ref bool __result)
            {
                if (Grid == null || Player.m_localPlayer == null) return true;
                var tackle = Tackle.Get(Player.m_localPlayer);

                if (__instance == Grid && Tackle.SlotFor(item) != pos.x)
                {
                    Player.m_localPlayer.Message(MessageHud.MessageType.Center, pos.x == Tackle.RodSlot ? "Only a fishing rod goes in that slot."
                        : pos.x == Tackle.WeightSlot ? "Only a weight (sinker) goes in that slot." : pos.x == Tackle.LeaderSlot ? "Only a leader goes in that slot."
                        : pos.x == Tackle.BaitSlot ? "Only bait (or a trailer) goes in that slot." : "Only hooks and lures go in that slot.");
                    __result = false;
                    return false;
                }

                // Dragging tackle onto an occupied inventory cell would swap that item into the slot.
                if (fromInventory == tackle && __instance != Grid)
                {
                    var target = __instance.GetInventory().GetItemAt(pos.x, pos.y);
                    if (target != null && target.m_shared.m_name != item.m_shared.m_name && Tackle.SlotFor(target) != item.m_gridPos.x)
                    {
                        Player.m_localPlayer.Message(MessageHud.MessageType.Center, "Drop it on an empty slot.");
                        __result = false;
                        return false;
                    }
                }
                return true;
            }
        }

        /// <summary>Right-click bait or a hook to move it into (or out of) its tackle slot.</summary>
        [HarmonyPatch(typeof(InventoryGui), "OnRightClickItem")]
        private static class RightClickPatch
        {
            private static bool Prefix(InventoryGrid grid, ItemDrop.ItemData item)
            {
                var player = Player.m_localPlayer;
                if (player == null || item == null || Grid == null) return true;

                if (grid == Grid)
                {
                    // the rod: take it in hand or put it away (Ctrl+click takes it out to the inventory)
                    if (Tackle.SlotFor(item) == Tackle.RodSlot) { Tackle.ToggleRod(player); return false; }
                    if (!Tackle.Unequip(player, item)) player.Message(MessageHud.MessageType.Center, "No room in your inventory.");
                    return false;
                }
                if (Tackle.SlotFor(item) < 0 || grid.GetInventory() != player.GetInventory()) return true;
                Tackle.Equip(player, item);
                return false;
            }
        }

        /// <summary>
        /// Ctrl+click (vanilla's "move") puts bait or a hook into its tackle slot, and takes a tackle item back
        /// out. Vanilla would drop it on the ground when no chest is open; with a chest open, inventory items
        /// still go to the chest as usual.
        /// </summary>
        [HarmonyPatch(typeof(InventoryGui), "OnSelectedItem")]
        private static class CtrlClickPatch
        {
            private static bool Prefix(InventoryGui __instance, InventoryGrid grid, ItemDrop.ItemData item, InventoryGrid.Modifier mod)
            {
                var player = Player.m_localPlayer;
                if (mod != InventoryGrid.Modifier.Move || player == null || item == null || Grid == null) return true;

                if (grid == Grid)
                {
                    if (!Tackle.Unequip(player, item)) player.Message(MessageHud.MessageType.Center, "No room in your inventory.");
                    return false;
                }
                if (__instance.IsContainerOpen() || Tackle.SlotFor(item) < 0 || grid.GetInventory() != player.GetInventory()) return true;
                Tackle.Equip(player, item);
                return false;
            }
        }
    }
}
