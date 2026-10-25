using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Testing for painted-on gear (the vanilla way: a chest or legs item's material sets _ChestTex / _LegsTex on the
    /// player's own body). "vdw_debug paint chest|legs|both|alpha|off" puts test textures on your body to show the body's
    /// UV layout and which layer draws on top; "vdw_debug paint dump" writes the body mesh, its UV layout and vanilla
    /// armour textures to config/ValheimDeepWaters/armordump for baking the gear onto.
    /// </summary>
    internal static class ArmorPaintTest
    {
        private static readonly int ChestTex = Shader.PropertyToID("_ChestTex"), LegsTex = Shader.PropertyToID("_LegsTex");
        private static Texture? _origChest, _origLegs;
        private static bool _saved;
        private static Texture2D? _grid, _gridAlpha, _stripes;

        public static string Run(Player p, string mode)
        {
            var body = p.GetComponent<VisEquipment>()?.m_bodyModel;
            if (body == null) return "No body model found.";
            var mat = body.material;
            if (!_saved) { _origChest = mat.GetTexture(ChestTex); _origLegs = mat.GetTexture(LegsTex); _saved = true; }
            switch (mode)
            {
                case "chest": mat.SetTexture(ChestTex, Grid(false)); mat.SetTexture(LegsTex, _origLegs); return "Chest layer: UV grid. Legs layer: back to normal.";
                case "legs": mat.SetTexture(ChestTex, _origChest); mat.SetTexture(LegsTex, Stripes()); return "Legs layer: yellow/black stripes. Chest layer: back to normal.";
                case "both": mat.SetTexture(ChestTex, Grid(false)); mat.SetTexture(LegsTex, Stripes()); return "Chest layer: UV grid, legs layer: stripes. Where they overlap, whichever shows is the one on top.";
                case "alpha": mat.SetTexture(ChestTex, Grid(true)); mat.SetTexture(LegsTex, _origLegs); return "Chest layer: UV grid with the left half (U < 0.5) transparent - shows whether the chest texture's alpha masks it.";
                case "off": mat.SetTexture(ChestTex, _origChest); mat.SetTexture(LegsTex, _origLegs); return "Body textures back to normal (re-equip your chest/legs armour if it looks wrong).";
                case "dump": return Dump(p, body);
                default: return "Usage: vdw_debug paint chest | legs | both | alpha | off | dump";
            }
        }

        /// <summary>
        /// 8x8 cells: red rises with U (left to right), green with V (bottom to top), blue alternates like a checker.
        /// Black lines between cells, white at the edges of the texture, a white dot in the cell at U,V = 0,0.
        /// </summary>
        private static Texture2D Grid(bool halfAlpha)
        {
            ref var cache = ref (halfAlpha ? ref _gridAlpha : ref _grid);
            if (cache != null) return cache;
            const int N = 512;
            var t = new Texture2D(N, N, TextureFormat.RGBA32, true) { name = "vdw_paint_grid", wrapMode = TextureWrapMode.Clamp };
            var px = new Color32[N * N];
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    int cx = x * 8 / N, cy = y * 8 / N;
                    Color c = new Color(0.12f + 0.88f * cx / 7f, 0.12f + 0.88f * cy / 7f, ((cx + cy) & 1) == 0 ? 0.15f : 0.75f, 1f);
                    int lx = x % (N / 8), ly = y % (N / 8);
                    if (lx < 3 || ly < 3) c = Color.black;
                    if (x < 6 || y < 6 || x >= N - 6 || y >= N - 6) c = Color.white;
                    if (cx == 0 && cy == 0 && (new Vector2(lx, ly) - new Vector2(32, 32)).sqrMagnitude < 100) c = Color.white;
                    if (halfAlpha && x < N / 2) c.a = 0f;
                    px[y * N + x] = c;
                }
            t.SetPixels32(px); t.Apply(true);
            return cache = t;
        }

        private static Texture2D Stripes()
        {
            if (_stripes != null) return _stripes;
            const int N = 512;
            var t = new Texture2D(N, N, TextureFormat.RGBA32, true) { name = "vdw_paint_stripes" };
            var px = new Color32[N * N];
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                    px[y * N + x] = ((x + y) / 24 & 1) == 0 ? new Color32(250, 210, 30, 255) : new Color32(20, 20, 20, 255);
            t.SetPixels32(px); t.Apply(true);
            return _stripes = t;
        }

        private static string Dump(Player p, SkinnedMeshRenderer body)
        {
            string dir = Path.Combine(BepInEx.Paths.ConfigPath, "ValheimDeepWaters", "armordump");
            Directory.CreateDirectory(dir);
            var log = new StringBuilder();
            var mesh = body.sharedMesh;
            if (mesh != null && mesh.isReadable)
            {
                // the body as it's bound (bind pose, the mesh's own space), with its UVs, as OBJ
                var sb = new StringBuilder("# Valheim player body (" + mesh.name + "), bind pose\n");
                var inv = CultureInfo.InvariantCulture;
                foreach (var v in mesh.vertices) sb.Append("v ").Append((-v.x).ToString(inv)).Append(' ').Append(v.y.ToString(inv)).Append(' ').Append(v.z.ToString(inv)).Append('\n');
                var uv = mesh.uv;
                foreach (var u in uv) sb.Append("vt ").Append(u.x.ToString(inv)).Append(' ').Append(u.y.ToString(inv)).Append('\n');
                var tris = mesh.triangles;
                for (int i = 0; i + 2 < tris.Length; i += 3)   // x was mirrored above (Unity is left-handed), so the winding flips too
                    sb.Append("f ").Append(tris[i] + 1).Append('/').Append(tris[i] + 1).Append(' ')
                      .Append(tris[i + 2] + 1).Append('/').Append(tris[i + 2] + 1).Append(' ')
                      .Append(tris[i + 1] + 1).Append('/').Append(tris[i + 1] + 1).Append('\n');
                File.WriteAllText(Path.Combine(dir, "body.obj"), sb.ToString());
                File.WriteAllBytes(Path.Combine(dir, "body_uv.png"), UvLayout(uv, tris, 2048).EncodeToPNG());
                log.Append($"body.obj ({mesh.vertexCount} points, {tris.Length / 3} triangles), body_uv.png; ");
            }
            else log.Append("body mesh not readable; ");

            var mat = body.material;
            log.Append($"shader {mat.shader.name}; ");
            foreach (var prop in new[] { "_MainTex", "_ChestTex", "_LegsTex", "_BumpMap", "_ChestBumpMap", "_LegsBumpMap", "_ChestMetal", "_LegsMetal", "_SkinBumpMap" })
                if (mat.HasProperty(prop) && mat.GetTexture(prop) is Texture tx) Save(tx, Path.Combine(dir, "body" + prop + ".png"), log);
            foreach (var item in new[] { "ArmorLeatherChest", "ArmorLeatherLegs", "ArmorRagsChest", "ArmorRagsLegs", "ArmorBronzeChest", "ArmorTrollLeatherChest" })
            {
                var am = ObjectDB.instance?.GetItemPrefab(item)?.GetComponent<ItemDrop>()?.m_itemData.m_shared.m_armorMaterial;
                if (am == null) continue;
                foreach (var prop in new[] { "_ChestTex", "_LegsTex", "_ChestBumpMap", "_LegsBumpMap" })
                    if (am.HasProperty(prop) && am.GetTexture(prop) is Texture tx) Save(tx, Path.Combine(dir, item + prop + ".png"), log);
            }
            var props = Enumerable.Range(0, mat.shader.GetPropertyCount()).Select(i => mat.shader.GetPropertyName(i));
            File.WriteAllText(Path.Combine(dir, "shader_properties.txt"), mat.shader.name + "\n" + string.Join("\n", props));
            Plugin.Log.LogInfo("Armour paint dump: " + log + " -> " + dir);
            return "Written to " + dir + ": " + log;
        }

        private static void Save(Texture tx, string path, StringBuilder log)
        {
            var rt = RenderTexture.GetTemporary(tx.width, tx.height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB);
            Graphics.Blit(tx, rt);
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var t = new Texture2D(tx.width, tx.height, TextureFormat.RGBA32, false);
            t.ReadPixels(new Rect(0, 0, tx.width, tx.height), 0, 0); t.Apply();
            RenderTexture.active = prev; RenderTexture.ReleaseTemporary(rt);
            File.WriteAllBytes(path, t.EncodeToPNG());
            Object.Destroy(t);
            log.Append(Path.GetFileName(path)).Append(' ');
        }

        private static Texture2D UvLayout(Vector2[] uv, int[] tris, int n)
        {
            var t = new Texture2D(n, n, TextureFormat.RGBA32, false);
            var px = Enumerable.Repeat(new Color32(0, 0, 0, 0), n * n).ToArray();
            void Line(Vector2 a, Vector2 b)
            {
                int steps = Mathf.CeilToInt((b - a).magnitude * n) + 1;
                for (int s = 0; s <= steps; s++)
                {
                    var q = Vector2.Lerp(a, b, s / (float)steps);
                    int x = Mathf.Clamp((int)(q.x * n), 0, n - 1), y = Mathf.Clamp((int)(q.y * n), 0, n - 1);
                    px[y * n + x] = new Color32(255, 255, 255, 255);
                }
            }
            for (int i = 0; i + 2 < tris.Length; i += 3) { Line(uv[tris[i]], uv[tris[i + 1]]); Line(uv[tris[i + 1]], uv[tris[i + 2]]); Line(uv[tris[i + 2]], uv[tris[i]]); }
            t.SetPixels32(px); t.Apply();
            return t;
        }
    }
}
