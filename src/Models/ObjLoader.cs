using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Minimal runtime .obj parser: positions, UVs and faces (polygons fan-triangulated, negative indices
    /// supported). Normals are recalculated; materials, groups and everything else are ignored.
    /// </summary>
    internal static class ObjLoader
    {
        public static Mesh? Load(string path)
        {
            if (!File.Exists(path))
            {
                Plugin.Log.LogWarning($"ObjLoader: file not found: {path}");
                return null;
            }

            try
            {
                var positions = new List<Vector3>();
                var uvs = new List<Vector2>();

                var outVerts = new List<Vector3>();
                var outUvs = new List<Vector2>();
                var outTris = new List<int>();

                // Each unique position/UV pair becomes one Unity vertex, shared between faces that reuse it.
                var cache = new Dictionary<(int, int), int>();

                foreach (var rawLine in File.ReadLines(path))
                {
                    var line = rawLine.Trim();
                    if (line.Length == 0 || line[0] == '#') continue;

                    var parts = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length == 0) continue;

                    switch (parts[0])
                    {
                        case "v" when parts.Length >= 4:
                            positions.Add(new Vector3(
                                ParseFloat(parts[1]), ParseFloat(parts[2]), ParseFloat(parts[3])));
                            break;

                        case "vt" when parts.Length >= 3:
                            uvs.Add(new Vector2(ParseFloat(parts[1]), ParseFloat(parts[2])));
                            break;

                        case "f" when parts.Length >= 4:
                        {
                            // Fan-triangulate: (0,1,2), (0,2,3), (0,3,4), ...
                            int first = ResolveVertex(parts[1], positions, uvs, cache, outVerts, outUvs);
                            int prev = ResolveVertex(parts[2], positions, uvs, cache, outVerts, outUvs);
                            for (int i = 3; i < parts.Length; i++)
                            {
                                int curr = ResolveVertex(parts[i], positions, uvs, cache, outVerts, outUvs);
                                // Reversed winding: OBJ is counter-clockwise, Unity renders clockwise as front.
                                outTris.Add(first);
                                outTris.Add(curr);
                                outTris.Add(prev);
                                prev = curr;
                            }
                            break;
                        }
                    }
                }

                if (outVerts.Count == 0 || outTris.Count == 0)
                {
                    Plugin.Log.LogWarning($"ObjLoader: no usable geometry found in {path}.");
                    return null;
                }

                var mesh = new Mesh { name = Path.GetFileNameWithoutExtension(path) };
                if (outVerts.Count > 65000) mesh.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;

                mesh.SetVertices(outVerts);
                mesh.SetUVs(0, outUvs);
                mesh.SetTriangles(outTris, 0);
                mesh.RecalculateNormals();
                mesh.RecalculateBounds();
                return mesh;
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"ObjLoader: failed to parse {path} ({ex.Message}).");
                return null;
            }
        }

        private static int ResolveVertex(string token, List<Vector3> positions, List<Vector2> uvs,
            Dictionary<(int, int), int> cache, List<Vector3> outVerts, List<Vector2> outUvs)
        {
            // "v", "v/vt", "v/vt/vn", or "v//vn" - the normal index is ignored.
            var segs = token.Split('/');
            int vi = ResolveIndex(segs[0], positions.Count);
            int ti = segs.Length > 1 && segs[1].Length > 0 ? ResolveIndex(segs[1], uvs.Count) : -1;

            var key = (vi, ti);
            if (cache.TryGetValue(key, out int existing)) return existing;

            int idx = outVerts.Count;
            outVerts.Add(vi >= 0 && vi < positions.Count ? positions[vi] : Vector3.zero);
            outUvs.Add(ti >= 0 && ti < uvs.Count ? uvs[ti] : Vector2.zero);
            cache[key] = idx;
            return idx;
        }

        /// <summary>OBJ indices are 1-based; negative indices are relative to the current end of the list.</summary>
        private static int ResolveIndex(string s, int count)
        {
            int i = int.Parse(s, CultureInfo.InvariantCulture);
            return i < 0 ? count + i : i - 1;
        }

        private static float ParseFloat(string s) => float.Parse(s, CultureInfo.InvariantCulture);
    }
}
