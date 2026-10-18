// Deep Waters: sets up every model in Assets/DeepWaters/<key>/ (a <key>_model.fbx plus its *_Unity_* maps) as a
// prefab named <key>, tags it into its bundle, builds the bundles and installs them in the Test profile.
//   Menu: Deep Waters > Import Models And Build Bundles
// It also runs once by itself when Assets/DeepWaters/RUN_IMPORT.txt exists (the file is then deleted).
// A report is written to <project>/vdw_import_report.txt.
//
// Per model: textures get the right import type (normal map, linear metallic/smoothness), a Standard material is
// made from them (emission where there's an emission map), the FBX is imported at 1 unit = 1 m without its own
// materials, animated models get an Animator Controller with one state per clip (Swim default, "Speed" parameter),
// and the prefab is saved as <key>.prefab. The old prefabs these replace (rod_wood, bobber, the five baits) are
// taken out of the bundles but left in the project.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UnityEngine.Rendering;

[InitializeOnLoad]
public static class VdwModelImporter
{
    const string Root = "Assets/DeepWaters";
    const string Trigger = Root + "/RUN_IMPORT.txt";
    const string OutDir = "AssetBundles/StandaloneWindows";

    static string ModelsDir => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        @"Thunderstore Mod Manager\DataFolder\Valheim\profiles\Test\BepInEx\config\ValheimDeepWaters\Models");

    enum Kind { Static, Rigged, Animated }

    class Entry
    {
        public string Key, Bundle; public Kind Kind; public float Glow; public int TexSize; public float Scale = 1f;
        public Entry(string key, string bundle, Kind kind, float glow = 0f, int texSize = 512)   // 512: Valheim's own texture size (roadmap #11)
        { Key = key; Bundle = bundle; Kind = kind; Glow = glow; TexSize = texSize; }
    }

    // Bait is shown bigger than its Blender size so it reads in game (on the ground, on the hook, in the world).
    const float BaitScale = 2f;
    const float LureScale = 3.5f;   // lures and trailers: at bait size they were barely visible dropped or on the line

    static readonly Entry[] Entries =
    {
        new Entry("rod", "rod", Kind.Rigged),
        new Entry("rod_copper", "rod", Kind.Rigged),
        new Entry("rod_finewood", "rod", Kind.Rigged),
        new Entry("rod_ancientbark", "rod", Kind.Rigged),
        new Entry("rod_silver", "rod", Kind.Rigged),
        // Themed rods built from scratch (build_rod_model.py): the glowing ones get emission.
        new Entry("rod_blackmetal", "rod", Kind.Rigged),
        new Entry("rod_yggdrasil", "rod", Kind.Rigged, 1.5f),
        new Entry("rod_ashwood", "rod", Kind.Rigged, 1.5f),
        new Entry("rod_haldor", "rod", Kind.Rigged, 1f),
        new Entry("rod_leviathan", "rod", Kind.Rigged, 1.5f),
        new Entry("rod_frostwood", "rod", Kind.Rigged, 1.5f),   // the Deep North (build_rod_model.py frostwood)
        new Entry("bobber", "rod", Kind.Static, 1.5f),
        new Entry("hook_tiny", "hooks", Kind.Static, 0f),
        new Entry("hook_small", "hooks", Kind.Static, 0f),
        new Entry("hook_medium", "hooks", Kind.Static, 0f),
        new Entry("hook_large", "hooks", Kind.Static, 0f),
        new Entry("hook_heavy", "hooks", Kind.Static, 0f),
        new Entry("hook_giant", "hooks", Kind.Static, 0f),
        new Entry("hook_golden", "hooks", Kind.Static, 1f),
        // Fisherman's gear (armour) - on hold: back in when it's ready (FisherGear.cs; Mesh\Fishermen gear\README.txt).
        new Entry("fisher_chest", "armor", Kind.Rigged),        // the striped shirt (tunic)
        new Entry("fisher_coat", "armor", Kind.Rigged),         // the oilskin coat (cape)
        new Entry("fisher_legs", "armor", Kind.Rigged),
        new Entry("fisher_hat", "armor", Kind.Rigged),
        // Boss trophies: the material each great fish drops (build_bossmats.py).
        new Entry("bossmat_eikthyr_elver", "bossmats", Kind.Static, 1.5f),
        new Entry("bossmat_elder_bass", "bossmats", Kind.Static, 1.5f),
        new Entry("bossmat_bonemass_catfish", "bossmats", Kind.Static, 1.5f),
        new Entry("bossmat_moder_scale", "bossmats", Kind.Static, 1.5f),
        new Entry("bossmat_yagluthgill", "bossmats", Kind.Static, 1.5f),
        new Entry("bossmat_queen_eel", "bossmats", Kind.Static, 1.5f),
        new Entry("bossmat_fimbul_salmon", "bossmats", Kind.Static, 1.5f),
        new Entry("hook_fimbul", "hooks", Kind.Static, 1.2f),   // rime metal, frost glow (build_hooks.py fimbul)
        new Entry("bait_worm", "bait", Kind.Animated) { Scale = BaitScale },
        new Entry("bait_grub", "bait", Kind.Animated) { Scale = BaitScale },
        new Entry("bait_shrimp", "bait", Kind.Animated) { Scale = BaitScale },
        new Entry("bait_minnow", "bait", Kind.Animated) { Scale = BaitScale },
        new Entry("bait_large_minnow", "bait", Kind.Animated) { Scale = BaitScale },
        new Entry("bait_leech", "bait", Kind.Animated) { Scale = BaitScale },
        // Boss lures (build_lures.py): static, each glowing in its boss's colour.
        new Entry("bait_lure_antler", "bait", Kind.Static, 1.5f) { Scale = LureScale },
        new Entry("bait_lure_root", "bait", Kind.Static, 1.5f) { Scale = LureScale },
        new Entry("bait_lure_ooze", "bait", Kind.Static, 1.5f) { Scale = LureScale },
        new Entry("bait_lure_wyrm", "bait", Kind.Static, 1.5f) { Scale = LureScale },
        new Entry("bait_lure_ember", "bait", Kind.Static, 1.5f) { Scale = LureScale },
        new Entry("bait_lure_chitin", "bait", Kind.Static, 1.5f) { Scale = LureScale },
        // Everyday lures and trailers (build_lures.py): static, no glow.
        new Entry("bait_lure_feather_fly", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_lure_flint_spinner", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_lure_leather_grub", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_lure_bronze_spoon", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_lure_finewood_crank", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_lure_guck_crawler", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_lure_bone_jig", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_lure_silver_swimbait", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_lure_linen_popper", "bait", Kind.Static) { Scale = LureScale },
        // the Deep North (build_lures.py)
        new Entry("bait_lure_crown", "bait", Kind.Static, 1.5f) { Scale = LureScale },
        new Entry("bait_lure_ice_spoon", "bait", Kind.Static, 0.6f) { Scale = LureScale },
        new Entry("bait_lure_frostcore_jig", "bait", Kind.Static, 1.2f) { Scale = LureScale },
        new Entry("bait_northern_bait", "bait", Kind.Static) { Scale = BaitScale },
        new Entry("bait_trailer_curly_tail", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_trailer_boar_rind", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_trailer_feather_skirt", "bait", Kind.Static) { Scale = LureScale },
        new Entry("bait_fly", "bait", Kind.Animated) { Scale = BaitScale },
        // Worm mound: soil + a wriggling half-worm, at its own size (the worm is already modelled at bait size).
        new Entry("pickable_worm", "bait", Kind.Animated),
        // Buildable pieces: the mod uses the whole prefab in place of the vanilla piece it clones.
        new Entry("buff_totem_fisher", "pieces", Kind.Static, 1.5f),
        new Entry("buff_totem_njord", "pieces", Kind.Static, 1.5f),   // the same totem, recoloured (recolor_totem.py)
        new Entry("fishing_boat", "pieces", Kind.Static),             // hull + oar.L / oar.R pivoting at their oarlocks (build_boat.py)
        // Chum: one bucket of minnows, a different liquid per tier (bucket_ / fish_ / liquid_ maps per mesh).
        new Entry("buff_relic_horn", "buffs", Kind.Static),
        new Entry("buff_relic_pearl", "buffs", Kind.Static, 1.5f),
        new Entry("buff_rune_njord", "buffs", Kind.Static, 1.5f),    // a necklace, its blue ring glowing (build_rune_necklace.py)
        new Entry("buff_chum_basic", "buffs", Kind.Static),
        new Entry("buff_chum_blood", "buffs", Kind.Static),
        new Entry("buff_chum_abyssal", "buffs", Kind.Static, 1.5f),
        new Entry("buff_chum_blubber", "buffs", Kind.Static),   // whale blubber in oil (build_chum.py chum_blubber)
        // Meads and tonics: one bottle, re-coloured per family, the major ones glowing.
        new Entry("buff_angler_minor", "buffs", Kind.Static),
        new Entry("buff_angler_medium", "buffs", Kind.Static),
        new Entry("buff_angler_major", "buffs", Kind.Static, 1.5f),
        new Entry("buff_angler_north", "buffs", Kind.Static, 1.5f),   // Lingonberry Angler's Mead (build_meads.py EXTRA)
        new Entry("buff_steady_minor", "buffs", Kind.Static),
        new Entry("buff_steady_medium", "buffs", Kind.Static),
        new Entry("buff_steady_major", "buffs", Kind.Static, 1.5f),
        new Entry("buff_grip_minor", "buffs", Kind.Static),
        new Entry("buff_grip_medium", "buffs", Kind.Static),
        new Entry("buff_grip_major", "buffs", Kind.Static, 1.5f),
        new Entry("fish_moder_scale", "fish", Kind.Animated, 2f),
        new Entry("fish_bonemass_catfish", "fish", Kind.Animated, 2f),
        new Entry("fish_eikthyr_elver", "fish", Kind.Animated, 2f),
        new Entry("fish_elder_bass", "fish", Kind.Animated, 2f),
        new Entry("fish_yagluthgill", "fish", Kind.Animated, 2f),
        new Entry("fish_queen_eel", "fish", Kind.Animated, 2f),
        new Entry("fish_fimbul_salmon", "fish", Kind.Animated, 2f),   // the Deep North boss (Mesh/Deep north salmon)
        // Deep North fish: source fish re-rigged and repainted (recolor_fish.py)
        // new Entry("fish_rimejaw_cod", "fish", Kind.Animated, 1f),        // from the largemouth bass   (off: re-skinned from another species' model - needs its own)
        // new Entry("fish_glacier_grayling", "fish", Kind.Animated, 1.5f), // from the sea bass (Mesh/perch)   (off: re-skinned from another species' model - needs its own)
        // new Entry("fish_frost_sculpin", "fish", Kind.Animated, 1f),      // from the catfish   (off: re-skinned from another species' model - needs its own)
        // Sourced fish (Mesh/Sourced/<id>, Sketchfab models - see Mesh/Sourced/CREDITS.md): one model per species
        new Entry("fish_trout", "fish", Kind.Animated),
        new Entry("fish_mackerel", "fish", Kind.Animated),
        new Entry("fish_halibut", "fish", Kind.Animated),
        new Entry("fish_frost_sculpin", "fish", Kind.Animated, 1f),       // roughskin sculpin scan
        new Entry("fish_frostchar", "fish", Kind.Animated, 1f),
        new Entry("fish_greydwarf_goby", "fish", Kind.Animated),
        new Entry("fish_bonemaw", "fish", Kind.Animated, 1.5f),             // pacific viperfish
        new Entry("fish_jotunnperch", "fish", Kind.Animated, 1f),         // european perch (CC-BY-NC)
        new Entry("fish_odinfin", "fish", Kind.Animated, 2f),             // opah
        new Entry("fish_thorhammerhead", "fish", Kind.Animated, 1.5f),      // scalloped hammerhead
        new Entry("fish_serpentfin", "fish", Kind.Animated, 1f),          // oarfish
        new Entry("fish_surtling_sardine", "fish", Kind.Animated, 2f),
        // Tripo models made by the user (Mesh/Sourced/<id>, source FBX/maps in the user's own folders)
        new Entry("fish_fenringfin", "fish", Kind.Animated),          // legendary wolffish
        new Entry("fish_rimejaw_cod", "fish", Kind.Animated, 1f),     // atlantic cod (frost-rimed jaw glows)
        new Entry("fish_glacier_grayling", "fish", Kind.Animated, 1.5f), // arctic grayling (glowing fin dots, frosted head)
        new Entry("fish_lingcod", "fish", Kind.Animated),             // lingcod (natural)
        new Entry("fish_mistfin", "fish", Kind.Animated, 1f),         // swamp / Mistlands fish (faint glowing mist flecks)
        // Roadmap 16: the bass and bluegill keep their download's own rig and swim cycle (carry_source_rig.py)
        new Entry("fish_bass", "fish", Kind.Animated),                // largemouth bass (DigitalLife3D, CC-BY-NC)
        new Entry("fish_bluegill", "fish", Kind.Animated),            // bluegill (DigitalLife3D, CC-BY-NC)
        new Entry("fish_sea_bass", "fish", Kind.Animated),            // european sea bass (boxgizmo, Sketchfab Standard)
        new Entry("fish_catfish", "fish", Kind.Animated),             // channel catfish (the user's Tripo model)
    };

    // Old prefabs (and their files) that the new ones replace: taken out of the bundles, files kept.
    static readonly string[] Replaced =
    {
        "Assets/rod/rod_wood", "Assets/rod/bobber", "Assets/bait/worm", "Assets/bait/grub", "Assets/bait/shrimp",
        "Assets/bait/minnow", "Assets/bait/lg_minnow", "Assets/bait_pickable/Pickable_worms",
        "Assets/rod/rod_copper", "Assets/rod/rod_finewood", "Assets/rod/rod_ancientbark", "Assets/rod/rod_siilver",
    };

    static VdwModelImporter()
    {
        if (File.Exists(Trigger)) EditorApplication.delayCall += RunWhenReady;
    }

    static void RunWhenReady()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode)
        {
            EditorApplication.delayCall += RunWhenReady;
            return;
        }
        if (!File.Exists(Trigger)) return;
        AssetDatabase.DeleteAsset(Trigger);
        Run();
    }

    [MenuItem("Deep Waters/Import Models And Build Bundles")]
    public static void Run()
    {
        var log = new StringBuilder();
        log.AppendLine($"Deep Waters model import {DateTime.Now}");
        AssetDatabase.Refresh();
        int ok = 0;
        try
        {
            AssetDatabase.StartAssetEditing();
            foreach (var e in Entries) SetupImporters(e, log);
        }
        finally { AssetDatabase.StopAssetEditing(); }
        AssetDatabase.Refresh();

        foreach (var e in Entries)
        {
            try { if (BuildPrefab(e, log)) ok++; }
            catch (Exception ex) { log.AppendLine($"!! {e.Key}: {ex}"); }
        }

        // Sounds (e.g. horn_of_aegir.ogg): every audio file in Assets/DeepWaters/Sounds goes into the buffs bundle, found
        // in game by its file name.
        if (AssetDatabase.IsValidFolder(Root + "/Sounds"))
            foreach (var g in AssetDatabase.FindAssets("t:AudioClip", new[] { Root + "/Sounds" }))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(path) is AudioImporter ai && !ai.forceToMono)
                {
                    ai.forceToMono = true;          // played in the world (3D): one channel
                    ai.SaveAndReimport();
                }
                AssetImporter.GetAtPath(path).SetAssetBundleNameAndVariant("buffs", "");
                log.AppendLine($"sound {path} -> buffs");
            }

        // Loose textures (e.g. the JÃ¶rmungandr's Scale cape maps put on a vanilla cape): every texture in
        // Assets/DeepWaters/Textures goes into the buffs bundle, found in game by its file name. *_Normal is a normal map,
        // *_MetallicSmoothness linear.
        if (AssetDatabase.IsValidFolder(Root + "/Textures"))
            foreach (var g in AssetDatabase.FindAssets("t:Texture2D", new[] { Root + "/Textures" }))
            {
                var path = AssetDatabase.GUIDToAssetPath(g);
                if (AssetImporter.GetAtPath(path) is TextureImporter ti)
                {
                    bool normal = path.Contains("_Normal"), linear = normal || path.Contains("_MetallicSmoothness");
                    var type = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                    if (ti.textureType != type || ti.sRGBTexture == linear || ti.maxTextureSize != 512)
                    {
                        ti.textureType = type; ti.sRGBTexture = !linear; ti.maxTextureSize = 512;
                        ti.SaveAndReimport();
                    }
                }
                AssetImporter.GetAtPath(path).SetAssetBundleNameAndVariant("buffs", "");
                log.AppendLine($"texture {path} -> buffs");
            }

        // The old prefabs these replace leave the bundles (their files stay).
        foreach (var folder in Replaced.Where(AssetDatabase.IsValidFolder))
        {
            var paths = AssetDatabase.FindAssets("", new[] { folder }).Select(AssetDatabase.GUIDToAssetPath).Append(folder).Distinct();
            foreach (var p in paths)
            {
                var imp = AssetImporter.GetAtPath(p);
                if (imp != null && !string.IsNullOrEmpty(imp.assetBundleName))
                {
                    imp.SetAssetBundleNameAndVariant("", "");
                    log.AppendLine($"   untagged old {p}");
                }
            }
        }
        AssetDatabase.RemoveUnusedAssetBundleNames();
        AssetDatabase.SaveAssets();
        log.AppendLine($"{ok}/{Entries.Length} prefabs made.");

        // Build every bundle.
        try
        {
            Directory.CreateDirectory(OutDir);
            var target = EditorUserBuildSettings.activeBuildTarget;
            if (target != BuildTarget.StandaloneWindows && target != BuildTarget.StandaloneWindows64) target = BuildTarget.StandaloneWindows64;
            var manifest = BuildPipeline.BuildAssetBundles(OutDir, BuildAssetBundleOptions.ChunkBasedCompression, target);
            if (manifest == null) throw new Exception("BuildAssetBundles returned null - see the Console.");
            log.AppendLine($"Built bundles for {target} in {Path.GetFullPath(OutDir)}:");
            foreach (var b in manifest.GetAllAssetBundles())
            {
                var file = Path.Combine(OutDir, b);
                log.AppendLine($"   {b}  {new FileInfo(file).Length / 1048576.0:F1} MB");
            }

            // Install them in the Test profile (the mod loads <name>.bundle from its Models folder).
            if (Directory.Exists(ModelsDir))
            {
                var backup = Path.Combine(ModelsDir, "bundles_backup_" + DateTime.Now.ToString("yyyyMMdd_HHmmss"));
                foreach (var b in manifest.GetAllAssetBundles())
                {
                    var dst = Path.Combine(ModelsDir, b + ".bundle");
                    if (File.Exists(dst))
                    {
                        Directory.CreateDirectory(backup);
                        File.Copy(dst, Path.Combine(backup, b + ".bundle"), true);
                    }
                    File.Copy(Path.Combine(OutDir, b), dst, true);
                    log.AppendLine($"   installed {dst}");
                }
                if (Directory.Exists(backup)) log.AppendLine($"   previous bundles backed up to {backup}");
            }
            else log.AppendLine($"!! Models folder not found, bundles not installed: {ModelsDir}");
        }
        catch (Exception ex) { log.AppendLine($"!! bundle build failed: {ex}"); }

        File.WriteAllText("vdw_import_report.txt", log.ToString());
        Debug.Log("Deep Waters import finished:\n" + log);
    }

    // ------------------------------------------------------------------ importers

    static string Folder(Entry e) => $"{Root}/{e.Key}";
    static string Fbx(Entry e) => $"{Folder(e)}/{e.Key}_model.fbx";

    static IEnumerable<string> Textures(Entry e) =>
        Directory.GetFiles(Folder(e)).Select(p => p.Replace('\\', '/')).Where(p => !p.EndsWith(".meta") && !p.EndsWith(".fbx", StringComparison.OrdinalIgnoreCase));

    // A model made of several meshes can have a texture set per mesh, named after it ("mound_Unity_Albedo" for the
    // mesh "mound"); prefix null = the model's only set.
    static string FindTex(Entry e, string suffix, string prefix = null) =>
        Textures(e).FirstOrDefault(p =>
        {
            var n = Path.GetFileNameWithoutExtension(p);
            return n.EndsWith(suffix, StringComparison.OrdinalIgnoreCase) &&
                   (prefix == null || n.StartsWith(prefix + "_Unity_", StringComparison.OrdinalIgnoreCase));
        });

    static bool HasSet(Entry e, string prefix) => FindTex(e, "_Albedo", prefix) != null;

    static void SetupImporters(Entry e, StringBuilder log)
    {
        void Tex(string suffix, Action<TextureImporter> setup)
        {
            foreach (var p in Textures(e).Where(t => Path.GetFileNameWithoutExtension(t).EndsWith(suffix, StringComparison.OrdinalIgnoreCase)))
            {
            if (!(AssetImporter.GetAtPath(p) is TextureImporter ti)) continue;
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = true; ti.alphaIsTransparency = false;
            ti.maxTextureSize = e.TexSize; ti.mipmapEnabled = true;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            setup(ti);
            ti.SaveAndReimport();
            }
        }
        Tex("_Albedo", ti => ti.alphaIsTransparency = e.Key == "bait_fly");
        Tex("_MetallicSmoothness", ti => ti.sRGBTexture = false);
        Tex("_Normal", ti => ti.textureType = TextureImporterType.NormalMap);
        Tex("_Emission", ti => { });

        if (!(AssetImporter.GetAtPath(Fbx(e)) is ModelImporter mi)) { log.AppendLine($"!! {e.Key}: no {Fbx(e)}"); return; }
        mi.globalScale = 1f;
        mi.useFileScale = true;
        mi.isReadable = true;
        mi.importCameras = false;
        mi.importLights = false;
        mi.importBlendShapes = false;
        mi.materialImportMode = ModelImporterMaterialImportMode.None;
        // The small procedural lures and trailers: Unity works out their normals itself (smooth under 60 degrees, so
        // knapped flint and blade edges stay sharp) rather than trusting the file's, which it rejected for tiny parts.
        bool lure = e.Key.StartsWith("bait_lure_") || e.Key.StartsWith("bait_trailer_");
        mi.importNormals = lure ? ModelImporterNormals.Calculate : ModelImporterNormals.Import;
        if (lure) mi.normalSmoothingAngle = 60f;
        switch (e.Kind)
        {
            case Kind.Animated:
                mi.animationType = ModelImporterAnimationType.Generic;
                mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                mi.importAnimation = true;
                break;
            case Kind.Rigged:   // the mod poses the rod's bones itself
                mi.animationType = ModelImporterAnimationType.Generic;
                mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
                mi.importAnimation = false;
                break;
            default:
                mi.animationType = ModelImporterAnimationType.None;
                mi.importAnimation = false;
                break;
        }
        mi.SaveAndReimport();
        if (e.Kind == Kind.Animated)
        {
            var clips = mi.defaultClipAnimations;
            foreach (var c in clips) { c.loopTime = true; c.loopPose = false; }
            mi.clipAnimations = clips;
            mi.SaveAndReimport();
        }
    }

    // ------------------------------------------------------------------ material, controller, prefab

    static Material MakeMaterial(string path, Entry e, bool fade, string prefix = null)
    {
        var alb = Load<Texture2D>(FindTex(e, "_Albedo", prefix));
        var ms = Load<Texture2D>(FindTex(e, "_MetallicSmoothness", prefix));
        var nrm = Load<Texture2D>(FindTex(e, "_Normal", prefix));
        var em = Load<Texture2D>(FindTex(e, "_Emission", prefix));

        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        bool isNew = m == null;
        if (isNew) m = new Material(Shader.Find("Standard"));
        m.shader = Shader.Find("Standard");
        m.color = Color.white;
        m.SetTexture("_MainTex", alb);
        if (ms != null)
        {
            m.SetTexture("_MetallicGlossMap", ms); m.EnableKeyword("_METALLICGLOSSMAP");
            m.SetFloat("_GlossMapScale", 1f); m.SetFloat("_SmoothnessTextureChannel", 0f);
        }
        if (nrm != null) { m.SetTexture("_BumpMap", nrm); m.SetFloat("_BumpScale", 1f); m.EnableKeyword("_NORMALMAP"); }
        if (em != null && e.Glow > 0f)
        {
            m.SetTexture("_EmissionMap", em);
            m.SetColor("_EmissionColor", Color.white * e.Glow);
            m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
        }
        if (fade)
        {
            // queue first: switching to Fade while still in the opaque queue warns "render queue outside the range"
            m.renderQueue = (int)RenderQueue.Transparent;
            m.SetFloat("_Mode", 2f);
            m.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
            m.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
            m.SetInt("_ZWrite", 0);
            m.DisableKeyword("_ALPHATEST_ON"); m.EnableKeyword("_ALPHABLEND_ON"); m.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        }
        else
        {
            // opaque (and back to it, for a material reused from an earlier import)
            m.SetFloat("_Mode", 0f);
            m.SetInt("_SrcBlend", (int)BlendMode.One);
            m.SetInt("_DstBlend", (int)BlendMode.Zero);
            m.SetInt("_ZWrite", 1);
            m.DisableKeyword("_ALPHATEST_ON"); m.DisableKeyword("_ALPHABLEND_ON"); m.DisableKeyword("_ALPHAPREMULTIPLY_ON");
            m.renderQueue = -1;
        }
        if (isNew) AssetDatabase.CreateAsset(m, path); else EditorUtility.SetDirty(m);
        return m;
    }

    static AnimatorController MakeController(Entry e, StringBuilder log)
    {
        var clips = AssetDatabase.LoadAllAssetsAtPath(Fbx(e)).OfType<AnimationClip>()
            .Where(c => !c.name.StartsWith("__preview__")).ToList();
        var path = $"{Folder(e)}/{e.Key}_Animator.controller";
        AssetDatabase.DeleteAsset(path);
        var ctrl = AnimatorController.CreateAnimatorControllerAtPath(path);
        ctrl.AddParameter("Speed", AnimatorControllerParameterType.Float);
        ctrl.parameters = ctrl.parameters.Select(p => { if (p.name == "Speed") p.defaultFloat = 1f; return p; }).ToArray();
        var sm = ctrl.layers[0].stateMachine;
        AnimatorState swim = null;
        var names = new List<string>();
        foreach (var clip in clips)
        {
            string state = clip.name.Contains("|") ? clip.name.Substring(clip.name.LastIndexOf('|') + 1) : clip.name;
            var st = sm.AddState(state);
            st.motion = clip;                    // each state plays its own clip
            st.speedParameterActive = true;
            st.speedParameter = "Speed";
            if (state == "Swim") swim = st;
            names.Add($"{state} ({clip.length:F2}s{(clip.isLooping ? ", loops" : "")})");
        }
        if (swim != null) sm.defaultState = swim;
        log.AppendLine($"   states: {string.Join(", ", names)}{(swim == null ? "  !! no Swim clip" : "")}");
        return ctrl;
    }

    static bool BuildPrefab(Entry e, StringBuilder log)
    {
        var src = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx(e));
        if (src == null) { log.AppendLine($"!! {e.Key}: FBX didn't import"); return false; }
        log.AppendLine($"{e.Key}  [{e.Bundle}]  {e.Kind}");

        var mat = MakeMaterial($"{Folder(e)}/{e.Key}.mat", e, false);
        var wings = e.Key == "bait_fly" ? MakeMaterial($"{Folder(e)}/{e.Key}_wings.mat", e, true) : null;

        var go = (GameObject)UnityEngine.Object.Instantiate(src);
        go.name = e.Key;
        go.transform.localScale = Vector3.one * e.Scale;   // the mod uses the prefab at exactly this size
        try
        {
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var mesh = r is SkinnedMeshRenderer s ? s.sharedMesh : r.GetComponent<MeshFilter>()?.sharedMesh;
                int n = mesh != null ? Math.Max(1, mesh.subMeshCount) : 1;
                // A mesh with its own texture set ("mound_Unity_*" on the mesh "mound") gets its own material.
                // "oar.L" and "oar.R" share the set "oar_Unity_*": the name up to its first dot counts too.
                string setName = HasSet(e, r.gameObject.name) ? r.gameObject.name : r.gameObject.name.Split('.')[0];
                var own = HasSet(e, setName)
                    ? MakeMaterial($"{Folder(e)}/{e.Key}_{setName}.mat", e, false, setName) : null;
                // the fly's wings (see-through) are the slot whose vertices ride the Wing bones - Unity doesn't keep
                // Blender's slot order, and assuming slot 1 put the see-through material on the body
                bool IsWing(int i)
                {
                    if (!(r is SkinnedMeshRenderer sk) || mesh == null || i >= mesh.subMeshCount) return i == 1;
                    var tris = mesh.GetTriangles(i); var bw = mesh.boneWeights;
                    if (tris.Length == 0 || bw.Length == 0) return i == 1;
                    int onWing = tris.Count(v => { int b = bw[v].boneIndex0; return b < sk.bones.Length && sk.bones[b] != null && sk.bones[b].name.StartsWith("Wing"); });
                    return onWing > tris.Length / 2;
                }
                r.sharedMaterials = Enumerable.Range(0, n).Select(i => own ?? (wings != null && IsWing(i) ? wings : mat)).ToArray();
                if (wings != null) log.AppendLine($"   wings in slot(s) {string.Join(",", Enumerable.Range(0, n).Where(IsWing))} of {n}");
                r.shadowCastingMode = ShadowCastingMode.On;
                if (r is SkinnedMeshRenderer smr) smr.updateWhenOffscreen = false;
            }

            var animator = go.GetComponent<Animator>();
            if (e.Kind == Kind.Animated)
            {
                if (animator == null) animator = go.AddComponent<Animator>();
                animator.runtimeAnimatorController = MakeController(e, log);
                animator.applyRootMotion = false;
                animator.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
            }
            else if (animator != null && e.Kind == Kind.Static) UnityEngine.Object.DestroyImmediate(animator);

            var renderers = go.GetComponentsInChildren<Renderer>(true);
            var b = renderers.Length > 0 ? renderers.Select(r => r.bounds).Aggregate((x, y) => { x.Encapsulate(y); return x; }) : new Bounds();
            log.AppendLine($"   scale {e.Scale}, size {b.size.x * 100:F1} x {b.size.y * 100:F1} x {b.size.z * 100:F1} cm, " +
                           $"{renderers.Length} renderer(s) ({string.Join(", ", renderers.Select(r => r.GetType().Name).Distinct())}), " +
                           $"{go.GetComponentsInChildren<Transform>(true).Length} transforms, maps: " +
                           string.Join(" ", new[] { "_Albedo", "_MetallicSmoothness", "_Normal", "_Emission" }.Where(s => FindTex(e, s) != null).Select(s => s.TrimStart('_'))));

            var prefabPath = $"{Folder(e)}/{e.Key}.prefab";
            PrefabUtility.SaveAsPrefabAsset(go, prefabPath);
            AssetImporter.GetAtPath(prefabPath).SetAssetBundleNameAndVariant(e.Bundle, "");
            return true;
        }
        finally { UnityEngine.Object.DestroyImmediate(go); }
    }

    static T Load<T>(string path) where T : UnityEngine.Object => path == null ? null : AssetDatabase.LoadAssetAtPath<T>(path);
}
