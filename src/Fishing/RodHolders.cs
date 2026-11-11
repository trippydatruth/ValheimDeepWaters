using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Two pieces for rods (playtest notes 2026-11-07):
    ///   the Rod Holder - a forked stake for the bank. Set a rod in it with its line out and the line keeps fishing:
    ///     the rod's butt rests on the ground and it leans into the fork, its tip twitching at nibbles and bending over
    ///     when something takes the bait, for everyone nearby to see. A circle hook left alone sets itself. Anyone can
    ///     pick the rod up - a fish on is theirs to fight. Set out as many as you like, and fish another rod by hand.
    ///   the Rod Rack - storage only, like an armor stand: up to ten rods stand in it, shown as they are.
    /// </summary>
    internal static class RodHolders
    {
        public const string HolderPrefab = "VDW_RodHolder", RackPrefab = "VDW_RodRack";

        public static void Register()
        {
            try
            {
                var holder = new CustomPiece(HolderPrefab, "wood_pole", new PieceConfig
                {
                    Name = Loc.Token("vdw_piece_rod_holder", "Rod Holder"),
                    Description = Loc.Token("vdw_piece_rod_holder_desc", "A forked stake for the bank. Set your rod in it with the line out and it keeps fishing: the tip twitches at a nibble and bends over when something takes it. A circle hook sets itself. Anyone can grab the rod and fight the fish."),
                    PieceTable = "Hammer",
                    Category = "Furniture",
                    CraftingStation = "piece_workbench",
                    Requirements = new[] { new RequirementConfig("Wood", 4), new RequirementConfig("LeatherScraps", 2) }
                });
                Setup(holder.PiecePrefab, "piece_rod_holder");
                holder.PiecePrefab.AddComponent<RodHolder>();
                PieceManager.Instance.AddPiece(holder);

                var rack = new CustomPiece(RackPrefab, "wood_pole", new PieceConfig
                {
                    Name = Loc.Token("vdw_piece_rod_rack", "Rod Rack"),
                    Description = Loc.Token("vdw_piece_rod_rack_desc", "A round oak rack to keep up to ten rods, each standing in its socket and clip."),
                    PieceTable = "Hammer",
                    Category = "Furniture",
                    CraftingStation = "piece_workbench",
                    Requirements = new[] { new RequirementConfig("FineWood", 8), new RequirementConfig("Iron", 2), new RequirementConfig("LeatherScraps", 4) }
                });
                Setup(rack.PiecePrefab, "piece_rod_rack");
                rack.PiecePrefab.AddComponent<RodRack>();
                PieceManager.Instance.AddPiece(rack);
            }
            catch (Exception ex) { Plugin.Log.LogError($"Rod holders: couldn't register ({ex})"); }
        }

        private static void Setup(GameObject prefab, string model)
        {
            CustomModels.ApplyToPrefab(prefab, model);
            var wnt = prefab.GetComponent<WearNTear>();
            if (wnt != null) wnt.m_supports = false;   // nothing builds onto it
        }

        // ------------------------------------------------------------------ the rod item on a piece

        public static void SaveRod(ZDO zdo, int index, ItemDrop.ItemData? item)
        {
            zdo.Set($"vdw_rodname_{index}", item?.m_dropPrefab != null ? item.m_dropPrefab.name : "");
            if (item != null) ItemDrop.SaveToZDO(item, zdo, index);
        }

        public static ItemDrop.ItemData? LoadRod(ZDO zdo, int index)
        {
            string name = zdo.GetString($"vdw_rodname_{index}", "");
            if (name.Length == 0 || ObjectDB.instance == null) return null;
            var prefab = ObjectDB.instance.GetItemPrefab(name);
            var drop = prefab != null ? prefab.GetComponent<ItemDrop>() : null;
            if (drop == null) return null;
            var item = drop.m_itemData.Clone();
            item.m_dropPrefab = prefab;
            ItemDrop.LoadFromZDO(item, zdo, index);
            item.m_equipped = false;
            return item;
        }

        /// <summary>Puts a rod into the player's hands (through the tackle's rod slot, as the rod key does). False: no room.</summary>
        public static bool GiveRodInHand(Player player, ItemDrop.ItemData rod)
        {
            if (!player.GetInventory().AddItem(rod))
            {
                player.Message(MessageHud.MessageType.Center, "No room in your inventory for the rod.");
                return false;
            }
            var held = player.GetCurrentWeapon();
            if (held != null && held != rod && ContentRegistry.IsRod(held)) player.UnequipItem(held, false);
            Tackle.PutRodInSlot(player, rod, hold: true);
            return true;
        }

        /// <summary>Takes the rod the player is holding out of their hands and inventory (or tackle slot).</summary>
        public static void TakeRodFrom(Player player, ItemDrop.ItemData rod)
        {
            player.UnequipItem(rod, false);
            var tackle = Tackle.Get(player);
            if (tackle.ContainsItem(rod)) tackle.RemoveItem(rod);
            else player.GetInventory().RemoveItem(rod);
        }

        public static string RodName(ItemDrop.ItemData? item) => item != null ? Loc.Text(item.m_shared.m_name) : "";
    }

    /// <summary>
    /// A rod shown on a holder or rack: its own (rigged) model, placed with its butt at a point and its length along a
    /// direction, the side the reel and guides hang on facing <c>down</c>.
    /// </summary>
    internal static class RodDisplay
    {
        public static GameObject? Build(ItemDrop.ItemData item, Transform parent, Vector3 butt, Vector3 dir, Vector3 down, out RodRig? rig)
        {
            rig = null;
            var def = ContentRegistry.GetRod(item);
            if (def == null) return null;
            var model = CustomModels.GetBundlePrefab("rod_" + def.Id) ?? CustomModels.GetBundlePrefab("rod");
            if (model == null) return null;

            var go = UnityEngine.Object.Instantiate(model, parent, false);
            go.name = "vdw_shown_rod";
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
            foreach (var rb in go.GetComponentsInChildren<Rigidbody>(true)) UnityEngine.Object.DestroyImmediate(rb);
            foreach (var an in go.GetComponentsInChildren<Animator>(true)) UnityEngine.Object.DestroyImmediate(an);
            foreach (var smr in go.GetComponentsInChildren<SkinnedMeshRenderer>(true)) smr.updateWhenOffscreen = true;
            foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = parent.gameObject.layer;
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale = model.transform.localScale;

            // the rod's own length and underside, from its bones (butt to tip; Rod.BendDir marks its underside)
            var all = go.GetComponentsInChildren<Transform>(true);
            var blank = all.Where(t => t.name.StartsWith("Rod.") && int.TryParse(t.name.Substring(4), out _)).OrderBy(t => int.Parse(t.name.Substring(4))).ToList();
            var tip = all.FirstOrDefault(t => t.name == "Rod.Tip") ?? blank.LastOrDefault();
            var bend = all.FirstOrDefault(t => t.name == "Rod.BendDir");
            Vector3 P(Transform t) => parent.InverseTransformPoint(t.position);
            Vector3 axis = blank.Count > 0 && tip != null ? P(tip) - P(blank[0]) : Vector3.up;
            if (axis.sqrMagnitude < 1e-6f) axis = Vector3.up;
            Vector3 under = bend != null && blank.Count > 0 ? Vector3.ProjectOnPlane(P(bend) - P(blank[0]), axis) : Vector3.zero;
            if (under.sqrMagnitude < 1e-6f) under = Vector3.ProjectOnPlane(Vector3.down, axis);
            if (under.sqrMagnitude < 1e-6f) under = Vector3.ProjectOnPlane(Vector3.forward, axis);
            var want = Quaternion.LookRotation(dir, -down);
            var have = Quaternion.LookRotation(axis.normalized, -under.normalized);
            go.transform.localRotation = want * Quaternion.Inverse(have);

            // its butt (the end furthest back along its length) at the butt point
            float min = float.MaxValue;
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                Mesh? mesh = r is SkinnedMeshRenderer s ? s.sharedMesh : r.GetComponent<MeshFilter>()?.sharedMesh;
                if (mesh == null) continue;
                var b = mesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = b.center + Vector3.Scale(b.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                    min = Mathf.Min(min, Vector3.Dot(parent.InverseTransformPoint(r.transform.TransformPoint(c)), dir));
                }
            }
            if (min == float.MaxValue) min = Vector3.Dot(blank.Count > 0 ? P(blank[0]) : Vector3.zero, dir);
            go.transform.localPosition = butt - dir * min;
            rig = go.AddComponent<RodRig>();
            return go;
        }
    }

    /// <summary>The Rod Holder (see RodHolders). Its rod and line live in its ZDO, so every player sees the same.</summary>
    internal sealed class RodHolder : MonoBehaviour, Hoverable, Interactable
    {
        internal static readonly List<RodHolder> All = new();

        // the rod lies with its butt on the ground, leaning into the fork at 35 degrees, its tip away from where the
        // holder was placed from (the piece's forward), its reel underneath
        private const float Rest = 0.665f, Lean = 35f;
        internal ZNetView? NView;
        private GameObject? _shown;
        private RodRig? _rig;
        private string _shownKey = "";

        // what everyone draws of the line (the owner draws its real one)
        private BobberVisual? _bobber;
        private HookedFishVisual? _fish;
        private string _fishKey = "";
        private int _fxSeen = -1, _saidSeen = -1, _phaseSeen;
        private float _nibble, _spin;

        public ZDO? Zdo => NView != null && NView.IsValid() ? NView.GetZDO() : null;
        public bool HasRod => Zdo is ZDO z && z.GetString("vdw_rodname_0", "").Length > 0;
        public bool LineOut => Zdo is ZDO z && z.GetBool("vdw_line", false);
        public int Phase => Zdo?.GetInt("vdw_ph", 0) ?? 0;

        private void Awake()
        {
            NView = GetComponent<ZNetView>();
            if (NView == null || NView.GetZDO() == null) return;
            All.Add(this);
        }

        private void OnDestroy()
        {
            All.Remove(this);
            ClearRemote();
            ParkedLines.HolderGone(this);
        }

        public Vector3 RodDir => transform.TransformDirection(new Vector3(0f, Mathf.Sin(Lean * Mathf.Deg2Rad), Mathf.Cos(Lean * Mathf.Deg2Rad)));

        /// <summary>Where the line leaves the rod resting in it.</summary>
        public Vector3 Tip => _rig != null && _rig.Tip != null ? _rig.Tip.position : transform.position + RodDir * 2.5f;

        private void UpdateShownRod()
        {
            var z = Zdo; if (z == null) return;
            string key = z.GetString("vdw_rodname_0", "") + "#" + z.GetInt("vdw_rodq", 0);
            if (key == _shownKey) return;
            _shownKey = key;
            if (_shown != null) Destroy(_shown);
            _shown = null; _rig = null;
            var item = RodHolders.LoadRod(z, 0);
            if (item == null) return;
            var dir = new Vector3(0f, Mathf.Sin(Lean * Mathf.Deg2Rad), Mathf.Cos(Lean * Mathf.Deg2Rad));
            var down = new Vector3(0f, -Mathf.Cos(Lean * Mathf.Deg2Rad), Mathf.Sin(Lean * Mathf.Deg2Rad));
            var butt = new Vector3(0f, Rest, 0f) - dir * ((Rest - 0.016f) / Mathf.Sin(Lean * Mathf.Deg2Rad));
            _shown = RodDisplay.Build(item, transform, butt, dir, down, out _rig);
        }

        private void LateUpdate()
        {
            if (Zdo == null) return;
            UpdateShownRod();
            var z = Zdo;
            bool line = z.GetBool("vdw_line", false);
            int phase = line ? z.GetInt("vdw_ph", 1) : 0;
            Vector3 end = z.GetVec3("vdw_end", transform.position);
            bool running = z.GetBool("vdw_run", false);
            var me = Player.m_localPlayer;

            // its news: a bite, a fish on, a fish lost - for everyone near enough to do something about it
            int said = z.GetInt("vdw_saidn", 0);
            if (_saidSeen < 0) _saidSeen = said;
            if (said != _saidSeen)
            {
                _saidSeen = said;
                string text = z.GetString("vdw_said", "");
                if (me != null && text.Length > 0 && Vector3.Distance(me.transform.position, transform.position) < 60f)
                {
                    bool big = text.StartsWith("FISH ON") || text.Contains("hooked") || text.Contains("set itself") || text.Contains("Hook set");
                    me.Message(big ? MessageHud.MessageType.Center : MessageHud.MessageType.TopLeft, $"Rod holder ({RodHolders.RodName(RodHolders.LoadRod(z, 0))}): {text}");
                }
            }

            // what happened at its line, for everyone (the owner's own effects already played)
            int fx = z.GetInt("vdw_fxn", 0);
            if (_fxSeen < 0) _fxSeen = fx;
            bool owner = NView!.IsOwner() && ParkedLines.Has(this);
            if (fx != _fxSeen)
            {
                _fxSeen = fx;
                var kind = (FishFx)z.GetInt("vdw_fxk", 0); float arg = z.GetFloat("vdw_fxa", 0f);
                if (kind == FishFx.Nibble || kind == FishFx.Bite) _nibble = kind == FishFx.Bite ? 1.4f : 1f;
                if (!owner && line)
                {
                    switch (kind)
                    {
                        case FishFx.Nibble: FishingFx.Nibble(end, share: false); _bobber?.Nibble(0.08f); break;
                        case FishFx.Bite: FishingFx.Bite(end, share: false); break;
                        case FishFx.HookSet: FishingFx.HookSet(end, share: false); break;
                        case FishFx.Splash: FishingFx.FishSplash(end, arg, share: false); break;
                        case FishFx.Leap: _fish?.Leap(arg, 1f); FishingFx.FishSplash(end, 0.5f + arg * 0.4f, share: false); break;
                        case FishFx.Snap: FishingFx.LineSnap(end, share: false); break;
                        case FishFx.Landing: FishingFx.Landing(end, share: false); break;
                    }
                }
            }

            // the rod's tells: a twitch at a nibble, nodding while a fish has the bait, bent over with a fish on
            if (_rig != null)
            {
                _nibble = Mathf.Max(0f, _nibble - Time.deltaTime * 2.2f);
                float t = Time.time, bend;
                if (phase == 3) bend = (running ? 26f : 15f) + (running ? 5f : 2f) * Mathf.Sin(t * 23f) + 3f * Mathf.Sin(t * 7.3f);
                else if (phase == 2) bend = 9f + 7f * Mathf.Abs(Mathf.Sin(t * 9f));
                else bend = _nibble * 7f * Mathf.Sin(t * 38f);
                bend += line && phase == 1 ? 1.5f : 0f;   // a line out pulls the tip over a hair
                _spin = phase == 3 && running ? 720f * Time.deltaTime : 0f;   // the drag giving line
                _rig.Pose(bend, line ? end : (Vector3?)null, _spin);
            }

            if (phase != _phaseSeen) _phaseSeen = phase;

            // everyone else's view of the line: the float (or the line going into the water) and a fish on
            if (!line || owner || me == null || Vector3.Distance(me.transform.position, transform.position) > 90f) { ClearRemote(); return; }
            if (_bobber == null)
            {
                _bobber = BobberVisual.Create(end, z.GetBool("vdw_lure", false), remote: true);
                _bobber.Position = end;
            }
            _bobber.Position = Vector3.Lerp(_bobber.Position, end, 1f - Mathf.Exp(-Time.deltaTime * 8f));
            _bobber.Slack = phase == 3 ? 0f : 0.12f;
            _bobber.Dipped = phase == 2;
            _bobber.Thrashing = phase == 3 && running;
            _bobber.Refresh(me, Tip);
            string fishKey = phase == 3 ? z.GetString("vdw_fish", "") : "";
            if (fishKey != _fishKey)
            {
                if (_fish != null) Destroy(_fish.gameObject);
                _fish = null; _fishKey = fishKey;
                var parts = fishKey.Split('#');
                if (parts[0].Length > 0 && ContentRegistry.Fish.TryGetValue(parts[0], out var fd) && ContentRegistry.FishItems.TryGetValue(parts[0], out var prefab))
                {
                    _fish = HookedFishVisual.Create(prefab, ContentRegistry.ModelKeyFor(fd), z.GetFloat("vdw_fsc", 1f));
                    if (_fish != null) _fish.StayUnder = 0.05f;
                    if (parts.Length > 1 && int.TryParse(parts[1], out int v)) RareFish.TintModel(_fish?.gameObject, v);
                }
            }
            if (_fish != null) { _fish.Position = end + Vector3.down * 0.15f; _fish.Intensity = running ? 1f : 0.25f; }
        }

        private void ClearRemote()
        {
            if (_bobber != null) Destroy(_bobber.gameObject);
            if (_fish != null) Destroy(_fish.gameObject);
            _bobber = null; _fish = null; _fishKey = "";
        }

        // ------------------------------------------------------------------ hover and use

        public string GetHoverName() => Loc.Text(Loc.Token("vdw_piece_rod_holder", "Rod Holder"));
        public float GetHoverOffset() => 0f;

        public string GetHoverText()
        {
            var z = Zdo; if (z == null) return "";
            string name = GetHoverName();
            if (!HasRod)
            {
                bool lineInHand = FishingController.HandSession != null;
                return $"{name}\n[<color=yellow><b>{Loc.Text("$KEY_Use")}</b></color>] {(lineInHand ? "Set your rod in it - its line stays out" : "Set your rod in it")}";
            }
            string rod = RodHolders.RodName(RodHolders.LoadRod(z, 0));
            string state = !LineOut ? "" : Phase switch { 3 => "  <color=#ff6040>FISH ON!</color>", 2 => "  <color=#ffcc40>a bite!</color>", _ => "  <color=#9fd4ff>line out</color>" };
            return $"{name}: {rod}{state}\n[<color=yellow><b>{Loc.Text("$KEY_Use")}</b></color>] {(LineOut ? "Take up the rod" : "Take the rod")}";
        }

        public bool Interact(Humanoid user, bool hold, bool alt)
        {
            if (hold || !(user is Player player) || player != Player.m_localPlayer || Zdo == null) return false;
            if (HasRod) return TakeRod(player);
            var held = player.GetCurrentWeapon();
            if (held == null || !ContentRegistry.IsRod(held))
            {
                player.Message(MessageHud.MessageType.Center, "Take a rod in hand to set it in the holder.");
                return false;
            }
            return SetRod(player, held);
        }

        public bool UseItem(Humanoid user, ItemDrop.ItemData item)
        {
            if (!(user is Player player) || player != Player.m_localPlayer || item == null || !ContentRegistry.IsRod(item) || HasRod) return false;
            return SetRod(player, item);
        }

        /// <summary>A rod set in the holder: if it's the one in your hands with a line out, the line stays out and fishes.</summary>
        private bool SetRod(Player player, ItemDrop.ItemData rod)
        {
            FishingSession? parked = null;
            bool hasLine = FishingController.HandSession != null && player.GetCurrentWeapon() == rod;
            if (hasLine)
            {
                parked = FishingController.Park(player, Tip, out var why);
                if (parked == null) { player.Message(MessageHud.MessageType.Center, why); return false; }
            }
            NView!.ClaimOwnership();
            var z = Zdo!;
            RodHolders.TakeRodFrom(player, rod);
            RodHolders.SaveRod(z, 0, rod);
            z.Set("vdw_rodq", rod.m_quality);
            UpdateShownRod();
            if (parked != null)
            {
                parked.Anchor = Tip;
                ParkedLines.Start(this, parked);
                player.Message(MessageHud.MessageType.Center, "You set the rod in the holder. Its line stays out.");
            }
            else player.Message(MessageHud.MessageType.TopLeft, "You set the rod in the holder.");
            return true;
        }

        /// <summary>Takes the rod out - with its line, and any fish on it, if the line is out.</summary>
        private bool TakeRod(Player player)
        {
            var z = Zdo!;
            if (LineOut && FishingController.HandSession != null)
            {
                player.Message(MessageHud.MessageType.Center, "You've already a line out in your hands - reel it in first.");
                return false;
            }
            var rod = RodHolders.LoadRod(z, 0);
            if (rod == null) { RodHolders.SaveRod(z, 0, null); return false; }
            FishingSession? s = null;
            if (LineOut)
            {
                NView!.ClaimOwnership();
                s = ParkedLines.Take(this, player);
            }
            if (!RodHolders.GiveRodInHand(player, rod))
            {
                if (s != null) ParkedLines.Start(this, s);   // (no room: it stays where it was)
                return false;
            }
            NView!.ClaimOwnership();
            RodHolders.SaveRod(z, 0, null);
            z.Set("vdw_line", false);
            z.Set("vdw_ph", 0);
            _shownKey = "#";
            UpdateShownRod();
            // tackle left from a line that ended while it sat here
            var spare = z.GetString("vdw_spare", "");
            if (spare.Length > 0)
            {
                FishingController.GiveBack(player, ParkedLines.ParseSpare(spare));
                z.Set("vdw_spare", "");
            }
            if (s != null) FishingController.TakeOver(player, s, rod);
            return true;
        }
    }

    /// <summary>
    /// The lines left out in rod holders, ticked by the player who owns each holder (whoever set the rod in it, or
    /// whoever's nearest once they've gone): the same fishing as by hand, shared through the holder for everyone.
    /// </summary>
    internal static class ParkedLines
    {
        private sealed class Line { public RodHolder Holder = null!; public FishingSession S = null!; public float NextSave; public int Phase; }
        private static readonly Dictionary<RodHolder, Line> Lines = new();
        private static Line? _current;

        public static bool Has(RodHolder h) => Lines.ContainsKey(h);

        static ParkedLines() { FishingController.PrepaidEnded = OnEnded; }

        public static void Start(RodHolder h, FishingSession s)
        {
            Lines[h] = new Line { Holder = h, S = s };
            var z = h.Zdo; if (z == null) return;
            z.Set("vdw_line", true);
            Write(Lines[h], force: true);
        }

        /// <summary>The line on a holder being picked up: its cast, from this client's own tick or read back from the holder.</summary>
        public static FishingSession? Take(RodHolder h, Player player)
        {
            if (Lines.TryGetValue(h, out var line)) { Lines.Remove(h); return line.S; }
            var data = h.Zdo?.GetByteArray("vdw_sess");
            if (data == null || data.Length == 0) return null;
            return FishingController.Load(data, player, RodHolders.LoadRod(h.Zdo!, 0), h.Tip);
        }

        public static void HolderGone(RodHolder h)
        {
            if (Lines.TryGetValue(h, out var line)) { FishingController.DropVisuals(line.S); Lines.Remove(h); }
        }

        public static void Shutdown()
        {
            foreach (var l in Lines.Values) FishingController.DropVisuals(l.S);
            Lines.Clear();
        }

        /// <summary>Every frame (before the hand fishing): each holder's line this client owns is fished.</summary>
        public static void Update(Player player)
        {
            foreach (var h in RodHolder.All.ToList())
            {
                if (h == null || h.NView == null || !h.NView.IsValid()) continue;
                bool owner = h.NView.IsOwner();
                bool lineOut = h.LineOut && h.HasRod;
                if (!owner || !lineOut)
                {
                    // someone else has it now, or it was taken up: drop what this client drew of it
                    if (Lines.TryGetValue(h, out var gone)) { FishingController.DropVisuals(gone.S); Lines.Remove(h); }
                    continue;
                }
                if (!Lines.TryGetValue(h, out var line))
                {
                    // a line left out while this client wasn't fishing it (set by someone who's gone, or from before)
                    var data = h.Zdo!.GetByteArray("vdw_sess");
                    var s = data != null && data.Length > 0 ? FishingController.Load(data, player, RodHolders.LoadRod(h.Zdo!, 0), h.Tip) : null;
                    if (s == null) { h.Zdo!.Set("vdw_line", false); continue; }
                    Lines[h] = line = new Line { Holder = h, S = s };
                }
                _current = line;
                bool alive;
                try { alive = FishingController.TickParked(player, line.S, h.Tip); }
                finally { _current = null; }
                if (!alive) { Lines.Remove(h); h.Zdo!.Set("vdw_line", false); h.Zdo!.Set("vdw_ph", 0); continue; }
                Write(line, force: false);
            }
        }

        /// <summary>After the rods have been posed: the line from each holder's rod tip to its float.</summary>
        public static void LateUpdate(Player player)
        {
            foreach (var l in Lines.Values)
                if (l.Holder != null) l.S.Bobber?.Refresh(player, l.Holder.Tip);
        }

        private static void Write(Line line, bool force)
        {
            var z = line.Holder.Zdo; if (z == null) return;
            var s = line.S;
            int phase = s.Phase == FishingPhase.Waiting ? 1 : s.Phase == FishingPhase.Bite ? 2 : 3;
            var player = Player.m_localPlayer;
            Vector3 end = player != null ? FishingController.LineEnd(player, s) : s.FloatPos;
            z.Set("vdw_end", end);
            z.Set("vdw_run", s.Running);
            if (phase != line.Phase || force)
            {
                line.Phase = phase;
                z.Set("vdw_ph", phase);
                z.Set("vdw_lure", s.Lure != null || s.Weight != null);
                z.Set("vdw_fish", phase == 3 ? s.Fish.Id + (s.Variant != 0 ? "#" + s.Variant : "") : "");
                z.Set("vdw_fsc", BossFish.ScaleFor(s.Fish.Id) * FishSize.ModelScale(s.Fish, s.FishWeight));
                line.NextSave = 0f;
            }
            if (Time.time >= line.NextSave)
            {
                line.NextSave = Time.time + 1f;
                z.Set("vdw_sess", FishingController.Save(s));
            }
        }

        /// <summary>A shared effect from the line being ticked (FishingFx, RodMotion): for everyone, through its holder.</summary>
        public static void Fx(FishFx kind, float arg)
        {
            var z = _current?.Holder?.Zdo; if (z == null) return;
            z.Set("vdw_fxk", (int)kind); z.Set("vdw_fxa", arg); z.Set("vdw_fxn", z.GetInt("vdw_fxn", 0) + 1);
        }

        /// <summary>A message from the line being ticked: shown by the holder to everyone near it.</summary>
        public static void Said(string text)
        {
            var z = _current?.Holder?.Zdo; if (z == null) return;
            z.Set("vdw_said", text); z.Set("vdw_saidn", z.GetInt("vdw_saidn", 0) + 1);
        }

        /// <summary>A line that ended on its holder: what's left of its tackle waits there for whoever takes the rod.</summary>
        private static void OnEnded(FishingSession s)
        {
            var z = _current?.Holder?.Zdo; if (z == null) return;
            var left = FishingController.PrepaidLeft(s);
            left.AddRange(ParseSpare(z.GetString("vdw_spare", "")));
            z.Set("vdw_spare", string.Join(";", left.GroupBy(x => x.prefab).Select(g => $"{g.Key}:{g.Sum(x => x.n)}")));
        }

        public static List<(string prefab, int n)> ParseSpare(string spare) =>
            spare.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries)
                 .Select(e => e.Split(':'))
                 .Where(p => p.Length == 2 && int.TryParse(p[1], out _))
                 .Select(p => (p[0], int.Parse(p[1]))).ToList();
    }

    /// <summary>The Rod Rack (see RodHolders): storage only, its rods shown standing in their sockets.</summary>
    internal sealed class RodRack : MonoBehaviour, Hoverable, Interactable
    {
        private const int Slots = 10;
        private const float SlotR = 0.30f, BaseH = 0.078f, LeanOut = 0.03f;
        private ZNetView? _nview;
        private readonly GameObject?[] _shown = new GameObject?[Slots];
        private readonly string[] _shownKey = new string[Slots];

        private ZDO? Zdo => _nview != null && _nview.IsValid() ? _nview.GetZDO() : null;

        private void Awake() { _nview = GetComponent<ZNetView>(); }

        private static Vector3 Out(int k) { float a = 2f * Mathf.PI * k / Slots; return new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)); }

        private void Update()
        {
            var z = Zdo; if (z == null) return;
            for (int k = 0; k < Slots; k++)
            {
                string key = z.GetString($"vdw_rodname_{k}", "") + "#" + z.GetInt($"vdw_rodq_{k}", 0);
                if (key == _shownKey[k]) continue;
                _shownKey[k] = key;
                if (_shown[k] != null) Destroy(_shown[k]);
                _shown[k] = null;
                var item = RodHolders.LoadRod(z, k);
                if (item == null) continue;
                var u = Out(k);
                var dir = (Vector3.up * Mathf.Cos(LeanOut) + u * Mathf.Sin(LeanOut)).normalized;
                _shown[k] = RodDisplay.Build(item, transform, u * SlotR + Vector3.up * BaseH, dir, u, out _);
            }
        }

        private bool Occupied(ZDO z, int k) => z.GetString($"vdw_rodname_{k}", "").Length > 0;

        /// <summary>The slot nearest to where you're looking: an empty one to put a rod in, a full one to take one out.</summary>
        private int Aimed(ZDO z, bool wantFull)
        {
            var cam = GameCamera.instance != null ? GameCamera.instance.transform : null;
            int best = -1; float bestD = float.MaxValue;
            for (int k = 0; k < Slots; k++)
            {
                if (Occupied(z, k) != wantFull) continue;
                Vector3 at = transform.TransformPoint(Out(k) * SlotR + Vector3.up * 0.7f);
                float d = cam != null ? Vector3.Cross(cam.forward, at - cam.position).magnitude : k;
                if (d < bestD) { bestD = d; best = k; }
            }
            return best;
        }

        public string GetHoverName() => Loc.Text(Loc.Token("vdw_piece_rod_rack", "Rod Rack"));
        public float GetHoverOffset() => 0f;

        public string GetHoverText()
        {
            var z = Zdo; if (z == null) return "";
            int n = Enumerable.Range(0, Slots).Count(k => Occupied(z, k));
            string use = $"[<color=yellow><b>{Loc.Text("$KEY_Use")}</b></color>]";
            var p = Player.m_localPlayer;
            bool rodInHand = p != null && ContentRegistry.IsRod(p.GetCurrentWeapon());
            int take = Aimed(z, true);
            string lines = $"{GetHoverName()} ({n}/{Slots})";
            if (rodInHand && n < Slots) lines += $"\n{use} Stand your rod in it";
            else if (take >= 0) lines += $"\n{use} Take the {RodHolders.RodName(RodHolders.LoadRod(z, take))}";
            return lines;
        }

        public bool Interact(Humanoid user, bool hold, bool alt)
        {
            if (hold || !(user is Player player) || player != Player.m_localPlayer) return false;
            var z = Zdo; if (z == null) return false;
            var held = player.GetCurrentWeapon();
            if (held != null && ContentRegistry.IsRod(held)) return Store(player, held);
            int k = Aimed(z, true);
            if (k < 0) { player.Message(MessageHud.MessageType.Center, "The rack is empty."); return false; }
            var rod = RodHolders.LoadRod(z, k);
            if (rod == null) return false;
            if (FishingController.HandSession != null) { player.Message(MessageHud.MessageType.Center, "Reel in your line first."); return false; }
            if (!RodHolders.GiveRodInHand(player, rod)) return false;
            _nview!.ClaimOwnership();
            RodHolders.SaveRod(z, k, null);
            return true;
        }

        public bool UseItem(Humanoid user, ItemDrop.ItemData item) =>
            user is Player player && player == Player.m_localPlayer && item != null && ContentRegistry.IsRod(item) && Store(player, item);

        private bool Store(Player player, ItemDrop.ItemData rod)
        {
            var z = Zdo!;
            if (FishingController.HandSession != null && player.GetCurrentWeapon() == rod)
            {
                player.Message(MessageHud.MessageType.Center, "Reel in first - or set the rod in a rod holder to leave its line out.");
                return false;
            }
            int k = Aimed(z, false);
            if (k < 0) { player.Message(MessageHud.MessageType.Center, "The rack is full."); return false; }
            _nview!.ClaimOwnership();
            RodHolders.TakeRodFrom(player, rod);
            RodHolders.SaveRod(z, k, rod);
            z.Set($"vdw_rodq_{k}", rod.m_quality);
            return true;
        }
    }
}
