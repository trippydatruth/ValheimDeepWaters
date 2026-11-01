using System.Collections.Generic;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Gives a cooked fish the look of its raw fish, browned, matte and grill-marked: the model's texture and the icon
    /// are redrawn once at load (copied off the GPU, so the source textures don't need to be readable). The grill marks
    /// are laid across the fish's real shape - each texture pixel is traced back to where it sits on the mesh - so they
    /// run the same steep way on every species, whatever its texture layout.
    /// </summary>
    internal static class CookedLook
    {
        private static readonly Dictionary<(Material, Mesh?, int), Material> Done = new();
        private static readonly Color Brown = new(0.60f, 0.36f, 0.17f);
        private static readonly Color Char = new(0.13f, 0.07f, 0.03f);
        private const int MaxSize = 512;
        private const float BarsAlong = 9f;          // grill bars along the fish's length
        private const float BarAngle = 60f;          // degrees from the fish's long axis
        private const float BarWidth = 0.075f;       // of the gap between bars (tried on the trout and bass in Blender)

        /// <summary>Swaps every renderer's materials for browned, grill-marked copies.</summary>
        public static void ApplyToModel(GameObject prefab)
        {
            foreach (var r in prefab.GetComponentsInChildren<Renderer>(true))
            {
                if (r is ParticleSystemRenderer) continue;
                Mesh? mesh = r is SkinnedMeshRenderer smr ? smr.sharedMesh : r.GetComponent<MeshFilter>()?.sharedMesh;
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = Cooked(mats[i], mesh, i);
                r.sharedMaterials = mats;
            }
        }

        /// <summary>A browned, grill-marked copy of the icon (its transparent background kept).</summary>
        public static Sprite? Icon(Sprite? raw)
        {
            if (raw == null || raw.texture == null) return null;
            var tex = Grab(raw.texture, raw.texture.width);
            if (tex == null) return null;
            // on the picture: bars on its diagonal, as the fish lies across the icon
            var coord = new float[tex.width * tex.height];
            for (int y = 0; y < tex.height; y++)
                for (int x = 0; x < tex.width; x++)
                    coord[y * tex.width + x] = (x * 0.8f + y * 0.6f) / tex.width * 9f;
            Paint(tex, coord, skipClear: true);
            return Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f));
        }

        private static Material Cooked(Material src, Mesh? mesh, int sub)
        {
            if (src == null) return src!;
            var key = (src, mesh, sub);
            if (Done.TryGetValue(key, out var have)) return have;
            var m = new Material(src) { name = src.name + "_cooked" };
            if (src.mainTexture != null && Grab(src.mainTexture, MaxSize) is Texture2D tex)
            {
                Paint(tex, mesh != null ? BarCoords(mesh, sub, tex.width, tex.height) : null, skipClear: false);
                m.mainTexture = tex;
            }
            else m.color = src.color * Brown;
            // cooked skin is matte: no glow, and the raw fish's metal/gloss map (shiny wet scales) is dropped
            if (m.HasProperty("_EmissionColor")) m.SetColor("_EmissionColor", Color.black);
            m.DisableKeyword("_EMISSION");
            if (m.HasProperty("_MetallicGlossMap")) m.SetTexture("_MetallicGlossMap", null);
            m.DisableKeyword("_METALLICGLOSSMAP");
            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", 0f);
            if (m.HasProperty("_Glossiness")) m.SetFloat("_Glossiness", 0.18f);
            if (m.HasProperty("_GlossMapScale")) m.SetFloat("_GlossMapScale", 0.18f);
            Done[key] = m;
            return m;
        }

        /// <summary>
        /// For each texture pixel, where it falls between grill bars (whole numbers are bar centres), found by drawing
        /// the mesh's triangles into texture space. NaN where no triangle covers a pixel; null if the mesh can't be read.
        /// </summary>
        private static float[]? BarCoords(Mesh mesh, int sub, int w, int h)
        {
            if (!mesh.isReadable) return null;
            var verts = mesh.vertices; var uvs = mesh.uv;
            if (uvs == null || uvs.Length != verts.Length || verts.Length == 0) return null;
            var e = mesh.bounds.size;
            int along = e.x >= e.y && e.x >= e.z ? 0 : e.y >= e.z ? 1 : 2;
            int thin = e.x <= e.y && e.x <= e.z ? 0 : e.y <= e.z ? 1 : 2;
            if (thin == along) thin = (along + 1) % 3;
            int up = 3 - along - thin;
            float gap = Mathf.Max(e[along] / BarsAlong, 1e-4f);
            float ca = Mathf.Cos(BarAngle * Mathf.Deg2Rad), sa = Mathf.Sin(BarAngle * Mathf.Deg2Rad);
            var s = new float[verts.Length];
            for (int i = 0; i < verts.Length; i++) s[i] = (verts[i][along] * ca + verts[i][up] * sa) / gap;

            var coord = new float[w * h];
            for (int i = 0; i < coord.Length; i++) coord[i] = float.NaN;
            var tris = sub < mesh.subMeshCount ? mesh.GetTriangles(sub) : mesh.triangles;
            for (int t = 0; t + 2 < tris.Length; t += 3)
            {
                int i0 = tris[t], i1 = tris[t + 1], i2 = tris[t + 2];
                Vector2 a = Px(uvs[i0], w, h), b = Px(uvs[i1], w, h), c = Px(uvs[i2], w, h);
                float area = (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y);
                if (Mathf.Abs(area) < 1e-6f) continue;
                int x0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(a.x, Mathf.Min(b.x, c.x))));
                int x1 = Mathf.Min(w - 1, Mathf.CeilToInt(Mathf.Max(a.x, Mathf.Max(b.x, c.x))));
                int y0 = Mathf.Max(0, Mathf.FloorToInt(Mathf.Min(a.y, Mathf.Min(b.y, c.y))));
                int y1 = Mathf.Min(h - 1, Mathf.CeilToInt(Mathf.Max(a.y, Mathf.Max(b.y, c.y))));
                for (int y = y0; y <= y1; y++)
                    for (int x = x0; x <= x1; x++)
                    {
                        float px = x + 0.5f, py = y + 0.5f;
                        float w0 = ((b.x - px) * (c.y - py) - (c.x - px) * (b.y - py)) / area;
                        float w1 = ((c.x - px) * (a.y - py) - (a.x - px) * (c.y - py)) / area;
                        float w2 = 1f - w0 - w1;
                        const float eps = -0.02f;   // a hair over the edge, so islands have no gaps
                        if (w0 < eps || w1 < eps || w2 < eps) continue;
                        coord[y * w + x] = w0 * s[i0] + w1 * s[i1] + w2 * s[i2];
                    }
            }
            return coord;
        }

        private static Vector2 Px(Vector2 uv, int w, int h) =>
            new((uv.x - Mathf.Floor(uv.x)) * w, (uv.y - Mathf.Floor(uv.y)) * h);

        /// <summary>A readable copy of any texture, at most maxSize across.</summary>
        private static Texture2D? Grab(Texture src, int maxSize)
        {
            int w = src.width, h = src.height;
            float k = Mathf.Min(1f, maxSize / (float)Mathf.Max(w, h));
            w = Mathf.Max(8, Mathf.RoundToInt(w * k)); h = Mathf.Max(8, Mathf.RoundToInt(h * k));
            var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            var prev = RenderTexture.active;
            try
            {
                Graphics.Blit(src, rt);
                RenderTexture.active = rt;
                var tex = new Texture2D(w, h, TextureFormat.RGBA32, true, false) { name = src.name + "_cooked" };
                tex.ReadPixels(new Rect(0, 0, w, h), 0, 0);
                return tex;
            }
            catch (System.Exception ex)
            {
                Plugin.Log.LogWarning($"Cooked look: couldn't copy '{src.name}' ({ex.Message}).");
                return null;
            }
            finally
            {
                RenderTexture.active = prev;
                RenderTexture.ReleaseTemporary(rt);
            }
        }

        /// <summary>Browns the colours (keeping their light and dark), adds sear patches, and grill bars where
        /// <paramref name="coord"/> is near a whole number (no bars where it's NaN, or with no coords at all).</summary>
        private static void Paint(Texture2D tex, float[]? coord, bool skipClear)
        {
            int w = tex.width, h = tex.height;
            var px = tex.GetPixels32();
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    int i = y * w + x;
                    Color c = px[i];
                    if (skipClear && c.a < 0.02f) continue;
                    float u = x / (float)w, v = y / (float)h;
                    float lum = c.r * 0.30f + c.g * 0.55f + c.b * 0.15f;
                    Color cooked = Color.Lerp(c, Brown * (0.5f + 1.05f * lum), 0.85f);
                    cooked *= Mathf.Lerp(0.74f, 1.08f, Mathf.PerlinNoise(u * 7f + 3.1f, v * 7f + 1.7f));
                    if (coord != null && !float.IsNaN(coord[i]))
                    {
                        float d = Mathf.Abs(coord[i] - Mathf.Round(coord[i]));            // 0 at a bar's centre
                        float bar = 1f - Smooth(BarWidth * 0.7f, BarWidth, d);     // crisp edges
                        cooked = Color.Lerp(cooked, Char, bar * 0.85f);
                    }
                    cooked.a = c.a;
                    px[i] = cooked;
                }
            tex.SetPixels32(px);
            tex.Apply(true, true);
        }

        /// <summary>0 below a, 1 above b, eased between (the shader smoothstep; Unity's Mathf.SmoothStep is a different thing).</summary>
        private static float Smooth(float a, float b, float x)
        {
            float s = Mathf.Clamp01((x - a) / (b - a));
            return s * s * (3f - 2f * s);
        }
    }
}
