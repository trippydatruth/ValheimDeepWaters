using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal static partial class CustomModels
    {
        /// <summary>
        /// A buildable piece (a totem) with a model prefab in a bundle: the model is used whole, in place of the
        /// vanilla piece it was cloned from (a banner, with a pole, cloth and so on that a single mesh swap would
        /// scatter copies over). The vanilla visuals are hidden and its colliders replaced by a box around the model,
        /// so it's placed, hit and highlighted by its real shape.
        /// </summary>
        private static bool ApplyPieceModel(GameObject prefab, string baseName)
        {
            // Buildable pieces only: some vanilla items (the meads chum and potions are cloned from) carry a Piece too.
            if (prefab.GetComponent<Piece>() == null || prefab.GetComponent<ItemDrop>() != null) return false;
            var model = FindBundlePrefab(baseName, out var source);
            if (model == null || model.GetComponentInChildren<MeshFilter>(true) == null) return false;

            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true)) r.enabled = false;
            // The banner's cloth would keep simulating under the hidden flag (UnityEngine.Cloth, not referenced here).
            foreach (var cloth in prefab.GetComponentsInChildren<Component>(true).Where(c => c != null && c.GetType().Name == "Cloth"))
                cloth.GetType().GetProperty("enabled")?.SetValue(cloth, false);
            foreach (var col in prefab.GetComponentsInChildren<Collider>(true))
                if (!col.isTrigger) Object.DestroyImmediate(col);

            var go = Object.Instantiate(model, prefab.transform, false);
            go.name = "vdw_model";
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;
            go.transform.localScale = model.transform.localScale; // exactly as big as it is in Unity
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
            foreach (var rb in go.GetComponentsInChildren<Rigidbody>(true)) Object.DestroyImmediate(rb);
            foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = prefab.layer;

            // A box around the model, in the piece's own space.
            Bounds b = default;
            bool any = false;
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true).Where(m => m.sharedMesh != null))
            {
                var mb = mf.sharedMesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var corner = mb.center + Vector3.Scale(mb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                    var p = prefab.transform.InverseTransformPoint(mf.transform.TransformPoint(corner));
                    if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                }
            }
            if (any)
            {
                // Starts a little above the base: a box flush with the ground digs into any slope, and the build
                // ghost then shows "Invalid placement" everywhere.
                const float lift = 0.05f;
                float bottom = Mathf.Min(b.max.y - 0.05f, b.min.y + lift);
                var box = prefab.AddComponent<BoxCollider>();
                box.center = new Vector3(b.center.x, (bottom + b.max.y) / 2f, b.center.z);
                box.size = Vector3.Max(new Vector3(b.size.x, b.max.y - bottom, b.size.z), Vector3.one * 0.05f);
            }
            // Like vanilla statues and stones, it may sit into the ground.
            var piece = prefab.GetComponent<Piece>();
            piece.m_clipGround = true;
            Plugin.Log.LogDebug($"Custom models: '{baseName}' is a piece model (from '{source}'), {b.size.y:0.##} m tall.");
            return true;
        }

        /// <summary>
        /// An item whose bundle prefab is made of several meshes or materials (a chum bucket: bucket, liquid and fish),
        /// or any buff item: used whole, since the plain model path keeps only one mesh and material. The cloned item's own visuals are
        /// hidden; item stands get a copy under "attach" that only shows there.
        /// </summary>
        private static bool ApplyWholeItemModel(GameObject prefab, string baseName)
        {
            if (prefab.GetComponent<ItemDrop>() == null) return false;
            var model = FindBundlePrefab(baseName, out var source);
            if (model == null) return false;
            var renderers = model.GetComponentsInChildren<MeshRenderer>(true);
            if (renderers.Length == 0) return false;
            // Several parts, or a buff item (a mead bottle, a chum bucket) - its vanilla template (a mead) can hold more
            // than one mesh, which a plain mesh swap would fill with copies.
            bool several = renderers.Length > 1 || renderers.Sum(r => r.sharedMaterials.Length) > 1;
            if (!several && !baseName.StartsWith("buff_")) return false;

            var attach = prefab.transform.Find("attach");
            // The worn version (a belt's attach_skin) stays as it is.
            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true))
                if (!IsUnder(r.transform, prefab.transform, "attach_skin")) r.enabled = false;

            GameObject Place(Transform parent, string name)
            {
                var go = Object.Instantiate(model, parent, false);
                go.name = name;
                go.transform.localPosition = Vector3.zero;
                go.transform.localRotation = Quaternion.identity;
                go.transform.localScale = model.transform.localScale;
                foreach (var c in go.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
                foreach (var rb in go.GetComponentsInChildren<Rigidbody>(true)) Object.DestroyImmediate(rb);
                return go;
            }
            var live = Place(prefab.transform, "vdw_model");
            AddGarnish(live.transform, baseName);
            if (attach != null)
            {
                var still = Place(attach.Find("attachobj") ?? attach, "vdw_model_still");   // stands copy only attachobj when there is one
                AddGarnish(still.transform, baseName);
                foreach (var r in still.GetComponentsInChildren<Renderer>(true)) r.gameObject.AddComponent<StandOnlyModel>();
            }
            Plugin.Log.LogDebug($"Custom models: '{baseName}' is a whole model (from '{source}'), {renderers.Length} parts.");
            return true;
        }

        private static bool IsUnder(Transform t, Transform root, string name)
        {
            for (; t != null && t != root; t = t.parent)
                if (t.name == name) return true;
            return false;
        }

        // Vanilla items floating in a chum bucket, from its recipe: (prefab, x, y, height above the liquid, yaw, pitch,
        // roll, longest side in m). The bucket model (build_chum.py) is 0.40 m tall, liquid at 0.344 m, 0.16 m inner radius.
        private const float ChumLiquid = 0.344f;
        private static readonly System.Collections.Generic.Dictionary<string, (string prefab, float x, float y, float dz, float yaw, float pitch, float roll, float size)[]> Garnish = new()
        {
            ["buff_chum_basic"] = new[] { ("NeckTail", -0.07f, 0.06f, 0.012f, 30f, 15f, 70f, 0.13f), ("NeckTail", 0.08f, -0.03f, 0.015f, 200f, 25f, -60f, 0.12f), ("RawMeat", -0.02f, -0.08f, 0.01f, 110f, 10f, 20f, 0.11f) },
            ["buff_chum_blood"] = new[] { ("Entrails", -0.06f, -0.05f, 0.008f, 40f, 5f, 0f, 0.12f), ("Entrails", 0.07f, 0.02f, 0.01f, 250f, 10f, 15f, 0.11f), ("Bloodbag", -0.04f, 0.08f, 0.02f, 160f, 30f, 10f, 0.09f) },
            ["buff_chum_abyssal"] = new[] { ("Chitin", -0.07f, 0.04f, 0.012f, 20f, 20f, 40f, 0.10f), ("Chitin", 0.02f, -0.09f, 0.01f, 140f, 15f, -30f, 0.09f), ("Ooze", 0.09f, -0.02f, 0.008f, 0f, 0f, 0f, 0.07f), ("Ooze", -0.01f, 0.08f, 0.006f, 70f, 0f, 0f, 0.06f), ("Bloodbag", -0.09f, -0.06f, 0.015f, 300f, 35f, 0f, 0.08f) },
        };

        /// <summary>
        /// Copies the look (meshes and materials) of vanilla items into a bucket, each scaled to its size and floating
        /// at its spot. Anything the game doesn't have is skipped.
        /// </summary>
        private static void AddGarnish(Transform model, string baseName)
        {
            if (!Garnish.TryGetValue(baseName, out var list)) return;
            foreach (var g in list)
            {
                var src = Jotunn.Managers.PrefabManager.Instance.GetPrefab(g.prefab);
                if (src == null) continue;
                var holder = new GameObject("garnish_" + g.prefab);
                holder.transform.SetParent(model, false);
                var inner = new GameObject("look");
                inner.transform.SetParent(holder.transform, false);
                Bounds b = default; bool any = false;
                foreach (var mf in src.GetComponentsInChildren<MeshFilter>(true))
                {
                    var mr = mf.GetComponent<MeshRenderer>();
                    if (mf.sharedMesh == null || mr == null) continue;
                    // the item's "attach" copy (for hands and stands) would double it up
                    bool underAttach = false;
                    for (var t = mf.transform; t != null && t != src.transform; t = t.parent) if (t.name == "attach") underAttach = true;
                    if (underAttach) continue;
                    var part = new GameObject(mf.name);
                    part.transform.SetParent(inner.transform, false);
                    // where this mesh sits in the vanilla item, relative to the item's root
                    var m = src.transform.worldToLocalMatrix * mf.transform.localToWorldMatrix;
                    part.transform.localPosition = m.GetColumn(3);
                    part.transform.localRotation = m.rotation;
                    part.transform.localScale = m.lossyScale;
                    part.AddComponent<MeshFilter>().sharedMesh = mf.sharedMesh;
                    part.AddComponent<MeshRenderer>().sharedMaterials = mr.sharedMaterials;
                    var mb = mf.sharedMesh.bounds;
                    for (int i = 0; i < 8; i++)
                    {
                        var c = m.MultiplyPoint3x4(mb.center + Vector3.Scale(mb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1)));
                        if (!any) { b = new Bounds(c, Vector3.zero); any = true; } else b.Encapsulate(c);
                    }
                }
                if (!any) { Object.DestroyImmediate(holder); continue; }
                // centre it and scale its longest side to the size wanted
                float s = g.size / Mathf.Max(0.001f, Mathf.Max(b.size.x, Mathf.Max(b.size.y, b.size.z)));
                inner.transform.localPosition = -b.center * s;
                inner.transform.localScale = Vector3.one * s;
                holder.transform.localPosition = new Vector3(g.x, ChumLiquid + g.dz, g.y);
                holder.transform.localRotation = Quaternion.Euler(g.pitch, g.yaw, g.roll);
            }
        }
    }
}
