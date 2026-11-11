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
        // (new slots go on the end: a saved row of tackle keeps its places)
        public const int RodSlot = 0, BaitSlot = 1, HookSlot = 2, WeightSlot = 3, LeaderSlot = 4, ReelSlot = 5, LineSlot = 6, FloatSlot = 7, Slots = 8;

        /// <summary>Reels, lines and floats as tackle of their own (the server's "Reels, Lines and Floats" setting).</summary>
        public static bool Separate => VdwConfig.SeparateTackle?.Value ?? true;
        public static bool SlotInUse(int slot) => slot < ReelSlot || Separate;
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
            if (ContentRegistry.TackleByItemName.TryGetValue(name, out var gear))
                return gear.IsLeader ? LeaderSlot : gear.IsReel ? (Separate ? ReelSlot : -1) : gear.IsLine ? (Separate ? LineSlot : -1) : WeightSlot;
            if (ContentRegistry.BaitByItemName.TryGetValue(name, out var bait)) return bait.IsLure ? HookSlot : BaitSlot;
            if (ContentRegistry.HookByItemName.ContainsKey(name)) return HookSlot;
            if (Separate && FishingBuffs.FloatByItemName(name) != null) return FloatSlot;
            return -1;
        }

        // ------------------------------------------------------------------ reel, line and float

        public static TackleDefinition? ReelOn(Player player) => Separate ? GearIn(player, ReelSlot) : null;
        public static TackleDefinition? LineOn(Player player) => Separate ? GearIn(player, LineSlot) : null;
        public static BuffDefinition? FloatOn(Player player) => Separate ? FishingBuffs.FloatByItemName(ItemIn(player, FloatSlot)?.m_shared?.m_name) : null;

        /// <summary>One fishing stat from the reel, line and float in the slots (they count like a buff while they're on).</summary>
        public static float GearEffect(Player player, string stat)
        {
            if (!Separate) return 0f;
            float total = 0f;
            if (ReelOn(player) is TackleDefinition reel && reel.Effects.TryGetValue(stat, out var r)) total += r;
            if (LineOn(player) is TackleDefinition line && line.Effects.TryGetValue(stat, out var l)) total += l;
            if (FloatOn(player) is BuffDefinition fl && fl.Effects.TryGetValue(stat, out var f)) total += f;
            return total;
        }

        /// <summary>The rod as it fishes: its upgrade level's stats, with the line in the Line slot added to its own.</summary>
        public static RodDefinition EffectiveRod(Player player, RodDefinition def, int quality)
        {
            var rod = RodUpgrades.Scaled(def, quality);
            if (LineOn(player) is TackleDefinition line)
            {
                if (ReferenceEquals(rod, def)) rod = def.Copy();
                rod.LineCapacity += line.LineCapacity;
                rod.BreakTension = Mathf.Min(99.9f, rod.BreakTension + line.LineStrength);
            }
            return rod;
        }

        // ------------------------------------------------------------------ loadouts

        public const int Loadouts = 3;
        private const string LoadoutKey = "vdw_loadout_";

        private static string KeyOf(ItemDrop.ItemData item) => item.m_dropPrefab != null ? item.m_dropPrefab.name : item.m_shared.m_name;

        public static bool HasLoadout(Player player, int n) => player.m_customData.TryGetValue(LoadoutKey + n, out var s) && !string.IsNullOrEmpty(s);

        /// <summary>Remembers what's in every slot now as loadout n (1..3).</summary>
        public static void SaveLoadout(Player player, int n)
        {
            var parts = new string[Slots];
            for (int s = 0; s < Slots; s++) { var it = ItemIn(player, s); parts[s] = it != null ? KeyOf(it) : ""; }
            player.m_customData[LoadoutKey + n] = string.Join("|", parts);
            player.Message(MessageHud.MessageType.Center, $"Tackle saved as loadout {n}.");
        }

        /// <summary>
        /// Puts loadout n back on: each slot takes the saved item from your inventory or the tackle box you're wearing
        /// (the best one you have: highest level, biggest stack). Slots saved empty are left as they are.
        /// </summary>
        public static void ApplyLoadout(Player player, int n)
        {
            if (!player.m_customData.TryGetValue(LoadoutKey + n, out var saved) || string.IsNullOrEmpty(saved))
            {
                player.Message(MessageHud.MessageType.Center, $"Loadout {n} is empty. Shift+click it to save your tackle to it.");
                return;
            }
            var parts = saved.Split('|');
            var missing = new List<string>();
            for (int s = 0; s < Slots; s++)
            {
                if (!SlotInUse(s)) continue;
                string want = s < parts.Length ? parts[s] : "";
                var cur = ItemIn(player, s);
                if (cur != null && KeyOf(cur) == want) continue;
                bool wasHeld = s == RodSlot && cur != null && player.IsItemEquiped(cur);   // the rod coming in is taken up in its place
                // the loadout is exactly what was saved: anything else in a slot comes out (the inventory, else the
                // tackle box you're wearing), so a slot saved empty is empty again
                if (cur != null && !ClearSlot(player, s, cur))
                {
                    player.Message(MessageHud.MessageType.Center, $"No room to take the {Loc.Text(cur.m_shared.m_name)} out of your tackle.");
                    continue;
                }
                if (string.IsNullOrEmpty(want)) continue;
                cur = ItemIn(player, s);
                var found = Carried(player).Where(i => KeyOf(i) == want && SlotFor(i) == s)
                    .OrderByDescending(i => i.m_quality).ThenByDescending(i => i.m_stack).FirstOrDefault();
                if (found == null) { missing.Add(PrettyName(want)); continue; }
                if (s == RodSlot)
                {
                    if (!player.GetInventory().ContainsItem(found)) { missing.Add(PrettyName(want) + " (in your tackle box)"); continue; }
                    PutRodInSlot(player, found, wasHeld);
                }
                else Equip(player, found);
            }
            player.Message(MessageHud.MessageType.Center, missing.Count == 0 ? $"Loadout {n} on." : $"Loadout {n} on. Not carrying: {string.Join(", ", missing)}");
        }

        /// <summary>Takes an item out of a tackle slot into the inventory (or the worn tackle box). False: nowhere to put it.</summary>
        private static bool ClearSlot(Player player, int slot, ItemDrop.ItemData item)
        {
            if (slot == RodSlot)
            {
                if (FishingController.HandSession != null && player.IsItemEquiped(item)) return false;   // not with its line out
                if (player.IsItemEquiped(item)) player.UnequipItem(item, false);
                if (!player.GetInventory().CanAddItem(item)) return false;
                Get(player).RemoveItem(item);
                player.GetInventory().AddItem(item);
                return true;
            }
            var pack = player.GetInventory();
            var box = TackleBoxes.WornContents(player);
            var to = pack.CanAddItem(item) ? pack : box != null && box.CanAddItem(item) ? box : null;
            if (to == null) return false;
            to.MoveItemToThis(Get(player), item);
            return true;
        }

        private static string PrettyName(string prefab)
        {
            var go = ObjectDB.instance?.GetItemPrefab(prefab);
            var shared = go != null ? go.GetComponent<ItemDrop>()?.m_itemData?.m_shared : null;
            return shared != null ? Loc.Text(shared.m_name) : prefab;
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
            var boxes = TackleBoxes.Reachable(player);
            var box = boxes.FirstOrDefault();
            // it may come from the inventory or any tackle box you can reach
            var from = pack.ContainsItem(item) ? pack : boxes.FirstOrDefault(b => b.ContainsItem(item)) ?? pack;
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
            player.GetInventory().GetAllItems().Concat(TackleBoxes.Reachable(player).SelectMany(b => b.GetAllItems()));

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
                // The swap moves items between grids: the grave-return hook (GraveReturn, on every inventory change) mustn't
                // act half way through. A rod still marked from a grave put itself back in the slot - and in your hands -
                // before the new one got there (a rod taken from a holder came out as the one from your slot). The marks
                // go, too: they're only for a grave.
                bool was = _returning;
                _returning = true;
                try
                {
                    foreach (var r in new[] { rod, current }) if (r != null) { r.m_customData.Remove(SlotKey); r.m_customData.Remove(WasEquippedKey); }
                    if (current != null)
                    {
                        if (!pack.ContainsItem(rod) && !pack.HaveEmptySlot())
                        {
                            player.Message(MessageHud.MessageType.Center, "No room in your inventory to swap it out.");
                            return false;
                        }
                        if (player.IsItemEquiped(current)) player.UnequipItem(current, false);
                        inv.RemoveItem(current);
                        pack.RemoveItem(rod);
                        pack.AddItem(current);
                    }
                    else pack.RemoveItem(rod);
                    if (!inv.AddItem(rod, new Vector2i(RodSlot, 0))) { pack.AddItem(rod); Plugin.Log.LogWarning("Tackle: couldn't put the rod in the rod slot; it's in your inventory."); }
                }
                finally { _returning = was; }
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
                ?? TackleBoxes.Reachable(player).SelectMany(b => b.GetAllItems()).Where(i => i.m_shared.m_name == name).OrderByDescending(i => i.m_stack).FirstOrDefault();
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
        /// <summary>
        /// Reel and line recipes only while reels, lines and floats are separate tackle; re-checked when the setting
        /// changes (a server's value arrives after the world loads) and each time ObjectDB is set up.
        /// </summary>
        public static void ApplySeparateSetting()
        {
            if (ObjectDB.instance == null) return;
            foreach (var r in ObjectDB.instance.m_recipes)
            {
                var n = r?.m_item != null ? r.m_item.name : null;
                if (n != null && (n.StartsWith("VDW_Tackle_reel_") || n.StartsWith("VDW_Tackle_line_"))) r!.m_enabled = Separate;
            }
            if (Player.m_localPlayer != null) TidyNow(Player.m_localPlayer);
        }

        [HarmonyPatch(typeof(ObjectDB), nameof(ObjectDB.CopyOtherDB))]
        private static class RecipesCopyPatch { private static void Postfix() => ApplySeparateSetting(); }
        [HarmonyPatch(typeof(ObjectDB), "Awake")]
        private static class RecipesAwakePatch { private static void Postfix() => ApplySeparateSetting(); }

        /// <summary>Reels, lines and floats turned off by the server: they go back to the inventory.</summary>
        public static void TidyNow(Player player) { if (_inv != null && _owner == player) Tidy(player, _inv); }

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
                // what was worn or held, and which tackle slot each piece of tackle sat in, so looting the grave puts
                // them all back (GraveReturn)
                foreach (var item in __instance.GetInventory().GetAllItems())
                    if (item.m_equipped) item.m_customData[WasEquippedKey] = __instance.GetPlayerID().ToString();
                foreach (var item in _inv.GetAllItems().ToList())
                {
                    item.m_customData[SlotKey] = item.m_gridPos.x.ToString();
                    if (item.m_equipped) item.m_customData[WasEquippedKey] = __instance.GetPlayerID().ToString();
                    __instance.GetInventory().MoveItemToThis(_inv, item);
                }
            }
        }

        private const string SlotKey = "vdw_tackle_slot", WasEquippedKey = "vdw_was_equipped";
        [ThreadStatic] private static bool _returning;

        /// <summary>
        /// Looting your grave puts things back the way they were: tackle into its own tackle slots (the rod too), and
        /// what you had on (armor, weapons, the tackle box) worn again. Runs whenever the inventory changes, so it
        /// works for "take all" and for dragging things out of the grave one at a time.
        /// </summary>
        [HarmonyPatch(typeof(Inventory), "Changed")]
        private static class GraveReturn
        {
            private static void Postfix(Inventory __instance)
            {
                var player = Player.m_localPlayer;
                if (_returning || player == null || player.IsDead() || __instance != player.GetInventory() || _owner != player || _inv == null) return;
                var marked = __instance.GetAllItems().Where(i => i.m_customData.ContainsKey(SlotKey) || i.m_customData.ContainsKey(WasEquippedKey)).ToList();
                if (marked.Count == 0) return;
                _returning = true;
                try
                {
                    foreach (var item in marked)
                    {
                        bool wear = item.m_customData.TryGetValue(WasEquippedKey, out var who) && who == player.GetPlayerID().ToString();
                        item.m_customData.Remove(WasEquippedKey);
                        if (item.m_customData.TryGetValue(SlotKey, out var s))
                        {
                            item.m_customData.Remove(SlotKey);
                            if (int.TryParse(s, out int slot) && slot == SlotFor(item) && _inv.GetItemAt(slot, 0) == null)
                            {
                                if (slot == RodSlot) { PutRodInSlot(player, item, hold: wear); continue; }
                                _inv.MoveItemToThis(__instance, item, item.m_stack, slot, 0);
                                continue;
                            }
                        }
                        if (wear && !item.m_equipped && item.IsEquipable()) player.EquipItem(item, false);
                    }
                }
                catch (Exception ex) { Plugin.Log.LogWarning($"Tackle: couldn't put your gear back from the grave ({ex.Message})."); }
                finally { _returning = false; }
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
        private static TextMeshProUGUI? _rigLabel, _leaderLen;
        private static Image? _rodPic;
        private static RectTransform? _leaderCtl, _rodRt;
        private static readonly TextMeshProUGUI?[] _captions = new TextMeshProUGUI?[Tackle.Slots];
        private static readonly Image?[] _loadoutBtn = new Image?[Tackle.Loadouts + 1];
        private static float _space, _rowH;
        private static Vector2 _cell0;                      // where the grid put its first cell (the others are moved from there)
        private static UnityEngine.Object? _firstElement;
        private static bool _laidOutSeparate;

        private static readonly FieldInfo? ElementsField = AccessTools.Field(typeof(InventoryGrid), "m_elements");

        // the screen: what's on the line listed on the left, the rod pictured in the middle, its slots to the right
        private const float PadX = 14f, Top = 44f, BarH = 34f, InfoW = 162f, Footer = 24f, PadBottom = 10f;
        private static float _rodW = 80f;                   // the rod picture is 1 wide by 4 high: as wide as its height needs
        private const int Cols = 2, Rows = 4;

        /// <summary>Slot order on the screen, tip to handle (as the line runs from the float back to the reel and rod).</summary>
        private static int[] Order => Tackle.Separate
            ? new[] { Tackle.FloatSlot, Tackle.BaitSlot, Tackle.HookSlot, Tackle.LeaderSlot, Tackle.WeightSlot, Tackle.LineSlot, Tackle.ReelSlot, Tackle.RodSlot }
            : new[] { Tackle.BaitSlot, Tackle.HookSlot, Tackle.LeaderSlot, Tackle.WeightSlot, Tackle.RodSlot };

        private static string Caption(int slot, bool lure) => slot switch
        {
            Tackle.RodSlot => "Rod", Tackle.BaitSlot => lure ? "Trailer" : "Bait", Tackle.HookSlot => lure ? "Lure" : "Hook",
            Tackle.WeightSlot => "Weight", Tackle.LeaderSlot => "Leader", Tackle.ReelSlot => "Reel", Tackle.LineSlot => "Line", _ => "Float"
        };

        private static float RodX => PadX + InfoW;
        private static float SlotsX => RodX + _rodW;
        /// <summary>The rod picture's height for this many rows: the top of the first slot to the bottom of the last.</summary>
        private static float RodH(int rows) => (rows - 1) * _rowH + _space;
        private static float SlotsY => Top + Tuck + BarH;

        /// <summary>
        /// Builds the screen from a copy of Valheim's chest panel, so the wood background, title and slot cells look
        /// like the rest of the inventory screen. Its buttons and weight readout are removed.
        /// </summary>
        private static void Build(InventoryGui gui)
        {
            try
            {
                _space = gui.m_playerGrid.m_elementSpace;
                _rowH = _space + 22f;                                        // cell and caption
                _rodW = RodH(Rows) / 4f;
                float w = SlotsX + Cols * _space + PadX, h = Top + BarH + Rows * _rowH + Footer + PadBottom;

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
                    var group = tmp.transform.parent != prt ? tmp.transform.parent : tmp.transform;
                    UnityEngine.Object.DestroyImmediate(group.gameObject);
                    break;
                }

                var grid = panelGo.GetComponentInChildren<InventoryGrid>(true);
                var title = panelGo.GetComponentsInChildren<TMP_Text>(true).FirstOrDefault(t => t.gameObject.name == titleName);

                prt.anchorMin = prt.anchorMax = gui.m_player.pivot;
                prt.pivot = Vector2.zero;
                prt.sizeDelta = new Vector2(w, h + Tuck);
                prt.SetAsFirstSibling();
                panelGo.SetActive(true);

                // the grid: emptied; its cells are made in one row and moved into place each frame. Its masks would clip
                // every cell below the first row, so they go.
                foreach (Transform child in grid.m_gridRoot) UnityEngine.Object.Destroy(child.gameObject);
                foreach (var scroll in grid.GetComponentsInChildren<Scrollbar>(true)) scroll.gameObject.SetActive(false);
                foreach (var m in grid.GetComponentsInChildren<RectMask2D>(true)) UnityEngine.Object.DestroyImmediate(m);
                foreach (var m in grid.GetComponentsInChildren<Mask>(true)) UnityEngine.Object.DestroyImmediate(m);
                var grt = (RectTransform)grid.transform;
                grt.anchorMin = grt.anchorMax = new Vector2(0f, 1f);
                grt.pivot = new Vector2(0f, 1f);
                grt.anchoredPosition = new Vector2(SlotsX, -SlotsY);
                grt.sizeDelta = new Vector2(_space * Tackle.Slots, Rows * _rowH);

                if (title != null)
                {
                    var trt = title.rectTransform;
                    trt.anchorMin = new Vector2(0f, 1f); trt.anchorMax = new Vector2(1f, 1f);
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

                // dragged anywhere by its wood (not its slots or buttons); double-click it to put it back. The chest panel's
                // wood doesn't catch the mouse, so an invisible layer under everything does.
                var catcher = new GameObject("VDW_DragArea", typeof(RectTransform));
                var crt = (RectTransform)catcher.transform;
                crt.SetParent(prt, false);
                crt.SetAsFirstSibling();
                crt.anchorMin = Vector2.zero; crt.anchorMax = Vector2.one;
                crt.offsetMin = Vector2.zero; crt.offsetMax = new Vector2(0f, -Tuck);
                var img = catcher.AddComponent<Image>();
                img.color = new Color(0f, 0f, 0f, 0f);
                img.raycastTarget = true;
                panelGo.AddComponent<TacklePanelDrag>().Init(prt, grid.transform);

                var font = title != null ? title.font : gui.m_containerName.font;
                var caption = new Color(0.93f, 0.82f, 0.62f);

                // loadouts, centred under the title: 1 2 3 (click to put one on, Shift+click to save your tackle to it)
                float barY = -(Top + Tuck), groupW = 70f + Tackle.Loadouts * 32f, gx = (w - groupW) / 2f;
                var bl = AddLabel(prt, "Loadouts", font, 14f, caption, new Vector2(gx, barY - 2f), new Vector2(68f, 22f));
                bl.alignment = TextAlignmentOptions.MidlineLeft;
                for (int n = 1; n <= Tackle.Loadouts; n++)
                {
                    int k = n;
                    _loadoutBtn[n] = AddButton(prt, n.ToString(), font, new Vector2(gx + 70f + (n - 1) * 32f, barY - 1f), new Vector2(26f, 24f), () =>
                    {
                        var p = Player.m_localPlayer; if (p == null) return;
                        if (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)) Tackle.SaveLoadout(p, k); else Tackle.ApplyLoadout(p, k);
                    });
                }
                var hint = AddLabel(prt, "Shift+click to save", font, 11f, new Color(0.62f, 0.56f, 0.46f), new Vector2(0f, barY - 24f), new Vector2(w, 12f));
                hint.alignment = TextAlignmentOptions.Center;

                // the left: what's on the line, a section a piece, each opened or closed with a click on its name
                BuildSections(prt, font);

                // the middle: the rod, standing tip up from the top slot to the bottom one
                var rodGo = new GameObject("VDW_RodPicture", typeof(RectTransform));
                _rodRt = (RectTransform)rodGo.transform;
                _rodRt.SetParent(prt, false);
                _rodRt.anchorMin = _rodRt.anchorMax = new Vector2(0f, 1f); _rodRt.pivot = new Vector2(0f, 1f);
                _rodRt.anchoredPosition = new Vector2(RodX, -SlotsY);
                _rodRt.sizeDelta = new Vector2(_rodW, RodH(Rows));
                _rodPic = rodGo.AddComponent<Image>();
                _rodPic.preserveAspect = true; _rodPic.raycastTarget = false;

                // the slot captions (moved with their slots)
                for (int s = 0; s < Tackle.Slots; s++)
                    _captions[s] = AddLabel(prt, "", font, 14f, caption, Vector2.zero, new Vector2(_space + 10f, 20f));

                // the rig and how deep it fishes, along the bottom
                _rigLabel = AddLabel(prt, "", font, 13f, new Color(0.62f, 0.86f, 0.93f), new Vector2(PadX, -(h + Tuck - PadBottom - Footer)), new Vector2(w - 2f * PadX, Footer));
                _rigLabel.alignment = TextAlignmentOptions.MidlineLeft;

                _panel = prt;
                Grid = grid;
            }
            catch (Exception ex)
            {
                _failed = true;
                Plugin.Log.LogError($"Tackle: could not build the tackle screen ({ex}). Bait and hooks still work from the B and H keys.");
            }
        }

        /// <summary>
        /// Puts each slot (and its caption) where it goes on the screen, two to a row, tip to handle. The grid makes its
        /// cells in one row; they're moved from where it put the first one. Slots not in use (reels, lines and floats
        /// turned off) are hidden.
        /// </summary>
        private static void Layout(Player player)
        {
            if (Grid == null || !(ElementsField?.GetValue(Grid) is System.Collections.IList els) || els.Count < Tackle.Slots) return;
            if (!(els[0] is Component first)) return;
            if (!ReferenceEquals(first, _firstElement)) { _firstElement = first; _cell0 = ((RectTransform)first.transform).anchoredPosition; }
            bool lure = Tackle.LureOn(player) != null;
            var order = Order;
            for (int s = 0; s < Tackle.Slots; s++)
            {
                int at = Array.IndexOf(order, s);
                if (!(els[s] is Component el)) continue;
                el.gameObject.SetActive(at >= 0);
                var cap = _captions[s];
                if (cap != null) cap.gameObject.SetActive(at >= 0);
                if (at < 0) continue;
                int c = at % Cols, r = at / Cols;
                var ert = (RectTransform)el.transform;
                ert.anchoredPosition = _cell0 + new Vector2(c * _space, -r * _rowH);
                if (cap != null)
                {
                    cap.rectTransform.anchoredPosition = new Vector2(SlotsX + c * _space - 5f, -(SlotsY + r * _rowH + _space + 1f));
                    cap.text = Caption(s, lure);
                    // The cell's top-left corner snapped to where its caption says it is (the caption sits _space + 1 under
                    // the cell's top and 5 left of it). Where the grid first put its cells depends on how it was anchored
                    // when it made them, and once that came out a row low: every cell a row under its caption, the top
                    // row's cells missing and the rod's off the bottom.
                    cap.rectTransform.GetWorldCorners(Corners); var capTL = Corners[1];
                    ert.GetWorldCorners(Corners); var elTL = Corners[1];
                    float k = _panel != null ? _panel.lossyScale.y : 1f;
                    ert.position += new Vector3(capTL.x + 5f * k - elTL.x, capTL.y + (_space + 1f) * k - elTL.y, 0f);
                }
            }
            // the rod reaches from the top row to the bottom one in use
            int rows = (order.Length + Cols - 1) / Cols;
            if (_rodRt != null) _rodRt.sizeDelta = new Vector2(_rodW, RodH(rows));
            _laidOutSeparate = Tackle.Separate;
        }

        private static readonly Vector3[] Corners = new Vector3[4];

        private const float Tuck = 14f; // how far the panel slides up under the inventory's top border

        /// <summary>
        /// Beside the inventory, past its armor and weight readouts, top edges level. Re-done every frame since the
        /// inventory grows with extra rows. Dragged somewhere, it stays there.
        /// </summary>
        private static void Position(InventoryGui gui)
        {
            if (_panel == null || TacklePanelDrag.Dragging) return;
            var player = gui.m_player;
            if (CustomPosition is Vector2 custom) { _panel.anchoredPosition = custom; return; }
            float right = player.rect.xMax;
            var corners = new Vector3[4];
            foreach (var text in new TMP_Text?[] { gui.m_armor, gui.m_weight })
            {
                if (text == null) continue;
                var rt = text.transform.parent is RectTransform parent && parent != player ? parent : text.rectTransform;
                rt.GetWorldCorners(corners);
                foreach (var corner in corners) right = Mathf.Max(right, player.InverseTransformPoint(corner).x);
            }
            _panel.anchoredPosition = new Vector2(right + 8f, player.rect.yMax - _panel.sizeDelta.y + Tuck);
        }

        // ------------------------------------------------------------------ where the player put it

        /// <summary>Where the screen was dragged to (in the inventory's own space), or null to sit beside the inventory.</summary>
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

        // ------------------------------------------------------------------ the left: what's on the line, in sections

        private const string Dim = "#9a8d78", Gold = "#c9a85c", Green = "#8fd18f";
        private const int SecRod = 0, SecReel = 1, SecLine = 2, SecFloat = 3, SecHook = 4, SecBait = 5, SecWeight = 6, SecLeader = 7, Sections = 8;
        private const string OpenKey = "vdw_tackle_open";

        private sealed class Section { public RectTransform Head = null!; public TextMeshProUGUI HeadText = null!, Body = null!; }
        private static readonly Section?[] _sec = new Section?[Sections];

        /// <summary>Which sections are open, saved with the character (the rod and reel open to start with).</summary>
        private static bool IsOpen(Player p, int i)
        {
            string s = p.m_customData.TryGetValue(OpenKey, out var v) ? v : "11000000";
            return i < s.Length && s[i] == '1';
        }

        private static void ToggleOpen(int i)
        {
            var p = Player.m_localPlayer; if (p == null) return;
            var s = (p.m_customData.TryGetValue(OpenKey, out var v) ? v : "11000000").PadRight(Sections, '0').ToCharArray();
            s[i] = s[i] == '1' ? '0' : '1';
            p.m_customData[OpenKey] = new string(s);
        }

        private static void BuildSections(RectTransform prt, TMP_FontAsset? font)
        {
            for (int i = 0; i < Sections; i++)
            {
                int k = i;
                var go = new GameObject("VDW_Section_" + i, typeof(RectTransform));
                var rt = (RectTransform)go.transform;
                rt.SetParent(prt, false);
                rt.anchorMin = rt.anchorMax = new Vector2(0f, 1f); rt.pivot = new Vector2(0f, 1f);
                rt.sizeDelta = new Vector2(InfoW, 18f);
                var bg = go.AddComponent<Image>(); bg.color = new Color(0f, 0f, 0f, 0.001f);   // catches the click
                var btn = go.AddComponent<Button>(); btn.targetGraphic = bg;
                btn.onClick.AddListener(() => ToggleOpen(k));
                var head = AddLabel(rt, "", font, 13f, new Color(0.93f, 0.86f, 0.72f), Vector2.zero, new Vector2(InfoW, 18f));
                head.alignment = TextAlignmentOptions.MidlineLeft;
                head.overflowMode = TextOverflowModes.Ellipsis;
                var body = AddLabel(prt, "", font, 12f, new Color(0.7f, 0.65f, 0.56f), Vector2.zero, new Vector2(InfoW - 10f, 20f));
                body.alignment = TextAlignmentOptions.TopLeft;
                body.textWrappingMode = TextWrappingModes.Normal;
                _sec[i] = new Section { Head = rt, HeadText = head, Body = body };
            }
            // the leader's length, - and + on its row
            var lc = new GameObject("VDW_LeaderLength", typeof(RectTransform));
            _leaderCtl = (RectTransform)lc.transform;
            _leaderCtl.SetParent(prt, false);
            _leaderCtl.anchorMin = _leaderCtl.anchorMax = new Vector2(0f, 1f); _leaderCtl.pivot = new Vector2(1f, 1f);
            _leaderCtl.sizeDelta = new Vector2(74f, 18f);
            AddButton(_leaderCtl, "-", font, new Vector2(0f, 0f), new Vector2(18f, 18f), () => { if (Player.m_localPlayer != null) Tackle.StepLeader(Player.m_localPlayer, -1); });
            _leaderLen = AddLabel(_leaderCtl, "", font, 12f, Color.white, new Vector2(18f, 0f), new Vector2(38f, 18f));
            AddButton(_leaderCtl, "+", font, new Vector2(56f, 0f), new Vector2(18f, 18f), () => { if (Player.m_localPlayer != null) Tackle.StepLeader(Player.m_localPlayer, 1); });
        }

        /// <summary>Each section's name and its stats (empty: nothing to open), or null to leave it out.</summary>
        private static (string head, string body)? SectionText(Player player, int i)
        {
            bool lure = Tackle.LureOn(player) != null;
            switch (i)
            {
                case SecRod:
                {
                    var item = Tackle.RodIn(player);
                    var def = ContentRegistry.GetRod(item);
                    if (item == null || def == null) return ($"<color={Dim}>No rod</color>", $"Put one in the rod slot. Right-click it or press {VdwConfig.RodKey.Value} to use it.");
                    var rod = Tackle.EffectiveRod(player, def, item.m_quality);
                    string level = item.m_shared.m_maxQuality > 1 ? $" <color={Gold}>{item.m_quality}</color>" : "";
                    string held = player.IsItemEquiped(item) ? $" <color={Green}>in hand</color>" : "";
                    float reel = rod.ReelSpeed * (1f + FishingBuffs.Total(player, BuffStat.ReelSpeed));
                    string wear = item.m_shared.m_useDurability ? $"\nWear: {Mathf.CeilToInt(item.m_durability)}/{Mathf.CeilToInt(item.GetMaxDurability())}" : "";
                    return ($"<b>{Loc.Text(item.m_shared.m_name)}</b>{level}{held}",
                            $"Line: {rod.LineCapacity:0} m\nStrength: {rod.BreakTension:0.#}\nCast: {rod.CastDistance:0} m\nReel: {reel:0.#} m/s\nPower: {rod.Power:0.##}{wear}");
                }
                case SecReel when Tackle.Separate:
                    return Piece(Tackle.ItemIn(player, Tackle.ReelSlot), "No reel: the rod's own",
                        Tackle.ReelOn(player) is TackleDefinition reelDef ? string.Join("\n", reelDef.Effects.Select(e => BuffStat.Describe(e.Key, e.Value))) : "");
                case SecLine when Tackle.Separate:
                    return Piece(Tackle.ItemIn(player, Tackle.LineSlot), "No line: the rod's own",
                        Tackle.LineOn(player) is TackleDefinition line ? $"Line +{line.LineCapacity:0} m" + (line.LineStrength > 0f ? $"\nStrength +{line.LineStrength:0.#}" : "") : "");
                case SecFloat when Tackle.Separate:
                    return Piece(Tackle.ItemIn(player, Tackle.FloatSlot), "Plain float",
                        Tackle.FloatOn(player) is BuffDefinition fl ? string.Join("\n", fl.Effects.Select(e => BuffStat.Describe(e.Key, e.Value))) + (fl.FloatLight ? "\nLit after dark" : "") : "");
                case SecHook: return Piece(Tackle.ItemIn(player, Tackle.HookSlot), lure ? "No lure" : "No hook", "", true);
                case SecBait: return Piece(Tackle.ItemIn(player, Tackle.BaitSlot), lure ? "No trailer" : "No bait", "", true);
                case SecWeight: return Piece(Tackle.ItemIn(player, Tackle.WeightSlot), "No weight", "", true);
                case SecLeader: return Piece(Tackle.ItemIn(player, Tackle.LeaderSlot), "No leader", "");
                default: return null;
            }
        }

        private static (string, string) Piece(ItemDrop.ItemData? item, string none, string stats, bool count = false)
        {
            if (item == null) return ($"<color={Dim}>{none}</color>", "");
            string n = $"<b>{Loc.Text(item.m_shared.m_name)}</b>";
            if (count && item.m_stack > 1) n += $" <color={Dim}>x{item.m_stack}</color>";
            return (n, stats);
        }

        /// <summary>Lays the sections out down the left: each name, and its stats under it when it's open.</summary>
        private static void UpdateSections(Player player)
        {
            float y = -SlotsY;
            float bottom = -(SlotsY + Rows * _rowH);
            for (int i = 0; i < Sections; i++)
            {
                var sec = _sec[i]; if (sec == null) continue;
                var t = SectionText(player, i);
                bool show = t != null && y > bottom + 18f;
                sec.Head.gameObject.SetActive(show);
                sec.Body.gameObject.SetActive(false);
                if (!show) continue;
                var (head, body) = t!.Value;
                bool open = IsOpen(player, i) && body.Length > 0;
                string mark = body.Length == 0 ? "   " : open ? "- " : "+ ";
                sec.HeadText.text = $"<color={Dim}>{mark}</color>{head}";
                sec.Head.anchoredPosition = new Vector2(PadX, y);
                y -= 19f;
                if (i == SecLeader && _leaderCtl != null)
                {
                    bool on = Tackle.LeaderOn(player) != null;
                    _leaderCtl.gameObject.SetActive(on);
                    _leaderCtl.anchoredPosition = new Vector2(PadX + InfoW, y + 19f);
                    if (on) sec.HeadText.rectTransform.sizeDelta = new Vector2(InfoW - 78f, 18f);
                }
                if (!open) continue;
                sec.Body.text = body;
                float bh = sec.Body.GetPreferredValues(body, InfoW - 10f, 0f).y;
                sec.Body.rectTransform.sizeDelta = new Vector2(InfoW - 10f, bh);
                sec.Body.rectTransform.anchoredPosition = new Vector2(PadX + 12f, y);
                sec.Body.gameObject.SetActive(true);
                y -= bh + 4f;
            }
        }

        // ------------------------------------------------------------------ the middle: the rod

        private static readonly Dictionary<string, Sprite?> RodPictures = new();

        /// <summary>The rod standing tip up (rod_&lt;id&gt;_full.png beside the icons), or its icon if there's no picture of it.</summary>
        private static Sprite? RodPicture(ItemDrop.ItemData? item)
        {
            var def = ContentRegistry.GetRod(item);
            if (item == null || def == null) return null;
            if (!RodPictures.TryGetValue(def.Id, out var pic))
            {
                pic = null;
                string? png = CustomModels.FindFile("rod_" + def.Id + "_full.png");
                if (png != null)
                {
                    var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false) { name = "rod_" + def.Id + "_full" };
                    if (tex.LoadImage(System.IO.File.ReadAllBytes(png)))
                        pic = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f));
                }
                RodPictures[def.Id] = pic;
            }
            return pic ?? item.GetIcon();
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
        private static Image AddButton(RectTransform parent, string text, TMP_FontAsset? font, Vector2 topLeft, Vector2 size, Action onClick)
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
            return img;
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
                if (_laidOutSeparate != Tackle.Separate) Tackle.TidyNow(player);
                Layout(player);
                UpdateSections(player);
                if (_leaderLen != null) _leaderLen.text = $"{Tackle.LeaderLength(player):0.#} m";
                if (_rigLabel != null) _rigLabel.text = FishingController.RigSummary(player);
                if (_rodPic != null)
                {
                    var pic = RodPicture(Tackle.RodIn(player));
                    _rodPic.sprite = pic;
                    _rodPic.enabled = pic != null;
                }
                // a saved loadout's button is lit; an empty one is dim
                for (int n = 1; n <= Tackle.Loadouts; n++)
                    if (_loadoutBtn[n] != null) _loadoutBtn[n]!.color = Tackle.HasLoadout(player, n) ? new Color(0.42f, 0.29f, 0.14f, 0.95f) : new Color(0.18f, 0.13f, 0.09f, 0.9f);
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
                        : pos.x == Tackle.ReelSlot ? "Only a reel goes in that slot." : pos.x == Tackle.LineSlot ? "Only a fishing line goes in that slot."
                        : pos.x == Tackle.FloatSlot ? "Only a float goes in that slot."
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
