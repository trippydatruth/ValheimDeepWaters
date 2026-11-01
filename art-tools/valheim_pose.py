# Poses the gear rig's Armature as Valheim does, from bone poses recorded in the game itself (vdw_debug pose <name>,
# PoseRecorder.cs: a folder of pose_<name>.json in BepInEx/config/ValheimDeepWaters/poses). The older Unity sampler
# (VdwPoseSampler.cs) retargets the rip's clips and distorts the arms and legs; don't trust it. Import it from a script:
#   import valheim_pose; P = valheim_pose.Poses(folder_or_json, armature); P.apply("run", 3); P.reset()
# The Unity -> Blender mapping is found from the rest pose: the bone heads matched by name, fitted with scale, any turn and
# the left/right-handed mirror; each bone's turn from its rest is carried over through that mapping.
import json, numpy as np
from mathutils import Matrix, Quaternion, Vector

class Poses:
    def __init__(self, path, arm):
        self.arm = arm; self.data = self._load(path)
        arm.animation_data_clear()   # keyed poses in the blend (Game_anims_*) would override the ones set here
        rest = self.data["rest"]
        for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
        names = [b.name for b in arm.data.bones if b.name in rest]
        U = np.array([rest[n][:3] for n in names]); B = np.array([tuple(arm.matrix_world @ arm.data.bones[n].head_local) for n in names])
        mu, mb = U.mean(0), B.mean(0); H = (B - mb).T @ (U - mu); Uu, S, Vt = np.linalg.svd(H)
        R = Uu @ Vt                                          # orthogonal, mirror allowed (Unity is left-handed)
        s = S.sum() / ((U - mu) ** 2).sum(); t = mb - s * R @ mu
        self.R, self.s, self.t = R, s, t
        err = np.linalg.norm((s * (R @ U.T)).T + t - B, axis=1)
        print(f"POSE mapping: {len(names)} bones, mirror {np.linalg.det(R) < 0}, scale {s:.4f}, fit {err.mean() * 100:.2f} cm (max {err.max() * 100:.2f})")
        off = [f"{n} {e * 100:.1f} cm" for n, e in zip(names, err) if e > 0.01]
        if off: print("POSE WARNING: these bones aren't where the game has them (moved in Edit Mode?) - fix_rig_rest.py puts them back:", ", ".join(off))
        self.rest_q = {n: self._rot(rest[n]) for n in names}
        self.names = names

    @staticmethod
    def _load(path):
        """one JSON file, or a folder of them (the game's vdw_debug pose recordings, pose_<name>.json): clips merged,
        rest from the first file"""
        import os
        if not os.path.isdir(path): return json.load(open(path))
        data = None
        for f in sorted(os.listdir(path)):
            if not f.endswith(".json"): continue
            d = json.load(open(os.path.join(path, f)))
            if data is None: data = {"rest": d["rest"], "clips": {}}
            data["clips"].update(d["clips"])
        if data is None: raise SystemExit("no pose recordings in " + path)
        print("POSE clips:", {k: len(v) for k, v in data["clips"].items()})
        return data

    def _rot(self, v):
        q = Quaternion((v[6], v[3], v[4], v[5])).to_matrix()
        M = np.array(q); return self.R @ M @ self.R.T if hasattr(self, "R") else M
    def _pos(self, v): return Vector(self.s * self.R @ np.array(v[:3]) + self.t)

    def frames(self, clip): return len(self.data["clips"][clip])

    def reset(self):
        for pb in self.arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)

    def apply(self, clip, frame):
        import bpy
        self.reset(); bpy.context.view_layer.update()
        pose = self.data["clips"][clip][frame]; rest = self.data["rest"]
        aw_inv = self.arm.matrix_world.inverted()
        def depth(b): d = 0; p = b.parent
        order = sorted(self.names, key=lambda n: len(self.arm.data.bones[n].parent_recursive))
        for n in order:
            if n not in pose: continue
            Ru0 = np.array(Quaternion((rest[n][6], rest[n][3], rest[n][4], rest[n][5])).to_matrix())
            Ru1 = np.array(Quaternion((pose[n][6], pose[n][3], pose[n][4], pose[n][5])).to_matrix())
            delta = self.R @ (Ru1 @ Ru0.T) @ self.R.T         # the bone's turn since rest, in Blender's world
            bone = self.arm.data.bones[n]
            rest_w = self.arm.matrix_world @ bone.matrix_local
            rot = Matrix(delta.tolist()) @ rest_w.to_3x3().normalized()
            M = rot.to_4x4(); M.translation = self._pos(pose[n])
            self.arm.pose.bones[n].matrix = aw_inv @ M
            bpy.context.view_layer.update()
