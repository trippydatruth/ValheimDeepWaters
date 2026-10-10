using HarmonyLib;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal enum RodEvent { None, Cast, CatchLift, Snap }

    /// <summary>
    /// Client-side procedural rod animation. The rod's item instance is a child of the hand bone, so the
    /// animator never touches its local rotation; we reset it to the captured base every LateUpdate and then
    /// apply a world-space pitch about the player's right axis (positive pitch = tip down).
    /// </summary>
    internal static class RodMotion
    {
        // The equipped item's visual GameObject.
        private static readonly FieldInfo? VisRightItem = AccessTools.Field(typeof(VisEquipment), "m_rightItemInstance");

        private static Transform? _rod;
        private static RodRig? _rig; // set when the rod model is rigged: it bends and its reel turns
        private static Quaternion _baseLocal = Quaternion.identity;
        private static Vector3 _baseLocalPos;
        private static bool _hasTip;
        private static Vector3 _tipLocal;
        private static bool _warnedNoRod;

        private static RodEvent _event = RodEvent.None;
        private static float _eventStart;

        private static bool _charging;
        private static float _chargeFraction;

        /// <summary>Called every frame while the player holds Attack to charge a cast; fraction is 0..1.</summary>
        public static void SetCharge(bool active, float fraction)
        {
            _charging = active;
            _chargeFraction = Mathf.Clamp01(fraction);
        }

        public static void Trigger(RodEvent e)
        {
            _event = e;
            _eventStart = Time.time;
        }

        private static float _tapTime = -100f, _tapStrength;

        /// <summary>A fish nibbling a lure: the rod tip nods down sharply and springs back (there's no float to watch).</summary>
        public static void Tap(float strength)
        {
            _tapTime = Time.time;
            _tapStrength = Mathf.Clamp01(strength);
        }

        private static float TapPulse(float t)
        {
            float e = (t - _tapTime) / 0.35f;
            return e < 0f || e > 1f ? 0f : Mathf.Sin(e * Mathf.PI) * (1f - e * 0.5f) * _tapStrength;
        }

        public static void Reset()
        {
            Restore();
            _rod = null;
            _rig = null;
            _hasTip = false;
            _event = RodEvent.None;
            _charging = false;
        }

        private static void Restore()
        {
            if (_rod != null) { _rod.localRotation = _baseLocal; _rod.localPosition = _baseLocalPos; }
            if (_rig != null) _rig.Rest();
        }

        private static Transform? FindRod(Player player)
        {
            GameObject? go = null;
            try
            {
                if (VisRightItem != null)
                {
                    var vis = player.GetComponent<VisEquipment>();
                    if (vis != null) go = VisRightItem.GetValue(vis) as GameObject;
                }
            }
            catch { }

            if (go == null && !_warnedNoRod)
            {
                _warnedNoRod = true;
                Plugin.Log.LogWarning("Rod animation: could not find the equipped rod instance; rod motion and line anchoring are disabled.");
            }
            return go != null ? go.transform : null;
        }

        private static void CaptureRod(Transform rod)
        {
            _rod = rod;
            _baseLocal = rod.localRotation;
            _baseLocalPos = rod.localPosition;
            _rig = rod.GetComponentInChildren<RodRig>(true);
            ComputeTip(rod);

            // A rigged rod with a grip marker: its unbent axis (grip to tip) in the rod's own space, for aiming it
            // through the left hand.
            _hasAxis = false;
            if (_rig != null && _rig.Grip != null && _rig.Tip != null)
            {
                _rig.Rest();
                var along = _rig.Tip.position - _rig.Grip.position;
                if (along.sqrMagnitude > 1e-6f)
                {
                    _gripLocal = rod.InverseTransformPoint(_rig.Grip.position);
                    _axisLocal = rod.InverseTransformDirection(along.normalized);
                    _hasAxis = true;
                }
            }
        }

        private static bool _hasAxis;
        private static Vector3 _gripLocal, _axisLocal;

        /// <summary>
        /// The hold animation was made for the vanilla rod, so a custom rod can miss the left hand. Turns the rod about
        /// its grip so its axis runs through the left hand - small corrections only, while the hand is on the rod.
        /// </summary>
        private static void AimThroughLeftHand(Player player)
        {
            if (!_hasAxis || _rod == null) return;
            var left = player.GetComponent<VisEquipment>()?.m_leftHand;
            if (left == null) return;
            Vector3 grip = _rod.TransformPoint(_gripLocal);
            Vector3 axis = _rod.TransformDirection(_axisLocal);
            Vector3 toHand = left.position - grip;
            float along = Vector3.Dot(toHand, axis);
            if (along < 0.15f || along > 1.4f) return;                       // the hand isn't on the rod
            var turn = Quaternion.FromToRotation(axis, toHand.normalized);
            turn.ToAngleAxis(out float angle, out Vector3 turnAxis);
            if (angle > 180f) angle -= 360f;
            if (Mathf.Abs(angle) > 30f || turnAxis.sqrMagnitude < 1e-6f) return;
            // About the grip, which stays in the right hand.
            Vector3 pivot = grip;
            _rod.rotation = turn * _rod.rotation;
            _rod.position += pivot - _rod.TransformPoint(_gripLocal);
        }

        /// <summary>
        /// Finds the rod's tip in rod-local space: along the mesh's longest axis, the end farther from the grip
        /// (the local origin) is the tip, and the vertex closest to that end is used. Runs once per equip.
        /// </summary>
        private static void ComputeTip(Transform rod)
        {
            _hasTip = false;

            var filters = rod.GetComponentsInChildren<MeshFilter>();

            Vector3 min = Vector3.zero, max = Vector3.zero;
            bool any = false;

            foreach (var mf in filters)
            {
                var mesh = mf.sharedMesh;
                if (mesh == null) continue;

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
            bool tipIsMax = Mathf.Abs(maxAlong) >= Mathf.Abs(minAlong);
            float target = tipIsMax ? maxAlong : minAlong;

            float bestDist = float.MaxValue;
            Vector3 bestPoint = Vector3.zero;
            bool found = false;

            foreach (var mf in filters)
            {
                var mesh = mf.sharedMesh;
                if (mesh == null) continue;

                foreach (var local in EnumeratePoints(rod, mf))
                {
                    float v = axis == 0 ? local.x : axis == 1 ? local.y : local.z;
                    float d = Mathf.Abs(v - target);
                    if (d < bestDist)
                    {
                        bestDist = d;
                        bestPoint = local;
                        found = true;
                    }
                }
            }

            if (found)
            {
                _tipLocal = bestPoint;
                _hasTip = true;
            }
        }

        /// <summary>Yields every mesh point (real vertices if readable, else the 8 bounds corners), already
        /// converted into the rod's local space.</summary>
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

        public static bool TryGetTip(out Vector3 tip)
        {
            // A rigged rod: the tip marker, which follows the bend.
            if (_rod != null && _rig != null && _rig.Tip != null)
            {
                tip = _rig.Tip.position;
                return true;
            }
            if (_rod != null && _hasTip)
            {
                tip = _rod.TransformPoint(_tipLocal);
                return true;
            }
            tip = Vector3.zero;
            return false;
        }

        public static void Apply(Player player, FishingSession? s, bool rodActive, bool reeling)
        {
            Transform? rod = rodActive ? FindRod(player) : null;

            if (rod != _rod)
            {
                Restore();
                _rod = null;
                _hasTip = false;
                if (rod != null) CaptureRod(rod);
            }

            if (_rod == null) return;

            _rod.localRotation = _baseLocal;
            _rod.localPosition = _baseLocalPos;
            AimThroughLeftHand(player);
            float pitch = 0f;
            float t = Time.time;

            if (_charging)
            {
                // Wind-up: tip pulls back the longer Attack is held.
                pitch = -Mathf.Lerp(0f, 48f, _chargeFraction);
            }
            else if (_event != RodEvent.None)
            {
                float e = t - _eventStart;
                float done;
                pitch = EventPitch(_event, e, out done);
                if (done >= 1f) _event = RodEvent.None;
            }
            else if (s != null)
            {
                switch (s.Phase)
                {
                    case FishingPhase.Waiting:
                        pitch = Mathf.Sin(t * 1.5f) * 1.5f + TapPulse(t) * 7f;
                        break;
                    case FishingPhase.Bite:
                        pitch = 9f + Mathf.Sin(t * 35f) * 5f;
                        break;
                    case FishingPhase.Fighting:
                        float load = Mathf.Clamp01(s.Tension / Mathf.Max(1f, s.Rod.BreakTension));
                        // A rigged rod shows the load in its bend, so the whole rod tips less.
                        pitch = Mathf.Lerp(2f, _rig != null ? 12f : 28f, load);
                        if (s.Running) pitch += Mathf.Sin(t * 28f) * 3.5f * (0.4f + load);
                        if (reeling) pitch += Mathf.Sin(t * 14f) * 1.5f;
                        break;
                }
            }

            if (Mathf.Abs(pitch) > 0.01f)
                _rod.rotation = Quaternion.AngleAxis(pitch, player.transform.right) * _rod.rotation;

            // The rod follows a fish that's pulled the line off to one side.
            if (s != null && s.Phase == FishingPhase.Fighting && Mathf.Abs(s.Angle) > 0.5f)
                _rod.rotation = Quaternion.AngleAxis(s.Angle * 0.35f, Vector3.up) * _rod.rotation;

            if (_rig != null) PoseRig(player, s, reeling, t);
        }

        /// <summary>
        /// Bends a rigged rod toward the line (back on the wind-up, a whip on release, loaded by a fish) and turns its
        /// reel: winding in while reeling, spinning backward as line pays out on a cast or a running fish.
        /// </summary>
        private static void PoseRig(Player player, FishingSession? s, bool reeling, float t)
        {
            float bend = 0f, spin = 0f, dt = Time.deltaTime;
            Vector3 ahead = player.transform.position + player.transform.forward * 12f + Vector3.down * 2f;
            Vector3? toward = FishingController.CurrentBobberPosition() ?? ahead;

            if (_charging)
            {
                bend = -16f * _chargeFraction;      // loading backward
                toward = ahead;
            }
            else if (_event != RodEvent.None)
            {
                float e = t - _eventStart;
                switch (_event)
                {
                    case RodEvent.Cast:
                        toward = ahead;
                        bend = e < 0.06f ? Mathf.Lerp(-16f, 30f, e / 0.06f)
                                         : 30f * Mathf.Exp(-(e - 0.06f) * 7f) * Mathf.Cos((e - 0.06f) * 28f);
                        spin = -2200f * dt;          // line flying off the reel
                        break;
                    case RodEvent.CatchLift:
                        bend = 32f * Mathf.Sin(Mathf.Clamp01(e / 0.8f) * Mathf.PI);   // the fish's weight
                        toward = player.transform.position + player.transform.forward * 2f + Vector3.down * 3f;
                        break;
                    case RodEvent.Snap:
                        float k = 1f - Mathf.Clamp01(e / 0.5f);
                        bend = -24f * k * Mathf.Cos(e * 40f); // springing back when the line breaks
                        break;
                }
            }
            else if (s != null)
            {
                switch (s.Phase)
                {
                    case FishingPhase.Waiting:
                        bend = 4f + Mathf.Sin(t * 1.5f) * 1.5f + TapPulse(t) * 14f;
                        break;
                    case FishingPhase.Bite:
                        bend = 10f + Mathf.Sin(t * 35f) * 7f;
                        break;
                    case FishingPhase.Fighting:
                        float load = Mathf.Clamp01(s.Tension / Mathf.Max(1f, s.Rod.BreakTension));
                        bend = 72f * Mathf.Pow(load, 0.85f);
                        if (s.Running) bend += Mathf.Sin(t * 28f) * 5f * (0.4f + load);
                        if (reeling) bend += Mathf.Sin(t * 14f) * 1.5f;
                        if (s.Running && !reeling) spin -= 600f * load * dt;   // line stripping off against the drag
                        break;
                }
            }
            if (reeling) spin += 900f * dt;          // winding in, about two and a half turns a second

            _rig!.Pose(bend, toward, spin);
        }

        private static float EventPitch(RodEvent ev, float e, out float done)
        {
            switch (ev)
            {
                case RodEvent.Cast:
                {
                    // Snaps forward within a couple of frames of release, then settles.
                    done = e / 0.3f;
                    if (e < 0.06f) return Mathf.Lerp(-48f, 32f, e / 0.06f);
                    return Mathf.Lerp(32f, 0f, Mathf.Clamp01((e - 0.06f) / 0.24f));
                }
                case RodEvent.CatchLift:
                {
                    done = e / 0.8f;
                    return -40f * Mathf.Sin(Mathf.Clamp01(e / 0.8f) * Mathf.PI);
                }
                case RodEvent.Snap:
                {
                    done = e / 0.5f;
                    float k = 1f - Mathf.Clamp01(e / 0.5f);
                    return -40f * k + Mathf.Sin(e * 45f) * 6f * k;
                }
                default:
                    done = 1f;
                    return 0f;
            }
        }
    }
}
