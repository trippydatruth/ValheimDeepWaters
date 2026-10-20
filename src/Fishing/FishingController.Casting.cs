using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>Casting: charge and release, finding water, and choosing what lives there.</summary>
    internal static partial class FishingController
    {
        // ------------------------------------------------------------------
        // Casting
        // ------------------------------------------------------------------

        private static void TryCast(Player player, float chargeFraction)
        {
            var rodItem = player.GetCurrentWeapon();
            var rod = ContentRegistry.GetRod(rodItem);
            if (rod == null) return;
            rod = RodUpgrades.Scaled(rod, rodItem.m_quality);   // its upgrade level's stats, for the whole cast and fight
            if (rodItem.m_shared.m_useDurability && rodItem.m_durability <= 0f)
            {
                Msg("Your rod is broken. Repair it where you crafted it.");
                return;
            }

            var hookStack = GetActiveHook(player);
            if (hookStack == null)
            {
                Msg("Put a hook or a lure in your tackle slot: press H, or right-click one in your inventory.");
                return;
            }

            // A lure carries its own hook and needs no bait; the bait slot then holds an optional trailer, used
            // only if it's a trailer this lure takes (anything else there stays put).
            var lure = Tackle.LureOn(player);
            var stack = GetActiveBait(player);
            BaitDefinition? trailer = null;
            if (lure != null)
            {
                if (stack != null && lure.AcceptsTrailer && ContentRegistry.BaitByItemName.TryGetValue(stack.Name, out var tr) && tr.Trailer)
                    trailer = tr;
            }
            else if (stack == null)
            {
                Msg("Put bait in your tackle slot: press B, or right-click some in your inventory.");
                return;
            }

            // A lure is heavier than a float rig and is meant to be cast far and worked back: it goes further.
            float fullCast = Mathf.Min(rod.CastDistance * (lure != null ? LureCastFactor : 1f), rod.LineCapacity);
            float maxDist = fullCast * Mathf.Lerp(MinChargeCastFraction, 1f, Mathf.Clamp01(chargeFraction));

            if (!TryFindWater(player, maxDist, out var dir, out var spot, out var distance, out var depth))
            {
                Msg("There is no water deep enough to fish there.");
                return;
            }

            BaitDefinition? baitDef = lure;
            if (lure == null && stack != null) ContentRegistry.BaitByItemName.TryGetValue(stack.Name, out baitDef);

            bool ocean = IsOceanAt(spot, dir);
            var biome = WorldGenerator.instance != null ? WorldGenerator.instance.GetBiome(spot) : Heightmap.Biome.None;
            // A boss lure only ever brings its boss (if the water, place and time are right); nothing else bites it.
            var lureBoss = baitDef != null ? BossFish.ForLure(baitDef.Id) : null;
            if (DebugBoss != null && BossFish.ForFish(DebugBoss) is BossInfo forced) lureBoss = forced;
            BossInfo? boss = null;
            FishDefinition? fish;
            if (lureBoss != null)
            {
                fish = ContentRegistry.Fish.TryGetValue(lureBoss.FishId, out var bf) ? bf : null;
                boss = DebugBoss != null ? lureBoss : SummonedBoss(lureBoss, spot, ocean, depth, biome);
                DebugBoss = null;
            }
            else
            {
                fish = SelectFish(baitDef, ocean, depth, 1f, biome, null, trailer, allowNone: false);   // a stand-in until one bites
                if (fish != null && baitDef != null && !AnyTakers(baitDef, trailer, ocean, depth, biome))
                    Msg($"Nothing in these waters goes for {Loc.Text(BaitItemName(baitDef))}. Try another bait.");
            }
            if (fish == null)
            {
                Msg("Nothing seems to live in these waters.");
                return;
            }

            bool quick = DebugQuickBite;
            DebugQuickBite = false;
            float wait = quick ? 0f : RollWait(baitDef, spot, trailer);
            if (lure != null && !quick) wait *= LureWaitFactor;   // fish come at a lure fast - it's on the move

            // Fish/weight/stamina here are placeholders until a fish actually bites (SetBiterFish).
            var s = new FishingSession
            {
                Fish = fish,
                Bait = baitDef,
                Rod = rod,
                RodItem = rodItem,
                Hook = lure != null ? LureHook(lure)
                     : ContentRegistry.HookByItemName.TryGetValue(hookStack.Name, out var hookDef) ? hookDef : null,
                Lure = lure,
                Trailer = trailer,
                LastMoved = Time.time,             // a lure draws strikes as it falls, then only while it's worked
                Phase = FishingPhase.Waiting,
                LineDistance = distance,
                StartDistance = distance,
                CastDir = dir,
                WaterY = spot.y,
                Depth = depth,
                Ocean = ocean,
                Spot = spot,
                FloatPos = spot,
                Biome = biome
            };
            SetBiterFish(s, fish, RollWeight(fish), standIn: true);

            s.Drag = _dragLevel;
            s.Bobber = BobberVisual.Create(spot, hidden: lure != null);   // no float on a lure
            // Thrown from the rod tip along a throw's arc, longer in the air the further it goes.
            Vector3 throwFrom = RodMotion.TryGetTip(out var tipNow) ? tipNow : player.transform.position + player.transform.forward * 0.6f + Vector3.up * 1.5f;
            s.Bobber.BeginCastTravel(throwFrom, spot);

            // The bait on the hook, until a fish is hooked.
            if (baitDef != null && ContentRegistry.BaitItems.TryGetValue(baitDef.Id, out var baitPrefab))
            {
                s.BaitVisual = HookedFishVisual.Create(baitPrefab, "bait_" + baitDef.Id);
                if (s.BaitVisual != null)
                {
                    s.BaitVisual.StayUnder = lure != null ? 0.3f : 0.05f;   // a lure swims under the surface, below where the line goes in
                    s.BaitVisual.SetOnHook();
                }
            }

            if (lureBoss != null)
            {
                // The omen begins once the float has landed; a lure in the wrong place just sits there.
                s.Boss = boss;
                s.OmenStart = Time.time + 1.2f;
                _session = s;
                return;
            }

            // Fish start swimming once the float has landed (0.55s cast travel).
            FishApproach.Spawn(s, spot, wait + 0.55f, quick);

            _session = s;
            Msg(lure != null ? "Cast... hold right click to work the lure back." : "Cast...");
        }

        /// <summary>The hook built into a lure, as the fight sees it: its weight range, or one that never gives.</summary>
        private static HookDefinition LureHook(BaitDefinition lure) => new HookDefinition
        {
            Id = lure.Id,
            Name = lure.Name,
            MinKg = lure.LureMinKg,
            MaxKg = lure.LureMaxKg > 0f ? lure.LureMaxKg : 100000f,
            NeverStraightens = lure.LureMaxKg <= 0f,
        };

        /// <summary>Boss lures are spent when the fish takes them; other lures, like hooks, only when the line is lost.</summary>
        internal static bool LureUsedOnBite(BaitDefinition lure) => BossFish.ForLure(lure.Id) != null;

        internal static float RollWait(BaitDefinition? bait, Vector3 spot, BaitDefinition? trailer = null)
        {
            float attraction = bait != null && bait.IsLure ? Lures.Attraction(bait, trailer) : Mathf.Max(0.5f, bait?.Attraction ?? 1f);
            float biteSpeed = 1f + FishingBuffs.Total(Player.m_localPlayer, BuffStat.BiteSpeed, spot);
            return UnityEngine.Random.Range(BiteMinSeconds, BiteMaxSeconds) / attraction / biteSpeed;
        }

        /// <summary>Where the float is right now, if the local player is fishing. Used to aim chum.</summary>
        internal static Vector3? CurrentBobberPosition()
        {
            var s = _session;
            var player = Player.m_localPlayer;
            if (s == null || player == null) return null;
            return LineEnd(player, s);
        }

        /// <summary>Rolls the species of one fish swimming around the cast.</summary>
        internal static FishDefinition? RollSuitorFish(FishingSession s) =>
            SelectFish(s.Bait, s.Ocean, s.Depth, 1f + FishingBuffs.Total(Player.m_localPlayer, BuffStat.Legendary, s.Spot), s.Biome, s.Nearby.Keys, s.Trailer, s.Style);

        /// <summary>
        /// Chance a fish that comes to the bait actually wants it - vanilla's per-bait chance (TestBate). A fish
        /// that fails this nibbles once and swims away instead of biting.
        /// </summary>
        internal static float BaitInterest(FishDefinition fish, BaitDefinition? bait, BaitDefinition? trailer = null) =>
            bait == null ? 0.5f : Mathf.Clamp(BaseInterest(fish, bait, trailer) + (BaseInterest(fish, bait, trailer) > 0f ? Mastery.InterestBonus(fish) : 0f), 0f, 0.95f);

        private static float BaseInterest(FishDefinition fish, BaitDefinition? bait, BaitDefinition? trailer)
        {
            if (bait == null) return 0.5f;
            if (fish.ForbiddenBaits != null && fish.ForbiddenBaits.Contains(bait.Id)) return 0f;
            if (bait.IsLure)
                return Mathf.Clamp(0.55f * Lures.Attraction(bait, trailer) + Lures.InterestBonus(fish, bait, trailer), 0.05f, 0.95f);
            float chance = 0.55f * Mathf.Max(0.5f, bait.Attraction);
            if (fish.PreferredBaits != null && fish.PreferredBaits.Contains(bait.Id)) chance += 0.25f;
            if (bait.TargetFish != null && bait.TargetFish.Contains(fish.Id)) chance += 0.25f;
            if (!Lures.Takes(fish, bait, null)) chance *= 0.4f;   // a stray: it looks, and mostly swims off
            return Mathf.Clamp(chance, 0.1f, 0.95f);
        }

        /// <param name="standIn">The placeholder set at the cast, before anything bites: no variant rolled (nor the debug one used up).</param>
        private static void SetBiterFish(FishingSession s, FishDefinition fish, float weightKg, bool standIn = false)
        {
            s.Fish = fish;
            s.FishStaminaMax = fish.Stamina * Mastery.FightFactor(fish);
            s.FishStamina = s.FishStaminaMax;
            s.FishWeight = weightKg;
            if (standIn) { s.Variant = RareFish.Normal; return; }
            s.Variant = DebugVariant != 0 && RareFish.Eligible(fish) ? DebugVariant : RareFish.Roll(fish);
            if (DebugVariant != 0 && RareFish.Eligible(fish)) DebugVariant = 0;
        }

        /// <summary>A fish that doesn't go for the bait is this much less likely to be the one that comes...</summary>
        internal const float OffTargetWeight = 0.03f;
        /// <summary>...and where nothing goes for it, the chance a fish comes to look at all (per fish rolled round the bait).</summary>
        private const float StrayChance = 0.02f;

        /// <summary>Whether any fish living here goes for this bait (else the cast gets a hint to try another).</summary>
        private static bool AnyTakers(BaitDefinition bait, BaitDefinition? trailer, bool ocean, float depth, Heightmap.Biome biome)
        {
            bool deep = ocean && depth >= DeepOceanDepth;
            return ContentRegistry.Fish.Values.Any(f => !BossFish.IsBoss(f.Id) && Matches(f, ocean, deep, depth) && InBiome(f, ocean, biome) && Lures.Takes(f, bait, trailer));
        }

        private static string BaitItemName(BaitDefinition bait) =>
            ContentRegistry.BaitItems.TryGetValue(bait.Id, out var p) && p.GetComponent<ItemDrop>() is ItemDrop d ? d.m_itemData.m_shared.m_name : bait.Name;

        /// <summary>Most fish come in near the bottom of their species' range; big ones are rarer.</summary>
        /// <param name="heavier">FishWeight buff: shifts the roll toward the top of the range.</param>
        internal static float RollWeight(FishDefinition fish, float heavier = 0f) =>
            Mathf.Lerp(fish.MinWeightKg, fish.MaxWeightKg, Mathf.Pow(UnityEngine.Random.value, 2f / (1f + Mathf.Max(0f, heavier + Mastery.HeavierBonus(fish)))));


        // ------------------------------------------------------------------
        // Fish selection
        // ------------------------------------------------------------------

        private static bool Matches(FishDefinition f, bool ocean, bool deepOcean, float depth)
        {
            if (depth < f.MinDepth || depth > f.MaxDepth) return false;
            switch (f.Water)
            {
                case WaterType.Any: return true;
                case WaterType.Ocean: return ocean;
                case WaterType.DeepOcean: return deepOcean;
                default: return !ocean; // River / Lake
            }
        }

        /// <summary>Fish with a Biomes list only live in those biomes (out at sea, the biome is usually Ocean).</summary>
        private static bool InBiome(FishDefinition f, bool ocean, Heightmap.Biome biome)
        {
            if (f.Biomes == null || f.Biomes.Count == 0 || biome == Heightmap.Biome.None) return true;
            foreach (var name in f.Biomes)
                if (Enum.TryParse<Heightmap.Biome>(name, true, out var b) && (b & biome) != 0) return true;
            return false;
        }

        private const float NearbySpeciesBoost = 4f; // species swimming near the float are this much likelier to bite
        private const float NearbyScanRadius = 15f;

        /// <summary>Which of our fish species are actually swimming near the cast, and where (one each).</summary>
        internal static Dictionary<string, Vector3> ScanNearbyFish(Vector3 spot)
        {
            var found = new Dictionary<string, Vector3>();
            foreach (var updater in global::Fish.Instances)
            {
                if (!(updater is global::Fish fish) || fish == null) continue;
                if (Vector3.Distance(fish.transform.position, spot) > NearbyScanRadius) continue;
                string name = fish.gameObject.name.Replace("(Clone)", "").Trim();
                if (ContentRegistry.FishIdByPrefab.TryGetValue(name, out var id) && !found.ContainsKey(id))
                    found[id] = fish.transform.position;
            }
            return found;
        }

        private static FishDefinition? SelectFish(BaitDefinition? bait, bool ocean, float depth, float legendaryBoost = 1f,
            Heightmap.Biome biome = Heightmap.Biome.None, IEnumerable<string>? nearby = null, BaitDefinition? trailer = null,
            RetrieveStyle style = RetrieveStyle.None, bool allowNone = true)
        {
            bool deep = ocean && depth >= DeepOceanDepth;
            // Boss fish are never caught by chance: only their lure brings them.
            var pool = ContentRegistry.Fish.Values.Where(f => !BossFish.IsBoss(f.Id) && Matches(f, ocean, deep, depth) && InBiome(f, ocean, biome)).ToList();
            if (pool.Count == 0) pool = ContentRegistry.Fish.Values.Where(f => !BossFish.IsBoss(f.Id) && Matches(f, ocean, deep, depth)).ToList();
            var near = nearby != null ? new HashSet<string>(nearby) : null;
            if (pool.Count == 0) return null;

            var weights = new float[pool.Count];
            float total = 0f, takers = 0f;
            for (int i = 0; i < pool.Count; i++)
            {
                var f = pool[i];
                float w = Mathf.Max(0f, f.BiteWeight) * Mastery.BiteFactor(f);   // species you've mastered come more readily
                if (near != null && near.Contains(f.Id)) w *= NearbySpeciesBoost;
                if (f.Legendary) w *= legendaryBoost;

                if (EnvMan.instance != null)
                {
                    bool night = EnvMan.IsNight();
                    if (string.Equals(f.ActiveTime, "Night", StringComparison.OrdinalIgnoreCase)) w *= night ? 2.5f : 0.4f;
                    else if (string.Equals(f.ActiveTime, "Day", StringComparison.OrdinalIgnoreCase)) w *= night ? 0.4f : 2.0f;
                }

                if (f.LovesRain && EnvMan.instance != null)
                    w *= EnvMan.IsWet() ? 2.5f : 0.6f;

                if (bait != null)
                {
                    if (f.ForbiddenBaits != null && f.ForbiddenBaits.Contains(bait.Id)) w = 0f;
                    else if (bait.IsLure) w *= Lures.WeightFactor(f, bait, trailer) * Retrieves.Factor(f, bait, style);   // its kind, list, trailer and how it's worked
                    else
                    {
                        bool target = bait.TargetFish != null && bait.TargetFish.Contains(f.Id);
                        bool preferred = f.PreferredBaits != null && f.PreferredBaits.Contains(bait.Id);
                        if (target) w *= 3f;
                        if (preferred) w *= 2f;
                        if (!target && !preferred) w *= OffTargetWeight;   // not its bait: only a rare stray bite
                    }
                }

                weights[i] = w;
                total += w;
                if (Lures.Takes(f, bait, trailer)) takers += w;
            }

            if (total <= 0f) return allowNone ? null : pool[UnityEngine.Random.Range(0, pool.Count)];
            // nothing here goes for this bait: now and then a stray fish takes it anyway, mostly nothing comes
            if (bait != null && takers <= 0f && allowNone && UnityEngine.Random.value > StrayChance) return null;

            float roll = UnityEngine.Random.value * total;
            for (int i = 0; i < pool.Count; i++)
            {
                roll -= weights[i];
                if (roll <= 0f) return pool[i];
            }
            return pool[pool.Count - 1];
        }

    }
}
