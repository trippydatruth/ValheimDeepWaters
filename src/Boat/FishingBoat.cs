using HarmonyLib;
using Jotunn.Configs;
using Jotunn.Entities;
using Jotunn.Managers;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// The Fishing Boat: a one-man rowing boat built with the hammer. It's Valheim's raft underneath (so it floats,
    /// steers, carries players and saves like any ship) with the raft's logs, mast and sail hidden and the
    /// fishing_boat model (hull, oar.L, oar.R from build_boat.py) in their place. There's no sail: it's rowed, at
    /// the raft's paddling speeds only. The rower sits on the middle bench facing the stern and pulls both oars;
    /// the oars sweep through the stroke and the rower's arms and back follow the handles (FishingBoatOars).
    /// </summary>
    internal static class FishingBoat
    {
        public const string PrefabName = "VDW_FishingBoat";
        private const string ModelKey = "fishing_boat";

        // The model's measurements (build_boat.py, fishing_boat_rig.json), in metres in the model's own space:
        // X across (right), Y up from the keel, Z along (bow +Z), origin at the keel under the middle.
        internal const float Length = 3.97f, Beam = 1.63f, Height = 0.929f;   // 1.2x taller hull (build_boat.py VDW_ZSCALE 1.2)
        internal const float Waterline = 0.30f;       // how deep it sits
        internal const float BenchTop = 0.538f;       // the rowing bench's seat
        internal const float BenchToBow = 0.41f;      // bench centre, toward the bow from the oarlocks
        internal const float OarInboard = 0.51f;      // oarlock to the end of the handle
        internal const float SternSeatTop = 0.556f;   // the seat across the stern
        internal const float OarlockToSternSeat = 0.93f; // stern seat centre, toward the stern from the oarlocks
        internal const float BowDeckTop = 0.762f;     // the little deck in the bow (from 1.4 m forward)
        internal const float BowStandX = -0.16f, BowStandZ = 1.1f, BowFloor = 0.36f, BowStandTurn = 12f; // where you stand to hold fast in the bow
        // the rower's seat point in the boat's own frame (x right, y up from the keel, z toward the bow) and facing the
        // stern: fitted in game with vdw_debug boatseat (the seat pose sits about 0.36 m above its point)
        internal static readonly Vector3 RowerSeat = new Vector3(0f, 0.14f, -0.18f);
        internal const float PassengerDrop = 0.36f;   // the sitting pose sits this far above its seat point (feet on the floor)

        public static void Register()
        {
            var model = CustomModels.GetBundlePrefab(ModelKey);
            if (model == null)
            {
                Plugin.Log.LogInfo("Fishing Boat: no 'fishing_boat' model in the bundles; the boat isn't added.");
                return;
            }
            if (PrefabManager.Instance.GetPrefab("Raft") == null)
            {
                Plugin.Log.LogWarning("Fishing Boat: vanilla 'Raft' not found; the boat isn't added.");
                return;
            }

            var piece = new CustomPiece(PrefabName, "Raft", new PieceConfig
            {
                Name = Loc.Token("vdw_piece_fishing_boat", "Fishing Boat"),
                Description = Loc.Token("vdw_piece_fishing_boat_desc", "A small rowing boat for one angler. Sit on the bench and row."),
                PieceTable = "Hammer",
                Category = "Misc",
                CraftingStation = "piece_workbench",
                Requirements = new[]
                {
                    new RequirementConfig("Wood", 24, 0, true),
                    new RequirementConfig("Resin", 8, 0, true),
                    new RequirementConfig("DeerHide", 4, 0, true),
                }
            });
            if (!Build(piece.PiecePrefab, model)) return;
            ItemIcons.Apply(piece.PiecePrefab, ModelKey);
            PieceManager.Instance.AddPiece(piece);
            Plugin.Log.LogInfo("Fishing Boat added.");
        }

        private static bool Build(GameObject prefab, GameObject model)
        {
            var ship = prefab.GetComponent<Ship>();
            var controls = ship != null ? ship.m_shipControlls : null;
            if (ship == null || controls == null || ship.m_floatCollider == null)
            {
                Plugin.Log.LogWarning("Fishing Boat: the raft has no ship parts to build on; the boat isn't added.");
                return false;
            }
            var root = prefab.transform;
            var ladder = root.GetComponentsInChildren<Ladder>(true).FirstOrDefault();

            // The raft's own looks go: its logs, mast, ropes and sail (its water splashes and wake stay).
            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true))
                if (r is MeshRenderer || r is SkinnedMeshRenderer || r is LineRenderer) r.enabled = false;
            foreach (var mb in prefab.GetComponentsInChildren<MonoBehaviour>(true))
                if (mb.GetType().Name.StartsWith("Magica")) mb.enabled = false;            // the sail cloth
            // ...and its deck and the mast's holdfast seat: only the float box, triggers, the controls and the ladder stay.
            int layer = -1;
            foreach (var c in prefab.GetComponentsInChildren<Collider>(true))
            {
                if (c == ship.m_floatCollider || c.isTrigger || c.transform.IsChildOf(controls.transform) ||
                    (ladder != null && c.transform.IsChildOf(ladder.transform))) continue;
                if (layer < 0) layer = c.gameObject.layer;
                c.enabled = false;
            }
            if (layer < 0) layer = LayerMask.NameToLayer("vehicle");

            // The boat.
            var boat = Object.Instantiate(model, root, false);
            boat.name = "vdw_model";
            boat.transform.localPosition = Vector3.zero;
            boat.transform.localRotation = Quaternion.identity;
            foreach (var c in boat.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
            var wnt = prefab.GetComponent<WearNTear>();
            DressInShipPlanks(boat.transform);
            if (wnt != null)
            {
                wnt.m_new = wnt.m_worn = wnt.m_broken = boat;
                // Breaking it threw out the raft's logs and mast ("vfx_Destroyed_Raft"): this boat's planks and oars instead.
                wnt.m_destroyedEffect = WoodBreakEffect(wnt.m_destroyedEffect, boat.transform);
            }

            var oars = boat.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("oar.")).ToList();   // oar.L, oar.R (not the oarlocks)
            float oarlockZ = oars.Count > 0 ? oars.Average(t => t.localPosition.z) : -0.4f;
            float oarlockY = oars.Count > 0 ? oars.Average(t => t.localPosition.y) : 0.65f;
            float benchZ = oarlockZ + BenchToBow;

            // What you stand and sit on: a floor, the sides, bow and stern, and the bench.
            var cols = new GameObject("vdw_colliders"); cols.layer = layer;
            cols.transform.SetParent(root, false);
            void Box(string name, Vector3 centre, Vector3 size)
            {
                var go = new GameObject(name) { layer = layer };
                go.transform.SetParent(cols.transform, false);
                var b = go.AddComponent<BoxCollider>(); b.center = centre; b.size = size;
            }
            // the inside floor is 0.22 m up amidships, rising to 0.32 m toward the bow; a little deck in the bow at 0.635 m
            Box("floor", new Vector3(0, 0.17f, -0.1f), new Vector3(Beam * 0.72f, 0.2f, Length * 0.72f));
            Box("floor_bow", new Vector3(0, 0.25f, 1.15f), new Vector3(Beam * 0.42f, 0.2f, 0.5f));
            Box("bow_deck", new Vector3(0, BowDeckTop - 0.04f, 1.62f), new Vector3(Beam * 0.32f, 0.08f, 0.45f));
            Box("side_r", new Vector3(Beam * 0.47f, Height * 0.5f, 0), new Vector3(0.08f, Height, Length * 0.78f));
            Box("side_l", new Vector3(-Beam * 0.47f, Height * 0.5f, 0), new Vector3(0.08f, Height, Length * 0.78f));
            Box("bow", new Vector3(0, Height * 0.5f, Length * 0.44f), new Vector3(Beam * 0.45f, Height, 0.25f));
            Box("stern", new Vector3(0, Height * 0.5f, -Length * 0.46f), new Vector3(Beam * 0.6f, Height, 0.12f));
            Box("bench", new Vector3(0, BenchTop - 0.03f, benchZ), new Vector3(Beam * 0.85f, 0.06f, 0.32f));

            // Floating: the float box at the waterline, the hull's length and beam.
            var ft = ship.m_floatCollider.transform;
            ft.localPosition = new Vector3(0, Waterline, 0); ft.localRotation = Quaternion.identity; ft.localScale = Vector3.one;
            ship.m_floatCollider.center = Vector3.zero;
            ship.m_floatCollider.size = new Vector3(Beam * 0.9f, 0.5f, Length * 0.9f);
            // Valheim's buoyancy settles the centre of mass about 0.785 m below the water plus this offset (with the
            // raft's force 0.5 over 2 m); the centre of mass is put at the waterline (FishingBoatOars.Awake).
            ship.m_waterLevelOffset = 1.6f;   // where the self-trim settled in game (FishingBoatOars.FixedUpdate keeps it there)
            ship.m_stearForceOffset = -Length * 0.4f;
            ship.m_stearForce = 0.5f;
            ship.m_backwardForce = 1.1f;      // rowing (forward and back): 0.8 felt slow
            ship.m_hasSail = false;
            ship.m_sailForceFactor = 0f;      // no sail, so no wind (it only rows at Slow/Back anyway: RowingOnly)
            ship.m_rudderObject = null;
            foreach (var trig in prefab.GetComponentsInChildren<Collider>(true).Where(c => c.isTrigger && c is BoxCollider && c != ship.m_floatCollider))
            {
                // the onboard trigger: covers the hull and a body's height above it
                var bt = (BoxCollider)trig;
                trig.transform.localPosition = Vector3.zero; trig.transform.localRotation = Quaternion.identity; trig.transform.localScale = Vector3.one;
                bt.center = new Vector3(0, 1.2f, 0); bt.size = new Vector3(Beam, 2.4f, Length);
            }

            // The rower's seat: on the bench, facing the stern.
            var ct = controls.transform;
            ct.localPosition = new Vector3(0, BenchTop, benchZ);
            // The rower faces the stern and the passenger, as a rower sits (Valheim's turn-to-the-bow for whoever steers is
            // skipped on this boat: see KeepRowerFacing).
            ct.localRotation = Quaternion.LookRotation(Vector3.back, Vector3.up);
            if (controls.m_attachPoint != null)
            {
                controls.m_attachPoint.localPosition = Vector3.zero;   // placed on the boat in FishingBoatOars.Start
                controls.m_attachPoint.localRotation = Quaternion.identity;
            }
            controls.m_attachAnimation = "attach_sitship";
            controls.m_detachOffset = new Vector3(0, 0.5f, 0);
            controls.m_hoverText = Loc.Token("vdw_boat_row", "Row");
            foreach (var bc in ct.GetComponentsInChildren<BoxCollider>(true))
            {
                if (bc.isTrigger) continue;
                bc.transform.localPosition = Vector3.zero; bc.transform.localRotation = Quaternion.identity;
                // a generous box over the whole rowing seat, so looking anywhere at it shows "Row" - on the non-solid
                // piece layer, so it can be looked at and used but not bumped into
                bc.center = new Vector3(0, 0.45f, 0.1f); bc.size = new Vector3(Beam * 0.85f, 0.9f, 0.75f);
                int nonSolid = LayerMask.NameToLayer("piece_nonsolid");
                if (nonSolid >= 0) bc.gameObject.layer = nonSolid;
            }
            if (ship.m_controlGuiPos != null) ship.m_controlGuiPos.localPosition = new Vector3(0, BenchTop + 1.4f, benchZ);

            // A passenger's seat on the stern seat, facing the bow (and the rower).
            float sternZ = oarlockZ - OarlockToSternSeat;
            Box("stern_seat", new Vector3(0, SternSeatTop - 0.03f, sternZ), new Vector3(Beam * 0.55f, 0.06f, 0.38f));
            var seat = new GameObject("vdw_passenger_seat");
            seat.layer = ct.GetComponentsInChildren<Collider>(true).Select(c => c.gameObject.layer).DefaultIfEmpty(layer).First();
            seat.transform.SetParent(root, false);
            seat.transform.localPosition = new Vector3(0, SternSeatTop - PassengerDrop, sternZ);   // the pose sits above its point
            seat.transform.localRotation = Quaternion.LookRotation(Vector3.forward, Vector3.up);   // faces the rower
            var seatBox = seat.AddComponent<BoxCollider>();
            seatBox.center = new Vector3(0, 0.1f, 0); seatBox.size = new Vector3(Beam * 0.5f, 0.3f, 0.36f);
            var chair = seat.AddComponent<Chair>();
            chair.m_name = Loc.Token("vdw_boat_passenger", "Passenger seat");
            chair.m_attachPoint = seat.transform;
            chair.m_attachAnimation = "attach_sitship";
            chair.m_inShip = true;
            chair.m_detachOffset = new Vector3(0, 0.5f, 0);
            chair.m_useDistance = 2f;

            // A holdfast in the bow, like the Longship's at its dragon head: stand braced against the bow deck, facing
            // ahead, and you don't get thrown about in rough water.
            var hold = new GameObject("vdw_bow_holdfast") { layer = seat.layer };
            hold.transform.SetParent(root, false);
            // the front foot up on the bow deck, a little left of centre and turned slightly in
            hold.transform.localPosition = new Vector3(BowStandX, BowFloor, BowStandZ);
            hold.transform.localRotation = Quaternion.AngleAxis(BowStandTurn, Vector3.up);
            var holdBox = hold.AddComponent<BoxCollider>();
            holdBox.center = new Vector3(0, 0.6f, 0.15f); holdBox.size = new Vector3(Beam * 0.4f, 1.0f, 0.4f);
            var holdfast = hold.AddComponent<Chair>();
            holdfast.m_name = "$ship_holdfast";                 // Valheim's own name for it
            holdfast.m_attachPoint = hold.transform;
            holdfast.m_attachAnimation = "attach_dragon";      // the Longship's bow pose
            holdfast.m_inShip = true;
            holdfast.m_detachOffset = Vector3.zero;
            holdfast.m_useDistance = 2f;

            // Getting in from the water: the raft's (now unseen) ladder on the right side by the bench. Climbing it puts you
            // where its target is - still on the raft's layout (across the deck and behind), so it gets a new one: on the
            // floor just inside the gunwale, facing in.
            if (ladder != null)
            {
                ladder.transform.localPosition = new Vector3(Beam * 0.5f + 0.05f, 0.1f, benchZ - 0.6f);
                ladder.transform.localRotation = Quaternion.LookRotation(Vector3.left, Vector3.up);
                var step = new GameObject("vdw_ladder_target").transform;
                step.SetParent(root, false);
                step.localPosition = new Vector3(Beam * 0.18f, 0.3f, benchZ - 0.6f);
                step.localRotation = Quaternion.LookRotation(Vector3.left, Vector3.up);
                ladder.m_targetPos = step;
            }

            var rower = prefab.AddComponent<FishingBoatOars>();
            rower.Setup(boat.transform, oars, oarlockY, hold.transform);
            return true;
        }

        /// <summary>
        /// The raft's break effect with its debris swapped for this boat's: the raft's logs and mast flying apart became
        /// broken hull planks, plank shards and the two oars, which tumble and drift like the raft's did (its debris has
        /// the physics and clears itself away). Its sound stays, with a wood piece's splinter burst.
        /// </summary>
        private static EffectList WoodBreakEffect(EffectList? raft, Transform boat)
        {
            var keep = new List<EffectList.EffectData>();
            foreach (var e in raft?.m_effectPrefabs ?? new EffectList.EffectData[0])
            {
                if (e?.m_prefab == null) continue;
                if (!e.m_prefab.name.StartsWith("vfx_Destroyed_Raft")) { keep.Add(e); continue; }
                var wreck = Wreckage(boat);
                if (wreck != null) keep.Add(new EffectList.EffectData { m_prefab = wreck, m_enabled = true });
            }
            var wall = PrefabManager.Instance.GetPrefab("wood_wall_half")?.GetComponent<WearNTear>();
            if (wall?.m_destroyedEffect?.m_effectPrefabs != null)
                keep.AddRange(wall.m_destroyedEffect.m_effectPrefabs.Where(e => e?.m_prefab != null && e.m_prefab.name.StartsWith("vfx")));
            return new EffectList { m_effectPrefabs = keep.ToArray() };
        }

        private const string WreckName = "vdw_vfx_Destroyed_FishingBoat";

        // what the raft's debris pieces become, in the order they come (4 logs, 3 split logs, the mast and its boom): a
        // length of plank (metres, along the piece) or an oar
        private static readonly float[] WreckPlanks = { 1.6f, 1.3f, 1.1f, 0.9f, 0.6f, 0.45f, 0.35f };

        private static GameObject? Wreckage(Transform boat)
        {
            var existing = PrefabManager.Instance.GetPrefab(WreckName);
            if (existing != null) return existing;
            var wreck = PrefabManager.Instance.CreateClonedPrefab(WreckName, "vfx_Destroyed_Raft");
            if (wreck == null) return null;

            var oarParts = boat.GetComponentsInChildren<MeshFilter>(true).Where(f => f.name.StartsWith("oar.") && f.sharedMesh != null).ToList();
            var planks = boat.GetComponentsInChildren<Renderer>(true).FirstOrDefault(r => r.name == "hull")?.sharedMaterial;
            var cubeGo = GameObject.CreatePrimitive(PrimitiveType.Cube);
            var cube = cubeGo.GetComponent<MeshFilter>().sharedMesh;
            Object.DestroyImmediate(cubeGo);

            int plank = 0, oar = 0;
            var pieces = wreck.GetComponentsInChildren<MeshFilter>(true).Where(f => f.GetComponent<Rigidbody>() != null || f.GetComponentInParent<Rigidbody>() != null).ToList();
            foreach (var f in pieces)
            {
                var t = f.transform;
                var r = f.GetComponent<MeshRenderer>();
                foreach (var c in f.GetComponents<Collider>()) Object.DestroyImmediate(c);
                t.localPosition *= 0.55f;                       // the raft spread wider than this little boat
                t.localScale = Vector3.one;
                bool isOar = plank >= WreckPlanks.Length && oar < oarParts.Count;
                if (isOar)
                {
                    var src = oarParts[oar++];
                    f.sharedMesh = src.sharedMesh;
                    if (r != null) r.sharedMaterials = src.GetComponent<Renderer>()?.sharedMaterials ?? r.sharedMaterials;
                }
                else if (plank < WreckPlanks.Length)
                {
                    // a broken plank: about a hand wide and two fingers thick, along the piece
                    float len = WreckPlanks[plank++];
                    f.sharedMesh = cube;
                    t.localScale = new Vector3(0.17f, 0.03f, len);
                    if (r != null && planks != null) r.sharedMaterials = new[] { planks };
                }
                else
                {
                    Object.DestroyImmediate(f.gameObject);
                    continue;
                }
                var box = f.gameObject.AddComponent<BoxCollider>();
                box.center = f.sharedMesh.bounds.center; box.size = f.sharedMesh.bounds.size;
                var rb = f.GetComponent<Rigidbody>();
                if (rb != null) rb.mass = isOar ? 3f : 2f;
            }
            Plugin.Log.LogInfo($"Fishing Boat: wreckage of {plank} planks and {oar} oars.");
            return wreck;
        }

        // The hull is unwrapped in metres (build_boat.py VDW_PLANKS): this many plank tiles per metre along the boat
        // and up/around it.
        private static readonly Vector2 PlankTiling = new Vector2(0.4f, 0.7f);

        /// <summary>
        /// The hull wears Valheim's own ship planks (the Longship's / Karve's tiling "worn_shipplank" material, with the
        /// game's full textures), the oarlocks dark iron. Without it the bundle's stand-in planks stay.
        /// </summary>
        private static void DressInShipPlanks(Transform boat)
        {
            Material? planks = null;
            foreach (var ship in new[] { "VikingShip", "Karve" })
            {
                var go = PrefabManager.Instance.GetPrefab(ship);
                planks = go?.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials)
                    .FirstOrDefault(m => m != null && m.name.StartsWith("worn_shipplank"));
                if (planks != null) break;
            }
            if (planks == null)
            {
                Plugin.Log.LogInfo("Fishing Boat: Valheim's ship planks weren't found; the hull keeps its own planks.");
                return;
            }

            var wood = new Material(planks) { name = "VDW_BoatPlanks" };
            Vector2 vanillaScale = wood.mainTextureScale;
            foreach (var prop in wood.GetTexturePropertyNames())
                if (wood.GetTexture(prop) != null && wood.GetTextureScale(prop) == vanillaScale)
                {
                    wood.SetTextureScale(prop, PlankTiling);
                    wood.SetTextureOffset(prop, Vector2.zero);
                }
            var iron = new Material(planks) { name = "VDW_BoatIron", mainTexture = Texture2D.whiteTexture };
            if (iron.HasProperty("_Color")) iron.SetColor("_Color", new Color(0.13f, 0.13f, 0.14f));

            foreach (var r in boat.GetComponentsInChildren<Renderer>(true))
            {
                var use = r.name == "hull" ? wood : r.name.StartsWith("oarlocks") ? iron : null;
                if (use != null) r.sharedMaterials = Enumerable.Repeat(use, r.sharedMaterials.Length).ToArray();
            }
            Plugin.Log.LogInfo($"Fishing Boat: hull in Valheim's ship planks ({planks.shader.name}, vanilla tiling {vanillaScale}).");
        }

        /// <summary>
        /// Valheim turns whoever steers a ship toward its bow every frame, while their seat snaps them back to face where
        /// it points: on this boat that left the rower facing forward and shaking. Here the rower keeps the seat's facing
        /// (the stern); the controls still stop if they become invalid.
        /// </summary>
        [HarmonyPatch(typeof(Player), "UpdateDoodadControls")]
        private static class KeepRowerFacing
        {
            private static readonly System.Reflection.FieldInfo? Controller = AccessTools.Field(typeof(Player), "m_doodadController");

            private static bool Prefix(Player __instance)
            {
                if (!(Controller?.GetValue(__instance) is ShipControlls sc) || sc.m_ship == null || sc.m_ship.GetComponent<FishingBoatOars>() == null) return true;
                if (!sc.IsValid()) __instance.StopDoodadControl();
                return false;
            }
        }

        /// <summary>
        /// Valheim also turns a character toward the way they're walking - and rowing with W counts as walking - even when
        /// they're seated, while the seat snaps them back each physics step: the rower spun toward the bow and shook while
        /// rowing. Anyone seated on this boat (rower, passenger, bow holdfast) keeps their seat's facing.
        /// </summary>
        [HarmonyPatch(typeof(Character), "UpdateRotation")]
        private static class SeatedStayPut
        {
            private static readonly System.Reflection.FieldInfo? AttachPoint = AccessTools.Field(typeof(Player), "m_attachPoint");

            private static bool Prefix(Character __instance, ref float __result)
            {
                if (!(__instance is Player p) || !p.IsAttached()) return true;
                if (!(AttachPoint?.GetValue(p) is Transform seat) || seat == null || seat.GetComponentInParent<FishingBoatOars>() == null) return true;
                __result = 0f;
                return false;
            }
        }

        private static readonly Dictionary<string, Vector4> SeatNudges = new Dictionary<string, Vector4>();

        /// <summary>
        /// vdw_debug boatseat: moves a seat (rower, passenger or holdfast) on every Fishing Boat loaded, in the boat's own
        /// frame (right, up, toward the bow, in metres) and turns it (degrees), to fit it by eye. Returns the running total
        /// since the game started, to be put into the build, or null for an unknown seat.
        /// </summary>
        internal static string? NudgeSeat(string which, Vector3 move, float turn)
        {
            which = which.ToLowerInvariant();
            if (which != "rower" && which != "passenger" && which != "holdfast") return null;
            int n = 0;
            foreach (var oars in Object.FindObjectsByType<FishingBoatOars>(FindObjectsSortMode.None))
            {
                var root = oars.transform;
                Transform? seat = which == "rower" ? oars.GetComponent<Ship>()?.m_shipControlls?.m_attachPoint
                                : root.Find(which == "passenger" ? "vdw_passenger_seat" : "vdw_bow_holdfast");
                if (seat == null) continue;
                seat.position += root.TransformDirection(move);
                seat.rotation = Quaternion.AngleAxis(turn, root.up) * seat.rotation;
                n++;
            }
            SeatNudges.TryGetValue(which, out var total);
            total += new Vector4(move.x, move.y, move.z, turn);
            SeatNudges[which] = total;
            string msg = $"{which} on {n} boat(s): moved in all {total.x:0.00} right, {total.y:0.00} up, {total.z:0.00} toward the bow, turned {total.w:0} degrees.";
            Plugin.Log.LogInfo("Fishing Boat seat: " + msg);
            return msg;
        }

        /// <summary>No sail to raise: Forward stops at rowing speed.</summary>
        [HarmonyPatch(typeof(Ship), nameof(Ship.Forward))]
        private static class RowingOnly
        {
            private static bool Prefix(Ship __instance)
            {
                if (__instance.GetComponent<FishingBoatOars>() == null) return true;
                var s = __instance.GetSpeedSetting();
                return s == Ship.Speed.Stop || s == Ship.Speed.Back;
            }
        }
    }

    /// <summary>
    /// Rows the Fishing Boat: both oars sweep through the stroke (blades in and pulling, then out, feathered and
    /// swung back) at the boat's speed setting, easing the inside oar to turn; the rower on the bench leans into each
    /// stroke and their hands stay on the handles. Runs on every client from the ship's synced speed, rudder and user.
    /// </summary>
    internal sealed class FishingBoatOars : MonoBehaviour
    {
        [SerializeField] private Transform? _model;
        [SerializeField] private Transform[] _oars = new Transform[0];
        [SerializeField] private Quaternion[] _rest = new Quaternion[0];
        [SerializeField] private float _oarlockY;
        [SerializeField] private Transform? _holdfast;

        private Ship? _ship;
        private float _phase, _row, _gripReach;

        // the stroke, in degrees: sweep toward the bow at the catch / toward the stern at the finish, blade pitch down
        // in the water / out of it, and the feather (blade turned flat) on the way back
        private const float Catch = 38f, Finish = 32f, PitchIn = 22f, PitchOut = 9f, Feather = 80f, Drive = 0.42f;

        public void Setup(Transform model, List<Transform> oars, float oarlockY, Transform holdfast)
        {
            _holdfast = holdfast;
            _model = model;
            _oars = oars.ToArray();
            _rest = oars.Select(o => o.localRotation).ToArray();
            _oarlockY = oarlockY;
        }

        private void Awake()
        {
            _ship = GetComponent<Ship>();
            var body = GetComponent<Rigidbody>();
            if (body != null) body.centerOfMass = new Vector3(0, FishingBoat.Waterline, 0);
            _gripReach = FishingBoat.OarInboard - 0.08f;
            _phase = Random.value;
        }

        /// <summary>
        /// The rower's seat is placed on each boat once it's in the world: the raft's controls don't keep where they were
        /// put on the prefab (in game they were back at the boat's origin, unturned), so the seat is set here in the
        /// boat's own frame.
        /// </summary>
        private void Start()
        {
            var seat = _ship?.m_shipControlls?.m_attachPoint;
            if (seat == null) return;
            seat.SetPositionAndRotation(transform.TransformPoint(FishingBoat.RowerSeat),
                                        transform.rotation * Quaternion.LookRotation(Vector3.back, Vector3.up));
        }

        private static readonly System.Reflection.FieldInfo? AttachPointField = AccessTools.Field(typeof(Player), "m_attachPoint");

        /// <summary>
        /// The boat is drawn smoothly between physics steps, but Valheim only puts a seated player on their seat on
        /// physics steps: on a moving boat they lagged and caught up every step (the rower shook, and their arms with the
        /// oars). Each frame, everyone seated here is put exactly on their seat as it's drawn, before their arms are posed.
        /// </summary>
        private Transform? _loggedSeat;

        /// <summary>Which way someone who sits down faces, in the boat's own terms, and where the stern seat and the bow are.</summary>
        private void LogSeat(Player p, Transform seat)
        {
            _loggedSeat = seat;
            var root = transform;
            Vector3 face = root.InverseTransformDirection(p.transform.forward);
            var stern = root.Find("vdw_passenger_seat");
            var hold = root.Find("vdw_bow_holdfast");
            string Fmt(Vector3 v) => $"({v.x:0.00}, {v.y:0.00}, {v.z:0.00})";
            Plugin.Log.LogInfo($"Fishing Boat: {p.GetPlayerName()} sat at '{seat.name}' (under '{seat.parent?.name}') at {Fmt(root.InverseTransformPoint(seat.position))}, " +
                $"facing {Fmt(face)} in the boat's frame; passenger seat at {(stern != null ? Fmt(stern.localPosition) : "?")}, " +
                $"holdfast at {(hold != null ? Fmt(hold.localPosition) : "?")}; controls turned {_ship?.m_shipControlls?.transform.localEulerAngles.y:0} degrees.");
        }

        private void SnapSeated()
        {
            foreach (var p in Player.GetAllPlayers())
            {
                if (p == null || !p.IsAttached()) continue;
                if (!(AttachPointField?.GetValue(p) is Transform seat) || seat == null || !seat.IsChildOf(transform)) continue;
                p.transform.SetPositionAndRotation(seat.position, seat.rotation);
                if (_loggedSeat != seat) LogSeat(p, seat);
            }
        }

        // Snapped in Update as well, before the camera and the animator run (whose LateUpdates may come before this
        // one's): the camera then follows the rower where they're drawn, not where the last physics step left them.
        private void Update() => SnapSeated();

        private void LateUpdate()
        {
            if (_ship == null || _model == null || _oars.Length == 0) return;
            SnapSeated();
            float dt = Time.deltaTime;
            var speed = _ship.GetSpeedSetting();
            bool back = speed == Ship.Speed.Back;
            bool rowing = speed != Ship.Speed.Stop && _ship.m_shipControlls != null && _ship.m_shipControlls.HaveValidUser();
            _row = Mathf.MoveTowards(_row, rowing ? 1f : 0f, dt * 1.5f);
            _phase = Mathf.Repeat(_phase + (back ? -0.6f : 0.75f) * dt * _row, 1f);
            float rudder = _ship.GetRudderValue();

            // where each hand goes, keyed by side (+1 right, -1 left)
            var grips = new Dictionary<int, Vector3>();
            float sweepNow = 0f;
            for (int i = 0; i < _oars.Length; i++)
            {
                var oar = _oars[i];
                int side = oar.localPosition.x >= 0 ? 1 : -1;
                // turning: ease the oar on the side you turn toward (rudder > 0 turns the bow right)
                float amp = 1f - 0.75f * Mathf.Clamp01(rudder * side * (back ? -1f : 1f));
                Stroke(_phase, out float sweep, out float pitch, out float feather);
                sweep *= amp * _row; feather *= _row;
                pitch = Mathf.Lerp(3f, pitch, _row);
                if (i == 0) sweepNow = sweep;

                float th = sweep * Mathf.Deg2Rad, ph = pitch * Mathf.Deg2Rad;
                var a = new Vector3(side * Mathf.Cos(th) * Mathf.Cos(ph), -Mathf.Sin(ph), Mathf.Sin(th) * Mathf.Cos(ph));
                var a0 = new Vector3(side, 0, 0);
                var up = Vector3.ProjectOnPlane(Vector3.up, a).normalized;
                var q = Quaternion.LookRotation(a, up) * Quaternion.Inverse(Quaternion.LookRotation(a0, Vector3.up));
                q = Quaternion.AngleAxis(feather * side, a) * q;
                oar.localRotation = q * _rest[i];
                grips[side] = _model.TransformPoint(oar.localPosition - a * _gripReach);
            }

            var rower = Rower();
            if (rower != null) PoseRower(rower, grips, sweepNow);
            PoseHoldfast();
        }

        /// <summary>
        /// Whoever holds fast in the bow keeps the Longship's braced stance, but with nothing to grip their arms hang down
        /// at their sides instead of reaching for a dragon head.
        /// </summary>
        private void PoseHoldfast()
        {
            if (_holdfast == null) return;
            var p = Player.GetClosestPlayer(_holdfast.position, 0.3f);
            if (p == null || !p.IsAttached()) return;
            BeginPose(p);
            try { PoseHoldfastArms(p); }
            finally { EndPose(p); }
        }

        private void PoseHoldfastArms(Player p)
        {
            foreach (var (prefix, side) in new[] { ("Left", -1), ("Right", 1) })
            {
                var upper = Bone(p, prefix + "Arm"); var lower = Bone(p, prefix + "ForeArm"); var hand = Bone(p, prefix + "Hand");
                if (upper == null || lower == null || hand == null) continue;
                var t = p.transform;
                // hands just in front of the thighs with a soft bend at the elbow (not locked straight)
                var target = upper.position - Vector3.up * 0.46f + t.right * (side * 0.09f) + t.forward * 0.08f;
                var pole = upper.position - Vector3.up * 0.3f - t.forward * 0.4f + t.right * (side * 0.15f);   // elbows back, a little out
                SolveArm(upper, lower, hand, target, pole);
                // the elbows stay where that puts them; from there the forearms just hang, a touch forward and out
                // so they clear the thighs
                Vector3 fore = hand.position - lower.position;
                Vector3 hang = -Vector3.up + t.forward * 0.12f + t.right * (side * 0.06f);
                if (fore.sqrMagnitude > 1e-6f) lower.rotation = Quaternion.FromToRotation(fore, hang) * lower.rotation;
                RelaxHand(p, prefix, lower, hand, t.forward);
                RelaxFingers(p, prefix);
            }
        }

        private static readonly string[] Fingers = { "Index", "Middle", "Ring", "Pinky", "Thumb" };

        /// <summary>
        /// The dragon-head stance clenches the fingers round the dragon's neck: they ease about halfway open, to a loose
        /// natural curl (fully open, flat as in the rest pose, looked stiff).
        /// </summary>
        private static void RelaxFingers(Player p, string prefix)
        {
            foreach (var f in Fingers)
                for (int j = 1; j <= 3; j++)
                {
                    var b = Bone(p, prefix + "Hand" + f + j);
                    if (b != null && RestLocal(p, b) is Quaternion rest)
                        b.localRotation = Quaternion.Slerp(b.localRotation, rest, f == "Thumb" ? 0.45f : 0.55f);
                }
        }

        private static readonly Dictionary<int, Dictionary<Transform, Quaternion>> RestPose = new();

        /// <summary>A bone's rotation in the character's rest pose (from the skin's bind poses), relative to its parent.</summary>
        private static Quaternion? RestLocal(Player p, Transform bone)
        {
            int id = p.GetInstanceID();
            if (!RestPose.TryGetValue(id, out var map))
            {
                map = new Dictionary<Transform, Quaternion>();
                var body = p.GetComponent<VisEquipment>()?.m_bodyModel;
                if (body != null && body.sharedMesh != null)
                {
                    var bones = body.bones; var bind = body.sharedMesh.bindposes;
                    var index = new Dictionary<Transform, int>();
                    for (int i = 0; i < bones.Length && i < bind.Length; i++) if (bones[i] != null) index[bones[i]] = i;
                    foreach (var kv in index)
                    {
                        var parent = kv.Key.parent;
                        if (parent == null || !index.TryGetValue(parent, out int pi)) continue;
                        // rest pose in mesh space is the inverse bind pose; local = parent^-1 * child
                        var local = bind[pi] * bind[kv.Value].inverse;
                        map[kv.Key] = local.rotation;
                    }
                }
                RestPose[id] = map;
            }
            return map.TryGetValue(bone, out var q) ? q : (Quaternion?)null;
        }

        /// <summary>
        /// The dragon-head stance grips with the wrist bent back; hanging at the side that looked wrong. The wrist is
        /// straightened in line with the forearm, then the hand turned about it so the thumb leads and the palm faces in.
        /// </summary>
        private static void RelaxHand(Player p, string prefix, Transform lower, Transform hand, Vector3 forward)
        {
            Vector3 arm = hand.position - lower.position;
            if (arm.sqrMagnitude < 1e-6f) return;
            arm.Normalize();
            var middle = Bone(p, prefix + "HandMiddle1");
            if (middle != null)
            {
                Vector3 fingers = middle.position - hand.position;
                if (fingers.sqrMagnitude > 1e-6f) hand.rotation = Quaternion.FromToRotation(fingers, arm) * hand.rotation;
            }
            var thumb = Bone(p, prefix + "HandThumb1");
            if (thumb != null)
            {
                Vector3 have = Vector3.ProjectOnPlane(thumb.position - hand.position, arm);
                Vector3 want = Vector3.ProjectOnPlane(forward, arm);
                if (have.sqrMagnitude > 1e-6f && want.sqrMagnitude > 1e-6f)
                    hand.rotation = Quaternion.AngleAxis(Vector3.SignedAngle(have, want, arm), arm) * hand.rotation;
            }
        }

        // ------------------------------------------------------------------ floating at the right height
        // Valheim's ship buoyancy settles the boat at a height set by m_waterLevelOffset; the boat trims that itself until
        // the water sits at the waterline (Waterline up the hull from the keel), whatever the physics make of the hull.
        private ZNetView? _nview;
        private WaterVolume? _water;
        private float _trimSince = -1f;
        private bool _trimLogged;

        // A small boat with its float points close together has little to keep it level, and standing on a side heeled it
        // right over. It now rights itself like a spring (about a one-second roll), damped so it settles, and still rocks
        // on the waves.
        private const float RightingStiffness = 40f, RightingDamping = 8f;
        private Rigidbody? _rb;

        private void KeepUpright()
        {
            if (_rb == null && (_rb = GetComponent<Rigidbody>()) == null) return;
            Vector3 tilt = Vector3.Cross(transform.up, Vector3.up);                     // axis * sin(heel)
            Vector3 spin = _rb.angularVelocity; spin -= Vector3.Project(spin, Vector3.up);   // roll and pitch only, not turning
            _rb.AddTorque(tilt * RightingStiffness - spin * RightingDamping, ForceMode.Acceleration);
        }

        private void FixedUpdate()
        {
            if (_ship == null) return;
            if (_nview == null) _nview = GetComponent<ZNetView>();
            if (_nview == null || !_nview.IsValid() || !_nview.IsOwner()) return;
            KeepUpright();
            if (Vector3.Dot(transform.up, Vector3.up) < 0.7f) return;                    // tipped over: no trimming
            float water = Floating.GetWaterLevel(transform.position, ref _water);
            float draft = water - transform.position.y;                                 // the root is at the keel
            if (draft < -1f || draft > 3f) return;                                    // out of the water, or sunk
            float error = draft - FishingBoat.Waterline;                                // > 0: sitting too deep
            _ship.m_waterLevelOffset = Mathf.Clamp(_ship.m_waterLevelOffset + error * 0.8f * Time.fixedDeltaTime, -2f, 4f);
            if (_trimSince < 0f) _trimSince = Time.time;
            if (!_trimLogged && Time.time - _trimSince > 20f)
            {
                _trimLogged = true;
                Plugin.Log.LogInfo($"Fishing Boat: trimmed to float at its waterline (water level offset {_ship.m_waterLevelOffset:0.000}, draft {draft:0.00} m).");
            }
        }

        /// <summary>Sweep, pitch and feather at a point in the stroke (0..1: the drive, then the recovery).</summary>
        private static void Stroke(float p, out float sweep, out float pitch, out float feather)
        {
            if (p < Drive)
            {
                float u = p / Drive;
                sweep = Mathf.Lerp(Catch, -Finish, Ease(u));
                float inWater = Mathf.Clamp01(u / 0.12f) * Mathf.Clamp01((1f - u) / 0.12f);
                pitch = Mathf.Lerp(PitchOut, PitchIn, inWater);
                feather = 0f;
            }
            else
            {
                float u = (p - Drive) / (1f - Drive);
                sweep = Mathf.Lerp(-Finish, Catch, Ease(u));
                pitch = PitchOut;
                feather = Feather * Mathf.Clamp01(u / 0.25f) * Mathf.Clamp01((0.9f - u) / 0.2f);
            }
        }

        private static float Ease(float u) => 0.5f - 0.5f * Mathf.Cos(u * Mathf.PI);

        private Player? Rower()
        {
            var controls = _ship!.m_shipControlls;
            if (controls == null || !controls.HaveValidUser()) return null;
            long user = controls.GetUser();
            foreach (var p in Player.GetAllPlayers())
                if (p != null && p.GetPlayerID() == user && p.IsAttached()) return p;
            return null;
        }

        // ------------------------------------------------------------------ the rower
        private static readonly Dictionary<int, Dictionary<string, Transform>> BoneCache = new();

        internal static Transform? Bone(Player p, string name)
        {
            int id = p.GetInstanceID();
            if (!BoneCache.TryGetValue(id, out var map))
            {
                map = new Dictionary<string, Transform>();
                var body = p.GetComponent<VisEquipment>()?.m_bodyModel;
                if (body != null)
                    foreach (var b in body.bones)
                        if (b != null && !map.ContainsKey(b.name)) map[b.name] = b;
                BoneCache[id] = map;
            }
            return map.TryGetValue(name, out var t) && t != null ? t : null;
        }

        // ------------------------------------------------------------------ posing on top of the animation
        // A character's animator runs on physics steps, not every frame: on the frames between, the bones still hold last
        // frame's pose with our changes on it, and turning them again from there stacked up (the rower shook while rowing,
        // a thumb trembled). Before posing, any bone the animator hasn't rewritten goes back to what it last gave.
        private static readonly string[] PosedBones = BuildPosedBones();
        private static readonly Dictionary<int, Dictionary<Transform, (Quaternion anim, Quaternion ours)>> Posed = new();

        private static string[] BuildPosedBones()
        {
            var names = new List<string> { "Spine1" };
            foreach (var side in new[] { "Left", "Right" })
            {
                names.Add(side + "Arm"); names.Add(side + "ForeArm"); names.Add(side + "Hand");
                foreach (var f in Fingers) for (int j = 1; j <= 3; j++) names.Add(side + "Hand" + f + j);
            }
            return names.ToArray();
        }

        /// <summary>Puts the player's posed bones back to the animator's pose for this frame, before posing them.</summary>
        internal static void BeginPose(Player p)
        {
            if (!Posed.TryGetValue(p.GetInstanceID(), out var map)) Posed[p.GetInstanceID()] = map = new();
            foreach (var name in PosedBones)
            {
                var b = Bone(p, name);
                if (b == null) continue;
                if (map.TryGetValue(b, out var was) && b.localRotation == was.ours) b.localRotation = was.anim;   // not re-animated
                map[b] = (b.localRotation, b.localRotation);
            }
        }

        /// <summary>Notes the pose as we left it, to tell next frame whether the animator has been since.</summary>
        internal static void EndPose(Player p)
        {
            if (!Posed.TryGetValue(p.GetInstanceID(), out var map)) return;
            foreach (var b in map.Keys.ToList())
                if (b != null) map[b] = (map[b].anim, b.localRotation);
        }

        private void PoseRower(Player p, Dictionary<int, Vector3> grips, float sweep)
        {
            BeginPose(p);
            try { PoseRowerArms(p, grips, sweep); }
            finally { EndPose(p); }
        }

        private void PoseRowerArms(Player p, Dictionary<int, Vector3> grips, float sweep)
        {
            // Lean into the stroke: forward (toward the stern, where they face) at the catch, back at the finish.
            float lean = Mathf.Lerp(-12f, 20f, Mathf.InverseLerp(-Finish, Catch, sweep)) * _row;
            var spine = Bone(p, "Spine1");
            if (spine != null) spine.rotation = Quaternion.AngleAxis(lean, p.transform.right) * spine.rotation;

            foreach (var (prefix, sideOfRower) in new[] { ("Left", -1), ("Right", 1) })
            {
                var upper = Bone(p, prefix + "Arm"); var lower = Bone(p, prefix + "ForeArm"); var hand = Bone(p, prefix + "Hand");
                if (upper == null || lower == null || hand == null) continue;
                // the oar on this hand's side of the rower
                Vector3 target = Vector3.zero; bool found = false;
                foreach (var g in grips)
                    if (Vector3.Dot(g.Value - p.transform.position, p.transform.right) * sideOfRower > 0) { target = g.Value; found = true; }
                if (!found) continue;
                // elbows out to the side and a little down
                var pole = upper.position + p.transform.right * (sideOfRower * 0.6f) - Vector3.up * 0.4f - p.transform.forward * 0.2f;
                SolveArm(upper, lower, hand, target, pole);
            }
        }

        /// <summary>Two-bone reach: turns the upper arm and forearm so the hand lands on the target, the elbow toward the pole.</summary>
        internal static void SolveArm(Transform upper, Transform lower, Transform hand, Vector3 target, Vector3 pole)
        {
            Vector3 a = upper.position, b = lower.position, c = hand.position;
            float la = (b - a).magnitude, lb = (c - b).magnitude;
            if (la < 1e-4f || lb < 1e-4f) return;
            Vector3 toTarget = target - a;
            float d = Mathf.Clamp(toTarget.magnitude, Mathf.Abs(la - lb) + 1e-3f, la + lb - 1e-3f);
            Vector3 dir = toTarget.normalized;
            float cosA = Mathf.Clamp((la * la + d * d - lb * lb) / (2f * la * d), -1f, 1f);
            Vector3 bend = Vector3.ProjectOnPlane(pole - a, dir);
            if (bend.sqrMagnitude < 1e-6f) bend = Vector3.ProjectOnPlane(Vector3.down, dir);
            Vector3 elbow = a + dir * (la * cosA) + bend.normalized * (la * Mathf.Sqrt(1f - cosA * cosA));
            upper.rotation = Quaternion.FromToRotation(b - a, elbow - a) * upper.rotation;
            b = lower.position; c = hand.position;
            lower.rotation = Quaternion.FromToRotation(c - b, a + dir * d - b) * lower.rotation;
        }
    }
}
