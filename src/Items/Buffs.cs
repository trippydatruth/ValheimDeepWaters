using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>Where a non-craftable item can turn up: inside a landed fish.</summary>
    public sealed class FindDefinition
    {
        public float Chance = 0f;          // per catch
        public float LegendaryChance = 0f; // per legendary catch (replaces Chance)
        public float MinFishKg = 0f;       // only fish at least this heavy
        public bool OceanOnly = false;
    }

    /// <summary>
    /// One fishing buff item from Buffs.json. Kind decides what it is: a Mead (drink for a timed buff),
    /// Wearable (buff while equipped; Slot = Helmet, Shoulder or Utility), Chum (drink-style item that baits
    /// the water where you're fishing for a while), Totem (a piece you build that buffs anyone fishing nearby) or
    /// Float (used like a mead: your line wears its float, FloatModel, for Duration - no slot to fill).
    /// </summary>
    public sealed class BuffDefinition
    {
        public string Id = "";
        public string Name = "";
        public string Description = "";
        public string Kind = "Mead";
        public int Tier = 1;
        public float Duration = 600f;     // seconds, for Mead and Chum
        public float Radius = 20f;        // metres, for Chum and Totem
        public float Armor = 0f;          // for Wearable
        public Dictionary<string, float> Effects = new Dictionary<string, float>();
        /// <summary>A float: the bobber model your casts use while this is active (only one float at a time).</summary>
        public string FloatModel = "";
        /// <summary>A float with a light in it, lit after dark.</summary>
        public bool FloatLight = false;

        public string VanillaFallbackPrefab = "";
        public bool Craftable = true;
        public string CraftingStation = "piece_cauldron";
        public int StationLevel = 1;
        public int CraftAmount = 1;
        public List<RequirementDefinition> Recipe = new List<RequirementDefinition>();
        public FindDefinition? Find;
    }

    /// <summary>The fishing stats buffs can change. Values add up across active buffs.</summary>
    internal static class BuffStat
    {
        public const string BiteSpeed = "BiteSpeed";           // +x: fish head for the bait sooner (wait / (1 + x))
        public const string Nibbles = "Nibbles";               // fewer fake nibbles before the bite
        public const string BaitInterest = "BaitInterest";     // + chance a fish wants the bait
        public const string ExtraFish = "ExtraFish";           // more fish around each cast
        public const string HookWindow = "HookWindow";         // +x: longer hook window
        public const string HookChance = "HookChance";         // + hook chance
        public const string Tension = "Tension";               // -x: fish pull the line less
        public const string ReelSpeed = "ReelSpeed";           // +x: faster retrieve
        public const string ReelStamina = "ReelStamina";       // -x: less stamina while reeling
        public const string RodWear = "RodWear";               // -x: less rod wear
        public const string HookStraighten = "HookStraighten"; // -x: hooks straighten less (1 = never)
        public const string FishWeight = "FishWeight";         // +x: catches run heavier
        public const string Legendary = "Legendary";           // +x: legendary fish more likely
        public const string Stealth = "Stealth";               // > 0: fish don't flee from your noise
        public const string NightBite = "NightBite";           // +x: fish bite sooner, at night only (the lantern float)

        public static readonly string[] All =
            { BiteSpeed, Nibbles, BaitInterest, ExtraFish, HookWindow, HookChance, Tension, ReelSpeed, ReelStamina, RodWear, HookStraighten, FishWeight, Legendary, Stealth, NightBite };

        public static string Describe(string stat, float v)
        {
            string pct = (v * 100f).ToString("0", CultureInfo.InvariantCulture) + "%";
            return stat switch
            {
                BiteSpeed => $"Fish bite {pct} sooner",
                Nibbles => $"{v:0} fewer nibble{(Mathf.Approximately(v, 1f) ? "" : "s")} before the bite",
                BaitInterest => $"Fish {pct} more likely to take bait",
                ExtraFish => $"+{v:0} fish around your bait",
                HookWindow => $"Hook window +{pct}",
                HookChance => $"Hook chance +{pct}",
                Tension => $"Line tension -{pct}",
                ReelSpeed => $"Reel speed +{pct}",
                ReelStamina => $"Reeling stamina -{pct}",
                RodWear => $"Rod wear -{pct}",
                HookStraighten => v >= 1f ? "Hooks never straighten" : $"Hooks straighten {pct} less",
                FishWeight => $"Catches {pct} heavier",
                Legendary => $"Legendary fish +{pct} more likely",
                Stealth => "Fish don't flee from your noise",
                NightBite => $"At night, fish bite {pct} sooner",
                _ => $"{stat} {v}"
            };
        }
    }

    /// <summary>The status effect every fishing buff item gives. Effects come from its BuffDefinition.</summary>
    internal sealed class SE_FishingBuff : StatusEffect
    {
        // Set on the live copy when a chum is used: where in the water it went.
        public Vector3 ChumPoint;

        public override void Setup(Character character)
        {
            base.Setup(character);
            var def = FishingBuffs.ByStatusName(m_name);
            if (def == null || !def.Kind.Equals("Chum", StringComparison.OrdinalIgnoreCase)) return;

            // Into the water where you're fishing, or a little way in front of you.
            ChumPoint = FishingController.CurrentBobberPosition() ?? character.transform.position + character.transform.forward * 10f;
        }
    }

    /// <summary>Registers the buff items and answers "how much of stat X does this player have right now?".</summary>
    internal static class FishingBuffs
    {
        public static readonly Dictionary<string, BuffDefinition> Buffs = new();
        private static readonly Dictionary<string, BuffDefinition> ByStatus = new(); // status effect display name -> buff
        private static readonly Dictionary<string, StatusEffect> Effects = new();   // buff id -> status effect

        public static BuffDefinition? ByStatusName(string statusName) => ByStatus.TryGetValue(statusName, out var d) ? d : null;
        public static string PrefabName(BuffDefinition b) => "VDW_Buff_" + b.Id;

        private static bool Is(BuffDefinition b, string kind) => b.Kind.Equals(kind, StringComparison.OrdinalIgnoreCase);

        /// <summary>
        /// Total of one stat across the player's active fishing buffs. Chum only counts when <paramref name="at"/>
        /// (the cast) is within its radius.
        /// </summary>
        public static float Total(Player? player, string stat, Vector3? at = null)
        {
            if (player == null) return 0f;
            float total = 0f;
            foreach (var se in player.GetSEMan().GetStatusEffects())
            {
                if (!ByStatus.TryGetValue(se.m_name, out var def) || !def.Effects.TryGetValue(stat, out var v)) continue;
                if (Is(def, "Chum"))
                {
                    if (at == null || !(se is SE_FishingBuff chum) || Vector3.Distance(chum.ChumPoint, at.Value) > def.Radius) continue;
                }
                total += v;
            }
            // Chum buckets set down by anyone, near where the line is in the water.
            if (at != null) total += ChumBuckets.Total(stat, at.Value);
            // the lantern float's bite bonus only counts after dark
            if (stat == BuffStat.BiteSpeed && EnvMan.instance != null && EnvMan.IsNight()) total += Total(player, BuffStat.NightBite, at);
            return total;
        }

        /// <summary>A reduction stat (Tension, RodWear...) as a multiplier, never below 10%.</summary>
        public static float Reduction(Player? player, string stat) => Mathf.Clamp(1f - Total(player, stat), 0.1f, 1f);

        /// <summary>The float the player's line wears right now (an active buff with a FloatModel), or null for the usual bobber.</summary>
        public static BuffDefinition? ActiveFloat(Player? player)
        {
            if (player == null) return null;
            foreach (var se in player.GetSEMan().GetStatusEffects())
                if (ByStatus.TryGetValue(se.m_name, out var def) && !string.IsNullOrWhiteSpace(def.FloatModel)) return def;
            return null;
        }

        public static void Load(List<BuffDefinition> buffs)
        {
            Buffs.Clear();
            foreach (var b in buffs)
                if (!string.IsNullOrWhiteSpace(b.Id))
                    Buffs[b.Id] = b;
        }

        public static void Register()
        {
            int ok = 0;
            foreach (var b in Buffs.Values.OrderBy(b => b.Tier))
            {
                try
                {
                    foreach (var key in b.Effects.Keys.Where(k => !BuffStat.All.Contains(k)))
                        Plugin.Log.LogWarning($"Buff '{b.Id}': unknown effect '{key}' (known: {string.Join(", ", BuffStat.All)}).");

                    if (Is(b, "Totem")) RegisterTotem(b);
                    else RegisterItem(b);
                    ok++;
                }
                catch (Exception ex)
                {
                    Plugin.Log.LogError($"Failed to register buff '{b.Id}': {ex.Message}");
                }
            }
        }

        internal static string DisplayName(BuffDefinition b) => Loc.Token("vdw_buff_" + b.Id, string.IsNullOrWhiteSpace(b.Name) ? b.Id : b.Name);

        internal static string EffectText(BuffDefinition b)
        {
            var lines = b.Effects.Where(e => BuffStat.All.Contains(e.Key)).Select(e => BuffStat.Describe(e.Key, e.Value)).ToList();
            if (!string.IsNullOrWhiteSpace(b.FloatModel)) lines.Add($"Your line wears this float for {b.Duration / 60f:0.#} min{(b.FloatLight ? ", lit after dark" : "")}");
            else if (Is(b, "Mead")) lines.Add($"Lasts {b.Duration / 60f:0.#} min");
            if (Is(b, "Chum")) lines.Add($"For {b.Duration / 60f:0.#} min, within {b.Radius:0} m of where you set it down");
            if (Is(b, "Totem")) lines.Add($"Anyone fishing within {b.Radius:0} m");
            return string.Join("\n", lines);
        }

        private static StatusEffect MakeStatus(BuffDefinition b, Sprite? icon, float ttl)
        {
            var se = ScriptableObject.CreateInstance<SE_FishingBuff>();
            se.name = "VDW_SE_" + b.Id;
            se.m_name = DisplayName(b);
            se.m_tooltip = EffectText(b);
            se.m_icon = icon;
            se.m_ttl = ttl;
            // Tiers of the same family share a category, so (like vanilla meads) only one runs at a time.
            se.m_category = string.IsNullOrWhiteSpace(b.FloatModel) ? "vdw_" + b.Id.Split('_')[0] : "vdw_float";   // one float on the line at a time
            ItemManager.Instance.AddStatusEffect(new CustomStatusEffect(se, fixReference: false));
            ByStatus[se.m_name] = b;
            Effects[b.Id] = se;
            return se;
        }

        /// <summary>A lasting status effect for worn gear (an armour set's bonus): its fishing stats count like any buff's.</summary>
        internal static StatusEffect MakeGearStatus(BuffDefinition b, Sprite? icon)
        {
            var se = MakeStatus(b, icon, 0f);
            se.m_category = "vdw_gear_" + b.Id;
            return se;
        }

        /// <summary>A safe vanilla item of the same kind (and, for wearables, the same slot) to clone instead.</summary>
        private static string DefaultBase(BuffDefinition b)
        {
            if (Is(b, "Mead") || Is(b, "Chum") || Is(b, "Float")) return "MeadHealthMinor";
            string wanted = b.VanillaFallbackPrefab ?? "";
            if (wanted.StartsWith("Cape", StringComparison.OrdinalIgnoreCase)) return "CapeDeerHide";
            if (wanted.StartsWith("Belt", StringComparison.OrdinalIgnoreCase)) return "BeltStrength";
            return "HelmetLeather";
        }

        private static void RegisterItem(BuffDefinition b)
        {
            string basePrefab = ResolvePrefab(b.VanillaFallbackPrefab, DefaultBase(b));
            var item = b.Craftable && b.Recipe.Count > 0
                ? new CustomItem(PrefabName(b), basePrefab, new ItemConfig
                {
                    Amount = Math.Max(1, b.CraftAmount),
                    CraftingStation = b.CraftingStation,
                    MinStationLevel = Math.Max(1, b.StationLevel),
                    Requirements = b.Recipe.Select(r => new RequirementConfig(r.Item, r.Amount)).ToArray()
                })
                : new CustomItem(PrefabName(b), basePrefab);

            var shared = item.ItemDrop.m_itemData.m_shared;
            shared.m_name = DisplayName(b);
            string source = b.Craftable ? ""
                : Relics.SourceText(PrefabName(b)) ?? "\n\nCan't be crafted. Sometimes found inside a fish.";
            shared.m_description = Loc.Token("vdw_buff_" + b.Id + "_desc", $"{b.Description}\n\n{EffectText(b)}{source}");

            var icon = shared.m_icons != null && shared.m_icons.Length > 0 ? shared.m_icons[0] : null;
            if (Is(b, "Wearable"))
            {
                shared.m_equipStatusEffect = MakeStatus(b, icon, 0f);
                shared.m_armor = b.Armor;
                shared.m_armorPerLevel = 0f;
                shared.m_maxQuality = 1;
                shared.m_setName = "";
                shared.m_setStatusEffect = null;
                shared.m_movementModifier = 0f;
            }
            else
            {
                shared.m_consumeStatusEffect = MakeStatus(b, icon, b.Duration);
                shared.m_food = shared.m_foodStamina = shared.m_foodEitr = 0f;
            }

            if (CustomModels.ApplyToPrefab(item.ItemPrefab, "buff_" + b.Id))
                GroundPose.FitCollider(item.ItemPrefab);
            RelicVisuals.Apply(item.ItemPrefab, "buff_" + b.Id);
            ItemManager.Instance.AddItem(item);
            if (Is(b, "Chum")) ChumBuckets.RegisterPlaced(b, item.ItemPrefab);
        }

        private static void RegisterTotem(BuffDefinition b)
        {
            string basePrefab = ResolvePrefab(b.VanillaFallbackPrefab, "piece_banner01", "sign");
            var piece = new CustomPiece(PrefabName(b), basePrefab, new PieceConfig
            {
                Name = DisplayName(b),
                Description = Loc.Token("vdw_buff_" + b.Id + "_desc", $"{b.Description}\n\n{EffectText(b)}"),
                PieceTable = "Hammer",
                Category = "Misc",
                CraftingStation = b.CraftingStation,
                Requirements = b.Recipe.Select(r => new RequirementConfig(r.Item, r.Amount, 0, true)).ToArray()
            });
            var se = MakeStatus(b, piece.Piece.m_icon, 3f); // refreshed every second while you're in range
            piece.PiecePrefab.AddComponent<FishingTotem>();
            CustomModels.ApplyToPrefab(piece.PiecePrefab, "buff_" + b.Id);
            se.m_icon = piece.Piece.m_icon;                  // the totem's own icon (set just above), not the banner's
            CopyPlacementFlags("guard_stone", piece.Piece);
            PieceManager.Instance.AddPiece(piece);
        }

        /// <summary>
        /// A totem places like vanilla's ward (guard_stone) rather than the banner it's cloned from: every placement
        /// rule on the Piece (ground only, may sit into the ground, not in water and so on) is copied over.
        /// </summary>
        private static void CopyPlacementFlags(string vanillaPrefab, Piece target)
        {
            var source = PrefabManager.Instance.GetPrefab(vanillaPrefab)?.GetComponent<Piece>();
            if (source == null)
            {
                target.m_clipGround = true;
                return;
            }
            string[] fields =
            {
                "m_groundPiece", "m_allowAltGroundPlacement", "m_groundOnly", "m_cultivatedGroundOnly", "m_waterPiece",
                "m_clipGround", "m_clipEverything", "m_noInWater", "m_notOnWood", "m_notOnTiltingSurface",
                "m_inCeilingOnly", "m_notOnFloor", "m_noClipping", "m_onlyInTeleportArea", "m_allowedInDungeons",
                "m_spaceRequirement", "m_allowRotatedOverlap", "m_vegetationGroundOnly",
            };
            foreach (var name in fields)
            {
                var f = typeof(Piece).GetField(name);
                if (f != null) f.SetValue(target, f.GetValue(source));
            }
            target.m_clipGround = true; // the statue sits into the ground whatever the ward says
        }

        private static string ResolvePrefab(params string[] candidates)
        {
            foreach (var c in candidates)
                if (!string.IsNullOrWhiteSpace(c) && PrefabManager.Instance.GetPrefab(c) != null) return c;
            return candidates.Last(c => !string.IsNullOrWhiteSpace(c));
        }

        /// <summary>Totems call this each second for a local player in range.</summary>
        public static void ApplyTotem(Player player, string buffId)
        {
            if (Effects.TryGetValue(buffId, out var se))
                player.GetSEMan().AddStatusEffect(se, resetTime: true);
        }

        // ------------------------------------------------------------------ finds

        /// <summary>
        /// Rolls for a non-craftable relic inside a landed fish (rarest first, at most one). Returns the prefab
        /// to drop, or null. Bait fish never hold one, and the boss relics only come from bosses (BossFish).
        /// </summary>
        public static GameObject? RollFind(FishingSession s)
        {
            if (!string.IsNullOrWhiteSpace(s.Fish.CatchBait)) return null;
            var candidates = new List<(string prefab, FindDefinition find)>();
            foreach (var b in Buffs.Values) if (b.Find != null) candidates.Add((PrefabName(b), b.Find));
            foreach (var h in ContentRegistry.Hooks.Values) if (h.Find != null) candidates.Add(("VDW_Hook_" + h.Id, h.Find));

            foreach (var (prefab, find) in candidates.OrderBy(c => c.find.Chance))
            {
                if (s.FishWeight < find.MinFishKg || (find.OceanOnly && !s.Ocean)) continue;
                float chance = s.Fish.Legendary && find.LegendaryChance > 0f ? find.LegendaryChance : find.Chance;
                if (UnityEngine.Random.value < chance)
                    return ZNetScene.instance != null ? ZNetScene.instance.GetPrefab(prefab) : null;
            }
            return null;
        }
    }

    /// <summary>
    /// On a built totem: buffs the local player while they're within its radius. Every player's game runs this for
    /// every totem, so a totem works for anyone fishing near it. Hovering shows what it does and whether you're in reach.
    /// </summary>
    internal sealed class FishingTotem : MonoBehaviour, Hoverable
    {
        private string _buffId = "";
        private float _radius = 20f;
        private float _next;

        private void Start()
        {
            // The piece's prefab is VDW_Buff_<id>; clones carry that name with "(Clone)" after it.
            string name = gameObject.name.Replace("(Clone)", "").Trim();
            _buffId = name.StartsWith("VDW_Buff_") ? name.Substring("VDW_Buff_".Length) : "";
            if (FishingBuffs.Buffs.TryGetValue(_buffId, out var def)) _radius = def.Radius;
        }

        private void Update()
        {
            if (Time.time < _next || _buffId.Length == 0) return;
            _next = Time.time + 1f;

            // The build-mode placement ghost has no live network view: don't buff from that.
            var player = Player.m_localPlayer;
            var nview = GetComponent<ZNetView>();
            if (player == null || (nview != null && !nview.IsValid())) return;
            if (Vector3.Distance(player.transform.position, transform.position) <= _radius)
                FishingBuffs.ApplyTotem(player, _buffId);
        }

        public string GetHoverText()
        {
            if (!FishingBuffs.Buffs.TryGetValue(_buffId, out var def)) return "";
            var player = Player.m_localPlayer;
            bool inReach = player != null && Vector3.Distance(player.transform.position, transform.position) <= _radius;
            return $"{Loc.Text(FishingBuffs.DisplayName(def))}\n{Loc.Text(FishingBuffs.EffectText(def))}\n" +
                   (inReach ? "<color=#8fd16a>You're within its reach</color>" : $"<color=#b6a584>Reaches {_radius:0} m</color>");
        }

        public string GetHoverName() => FishingBuffs.Buffs.TryGetValue(_buffId, out var def) ? Loc.Text(FishingBuffs.DisplayName(def)) : "";

        public float GetHoverOffset() => 0f;
    }
}
