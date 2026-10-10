using HarmonyLib;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Makes dropped bait and fish lie naturally instead of balancing upright: each one is turned so its
    /// thinnest dimension points up (a fish rests on its side, a worm lies flat), with a yaw taken from its
    /// position so it looks scattered but stays the same across reloads.
    /// </summary>
    internal static class GroundPose
    {
        private static bool IsOurs(string name) =>
            name.StartsWith("VDW_Bait_") || name.StartsWith("VDW_Hook_") || name.StartsWith("VDW_Buff_") || name.StartsWith("VDW_Fish_") || name.StartsWith("VDW_CookedFish_");

        /// <summary>Called on registered prefabs: no on-land flopping for our fish, which could stand them on end.</summary>
        public static void PrepareFishPrefab(GameObject prefab)
        {
            var fish = prefab.GetComponent<global::Fish>();
            if (fish == null) return;
            fish.m_jumpOnLandChance = 0f;
            // Hover name while it's swimming (otherwise the vanilla fish it was cloned from).
            var drop = prefab.GetComponent<ItemDrop>();
            if (drop != null) fish.m_name = drop.m_itemData.m_shared.m_name;
        }

        /// <summary>
        /// Replaces the cloned vanilla item's solid colliders with a box fitted to the custom model, so
        /// physics settles the item on the model's real shape.
        /// </summary>
        public static void FitCollider(GameObject prefab)
        {
            if (!TryGetBounds(prefab.transform, out var bounds)) return;

            foreach (var col in prefab.GetComponentsInChildren<Collider>(true))
                if (!col.isTrigger) Object.DestroyImmediate(col);

            var box = prefab.AddComponent<BoxCollider>();
            box.center = bounds.center;
            box.size = Vector3.Max(bounds.size, Vector3.one * 0.03f);
        }

        private static void LayFlat(Transform t)
        {
            if (!TryGetBounds(t, out var bounds)) return;

            Vector3 size = bounds.size;
            Vector3 thinLocal = size.x <= size.y && size.x <= size.z ? Vector3.right
                              : size.y <= size.z ? Vector3.up
                              : Vector3.forward;

            Vector3 thinWorld = t.TransformDirection(thinLocal);
            if (Vector3.Dot(thinWorld, Vector3.up) < 0f) thinWorld = -thinWorld;

            Vector3 p = t.position;
            float yaw = Mathf.Repeat(p.x * 73.13f + p.z * 19.71f, 360f);
            t.rotation = Quaternion.AngleAxis(yaw, Vector3.up) * Quaternion.FromToRotation(thinWorld, Vector3.up) * t.rotation;
        }

        /// <summary>Combined bounds of all meshes under root, in root's local space.</summary>
        private static bool TryGetBounds(Transform root, out Bounds bounds)
        {
            Bounds result = default;
            bool any = false;

            void Add(Transform node, Bounds local)
            {
                for (int i = 0; i < 8; i++)
                {
                    var corner = local.center + Vector3.Scale(local.extents, new Vector3(
                        (i & 1) == 0 ? -1f : 1f, (i & 2) == 0 ? -1f : 1f, (i & 4) == 0 ? -1f : 1f));
                    var p = root.InverseTransformPoint(node.TransformPoint(corner));
                    if (!any) { result = new Bounds(p, Vector3.zero); any = true; }
                    else result.Encapsulate(p);
                }
            }

            // An animated model is the only thing showing: measure just it, in its rest pose. (The hidden vanilla mesh
            // and the upright item-stand copy under "attach" would skew the box and the way it lies.)
            var animated = root.Find("vdw_model");
            if (animated != null)
            {
                foreach (var smr in animated.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                    if (smr.sharedMesh != null) Add(smr.transform, smr.sharedMesh.bounds);
                foreach (var mf in animated.GetComponentsInChildren<MeshFilter>(true))   // static parts of it (a worm mound's soil)
                    if (mf.sharedMesh != null) Add(mf.transform, mf.sharedMesh.bounds);
                bounds = result;
                return any;
            }

            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
                if (mf.sharedMesh != null) Add(mf.transform, mf.sharedMesh.bounds);
            foreach (var smr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                Add(smr.transform, smr.localBounds);

            bounds = result;
            return any;
        }

        [HarmonyPatch(typeof(ItemDrop), "Awake")]
        private static class ItemDropAwakePatch
        {
            private static void Postfix(ItemDrop __instance)
            {
                if (!IsOurs(__instance.gameObject.name)) return;
                // A chum bucket stands upright (laid on its side it would spill).
                if (__instance.gameObject.name.Contains("_chum_")) return;
                // Fish spawned in the water swim upright on their own; only items on land get laid down.
                if (Floating.GetLiquidLevel(__instance.transform.position) > __instance.transform.position.y) return;
                LayFlat(__instance.transform);
            }
        }
    }
}
