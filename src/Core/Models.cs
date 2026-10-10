using System;
using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    public enum WaterType { Any, River, Lake, Ocean, DeepOcean }

    public sealed class FishDefinition
    {
        public string Id = "";
        public string Name = "";
        public string Description = "";
        public WaterType Water = WaterType.Any;
        public float MinDepth = 0f;
        public float MaxDepth = 999f;
        public float MinWeightKg = 0.1f;
        public float MaxWeightKg = 3f;
        public float FightStrength = 1f;
        public float Stamina = 20f;
        public float BiteWeight = 1f;
        public bool Legendary = false;
        /// <summary>Any | Day | Night. Fish are more likely to bite in their active period.</summary>
        public string ActiveTime = "Any";
        /// <summary>True if the fish bites more in rain/wet weather.</summary>
        public bool LovesRain = false;
        /// <summary>Coins Haldor pays per fish. 0 = calculated from size and strength.</summary>
        public int SellValue = 0;
        /// <summary>Cooked meal health / stamina. 0 = calculated from fight strength.</summary>
        public float FoodHealth = 0f;
        public float FoodStamina = 0f;
        public string VanillaFallbackPrefab = "Fish1";
        /// <summary>
        /// A vanilla fish (e.g. "Fish1" for Perch): landing it gives that vanilla item, it lives where vanilla spawns it
        /// and its vanilla baits work on it. The stats here still drive the fight, weight and bite.
        /// </summary>
        public string VanillaPrefab = "";
        [Newtonsoft.Json.JsonIgnore] public bool IsVanilla => !string.IsNullOrWhiteSpace(VanillaPrefab);
        /// <summary>A baitfish: landing it gives this bait (by bait id) instead of a fish to eat.</summary>
        public string CatchBait = "";
        /// <summary>Freshwater biomes it lives in (Meadows, BlackForest, Swamp, Mountain, Plains, Mistlands, AshLands, DeepNorth). Empty = any.</summary>
        public List<string> Biomes = new List<string>();
        public int CatchAmount = 1;
        public List<string> PreferredBaits = new List<string>();
        public List<string> ForbiddenBaits = new List<string>();
    }

    public sealed class BaitDefinition
    {
        public string Id = "";
        public string Name = "";
        public string Description = "";
        public float Attraction = 1f;
        public float HookBonus = 0f;
        public List<string> TargetFish = new List<string>();
        public string VanillaFallbackPrefab = "FishingBait";
        /// <summary>Only baits with no natural source have a recipe; empty = can't be crafted.</summary>
        public string CraftingStation = "piece_workbench";
        public int StationLevel = 1;
        public int CraftAmount = 5;
        public List<RequirementDefinition> Recipe = new List<RequirementDefinition>();

        /// <summary>
        /// A lure carries its own hook: it goes in the hook slot and needs no bait. It suits fish between LureMinKg
        /// and LureMaxKg (a max of 0: it never straightens or turns a fish away, like the boss lures). Ids starting
        /// "lure_" are lures even in data files written before this existed.
        /// </summary>
        public bool Lure = false;
        public float LureMinKg = 0f;
        public float LureMaxKg = 0f;
        /// <summary>
        /// What kind of lure: Spoon, Spinner, Crankbait, Jig, SoftPlastic, TexasRig, Swimbait, Topwater or Fly. Each
        /// draws its own fish (Lures.KindTargets), plus any in TargetFish. Boss lures need none.
        /// </summary>
        public string LureKind = "";
        /// <summary>Whether a trailer can go on this lure (in the bait slot, which becomes the trailer slot).</summary>
        public bool AcceptsTrailer = false;
        /// <summary>
        /// A trailer: goes on a lure that takes one, in the bait slot. Its TargetFish come to the lure too, and the
        /// fish the lure already draws come this much more readily (TrailerBoost; 0 = the usual 1.6).
        /// </summary>
        public bool Trailer = false;
        public float TrailerBoost = 0f;

        [Newtonsoft.Json.JsonIgnore] public bool IsLure => Lure || Id.StartsWith("lure_", StringComparison.OrdinalIgnoreCase);
    }

    /// <summary>One hook size, from Hooks.json. Suits fish between MinKg and MaxKg.</summary>
    public sealed class HookDefinition
    {
        public string Id = "";
        public string Name = "";
        public string Description = "";
        public string Label = "";         // the size as anglers write it, e.g. "#6" or "2/0"
        public float MinKg = 0f;          // lighter fish struggle to take a hook this big
        public float MaxKg = 5f;          // heavier fish can straighten it; much heavier ones won't bite
        public string VanillaFallbackPrefab = "BronzeNails";
        public string CraftingStation = "forge";
        public int StationLevel = 1;
        public int CraftAmount = 5;
        public List<RequirementDefinition> Recipe = new List<RequirementDefinition>();

        public bool Craftable = true;
        public bool NeverStraightens = false;
        public float KeepChance = 0f;     // chance the hook survives a snapped line or broken rod
        public FindDefinition? Find;      // for non-craftable hooks: where they turn up
    }

    public sealed class RequirementDefinition
    {
        public string Item = "";
        public int Amount = 1;
    }

    /// <summary>One rod tier, from Rods.json.</summary>
    public sealed class RodDefinition
    {
        public string Id = "";
        public string Name = "";
        public string Description = "";

        public float CastDistance = 20f;  // m at full charge
        public float LineCapacity = 40f;  // m of line on the reel; the fish wins if it takes it all
        public float BreakTension = 85f;  // line snaps at this tension (out of 100)
        public float ReelSpeed = 4.5f;    // m/s base retrieve
        public float Power = 1f;          // divides how hard fish pull on the line
        public float HookBonus = 0f;      // added to the hookset chance
        public float StaminaUse = 1f;     // multiplies your stamina cost while reeling
        public float Durability = 100f;   // max durability; wears during fights, repaired at the crafting station
        public float[]? ModelRotation;    // optional [x, y, z] degrees to turn a custom model that's exported facing the wrong way
        public string CraftingStation = "piece_workbench";
        public int StationLevel = 1;
        public List<RequirementDefinition> Recipe = new List<RequirementDefinition>();

        public bool Craftable = true;
        public int TraderPrice = 0;              // > 0: Haldor sells it for this many coins
        public string TraderRequiredKey = "";    // optional global key (e.g. "defeated_bonemass") before he offers it
    }

    internal enum FishingPhase { Waiting, Bite, Fighting }

    internal sealed class FishingSession
    {
        public FishDefinition Fish = null!;
        public BaitDefinition? Bait;
        public RodDefinition Rod = null!;
        public ItemDrop.ItemData? RodItem; // the actual rod in the player's hand, for durability
        public HookDefinition? Hook;
        public BaitDefinition? Lure;      // the lure in the hook slot (it is also Bait: what the fish come to), or null
        public BaitDefinition? Trailer;   // the trailer on that lure, if any
        public float LastMoved = -100f;    // when the line was last reeled while waiting (a lure only draws strikes while it moves)
        public float DragSlip;            // 0..1: how hard the drag is slipping (line pulled out against it, or a loose drag spinning)
        public Vector3 FloatPos;          // where the float (or lure) is in the world while waiting: it stays put when you move
        public float Slack;               // how slack the line is, 0 (taut) .. 0.3 (hanging loose), as vanilla draws it
        public bool WornWarned;
        public FishingPhase Phase = FishingPhase.Waiting;

        public float HookDeadline;

        public float FishStamina;
        public float FishStaminaMax;
        public float FishWeight;

        public float Tension;
        public float LineDistance;
        public float StartDistance;
        public float SlackTime;

        public bool Running;
        public float StateTimer;
        public float SkillTimer; // reeling time toward the next Fishing skill raise
        public float NextSplash; // next splash while the fish is running

        /// <summary>0 = loose (safe, slow), 1 = tight (fast, risky). Set from mouse wheel; persists between casts.</summary>
        public float Drag;

        public Vector3 CastDir;
        /// <summary>Degrees the fish has pulled the line off the cast direction (sideways runs).</summary>
        public float Angle;
        public float AngleSpeed;
        public float LeapEnd;   // when the current leap lands (0 = not leaping)
        public Vector3 LineDir => Quaternion.AngleAxis(Angle, Vector3.up) * CastDir;
        public float WaterY;
        public float Depth;
        public bool Ocean;
        public Vector3 Spot; // where the cast landed
        public Heightmap.Biome Biome;
        public Dictionary<string, Vector3> Nearby = new Dictionary<string, Vector3>(); // our species swimming near the cast

        public BobberVisual? Bobber;
        public HookedFishVisual? HookedFish;
        public HookedFishVisual? BaitVisual; // the bait itself, visible on the hook until something takes it

        // Fish swimming around the cast before the bite (see FishApproach). Biter is the one currently
        // holding the bait during the Bite phase.
        public List<Suitor> Suitors = new List<Suitor>();
        public Suitor? Biter;
        public float NextRespawn;

        // Boss fish (see BossFish): summoned by its lure, announced by an omen, then fought with a boss bar.
        public BossInfo? Boss;
        public float OmenStart;      // when the omen begins (the float has landed)
        public int OmenStep;         // 0 waiting, 1 the omen is under way, 2 it has struck
        public float ShudderUntil;   // the float dips while the boss circles
        public GameObject? Swirl;
        // Legendary fights (bosses and mini-bosses): 0 fresh, 1 enraged, 2 desperate. Never goes back down.
        public int FightPhase;
        public float NextDive;

        public float MaxLine => Mathf.Max(StartDistance, Rod.LineCapacity);
    }
}
