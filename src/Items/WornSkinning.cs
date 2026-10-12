using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Turns a rigid model worn on the body (the pearl belt, the rune necklace) into a skinned mesh on the wearer's own
    /// skeleton, so it bends with the body the way Valheim's belts and armour do. Valheim's own skinned equipment is
    /// authored against its exact skeleton; ours is skinned when it's put on instead:
    /// - the model, placed where it's worn in the skeleton's rest pose, is brought into the body mesh's space, so the body's
    ///   own bind poses fit it;
    /// - each vertex takes its bone weights from the nearest points of the body under it (only body parts near where the
    ///   relic is worn count, so a belt never follows a hand); if the body mesh can't be read, from how close it is to
    ///   those bones instead.
    /// The result is cached per model, fit and body mesh, so it's worked out once.
    /// </summary>
    internal static class WornSkinning
    {
        private const int Neighbours = 4;

        private static readonly Dictionary<string, List<(Mesh mesh, Material[] mats)>> Cache = new();
        private static readonly HashSet<string> Logged = new();

        /// <summary>
        /// Builds the skinned copy of <paramref name="model"/> (already placed where it's worn, in the rest pose, with no
        /// parent) on <paramref name="body"/>'s bones, weighted to <paramref name="bones"/>. Null if it can't.
        /// </summary>
        public static GameObject? Skin(SkinnedMeshRenderer body, GameObject model, string key, string[] bones, string rigidBone, float strength)
        {
            if (body.sharedMesh == null || body.bones == null || body.bones.Length == 0) return null;
            var allowed = new HashSet<int>();
            for (int i = 0; i < body.bones.Length; i++)
                if (body.bones[i] != null && bones.Contains(body.bones[i].name)) allowed.Add(i);
            if (allowed.Count == 0) return null;

            string cacheKey = key + "|" + body.sharedMesh.GetInstanceID();
            if (!Cache.TryGetValue(cacheKey, out var parts))
            {
                int rigid = System.Array.FindIndex(body.bones, b => b != null && b.name == rigidBone);
                parts = Build(body, model, allowed, rigid, Mathf.Clamp01(strength), out string source);
                if (parts.Count == 0) return null;
                Cache[cacheKey] = parts;
                if (Logged.Add(key.Split('|')[0] + source))
                    Plugin.Log.LogInfo($"Worn relic: {key.Split('|')[0]} skinned to the body ({parts.Sum(p => p.mesh.vertexCount)} vertices, weights {source}).");
            }

            // Where Valheim puts its own skinned equipment: beside the body, on the body's bones.
            var go = new GameObject(model.name + "_skinned");
            go.layer = body.gameObject.layer;
            go.transform.SetParent(body.transform.parent, false);
            go.transform.localPosition = body.transform.localPosition;
            go.transform.localRotation = body.transform.localRotation;
            go.transform.localScale = body.transform.localScale;
            foreach (var (mesh, mats) in parts)
            {
                var child = new GameObject("part");
                child.layer = go.layer;
                child.transform.SetParent(go.transform, false);
                var smr = child.AddComponent<SkinnedMeshRenderer>();
                smr.sharedMesh = mesh;
                smr.sharedMaterials = mats;
                smr.bones = body.bones;
                smr.rootBone = body.rootBone;
                smr.localBounds = body.localBounds;
                smr.shadowCastingMode = body.shadowCastingMode;
            }
            return go;
        }

        private static List<(Mesh, Material[])> Build(SkinnedMeshRenderer body, GameObject model, HashSet<int> allowed, int rigid, float strength, out string source)
        {
            var parts = new List<(Mesh, Material[])>();
            var bind = body.sharedMesh.bindposes;
            var toBody = body.transform.worldToLocalMatrix;

            // The body's points and weights near where the relic is worn, if the body mesh can be read.
            List<Vector3>? bodyPts = null;
            List<BoneWeight>? bodyWts = null;
            if (body.sharedMesh.isReadable)
            {
                var verts = body.sharedMesh.vertices;
                var weights = body.sharedMesh.boneWeights;
                if (weights.Length == verts.Length)
                {
                    bodyPts = new List<Vector3>(); bodyWts = new List<BoneWeight>();
                    for (int i = 0; i < verts.Length; i++)
                        if (allowed.Contains(weights[i].boneIndex0)) { bodyPts.Add(verts[i]); bodyWts.Add(weights[i]); }
                    if (bodyPts.Count < Neighbours) bodyPts = null;
                }
            }
            source = bodyPts != null ? "from the body mesh" : "by distance to the bones";

            // Otherwise: each allowed bone as a line from its rest position to its child's (in the body mesh's space).
            var segments = new List<(int bone, Vector3 a, Vector3 b)>();
            if (bodyPts == null)
                foreach (int i in allowed)
                {
                    if (i >= bind.Length) continue;
                    Vector3 a = bind[i].inverse.GetColumn(3), b = a;
                    for (int j = 0; j < body.bones.Length && j < bind.Length; j++)
                        if (body.bones[j] != null && body.bones[j].parent == body.bones[i]) { b = bind[j].inverse.GetColumn(3); break; }
                    segments.Add((i, a, b));
                }

            foreach (var mf in model.GetComponentsInChildren<MeshFilter>(true))
            {
                var src = mf.sharedMesh;
                var mr = mf.GetComponent<MeshRenderer>();
                if (src == null || mr == null || !src.isReadable) continue;
                var m = toBody * mf.transform.localToWorldMatrix;   // model space, as worn in the rest pose, to body space
                var n = m.inverse.transpose;

                var verts = src.vertices;
                var outV = new Vector3[verts.Length];
                for (int i = 0; i < verts.Length; i++) outV[i] = m.MultiplyPoint3x4(verts[i]);
                var mesh = new Mesh { name = src.name + "_skinned" };
                if (verts.Length > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                mesh.vertices = outV;
                var normals = src.normals;
                if (normals.Length == verts.Length) mesh.normals = normals.Select(v => n.MultiplyVector(v).normalized).ToArray();
                var tangents = src.tangents;
                if (tangents.Length == verts.Length)
                    mesh.tangents = tangents.Select(t => { Vector3 d = m.MultiplyVector(t).normalized; return new Vector4(d.x, d.y, d.z, t.w); }).ToArray();
                var uv = new List<Vector2>(); src.GetUVs(0, uv); if (uv.Count == verts.Length) mesh.SetUVs(0, uv);
                var uv2 = new List<Vector2>(); src.GetUVs(1, uv2); if (uv2.Count == verts.Length) mesh.SetUVs(1, uv2);
                var colors = src.colors; if (colors.Length == verts.Length) mesh.colors = colors;
                mesh.subMeshCount = src.subMeshCount;
                for (int s = 0; s < src.subMeshCount; s++) mesh.SetTriangles(src.GetTriangles(s), s);

                var raw = new BoneWeight[verts.Length];
                for (int i = 0; i < verts.Length; i++)
                    raw[i] = bodyPts != null ? FromBody(outV[i], bodyPts, bodyWts!) : FromBones(outV[i], segments);
                mesh.boneWeights = Soften(raw, outV, src.triangles, body.bones.Length, rigid, strength);
                mesh.bindposes = bind;
                mesh.RecalculateBounds();
                parts.Add((mesh, mr.sharedMaterials));
            }
            return parts;
        }

        /// <summary>
        /// Evens the weights out over the model's surface so neighbouring vertices move together (picked one by one from
        /// the body, a vertex here and there could follow a different bone and pull out of shape): each is averaged with
        /// the vertices it shares an edge with, several times over (vertices split at UV seams count as one). Then the
        /// skinning is eased by <paramref name="strength"/> toward moving rigidly with one bone (1: fully skinned).
        /// </summary>
        internal static BoneWeight[] Soften(BoneWeight[] raw, Vector3[] pos, int[] tris, int boneCount, int rigid, float strength, int passes = 8)
        {
            int n = raw.Length;
            // one id per position, so a seam doesn't split the smoothing
            var ids = new int[n];
            var byPos = new Dictionary<Vector3Int, int>();
            for (int i = 0; i < n; i++)
            {
                var k = Vector3Int.RoundToInt(pos[i] * 2000f);   // half a millimetre
                if (!byPos.TryGetValue(k, out int id)) byPos[k] = id = byPos.Count;
                ids[i] = id;
            }
            int m = byPos.Count;
            var w = new float[m, boneCount];
            var count = new int[m];
            for (int i = 0; i < n; i++)
            {
                int id = ids[i]; count[id]++;
                void Add(int b, float v) { if (b >= 0 && b < boneCount) w[id, b] += v; }
                Add(raw[i].boneIndex0, raw[i].weight0); Add(raw[i].boneIndex1, raw[i].weight1);
                Add(raw[i].boneIndex2, raw[i].weight2); Add(raw[i].boneIndex3, raw[i].weight3);
            }
            for (int id = 0; id < m; id++) for (int b = 0; b < boneCount; b++) w[id, b] /= Mathf.Max(1, count[id]);

            var nbrs = new HashSet<int>[m];
            for (int id = 0; id < m; id++) nbrs[id] = new HashSet<int>();
            for (int t = 0; t + 2 < tris.Length; t += 3)
                for (int e = 0; e < 3; e++)
                {
                    int p = ids[tris[t + e]], q = ids[tris[t + (e + 1) % 3]];
                    if (p != q) { nbrs[p].Add(q); nbrs[q].Add(p); }
                }

            var next = new float[m, boneCount];
            for (int pass = 0; pass < passes; pass++)
            {
                for (int id = 0; id < m; id++)
                {
                    int c = nbrs[id].Count;
                    for (int b = 0; b < boneCount; b++)
                    {
                        if (c == 0) { next[id, b] = w[id, b]; continue; }
                        float sum = 0f;
                        foreach (int o in nbrs[id]) sum += w[o, b];
                        next[id, b] = 0.5f * w[id, b] + 0.5f * sum / c;
                    }
                }
                (w, next) = (next, w);
            }

            var outW = new BoneWeight[n];
            var dict = new Dictionary<int, float>();
            for (int i = 0; i < n; i++)
            {
                dict.Clear();
                int id = ids[i];
                for (int b = 0; b < boneCount; b++)
                {
                    float v = w[id, b] * strength + (b == rigid ? 1f - strength : 0f);
                    if (v > 1e-4f) dict[b] = v;
                }
                outW[i] = Top4(dict);
            }
            return outW;
        }

        /// <summary>Blends the weights of the nearest body points, the nearest counting most.</summary>
        internal static BoneWeight FromBody(Vector3 p, List<Vector3> pts, List<BoneWeight> wts)
        {
            var best = new (float d, int i)[Neighbours];
            for (int k = 0; k < Neighbours; k++) best[k] = (float.MaxValue, -1);
            for (int i = 0; i < pts.Count; i++)
            {
                float d = (pts[i] - p).sqrMagnitude;
                if (d >= best[Neighbours - 1].d) continue;
                int k = Neighbours - 1;
                while (k > 0 && best[k - 1].d > d) { best[k] = best[k - 1]; k--; }
                best[k] = (d, i);
            }
            var sum = new Dictionary<int, float>();
            foreach (var (d, i) in best)
            {
                if (i < 0) continue;
                float f = 1f / (Mathf.Sqrt(d) + 0.005f);
                var w = wts[i];
                void Add(int bone, float weight) { if (weight > 0f) sum[bone] = (sum.TryGetValue(bone, out var v) ? v : 0f) + weight * f; }
                Add(w.boneIndex0, w.weight0); Add(w.boneIndex1, w.weight1); Add(w.boneIndex2, w.weight2); Add(w.boneIndex3, w.weight3);
            }
            return Top4(sum);
        }

        /// <summary>Weights by closeness to each bone's line, falling off steeply so the nearest bone leads.</summary>
        private static BoneWeight FromBones(Vector3 p, List<(int bone, Vector3 a, Vector3 b)> segments)
        {
            var sum = new Dictionary<int, float>();
            foreach (var (bone, a, b) in segments)
            {
                Vector3 ab = b - a;
                float t = ab.sqrMagnitude > 1e-8f ? Mathf.Clamp01(Vector3.Dot(p - a, ab) / ab.sqrMagnitude) : 0f;
                float d = (a + ab * t - p).magnitude;
                sum[bone] = 1f / Mathf.Pow(d + 0.02f, 4f);
            }
            return Top4(sum);
        }

        internal static BoneWeight Top4(Dictionary<int, float> sum)
        {
            var top = sum.OrderByDescending(kv => kv.Value).Take(4).ToArray();
            float total = top.Sum(kv => kv.Value);
            var w = new BoneWeight();
            if (top.Length == 0 || total <= 0f) return w;
            (int, float) At(int k) => k < top.Length ? (top[k].Key, top[k].Value / total) : (0, 0f);
            (w.boneIndex0, w.weight0) = At(0);
            (w.boneIndex1, w.weight1) = At(1);
            (w.boneIndex2, w.weight2) = At(2);
            (w.boneIndex3, w.weight3) = At(3);
            return w;
        }
    }
}
