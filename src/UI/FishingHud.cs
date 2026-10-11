using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The fishing HUD and catch log, drawn with IMGUI in a Valheim style: dark wood panels with gold trim,
    /// Valheim's own font, and key-prompt chips. Scales with screen height like Valheim's UI (times HUD Scale);
    /// positions near Valheim's own elements (minimap, stamina bar) are given in Valheim's 1080p units.
    /// </summary>
    internal static class FishingHud
    {
        private const float RefHeight = 1080f;

        // Palette taken from Valheim's UI: cream text, orange-gold headers, brass trim on dark wood.
        private static readonly Color Cream = new Color(1f, 0.93f, 0.80f);
        private static readonly Color Gold = new Color(1f, 0.76f, 0.35f);
        private static readonly Color Dim = new Color(0.74f, 0.68f, 0.58f);
        private static readonly Color Amber = new Color(0.98f, 0.66f, 0.16f);
        private static readonly Color Ember = new Color(0.90f, 0.26f, 0.12f);
        private static readonly Color Moss = new Color(0.50f, 0.70f, 0.28f);
        private static readonly Color Wood = new Color(0.10f, 0.08f, 0.055f, 0.88f);
        private static readonly Color WoodLight = new Color(0.24f, 0.18f, 0.11f, 0.95f);
        private static readonly Color Trim = new Color(0.74f, 0.56f, 0.28f, 1f);
        private static readonly Color Well = new Color(0f, 0f, 0f, 0.55f);

        private static Texture2D? _white, _panelTex, _chipTex, _discTex, _pipTex;
        private static GUIStyle _panel = null!, _chip = null!, _big = null!, _text = null!, _small = null!, _smallBold = null!, _hint = null!;
        private static bool _stylesReady, _fontApplied;
        private static float _width, _height; // virtual screen size
        private static float _vu;             // one Valheim 1080p UI unit, in virtual units

        public static void Draw()
        {
            if (!VdwConfig.Enabled.Value) return;
            var player = Player.m_localPlayer;
            if (player == null) return;

            bool showHud = VdwConfig.ShowHud.Value && FishingController.RodEquippedNow
                           && !InventoryGui.IsVisible() && !Menu.IsVisible() && !Hud.IsUserHidden();
            bool showLog = FishingController.LogOpen;
            if (!showHud && !showLog) return;

            EnsureStyles();

            float hudScale = Mathf.Clamp(VdwConfig.HudScale.Value, 0.4f, 2f);
            float scale = Screen.height / RefHeight * hudScale;
            _width = Screen.width / scale;
            _height = Screen.height / scale;
            _vu = 1f / hudScale;
            var oldMatrix = GUI.matrix;
            var oldColor = GUI.color;
            GUI.matrix = Matrix4x4.Scale(new Vector3(scale, scale, 1f));
            try
            {
                if (showHud) DrawHud(player);
                if (showLog) DrawLog(player);
            }
            finally
            {
                GUI.matrix = oldMatrix;
                GUI.color = oldColor;
            }
        }

        // ------------------------------------------------------------------
        // HUD
        // ------------------------------------------------------------------

        private static void DrawHud(Player player)
        {
            float right = _width - 24f;
            var s = FishingController.Session;

            float baitTop = 268f * _vu; // just below Valheim's minimap
            DrawBaitPanel(player, right, baitTop);

            float y = baitTop + 92f;
            if (s != null && s.Phase == FishingPhase.Fighting)
            {
                DrawTension(s, right, y);
                y += 346f;   // the line-out panel then still ends just above the drag gauge
            }
            if (s != null) DrawLineOut(s, right, y);

            DrawDials(right - 94f, _height - 160f, FishingController.DragLevel, FishingController.ReelSpeedLevel);
            DrawHint(s);
            if (s != null && FishingController.BossFightNow) DrawBossBar(s);
        }

        /// <summary>
        /// A boss fish's bar across the top: its name and title over its stamina, with marks where it enrages and
        /// turns desperate. Empty means it's beaten - then it only has to be reeled in.
        /// </summary>
        private static void DrawBossBar(FishingSession s)
        {
            const float w = 640f, h = 80f;
            var r = new Rect(_width / 2f - w / 2f, 70f * _vu, w, h);
            Panel(r);

            float frac = s.FishStaminaMax > 0f ? Mathf.Clamp01(s.FishStamina / s.FishStaminaMax) : 0f;
            Label(new Rect(r.x, r.y + 6f, w, 30f), s.Fish.Name.ToUpperInvariant(), _big, Gold, TextAnchor.MiddleCenter);
            Label(new Rect(r.x, r.y + 34f, w, 18f), frac <= 0f ? "Exhausted - reel it in!" : s.Boss!.Title, _small, frac <= 0f ? Moss : Dim, TextAnchor.MiddleCenter);

            var bar = new Rect(r.x + 24f, r.y + 58f, w - 48f, 12f);
            Fill(bar, Well);
            Color c = new Color(0.72f, 0.14f, 0.09f);
            if (s.FightPhase == 1) c = Ember;
            if (s.FightPhase == 2) c = Color.Lerp(Ember, Amber, 0.5f + 0.5f * Mathf.Sin(Time.time * 7f));
            Fill(new Rect(bar.x, bar.y, bar.width * frac, bar.height), c);
            foreach (float mark in new[] { 0.66f, 0.33f })
                Fill(new Rect(bar.x + bar.width * mark - 1f, bar.y - 3f, 2f, bar.height + 6f), Trim);
        }

        private static void DrawBaitPanel(Player player, float right, float top)
        {
            const float w = 320f, h = 80f;
            var r = new Rect(right - w, top, w, h);
            Panel(r);

            // Row 1: bait.
            // With a lure on, row 1 is its trailer (optional) and row 2 the lure itself.
            var lure = Tackle.LureOn(player);
            var bait = FishingController.ActiveBait(player);
            var line1 = new Rect(r.x + 14f, r.y + 8f, w - 28f, 30f);
            if (lure != null)
                Label(line1, bait != null ? Loc.Text(bait.Name) : lure.AcceptsTrailer ? "No trailer" : "No bait needed", _big, bait == null ? Dim : Gold, TextAnchor.MiddleLeft);
            else
                Label(line1, bait != null ? Loc.Text(bait.Name) : "No bait", _big, bait == null ? Dim : Gold, TextAnchor.MiddleLeft);
            KeyPrompts(new[] { (VdwConfig.CycleBaitKey.Value.ToString(), bait != null ? "x" + bait.Count : "-") }, line1.xMax, line1.y + 3f, alignRight: true);

            // Row 2: hook, with the fish weights it suits.
            var hook = FishingController.GetActiveHook(player);
            var line2 = new Rect(r.x + 14f, r.y + 44f, w - 28f, 24f);
            string hookText = "No hook";
            if (lure != null)
                hookText = lure.LureMaxKg > 0f ? $"{Loc.Text(hook!.Name)}  ·  {lure.LureMinKg:0.#}–{lure.LureMaxKg:0.#} kg" : $"{Loc.Text(hook!.Name)}  ·  lure";
            else if (hook != null && ContentRegistry.HookByItemName.TryGetValue(hook.Name, out var def))
                hookText = $"{Loc.Text(hook.Name)}  ·  {def.MinKg:0.#}–{def.MaxKg:0.#} kg";
            Label(line2, hookText, _text, hook == null ? Ember : Cream, TextAnchor.MiddleLeft);
            KeyPrompts(new[] { (VdwConfig.CycleHookKey.Value.ToString(), hook != null ? "x" + hook.Count : "-") }, line2.xMax, line2.y, alignRight: true);
        }

        private static void DrawTension(FishingSession s, float right, float top)
        {
            const float w = 100f, h = 334f;
            var r = new Rect(right - w, top, w, h);
            Panel(r);
            Label(new Rect(r.x, r.y + 8f, w, 22f), "TENSION", _smallBold, Gold, TextAnchor.MiddleCenter);

            float breakAt = Mathf.Max(1f, s.Rod.BreakTension);
            float fill = Mathf.Clamp01(s.Tension / FishingController.MaxTension);
            float danger = Mathf.Clamp01(s.Tension / breakAt);

            var bar = new Rect(r.center.x - 16f, r.y + 38f, 32f, 250f);
            Fill(bar, Well);

            Color c = danger < 0.6f ? Color.Lerp(Moss, Amber, danger / 0.6f) : Color.Lerp(Amber, Ember, (danger - 0.6f) / 0.4f);
            if (danger > 0.85f) c.a = 0.65f + 0.35f * Mathf.Abs(Mathf.Sin(Time.time * 9f)); // pulse near snapping
            float fh = bar.height * fill;
            Fill(new Rect(bar.x, bar.yMax - fh, bar.width, fh), c);

            // Snap line.
            float snapY = bar.yMax - bar.height * Mathf.Clamp01(breakAt / FishingController.MaxTension);
            Fill(new Rect(bar.x - 6f, snapY - 1f, bar.width + 12f, 2f), Ember);

            Label(new Rect(r.x, bar.yMax + 6f, w, 30f), $"{s.Tension:0}", _big, danger > 0.85f ? Ember : Cream, TextAnchor.MiddleCenter);
        }

        private static void DrawLineOut(FishingSession s, float right, float top)
        {
            var rodItem = s.RodItem;
            bool showRod = rodItem != null && rodItem.m_shared.m_useDurability;
            const float w = 230f;
            float h = showRod ? 112f : 74f;
            var r = new Rect(right - w, top, w, h);
            Panel(r);

            if (showRod)
            {
                float cond = Mathf.Clamp01(rodItem!.m_durability / Mathf.Max(1f, rodItem.GetMaxDurability()));
                var rodRow = new Rect(r.x + 14f, r.y + 66f, w - 28f, 22f);
                Label(rodRow, "ROD", _smallBold, Gold, TextAnchor.MiddleLeft);
                Label(rodRow, $"{cond * 100f:0}%", _text, cond < 0.2f ? Ember : Cream, TextAnchor.MiddleRight);
                var rodBar = new Rect(r.x + 14f, r.y + 92f, w - 28f, 8f);
                Fill(rodBar, Well);
                Fill(new Rect(rodBar.x, rodBar.y, rodBar.width * cond, rodBar.height), Color.Lerp(Ember, Moss, Mathf.InverseLerp(0.2f, 0.7f, cond)));
            }

            var head = new Rect(r.x + 14f, r.y + 8f, w - 28f, 28f);
            Label(head, "LINE OUT", _smallBold, Gold, TextAnchor.MiddleLeft);
            Label(head, $"{s.LineDistance:0} / {s.MaxLine:0} m", _big, Cream, TextAnchor.MiddleRight);

            float frac = s.MaxLine > 0f ? Mathf.Clamp01(s.LineDistance / s.MaxLine) : 0f;
            var bar = new Rect(r.x + 14f, r.y + 46f, w - 28f, 10f);
            Fill(bar, Well);
            Fill(new Rect(bar.x, bar.y, bar.width * frac, bar.height), Color.Lerp(Amber, Ember, Mathf.InverseLerp(0.6f, 1f, frac)));
        }

        /// <summary>
        /// Two round brass-rimmed gauges, one behind the other: the drag in front (12 amber pips) and the reel speed on
        /// the bigger one behind it (10 green pips round the rim, one per step). Lit pips show the setting; the exact
        /// value is shown in the middle of the screen as it changes.
        /// </summary>
        private static void DrawDials(float cx, float cy, float drag01, float reel01)
        {
            const float outer = 92f, reelRing = 79f, reelPip = 10f;
            GUI.color = Color.white;
            GUI.DrawTexture(new Rect(cx - outer, cy - outer, outer * 2f, outer * 2f), _discTex);
            int reelLit = Mathf.RoundToInt(Mathf.Clamp01(reel01) * 10f);
            for (int i = 0; i < 10; i++)
            {
                // round the top three quarters, leaving the bottom for the label
                float a = Mathf.Lerp(-135f, 135f, i / 9f) * Mathf.Deg2Rad;
                var p = new Vector2(cx + Mathf.Sin(a) * reelRing, cy - Mathf.Cos(a) * reelRing);
                GUI.color = i < reelLit ? Moss : new Color(0.35f, 0.30f, 0.24f, 0.9f);
                GUI.DrawTexture(new Rect(p.x - reelPip / 2f, p.y - reelPip / 2f, reelPip, reelPip), _pipTex);
            }
            GUI.color = Color.white;
            Label(new Rect(cx - outer, cy + reelRing - 12f, outer * 2f, 22f), "REEL", _smallBold, Gold, TextAnchor.MiddleCenter);

            const float radius = 60f, pipRing = 46f, pip = 11f;
            const int pips = 12;
            GUI.DrawTexture(new Rect(cx - radius, cy - radius, radius * 2f, radius * 2f), _discTex);
            int lit = Mathf.RoundToInt(Mathf.Clamp01(drag01) * pips);
            for (int i = 0; i < pips; i++)
            {
                float a = (i / (float)pips) * Mathf.PI * 2f; // clockwise from 12 o'clock
                var p = new Vector2(cx + Mathf.Sin(a) * pipRing, cy - Mathf.Cos(a) * pipRing);
                GUI.color = i < lit ? Amber : new Color(0.35f, 0.30f, 0.24f, 0.9f);
                GUI.DrawTexture(new Rect(p.x - pip / 2f, p.y - pip / 2f, pip, pip), _pipTex);
            }
            GUI.color = Color.white;
            Label(new Rect(cx - radius, cy - 11f, radius * 2f, 22f), "DRAG", _smallBold, Gold, TextAnchor.MiddleCenter);
        }

        /// <summary>One-line hint plus key prompts, in a small panel under Valheim's stamina bar.</summary>
        private static void DrawHint(FishingSession? s)
        {
            string bait = VdwConfig.CycleBaitKey.Value.ToString();
            string drag = FishingController.ControlLabel(VdwConfig.DragControl.Value);
            string speed = FishingController.ControlLabel(VdwConfig.ReelSpeedControl.Value);
            string text;
            Color color = Cream;
            (string key, string label)[] keys;

            if (s == null)
            {
                text = "Hold to charge, release to cast";
                keys = new[] { ("LMB", "Cast"), (bait, "Bait"), (VdwConfig.CycleHookKey.Value.ToString(), "Hook"), (drag, "Drag") };
            }
            else switch (s.Phase)
            {
                case FishingPhase.Bite:
                    text = "FISH ON!";
                    color = Color.Lerp(Amber, Ember, Mathf.PingPong(Time.time * 4f, 1f));
                    keys = new[] { ("RMB", "Set the hook") };
                    break;
                case FishingPhase.Fighting:
                    text = s.Running ? "The fish is running!" : "Reel it in";
                    if (s.Running) color = Amber;
                    keys = new[] { ("Hold RMB", "Reel"), ("Shift", "Full speed"), (speed, "Reel speed"), (drag, "Drag") };
                    break;
                default:
                    if (s.Lure != null)
                    {
                        // the retrieve you're doing: green when it suits the lure, dim while the lure sits still
                        text = s.Style == RetrieveStyle.None ? "Work the lure: reel, pause, twitch" : Retrieves.Name(s.Style) + " retrieve";
                        if (s.Style == RetrieveStyle.None) color = Dim;
                        else if (Retrieves.IsNatural(s.Lure, s.Style)) color = Moss;
                        keys = new[] { ("Hold RMB", "Retrieve"), ("LMB", "Twitch"), (speed, "Speed"), (drag, "Drag") };
                    }
                    else
                    {
                        text = "Ignore the nibbles. Wait for the real bite";
                        keys = new[] { ("RMB", "Reel in"), (drag, "Drag") };
                    }
                    break;
            }

            float textW = _hint.CalcSize(new GUIContent(text)).x;
            float keysW = KeyPromptsWidth(keys);
            float w = Mathf.Max(textW, keysW) + 48f;
            const float h = 74f;
            // Drawn smaller, in the strip under Valheim's stamina bar: laid out full size with its bottom edge on the
            // pivot, then shrunk toward that point.
            var pivot = new Vector2(_width / 2f, _height - HintBottomGap * _vu);
            var r = new Rect(pivot.x - w / 2f, pivot.y - h, w, h);
            var oldMatrix = GUI.matrix;
            GUIUtility.ScaleAroundPivot(new Vector2(HintScale, HintScale), pivot);
            try
            {
                Panel(r);
                Label(new Rect(r.x, r.y + 8f, w, 30f), text, _hint, color, TextAnchor.MiddleCenter);
                KeyPrompts(keys, r.center.x - keysW / 2f, r.y + 42f, alignRight: false);
            }
            finally { GUI.matrix = oldMatrix; }
        }

        // the hint panel's size, and its gap above the bottom of the screen (Valheim units; the stamina bar's bottom edge
        // is about 56 up)
        private const float HintScale = 0.65f, HintBottomGap = 30f;

        // ------------------------------------------------------------------
        // Catch log
        // ------------------------------------------------------------------

        private static List<FishDefinition>? _logOrder; // the species list never changes after loading

        private static void DrawLog(Player player)
        {
            var entries = CatchLog.Load(player);
            var fish = _logOrder ??= ContentRegistry.Fish.Values
                .OrderBy(f => f.Legendary).ThenBy(f => f.Water).ThenBy(f => f.Name).ToList();

            const float rowH = 24f, colW = 340f, perCol = 16;
            int cols = Mathf.Max(1, Mathf.CeilToInt(fish.Count / perCol));
            float w = colW * cols + 40f;
            float h = 92f + perCol * rowH;
            var r = new Rect(_width / 2f - w / 2f, _height / 2f - h / 2f, w, h);
            Panel(r);

            int found = fish.Count(f => entries.ContainsKey(f.Id));
            var head = new Rect(r.x + 20f, r.y + 14f, w - 40f, 32f);
            Label(head, "Catch Log", _big, Gold, TextAnchor.MiddleLeft);
            Label(head, $"{found} / {fish.Count} species", _text, Cream, TextAnchor.MiddleRight);
            Fill(new Rect(r.x + 20f, r.y + 52f, w - 40f, 1f), Trim);

            for (int i = 0; i < fish.Count; i++)
            {
                var f = fish[i];
                var row = new Rect(r.x + 20f + (int)(i / perCol) * colW, r.y + 62f + (i % (int)perCol) * rowH, colW - 12f, rowH);
                if (entries.TryGetValue(f.Id, out var e))
                {
                    Label(row, f.Name, _text, f.Legendary ? Gold : Cream, TextAnchor.MiddleLeft);
                    Label(row, $"{e.Count} caught  ·  best {e.BestKg:0.0} kg", _small, Dim, TextAnchor.MiddleRight);
                }
                else
                {
                    Label(row, "???", _text, new Color(0.5f, 0.46f, 0.40f), TextAnchor.MiddleLeft);
                }
            }

            string? next = CatchLog.NextReward(player);
            Label(new Rect(r.x + 20f, r.yMax - 30f, w - 160f, 24f), next ?? "Every catch-log reward earned.", _small, Gold, TextAnchor.MiddleLeft);
            KeyPrompts(new[] { (VdwConfig.LogKey.Value.ToString(), "Close") }, r.xMax - 20f, r.yMax - 30f, alignRight: true);
        }

        // ------------------------------------------------------------------
        // Drawing helpers
        // ------------------------------------------------------------------

        private static void Panel(Rect r)
        {
            GUI.color = Color.white;
            GUI.Box(r, GUIContent.none, _panel);
        }

        private static void Fill(Rect r, Color c)
        {
            GUI.color = c;
            GUI.DrawTexture(r, _white);
            GUI.color = Color.white;
        }

        /// <summary>Text with a soft drop shadow so it stays readable over bright water and sky.</summary>
        private static void Label(Rect r, string text, GUIStyle style, Color color, TextAnchor anchor)
        {
            style.alignment = anchor;
            style.normal.textColor = new Color(0f, 0f, 0f, 0.8f * color.a);
            GUI.Label(new Rect(r.x + 1.5f, r.y + 1.5f, r.width, r.height), text, style);
            style.normal.textColor = color;
            GUI.Label(r, text, style);
        }

        private const float ChipGap = 18f;

        private static float ChipWidth(string key) => _smallBold.CalcSize(new GUIContent(key)).x + 16f;

        private static float KeyPromptsWidth((string key, string label)[] keys)
        {
            float w = 0f;
            foreach (var (key, label) in keys)
                w += ChipWidth(key) + 6f + _small.CalcSize(new GUIContent(label)).x + ChipGap;
            return Mathf.Max(0f, w - ChipGap);
        }

        /// <summary>Draws "[key] label  [key] label" starting at x (or ending at x when alignRight).</summary>
        private static void KeyPrompts((string key, string label)[] keys, float x, float y, bool alignRight)
        {
            if (alignRight) x -= KeyPromptsWidth(keys);
            foreach (var (key, label) in keys)
            {
                float cw = ChipWidth(key);
                var chip = new Rect(x, y, cw, 24f);
                GUI.color = Color.white;
                GUI.Box(chip, GUIContent.none, _chip);
                Label(chip, key, _smallBold, Cream, TextAnchor.MiddleCenter);
                x += cw + 6f;

                float lw = _small.CalcSize(new GUIContent(label)).x;
                Label(new Rect(x, y, lw, 24f), label, _small, Dim, TextAnchor.MiddleLeft);
                x += lw + ChipGap;
            }
        }

        // ------------------------------------------------------------------
        // Styles and textures (built once, inside OnGUI)
        // ------------------------------------------------------------------

        private static void EnsureStyles()
        {
            if (!_stylesReady)
            {
                _white = Texture2D.whiteTexture;
                _panelTex = MakeRounded(32, 8f, 2f, Wood, Trim);
                _chipTex = MakeRounded(24, 5f, 1.5f, WoodLight, Trim);
                _discTex = MakeRounded(128, 64f, 3f, Wood, Trim);
                _pipTex = MakeRounded(16, 8f, 0f, Color.white, Color.white);

                _panel = new GUIStyle { normal = { background = _panelTex }, border = new RectOffset(10, 10, 10, 10) };
                _chip = new GUIStyle { normal = { background = _chipTex }, border = new RectOffset(6, 6, 6, 6) };

                _big = TextStyle(22, FontStyle.Bold);
                _text = TextStyle(18, FontStyle.Normal);
                _small = TextStyle(15, FontStyle.Normal);
                _smallBold = TextStyle(15, FontStyle.Bold);
                _hint = TextStyle(24, FontStyle.Bold);
                _stylesReady = true;
            }

            // Valheim's font may only become available after the first few frames.
            if (!_fontApplied)
            {
                var font = VdwFont.Get();
                if (font != null)
                {
                    foreach (var st in new[] { _big, _text, _small, _smallBold, _hint }) st.font = font;
                    _fontApplied = true;
                }
            }
        }

        private static GUIStyle TextStyle(int size, FontStyle fontStyle) => new GUIStyle(GUI.skin.label)
        {
            fontSize = size,
            fontStyle = fontStyle,
            wordWrap = false,
            clipping = TextClipping.Overflow,
            padding = new RectOffset(0, 0, 0, 0),
            margin = new RectOffset(0, 0, 0, 0)
        };

        /// <summary>A rounded rectangle (a circle when radius = size / 2) with an anti-aliased border.</summary>
        private static Texture2D MakeRounded(int size, float radius, float border, Color fill, Color edge)
        {
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
                hideFlags = HideFlags.HideAndDontSave
            };

            float half = size / 2f;
            var pixels = new Color[size * size];
            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    // Signed distance to the rounded rectangle's edge (negative inside).
                    float qx = Mathf.Abs(x + 0.5f - half) - (half - radius);
                    float qy = Mathf.Abs(y + 0.5f - half) - (half - radius);
                    float dist = new Vector2(Mathf.Max(qx, 0f), Mathf.Max(qy, 0f)).magnitude + Mathf.Min(Mathf.Max(qx, qy), 0f) - radius;

                    float coverage = Mathf.Clamp01(0.5f - dist);
                    float edgeAmount = border > 0f ? Mathf.Clamp01(dist + border + 0.5f) : 0f;
                    var c = Color.Lerp(fill, edge, edgeAmount);
                    c.a *= coverage;
                    pixels[y * size + x] = c;
                }
            }

            tex.SetPixels(pixels);
            tex.Apply();
            return tex;
        }
    }
}
