// Plays Valheim's own (humanoid) player animation clips from the game rip on our gear rig and writes the bones' world
// poses to JSON, for posing gear in Blender exactly as the game does (run, sit, crouch...). Works in a temporary folder
// (Assets/_PoseTmp, removed after); nothing else in the project changes.
//   Unity.exe -batchmode -nographics -projectPath <project> -executeMethod VdwPoseSampler.Run -quit
//   env: VDW_RIG (an FBX with the player skeleton, e.g. a gear model), VDW_ANIMS ("name=path;..." .anim files),
//        VDW_POSE_OUT (json path), VDW_FRAMES (samples per clip, default 8)
using System;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

public static class VdwPoseSampler
{
    const string Tmp = "Assets/_PoseTmp";

    public static void Run()
    {
        string rig = Environment.GetEnvironmentVariable("VDW_RIG");
        string anims = Environment.GetEnvironmentVariable("VDW_ANIMS");
        string outPath = Environment.GetEnvironmentVariable("VDW_POSE_OUT");
        int frames = int.TryParse(Environment.GetEnvironmentVariable("VDW_FRAMES"), out var f) ? f : 8;
        if (AssetDatabase.IsValidFolder(Tmp)) AssetDatabase.DeleteAsset(Tmp);
        AssetDatabase.CreateFolder("Assets", "_PoseTmp");
        try
        {
            File.Copy(rig, Tmp + "/rig.fbx");
            AssetDatabase.ImportAsset(Tmp + "/rig.fbx", ImportAssetOptions.ForceSynchronousImport);
            var mi = (ModelImporter)AssetImporter.GetAtPath(Tmp + "/rig.fbx");
            // Valheim's bone names to Unity's human bones (the automatic match trips over our extra skirt bones)
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(Tmp + "/rig.fbx");
            var all = model.GetComponentsInChildren<Transform>(true);
            var map = new (string human, string bone)[] {
                ("Hips","Hips"),("Spine","Spine"),("Chest","Spine1"),("UpperChest","Spine2"),("Neck","Neck"),("Head","Head"),("Jaw","Jaw"),
                ("LeftShoulder","LeftShoulder"),("LeftUpperArm","LeftArm"),("LeftLowerArm","LeftForeArm"),("LeftHand","LeftHand"),
                ("RightShoulder","RightShoulder"),("RightUpperArm","RightArm"),("RightLowerArm","RightForeArm"),("RightHand","RightHand"),
                ("LeftUpperLeg","LeftUpLeg"),("LeftLowerLeg","LeftLeg"),("LeftFoot","LeftFoot"),("LeftToes","LeftToeBase"),
                ("RightUpperLeg","RightUpLeg"),("RightLowerLeg","RightLeg"),("RightFoot","RightFoot"),("RightToes","RightToeBase") };
            var names = all.Select(t => t.name).ToHashSet();
            var missing = map.Where(m => !names.Contains(m.bone)).Select(m => m.bone).ToList();
            if (missing.Count > 0) Debug.LogWarning("VDWPOSE: rig lacks " + string.Join(", ", missing) + " / has " + string.Join(", ", names));
            var hd = mi.humanDescription;
            hd.human = map.Where(m => names.Contains(m.bone)).Select(m => new HumanBone { humanName = m.human, boneName = m.bone, limit = new HumanLimit { useDefaultValues = true } }).ToArray();
            hd.skeleton = all.Select(t => new SkeletonBone { name = t.name, position = t.localPosition, rotation = t.localRotation, scale = t.localScale }).ToArray();
            hd.upperArmTwist = 0.5f; hd.lowerArmTwist = 0.5f; hd.upperLegTwist = 0.5f; hd.lowerLegTwist = 0.5f; hd.armStretch = 0.05f; hd.legStretch = 0.05f; hd.feetSpacing = 0f;
            mi.animationType = ModelImporterAnimationType.Human;
            mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            mi.humanDescription = hd;
            mi.SaveAndReimport();
            var avatar = AssetDatabase.LoadAllAssetsAtPath(Tmp + "/rig.fbx").OfType<Avatar>().FirstOrDefault();
            if (avatar == null || !avatar.isHuman) { Debug.LogError("VDWPOSE: the rig didn't make a humanoid avatar"); return; }
            var go = (GameObject)UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(Tmp + "/rig.fbx"));
            var animator = go.GetComponent<Animator>() ?? go.AddComponent<Animator>();
            animator.avatar = avatar; animator.applyRootMotion = false; animator.enabled = true;
            animator.Rebind();
            var bones = go.GetComponentsInChildren<Transform>(true);

            var sb = new StringBuilder("{\"rest\":");
            Dump(sb, bones);
            sb.Append(",\"clips\":{");
            bool firstClip = true;
            foreach (var entry in anims.Split(';').Where(s => s.Contains("=")))
            {
                var name = entry.Substring(0, entry.IndexOf('=')); var src = entry.Substring(entry.IndexOf('=') + 1);
                string dst = Tmp + "/" + name + ".anim";
                File.Copy(src, dst);
                AssetDatabase.ImportAsset(dst, ImportAssetOptions.ForceSynchronousImport);
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(dst);
                if (clip == null) { Debug.LogWarning("VDWPOSE: couldn't load " + src); continue; }
                var graph = PlayableGraph.Create("vdw_pose");
                graph.SetTimeUpdateMode(DirectorUpdateMode.Manual);
                var output = AnimationPlayableOutput.Create(graph, "out", animator);
                var play = AnimationClipPlayable.Create(graph, clip);
                play.SetApplyFootIK(false);
                output.SetSourcePlayable(play);
                sb.Append(firstClip ? "" : ",").Append('"').Append(name).Append("\":[");
                firstClip = false;
                var thigh = bones.First(b => b.name == "LeftUpLeg"); var restRot = thigh.rotation;
                bool moved = false;
                for (int i = 0; i < frames; i++)
                {
                    float time = clip.length * i / frames;
                    play.SetTime(time);
                    graph.Evaluate(0f);
                    // in batch mode the graph doesn't move the rig: sample through AnimationMode (every frame)
                    if (!AnimationMode.InAnimationMode()) AnimationMode.StartAnimationMode();
                    AnimationMode.BeginSampling(); AnimationMode.SampleAnimationClip(go, clip, time); AnimationMode.EndSampling();
                    moved |= Quaternion.Angle(thigh.rotation, restRot) > 0.01f;
                    if (i > 0) sb.Append(',');
                    Dump(sb, bones);
                }
                if (!moved) Debug.LogWarning("VDWPOSE: " + name + " didn't move the rig");
                sb.Append(']');
                graph.Destroy();
                Debug.Log($"VDWPOSE: {name} ({clip.length:0.00} s, humanoid {clip.humanMotion}) sampled {frames} times");
            }
            sb.Append("}}");
            File.WriteAllText(outPath, sb.ToString());
            Debug.Log("VDWPOSE: wrote " + outPath);
            UnityEngine.Object.DestroyImmediate(go);
        }
        finally { AssetDatabase.DeleteAsset(Tmp); }
    }

    static void Dump(StringBuilder sb, Transform[] bones)
    {
        sb.Append('{');
        bool first = true;
        foreach (var t in bones)
        {
            var p = t.position; var q = t.rotation;
            sb.Append(first ? "" : ",").Append('"').Append(t.name).Append("\":[");
            sb.Append(string.Join(",", new[] { p.x, p.y, p.z, q.x, q.y, q.z, q.w }.Select(v => v.ToString("R", CultureInfo.InvariantCulture))));
            sb.Append(']');
            first = false;
        }
        sb.Append('}');
    }
}
