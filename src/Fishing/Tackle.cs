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
        public const int BaitSlot = 0, HookSlot = 1;
        private const string SaveKey = "vdw_tackle";

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

            var inv = Get(player);
            var pack = player.GetInventory();
            var current = inv.GetItemAt(slot, 0);
            if (current != null && current.m_shared.m_name != item.m_shared.m_name)
            {
                if (!pack.CanAddItem(current))
                {
                    player.Message(MessageHud.MessageType.Center, "No room in your inventory to swap it out.");
                    return false;
                }
                pack.MoveItemToThis(inv, current);
            }
            return inv.MoveItemToThis(pack, item, item.m_stack, slot, 0);
        }

        /// <summary>Moves a tackle item back into the player's inventory.</summary>
        public static bool Unequip(Player player, ItemDrop.ItemData item)
        {
            if (!player.GetInventory().CanAddItem(item)) return false;
            player.GetInventory().MoveItemToThis(Get(player), item);
            return true;
        }

        /// <summary>B / H: swap the slot to the next kind of bait or hook in the inventory.</summary>
        public static void CycleSlot(Player player, int slot)
        {
            string noun = slot == BaitSlot ? (LureOn(player) != null ? "trailer" : "bait") : "hook or lure";
            var current = ItemIn(player, slot)?.m_shared.m_name;
            var candidates = player.GetInventory().GetAllItems()
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

            var refill = player.GetInventory().GetAllItems().Where(i => i.m_shared.m_name == name).OrderByDescending(i => i.m_stack).FirstOrDefault();
            if (refill != null) Equip(player, refill);
        }

        // ------------------------------------------------------------------ saving

        private static void Load(Player player)
        {
            _owner = player;
            _inv = new Inventory("Tackle", null, 2, 1);
            if (player.m_customData.TryGetValue(SaveKey, out var data) && !string.IsNullOrEmpty(data))
            {
                try { _inv.Load(new ZPackage(data)); }
                catch (Exception ex) { Plugin.Log.LogWarning($"Tackle: could not load saved slots ({ex.Message})."); }
            }
            Tidy(player, _inv);
            _inv.m_onChanged += () => Save(player);
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
            // Saved data arrives after spawn; reload if the slots were opened before it did.
            private static void Postfix(Player __instance)
            {
                if (_owner == __instance) Load(__instance);
            }
        }

        [HarmonyPatch(typeof(Player), nameof(Player.Save))]
        private static class PlayerSavePatch
        {
            private static void Prefix(Player __instance) => Save(__instance);
        }

        [HarmonyPatch(typeof(Player), nameof(Player.CreateTombStone))]
        private static class TombstonePatch
        {
            // Tackle goes into the tombstone with everything else: move it into the inventory first.
            private static void Prefix(Player __instance)
            {
                if (_owner != __instance || _inv == null) return;
                foreach (var item in _inv.GetAllItems().ToList())
                    __instance.GetInventory().MoveItemToThis(_inv, item);
            }
        }
    }

    /// <summary>The tackle panel inside the inventory screen.</summary>
    internal static class TackleUi
    {
        public static InventoryGrid? Grid;

        private static readonly FieldInfo? DragItemField = AccessTools.Field(typeof(InventoryGui), "m_dragItem");
        private static bool _failed;

        private static RectTransform? _panel;
        private static TextMeshProUGUI? _baitLabel, _hookLabel;

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
                const float padX = 18f, top = 46f, labelH = 22f, padBottom = 12f;
                float w = space * 2f + padX * 2f, h = top + space + labelH + padBottom;

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
                grt.sizeDelta = new Vector2(space * 2f, space);

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
                _baitLabel = AddLabel(prt, "Bait", font, 15f, caption, new Vector2(padX, -(top + Tuck + space + 2f)), new Vector2(space, labelH));
                _hookLabel = AddLabel(prt, "Hook", font, 15f, caption, new Vector2(padX + space, -(top + Tuck + space + 2f)), new Vector2(space, labelH));

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
            if (_panel == null) return;
            var player = gui.m_player;

            if (!gui.IsContainerOpen())
            {
                _panel.anchoredPosition = new Vector2(player.rect.xMax - _panel.sizeDelta.x, player.rect.yMin - _panel.sizeDelta.y + Tuck);
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
                    Player.m_localPlayer.Message(MessageHud.MessageType.Center, pos.x == Tackle.BaitSlot ? "Only bait (or a trailer) goes in that slot." : "Only hooks and lures go in that slot.");
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
