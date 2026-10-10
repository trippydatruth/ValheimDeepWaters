using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Optional custom models, picked up by file name from BepInEx/config/ValheimDeepWaters/Models/:
    ///   rod, bobber, bait_&lt;bait id&gt;, fish_&lt;fish id&gt;   (ids as in Baits.json / Fish.json)
    /// A rod model with a skinned mesh is a rigged rod: it bends under load and its reel turns (see RodRig).
    /// For each name, in order: &lt;name&gt;.bundle (any prefab inside), a prefab called &lt;name&gt; inside any .bundle
    /// in the folder (so all baits can share one bait.bundle), then a plain &lt;name&gt;.obj with an optional
    /// &lt;name&gt;.png/.jpg texture. Bundles bring their own material. Anything missing or broken just keeps the
    /// vanilla-cloned mesh. Every model is used at exactly its size in Unity (1 unit = 1 metre): the mesh times
    /// every transform in its prefab, the root included. Nothing is resized.
    /// </summary>
    internal static partial class CustomModels
    {
        private static readonly Dictionary<string, (Mesh? mesh, Material? mat)> Cache = new();
        private static readonly Dictionary<string, AssetBundle> LoadedBundles = new();

        // Scale that couldn't be baked into a non-readable bundle mesh; ApplyToPrefab puts it on the transform.
        private static readonly Dictionary<string, Vector3> UnbakedScale = new();

        private static Shader? _shader;


        public static string ModelsFolder => Path.Combine(Plugin.ConfigDirectory, "Models");

        public static void EnsureFolder()
        {
            try { Directory.CreateDirectory(ModelsFolder); }
            catch (Exception ex) { Plugin.Log.LogWarning($"Custom models: could not create {ModelsFolder} ({ex.Message})."); }
        }

        public static bool TryGetCustom(string baseName, out Mesh mesh, out Material mat)
        {
            mesh = null!;
            mat = null!;

            if (!Cache.TryGetValue(baseName, out var entry))
            {
                entry = Load(baseName);
                Cache[baseName] = entry;
            }

            if (entry.mesh == null || entry.mat == null) return false;
            mesh = entry.mesh;
            mat = entry.mat;
            return true;
        }

        /// <summary>Puts the custom model, if there is one, on every renderer of a registered item prefab.
        /// Returns true if a custom model was applied.</summary>
        public static bool ApplyToPrefab(GameObject? prefab, string baseName)
        {
            if (prefab == null) return false;
            if (baseName.StartsWith("rod") && GetRiggedRod(baseName) is GameObject riggedRod)
            {
                ApplyRiggedRod(prefab, riggedRod, baseName);
                ItemIcons.Apply(prefab, baseName);
                return true;
            }
            if (GetAnimated(baseName) is GameObject animated)
            {
                ApplyAnimated(prefab, animated);
                ItemIcons.Apply(prefab, baseName);
                return true;
            }
            if (ApplyPieceModel(prefab, baseName) || ApplyWholeItemModel(prefab, baseName))
            {
                ItemIcons.Apply(prefab, baseName);
                return true;
            }
            if (!TryGetCustom(baseName, out var mesh, out var mat))
            {
                // No model, but a hand-drawn icon still counts.
                ItemIcons.ApplyHandMadeOnly(prefab, baseName);
                return false;
            }

            UnbakedScale.TryGetValue(baseName, out var unbaked);

            foreach (var mf in prefab.GetComponentsInChildren<MeshFilter>(true))
            {
                mf.sharedMesh = mesh;
                var mr = mf.GetComponent<MeshRenderer>();
                if (mr != null) mr.sharedMaterial = mat;

                if (unbaked == Vector3.zero) continue;
                // Valheim ignores scale on the item prefab's root, so this only works on a child renderer.
                if (mf.transform == prefab.transform)
                    Plugin.Log.LogWarning($"Custom models: '{baseName}' needs a scale correction but its renderer is on the prefab root - enable Read/Write on the model in Unity and rebuild the bundle.");
                else
                    mf.transform.localScale = Vector3.Scale(mf.transform.localScale, unbaked);
            }

            // Vanilla fish (and other creatures) draw a rigged, animated mesh. A custom model is static, so show it
            // in place of each skinned renderer instead.
            foreach (var smr in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                var stand = new GameObject("custom_static");
                stand.transform.SetParent(smr.transform.parent, false);
                stand.transform.localPosition = smr.transform.localPosition;
                stand.transform.localRotation = smr.transform.localRotation;
                stand.transform.localScale = smr.transform.localScale;
                stand.AddComponent<MeshFilter>().sharedMesh = mesh;
                stand.AddComponent<MeshRenderer>().sharedMaterial = mat;
                smr.enabled = false;
            }

            ItemIcons.Apply(prefab, baseName);
            return true;
        }

        /// <summary>
        /// The model's prefab from a bundle: 1. a bundle named after the model (rod.bundle; its prefab can be named
        /// anything), else 2. a prefab with this exact name in any bundle in the folder (bait_worm in bait.bundle).
        /// </summary>
        private static GameObject? FindBundlePrefab(string baseName, out string source)
        {
            source = "";
            string ownBundle = Path.Combine(ModelsFolder, baseName + ".bundle");
            if (File.Exists(ownBundle) && GetBundle(ownBundle) is AssetBundle own)
            {
                source = Path.GetFileName(ownBundle);
                if ((own.LoadAsset<GameObject>(baseName) ?? FirstGameObject(own)) is GameObject p) return p;
            }
            if (BundleIndex.TryGetValue(baseName.ToLowerInvariant(), out var entry))
            {
                source = entry.file;
                return entry.bundle.LoadAsset<GameObject>(entry.assetPath);
            }
            return null;
        }

        private static (Mesh?, Material?) Load(string baseName)
        {
            var prefab = FindBundlePrefab(baseName, out var source);
            if (prefab != null)
            {
                var fromBundle = ExtractFromPrefab(prefab, baseName, source, out var nodeScale);
                if (fromBundle.Item1 != null && fromBundle.Item2 != null)
                    return (BakeTransform(fromBundle.Item1, baseName, nodeScale, copy: true), fromBundle.Item2);
            }

            // 3. A plain .obj, with an optional same-named texture.
            string objPath = Path.Combine(ModelsFolder, baseName + ".obj");
            if (!File.Exists(objPath)) return (null, null);

            var mesh = ObjLoader.Load(objPath);
            if (mesh == null) return (null, null);

            mesh = BakeTransform(mesh, baseName, Vector3.one, copy: false);
            return (mesh, BuildMaterial(baseName));
        }

        /// <summary>A model's prefab from the bundles (see FindBundlePrefab), or null.</summary>
        public static GameObject? GetBundlePrefab(string baseName) => FindBundlePrefab(baseName, out _);

        /// <summary>Any asset (a sound, a texture...) with this name from any bundle in the Models folder, or null.</summary>
        public static T? LoadBundleAsset<T>(string name) where T : UnityEngine.Object =>
            BundleIndex.TryGetValue(name.ToLowerInvariant(), out var entry) ? entry.bundle.LoadAsset<T>(entry.assetPath) : null;

        private static Dictionary<string, (AssetBundle bundle, string assetPath, string file)>? _bundleIndex;

        /// <summary>Every GameObject in every .bundle in the Models folder, by lowercase asset name. Built once.</summary>
        /// <summary>A sprite (or texture, turned into one) with this name from any bundle in the Models folder.</summary>
        public static Sprite? LoadBundleSprite(string name)
        {
            if (!BundleIndex.TryGetValue(name.ToLowerInvariant(), out var entry)) return null;
            var sprite = entry.bundle.LoadAsset<Sprite>(entry.assetPath);
            if (sprite != null) return sprite;
            var tex = entry.bundle.LoadAsset<Texture2D>(entry.assetPath);
            return tex != null ? Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height), new Vector2(0.5f, 0.5f)) : null;
        }

        private static Dictionary<string, (AssetBundle bundle, string assetPath, string file)> BundleIndex
        {
            get
            {
                if (_bundleIndex != null) return _bundleIndex;
                _bundleIndex = new Dictionary<string, (AssetBundle, string, string)>();
                if (!Directory.Exists(ModelsFolder)) return _bundleIndex;

                foreach (var path in Directory.GetFiles(ModelsFolder, "*.bundle"))
                {
                    var bundle = GetBundle(path);
                    if (bundle == null) continue;
                    foreach (var assetPath in bundle.GetAllAssetNames())
                    {
                        string key = Path.GetFileNameWithoutExtension(assetPath).ToLowerInvariant();
                        // A prefab beats a raw model asset of the same name.
                        if (_bundleIndex.ContainsKey(key) && !assetPath.EndsWith(".prefab")) continue;
                        _bundleIndex[key] = (bundle, assetPath, Path.GetFileName(path));
                    }
                }
                return _bundleIndex;
            }
        }

        private static AssetBundle? GetBundle(string path)
        {
            if (LoadedBundles.TryGetValue(path, out var cached) && cached != null) return cached;
            try
            {
                var bundle = AssetBundle.LoadFromFile(path);
                if (bundle == null)
                {
                    Plugin.Log.LogWarning($"Custom models: could not load '{path}' - likely built with an incompatible Unity version.");
                    return null;
                }
                LoadedBundles[path] = bundle;
                return bundle;
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Custom models: failed loading '{path}' ({ex.Message}).");
                return null;
            }
        }

        private static GameObject? FirstGameObject(AssetBundle bundle)
        {
            foreach (var name in bundle.GetAllAssetNames())
                if (bundle.LoadAsset<GameObject>(name) is GameObject go) return go;
            return null;
        }

        private static (Mesh?, Material?) ExtractFromPrefab(GameObject prefab, string baseName, string source, out Vector3 nodeScale)
        {
            nodeScale = Vector3.one;
            var mf = prefab.GetComponentInChildren<MeshFilter>();
            var mr = prefab.GetComponentInChildren<MeshRenderer>();
            if (mf == null || mf.sharedMesh == null || mr == null || mr.sharedMaterial == null)
            {
                Plugin.Log.LogWarning($"Custom models: '{prefab.name}' in '{source}' has no usable mesh and material.");
                return (null, null);
            }

            // Only the raw mesh is used, so keep every scale above it in the prefab, root included: the model
            // comes out exactly as big as it is in Unity.
            nodeScale = mf.transform.lossyScale;
            return (mf.sharedMesh, mr.sharedMaterial);
        }


        /// <summary>
        /// Scale is baked into the vertices because Valheim's equip visuals ignore the item prefab's root scale.
        /// A bundle mesh is only CPU-readable if "Read/Write" was enabled on its import settings; otherwise the
        /// scale is left for ApplyToPrefab to put on the renderer's transform.
        /// </summary>
        private static Mesh BakeTransform(Mesh mesh, string baseName, Vector3 nodeScale, bool copy)
        {
            Vector3 scale = nodeScale;
            Quaternion rotation = RotationFor(baseName);
            if (scale == Vector3.one && rotation == Quaternion.identity) return mesh;

            if (!mesh.isReadable)
            {
                Plugin.Log.LogWarning($"Custom models: '{baseName}' mesh isn't readable, so its scale goes on the transform instead{(rotation == Quaternion.identity ? "" : " and its ModelRotation can't be applied")}. Enable Read/Write on the model in Unity and rebuild the bundle to fix.");
                UnbakedScale[baseName] = scale;
                return mesh;
            }

            // A bundle mesh may be shared by several prefabs (e.g. three rods using one model), so work on a copy.
            if (copy) mesh = UnityEngine.Object.Instantiate(mesh);

            var verts = mesh.vertices;
            for (int i = 0; i < verts.Length; i++) verts[i] = rotation * Vector3.Scale(verts[i], scale);
            mesh.vertices = verts;
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            Plugin.Log.LogInfo($"Custom models: '{baseName}' scaled by {scale}{(rotation == Quaternion.identity ? "" : $", rotated {rotation.eulerAngles}")} - final size {mesh.bounds.size}.");
            return mesh;
        }

        /// <summary>Per-rod ModelRotation from Rods.json (degrees around X, Y, Z).</summary>
        private static Quaternion RotationFor(string baseName)
        {
            if (!baseName.StartsWith("rod_")) return Quaternion.identity;
            var rod = ContentRegistry.Rods.FirstOrDefault(r => r.Id == baseName.Substring(4));
            var e = rod?.ModelRotation;
            return e != null && e.Length == 3 ? Quaternion.Euler(e[0], e[1], e[2]) : Quaternion.identity;
        }

        private static Material BuildMaterial(string baseName)
        {
            if (_shader == null) _shader = Shader.Find("Standard") ?? Shader.Find("Sprites/Default");
            var mat = new Material(_shader!) { name = baseName + "_mat" };

            foreach (var ext in new[] { ".png", ".jpg", ".jpeg" })
            {
                string texPath = Path.Combine(ModelsFolder, baseName + ext);
                if (!File.Exists(texPath)) continue;

                try
                {
                    var tex = new Texture2D(2, 2);
                    if (tex.LoadImage(File.ReadAllBytes(texPath)) && mat.HasProperty("_MainTex"))
                        mat.mainTexture = tex;
                }
                catch (Exception ex)
                {
                    Plugin.Log.LogWarning($"Custom models: failed loading texture for '{baseName}' ({ex.Message}).");
                }
                break;
            }

            return mat;
        }
    }
}
