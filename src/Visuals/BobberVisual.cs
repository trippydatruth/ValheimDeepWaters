using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Client-side bobber and line. Deliberately has no collider, Rigidbody, ZNetView, ZSyncTransform, ItemDrop
    /// or Floating component - spawning vanilla's physical bait caused ZSyncTransform/Floating/AutoPickup errors.
    /// </summary>
    internal sealed class BobberVisual : MonoBehaviour
    {
        private const int RopePoints = 10;
        private const float NibbleDuration = 0.45f;

        private const float Submerged = 0.55f; // fraction of the bobber's height that floats below the surface (keel and lower body)

        private LineRenderer _line = null!;
        private Transform _ball = null!;
        private Vector3 _lineAttachLocal;     // top of the bobber, in its own local space
        private float _waterlineOffset;      // height of the waterline above the bobber's origin

        public Vector3 Position;
        public bool Dipped;
        public bool Thrashing;
        /// <summary>
        /// Fishing a lure: there's no float. It's still worked out (where the line meets the water) but not shown; the
        /// line runs into the water a little under the surface, and a nibble twitches it and taps the rod tip.
        /// </summary>
        public bool Hidden { get; private set; }
        private const float LureLineDepth = 0.12f;

        private Vector3 _castFrom;
        private Vector3 _castTo;
        private float _castStart;
        private float _castDuration;

        private float _nibbleTime = -100f;
        private float _nibbleDepth;

        /// <summary>How slack the line is, 0 (tight) .. 0.3 (loose): the line sags by this much of half its length, as vanilla's does.</summary>
        public float Slack;
        private float _arcHeight = 1.1f;

        /// <summary>
        /// Throws the float from the rod tip along a real throw's arc to where it lands: steady across the ground, up and
        /// down under gravity, higher and longer in the air the further it goes. (duration below 0: worked out from the
        /// distance, like a float thrown at a fixed angle.)
        /// </summary>
        public void BeginCastTravel(Vector3 from, Vector3 to, float duration = -1f)
        {
            _castFrom = from;
            _castTo = to;
            _castStart = Time.time;
            float dist = Vector3.Distance(new Vector3(from.x, 0f, from.z), new Vector3(to.x, 0f, to.z));
            _castDuration = duration > 0f ? duration : Mathf.Clamp(Mathf.Sqrt(dist / 9.81f) * 1.15f, 0.45f, 2.2f);
            _arcHeight = Mathf.Clamp(dist * 0.22f, 0.6f, 7f);
        }

        private bool Travelling => Time.time - _castStart < _castDuration;
        private bool _landed; // splash once when the cast hits the water

        /// <summary>A quick tug under and back up, like vanilla's nibble force on the float.</summary>
        public void Nibble(float depth)
        {
            _nibbleTime = Time.time;
            _nibbleDepth = depth;
            if (Hidden) RodMotion.Tap(Mathf.Clamp01(depth / 0.12f));
        }

        public static BobberVisual Create(Vector3 startPosition, bool hidden = false)
        {
            var go = new GameObject("VDW_Bobber");
            var bobber = go.AddComponent<BobberVisual>();
            bobber.Position = startPosition;

            var shader = Shader.Find("Sprites/Default");

            GameObject ballGo;
            if (CustomModels.TryGetCustom("bobber", out var bobberMesh, out var bobberMat))
            {
                // Size is already baked into the custom mesh.
                ballGo = new GameObject("bobber_custom");
                ballGo.AddComponent<MeshFilter>().sharedMesh = bobberMesh;
                ballGo.AddComponent<MeshRenderer>().sharedMaterial = bobberMat;
            }
            else
            {
                ballGo = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                DestroyImmediate(ballGo.GetComponent<Collider>());
                ballGo.transform.localScale = Vector3.one * 0.16f;
                if (shader != null)
                    ballGo.GetComponent<Renderer>().material = new Material(shader) { color = new Color(0.9f, 0.15f, 0.1f) };
            }
            ballGo.transform.SetParent(go.transform, false);
            bobber._ball = ballGo.transform;

            // The line ties onto the top of the bobber, and it floats partly submerged. Both come from the
            // mesh bounds, so any model works regardless of where its origin sits. (go is at the world origin
            // here, so the renderer's world bounds are relative to the bobber's origin.)
            var meshBounds = ballGo.GetComponent<MeshFilter>().sharedMesh.bounds;
            bobber._lineAttachLocal = new Vector3(meshBounds.center.x, meshBounds.max.y, meshBounds.center.z);
            var worldBounds = ballGo.GetComponent<Renderer>().bounds;
            bobber._waterlineOffset = worldBounds.min.y + worldBounds.size.y * Submerged;

            var line = go.AddComponent<LineRenderer>();
            line.positionCount = RopePoints;
            line.useWorldSpace = true;
            FindVanillaLine();
            if (_vanillaLineMat != null)
            {
                line.sharedMaterial = _vanillaLineMat;                    // vanilla's own fishing line
                if (_vanillaLineCurve != null) line.widthCurve = _vanillaLineCurve;
                bobber._baseWidth = _vanillaLineWidth;                   // scaled to a real line's thickness
                line.textureMode = _vanillaTextureMode;
            }
            else
            {
                line.startWidth = 0.02f; line.endWidth = 0.012f; bobber._baseWidth = 1f;
                if (shader != null) line.material = new Material(shader) { color = new Color(0.85f, 0.85f, 0.85f) };
            }
            bobber._line = line;
            if (hidden)
            {
                bobber.Hidden = true;
                foreach (var r in ballGo.GetComponentsInChildren<Renderer>()) r.enabled = false;
            }

            return bobber;
        }

        private void Update()
        {
            if (Player.m_localPlayer == null) Destroy(gameObject);
        }

        /// <summary>Called from Plugin.LateUpdate, after the rod has been animated for this frame.</summary>
        public void Refresh(Player p)
        {
            if (!RodMotion.TryGetTip(out var tip))
            {
                Vector3 eye = p.m_eye != null ? p.m_eye.position : p.transform.position + Vector3.up * 1.6f;
                tip = eye + p.transform.forward * 0.6f + Vector3.down * 0.35f;
            }

            bool travelling = Travelling;
            float now = Time.time;

            if (travelling)
            {
                float t = Mathf.Clamp01((now - _castStart) / _castDuration);
                Vector3 arc = Vector3.Lerp(_castFrom, _castTo, t);           // steady across the ground
                arc.y += 4f * _arcHeight * t * (1f - t);                       // a gravity parabola on top
                _ball.SetPositionAndRotation(arc, Quaternion.identity);
            }
            else
            {
                if (!_landed)
                {
                    _landed = true;
                    FishingFx.Landed(Position);
                }

                // Ride the real wave surface where there is one.
                float surface = Floating.GetLiquidLevel(Position);
                if (surface < Position.y - 50f) surface = Position.y;

                // Plunges under on landing, then springs back up with a damped wobble.
                float sinceLanding = now - (_castStart + _castDuration);
                float settle = Mathf.Exp(-sinceLanding * 3.2f);
                float splash = -0.18f * settle * Mathf.Cos(sinceLanding * 11f);

                // Gentle idle bob from two out-of-step waves, so it never looks like a metronome.
                float bob = Mathf.Sin(now * 2.1f) * 0.025f + Mathf.Sin(now * 3.7f + 1.3f) * 0.012f + splash;
                if (Dipped) bob -= 0.22f;
                if (Thrashing) bob += Mathf.Sin(now * 25f) * 0.06f;
                float nt = (now - _nibbleTime) / NibbleDuration;
                if (nt >= 0f && nt < 1f) bob -= _nibbleDepth * Mathf.Sin(nt * Mathf.PI) * (1f - nt * 0.4f);

                // Rocks with the water, wobbles hard when it lands and while a fish thrashes.
                float tiltX = Mathf.Sin(now * 1.7f) * 6f + settle * Mathf.Sin(sinceLanding * 9f) * 25f;
                float tiltZ = Mathf.Cos(now * 1.3f) * 5f;
                if (Thrashing) tiltX += Mathf.Sin(now * 23f) * 14f;

                var floatPos = new Vector3(Position.x, surface + bob - _waterlineOffset, Position.z);
                if (Hidden) floatPos.y -= LureLineDepth;   // the line goes into the water where the lure is
                _ball.SetPositionAndRotation(floatPos,Quaternion.Euler(tiltX, 0f, tiltZ));
            }

            UpdateLine(tip, _ball.TransformPoint(_lineAttachLocal), travelling);
        }

        /// <summary>
        /// Draws the line the way vanilla's fishing line hangs: a curve from the rod tip to the float that sags by Slack
        /// times half its length (none when tight, loose and drooping when you've walked toward the float), thinner the
        /// further away it reaches. A thrashing fish makes it quiver; otherwise it hangs still.
        /// </summary>
        private void UpdateLine(Vector3 a, Vector3 b, bool straight)
        {
            float dist = Vector3.Distance(a, b);
            float sag = (straight ? 0.02f : Slack) * dist * 0.5f;
            float t = Time.time;
            for (int i = 0; i < RopePoints; i++)
            {
                float f = (float)i / (RopePoints - 1);
                float k = Mathf.Abs(0.5f - f) * 2f; k = 1f - k * k;           // vanilla's shape: 0 at the ends, 1 mid-line
                Vector3 pos = Vector3.Lerp(a, b, f) + Vector3.down * sag * k;
                if (Thrashing) pos += new Vector3(Mathf.Sin(t * 21f + i * 1.3f), Mathf.Sin(t * 26f + i * 0.9f), 0f) * (0.02f * k);
                _line.SetPosition(i, pos);
            }
            // thinner with distance, as vanilla's line (LineConnect: 6..30 m, 0.8..0.2 of its width)
            float far = Mathf.Pow(Mathf.Clamp01(Mathf.InverseLerp(6f, 30f, dist)), 0.2f);
            _line.widthMultiplier = _baseWidth * Mathf.Lerp(0.8f, 0.2f, far);
        }

        private float _baseWidth = 1f;
        private static Material? _vanillaLineMat;
        private static float _vanillaLineWidth = 1f;
        private static LineTextureMode _vanillaTextureMode = LineTextureMode.Tile;
        private const float LineThickness = 0.028f;   // metres, close up (thinner further out)
        private static AnimationCurve? _vanillaLineCurve;
        private static bool _lookedForLine;

        /// <summary>Vanilla's fishing line look (material and width), from the float the vanilla rod casts.</summary>
        private static void FindVanillaLine()
        {
            if (_lookedForLine || ObjectDB.instance == null) return;
            _lookedForLine = true;
            var proj = ObjectDB.instance.GetItemPrefab("FishingRod")?.GetComponent<ItemDrop>()?.m_itemData.m_shared.m_attack.m_attackProjectile;
            var lr = proj != null ? proj.GetComponentsInChildren<LineRenderer>(true).FirstOrDefault() : null;
            if (lr == null) return;
            _vanillaLineMat = lr.sharedMaterial;
            _vanillaLineCurve = lr.widthCurve;
            _vanillaTextureMode = lr.textureMode;
            // vanilla's curve is sized for its own float; scale it so the line is about 1.5 cm across up close
            float peak = 0f;
            foreach (var key in lr.widthCurve.keys) peak = Mathf.Max(peak, key.value);
            _vanillaLineWidth = peak > 0f ? LineThickness / peak : 1f;
        }
    }
}
