using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Real holes in the ice. The Deep North's ice (the IceSheet and Icepond props) is a plain low-poly slab of readable
    /// mesh: under an Ice Hole that slab gets a copy of its mesh with a round hole cut out of its top and bottom faces,
    /// so the game's own water shows through it, as it does through a crack. Every game cuts its own copy from the holes
    /// it knows (they're synced objects), and the slab gets its own mesh back when the last hole in it is gone.
    /// The cut is made by splitting the faces that cross a hole's edge into small triangles and dropping the ones inside;
    /// its slightly ragged edge is hidden under the hole's own rim and wall (IceHole).
    /// </summary>
    internal static class IceCut
    {
        public const float Radius = 0.27f;          // the hole through the slab (the wall and rim sit just inside it)
        private const float MinEdge = 0.03f;        // faces crossing the hole's edge are split down to about this size
        private const int MaxDepth = 16;

        private static readonly Dictionary<MeshFilter, Mesh> Originals = new();

        /// <summary>
        /// Cuts every hole into the ice slabs round a point (a hole just made, or one gone). Returns whether a slab under
        /// the point was cut, with the slab's top and bottom there (world y).
        /// </summary>
        public static bool Refresh(Vector3 at, out float top, out float bottom)
        {
            top = bottom = at.y;
            bool found = false;
            foreach (var mf in IceMeshesNear(at))
            {
                try
                {
                    if (!Originals.TryGetValue(mf, out var original)) Originals[mf] = original = mf.sharedMesh;
                    if (original == null) continue;
                    if (!original.isReadable)
                    {
                        Plugin.Log.LogDebug($"Ice holes: '{mf.name}' ice isn't readable - the hole keeps its own water.");
                        continue;
                    }
                    var holes = IceHole.All.Where(h => h != null && h.isActiveAndEnabled).Select(h => h.transform.position)
                                           .Where(p => Inside(mf, p, Radius + 0.5f)).ToList();
                    if (holes.Count == 0)
                    {
                        if (mf.sharedMesh != original) { var cut = mf.sharedMesh; mf.sharedMesh = original; Object.Destroy(cut); }
                        Originals.Remove(mf);
                        continue;
                    }
                    if (!found && Surfaces(original, mf.transform, at, out float t, out float b)) { top = t; bottom = b; found = true; }
                    var made = Cut(original, mf.transform, holes);
                    if (mf.sharedMesh != original && mf.sharedMesh != null) Object.Destroy(mf.sharedMesh);
                    mf.sharedMesh = made;
                }
                catch (System.Exception ex) { Plugin.Log.LogWarning($"Ice holes: couldn't cut the ice ({ex.Message})."); }
            }
            foreach (var gone in Originals.Keys.Where(k => k == null).ToList()) Originals.Remove(gone);
            return found;
        }

        /// <summary>The ice slabs' meshes round a point: whatever ice collider is there, and the meshes of the prop it's on.</summary>
        private static IEnumerable<MeshFilter> IceMeshesNear(Vector3 at)
        {
            var seen = new HashSet<MeshFilter>();
            foreach (var c in Physics.OverlapSphere(at, 1.5f, ~0, QueryTriggerInteraction.Ignore))
            {
                if (c.GetComponentInParent<IceHole>() != null || !IceFishing.IsIce(c)) continue;   // (not the holes themselves)
                var root = c.GetComponentInParent<ZNetView>()?.transform ?? c.transform.root;
                foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
                    if (mf != null && mf.GetComponent<MeshRenderer>() != null && Inside(mf, at, Radius + 0.5f) && seen.Add(mf)) yield return mf;
            }
        }

        private static bool Inside(MeshFilter mf, Vector3 p, float margin)
        {
            var r = mf.GetComponent<Renderer>();
            if (r == null) return false;
            var b = r.bounds; b.Expand(new Vector3(margin * 2f, 4f, margin * 2f));
            return b.Contains(p);
        }

        /// <summary>The slab's top and bottom faces' heights under a point (world y), from its own (uncut) mesh.</summary>
        private static bool Surfaces(Mesh mesh, Transform tr, Vector3 at, out float top, out float bottom)
        {
            top = float.MinValue; bottom = float.MaxValue;
            var v = mesh.vertices; var tris = mesh.triangles;
            var p = tr.InverseTransformPoint(at);
            for (int i = 0; i < tris.Length; i += 3)
            {
                Vector3 a = v[tris[i]], b = v[tris[i + 1]], c = v[tris[i + 2]];
                var n = Vector3.Cross(b - a, c - a);
                if (Mathf.Abs(n.normalized.y) < 0.5f || !InTriangle(p, a, b, c)) continue;
                // the face's height at the point
                float y = a.y - (n.x * (p.x - a.x) + n.z * (p.z - a.z)) / n.y;
                float wy = tr.TransformPoint(new Vector3(p.x, y, p.z)).y;
                top = Mathf.Max(top, wy); bottom = Mathf.Min(bottom, wy);
            }
            if (top == float.MinValue) return false;
            if (bottom >= top - 0.02f) bottom = top - 0.3f;   // (only a top face: a slab drawn as a sheet)
            return true;
        }

        private static bool InTriangle(Vector3 p, Vector3 a, Vector3 b, Vector3 c)
        {
            float Side(Vector3 p1, Vector3 p2, Vector3 p3) => (p1.x - p3.x) * (p2.z - p3.z) - (p2.x - p3.x) * (p1.z - p3.z);
            float d1 = Side(p, a, b), d2 = Side(p, b, c), d3 = Side(p, c, a);
            bool neg = d1 < 0 || d2 < 0 || d3 < 0, pos = d1 > 0 || d2 > 0 || d3 > 0;
            return !(neg && pos);
        }

        // ------------------------------------------------------------------ the cut

        private sealed class Build
        {
            public readonly List<Vector3> Pos = new(), Nrm = new();
            public readonly List<Vector4> Tan = new();
            public readonly List<Vector2> Uv = new(), Uv2 = new();
            public readonly List<Color> Col = new();
            public bool HasN, HasT, HasUv, HasUv2, HasC;
            public readonly Dictionary<long, int> Mid = new();

            public int Add(Mesh m, int i, Vector3[] v, Vector3[] n, Vector4[] t, Vector2[] uv, Vector2[] uv2, Color[] c)
            {
                Pos.Add(v[i]);
                if (HasN) Nrm.Add(n[i]);
                if (HasT) Tan.Add(t[i]);
                if (HasUv) Uv.Add(uv[i]);
                if (HasUv2) Uv2.Add(uv2[i]);
                if (HasC) Col.Add(c[i]);
                return Pos.Count - 1;
            }

            /// <summary>The point half way along an edge (one per edge, shared by the faces on both sides).</summary>
            public int Middle(int a, int b)
            {
                long key = a < b ? ((long)a << 32) | (uint)b : ((long)b << 32) | (uint)a;
                if (Mid.TryGetValue(key, out int m)) return m;
                Pos.Add((Pos[a] + Pos[b]) * 0.5f);
                if (HasN) Nrm.Add((Nrm[a] + Nrm[b]).normalized);
                if (HasT) Tan.Add((Tan[a] + Tan[b]) * 0.5f);
                if (HasUv) Uv.Add((Uv[a] + Uv[b]) * 0.5f);
                if (HasUv2) Uv2.Add((Uv2[a] + Uv2[b]) * 0.5f);
                if (HasC) Col.Add((Col[a] + Col[b]) * 0.5f);
                return Mid[key] = Pos.Count - 1;
            }
        }

        private static Mesh Cut(Mesh src, Transform tr, List<Vector3> holesWorld)
        {
            var v = src.vertices; var n = src.normals; var t = src.tangents; var uv = src.uv; var uv2 = src.uv2; var c = src.colors;
            var bld = new Build { HasN = n.Length == v.Length, HasT = t.Length == v.Length, HasUv = uv.Length == v.Length, HasUv2 = uv2.Length == v.Length, HasC = c.Length == v.Length };
            for (int i = 0; i < v.Length; i++) bld.Add(src, i, v, n, t, uv, uv2, c);
            // the holes in the mesh's own space (round in the world: its scale across is taken as even)
            var s = tr.lossyScale;
            float r = Radius / Mathf.Max(1e-4f, (Mathf.Abs(s.x) + Mathf.Abs(s.z)) * 0.5f);
            float minEdge = MinEdge / Mathf.Max(1e-4f, (Mathf.Abs(s.x) + Mathf.Abs(s.z)) * 0.5f);
            var holes = holesWorld.Select(h => { var p = tr.InverseTransformPoint(h); return new Vector2(p.x, p.z); }).ToList();

            bool In(Vector3 p) { foreach (var h in holes) if ((new Vector2(p.x, p.z) - h).sqrMagnitude < r * r) return true; return false; }
            float SegDist(Vector2 p, Vector2 a, Vector2 b)
            {
                var ab = b - a; float k = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(1e-9f, ab.sqrMagnitude));
                return (a + ab * k - p).magnitude;
            }
            bool Touches(Vector3 a, Vector3 b, Vector3 cc)
            {
                foreach (var h in holes)
                {
                    var hp = new Vector3(h.x, 0f, h.y);
                    if (InTriangle(hp, a, b, cc)) return true;
                    Vector2 A = new(a.x, a.z), B = new(b.x, b.z), C = new(cc.x, cc.z);
                    if (SegDist(h, A, B) < r || SegDist(h, B, C) < r || SegDist(h, C, A) < r) return true;
                }
                return false;
            }

            var outSubs = new List<int[]>();
            for (int sm = 0; sm < src.subMeshCount; sm++)
            {
                var tris = src.GetTriangles(sm);
                var keep = new List<int>(tris.Length);
                void Tri(int a, int b, int cc, int depth)
                {
                    Vector3 pa = bld.Pos[a], pb = bld.Pos[b], pc = bld.Pos[cc];
                    var nrm = Vector3.Cross(pb - pa, pc - pa);
                    // the slab's sides, and faces nowhere near a hole, stay as they are
                    if (nrm.sqrMagnitude < 1e-12f || Mathf.Abs(nrm.normalized.y) < 0.5f || !Touches(pa, pb, pc)) { keep.Add(a); keep.Add(b); keep.Add(cc); return; }
                    if (In(pa) && In(pb) && In(pc)) return;   // wholly inside a hole: gone
                    float edge = Mathf.Max(Flat(pa - pb), Mathf.Max(Flat(pb - pc), Flat(pc - pa)));
                    if (edge < minEdge || depth >= MaxDepth)
                    {
                        if (!In((pa + pb + pc) / 3f)) { keep.Add(a); keep.Add(b); keep.Add(cc); }
                        return;
                    }
                    int ab = bld.Middle(a, b), bc = bld.Middle(b, cc), ca = bld.Middle(cc, a);
                    Tri(a, ab, ca, depth + 1); Tri(ab, b, bc, depth + 1); Tri(ca, bc, cc, depth + 1); Tri(ab, bc, ca, depth + 1);
                }
                for (int i = 0; i < tris.Length; i += 3) Tri(tris[i], tris[i + 1], tris[i + 2], 0);
                outSubs.Add(keep.ToArray());
            }

            var mesh = new Mesh { name = src.name + " (ice hole)" };
            if (bld.Pos.Count > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            mesh.SetVertices(bld.Pos);
            if (bld.HasN) mesh.SetNormals(bld.Nrm);
            if (bld.HasT) mesh.SetTangents(bld.Tan);
            if (bld.HasUv) mesh.SetUVs(0, bld.Uv);
            if (bld.HasUv2) mesh.SetUVs(1, bld.Uv2);
            if (bld.HasC) mesh.SetColors(bld.Col);
            mesh.subMeshCount = outSubs.Count;
            for (int i = 0; i < outSubs.Count; i++) mesh.SetTriangles(outSubs[i], i);
            if (!bld.HasN) mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        private static float Flat(Vector3 d) => Mathf.Sqrt(d.x * d.x + d.z * d.z);
    }
}
