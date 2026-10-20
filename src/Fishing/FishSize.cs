using HarmonyLib;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Landed fish come in four size classes by where their weight falls in the species' range, stored as the
    /// item's quality. The tooltip shows the class, the weight and who caught it.
    /// </summary>
    internal static class FishSize
    {
        public const int MaxClass = 4;
        private static readonly string[] Names = { "", "Small", "Medium", "Large", "Trophy" };

        /// <param name="rank">0 = lightest possible, 1 = heaviest possible for the species.</param>
        public static int ClassFor(float rank) =>
            rank >= FishingController.TrophyThreshold ? 4 : rank >= 0.55f ? 3 : rank >= 0.25f ? 2 : 1;

        public static string NameOf(int quality) => Names[Mathf.Clamp(quality, 1, MaxClass)];

        // The model is shown bigger the heavier the fish: the species' lightest at MinModel, its heaviest at MaxModel.
        // Legendary and boss fish keep their fixed size (BossFish.ScaleFor).
        private const float MinModel = 0.8f, MaxModel = 1.3f;
        public static float ModelScale(FishDefinition? fish, float kg)
        {
            if (fish == null || fish.Legendary) return 1f;
            float range = fish.MaxWeightKg - fish.MinWeightKg;
            float rank = range > 0.001f ? Mathf.Clamp01((kg - fish.MinWeightKg) / range) : 0.5f;
            return Mathf.Lerp(MinModel, MaxModel, rank);
        }

        /// <summary>A dropped fish item shows at its own weight's size (from the weight stored on it when landed).</summary>
        [HarmonyPatch(typeof(ItemDrop), "Start")]
        private static class DroppedFishScale
        {
            private static void Postfix(ItemDrop __instance)
            {
                var item = __instance.m_itemData;
                if (item?.m_customData == null || !item.m_customData.TryGetValue("vdw_weight_kg", out var raw)) return;
                if (!float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out float kg)) return;
                string name = __instance.gameObject.name.Replace("(Clone)", "").Trim();
                if (!name.StartsWith("VDW_Fish_")) return;
                ContentRegistry.Fish.TryGetValue(name.Substring("VDW_Fish_".Length), out var fish);
                float s = ModelScale(fish, kg);
                if (Mathf.Abs(s - 1f) > 0.01f) __instance.transform.localScale = Vector3.one * s;
            }
        }

        /// <summary>
        /// A wall plaque for showing off a catch: a copy of Valheim's wall item stand that only takes fish (and
        /// shows bigger size classes bigger, as item stands scale by quality).
        /// </summary>
        public static void RegisterTrophyMount()
        {
            if (Jotunn.Managers.PrefabManager.Instance.GetPrefab("itemstand") == null)
            {
                Plugin.Log.LogWarning("Trophy mount: vanilla 'itemstand' not found; no trophy mount.");
                return;
            }

            var piece = new Jotunn.Entities.CustomPiece("VDW_TrophyMount", "itemstand", new Jotunn.Configs.PieceConfig
            {
                Name = Loc.Token("vdw_piece_trophy_mount", "Trophy Mount"),
                Description = Loc.Token("vdw_piece_trophy_mount_desc", "A plaque for your finest catch. Takes any fish."),
                PieceTable = "Hammer",
                Category = "Furniture",
                CraftingStation = "piece_workbench",
                Requirements = new[]
                {
                    new Jotunn.Configs.RequirementConfig("FineWood", 4, 0, true),
                    new Jotunn.Configs.RequirementConfig("Resin", 2, 0, true)
                }
            });

            var stand = piece.PiecePrefab.GetComponent<ItemStand>();
            if (stand != null)
            {
                stand.m_name = Loc.Token("vdw_piece_trophy_mount", "Trophy Mount");
                stand.m_supportedTypes.Clear();
                stand.m_supportedItems.Clear();
                foreach (var fish in ContentRegistry.Fish.Values)
                {
                    if (!string.IsNullOrWhiteSpace(fish.CatchBait)) continue;
                    var drop = ContentRegistry.DropFor(fish);
                    if (drop != null) stand.m_supportedItems.Add(drop);
                }
                foreach (var trophy in BossFish.Trophies.Values)
                    if (trophy.GetComponent<ItemDrop>() is ItemDrop t) stand.m_supportedItems.Add(t);
            }

            CustomModels.ApplyToPrefab(piece.PiecePrefab, "trophy_mount");
            Jotunn.Managers.PieceManager.Instance.AddPiece(piece);
        }

        /// <summary>Boss trophies on the Trophy Mount are shown smaller - they're modelled at the boss's size and overhang
        /// the plaque. Marked once, as the stand calls this again unchanged.</summary>
        private const float MountScale = 0.6f;
        private static readonly AccessTools.FieldRef<ItemStand, GameObject> VisualItem = AccessTools.FieldRefAccess<ItemStand, GameObject>("m_visualItem");
        private static readonly AccessTools.FieldRef<ItemStand, ItemDrop> VisualDrop = AccessTools.FieldRefAccess<ItemStand, ItemDrop>("m_visualItemDrop");

        private static bool IsBossTrophy(ItemDrop? drop)
        {
            if (drop == null) return false;
            string name = Utils.GetPrefabName(drop.gameObject);
            return BossFish.Trophies.Any(kv => BossFish.IsBoss(kv.Key) && kv.Value != null && kv.Value.name == name);
        }
        private sealed class MountScaled : MonoBehaviour { }

        [HarmonyPatch(typeof(ItemStand), "SetVisualItem")]
        private static class MountSize
        {
            private static void Postfix(ItemStand __instance)
            {
                var visual = VisualItem(__instance);
                if (visual == null || visual.GetComponent<MountScaled>() != null || Utils.GetPrefabName(__instance.gameObject) != "VDW_TrophyMount") return;
                if (!IsBossTrophy(VisualDrop(__instance))) return;
                visual.transform.localScale *= MountScale;
                visual.AddComponent<MountScaled>();
            }
        }

        [HarmonyPatch(typeof(ItemDrop.ItemData), nameof(ItemDrop.ItemData.GetTooltip),
            new[] { typeof(ItemDrop.ItemData), typeof(int), typeof(bool), typeof(float), typeof(int), typeof(bool) })]
        private static class TooltipPatch
        {
            private static void Postfix(ItemDrop.ItemData item, ref string __result)
            {
                if (item?.m_customData == null || !item.m_customData.TryGetValue("vdw_weight_kg", out var raw)) return;
                if (!float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var kg)) return;

                if (item.m_variant != RareFish.Normal && RareFish.IsFishItem(item))
                    __result = $"<color={(item.m_variant == RareFish.Golden ? "#FFD25A" : "#F2DCDC")}><b>{RareFish.Name(item.m_variant)}</b> - a rare variant</color>\n" + __result;
                string size = NameOf(item.m_quality);
                string color = item.m_quality >= MaxClass ? "#FFC34D" : "orange";
                __result += $"\n\nSize: <color={color}>{size}</color>  ({kg:0.0} kg)";
                if (item.m_stack > 1) __result += $"\n<size=85%>Weight of the first fish in this stack</size>";
                if (item.m_customData.TryGetValue("vdw_caught_by", out var who) && !string.IsNullOrEmpty(who))
                    __result += $"\nCaught by {who}";
            }
        }
    }
}
