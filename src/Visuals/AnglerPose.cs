using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The angler's body and hands, posed over the animation (Valheim's own reeling pump is switched off while the rod is
    /// out, see NoVanillaRodControls). The rod is held in the left hand and placed there each frame at the angle it
    /// should be at, just above the reel; the right hand stays on the reel handle, winding it while reeling:
    /// - waiting: rod up; working a lure: rod low toward the water;
    /// - a fish on: pull back (left click) hauls the rod high, leaning back, bending it hard; winding brings it down and
    ///   leans in; a running fish drags it toward the water and shakes it;
    /// - hook set: a sharp sweep up and back; twitch: a quick pop of the tip; nibble: a nod.
    /// Casting (and holding the rod with no line out) is Valheim's own animation; this pose blends in
    /// once the line is in the water. The same pose is used for every angler (others from what they share), so everyone sees it.
    /// </summary>
    internal static class AnglerPose
    {
        private const float HookSetTime = 0.55f, PopDown = 0.07f, PopBack = 0.2f, NodTime = 0.35f;

        // How long Valheim's own throw animation plays after a cast before our pose takes the body back (s).
        private const float CastAnimTime = 0.9f;

        // Where the reel sits (forward, down, to the right of the shoulders' midpoint, metres): in front of the belly, a
        // little right. vdw_debug hold sets it in game.
        internal static Vector3 Hold = new Vector3(0.30f, 0.40f, 0.12f);
        // the left hand: how far up the rod from the reel it holds (m), nudged up, right and forward (m), and rolled round
        // the rod (degrees) - vdw_debug lefthand
        internal static float LeftAlong = 0.09f, LeftUp = 0f, LeftRight = 0f, LeftRoll = -50f, LeftForward = 0f;
        // the right hand: on the reel's handle (nudged up, right, forward; rolled); on a rod with no reel, RightAlong down the
        // butt from the grip - vdw_debug righthand
        internal static float RightAlong = -0.22f, RightUp = 0f, RightRight = 0f, RightRoll = 0f, RightForward = 0f;
        // with no line out (Valheim's hold animation, the rod low in the right hand), how far up the rod from the reel the
        // left hand takes it - further than with a line out, out along the rod - vdw_debug idlehand
        internal static float IdleLeftAlong = 0.5f;           // fitted in game
        // and the whole hold (both hands and the rod) moved this far right, up and forward of Valheim's (m) - vdw_debug idleshift
        internal static Vector3 IdleShift = new Vector3(0.06f, 0f, 0.06f);

        /// <summary>0..1..0 over a short event.</summary>
        private static float Pulse(float since, float length) =>
            since < 0f || since > length ? 0f : Mathf.Sin(Mathf.Clamp01(since / length) * Mathf.PI);

        /// <summary>A twitch: the tip snaps down fast and comes back a little slower.</summary>
        public static float Pop(RodAnimator a)
        {
            float e = a.Since(RodEvent.Twitch);
            if (e > PopDown + PopBack) return 0f;
            return e < PopDown ? e / PopDown : 1f - (e - PopDown) / PopBack;
        }

        public static float Nod(RodAnimator a) => Pulse(a.Since(RodEvent.Nibble), NodTime);

        public static void Pose(Player player, RodAnimator a, in AnglerState st)
        {
            if (a.Rod == null) return;
            float dt = Time.deltaTime, now = Time.time;

            // Valheim animates the body itself with no line out, while a cast charges and through the throw (its own
            // bow-style draw and cast, driven by RodMotion and synced like any animation). Our pose blends in once the
            // line is in the water and blends back out for the next cast.
            bool vanilla = st.Phase == 0 || st.Charging || a.Since(RodEvent.Cast) < CastAnimTime;
            a.PoseW = Mathf.MoveTowards(a.PoseW, vanilla ? 0f : 1f, (vanilla ? 6f : 3f) * dt);
            // Holding the rod with no line out, Valheim's hold animation has the left hand where its own rod would be: it
            // goes onto ours instead (eased in and out, so starting a cast doesn't snap it away).
            a.IdleW = Mathf.MoveTowards(a.IdleW, st.Phase == 0 && !st.Charging && a.Since(RodEvent.Cast) >= CastAnimTime ? 1f : 0f, 4f * dt);
            if (a.PoseW <= 0f)
            {
                a.Placed = false;
                if (a.IdleW > 0f) IdleLeftHand(player, a);
                return;
            }
            var t = player.transform;

            // How high the rod is held (degrees above level) and how far the angler leans back.
            float elev = 35f, lean = 0f;
            // where the left hand holds it, from between the shoulders (Hold: forward, down, to the right), so the rod sits on
            // the right side with the right hand winding the reel beside it
            float forward = Hold.x, down = Hold.y, side = Hold.z;
            if (st.Phase == 1) { elev = st.Lure && st.Reeling ? 14f : 30f; if (st.Lure) { forward = Hold.x + 0.07f; down = Hold.y - 0.02f; } }
            else if (st.Phase == 2) { elev = 30f + Mathf.Sin(now * 35f) * 3f; }
            else if (st.Phase == 3)
            {
                if (st.Pulling) { elev = 62f + 8f * st.Load; lean = 12f + 8f * st.Load; forward = Hold.x - 0.10f; down = Hold.y - 0.20f; }
                else if (st.Running) { elev = 20f - 6f * st.Load; lean = 10f + 6f * st.Load; forward = Hold.x + 0.14f; }
                else if (st.Reeling) { elev = 24f; lean = 3f; }
                else { elev = 34f + 8f * st.Load; lean = 5f * st.Load; }
            }
            a.Elevation = a.Placed ? Mathf.MoveTowards(a.Elevation, elev, 160f * dt) : elev;
            a.Lean = a.Placed ? Mathf.MoveTowards(a.Lean, lean, 50f * dt) : lean;
            a.Placed = true;

            float hook = Pulse(a.Since(RodEvent.HookSet), HookSetTime);
            float pop = Pop(a), nod = Nod(a);
            float shake = st.Phase == 3 && st.Running ? Mathf.Sin(now * 26f) * 3f : 0f;
            // a little life: breathing and a slow drift, on mismatched beats and different for each angler
            float ph = (player.GetInstanceID() & 1023) * 0.37f;
            float swayElev = Mathf.Sin(now * 0.9f + ph) * 2f + Mathf.Sin(now * 2.3f + ph * 1.7f) * 0.7f;
            float swayYaw = Mathf.Sin(now * 0.6f + ph * 1.3f) * 2.5f;
            float swayLean = Mathf.Sin(now * 0.75f + ph) * 1.2f;
            float breathe = Mathf.Sin(now * 1.6f + ph) * 0.012f;
            float rodElev = a.Elevation + hook * 45f - pop * 32f - nod * 8f - (a.Event == RodEvent.Cast ? 0f : RodMotion.EventPitch(a)) + shake + swayElev;

            FishingBoatOars.BeginPose(player);
            try
            {
                // leaning back, in the upper back only (the lowest spine bone stays put so the waist - and the belt on
                // it - doesn't bend)
                float leanBy = -(a.Lean + hook * 14f + swayLean) / 2f;
                foreach (var name in new[] { "Spine1", "Spine2" })
                {
                    var spine = FishingBoatOars.Bone(player, name);
                    if (spine != null) spine.rotation = Quaternion.AngleAxis(leanBy, t.right) * spine.rotation;
                }

                var lUpper = FishingBoatOars.Bone(player, "LeftArm");
                var rUpper = FishingBoatOars.Bone(player, "RightArm");
                if (lUpper == null || rUpper == null) return;
                Vector3 shoulders = (lUpper.position + rUpper.position) * 0.5f;

                // The rod's direction: at its angle, out over the water (turned toward a fish off to the side).
                Vector3 dir = Quaternion.AngleAxis((st.Phase == 3 ? st.Angle * 0.35f : 0f) + swayYaw, Vector3.up)
                              * Quaternion.AngleAxis(-rodElev, t.right) * t.forward;
                // The rod's own frame, for hand nudges that stay on the rod however it's angled.
                Vector3 rodRight = Vector3.ProjectOnPlane(t.right, dir).normalized, rodUp = Vector3.Cross(dir, rodRight);
                Vector3 Nudge(float right, float upBy, float fwd) => RodNudge(rodRight, rodUp, dir, right, upBy, fwd);

                Vector3 up = Vector3.ProjectOnPlane(t.up, dir);
                if (up.sqrMagnitude < 1e-6f) up = -t.forward;
                Quaternion rot = Quaternion.LookRotation(dir, up) * Quaternion.Inverse(Quaternion.LookRotation(a.AxisLocal, a.UpLocal));
                float s = Mathf.Max(1e-4f, a.Rod.lossyScale.x);                      // rods are scaled evenly

                // Where the reel sits (pulled in and up on a haul, flicked on a pop) - both hands work from it.
                Vector3 grip = shoulders + t.forward * (forward - pop * 0.05f) - t.up * (down - hook * 0.12f - breathe) + t.right * side;
                // the reel's foot: the point on the rod above the reel (the grip point on a rod without one)
                Vector3 anchor = ReelFoot(a);

                // Where each hand goes for the rod placed with its reel at a point.
                Vector3 pos = Vector3.zero, leftT = Vector3.zero, rightT = Vector3.zero;
                Vector3 leftFingers = Vector3.zero, rightFingers = Vector3.zero;
                void Place(Vector3 at)
                {
                    pos = at - rot * (anchor * s);
                    Vector3 W(Vector3 local) => pos + rot * (local * s);             // rod space to world, as placed
                    // the left hand round the rod just above the reel (LeftAlong up from it, nudged), fingers across it,
                    // thumb along it
                    leftT = W(anchor + a.AxisLocal * (LeftAlong / s)) + Nudge(LeftRight, LeftUp, LeftForward);
                    leftFingers = Quaternion.AngleAxis(LeftRoll, dir) * Vector3.ProjectOnPlane(t.right - t.up * 0.3f, dir);

                    // the right hand: on the reel's handle (going round with it while reeling), or round the butt of a rod
                    // with no reel
                    if (a.HasReel && a.Rig != null)
                    {
                        Vector3 reel = W(a.ReelLocal);
                        Vector3 axle = (rot * a.AxleLocal).normalized;
                        if (Vector3.Dot(axle, t.right) < 0f) axle = -axle;        // the handle on the right-hand side
                        Vector3 spoke = Vector3.ProjectOnPlane(t.up, axle);
                        if (spoke.sqrMagnitude < 1e-6f) spoke = Vector3.ProjectOnPlane(t.forward, axle);
                        spoke = Quaternion.AngleAxis(a.Rig.Spin, axle) * spoke.normalized;
                        rightT = reel + axle * 0.06f + spoke * 0.05f + Nudge(RightRight, RightUp, RightForward);
                        rightFingers = Quaternion.AngleAxis(RightRoll, axle) * (-t.up + t.forward * 0.3f);   // round the knob
                    }
                    else
                    {
                        rightT = W(a.GripLocal + a.AxisLocal * (RightAlong / s)) + Nudge(RightRight, RightUp, RightForward);
                        rightFingers = Quaternion.AngleAxis(RightRoll, dir) * Vector3.ProjectOnPlane(-t.right - t.up * 0.3f, dir);
                    }
                }
                Place(grip);
                // Both hands must reach: if one would have to stretch past most of its arm's length, the rod moves toward
                // that shoulder by the difference (exactly enough, as the hand moves with the rod), so the hands stay on
                // it and the elbows keep a bend.
                for (int i = 0; i < 6; i++)
                {
                    float overL = Overreach(player, "Left", leftT), overR = Overreach(player, "Right", rightT);
                    if (overL <= 0.002f && overR <= 0.002f) break;
                    bool left = overL >= overR;
                    Vector3 shoulder = (left ? lUpper : rUpper).position, hand = left ? leftT : rightT;
                    grip += (shoulder - hand).normalized * Mathf.Max(overL, overR);
                    Place(grip);
                }

                Grasp(player, "Left", leftT, -1f, leftFingers, dir, 0.03f);
                Grasp(player, "Right", rightT, 1f, rightFingers, dir, 0.025f);

                // Last, as the rod hangs off the right hand: put it in the left.
                a.Rod.SetPositionAndRotation(pos, rot);

                // Part way between Valheim's animation and ours (going into or out of a cast): mix the body, and the rod
                // where it sits in the right hand, so neither jumps.
                if (a.PoseW < 1f)
                {
                    Quaternion ourRot = a.Rod.localRotation;
                    Vector3 ourPos = a.Rod.localPosition;
                    FishingBoatOars.BlendPose(player, a.PoseW);
                    a.Rod.localRotation = Quaternion.Slerp(a.BaseLocal, ourRot, a.PoseW);
                    a.Rod.localPosition = Vector3.Lerp(a.BaseLocalPos, ourPos, a.PoseW);
                }
            }
            finally { FishingBoatOars.EndPose(player); }
        }

        /// <summary>The point on the rod above its reel (the grip point on a rod without one), in the rod's own space.</summary>
        private static Vector3 ReelFoot(RodAnimator a) =>
            a.HasReel ? a.GripLocal + a.AxisLocal * Vector3.Dot(a.ReelLocal - a.GripLocal, a.AxisLocal) : a.GripLocal;

        /// <summary>
        /// With no line out: the rod stays where Valheim's hold animation has it in the right hand, and the left hand takes
        /// hold of it well up the rod (IdleLeftAlong from the reel; vdw_debug idlehand, and lefthand's nudges).
        /// </summary>
        private static void IdleLeftHand(Player player, RodAnimator a)
        {
            if (a.Rod == null) return;
            var lUpper = FishingBoatOars.Bone(player, "LeftArm");
            if (lUpper == null) return;
            var t = player.transform;
            float s = Mathf.Max(1e-4f, a.Rod.lossyScale.x);

            FishingBoatOars.BeginPose(player);
            try
            {
                // The whole hold a little right and forward of where Valheim's animation has it (IdleShift): the right arm
                // carries the rod there, its hand keeping its angle so the rod doesn't tip.
                var rHand = FishingBoatOars.Bone(player, "RightHand");
                if (rHand != null)
                {
                    Quaternion keep = rHand.rotation;
                    Arm(player, "Right", rHand.position + t.right * IdleShift.x + t.up * IdleShift.y + t.forward * IdleShift.z, 1f);
                    rHand.rotation = keep;
                }

                // Valheim's hold has the rod low at the right hip, out of the left hand's reach past the reel. The rod turns in
                // the right hand (about the reel) toward where a left hand rests - in front of the belly - just as far as it
                // takes for the left hand to reach IdleLeftAlong up it; if even turned all the way it can't, the hand comes
                // back down the rod until it can.
                Vector3 grip = a.Rod.TransformPoint(ReelFoot(a));
                Vector3 axis0 = (a.Rod.rotation * a.AxisLocal).normalized;
                Vector3 rest = lUpper.position + t.forward * 0.38f - t.up * 0.38f + t.right * 0.12f;
                Vector3 toward = (rest - grip).sqrMagnitude > 1e-4f ? (rest - grip).normalized : axis0;
                float along = Mathf.Clamp(IdleLeftAlong, 0.05f, 1.5f);
                bool Reaches(Vector3 d, float l) => Overreach(player, "Left", grip + d * l, 0.95f) <= 0f;
                Vector3 dir = toward;
                for (int i = 0; i <= 10; i++)
                {
                    Vector3 d = Vector3.Slerp(axis0, toward, i / 10f);
                    if (Reaches(d, along)) { dir = d; break; }
                }
                if (!Reaches(dir, along))
                {
                    float lo = 0.05f, hi = along;
                    for (int i = 0; i < 12; i++) { float mid = (lo + hi) * 0.5f; if (Reaches(dir, mid)) lo = mid; else hi = mid; }
                    along = lo;
                }
                dir = Vector3.Slerp(axis0, dir, a.IdleW);
                a.Rod.rotation = Quaternion.FromToRotation(axis0, dir) * a.Rod.rotation;
                a.Rod.position += grip - a.Rod.TransformPoint(ReelFoot(a));

                Vector3 axis = dir;
                Vector3 rodRight = Vector3.ProjectOnPlane(t.right, axis).normalized, rodUp = Vector3.Cross(axis, rodRight);
                Vector3 target = a.Rod.TransformPoint(ReelFoot(a) + a.AxisLocal * (along / s)) + RodNudge(rodRight, rodUp, axis, LeftRight, LeftUp, LeftForward);
                Vector3 fingers = Quaternion.AngleAxis(LeftRoll, axis) * Vector3.ProjectOnPlane(t.right - t.up * 0.3f, axis);
                Grasp(player, "Left", target, -1f, fingers, axis, 0.03f);
                FishingBoatOars.BlendPose(player, a.IdleW);
            }
            finally { FishingBoatOars.EndPose(player); }
        }

        /// <summary>
        /// A hand closed round something at a point: the arm reaches so the palm (not the wrist) lands there, and the
        /// hand turns so its fingers point along <paramref name="fingers"/> and its thumb toward <paramref name="thumb"/>.
        /// Returns where the palm ended up.
        /// </summary>
        private static Vector3 Grasp(Player player, string side, Vector3 palmAt, float sign, Vector3 fingers, Vector3 thumb, float thickness)
        {
            var hand = FishingBoatOars.Bone(player, side + "Hand");
            if (hand == null) { Arm(player, side, palmAt, sign); return palmAt; }
            Arm(player, side, palmAt, sign);
            Vector3 palm = Orient(player, side, hand, fingers, thumb);
            // The palm's skin goes against what's held, not its middle: the hand sits back from it, away from the way the
            // palm faces, by the palm's thickness plus the grip's radius.
            Vector3 facing = PalmFacing(player, side, hand, sign);
            Arm(player, side, palmAt - facing * thickness - (palm - hand.position), sign);   // again, with the palm where it should be
            palm = Orient(player, side, hand, fingers, thumb);
            // and the fingers closed round it
            var middle = FishingBoatOars.Bone(player, side + "HandMiddle1");
            if (middle != null && facing != Vector3.zero)
                FishingBoatOars.CurlFingers(player, side, Vector3.Cross((middle.position - hand.position).normalized, PalmFacing(player, side, hand, sign)));
            return palm;
        }

        /// <summary>
        /// The way a hand's palm faces: across the hand from its fingers and thumb (the two hands mirror each other, so
        /// <paramref name="sign"/>: right +1, left -1). Zero if the hand's bones aren't there.
        /// </summary>
        private static Vector3 PalmFacing(Player player, string side, Transform hand, float sign)
        {
            var middle = FishingBoatOars.Bone(player, side + "HandMiddle1");
            var thumb = FishingBoatOars.Bone(player, side + "HandThumb1");
            if (middle == null || thumb == null) return Vector3.zero;
            Vector3 n = Vector3.Cross(middle.position - hand.position, thumb.position - hand.position) * sign;
            return n.sqrMagnitude > 1e-10f ? n.normalized : Vector3.zero;
        }

        /// <summary>Turns a hand to point its fingers and thumb; returns the middle of its palm.</summary>
        private static Vector3 Orient(Player player, string side, Transform hand, Vector3 fingers, Vector3 thumb)
        {
            var middle = FishingBoatOars.Bone(player, side + "HandMiddle1");
            var thumbBone = FishingBoatOars.Bone(player, side + "HandThumb1");
            if (middle == null || fingers.sqrMagnitude < 1e-6f) return hand.position;
            fingers.Normalize();
            Vector3 have = middle.position - hand.position;
            if (have.sqrMagnitude > 1e-8f) hand.rotation = Quaternion.FromToRotation(have, fingers) * hand.rotation;
            if (thumbBone != null)
            {
                Vector3 th = Vector3.ProjectOnPlane(thumbBone.position - hand.position, fingers);
                Vector3 want = Vector3.ProjectOnPlane(thumb, fingers);
                if (th.sqrMagnitude > 1e-8f && want.sqrMagnitude > 1e-8f)
                    hand.rotation = Quaternion.AngleAxis(Vector3.SignedAngle(th, want, fingers), fingers) * hand.rotation;
            }
            return hand.position + (middle.position - hand.position) * 0.6f;
        }


        /// <summary>
        /// A hand nudge (right, up, forward, metres) given as seen with the rod at its usual holding angle, turned to sit the
        /// same way against the rod at whatever angle it's at now - so a hand set on the rod stays on it when the rod moves.
        /// </summary>
        private static Vector3 RodNudge(Vector3 rodRight, Vector3 rodUp, Vector3 along, float right, float up, float forward)
        {
            const float refElev = 30f * Mathf.Deg2Rad;
            float c = Mathf.Cos(refElev), sn = Mathf.Sin(refElev);
            float onUp = up * c - forward * sn, onAlong = up * sn + forward * c;
            return rodRight * right + rodUp * onUp + along * onAlong;
        }

        /// <summary>How far past <paramref name="limit"/> of its length an arm would have to reach to get its palm to a point (0 if it needn't).</summary>
        private static float Overreach(Player player, string side, Vector3 target, float limit = 0.85f)
        {
            var upper = FishingBoatOars.Bone(player, side + "Arm");
            var lower = FishingBoatOars.Bone(player, side + "ForeArm");
            var hand = FishingBoatOars.Bone(player, side + "Hand");
            if (upper == null || lower == null || hand == null) return 0f;
            float length = (lower.position - upper.position).magnitude + (hand.position - lower.position).magnitude + 0.07f;   // + to the palm
            return Mathf.Max(0f, (target - upper.position).magnitude - length * limit);
        }
        /// <summary>One arm's hand to a point, the elbow down and out to its side.</summary>
        private static void Arm(Player player, string side, Vector3 target, float sign)
        {
            var upper = FishingBoatOars.Bone(player, side + "Arm");
            var lower = FishingBoatOars.Bone(player, side + "ForeArm");
            var hand = FishingBoatOars.Bone(player, side + "Hand");
            if (upper == null || lower == null || hand == null) return;
            var t = player.transform;
            // the elbow out to its own side and a little down - never in toward the body
            Vector3 pole = upper.position + t.right * (sign * 0.5f) - t.up * 0.3f + t.forward * 0.05f;
            FishingBoatOars.SolveArm(upper, lower, hand, target, pole);
        }
    }
}
