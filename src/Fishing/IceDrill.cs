using HarmonyLib;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Drilling with the Ice Auger, in place of the swing of the spear it's made from: the auger is set upright on the
    /// ice in front of you and you twist its T-handle back and forth with both hands while the bit sinks into the ice,
    /// chips flying, until it breaks through and the hole opens. Walk off and you stop. Posed on top of the animation
    /// (as the rower is: FishingBoatOars), and shared through the player's ZDO so everyone sees it.
    /// </summary>
    internal static class IceDrill
    {
        public const string AugerModel = "tool_ice_auger";
        public const float GripFromPoint = 0.8f;   // held like a spear, halfway up the shaft
        public const float Seconds = 4f;
        private const float Reach = 0.62f;         // the auger stands this far in front of you
        private const float Sink = 0.35f;          // how far the bit goes into the ice
        private const float GripOut = 0.17f;       // the hands on the T-handle, this far out from the shaft
        private const string KeyStart = "vdw_drill", KeyAt = "vdw_drill_at", KeyYaw = "vdw_drill_yaw";

        private static Vector3 _from;              // where the local player stood when they began

        private sealed class Rig { public GameObject? Auger; public float NextChip; public GameObject? Hidden; public List<Renderer> Off = new(); }
        private static readonly Dictionary<int, Rig> Rigs = new();
        private static readonly AccessTools.FieldRef<VisEquipment, GameObject> RightItem = AccessTools.FieldRefAccess<VisEquipment, GameObject>("m_rightItemInstance");

        // the start kept in ticks: a float of the world's clock loses the fractions of a second on an old world
        private static long Now => ZNet.instance != null ? ZNet.instance.GetTime().Ticks : DateTime.Now.Ticks;

        private static ZDO? Zdo(Player p)
        {
            var nview = p.GetComponent<ZNetView>();
            return nview != null && nview.IsValid() ? nview.GetZDO() : null;
        }

        /// <summary>How far into a drill this player is (seconds), or -1 if they aren't drilling.</summary>
        private static float Progress(Player p, out Vector3 at, out float yaw)
        {
            at = Vector3.zero; yaw = 0f;
            var zdo = Zdo(p);
            if (zdo == null) return -1f;
            long start = zdo.GetLong(KeyStart, 0L);
            if (start <= 0L) return -1f;
            float t = (float)((Now - start) / (double)TimeSpan.TicksPerSecond);
            if (t < 0f || t > Seconds + 1f) return -1f;
            at = zdo.GetVec3(KeyAt, p.transform.position); yaw = zdo.GetFloat(KeyYaw, 0f);
            return t;
        }

        public static bool Busy(Player p) => Progress(p, out _, out _) >= 0f;

        /// <summary>The attack button with the auger in hand: start drilling, if there's ice to drill in front of you.</summary>
        public static void Begin(Player player)
        {
            if (Busy(player)) return;
            if (player.IsSwimming() || player.IsAttached() || !player.IsOnGround()) return;
            var fwd = player.transform.forward; fwd.y = 0f; fwd.Normalize();
            var at = player.transform.position + fwd * Reach;
            if (IceHole.Near(at, 0.9f) != null)
            {
                // (still holding the button from the drill that just made it: nothing to say)
                if (Time.time - _madeAt < 2f) return;
                player.Message(MessageHud.MessageType.Center, "There's a hole here already - clear its slush with [E].");
                return;
            }
            if (!IceFishing.IceAt(at, out float iceY, out float under))
            {
                player.Message(MessageHud.MessageType.Center, "There's no ice here to drill.");
                return;
            }
            if (under < IceFishing.MinWaterUnderIce)
            {
                player.Message(MessageHud.MessageType.Center, "The ice here is frozen solid to the bottom.");
                return;
            }
            var zdo = Zdo(player);
            if (zdo == null) return;
            zdo.Set(KeyStart, Now);
            zdo.Set(KeyAt, new Vector3(at.x, iceY, at.z));
            zdo.Set(KeyYaw, Quaternion.LookRotation(fwd).eulerAngles.y);
            _from = player.transform.position;
        }

        private static float _madeAt = -100f;   // when the local player last finished a hole

        private static void Stop(Player p)
        {
            var zdo = Zdo(p);
            if (zdo != null && zdo.GetLong(KeyStart, 0L) > 0L) zdo.Set(KeyStart, 0L);
        }

        /// <summary>Every frame, after the animator (Plugin.LateUpdate): each drilling player posed, the local one's drill run.</summary>
        public static void LateUpdate()
        {
            if (!VdwConfig.Enabled.Value) return;
            var local = Player.m_localPlayer;
            if (local != null) RunLocal(local);
            foreach (var p in Player.GetAllPlayers())
            {
                if (p == null) continue;
                float t = Progress(p, out var at, out float yaw);
                if (t >= 0f && t <= Seconds && !p.IsDead()) Pose(p, t, at, yaw);
                else Release(p);
            }
        }

        private static void RunLocal(Player p)
        {
            float t = Progress(p, out var at, out _);
            if (t < 0f) return;
            var moved = p.transform.position - _from; moved.y = 0f;
            if (p.IsDead() || p.IsSwimming() || p.IsAttached() || !IceFishing.IsAuger(p.GetCurrentWeapon()) || moved.magnitude > 0.35f)
            {
                Stop(p);
                if (!p.IsDead()) p.Message(MessageHud.MessageType.Center, "You stop drilling.");
                return;
            }
            if (t < Seconds) return;
            Stop(p);
            IceFishing.MakeHole(p, at);
            _madeAt = Time.time;
        }

        // ------------------------------------------------------------------ the look

        private static void Pose(Player p, float t, Vector3 at, float yaw)
        {
            int id = p.GetInstanceID();
            if (!Rigs.TryGetValue(id, out var rig)) Rigs[id] = rig = new Rig();
            var shape = CustomModels.Shape(AugerModel);
            float u = Mathf.Clamp01(t / Seconds);
            float sink = Sink * Mathf.SmoothStep(0f, 1f, u);
            // twisted back and forth, as you turn a T-handle without letting go
            float twist = Mathf.Sin(t * Mathf.PI * 2f * 0.9f) * 65f;
            var turn = Quaternion.Euler(0f, yaw + twist, 0f);
            var tip = at + Vector3.down * sink;
            float length = shape?.Length ?? 1.43f;

            // the auger in the hand is hidden, and an upright one stands in the ice
            var vis = p.GetComponent<VisEquipment>();
            var inHand = vis != null ? RightItem(vis) : null;
            if (inHand != null && rig.Hidden != inHand)
            {
                Show(rig, false);
                rig.Hidden = inHand; Show(rig, true);
            }
            if (rig.Auger == null && shape != null && CustomModels.TryGetCustom(AugerModel, out var mesh, out var mat))
            {
                rig.Auger = new GameObject("vdw_drilling_auger");
                var model = new GameObject("model");
                model.transform.SetParent(rig.Auger.transform, false);
                // the point at the root, the handle straight up, the T-handle along x
                model.transform.localRotation = Quaternion.LookRotation(Vector3.Cross(Vector3.right, Vector3.up), Vector3.up) *
                                               Quaternion.Inverse(Quaternion.LookRotation(Vector3.Cross(shape.Cross, shape.Up), shape.Up));
                model.transform.localPosition = -(model.transform.localRotation * shape.Point);
                model.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = model.AddComponent<MeshRenderer>(); r.sharedMaterial = mat;
            }
            if (rig.Auger != null) { rig.Auger.transform.position = tip; rig.Auger.transform.rotation = turn; }

            // chips and the crunch of the ice, now and then while it bites
            if (Time.time >= rig.NextChip)
            {
                rig.NextChip = Time.time + 0.4f;
                Chips(p, at + Vector3.up * 0.03f);
            }

            // both hands on the T-handle, leaning into it
            var handle = tip + Vector3.up * (length - 0.025f);
            var across = turn * Vector3.right;
            FishingBoatOars.BeginPose(p);
            try
            {
                var tr = p.transform;
                // the body works with the arms: the shoulders and back turn with the handle (spread down the spine), each
                // turn bears down a little more, and the head stays on the hole
                float bear = Mathf.Abs(Mathf.Sin(t * Mathf.PI * 2f * 0.9f));                          // 0 at each turn's end, 1 mid-turn
                float lean = Mathf.Lerp(10f, 24f, u) + bear * 5f;
                float body = twist * 0.45f;                                                            // how far the shoulders follow the handle
                foreach (var (name, share) in new[] { ("Spine", 0.25f), ("Spine1", 0.4f), ("Spine2", 0.35f) })
                {
                    var b = FishingBoatOars.Bone(p, name);
                    if (b == null) continue;
                    b.rotation = Quaternion.AngleAxis(body * share, Vector3.up) * Quaternion.AngleAxis(lean * share, tr.right) * b.rotation;
                }
                var head = FishingBoatOars.Bone(p, "Head");
                if (head != null) head.rotation = Quaternion.AngleAxis(-body * 0.7f, Vector3.up) * Quaternion.AngleAxis(8f, tr.right) * head.rotation;
                foreach (var (prefix, side) in new[] { ("Left", -1f), ("Right", 1f) })
                {
                    var upper = FishingBoatOars.Bone(p, prefix + "Arm"); var lower = FishingBoatOars.Bone(p, prefix + "ForeArm"); var hand = FishingBoatOars.Bone(p, prefix + "Hand");
                    if (upper == null || lower == null || hand == null) continue;
                    // each hand on the end of the handle on its own side
                    var grip = handle + across * (GripOut * (Vector3.Dot(across, tr.right) >= 0f ? side : -side));
                    // closed round the handle, overhand: fingers forward and down over it, the thumb in toward the shaft
                    var fingers = Vector3.ProjectOnPlane(tr.forward - Vector3.up * 0.5f, across);
                    AnglerPose.Grasp(p, prefix, grip, side, fingers, handle - grip, 0.025f);
                }
            }
            finally { FishingBoatOars.EndPose(p); }
        }

        private static void Release(Player p)
        {
            int id = p.GetInstanceID();
            if (!Rigs.TryGetValue(id, out var rig)) return;
            Show(rig, false);
            if (rig.Auger != null) UnityEngine.Object.Destroy(rig.Auger);
            Rigs.Remove(id);
        }

        /// <summary>
        /// Hides the auger in the hand (hide: true), or shows it again: only the renderers that were showing come back - the
        /// vanilla spear it's built on stays hidden (turning every renderer back on brought the spear back with it).
        /// </summary>
        private static void Show(Rig rig, bool hide)
        {
            if (hide)
            {
                if (rig.Hidden == null) return;
                rig.Off.Clear();
                foreach (var r in rig.Hidden.GetComponentsInChildren<Renderer>(true)) if (r.enabled) { r.enabled = false; rig.Off.Add(r); }
            }
            else
            {
                foreach (var r in rig.Off) if (r != null) r.enabled = true;
                rig.Off.Clear();
            }
        }

        private static readonly string[] ChipFx = { "fx_footstep_ice_run", "fx_footstep_snow_run" };

        /// <summary>A puff of ice chips and its crunch. Effects that are network objects are made only by the driller's own game.</summary>
        private static void Chips(Player p, Vector3 at)
        {
            try
            {
                foreach (var name in ChipFx)
                {
                    var fx = PrefabManager.Cache.GetPrefab<GameObject>(name);
                    if (fx == null) continue;
                    if (fx.GetComponent<ZNetView>() != null && p != Player.m_localPlayer) return;
                    UnityEngine.Object.Instantiate(fx, at, Quaternion.identity);
                    return;
                }
            }
            catch (Exception ex) { Plugin.Log.LogDebug($"Ice auger chips: {ex.Message}"); }
        }

        public static void Shutdown()
        {
            foreach (var rig in Rigs.Values) { Show(rig, false); if (rig.Auger != null) UnityEngine.Object.Destroy(rig.Auger); }
            Rigs.Clear();
        }

        // ------------------------------------------------------------------ the auger's attack starts a drill instead

        [HarmonyPatch(typeof(Humanoid), nameof(Humanoid.StartAttack))]
        private static class AttackPatch
        {
            private static bool Prefix(Humanoid __instance, ref bool __result)
            {
                try
                {
                    if (!VdwConfig.Enabled.Value || !(__instance is Player player) || !IceFishing.IsAuger(player.GetCurrentWeapon())) return true;
                    __result = false;
                    if (player == Player.m_localPlayer) Begin(player);
                    return false;
                }
                catch (Exception ex) { Plugin.Log.LogWarning($"Ice auger: {ex.Message}"); return true; }
            }
        }
    }
}
