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
        private static readonly Color[] TierColors = { Color.clear, new Color(0.80f, 0.50f, 0.25f), new Color(0.78f, 0.80f, 0.84f), new Color(1f, 0.80f, 0.25f) };   // mastery: bronze, silver, gold
        private static readonly Color Amber = new Color(0.98f, 0.66f, 0.16f);
        private static readonly Color Ember = new Color(0.90f, 0.26f, 0.12f);
        private static readonly Color Moss = new Color(0.50f, 0.70f, 0.28f);
        private static readonly Color Wood = new Color(0.10f, 0.08f, 0.055f, 0.88f);
        private static readonly Color WoodLight = new Color(0.24f, 0.18f, 0.11f, 0.95f);
        private static readonly Color Trim = new Color(0.74f, 0.56f, 0.28f, 1f);
        private static readonly Color Well = new Color(0f, 0f, 0f, 0.55f);

        private static Texture2D? _white, _panelTex, _chipTex, _discTex, _pipTex;
        private static GUIStyle _panel = null!, _chip = null!, _big = null!, _text = null!, _small = null!, _smallBold = null!, _hint = null!, _smallWrap = null!, _smallClip = null!, _textClip = null!;
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
        private static int _logFilter, _logPage;           // which biome filter (0 = all) and page the catch log shows

        private const float LogW = 1120f, LogH = 650f, SideW = 320f, CardH = 62f, CardGap = 8f;
        private const int CardCols = 3;

        /// <summary>
        /// The catch log: a sidebar with the angler rank (and what the next one unlocks), the reward ladder and each
        /// biome set's progress; beside it the species as cards - mastery square, name, the bait it goes for on its own
        /// line, the count to the next tier and the record weight. The mouse is free while it's open: click a biome chip
        /// to filter, the arrows (or the wheel) to turn pages.
        /// </summary>
        private static void DrawLog(Player player)
        {
            var entries = CatchLog.Load(player);
            var all = _logOrder ??= ContentRegistry.Fish.Values
                .OrderBy(f => f.Legendary).ThenBy(f => f.Water).ThenBy(f => f.Name).ToList();
            var sets = Rewards.Sets();

            // filters: All, Legendary, then each biome
            var filters = new List<(string name, string? biome, List<FishDefinition> fish)> { ("All", null, all), ("Legendary", null, all.Where(f => f.Legendary).OrderBy(f => f.Name).ToList()) };
            foreach (var s in sets) filters.Add((s.Name, s.Key, s.Fish.OrderBy(f => f.Name).ToList()));

            _logFilter = Mathf.Clamp(_logFilter, 0, filters.Count - 1);

            var r = new Rect(_width / 2f - LogW / 2f, _height / 2f - LogH / 2f, LogW, LogH);
            Panel(r);
            var side = new Rect(r.x, r.y, SideW, r.height);
            Fill(new Rect(side.xMax, r.y + 12f, 1f, r.height - 24f), Trim);
            DrawLogSidebar(player, entries, all, sets, new Rect(side.x + 20f, side.y + 16f, side.width - 36f, side.height - 32f));
            DrawLogCards(player, entries, filters, new Rect(side.xMax + 20f, r.y + 16f, r.xMax - side.xMax - 40f, r.height - 32f));
        }

        private static void DrawLogSidebar(Player player, Dictionary<string, CatchEntry> entries, List<FishDefinition> all, List<Rewards.BiomeSet> sets, Rect r)
        {
            float y = r.y;
            Label(new Rect(r.x, y, r.width, 32f), "Catch Log", _big, Gold, TextAnchor.MiddleLeft); y += 32f;
            int found = all.Count(f => entries.ContainsKey(f.Id));
            Label(new Rect(r.x, y, r.width, 22f), $"{found} of {all.Count} species logged", _small, Dim, TextAnchor.MiddleLeft); y += 20f;
            int variants = RareFish.Caught(player).Values.Sum(v => v.Count);
            Label(new Rect(r.x, y, r.width, 22f), $"Rare variants: {variants} of {RareFish.EligibleCount() * 2}", _small, Dim, TextAnchor.MiddleLeft); y += 20f;
            // the endgame: bosses landed, and what the next unlock (the Allfather's Rod, then Njord's Regalia) needs
            Label(new Rect(r.x, y, r.width, 22f), $"Boss fish landed: {Endgame.BossesAtLeast(player, 1)} of {Endgame.BossCount}", _small, Dim, TextAnchor.MiddleLeft); y += 20f;
            string step = Endgame.NextStep(player);
            if (step.Length > 0)
            {
                float sh2 = _smallWrap.CalcHeight(new GUIContent(step), r.width);
                Label(new Rect(r.x, y, r.width, sh2), step, _smallWrap, new Color(0.85f, 0.7f, 0.45f), TextAnchor.UpperLeft); y += sh2;
            }
            y += 10f;

            // the angler rank, its bar, and what the next rank unlocks
            int points = AnglerRanks.Points(player);
            int idx = AnglerRanks.RankIndex(points);
            var rank = AnglerRanks.Ranks[idx];
            bool top = idx >= AnglerRanks.Ranks.Length - 1;
            var next = top ? null : AnglerRanks.Ranks[idx + 1];
            Label(new Rect(r.x, y, r.width, 20f), $"Angler rank {idx + 1} of {AnglerRanks.Ranks.Length}", _small, Dim, TextAnchor.MiddleLeft); y += 20f;
            Label(new Rect(r.x, y, r.width, 26f), rank.Name, _text, Gold, TextAnchor.MiddleLeft); y += 28f;
            float frac = top ? 1f : Mathf.Clamp01((points - rank.Points) / (float)(next!.Points - rank.Points));
            var bar = new Rect(r.x, y, r.width, 12f);
            Fill(bar, new Color(0f, 0f, 0f, 0.55f));
            Fill(new Rect(bar.x + 1f, bar.y + 1f, (bar.width - 2f) * frac, bar.height - 2f), new Color(0.86f, 0.62f, 0.2f, 0.95f));
            y += 16f;
            Label(new Rect(r.x, y, r.width, 20f), top ? "Highest rank reached" : $"{points - rank.Points:N0} / {next!.Points - rank.Points:N0} ({Mathf.FloorToInt(frac * 100f)}%) to {next.Name}", _small, Cream, TextAnchor.MiddleLeft);
            y += 20f;
            if (!top)
            {
                string unlocks = next!.Unlocks.Length > 0 ? string.Join(", ", next.Unlocks.Select(AnglerRanks.ItemName)) : "nothing new";
                string line = "Next rank unlocks: " + unlocks;
                float h = _smallWrap.CalcHeight(new GUIContent(line), r.width);
                Label(new Rect(r.x, y, r.width, h), line, _smallWrap, Dim, TextAnchor.UpperLeft); y += h + 12f;
            }
            else y += 12f;

            // the reward ladder: done steps dimmed, the next one in gold
            Label(new Rect(r.x, y, r.width, 20f), "Catch log rewards", _small, Dim, TextAnchor.MiddleLeft); y += 22f;
            // earned steps and the next one; the rest stay a surprise
            bool nextMarked = false;
            foreach (var (at, label, done) in CatchLog.Ladder(player))
            {
                bool isNext = !done && !nextMarked;
                if (!done && !isNext) continue;
                if (isNext) nextMarked = true;
                var c = done ? new Color(0.49f, 0.45f, 0.38f) : isNext ? Gold : Cream;
                Label(new Rect(r.x, y, 32f, 18f), at, _small, c, TextAnchor.MiddleRight);
                var dot = new Rect(r.x + 40f, y + 5f, 8f, 8f);
                Fill(dot, done ? new Color(0.85f, 0.62f, 0.2f) : new Color(0f, 0f, 0f, 0.5f));
                Label(new Rect(r.x + 56f, y, r.width - 56f, 18f), label, _smallClip, c, TextAnchor.MiddleLeft);
                y += 19f;
            }
            y += 10f;

            // biome sets: a thin bar each, gold when complete
            Label(new Rect(r.x, y, r.width, 20f), "Biome sets", _small, Dim, TextAnchor.MiddleLeft); y += 22f;
            foreach (var s in sets)
            {
                if (y > r.yMax - 22f) break;
                int have = s.Fish.Count(f => Rewards.LoggedIn(player, f, s.Key, entries));
                bool done = Rewards.SetDone(player, s);
                Label(new Rect(r.x, y, r.width, 16f), s.Name, _small, done ? Gold : Cream, TextAnchor.MiddleLeft);
                Label(new Rect(r.x, y, r.width, 16f), $"{have} / {s.Fish.Count}", _small, Dim, TextAnchor.MiddleRight);
                var b = new Rect(r.x, y + 18f, r.width, 4f);
                Fill(b, new Color(0f, 0f, 0f, 0.5f));
                Fill(new Rect(b.x, b.y, b.width * have / Mathf.Max(1, s.Fish.Count), b.height), done ? Gold : new Color(0.54f, 0.63f, 0.44f));
                y += 26f;
            }
        }

        private static void DrawLogCards(Player player, Dictionary<string, CatchEntry> entries, List<(string name, string? biome, List<FishDefinition> fish)> filters, Rect r)
        {
            // the filter chips, wrapping onto a second row when they don't fit on one
            float x = r.x, chipY = r.y;
            for (int i = 0; i < filters.Count; i++)
            {
                string name = filters[i].name;
                float w = _small.CalcSize(new GUIContent(name)).x + 18f;
                if (x + w > r.xMax) { x = r.x; chipY += 28f; }
                var chip = new Rect(x, chipY, w, 24f);
                if (GUI.Button(chip, GUIContent.none, GUIStyle.none)) { _logFilter = i; _logPage = 0; }
                bool hover = chip.Contains(Event.current.mousePosition);
                if (i == _logFilter || hover) GUI.Box(chip, GUIContent.none, _chip);
                Label(chip, name, _small, i == _logFilter ? Gold : Dim, TextAnchor.MiddleCenter);
                x += w + 4f;
            }

            var fish = filters[_logFilter].fish;
            float cardW = (r.width - (CardCols - 1) * CardGap) / CardCols;
            float top = chipY + 36f, bottom = r.yMax - 34f;
            int rows = Mathf.Max(1, Mathf.FloorToInt((bottom - top + CardGap) / (CardH + CardGap)));
            int perPage = rows * CardCols;
            int pages = Mathf.Max(1, Mathf.CeilToInt(fish.Count / (float)perPage));
            // the mouse wheel over the cards turns the page
            var ev = Event.current;
            if (ev.type == EventType.ScrollWheel && new Rect(r.x, top, r.width, bottom - top).Contains(ev.mousePosition))
            {
                _logPage += ev.delta.y > 0 ? 1 : -1;
                ev.Use();
            }
            _logPage = Mathf.Clamp(_logPage, 0, pages - 1);

            for (int i = 0; i < perPage; i++)
            {
                int n = _logPage * perPage + i;
                if (n >= fish.Count) break;
                var card = new Rect(r.x + (i % CardCols) * (cardW + CardGap), top + (i / CardCols) * (CardH + CardGap), cardW, CardH);
                DrawFishCard(player, fish[n], entries, filters[_logFilter].biome, card);
            }

            // the page arrows, and a close button (J or Escape close it too)
            float by = r.yMax - 26f;
            if (pages > 1)
            {
                if (LogButton(new Rect(r.x, by, 34f, 26f), "<", _logPage > 0)) _logPage--;
                Label(new Rect(r.x + 40f, by, 110f, 26f), $"Page {_logPage + 1} of {pages}", _small, Dim, TextAnchor.MiddleCenter);
                if (LogButton(new Rect(r.x + 156f, by, 34f, 26f), ">", _logPage < pages - 1)) _logPage++;
            }
            if (LogButton(new Rect(r.xMax - 90f, by, 90f, 26f), "Close", true)) FishingController.CloseLog();
        }

        /// <summary>A small wooden button for the catch log: a chip that lights on hover; greyed out and dead when disabled.</summary>
        private static bool LogButton(Rect b, string text, bool enabled)
        {
            bool hover = enabled && b.Contains(Event.current.mousePosition);
            GUI.color = enabled ? (hover ? new Color(1f, 0.9f, 0.7f) : Color.white) : new Color(1f, 1f, 1f, 0.35f);
            GUI.Box(b, GUIContent.none, _chip);
            GUI.color = Color.white;
            Label(b, text, _smallBold, enabled ? (hover ? Gold : Cream) : Dim, TextAnchor.MiddleCenter);
            return enabled && GUI.Button(b, GUIContent.none, GUIStyle.none);
        }

        private static void DrawFishCard(Player player, FishDefinition f, Dictionary<string, CatchEntry> entries, string? biome, Rect c)
        {
            // in a biome's tab, a species caught only elsewhere so far: named, but not yet logged here
            if (biome != null && entries.ContainsKey(f.Id) && !Rewards.LoggedIn(player, f, biome, entries))
            {
                Fill(c, new Color(0.14f, 0.105f, 0.07f, 0.9f));
                var box = new Rect(c.x + 10f, c.y + 6f, c.width - 20f, c.height - 12f);
                Label(new Rect(box.x, box.y, box.width, 22f), f.Name, _textClip, new Color(0.6f, 0.55f, 0.46f), TextAnchor.MiddleLeft);
                string here = Rewards.Sets().FirstOrDefault(s => s.Key == biome)?.Name ?? biome;
                Label(new Rect(box.x, box.y + 26f, box.width, 18f), $"Not caught in the {here} yet", _smallClip, Dim, TextAnchor.MiddleLeft);
                return;
            }
            Fill(c, new Color(0.14f, 0.105f, 0.07f, 0.9f));
            Fill(new Rect(c.x, c.y, c.width, 1f), f.Legendary ? Trim : new Color(0.29f, 0.23f, 0.16f));
            var inner = new Rect(c.x + 10f, c.y + 6f, c.width - 20f, c.height - 12f);
            if (!entries.TryGetValue(f.Id, out var e))
            {
                Label(new Rect(inner.x, inner.y, inner.width, 22f), "???", _text, new Color(0.49f, 0.45f, 0.38f), TextAnchor.MiddleLeft);
                string where = string.Join(", ", Rewards.BiomesOf(f).Select(b => Rewards.Sets().FirstOrDefault(s => s.Key == b)?.Name ?? b));
                Label(new Rect(inner.x, inner.y + 26f, inner.width, 18f), "Not caught yet" + (where.Length > 0 ? " · " + where : ""), _smallClip, Dim, TextAnchor.MiddleLeft);
                return;
            }

            int tier = Mastery.TierFor(f, e.Count);
            var t = Mastery.Thresholds(f);
            var pip = new Rect(inner.x, inner.y + 5f, 12f, 12f);
            Fill(pip, tier == Mastery.None ? new Color(0f, 0f, 0f, 0.4f) : TierColors[tier]);
            if (tier == Mastery.None) Fill(new Rect(pip.x + 2f, pip.y + 2f, 8f, 8f), Wood);
            Label(new Rect(inner.x + 18f, inner.y, inner.width - 44f, 22f), f.Name, _textClip, f.Legendary ? Gold : Cream, TextAnchor.MiddleLeft);
            // the rare variants: a gold and a pale mark, lit once you've caught that one
            if (RareFish.Eligible(f))
            {
                RareFish.Caught(player).TryGetValue(f.Id, out var got);
                var gold = new Rect(inner.xMax - 22f, inner.y + 6f, 9f, 9f);
                var pale = new Rect(inner.xMax - 9f, inner.y + 6f, 9f, 9f);
                Fill(gold, got != null && got.Contains(RareFish.Golden) ? new Color(1f, 0.82f, 0.3f) : new Color(0f, 0f, 0f, 0.45f));
                Fill(pale, got != null && got.Contains(RareFish.Albino) ? new Color(0.96f, 0.9f, 0.9f) : new Color(0f, 0f, 0f, 0.45f));
            }

            string bait = BaitTargets.BaitsFor(f);
            if (Mastery.IsBaitfish(f)) bait = (bait.Length > 0 ? bait + " · " : "") + "baitfish";
            Label(new Rect(inner.x, inner.y + 22f, inner.width, 16f), bait, _smallClip, Dim, TextAnchor.MiddleLeft);

            // the count to the next tier, or the top tier with the count (baitfish stop at Bronze)
            string progress = BossFish.IsBoss(f.Id) ? $"Landed x{e.Count}" + (tier < t.Length - 1 ? $" · {t[tier + 1]} for {Mastery.TierNames[tier + 1]}" : $" · {Mastery.TierNames[tier]}")
                : tier < t.Length - 1
                ? $"{e.Count} / {t[tier + 1]} to {Mastery.TierNames[tier + 1]}"
                : $"{e.Count} caught · {Mastery.TierNames[tier]} ({(Mastery.IsBaitfish(f) ? "top for baitfish" : "top")})";
            Label(new Rect(inner.x, inner.y + 38f, inner.width, 16f), progress, _smallClip, Dim, TextAnchor.MiddleLeft);
            Label(new Rect(inner.x, inner.y + 38f, inner.width, 16f), $"best {e.BestKg:0.0} kg", _small, Dim, TextAnchor.MiddleRight);
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
                _smallWrap = TextStyle(15, FontStyle.Normal); _smallWrap.wordWrap = true;
                _smallClip = TextStyle(15, FontStyle.Normal); _smallClip.clipping = TextClipping.Clip;
                _textClip = TextStyle(18, FontStyle.Normal); _textClip.clipping = TextClipping.Clip;
                _stylesReady = true;
            }

            // Valheim's font may only become available after the first few frames.
            if (!_fontApplied)
            {
                var font = VdwFont.Get();
                if (font != null)
                {
                    foreach (var st in new[] { _big, _text, _small, _smallBold, _hint, _smallWrap, _smallClip, _textClip }) st.font = font;
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
