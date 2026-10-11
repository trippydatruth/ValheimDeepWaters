using HarmonyLib;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal sealed class BaitStack
    {
        public string Name = "";
        public int Count;
        public ItemDrop.ItemData First = null!;
    }

    internal static partial class FishingController
    {
        private static FishingSession? _session;
        private static bool _rodEquipped;
        private static float _lastErrorTime = -100f;

        private static readonly FieldInfo? WaterLevelField = AccessTools.Field(typeof(ZoneSystem), "m_waterLevel");
        private const float FallbackWaterLevel = 30f;

        // Set by the vdw_debug console command: the next cast gets a near-instant bite.
        internal static bool DebugQuickBite;

        private static readonly float[] CoastalProbeFractions = { 0.3f, 0.6f, 1.0f };
        private const float CoastalProbeDistance = 70f;   // how far out past the landing spot to look for open ocean
        private const float DeepOceanDepth = 15f;         // ocean at least this deep counts as deep ocean
        private const float MinChargeCastFraction = 0.3f; // an uncharged tap casts this fraction of Cast Distance
        private const float CastReleaseDelay = 0.04f;     // lure leaves on the rod's forward whip, not on release
        internal const float TrophyThreshold = 0.85f;      // this far up the species' weight range = trophy
        private const float MaxChargeSeconds = 1.2f;       // hold this long for a full-power cast
        private const float MinCastDepth = 1f;             // metres of water needed under the float

        // Bite timing: the first fish heads for the bait after BiteMin..BiteMax seconds (before bait and buffs).
        private const float BiteMinSeconds = 2.5f, BiteMaxSeconds = 12f;

        // Lures and the retrieve: reeling with no fish on works the line back in (a lure only draws strikes while it
        // moves, or just after it stops).
        private const float LureCastFactor = 1.5f;   // lures cast this much further than a float rig
        private const float LureWaitFactor = 0.5f;   // and fish find them twice as fast
        // Reel speed (Alt + wheel, 0.1..1; Shift reels at full speed): the retrieve runs at a share of the rod's reel
        // speed, and the fight reels at a share of its full rate (with less line strain when slower).
        private const float ReelSpeedStep = 0.1f;
        private const float RetrieveSlowest = 0.1f, RetrieveFastest = 0.6f;   // of the rod's reel speed (default 0.6 -> 0.4)
        private const float FightSlowest = 0.3f, FightFastest = 1f;          // of the full fight reel rate (Shift = 1)
        private const float LurePause = 1.2f;        // a lure stays alive this long after you stop reeling
        private const float TwitchDistance = 0.35f;  // how far a rod twitch (left click) darts the lure in
        private const float RetrieveEndDistance = 2.5f;
        private const float HookWindowSeconds = 1.2f;      // time after the real bite to set the hook
        private const float BaseHookChance = 0.72f;

        // Fight tuning. Drag (0 loose .. 1 tight) lerps each pair: tight transmits more of the fish's pull as
        // tension but reels faster, tires the fish faster and gives up less line on a run.
        internal const float MaxTension = 100f;
        private const float ReelTensionLoad = 10f;
        // Pulling back (left click with a fish on): extra line strain, extra tiring, a little line won, stamina used.
        private const float PullTensionLoad = 7f, PullTire = 1.2f, PullGain = 0.6f, PullStamina = 4f;
        private const float LineRelaxRate = 8f;
        private const float PlayerStaminaDrain = 3f;       // per second while reeling, before the fish's strength
        private const float PlayerStaminaPerStrength = 1.2f;
        private const float FishStaminaDrain = 2f;
        private const float DragStep = 0.08f;              // per mouse-wheel notch
        private const float DragTensionLoose = 0.5f, DragTensionTight = 1.6f;
        private const float DragReelLoose = 0.6f, DragReelTight = 1.3f;
        private const float DragStaminaLoose = 0.6f, DragStaminaTight = 1.5f;
        private const float DragRunLineLoose = 1.6f, DragRunLineTight = 0.6f;

        // Vanilla Fishing skill (0 at level 0 .. 1 at level 100). Raised while reeling like vanilla (twice a
        // second with a fish on) plus a bonus per catch; it cuts reeling stamina and speeds up the retrieve like
        // vanilla, and here also steadies the hookset a little.
        private const float SkillMinStamina = 0.4f;    // stamina multiplier at level 100
        private const float SkillMaxReel = 1.5f;       // reel speed multiplier at level 100
        private const float SkillHookChance = 0.1f;    // hook chance added at level 100
        private const float SkillHookWindow = 0.3f;    // hook window added (x) at level 100

        private static float Skill(Player player) =>
            Mathf.Clamp01(player.GetSkillFactor(Skills.SkillType.Fishing));

        private const float RodWearPerKgSecond = 0.04f; // durability per second per kg of fish at tension 50 and Power 1

        private const float RealFishNoticeRadius = 4f;
        private const float RealFishBiteSpeedup = 1.5f;

        private static bool _logOpen;
        private static bool _reelingNow;
        private static float _dragLevel = 0.5f;
        private static float _reelSpeed = 0.6f;

        // Charge-cast state, live only while _session == null.
        private static bool _charging;
        private static float _chargeStart;
        private static bool _pendingCastActive;
        private static float _pendingCastTime;
        private static float _pendingCastFraction;

        /// <summary>Read by ScrollSuppression and the HUD: the rod is out and the mod is active.</summary>
        internal static bool RodEquippedNow => _rodEquipped && VdwConfig.Enabled.Value && Player.m_localPlayer != null;

        // Read by FishingHud.
        internal static FishingSession? Session => _session;
        internal static float DragLevel => _dragLevel;
        internal static float ReelSpeedLevel => _reelSpeed;

        /// <summary>Shift held: reel at full speed.</summary>
        private static bool FullSpeed => ZInput.GetButton("Run");
        private static float RetrieveShare => FullSpeed ? 1f : Mathf.Lerp(RetrieveSlowest, RetrieveFastest, _reelSpeed);
        private static float FightShare => FullSpeed ? 1f : Mathf.Lerp(FightSlowest, FightFastest, _reelSpeed);
        internal static bool LogOpen => _logOpen;
        internal static BaitStack? ActiveBait(Player player) => GetActiveBait(player);

        public static void Shutdown()
        {
            EndSession();
            AnimationOverride.Reset();
            KeyHintOverride.Reset();
        }

        internal static void ReportError(Exception ex)
        {
            if (Time.time - _lastErrorTime < 5f) return;
            _lastErrorTime = Time.time;
            Plugin.Log.LogError($"Fishing update error: {ex}");
        }

        /// <summary>Runs after the animator each frame: animates the rod, then anchors the line to its tip.</summary>
        public static void LateUpdateVisuals()
        {
            var player = Player.m_localPlayer;
            if (player == null || !VdwConfig.Enabled.Value)
            {
                RodMotion.Reset();
                AnimationOverride.Reset();
                KeyHintOverride.Reset();
                return;
            }

            bool rodActive = _rodEquipped && !player.IsDead();
            RodMotion.Apply(player, _session, rodActive, _reelingNow);
            RodMotion.ApplyOthers(player);           // everyone else fishing nearby, from what they share
            FishingFx.UpdateReel(player, rodActive && _reelingNow, _session != null ? _session.Tension / Mathf.Max(1f, _session.Rod.BreakTension) : 0f,
                rodActive && _session != null ? _session.DragSlip : 0f);
            AnimationOverride.SetActive(player, rodActive);
            KeyHintOverride.SetActive(rodActive);
            _session?.Bobber?.Refresh(player);
        }

        // ------------------------------------------------------------------
        // Per-frame update (called from Player.Update postfix)
        // ------------------------------------------------------------------

        public static void UpdateLocalPlayer(Player player)
        {
            if (!VdwConfig.Enabled.Value) return;
            if (player == null || player != Player.m_localPlayer) return;

            _rodEquipped = ContentRegistry.IsRod(player.GetCurrentWeapon());

            if (VdwConfig.LogKey.Value.IsDown() && !InputBlocked())
                _logOpen = !_logOpen;

            if (!_rodEquipped || player.IsDead() || player.IsSwimming())
            {
                if (_session != null) Finish(player, "You put the rod away.");
                CancelCharge();
                return;
            }

            bool blocked = InputBlocked();
            if (!blocked) UpdateSideButtons();

            if (!blocked && VdwConfig.CycleBaitKey.Value.IsDown())
                Tackle.CycleSlot(player, Tackle.BaitSlot);
            if (!blocked && VdwConfig.CycleHookKey.Value.IsDown())
                Tackle.CycleSlot(player, Tackle.HookSlot);

            UpdateCastCharge(player, blocked);

            if (_session == null) return;

            Tick(player, _session, blocked);
        }

        /// <summary>
        /// Called from Plugin.OnGUI. The wheel is read from IMGUI events rather than ZInput, because ScrollSuppression
        /// zeroes ZInput's scroll for every caller while the rod is out. Drag and reel speed each go on the control
        /// chosen in the config (by default the wheel for drag, Alt + wheel for reel speed).
        /// </summary>
        public static void ProcessScrollEvent()
        {
            if (!VdwConfig.Enabled.Value || !_rodEquipped) return;
            var e = Event.current;
            if (e == null || e.type != EventType.ScrollWheel) return;
            if (InputBlocked()) return;

            // IMGUI reports scrolling down as positive: scroll up = more.
            float scroll = -e.delta.y;
            if (Mathf.Abs(scroll) > 0.0001f) Step(e.alt ? StepControl.AltMouseWheel : StepControl.MouseWheel, Mathf.Sign(scroll));
            e.Use();
        }

        /// <summary>The mouse side buttons, if drag or reel speed is set to them: Mouse 5 (forward) up, Mouse 4 (back) down.</summary>
        private static void UpdateSideButtons()
        {
            if (VdwConfig.DragControl.Value != StepControl.MouseSideButtons && VdwConfig.ReelSpeedControl.Value != StepControl.MouseSideButtons) return;
            if (BepInEx.UnityInput.Current.GetKeyDown(KeyCode.Mouse4)) Step(StepControl.MouseSideButtons, 1f);
            if (BepInEx.UnityInput.Current.GetKeyDown(KeyCode.Mouse3)) Step(StepControl.MouseSideButtons, -1f);
        }

        /// <summary>One step up or down on a control: drag if it's on that control, else reel speed if that is.</summary>
        private static void Step(StepControl control, float dir)
        {
            if (VdwConfig.DragControl.Value == control)
            {
                _dragLevel = Mathf.Clamp01(_dragLevel + dir * DragStep);
                if (_session != null) _session.Drag = _dragLevel;
                Msg($"Drag: {_dragLevel * 100f:0}%");
            }
            else if (VdwConfig.ReelSpeedControl.Value == control)
            {
                _reelSpeed = Mathf.Clamp(Mathf.Round((_reelSpeed + dir * ReelSpeedStep) * 10f) / 10f, 0.1f, 1f);
                Msg($"Reel speed: {_reelSpeed * 100f:0}%");
            }
        }

        /// <summary>How a control is shown in the key prompts.</summary>
        internal static string ControlLabel(StepControl control) => control switch
        {
            StepControl.AltMouseWheel => "Alt+Wheel",
            StepControl.MouseSideButtons => "Mouse 4/5",
            _ => "Wheel",
        };

        private static void CancelCharge()
        {
            _charging = false;
            _pendingCastActive = false;
            RodMotion.SetCharge(false, 0f);
        }

        /// <summary>
        /// Hold Attack to charge (the rod pulls back), release to cast; distance scales with charge time. The
        /// cast itself fires a moment after release, on the rod's forward whip.
        /// </summary>
        private static void UpdateCastCharge(Player player, bool blocked)
        {
            if (_session == null && !blocked)
            {
                bool attackHeld = ZInput.GetButton("Attack");
                bool attackUp = ZInput.GetButtonUp("Attack");

                if (attackHeld && !_charging && !_pendingCastActive)
                {
                    _charging = true;
                    _chargeStart = Time.time;
                }

                if (_charging)
                {
                    float frac = Mathf.Clamp01((Time.time - _chargeStart) / MaxChargeSeconds);
                    RodMotion.SetCharge(true, frac);

                    if (attackUp)
                    {
                        _charging = false;
                        RodMotion.SetCharge(false, 0f);
                        RodMotion.Trigger(RodEvent.Cast);
                        FishingFx.Cast(player);
                        _pendingCastFraction = frac;
                        _pendingCastActive = true;
                        _pendingCastTime = Time.time + CastReleaseDelay;
                    }
                }
            }
            else if (_charging)
            {
                CancelCharge();
            }

            if (_pendingCastActive && Time.time >= _pendingCastTime)
            {
                _pendingCastActive = false;
                TryCast(player, _pendingCastFraction);
            }
        }

        private static bool InputBlocked()
        {
            return (Chat.instance != null && Chat.instance.HasFocus())
                   || global::Console.IsVisible()
                   || Menu.IsVisible()
                   || InventoryGui.IsVisible()
                   || TextInput.IsVisible();
        }

        // ------------------------------------------------------------------
        // Bait and hooks: whatever is in the tackle slots (see Tackle)
        // ------------------------------------------------------------------

        private static BaitStack? FromSlot(Player player, int slot)
        {
            var item = Tackle.ItemIn(player, slot);
            return item == null || Tackle.SlotFor(item) != slot ? null
                : new BaitStack { Name = item.m_shared.m_name, Count = item.m_stack, First = item };
        }

        private static BaitStack? GetActiveBait(Player player) => FromSlot(player, Tackle.BaitSlot);
        internal static BaitStack? GetActiveHook(Player player) => FromSlot(player, Tackle.HookSlot);

    }

    [HarmonyPatch(typeof(Player), "Update")]
    internal static class PlayerUpdatePatch
    {
        private static void Postfix(Player __instance)
        {
            try { FishingController.UpdateLocalPlayer(__instance); }
            catch (Exception ex) { FishingController.ReportError(ex); }
        }
    }

    /// <summary>
    /// The cloned vanilla rod would otherwise throw the vanilla FishingFloat when Attack is pressed.
    /// Deep Waters handles casting itself, so the vanilla attack is skipped for our rod only.
    /// </summary>
    [HarmonyPatch(typeof(Humanoid), nameof(Humanoid.StartAttack))]
    internal static class RodAttackSuppressPatch
    {
        private static bool Prefix(Humanoid __instance, ref bool __result)
        {
            if (!VdwConfig.Enabled.Value) return true;
            if (__instance != Player.m_localPlayer) return true;
            if (!ContentRegistry.IsRod(__instance.GetCurrentWeapon())) return true;

            __result = false;
            return false;
        }
    }
}

namespace ValheimDeepWaters
{
    /// <summary>
    /// With a Deep Waters rod out, right click reels and left click casts, twitches and pulls back - all read by the mod.
    /// Valheim mustn't also see them: right click is its block button, and on a rod that plays its own reeling pump
    /// animation. Both are taken out of the player's controls (the rest - moving, jumping, running - go through).
    /// </summary>
    [HarmonyLib.HarmonyPatch(typeof(Player), nameof(Player.SetControls))]
    internal static class NoVanillaRodControls
    {
        private static void Prefix(Player __instance, ref bool attack, ref bool attackHold, ref bool block, ref bool blockHold)
        {
            if (!VdwConfig.Enabled.Value || __instance != Player.m_localPlayer) return;
            if (!ContentRegistry.IsRod(__instance.GetCurrentWeapon())) return;
            attack = attackHold = block = blockHold = false;
        }
    }
}
