using HarmonyLib;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal enum RodEvent { None, Cast, CatchLift, Snap, HookSet, Twitch, Nibble }

    /// <summary>
    /// One angler's rod: found on their right hand, measured once (tip, grip, axis, reel), then each frame placed in
    /// their hands by <see cref="AnglerPose"/>, bent toward the line and its reel turned. One-off moments (cast, hook
    /// set, twitch, nibble, snap, landing) play for a short while.
    /// </summary>
    internal sealed class RodAnimator
    {
        public Transform? Rod;
        public RodRig? Rig;
        public Quaternion BaseLocal = Quaternion.identity;
        public Vector3 BaseLocalPos;

        // measured once per rod, in the rod's own space
        public bool HasTip;
        public Vector3 TipLocal, GripLocal, AxisLocal = Vector3.up, UpLocal = Vector3.forward;
        public bool HasReel;
        public Vector3 ReelLocal, AxleLocal = Vector3.right;

        public RodEvent Event = RodEvent.None;
        public float EventStart;

        // eased body pose (AnglerPose)
        public float Lean, Elevation = 35f;
        public float IdleW;          // the left hand put on the rod over Valheim's hold animation (no line out)
        public float PoseW;          // 0 Valheim's own animation (no line out, a cast) .. 1 our pose
        public bool Placed;

        public void Capture(Transform rod, Player player)
        {
            Rod = rod;
            BaseLocal = rod.localRotation;
            BaseLocalPos = rod.localPosition;
            Rig = rod.GetComponentInChildren<RodRig>(true);
            Rig?.Rest();
            RodMotion.ComputeTip(this, rod);

            GripLocal = Rig?.Grip != null ? rod.InverseTransformPoint(Rig.Grip.position) : Vector3.zero;
            Vector3 tip = Rig?.Tip != null ? rod.InverseTransformPoint(Rig.Tip.position) : HasTip ? TipLocal : GripLocal + Vector3.up;
            AxisLocal = (tip - GripLocal).sqrMagnitude > 1e-6f ? (tip - GripLocal).normalized : Vector3.up;
            // which way is "up" round the rod: as the hold animation has it now, so the reel stays on its usual side
            Vector3 up = Vector3.ProjectOnPlane(rod.InverseTransformDirection(player.transform.up), AxisLocal);
            UpLocal = up.sqrMagnitude > 1e-6f ? up.normalized : Vector3.Cross(AxisLocal, Vector3.right).normalized;

            HasReel = Rig?.Spool != null;
            if (HasReel)
            {
                ReelLocal = rod.InverseTransformPoint(Rig!.Spool!.position);
                AxleLocal = rod.InverseTransformDirection(Rig.SpoolAxis).normalized;
            }
            if (player == Player.m_localPlayer)
            {
                float s = rod.lossyScale.x, along = Vector3.Dot(ReelLocal - GripLocal, AxisLocal) * s;
                Plugin.Log.LogInfo($"Rod rig: {rod.name}, reel {(HasReel ? $"{along:0.00} m from the grip point, {Vector3.ProjectOnPlane(ReelLocal - GripLocal, AxisLocal).magnitude * s:0.00} m off the rod" : "none")}, scale {s:0.00}.");
            }
            Placed = false;
        }

        public void Restore()
        {
            if (Rod != null) { Rod.localRotation = BaseLocal; Rod.localPosition = BaseLocalPos; }
            Rig?.Rest();
        }

        public void Trigger(RodEvent e) { Event = e; EventStart = Time.time; }

        public float Since(RodEvent e) => Event == e ? Time.time - EventStart : 99f;
    }

    /// <summary>
    /// The rod animation for every angler. The local angler's comes from their fishing session; other players' from the
    /// state they share (AnglerSync), so everyone sees everyone fish. Runs every LateUpdate, after the animator.
    /// </summary>
    internal static class RodMotion
    {
        private static readonly FieldInfo? VisRightItem = AccessTools.Field(typeof(VisEquipment), "m_rightItemInstance");
        private static readonly Dictionary<int, RodAnimator> Anglers = new();
        private static bool _warnedNoRod;

        private static bool _charging;
        private static float _chargeFraction;

        private static RodAnimator? Local => Player.m_localPlayer != null && Anglers.TryGetValue(Player.m_localPlayer.GetInstanceID(), out var a) ? a : null;

        /// <summary>
        /// Called every frame while the player holds Attack to charge a cast; fraction is 0..1. Plays Valheim's own rod
        /// draw (as a bow's: a held animation state and how far drawn), which the animator syncs to everyone.
        /// </summary>
        public static void SetCharge(bool active, float fraction)
        {
            var zanim = LocalAnim(out var attack);
            if (zanim != null && attack != null && attack.m_drawAnimationState != "")
            {
                if (active) { zanim.SetBool(attack.m_drawAnimationState, true); zanim.SetFloat("drawpercent", Mathf.Clamp01(fraction)); }
                else if (_charging) zanim.SetBool(attack.m_drawAnimationState, false);
            }
            _charging = active;
            _chargeFraction = Mathf.Clamp01(fraction);
        }

        /// <summary>A one-off moment on the local angler's rod, shared with everyone (a cast plays Valheim's throw).</summary>
        public static void Trigger(RodEvent e)
        {
            Local?.Trigger(e);
            if (Player.m_localPlayer != null) AnglerSync.Event(Player.m_localPlayer, e);
            if (e == RodEvent.Cast)
            {
                var zanim = LocalAnim(out var attack);
                if (zanim != null && attack != null && attack.m_attackAnimation != "") zanim.SetTrigger(attack.m_attackAnimation);
            }
        }

        private static readonly FieldInfo? ZAnimField = AccessTools.Field(typeof(Character), "m_zanim");

        /// <summary>The local player's synced animator and their rod's attack (its animation names), if a rod is out.</summary>
        private static ZSyncAnimation? LocalAnim(out Attack? attack)
        {
            attack = null;
            var p = Player.m_localPlayer;
            var weapon = p != null ? p.GetCurrentWeapon() : null;
            if (p == null || weapon == null || !ContentRegistry.IsRod(weapon)) return null;
            attack = weapon.m_shared.m_attack;
            return ZAnimField?.GetValue(p) as ZSyncAnimation;
        }

        /// <summary>A fish nibbling a lure: the rod tip nods (there's no float to watch).</summary>
        public static void Tap(float strength) => Trigger(RodEvent.Nibble);

        public static void Reset()
        {
            foreach (var a in Anglers.Values) a.Restore();
            Anglers.Clear();
            _charging = false;
        }

        public static bool TryGetTip(out Vector3 tip)
        {
            var a = Local;
            if (a?.Rod != null && a.Rig != null && a.Rig.Tip != null) { tip = a.Rig.Tip.position; return true; }
            if (a?.Rod != null && a.HasTip) { tip = a.Rod.TransformPoint(a.TipLocal); return true; }
            tip = Vector3.zero;
            return false;
        }

        /// <summary>The local angler, from their session.</summary>
        public static void Apply(Player player, FishingSession? s, bool rodActive, bool reeling)
        {
            var st = new AnglerState { RodOut = rodActive, Charging = _charging, Charge = _chargeFraction, Reeling = reeling };
            if (s != null)
            {
                st.Phase = s.Phase == FishingPhase.Waiting ? 1 : s.Phase == FishingPhase.Bite ? 2 : 3;
                st.Pulling = s.Pulling;
                st.Running = s.Running;
                st.Lure = s.Lure != null;
                st.Load = s.Phase == FishingPhase.Fighting ? Mathf.Clamp01(s.Tension / Mathf.Max(1f, s.Rod.BreakTension)) : 0f;
                st.Angle = s.Angle;
                var end = FishingController.CurrentBobberPosition();
                st.HasTarget = end.HasValue;
                if (end.HasValue) st.Target = end.Value;
            }
            AnglerSync.Write(player, st);
            Animate(player, st, RodEvent.None);
        }

        /// <summary>Everyone else holding a Deep Waters rod, from what they share.</summary>
        public static void ApplyOthers(Player local)
        {
            foreach (var p in Player.GetAllPlayers())
            {
                if (p == null || p == local) continue;
                var st = AnglerSync.Read(p, out var fresh);
                st.RodOut &= !p.IsDead() && ContentRegistry.IsRod(p.GetCurrentWeapon());
                Animate(p, st, fresh);
            }
            // forget anglers who've gone
            if (Anglers.Count > 8)
            {
                var gone = new List<int>();
                foreach (var kv in Anglers) if (kv.Value.Rod == null) gone.Add(kv.Key);
                foreach (var k in gone) Anglers.Remove(k);
            }
        }

        private static void Animate(Player player, in AnglerState st, RodEvent fresh)
        {
            int id = player.GetInstanceID();
            Transform? rod = st.RodOut ? FindRod(player) : null;
            Anglers.TryGetValue(id, out var a);
            if (rod == null)
            {
                if (a != null) { a.Restore(); Anglers.Remove(id); }
                return;
            }
            if (a == null) Anglers[id] = a = new RodAnimator();
            if (a.Rod != rod) { a.Restore(); a.Capture(rod, player); }
            if (fresh != RodEvent.None) a.Trigger(fresh);

            a.Restore();
            AnglerPose.Pose(player, a, st);
            if (a.Rig != null) PoseRig(player, a, st);
            if (a.Event != RodEvent.None && Time.time - a.EventStart > 1.2f) a.Event = RodEvent.None;
        }

        private static Transform? FindRod(Player player)
        {
            GameObject? go = null;
            try
            {
                var vis = player.GetComponent<VisEquipment>();
                if (vis != null && VisRightItem != null) go = VisRightItem.GetValue(vis) as GameObject;
            }
            catch { }
            if (go == null && player == Player.m_localPlayer && !_warnedNoRod)
            {
                _warnedNoRod = true;
                Plugin.Log.LogWarning("Rod animation: could not find the equipped rod instance; rod motion and line anchoring are disabled.");
            }
            return go != null ? go.transform : null;
        }

        /// <summary>
        /// Bends a rigged rod toward the line (back on the wind-up, a whip on release, loaded by a fish, hauled hard when
        /// pulled back) and turns its reel: winding in while reeling, spinning backward as line pays out.
        /// </summary>
        private static void PoseRig(Player player, RodAnimator a, in AnglerState st)
        {
            float bend = 0f, spin = 0f, dt = Time.deltaTime, t = Time.time;
            Vector3 ahead = player.transform.position + player.transform.forward * 12f + Vector3.down * 2f;
            Vector3? toward = st.HasTarget ? st.Target : ahead;

            if (st.Charging)
            {
                bend = -16f * st.Charge;      // loading backward
                toward = ahead;
            }
            else if (a.Event == RodEvent.Cast || a.Event == RodEvent.CatchLift || a.Event == RodEvent.Snap || a.Event == RodEvent.HookSet)
            {
                float e = t - a.EventStart;
                switch (a.Event)
                {
                    case RodEvent.Cast:
                        toward = ahead;
                        bend = e < 0.06f ? Mathf.Lerp(-16f, 30f, e / 0.06f)
                                         : 30f * Mathf.Exp(-(e - 0.06f) * 7f) * Mathf.Cos((e - 0.06f) * 28f);
                        if (e < 0.6f) spin = -2200f * dt;          // line flying off the reel
                        break;
                    case RodEvent.CatchLift:
                        bend = 32f * Mathf.Sin(Mathf.Clamp01(e / 0.8f) * Mathf.PI);   // the fish's weight
                        toward = player.transform.position + player.transform.forward * 2f + Vector3.down * 3f;
                        break;
                    case RodEvent.Snap:
                        float k = 1f - Mathf.Clamp01(e / 0.5f);
                        bend = -24f * k * Mathf.Cos(e * 40f); // springing back when the line breaks
                        break;
                    case RodEvent.HookSet:
                        bend = 46f * Mathf.Sin(Mathf.Clamp01(e / 0.55f) * Mathf.PI);   // the hook biting home
                        break;
                }
            }
            else
            {
                switch (st.Phase)
                {
                    case 1:
                        // the tip drooping toward where the line goes into the water, more with a lure being worked
                        bend = (st.Lure ? (st.Reeling ? 20f : 12f) : 14f) + Mathf.Sin(t * 1.5f) * 2f + AnglerPose.Pop(a) * 18f + AnglerPose.Nod(a) * 14f;
                        break;
                    case 2:
                        bend = 22f + Mathf.Sin(t * 35f) * 8f;
                        break;
                    case 3:
                        bend = 72f * Mathf.Pow(st.Load, 0.85f);
                        if (st.Pulling) bend = Mathf.Max(bend, 40f) * 1.25f;             // hauling back on it
                        if (st.Running) bend += Mathf.Sin(t * 28f) * 5f * (0.4f + st.Load);
                        if (st.Reeling) bend += Mathf.Sin(t * 14f) * 1.5f;
                        if (st.Running && !st.Reeling) spin -= 600f * st.Load * dt;   // line stripping off against the drag
                        break;
                }
            }
            if (st.Reeling) spin += 900f * dt;          // winding in, about two and a half turns a second

            a.Rig!.Pose(bend, toward, spin);
        }

        /// <summary>Degrees the rod tips down (negative: up) during a one-off moment.</summary>
        internal static float EventPitch(RodAnimator a)
        {
            float e = Time.time - a.EventStart;
            switch (a.Event)
            {
                case RodEvent.Cast:
                    // snaps forward within a couple of frames of release, then settles
                    if (e > 0.3f) return 0f;
                    if (e < 0.06f) return Mathf.Lerp(-48f, 32f, e / 0.06f);
                    return Mathf.Lerp(32f, 0f, Mathf.Clamp01((e - 0.06f) / 0.24f));
                case RodEvent.CatchLift:
                    return e > 0.8f ? 0f : -40f * Mathf.Sin(Mathf.Clamp01(e / 0.8f) * Mathf.PI);
                case RodEvent.Snap:
                {
                    if (e > 0.5f) return 0f;
                    float k = 1f - Mathf.Clamp01(e / 0.5f);
                    return -40f * k + Mathf.Sin(e * 45f) * 6f * k;
                }
                default:
                    return 0f;
            }
        }

        /// <summary>
        /// Finds the rod's tip in rod-local space: along the mesh's longest axis, the end farther from the grip
        /// (the local origin) is the tip, and the vertex closest to that end is used. Runs once per equip.
        /// </summary>
        internal static void ComputeTip(RodAnimator a, Transform rod)
        {
            a.HasTip = false;
            var filters = rod.GetComponentsInChildren<MeshFilter>();
            Vector3 min = Vector3.zero, max = Vector3.zero;
            bool any = false;
            foreach (var mf in filters)
            {
                if (mf.sharedMesh == null) continue;
                foreach (var local in EnumeratePoints(rod, mf))
                {
                    if (!any) { min = max = local; any = true; continue; }
                    min = Vector3.Min(min, local);
                    max = Vector3.Max(max, local);
                }
            }
            if (!any) return;

            Vector3 extent = max - min;
            int axis = 0;
            if (extent.y > extent.x && extent.y >= extent.z) axis = 1;
            else if (extent.z > extent.x && extent.z >= extent.y) axis = 2;
            float minAlong = axis == 0 ? min.x : axis == 1 ? min.y : min.z;
            float maxAlong = axis == 0 ? max.x : axis == 1 ? max.y : max.z;
            float target = Mathf.Abs(maxAlong) >= Mathf.Abs(minAlong) ? maxAlong : minAlong;

            float bestDist = float.MaxValue;
            foreach (var mf in filters)
            {
                if (mf.sharedMesh == null) continue;
                foreach (var local in EnumeratePoints(rod, mf))
                {
                    float v = axis == 0 ? local.x : axis == 1 ? local.y : local.z;
                    float d = Mathf.Abs(v - target);
                    if (d < bestDist) { bestDist = d; a.TipLocal = local; a.HasTip = true; }
                }
            }
        }

        /// <summary>Every mesh point (real vertices if readable, else the 8 bounds corners), in the rod's local space.</summary>
        private static IEnumerable<Vector3> EnumeratePoints(Transform rod, MeshFilter mf)
        {
            var mesh = mf.sharedMesh;
            if (mesh.isReadable)
            {
                foreach (var v in mesh.vertices)
                    yield return rod.InverseTransformPoint(mf.transform.TransformPoint(v));
            }
            else
            {
                var b = mesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var corner = b.center + new Vector3(
                        (i & 1) == 0 ? -b.extents.x : b.extents.x,
                        (i & 2) == 0 ? -b.extents.y : b.extents.y,
                        (i & 4) == 0 ? -b.extents.z : b.extents.z);
                    yield return rod.InverseTransformPoint(mf.transform.TransformPoint(corner));
                }
            }
        }
    }
}
