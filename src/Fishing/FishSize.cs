using HarmonyLib;
using System.Globalization;
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

        [HarmonyPatch(typeof(ItemDrop.ItemData), nameof(ItemDrop.ItemData.GetTooltip),
            new[] { typeof(ItemDrop.ItemData), typeof(int), typeof(bool), typeof(float), typeof(int), typeof(bool) })]
        private static class TooltipPatch
        {
            private static void Postfix(ItemDrop.ItemData item, ref string __result)
            {
                if (item?.m_customData == null || !item.m_customData.TryGetValue("vdw_weight_kg", out var raw)) return;
                if (!float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var kg)) return;

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
