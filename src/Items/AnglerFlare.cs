using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The Angler's Flare: Hildir's Basic Fireworks packed with fish oil. Carried, it fires by itself the moment you hook
    /// a boss fish - a firework goes up over you, everyone gets a ping on the map where you are, and you shout the
    /// boss's name - so friends know where the fight is. One is used each time.
    /// </summary>
    internal static class AnglerFlare
    {
        public const string Prefab = "VDW_AnglerFlare";
        private const string Firework = "FireworksRocket_White";
        private static GameObject? _rocket;   // the vanilla firework's projectile

        public static void Register()
        {
            if (PrefabManager.Instance.GetPrefab(Firework) == null) { Plugin.Log.LogWarning("Angler's Flare: no vanilla fireworks to make it from."); return; }
            var item = new CustomItem(Prefab, Firework, new ItemConfig
            {
                Amount = 1,
                CraftingStation = "piece_workbench",
                MinStationLevel = 2,
                Requirements = new[] { new RequirementConfig(Firework, 1), new RequirementConfig("VDW_Mat_oil", 2) }
            });
            var shared = item.ItemDrop.m_itemData.m_shared;
            _rocket = shared.m_attack?.m_attackProjectile ?? shared.m_secondaryAttack?.m_attackProjectile;
            // (vanilla fireworks have no attack: they're thrown in a campfire, whose effects the flare plays - FireworkEffects)
            shared.m_name = Loc.Token("vdw_angler_flare", "Angler's Flare");
            shared.m_description = Loc.Token("vdw_angler_flare_desc",
                "Hildir's fireworks packed with fish oil. Carry one: when you hook a boss fish it goes up by itself, " +
                "everyone sees where you are on the map, and you shout what you've hooked.");
            // carried, not fired by hand: no attack, nothing to equip
            shared.m_itemType = ItemDrop.ItemData.ItemType.Material;
            shared.m_maxStackSize = 10;
            ItemManager.Instance.AddItem(item);
        }

        private static EffectList? _fireworkFx;

        /// <summary>The Basic Fireworks' effects, as a campfire plays them when they're thrown in.</summary>
        private static EffectList? FireworkEffects()
        {
            if (_fireworkFx != null) return _fireworkFx;
            string? fwName = ObjectDB.instance?.GetItemPrefab(Firework)?.GetComponent<ItemDrop>()?.m_itemData.m_shared.m_name;
            if (fwName == null || ZNetScene.instance == null) return null;
            foreach (var prefab in ZNetScene.instance.m_prefabs)
            {
                var fire = prefab != null ? prefab.GetComponent<Fireplace>() : null;
                if (fire?.m_fireworkItemList == null) continue;
                foreach (var fw in fire.m_fireworkItemList)
                    if (fw.m_fireworkItem != null && fw.m_fireworkItem.m_itemData.m_shared.m_name == fwName && fw.m_fireworksEffects != null)
                    {
                        Plugin.Log.LogDebug($"Angler's Flare: the fireworks' effects from '{prefab!.name}'.");
                        return _fireworkFx = fw.m_fireworksEffects;
                    }
            }
            return null;
        }

        /// <summary>A boss fish was just hooked: fire a flare if the angler carries one.</summary>
        public static void OnBossHooked(Player player, string bossName)
        {
            var inv = player.GetInventory();
            var flare = inv?.GetItem("$vdw_angler_flare");
            if (inv == null || flare == null) return;
            inv.RemoveItem(flare, 1);
            Vector3 at = player.transform.position;
            try
            {
                // Vanilla fireworks go up from a campfire they're thrown into: the fire plays the firework's own effects
                // (Fireplace.m_fireworkItemList). The flare plays those same effects where the angler stands.
                var fx = FireworkEffects();
                if (fx != null) fx.Create(at, Quaternion.Euler(UnityEngine.Random.Range(-4f, 4f), 0f, UnityEngine.Random.Range(-4f, 4f)));
                else if (_rocket != null)
                {
                    var go = UnityEngine.Object.Instantiate(_rocket, at + Vector3.up * 1.8f, Quaternion.LookRotation(Vector3.up));
                    go.GetComponent<Projectile>()?.Setup(player, Vector3.up * 30f + UnityEngine.Random.insideUnitSphere * 2f, -1f, null, null, null);
                }
                else Plugin.Log.LogWarning("Angler's Flare: no firework effect found on any campfire; it only pings and shouts.");
            }
            catch (Exception ex) { Plugin.Log.LogWarning($"Angler's Flare: the firework failed ({ex.Message})."); }
            if (Chat.instance != null)
            {
                Chat.instance.SendPing(at);
                Chat.instance.SendText(Talker.Type.Shout, $"I've hooked {(bossName.StartsWith("The ", StringComparison.OrdinalIgnoreCase) ? bossName : "the " + bossName)}!");
            }
            player.Message(MessageHud.MessageType.TopLeft, "Your Angler's Flare goes up.", 0, flare.GetIcon());
        }
    }
}
