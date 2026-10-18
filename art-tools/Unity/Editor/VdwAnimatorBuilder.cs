// Deep Waters: builds an Animator Controller for an animated model (fish, bait) straight from its FBX.
// Put this file in any "Editor" folder of your Unity project. Then select one or more FBX files in the Project
// window and use  Assets > Deep Waters > Build Animator From FBX.
//
// For each FBX it:
//   - turns on Loop Time for every clip (Swim, Thrash, Flop, Hooked all loop)
//   - makes "<fbx name>_Animator.controller" next to the FBX, with one state per clip, each state's Motion set to
//     ITS OWN clip (named after the end of the clip name: "Armature|Armature|Thrash" -> state "Thrash"),
//     Swim as the default state, and a float parameter "Speed" driving the playback speed
//   - if a prefab with the FBX's model already uses an Animator, nothing else is touched: assign the controller to it.
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

public static class VdwAnimatorBuilder
{
    [MenuItem("Assets/Deep Waters/Build Animator From FBX")]
    private static void Build()
    {
        foreach (var obj in Selection.objects)
        {
            string path = AssetDatabase.GetAssetPath(obj);
            if (!path.ToLowerInvariant().EndsWith(".fbx")) continue;

            // 1. every clip loops
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            var clipsInfo = importer.clipAnimations.Length > 0 ? importer.clipAnimations : importer.defaultClipAnimations;
            foreach (var c in clipsInfo) { c.loopTime = true; c.loopPose = false; }
            importer.clipAnimations = clipsInfo;
            importer.SaveAndReimport();

            // 2. the clips themselves (not the editor preview clips)
            var clips = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>()
                .Where(c => !c.name.StartsWith("__preview__")).ToList();
            if (clips.Count == 0) { Debug.LogWarning($"Deep Waters: {path} has no animation clips."); continue; }

            // 3. the controller: one state per clip, each with its own Motion
            string ctrlPath = path.Substring(0, path.Length - 4) + "_Animator.controller";
            AssetDatabase.DeleteAsset(ctrlPath);
            var ctrl = AnimatorController.CreateAnimatorControllerAtPath(ctrlPath);
            ctrl.AddParameter("Speed", AnimatorControllerParameterType.Float);
            ctrl.parameters = ctrl.parameters.Select(p => { if (p.name == "Speed") p.defaultFloat = 1f; return p; }).ToArray();
            var sm = ctrl.layers[0].stateMachine;
            AnimatorState swim = null;
            foreach (var clip in clips)
            {
                string state = clip.name.Contains("|") ? clip.name.Substring(clip.name.LastIndexOf('|') + 1) : clip.name;
                var st = sm.AddState(state);
                st.motion = clip;                  // each state plays its own clip
                st.speedParameterActive = true;
                st.speedParameter = "Speed";
                if (state == "Swim") swim = st;
                Debug.Log($"Deep Waters: {System.IO.Path.GetFileName(ctrlPath)}: state '{state}' -> clip '{clip.name}'");
            }
            if (swim != null) sm.defaultState = swim;
            AssetDatabase.SaveAssets();
            Debug.Log($"Deep Waters: built {ctrlPath} with {clips.Count} states. Assign it to the Animator on your prefab.");
        }
    }

    [MenuItem("Assets/Deep Waters/Build Animator From FBX", true)]
    private static bool Validate() => Selection.objects.Any(o => AssetDatabase.GetAssetPath(o).ToLowerInvariant().EndsWith(".fbx"));
}
