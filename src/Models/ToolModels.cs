using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    internal static partial class CustomModels
    {
        /// <summary>
        /// A long tool's shape in its own mesh space: the tip of its point, the way from the point to the handle, the
        /// T-handle's direction across it, and its length.
        /// </summary>
        internal sealed class ToolShape { public Vector3 Point, Up, Cross; public float Length; }

        private static readonly Dictionary<string, ToolShape?> Shapes = new();

        /// <summary>
        /// Reads a long tool's shape from its model (the Ice Auger): the busy end, with most of the vertices, is the bit,
        /// and the T-handle lies along whichever cross axis spreads widest at the other end.
        /// </summary>
        internal static ToolShape? Shape(string key)
        {
            if (Shapes.TryGetValue(key, out var shape)) return shape;
            shape = null;
            if (TryGetCustom(key, out var mesh, out _))
            {
                var b = mesh.bounds; var size = b.size;
                int a = size.x >= size.y && size.x >= size.z ? 0 : size.y >= size.z ? 1 : 2;
                int c1 = (a + 1) % 3, c2 = (a + 2) % 3, cross = size[c1] >= size[c2] ? c1 : c2;
                float sign = 1f;
                try
                {
                    if (mesh.isReadable)
                    {
                        var verts = mesh.vertices;
                        float lo = b.min[a], len = Mathf.Max(0.0001f, size[a]);
                        int nLo = 0, nHi = 0;
                        foreach (var v in verts) { float t = (v[a] - lo) / len; if (t < 0.4f) nLo++; else if (t > 0.6f) nHi++; }
                        sign = nLo >= nHi ? 1f : -1f;   // up runs from the bit toward the handle
                        float e1 = 0f, e2 = 0f;
                        foreach (var v in verts)
                        {
                            float t = (v[a] - lo) / len;
                            if (sign > 0f ? t < 0.95f : t > 0.05f) continue;
                            e1 = Mathf.Max(e1, Mathf.Abs(v[c1] - b.center[c1])); e2 = Mathf.Max(e2, Mathf.Abs(v[c2] - b.center[c2]));
                        }
                        cross = e1 >= e2 ? c1 : c2;
                    }
                }
                catch { }
                Vector3 up = Vector3.zero, across = Vector3.zero; up[a] = sign; across[cross] = 1f;
                var point = b.center; point[a] = sign > 0f ? b.min[a] : b.max[a];
                shape = new ToolShape { Point = point, Up = up, Cross = across, Length = size[a] };
            }
            Shapes[key] = shape;
            return shape;
        }

        /// <summary>
        /// A long tool held like a spear, in the middle: laid along the vanilla spear it's cloned from (point toward the
        /// spear's head) at its own size, with the hand <paramref name="gripFromPoint"/> metres up from its point. Dropped,
        /// it lies centred where the spear would. The vanilla renderers are hidden.
        /// </summary>
        internal static bool ApplyHeldAt(GameObject prefab, string key, float gripFromPoint)
        {
            if (!TryGetCustom(key, out var mesh, out var mat) || !(Shape(key) is ToolShape shape)) return false;
            // a clone of a vanilla spear can come with the leister fitted onto it (SpearFishing): that goes, or it showed
            // alongside the tool
            foreach (var old in prefab.GetComponentsInChildren<Transform>(true).Where(t => t != null && t.name == "vdw_fitted").ToList())
                Object.DestroyImmediate(old.gameObject);
            var attach = prefab.transform.Find("attach");
            int fitted = 0;
            foreach (var vf in prefab.GetComponentsInChildren<MeshFilter>(true))
            {
                var vm = vf.sharedMesh; var vr = vf.GetComponent<MeshRenderer>();
                if (vm == null || vr == null || vf.name == "vdw_fitted") continue;
                var (va, vs, vp) = LongAxis(vm);
                var vb = vm.bounds;
                Vector3 head = Vector3.zero, flat = Vector3.zero; head[va] = vs; flat[vp] = 1f;
                var q = Quaternion.LookRotation(head, flat) * Quaternion.Inverse(Quaternion.LookRotation(-shape.Up, shape.Cross));
                bool held = attach != null && vf.transform.IsChildOf(attach);
                float k = (held ? attach!.lossyScale.x : 1f) / Mathf.Max(0.0001f, vf.transform.lossyScale.x);
                var ours = shape.Point + shape.Up * gripFromPoint;
                var grip = vb.center;
                if (held)
                {
                    var o = vf.transform.InverseTransformPoint(attach!.position);   // the hand, on the spear's line
                    grip = vb.center + head * Vector3.Dot(o - vb.center, head);
                }
                else ours = shape.Point + shape.Up * (shape.Length * 0.5f);
                var go = new GameObject("vdw_fitted");
                go.transform.SetParent(vf.transform, false);
                go.transform.localRotation = q;
                go.transform.localScale = Vector3.one * k;
                go.transform.localPosition = grip - q * (ours * k);
                go.layer = vf.gameObject.layer;
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterial = mat;
                vr.enabled = false;
                fitted++;
            }
            if (fitted > 0) Plugin.Log.LogInfo($"Custom models: '{key}' held at {gripFromPoint:0.##} m up from its point ({fitted} copies).");
            return fitted > 0;
        }
    }
}
