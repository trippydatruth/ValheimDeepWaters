using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>What an angler is doing, as far as their body and rod show it. Built from the session for the local
    /// player, and read from their player data for everyone else.</summary>
    internal struct AnglerState
    {
        public bool RodOut;
        public int Phase;              // 0 no line out, 1 waiting, 2 bite, 3 fighting
        public bool Reeling, Pulling, Running, Lure, Charging;
        public float Charge;           // 0..1 while charging a cast
        public float Load;             // 0..1 line tension against the breaking point
        public float Angle;            // degrees the line has been pulled off to the side
        public bool HasTarget;
        public Vector3 Target;         // where the line goes into the water
    }

    /// <summary>What happens at the end of an angler's line that others see and hear too.</summary>
    /// (Hump, Rear, TailSlap, Crash: a sea serpent boss's moves; the arg is its height / size.)
    internal enum FishFx { None, Bite, Nibble, HookSet, Splash, Leap, Snap, Landing, Hump, Rear, TailSlap, Crash }

    /// <summary>
    /// Shares each angler's state through their player ZDO so every client can pose them: a bit field, a few floats
    /// (sent at most ten times a second, and only when they change), and a counter for one-off moments (cast, hook set,
    /// twitch, nibble, line snap, landing) so those play everywhere too.
    /// </summary>
    internal static class AnglerSync
    {
        private static readonly int KeyBits = "vdw_ang".GetStableHashCode();
        private static readonly int KeyLoad = "vdw_ang_load".GetStableHashCode();
        private static readonly int KeyCharge = "vdw_ang_charge".GetStableHashCode();
        private static readonly int KeyAngle = "vdw_ang_angle".GetStableHashCode();
        private static readonly int KeyTarget = "vdw_ang_target".GetStableHashCode();
        private static readonly int KeyEvent = "vdw_ang_event".GetStableHashCode();

        private static float _nextSend;
        private static int _sentBits = -1, _eventCount;
        private static float _sentLoad = -1f, _sentCharge = -1f, _sentAngle = 999f;
        private static Vector3 _sentTarget;
        private static readonly Dictionary<int, int> SeenEvent = new();

        private static ZDO? Zdo(Player p)
        {
            var nview = p.GetComponent<ZNetView>();
            return nview != null && nview.IsValid() ? nview.GetZDO() : null;
        }

        private static int Bits(in AnglerState s) =>
            (s.RodOut ? 1 : 0) | (s.Reeling ? 2 : 0) | (s.Pulling ? 4 : 0) | (s.Running ? 8 : 0) | (s.Lure ? 16 : 0) |
            (s.Charging ? 32 : 0) | (s.HasTarget ? 64 : 0) | (s.Phase << 8);

        /// <summary>The local angler: written when it changes (the bits at once, the rest at most ten times a second).</summary>
        public static void Write(Player p, in AnglerState s)
        {
            var zdo = Zdo(p);
            if (zdo == null || !zdo.IsOwner()) return;
            int bits = Bits(s);
            if (bits != _sentBits) { zdo.Set(KeyBits, bits); _sentBits = bits; }
            if (Time.time < _nextSend) return;
            _nextSend = Time.time + 0.1f;
            float load = Mathf.Round(s.Load * 20f) / 20f, charge = Mathf.Round(s.Charge * 20f) / 20f, angle = Mathf.Round(s.Angle);
            if (load != _sentLoad) { zdo.Set(KeyLoad, load); _sentLoad = load; }
            if (charge != _sentCharge) { zdo.Set(KeyCharge, charge); _sentCharge = charge; }
            if (angle != _sentAngle) { zdo.Set(KeyAngle, angle); _sentAngle = angle; }
            if (s.HasTarget && (s.Target - _sentTarget).sqrMagnitude > 0.04f) { zdo.Set(KeyTarget, s.Target); _sentTarget = s.Target; }
        }

        /// <summary>A one-off moment on the local angler, for everyone else to play.</summary>
        public static void Event(Player p, RodEvent e)
        {
            var zdo = Zdo(p);
            if (zdo == null || !zdo.IsOwner()) return;
            _eventCount = (_eventCount + 1) & 0x0FFFFFFF;
            zdo.Set(KeyEvent, (_eventCount << 4) | ((int)e & 15));
        }

        // ------------------------------------------------------------------ what others see of the line (roadmap #29)

        private static readonly int KeyFx = "vdw_ang_fx".GetStableHashCode();
        private static readonly int KeyFxArg = "vdw_ang_fxarg".GetStableHashCode();
        private static readonly int KeyFloat = "vdw_ang_float".GetStableHashCode();
        private static readonly int KeyFish = "vdw_ang_fish".GetStableHashCode();
        private static readonly int KeyFishScale = "vdw_ang_fscale".GetStableHashCode();
        private static int _fxCount;
        private static string _sentFloat = "", _sentFish = "";
        private static float _sentScale = -1f;
        private static readonly Dictionary<int, int> SeenFx = new();

        /// <summary>A splash, bite or leap at the local angler's line, for everyone else to see and hear (arg: its size).</summary>
        public static void Fx(Player? p, FishFx kind, float arg = 0f)
        {
            if (p == null) return;
            var zdo = Zdo(p);
            if (zdo == null || !zdo.IsOwner()) return;
            _fxCount = (_fxCount + 1) & 0x0FFFFFFF;
            zdo.Set(KeyFxArg, arg);
            zdo.Set(KeyFx, (_fxCount << 4) | ((int)kind & 15));
        }

        /// <summary>What the local angler's line shows: the float buff on it (its id), and the fish on the hook (id, size).</summary>
        public static void SetLook(Player p, string floatId, string fishId, float fishScale)
        {
            var zdo = Zdo(p);
            if (zdo == null || !zdo.IsOwner()) return;
            if (floatId != _sentFloat) { zdo.Set(KeyFloat, floatId); _sentFloat = floatId; }
            if (fishId != _sentFish) { zdo.Set(KeyFish, fishId); _sentFish = fishId; }
            if (Mathf.Abs(fishScale - _sentScale) > 0.01f) { zdo.Set(KeyFishScale, fishScale); _sentScale = fishScale; }
        }

        public static (string floatId, string fishId, float fishScale) ReadLook(Player p)
        {
            var zdo = Zdo(p);
            if (zdo == null) return ("", "", 1f);
            return (zdo.GetString(KeyFloat), zdo.GetString(KeyFish), zdo.GetFloat(KeyFishScale, 1f));
        }

        /// <summary>Another angler's newest splash / bite / leap since this was last read (None if nothing new).</summary>
        public static FishFx ReadFx(Player p, out float arg)
        {
            arg = 0f;
            var zdo = Zdo(p);
            if (zdo == null) return FishFx.None;
            int fx = zdo.GetInt(KeyFx);
            int id = p.GetInstanceID();
            if (!SeenFx.TryGetValue(id, out int seen)) { SeenFx[id] = fx; return FishFx.None; }
            if (fx == seen) return FishFx.None;
            SeenFx[id] = fx;
            arg = zdo.GetFloat(KeyFxArg);
            return (FishFx)(fx & 15);
        }

        /// <summary>Another angler's state, and any moment they've had since this was last read.</summary>
        public static AnglerState Read(Player p, out RodEvent fresh)
        {
            fresh = RodEvent.None;
            var s = new AnglerState();
            var zdo = Zdo(p);
            if (zdo == null) return s;
            int bits = zdo.GetInt(KeyBits);
            s.RodOut = (bits & 1) != 0; s.Reeling = (bits & 2) != 0; s.Pulling = (bits & 4) != 0; s.Running = (bits & 8) != 0;
            s.Lure = (bits & 16) != 0; s.Charging = (bits & 32) != 0; s.HasTarget = (bits & 64) != 0; s.Phase = (bits >> 8) & 3;
            s.Load = zdo.GetFloat(KeyLoad); s.Charge = zdo.GetFloat(KeyCharge); s.Angle = zdo.GetFloat(KeyAngle);
            s.Target = zdo.GetVec3(KeyTarget, p.transform.position + p.transform.forward * 10f);

            int ev = zdo.GetInt(KeyEvent);
            int id = p.GetInstanceID();
            if (!SeenEvent.TryGetValue(id, out int seen)) SeenEvent[id] = ev;      // first look: don't replay an old one
            else if (ev != seen) { SeenEvent[id] = ev; fresh = (RodEvent)(ev & 15); }
            return s;
        }
    }
}
