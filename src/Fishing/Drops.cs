using UnityEngine;

namespace ValheimDeepWaters
{
    internal static class Drops
    {
        /// <summary>
        /// Drops an item in the world. A prefab's own item data has no drop prefab set (only spawned items do), and
        /// ItemDrop.DropItem instantiates that, so it's pointed at the prefab first.
        /// </summary>
        public static void Spawn(ItemDrop prefab, ItemDrop.ItemData data, int amount, Vector3 pos)
        {
            if (data.m_dropPrefab == null) data.m_dropPrefab = prefab.gameObject;
            ItemDrop.DropItem(data, amount, pos, Quaternion.identity);
        }

        public static void Spawn(ItemDrop prefab, int amount, Vector3 pos) => Spawn(prefab, prefab.m_itemData.Clone(), amount, pos);

        /// <summary>Seated or standing on a ship: there's no bank to drop a catch on, and a boat is small.</summary>
        public static bool Aboard(Player player) => player.IsAttachedToShip() || player.GetStandingOnShip() != null;

        /// <summary>
        /// Where a catch lands: on the bank just in front of you, or aboard a ship at your feet (in front of you is
        /// often over the side).
        /// </summary>
        public static Vector3 CatchPos(Player player, float up = 0.4f) =>
            player.transform.position + (Aboard(player) ? Vector3.zero : player.transform.forward * 1.2f) + Vector3.up * up;

        /// <summary>
        /// A catch for the player: aboard a ship it goes straight into the inventory (a drop slides off a rocking boat
        /// and sinks), or at their feet if there's no room; otherwise it's dropped on the bank as usual.
        /// </summary>
        public static void Give(Player player, ItemDrop prefab, ItemDrop.ItemData data, int amount, Vector3 pos)
        {
            if (data.m_dropPrefab == null) data.m_dropPrefab = prefab.gameObject;
            var inv = player.GetInventory();
            if (Aboard(player) && inv != null && inv.CanAddItem(data, amount))
            {
                data.m_stack = amount;
                if (inv.AddItem(data)) return;
            }
            Spawn(prefab, data, amount, pos);
        }

        public static void Give(Player player, ItemDrop prefab, int amount, Vector3 pos) => Give(player, prefab, prefab.m_itemData.Clone(), amount, pos);
    }
}
