using HarmonyLib;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.UI;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Each trader buys their own kind of catch:
    ///   Haldor     - ordinary raw and cooked fish, at their value
    ///   Hildir     - Trophy-size fish (x2.5) and legendary fish (x1.5) for her collection, and spare relics
    ///   Bog Witch  - roe, fish oil, ink, brined roe, leeches, and swamp, Mistlands and eel-like fish (x1.4)
    /// These sell from a small panel of our own beside the store, not through the store's sell button, so trader UI mods
    /// keep working: vanilla's button goes on selling vanilla valuables only, as vanilla does.
    /// </summary>
    internal static class TraderSales
    {
        private const float TrophyPremium = 2.5f, LegendaryPremium = 1.5f, WitchPremium = 1.4f;
        private const int RelicPrice = 400;
        private static readonly string[] EelLike = { "eikthyr_elver", "queen_eel", "serpentfin" };
        private static readonly Dictionary<string, int> WitchGoods = new Dictionary<string, int>
        {
            ["VDW_Mat_roe"] = 8, ["VDW_Mat_oil"] = 5, ["VDW_Mat_ink"] = 12, [FishDishes.Roe] = 25, ["VDW_Bait_leech"] = 4,
        };

        internal static readonly FieldInfo? TraderField = AccessTools.Field(typeof(StoreGui), "m_trader");

        private static bool IsOurs(ItemDrop.ItemData item) => item.m_dropPrefab != null && item.m_dropPrefab.name.StartsWith("VDW_", StringComparison.Ordinal);

        /// <summary>"Haldor", "Hildir" or "BogWitch" for a trader (by its prefab name; anything else counts as Haldor).</summary>
        public static string KeyOf(Trader? t)
        {
            string n = t != null ? Utils.GetPrefabName(t.gameObject) : "";
            return n.IndexOf("Hildir", StringComparison.OrdinalIgnoreCase) >= 0 ? "Hildir"
                 : n.IndexOf("BogWitch", StringComparison.OrdinalIgnoreCase) >= 0 ? "BogWitch"
                 : "Haldor";
        }

        /// <summary>What this trader pays for one of our items (0: they don't buy it).</summary>
        public static int PriceEach(string trader, ItemDrop.ItemData item)
        {
            if (!IsOurs(item)) return 0;
            string prefab = item.m_dropPrefab!.name;
            FishDefinition? fish = prefab.StartsWith("VDW_Fish_") && ContentRegistry.Fish.TryGetValue(prefab.Substring(9), out var f) ? f : null;
            bool cooked = prefab.StartsWith("VDW_CookedFish_");
            int value = item.m_shared.m_value;
            switch (trader)
            {
                case "Hildir":
                    if (prefab.StartsWith("VDW_Buff_relic_") || prefab == "VDW_Hook_golden") return RelicPrice;
                    if (fish == null || value <= 0) return 0;
                    if (item.m_quality >= FishSize.MaxClass) return Mathf.RoundToInt(value * TrophyPremium);
                    return fish.Legendary ? Mathf.RoundToInt(value * LegendaryPremium) : 0;
                case "BogWitch":
                    if (WitchGoods.TryGetValue(prefab, out int p)) return p;
                    if (fish == null || value <= 0) return 0;
                    bool murky = fish.Biomes.Any(b => b.Equals("Swamp", StringComparison.OrdinalIgnoreCase) || b.Equals("Mistlands", StringComparison.OrdinalIgnoreCase));
                    return murky || EelLike.Contains(fish.Id) ? Mathf.RoundToInt(value * WitchPremium) : 0;
                default:   // Haldor
                    return (fish != null || cooked) && value > 0 ? value : 0;
            }
        }

        /// <summary>Everything in the inventory this trader would buy from us, in inventory order.</summary>
        public static List<ItemDrop.ItemData> Sellable(Player player, string trader) =>
            player.GetInventory().GetAllItems()
                .Where(i => !i.m_equipped && PriceEach(trader, i) > 0)
                .OrderBy(i => i.m_gridPos.y).ThenBy(i => i.m_gridPos.x).ToList();

        /// <summary>Sells the stack: coins in, the trader's sale effects, a message like vanilla's.</summary>
        public static void Sell(Player player, Trader? trader, ItemDrop.ItemData item)
        {
            int coins = PriceEach(KeyOf(trader), item) * item.m_stack;
            if (coins <= 0) return;
            var inv = player.GetInventory();
            bool cheated = inv.ItemCheated(item.m_shared.m_name);
            inv.RemoveItem(item);
            var coin = ObjectDB.instance?.GetItemPrefab("Coins")?.GetComponent<ItemDrop>();
            if (coin != null) inv.AddItem(coin.gameObject.name, coins, 1, 0, 0L, "", cheated);
            string text = item.m_stack <= 1 ? item.m_shared.m_name : item.m_stack + "x" + item.m_shared.m_name;
            if (StoreGui.instance != null) StoreGui.instance.m_sellEffects.Create(player.transform.position, Quaternion.identity);
            player.Message(MessageHud.MessageType.TopLeft, Localization.instance.Localize("$msg_sold", text, coins.ToString()), 0, item.m_shared.m_icons[0]);
            trader?.OnSold();
        }

        /// <summary>Vanilla's sell button sells vanilla valuables only; our catch goes through our panel at each trader's price.</summary>
        [HarmonyPatch(typeof(StoreGui), "GetSellableItem")]
        private static class VanillaValuablesOnly
        {
            private static readonly List<ItemDrop.ItemData> Temp = new List<ItemDrop.ItemData>();
            private static bool Prefix(StoreGui __instance, ref ItemDrop.ItemData? __result)
            {
                var player = Player.m_localPlayer;
                __result = null;
                if (player == null) return false;
                Temp.Clear();
                player.GetInventory().GetValuableItems(Temp);
                __result = Temp.FirstOrDefault(i => i.m_shared.m_name != __instance.m_coinPrefab.m_itemData.m_shared.m_name && !IsOurs(i));
                return false;
            }
        }
    }

    /// <summary>A section of the panel below the sale (Hildir's bounty, a tackle box to give back).</summary>
    internal sealed class PanelSection
    {
        public string Title = "";
        public Sprite? Icon;
        public string Body = "";
        public string Status = "";
        public Color StatusColor = Color.white;
        public string Button = "";
        public bool CanPress;
        public Action? Press;
    }

    /// <summary>
    /// The "Sell your catch" panel: beside whatever store window is open (next to vanilla's store panel when there is
    /// one, wherever a mod has moved it, else on its own), listing everything this trader buys from you. Click a row to
    /// pick it, then Sell, or Sell all. Other sections (Hildir's bounty) add themselves below.
    /// </summary>
    internal sealed class TraderPanel : MonoBehaviour
    {
        private static TraderPanel? _instance;
        private const float W = 400f, Pad = 16f, RowH = 40f;
        private const int Rows = 5;
        private static readonly Color RowBg = new Color(0f, 0f, 0f, 0.35f), RowPicked = new Color(1f, 0.6f, 0.1f, 0.4f),
            Gold = new Color(1f, 0.85f, 0.4f), Muted = new Color(0.82f, 0.78f, 0.7f);
        public static readonly Color Good = new Color(0.55f, 1f, 0.45f), Bad = new Color(1f, 0.6f, 0.45f), Plain = new Color(0.82f, 0.78f, 0.7f);

        private sealed class Row { public GameObject Go = null!; public Image Bg = null!, Icon = null!; public Text Name = null!, Price = null!; }

        private GameObject? _panel;
        private Text? _title, _subtitle, _empty, _pageText, _secTitle, _secBody, _secStatus;
        private Image? _divider, _secIcon;
        private Button? _prevPage, _nextPage, _sell, _sellAll, _secButton;
        private readonly Row[] _rows = new Row[Rows];
        private int _pick, _page;
        private Trader? _trader;
        private Action? _pressSection;

        /// <summary>A section below the sale (Hildir's bounty and tackle boxes), or null to show none.</summary>
        public static Func<Player, Trader, PanelSection?>? ExtraSection;

        public static void Ensure()
        {
            if (_instance != null) return;
            var go = new GameObject("VDW_TraderPanel");
            DontDestroyOnLoad(go);
            _instance = go.AddComponent<TraderPanel>();
        }

        private static Trader? OpenTrader()
        {
            var player = Player.m_localPlayer;
            if (player == null) return null;
            if (StoreGui.IsVisible() && StoreGui.instance != null && TraderSales.TraderField?.GetValue(StoreGui.instance) is Trader t && t != null) return t;
            // a trader UI mod may replace the store: the trader you're standing at, while a trading or inventory screen is up
            if (!StoreGui.IsVisible() && !InventoryGui.IsVisible()) return null;
            Trader? best = null; float bestD = 4f;
            foreach (var tr in FindObjectsByType<Trader>(FindObjectsSortMode.None))
            {
                float d = Vector3.Distance(tr.transform.position, player.transform.position);
                if (d < bestD) { best = tr; bestD = d; }
            }
            return best;
        }

        private void Update()
        {
            var player = Player.m_localPlayer;
            _trader = player != null ? OpenTrader() : null;
            if (_trader == null || player == null) { if (_panel != null) _panel.SetActive(false); return; }
            if (_panel == null && !Build()) return;
            _panel!.SetActive(true);
            Refresh(player);
            Place();
        }

        // ------------------------------------------------------------------ building

        private static void SetRect(Component c, float x, float y, float w, float h)
        {
            var rt = (RectTransform)c.transform;
            rt.anchorMin = rt.anchorMax = new Vector2(0f, 1f); rt.pivot = new Vector2(0f, 1f);
            rt.anchoredPosition = new Vector2(x, y); rt.sizeDelta = new Vector2(w, h);
        }

        private static Text MakeText(Transform parent, int size, Color c, TextAnchor align)
        {
            var gui = GUIManager.Instance;
            var t = gui.CreateText("", parent, new Vector2(0f, 1f), new Vector2(0f, 1f), Vector2.zero, gui.AveriaSerifBold, size, c, true, Color.black, 100f, 20f, false).GetComponent<Text>();
            t.alignment = align; t.horizontalOverflow = HorizontalWrapMode.Wrap; t.verticalOverflow = VerticalWrapMode.Overflow;
            t.supportRichText = true; t.raycastTarget = false;
            return t;
        }

        private Button MakeButton(string label, Action onClick)
        {
            var b = GUIManager.Instance.CreateButton(label, _panel!.transform, new Vector2(0f, 1f), new Vector2(0f, 1f), Vector2.zero, 100f, 30f).GetComponent<Button>();
            b.onClick.AddListener(() => onClick());
            return b;
        }

        private static Image MakeImage(Transform parent, string name, Color c)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image));
            go.transform.SetParent(parent, false);
            var img = go.GetComponent<Image>(); img.color = c;
            return img;
        }

        private bool Build()
        {
            if (GUIManager.CustomGUIFront == null || GUIManager.Instance == null) return false;
            var gui = GUIManager.Instance;
            _panel = gui.CreateWoodpanel(GUIManager.CustomGUIFront.transform, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, W, 200f, false);
            ((RectTransform)_panel.transform).pivot = new Vector2(0f, 1f);
            var p = _panel.transform;

            _title = MakeText(p, 20, gui.ValheimOrange, TextAnchor.UpperLeft);
            _subtitle = MakeText(p, 13, Muted, TextAnchor.UpperLeft);
            _empty = MakeText(p, 14, Muted, TextAnchor.MiddleCenter);
            for (int i = 0; i < Rows; i++)
            {
                int k = i;
                var bg = MakeImage(p, "row" + i, RowBg);
                var btn = bg.gameObject.AddComponent<Button>(); btn.targetGraphic = bg;
                btn.onClick.AddListener(() => _pick = _page * Rows + k);
                var icon = MakeImage(bg.transform, "icon", Color.white); icon.preserveAspect = true; icon.raycastTarget = false;
                SetRect(icon, 4f, -4f, RowH - 8f, RowH - 8f);
                var name = MakeText(bg.transform, 15, Color.white, TextAnchor.MiddleLeft);
                SetRect(name, RowH + 4f, 0f, W - 2 * Pad - RowH - 116f, RowH);
                var price = MakeText(bg.transform, 15, Gold, TextAnchor.MiddleRight);
                SetRect(price, W - 2 * Pad - 112f, 0f, 104f, RowH);
                _rows[i] = new Row { Go = bg.gameObject, Bg = bg, Icon = icon, Name = name, Price = price };
            }
            _prevPage = MakeButton("<", () => _pick = Mathf.Max(0, (_page - 1) * Rows));
            _nextPage = MakeButton(">", () => _pick = (_page + 1) * Rows);
            _pageText = MakeText(p, 14, Muted, TextAnchor.MiddleCenter);
            _sell = MakeButton("Sell", SellPicked);
            _sellAll = MakeButton("Sell all", SellAll);

            _divider = MakeImage(p, "divider", new Color(1f, 0.75f, 0.4f, 0.35f));
            _secTitle = MakeText(p, 18, gui.ValheimOrange, TextAnchor.UpperLeft);
            _secIcon = MakeImage(p, "secIcon", Color.white); _secIcon.preserveAspect = true; _secIcon.raycastTarget = false;
            _secBody = MakeText(p, 14, Color.white, TextAnchor.UpperLeft);
            _secStatus = MakeText(p, 14, Color.white, TextAnchor.UpperLeft);
            _secButton = MakeButton("", () => _pressSection?.Invoke());
            return true;
        }

        // ------------------------------------------------------------------ selling

        private List<ItemDrop.ItemData> List(Player player) => TraderSales.Sellable(player, TraderSales.KeyOf(_trader));

        private void SellPicked()
        {
            var player = Player.m_localPlayer;
            if (player == null) return;
            var list = List(player);
            if (_pick >= 0 && _pick < list.Count) TraderSales.Sell(player, _trader, list[_pick]);
        }

        private void SellAll()
        {
            var player = Player.m_localPlayer;
            if (player == null) return;
            foreach (var item in List(player)) TraderSales.Sell(player, _trader, item);
        }

        private static float TextHeight(Text t, float width)
        {
            ((RectTransform)t.transform).sizeDelta = new Vector2(width, 20f);
            var settings = t.GetGenerationSettings(new Vector2(width, 0f));
            return Mathf.Ceil(t.cachedTextGeneratorForLayout.GetPreferredHeight(t.text, settings) / t.pixelsPerUnit) + 2f;
        }

        private void Refresh(Player player)
        {
            string key = TraderSales.KeyOf(_trader);
            float inner = W - 2 * Pad, y = -Pad;

            _title!.text = "Sell your catch to " + (key switch { "Hildir" => "Hildir", "BogWitch" => "the Bog Witch", _ => "Haldor" });
            SetRect(_title, Pad, y, inner, 26f); y -= 26f;
            _subtitle!.text = key switch
            {
                "Hildir" => "She collects Trophy-size and legendary fish, and spare relics.",
                "BogWitch" => "She pays for roe, oil, ink, leeches and murky-water fish.",
                _ => "He buys raw and cooked fish at their value."
            };
            float sh = TextHeight(_subtitle, inner);
            SetRect(_subtitle, Pad, y, inner, sh); y -= sh + 6f;

            var list = List(player);
            int pages = Mathf.Max(1, (list.Count + Rows - 1) / Rows);
            _pick = list.Count == 0 ? 0 : Mathf.Clamp(_pick, 0, list.Count - 1);
            _page = Mathf.Clamp(_pick / Rows, 0, pages - 1);

            _empty!.gameObject.SetActive(list.Count == 0);
            if (list.Count == 0)
            {
                _empty.text = "Nothing in your bags this trader wants.";
                SetRect(_empty, Pad, y, inner, 44f); y -= 48f;
            }
            for (int i = 0; i < Rows; i++)
            {
                int idx = _page * Rows + i;
                var row = _rows[i];
                bool show = idx < list.Count;
                row.Go.SetActive(show);
                if (!show) continue;
                var item = list[idx];
                SetRect(row.Bg, Pad, y, inner, RowH); y -= RowH + 3f;
                row.Bg.color = idx == _pick ? RowPicked : RowBg;
                row.Icon.sprite = item.GetIcon();
                bool trophy = item.m_quality >= FishSize.MaxClass && item.m_dropPrefab != null && item.m_dropPrefab.name.StartsWith("VDW_Fish_", StringComparison.Ordinal);
                row.Name.text = (item.m_stack > 1 ? item.m_stack + "x " : "") + Localization.instance.Localize(item.m_shared.m_name) + (trophy ? " <color=#ffcc55>(Trophy)</color>" : "");
                row.Price.text = (TraderSales.PriceEach(key, item) * item.m_stack).ToString("N0") + " coins";
            }

            bool paged = pages > 1;
            _prevPage!.gameObject.SetActive(paged); _nextPage!.gameObject.SetActive(paged); _pageText!.gameObject.SetActive(paged);
            if (paged)
            {
                y -= 2f;
                SetRect(_prevPage, Pad, y, 34f, 28f);
                SetRect(_pageText, Pad + 40f, y, inner - 80f, 28f); _pageText.text = $"Page {_page + 1} of {pages}";
                SetRect(_nextPage, W - Pad - 34f, y, 34f, 28f);
                _prevPage.interactable = _page > 0; _nextPage.interactable = _page < pages - 1;
                y -= 32f;
            }

            y -= 4f;
            int total = list.Sum(i => TraderSales.PriceEach(key, i) * i.m_stack);
            SetRect(_sell!, Pad, y, inner * 0.42f, 32f);
            SetRect(_sellAll!, Pad + inner * 0.46f, y, inner * 0.54f, 32f);
            _sell.interactable = list.Count > 0;
            _sellAll.interactable = list.Count > 1;
            _sellAll.GetComponentInChildren<Text>().text = list.Count > 1 ? $"Sell all ({total:N0})" : "Sell all";
            y -= 40f;

            var sec = ExtraSection != null && _trader != null ? ExtraSection(player, _trader) : null;
            foreach (var c in new Component[] { _divider!, _secTitle!, _secIcon!, _secBody!, _secStatus!, _secButton! }) c.gameObject.SetActive(sec != null);
            _pressSection = sec?.Press;
            if (sec != null)
            {
                SetRect(_divider!, Pad, y, inner, 2f); y -= 10f;
                _secTitle!.text = sec.Title;
                SetRect(_secTitle, Pad, y, inner, 24f); y -= 28f;
                float textX = Pad, textW = inner;
                _secIcon!.gameObject.SetActive(sec.Icon != null);
                if (sec.Icon != null)
                {
                    _secIcon.sprite = sec.Icon;
                    SetRect(_secIcon, Pad, y, 56f, 56f);
                    textX += 66f; textW -= 66f;
                }
                _secBody!.text = sec.Body;
                float bh = TextHeight(_secBody, textW);
                SetRect(_secBody, textX, y, textW, bh);
                y -= Mathf.Max(sec.Icon != null ? 58f : 0f, bh) + 8f;
                _secStatus!.gameObject.SetActive(!string.IsNullOrEmpty(sec.Status));
                if (!string.IsNullOrEmpty(sec.Status))
                {
                    _secStatus.text = sec.Status; _secStatus.color = sec.StatusColor;
                    float th = TextHeight(_secStatus, inner);
                    SetRect(_secStatus, Pad, y, inner, th); y -= th + 6f;
                }
                _secButton!.gameObject.SetActive(!string.IsNullOrEmpty(sec.Button));
                if (!string.IsNullOrEmpty(sec.Button))
                {
                    y -= 2f;
                    SetRect(_secButton, Pad + inner * 0.2f, y, inner * 0.6f, 32f); y -= 36f;
                    _secButton.GetComponentInChildren<Text>().text = sec.Button;
                    _secButton.interactable = sec.CanPress;
                }
            }

            ((RectTransform)_panel!.transform).sizeDelta = new Vector2(W, -y + Pad * 0.5f);
        }

        // ------------------------------------------------------------------ placing

        /// <summary>
        /// Somewhere none of the open windows are (the store, the inventory with our tackle panel, a chest or crafting
        /// panel): right of the store first, then left of it, then anywhere, moving down past whatever's in the way.
        /// </summary>
        private void Place()
        {
            var rt = (RectTransform)_panel!.transform;
            var parent = (RectTransform)rt.parent;
            float scale = rt.lossyScale.x > 0f ? rt.lossyScale.x : 1f;
            float pw = W * scale, ph = rt.sizeDelta.y * scale;
            var root = StoreGui.instance != null && StoreGui.IsVisible() && StoreGui.instance.m_rootPanel != null ? StoreGui.instance.m_rootPanel.transform as RectTransform : null;
            const float gap = 12f;
            var blocked = new List<Rect>();
            void Block(RectTransform? r) { if (r != null && r.gameObject.activeInHierarchy && Bounds(r, out var lo, out var hi)) blocked.Add(Rect.MinMaxRect(lo.x - gap, lo.y - gap, hi.x + gap, hi.y + gap)); }
            Block(root);
            var inv = InventoryGui.instance;
            if (inv != null && InventoryGui.IsVisible())
            {
                Block(inv.m_player);                                               // the inventory, with our tackle panel and the armour/weight tabs
                Block(inv.m_container);
                Block(inv.m_crafting);
            }

            // first spot that's free of all of them: right of the store, then left of it, then anywhere across the screen,
            // sliding down past whatever is in the way
            float top = Screen.height - 8f;
            var xs = new List<float>();
            Rect? store = root != null && root.gameObject.activeInHierarchy && Bounds(root, out var smin, out var smax) ? Rect.MinMaxRect(smin.x, smin.y, smax.x, smax.y) : (Rect?)null;
            if (store != null) { xs.Add(store.Value.xMax + gap); xs.Add(store.Value.xMin - gap - pw); top = Mathf.Min(top, store.Value.yMax); }
            for (float x = 8f; x + pw < Screen.width; x += 40f) xs.Add(x);
            Vector2? found = null;
            foreach (float x in xs)
            {
                if (x < 0f || x + pw > Screen.width) continue;
                float y = top;
                for (int guard = 0; guard < 20 && y - ph >= 4f; guard++)
                {
                    var me = Rect.MinMaxRect(x, y - ph, x + pw, y);
                    var hit = blocked.Where(b => b.Overlaps(me)).Select(b => (Rect?)b).FirstOrDefault();
                    if (hit == null) { found = new Vector2(x, y); break; }
                    y = hit.Value.yMin;
                }
                if (found != null) break;
            }
            Vector2 screen = found ?? (store != null ? new Vector2(Mathf.Min(store.Value.xMax + gap, Screen.width - pw), store.Value.yMax)
                                                     : new Vector2(Screen.width * 0.04f, Screen.height * 0.85f));
            screen.y = Mathf.Clamp(screen.y, ph + 4f, Screen.height - 4f);    // keep the whole panel on screen
            if (RectTransformUtility.ScreenPointToLocalPointInRectangle(parent, screen, null, out var local))
            {
                rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
                rt.anchoredPosition = local;
            }
        }

        /// <summary>The screen box around a panel and the two levels below it (bits like the store's sell button and our tackle panel hang outside it).</summary>
        private static bool Bounds(RectTransform root, out Vector2 min, out Vector2 max)
        {
            Vector2 lo = new Vector2(float.MaxValue, float.MaxValue), hi = new Vector2(float.MinValue, float.MinValue);
            var corners = new Vector3[4];
            void Add(RectTransform r)
            {
                r.GetWorldCorners(corners);                                       // overlay canvas: world = screen
                foreach (var c in corners) { lo = Vector2.Min(lo, c); hi = Vector2.Max(hi, c); }
            }
            void Walk(Transform t, int depth)
            {
                foreach (Transform child in t)
                {
                    if (!child.gameObject.activeSelf || !(child is RectTransform r)) continue;
                    if (child.GetComponent<Graphic>() != null) Add(r);
                    if (depth > 1) Walk(child, depth - 1);
                }
            }
            Add(root);
            Walk(root, 2);
            min = lo; max = hi;
            return hi.x > lo.x;
        }
    }
}
