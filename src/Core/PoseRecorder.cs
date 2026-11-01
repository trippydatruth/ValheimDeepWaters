using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// vdw_debug pose: records the local player's real skeleton while you move (run, sit, crouch...), so gear can be
    /// tested in Blender against Valheim's actual poses (art-tools/valheim_pose.py reads the files).
    /// Each recording is one file, config/ValheimDeepWaters/poses/pose_[name].json:
    ///   {"rest": {bone: [x,y,z, qx,qy,qz,qw]}, "clips": {name: [frame, ...]}}  (frame = the same per-bone list)
    /// Everything is in the player's own space (its position and facing taken out), so frames line up whatever
    /// way you walk. "rest" is the bind pose the body mesh is skinned to (the same rest the gear is weighted on).
    /// </summary>
    internal static class PoseRecorder
    {
        internal static string Dir => Path.Combine(Plugin.ConfigDirectory, "poses");

        internal static string Start(Player p, string name, float seconds, float delay, float fps)
        {
            var body = p.GetComponent<VisEquipment>()?.m_bodyModel;
            if (body == null || body.sharedMesh == null) return "No body model to record.";
            if (p.GetComponent<Recorder>() != null) return "Already recording; wait for it to finish.";
            name = new string(name.Where(c => char.IsLetterOrDigit(c) || c == '_' || c == '-').ToArray());
            if (name.Length == 0) return "Give the recording a name (letters, digits, _ or -).";
            var r = p.gameObject.AddComponent<Recorder>();
            r.Init(p, body, name, Mathf.Clamp(seconds, 0.2f, 30f), Mathf.Clamp(delay, 0f, 30f), Mathf.Clamp(fps, 1f, 60f));
            return $"Recording '{name}' for {r.Seconds:0.#} s at {r.Fps:0} fps, starting in {r.Delay:0.#} s. Close the console and do the move.";
        }

        static void Append(StringBuilder sb, Transform root, Matrix4x4 m, string name, bool first)
        {
            // m is a bone's matrix in world space; written in the player's space
            var local = root.worldToLocalMatrix * m;
            Vector3 pos = local.GetColumn(3);
            var rot = Quaternion.LookRotation(local.GetColumn(2), local.GetColumn(1));
            sb.Append(first ? "" : ",").Append('"').Append(name).Append("\":[");
            sb.Append(string.Join(",", new[] { pos.x, pos.y, pos.z, rot.x, rot.y, rot.z, rot.w }.Select(v => v.ToString("R", CultureInfo.InvariantCulture))));
            sb.Append(']');
        }

        class Recorder : MonoBehaviour
        {
            Player _p = null!; SkinnedMeshRenderer _body = null!; string _name = "";
            internal float Seconds, Delay, Fps;
            float _t, _next; readonly List<string> _frames = new List<string>(); bool _announced;

            internal void Init(Player p, SkinnedMeshRenderer body, string name, float seconds, float delay, float fps)
            { _p = p; _body = body; _name = name; Seconds = seconds; Delay = delay; Fps = fps; _t = -delay; }

            void LateUpdate()   // after the animator has posed the bones this frame
            {
                if (_p == null || _body == null) { Destroy(this); return; }
                _t += Time.deltaTime;
                if (_t < 0f) return;
                if (!_announced) { _announced = true; _p.Message(MessageHud.MessageType.Center, $"Recording '{_name}'..."); }
                if (_t >= _next)
                {
                    _next += 1f / Fps;
                    var sb = new StringBuilder("{"); bool first = true;
                    foreach (var b in _body.bones)
                    {
                        if (b == null) continue;
                        Append(sb, _p.transform, b.localToWorldMatrix, b.name, first); first = false;
                    }
                    _frames.Add(sb.Append('}').ToString());
                }
                if (_t >= Seconds) { Save(); Destroy(this); }
            }

            void Save()
            {
                // rest: the bind pose, world matrix of each bone = mesh's localToWorld * inverse(bindpose)
                var sb = new StringBuilder("{\"rest\":{");
                var binds = _body.sharedMesh.bindposes; bool first = true;
                var bones = _body.bones;
                for (int i = 0; i < bones.Length && i < binds.Length; i++)
                {
                    if (bones[i] == null) continue;
                    Append(sb, _p.transform, _body.transform.localToWorldMatrix * binds[i].inverse, bones[i].name, first); first = false;
                }
                sb.Append("},\"clips\":{\"").Append(_name).Append("\":[").Append(string.Join(",", _frames)).Append("]}}");
                Directory.CreateDirectory(Dir);
                string path = Path.Combine(Dir, "pose_" + _name + ".json");
                File.WriteAllText(path, sb.ToString());
                Plugin.Log.LogInfo($"Pose recording '{_name}': {_frames.Count} frames of {bones.Length} bones -> {path}");
                _p.Message(MessageHud.MessageType.Center, $"Saved '{_name}' ({_frames.Count} frames)");
            }
        }
    }
}
