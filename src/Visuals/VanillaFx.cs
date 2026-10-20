using Jotunn.Managers;
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Vanilla weapon and staff effects (docs/vanilla-vfx.md) on the legendary and boss fish and the top rods only.
    /// Each effect is the vanilla item's own particle object, copied at runtime from the game's prefab (never into our
    /// files), re-aimed to emit from our model's surface (its skinned or plain mesh - on a rigged rod they follow the
    /// bending blank), with at most one light. Shown on the fish item (landed / dropped), on the fish while it fights
    /// on the line, and on the rod in hand.
    /// </summary>
    internal static class VanillaFx
    {
        private sealed class Fx
        {
            public string Prefab = "", Path = "";
            public bool Light;              // keep the effect's own point light (one per effect)
            public Color? Tint;             // recolour the light (and the particles' start colour)
            public float Rate = 1f;         // extra emission multiplier
            public float Size = 1f;         // extra particle size multiplier
            public float Orbit;             // >0: particles circle the body along its length at this speed
            public bool AlongBody;          // emit from a thin box down the body's length (not the mesh surface), no throw, little jitter
            public bool Ribbon;             // keep the vanilla ribbon trails (lightning joined point to point) instead of per-particle sparks
            public float Life = 1f;         // particle lifetime multiplier (shorter flames)
            public string[] Skip = Array.Empty<string>();   // child objects of the effect left out (e.g. a big glow sprite)
            public bool Vary;               // on a rod's bones: each copy a different size and height (patchy, not an even line)
            public Fx(string prefab, string path, bool light = false, Color? tint = null, float rate = 1f, float size = 1f) { Prefab = prefab; Path = path; Light = light; Tint = tint; Rate = rate; Size = size; }
        }

        private static readonly Color Frost = new(0.58f, 0.91f, 1f), SkyBolt = new(0.6f, 0.85f, 1f), FrostCloud = new(0.78f, 0.9f, 1f, 0.55f),
            BrightBolt = new(0.75f, 0.92f, 1f), StormPuff = new(0.72f, 0.85f, 1f, 0.7f);

        /// <summary>By fish id: the boss fish take their boss's element, the three legendaries their name's.</summary>
        private static readonly Dictionary<string, Fx[]> FishFx = new()
        {
            ["eikthyr_elver"] = new[] { new Fx("SwordNiedhoggLightning", "attach/default/glow/Lightning", true, BrightBolt, 2.4f, 0.62f) { AlongBody = true }, new Fx("StaffLightning", "attach/Loaded/Clouds", false, StormPuff) },
            ["elder_bass"] = new[] { new Fx("SwordNiedhoggNature", "attach/default/glow/Spores", true, null, 1.6f, 1.8f), new Fx("SwordNiedhoggNature", "attach/default/glow/Spores_World", false, null, 1.6f, 1.8f) },
            ["bonemass_catfish"] = new[] { new Fx("BowDraugrFang", "attach/DraugrFangBow/Particle System", false, null, 1.1f, 0.9f), new Fx("BowDraugrFang", "attach/Point light", true) },
            ["moder_scale"] = new[] { new Fx("MaceSilver", "attach/effects/soft cloud", false, FrostCloud, 0.5f, 0.7f), new Fx("MaceSilver", "attach/effects/vfx_BloodHit 1") },
            ["yagluthgill"] = new[] { new Fx("SwordDyrnwyn", "attach/Burny vfx"), new Fx("SwordDyrnwyn", "attach/Point Light", true) },
            ["queen_eel"] = new[] { new Fx("StaffSkeleton", "attach/fi_vil_combs_props_bone_skull/equiped/flames", true, null, 1.5f, 0.6f), new Fx("StaffSkeleton", "attach/fi_vil_combs_props_bone_skull/equiped/embers") },
            ["fimbul_salmon"] = new[] { new Fx("StaffIceShards", "attach/default (1)/effects/embers (1)", true, Frost, 2f), new Fx("MaceSilver", "attach/effects/soft cloud", false, FrostCloud, 0.5f, 0.7f) },
            ["odinfin"] = new[] { new Fx("SwordMistwalker", "attach/Mistwalker/Particle System", false, null, 2f), new Fx("SwordMistwalker", "attach/Mistwalker/Point light", true) },
            ["thorhammerhead"] = new[] { new Fx("SwordNiedhoggLightning", "attach/default/glow/Lightning", true, null, 0.6f, 0.7f), new Fx("SwordNiedhoggLightning", "attach/default/glow/Clouds") },
            ["fenringfin"] = new[] { new Fx("SwordNiedhoggBlood", "attach/default/glow/Swirls", false, null, 1.5f, 0.5f) { Orbit = 2.5f }, new Fx("SwordNiedhoggBlood", "attach/default/glow/blood drip") },
        };

        /// <summary>By rod id: the Mistlands-and-later rods.</summary>
        private static readonly Dictionary<string, Fx[]> RodFx = new()
        {
            ["yggdrasil"] = new[] { new Fx("SwordNiedhoggNature", "attach/default/glow/Spores") },
            ["ashwood"] = new[] { new Fx("SwordDyrnwyn", "attach/Burny vfx", false, null, 0.18f, 0.36f) { Life = 0.42f, Skip = new[] { "flare" }, Vary = true }, new Fx("SwordDyrnwyn", "attach/Point Light", true) },
            ["frostwood"] = new[] { new Fx("MaceSilver", "attach/effects/vfx_BloodHit 1", false, null, 0.5f, 0.6f), new Fx("MaceSilver", "attach/effects/soft cloud", false, FrostCloud, 0.35f, 0.15f) { Life = 0.5f } },   // the Allfather's snowfall (a little more) in Frostner's frost cloud
            ["leviathan"] = new[] { new Fx("SwordMistwalker", "attach/Mistwalker/Particle System") },
            // Mistwalker's mist, Frostner's snowflakes and the gem sword's ribbon lightning (bolts joined point to point), one light
            ["allfather"] = new[] { new Fx("SwordMistwalker", "attach/Mistwalker/Particle System", false, null, 0.5f, 0.55f), new Fx("MaceSilver", "attach/effects/vfx_BloodHit 1", false, null, 0.4f, 0.6f),
                                    new Fx("SwordNiedhoggLightning", "attach/default/glow/Lightning", false, null, 0.55f, 0.65f) { Ribbon = true }, new Fx("SwordMistwalker", "attach/Mistwalker/Point light", true, SkyBolt) },
        };

        private static readonly HashSet<string> Warned = new();

        public static bool HasFish(string fishId) => FishFx.ContainsKey(fishId);

        /// <summary>The fish's effects on a fish object (item prefab or the hooked visual), emitting from its model.</summary>
        public static void AttachToFish(GameObject root, string fishId)
        {
            if (!FishFx.TryGetValue(fishId, out var list) || root.transform.Find("vdw_fx") != null) return;
            Attach(root.transform, list, Emitter(root.transform), "fish_" + fishId);
        }

        /// <summary>The rod's effects on its item prefab, under "attach" so the rod in hand shows them.</summary>
        public static void AttachToRod(GameObject itemPrefab, string rodId)
        {
            if (!RodFx.TryGetValue(rodId, out var list)) return;
            var attach = itemPrefab.transform.Find("attach") ?? itemPrefab.transform;
            if (attach.Find("vdw_fx") != null) return;
            if (!AttachAlongBones(attach, list, "rod_" + rodId)) Attach(attach, list, Emitter(attach), "rod_" + rodId);
        }

        /// <summary>
        /// A rigged rod's effects follow it as it bends: each blank bone (Rod.1, Rod.2, ...) carries its own copy, emitting
        /// from a thin box along its segment and simulating in that bone's space, so the sparks ride the curve instead of
        /// the straight rod at rest (or streaking off behind in the world). Ribbon lightning then joins points within each
        /// segment: a chain of bolts up the rod. The one light sits on the middle bone. False if the rod has no such bones.
        /// </summary>
        private const float BoneRate = 0.5f;   // eight copies up a rod added up to too much: every copy at half rate
        private static readonly float[] VaryPattern = { 0.55f, 1.15f, 0.8f, 1.35f, 0.65f, 1.0f, 0.5f, 1.25f };

        private static bool AttachAlongBones(Transform attach, Fx[] list, string what)
        {
            var bones = new List<Transform>();
            for (int i = 1; ; i++)
            {
                var b = attach.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Rod." + i);
                if (b == null) break;
                bones.Add(b);
            }
            var tip = attach.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Rod.Tip");
            if (bones.Count < 2) return false;
            var holder = new GameObject("vdw_fx"); holder.transform.SetParent(attach, false);
            int made = 0;
            foreach (var fx in list)
            {
                var src = Source(fx);
                if (src == null) continue;
                for (int i = 0; i < bones.Count; i++)
                {
                    var bone = bones[i];
                    var next = i + 1 < bones.Count ? bones[i + 1] : tip;
                    if (next == null) continue;
                    bool lightHere = i == bones.Count / 2;
                    float vary = fx.Vary ? VaryPattern[i % VaryPattern.Length] : 1f;
                    if (fx.Light && !lightHere && src.GetComponentsInChildren<ParticleSystem>(true).Length == 0) continue;   // a light-only effect: one copy
                    var go = UnityEngine.Object.Instantiate(src.gameObject, bone, false);
                    go.name = "vdw_fx_" + src.name;
                    go.SetActive(true);
                    go.transform.localPosition = Vector3.zero; go.transform.localRotation = Quaternion.identity; go.transform.localScale = Vector3.one;
                    foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                        if (r is MeshRenderer || r is SkinnedMeshRenderer) r.enabled = false;
                    foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);
                    foreach (var t in go.GetComponentsInChildren<Transform>(true).Where(t => fx.Skip.Contains(t.name)).ToArray())
                        if (t != null && t != go.transform) UnityEngine.Object.DestroyImmediate(t.gameObject);
                    // the segment in the bone's own space: from the bone to the next one
                    Vector3 seg = bone.InverseTransformPoint(next.position);
                    float segLen = seg.magnitude * bone.lossyScale.x;                   // metres
                    foreach (var ps in go.GetComponentsInChildren<ParticleSystem>(true))
                    {
                        var main = ps.main;
                        main.simulationSpace = ParticleSystemSimulationSpace.Local;      // ride the bone
                        main.scalingMode = ParticleSystemScalingMode.Shape;
                        if (fx.Tint is Color tint) main.startColor = tint;
                        main.startSizeMultiplier *= fx.Size * vary;
                        main.startSpeedMultiplier *= 0.15f;
                        main.startLifetimeMultiplier *= fx.Life * vary;
                        var noise = ps.noise; if (noise.enabled) noise.strengthMultiplier *= fx.Size;
                        var trails = ps.trails;
                        if (trails.enabled)
                        {
                            if (trails.mode == ParticleSystemTrailMode.Ribbon && !fx.Ribbon) { trails.mode = ParticleSystemTrailMode.PerParticle; trails.lifetimeMultiplier = 0.35f; }
                            trails.widthOverTrailMultiplier *= Mathf.Max(fx.Size, 0.5f);
                        }
                        var vel = ps.velocityOverLifetime;
                        if (vel.enabled) { vel.orbitalXMultiplier = 0f; vel.orbitalYMultiplier = 0f; vel.orbitalZMultiplier = 0f; vel.radialMultiplier = 0f; }
                        var sh = ps.shape;
                        sh.enabled = true; sh.shapeType = ParticleSystemShapeType.Box; sh.boxThickness = Vector3.zero;
                        sh.position = seg * 0.5f;
                        sh.rotation = Quaternion.FromToRotation(Vector3.up, seg).eulerAngles;
                        float thick = 0.04f / Mathf.Max(bone.lossyScale.x, 1e-4f);
                        sh.scale = new Vector3(thick, seg.magnitude, thick);
                        var em = ps.emission;
                        float rateK = fx.Rate * Mathf.Clamp(segLen, 0.1f, 1f) * BoneRate * vary;
                        em.rateOverTimeMultiplier *= rateK;                                 // sized for a 1 m blade: a segment's share, thinned
                        em.rateOverDistanceMultiplier *= rateK;                             // Dyrnwyn's flames and the frost staff's flakes mostly come from moving
                        var bursts = new ParticleSystem.Burst[em.burstCount]; em.GetBursts(bursts);
                        for (int bi = 0; bi < bursts.Length; bi++) bursts[bi].count = new ParticleSystem.MinMaxCurve(Mathf.Max(1f, bursts[bi].count.constant * fx.Rate * BoneRate));
                        em.SetBursts(bursts);
                        ps.Play(true);
                    }
                    var lights = go.GetComponentsInChildren<Light>(true);
                    for (int l = 0; l < lights.Length; l++)
                    {
                        if (!fx.Light || !lightHere || l > 0) { UnityEngine.Object.DestroyImmediate(lights[l]); continue; }
                        lights[l].range = Mathf.Max(lights[l].range, 2f) * 1.5f;
                        lights[l].transform.localPosition = seg * 0.5f;
                        if (fx.Tint is Color c) lights[l].color = c;
                    }
                    made++;
                }
            }
            if (made > 0) Plugin.Log.LogDebug($"Effects: '{what}' carries {made} vanilla effect copies along its bones.");
            return made > 0;
        }

        /// <summary>The biggest visible model renderer under a transform (the rigged one first).</summary>
        private static Renderer? Emitter(Transform t)
        {
            var smr = t.GetComponentsInChildren<SkinnedMeshRenderer>(true).Where(r => r.sharedMesh != null && !r.name.StartsWith("vdw_"))
                .OrderByDescending(r => r.sharedMesh.bounds.size.sqrMagnitude).FirstOrDefault();
            if (smr != null) return smr;
            return t.GetComponentsInChildren<MeshRenderer>(true).Where(r => r.enabled && r.GetComponent<MeshFilter>()?.sharedMesh != null)
                .OrderByDescending(r => r.GetComponent<MeshFilter>().sharedMesh.bounds.size.sqrMagnitude).FirstOrDefault();
        }

        private static Transform? Source(Fx fx)
        {
            var prefab = PrefabManager.Instance.GetPrefab(fx.Prefab) ?? ObjectDB.instance?.GetItemPrefab(fx.Prefab);
            var t = prefab != null ? prefab.transform.Find(fx.Path) : null;
            if (t == null && Warned.Add(fx.Prefab + "/" + fx.Path))
                Plugin.Log.LogWarning($"Effects: '{fx.Path}' not found on vanilla '{fx.Prefab}'; that effect is left out.");
            return t;
        }

        private static void Attach(Transform parent, Fx[] list, Renderer? emitter, string what)
        {
            if (emitter == null) { Plugin.Log.LogWarning($"Effects: '{what}' has no model to emit from."); return; }
            var mesh = emitter is SkinnedMeshRenderer s ? s.sharedMesh : emitter.GetComponent<MeshFilter>()?.sharedMesh;
            if (mesh == null) return;
            // how big the model is, as worn/held (the emitter's own scale included): sets emission and light range
            float length = Vector3.Scale(mesh.bounds.size, emitter.transform.lossyScale).magnitude /
                           Mathf.Max(parent.lossyScale.x, 1e-4f);
            float sizeK = Mathf.Clamp(length, 0.4f, 8f);
            // particles are sized for a ~1 m blade: smaller on a small fish (never bigger on a big one - more of them instead)
            float partK = Mathf.Clamp(length / 1.2f, 0.3f, 1f);

            var holder = new GameObject("vdw_fx");
            holder.transform.SetParent(parent, false);
            int made = 0;
            foreach (var fx in list)
            {
                var src = Source(fx);
                if (src == null) continue;
                var go = UnityEngine.Object.Instantiate(src.gameObject, holder.transform, false);
                go.name = "vdw_fx_" + src.name;
                go.SetActive(true);
                // ride the model: placed at the emitter, emitting from its surface
                go.transform.SetParent(emitter.transform, false);
                go.transform.localPosition = Vector3.zero; go.transform.localRotation = Quaternion.identity; go.transform.localScale = Vector3.one;
                foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                    if (r is MeshRenderer || r is SkinnedMeshRenderer) r.enabled = false;     // particles and lights only
                foreach (var c in go.GetComponentsInChildren<Collider>(true)) UnityEngine.Object.DestroyImmediate(c);

                foreach (var ps in go.GetComponentsInChildren<ParticleSystem>(true))
                {
                    var main = ps.main;
                    main.scalingMode = ParticleSystemScalingMode.Shape;   // the shape follows the model, particle size stays
                    if (fx.Tint is Color tint) main.startColor = tint;
                    main.startSizeMultiplier *= partK * fx.Size;
                    main.startSpeedMultiplier *= 0.4f;                     // hug the body instead of flying off it
                    // a blade's orbit (the blood swirls) becomes metre-wide rings round a fish: drift instead
                    // lightning arcs: their length is the trail and the jitter (noise), not the particle size - both
                    // are in world units for a 1 m blade, so on a small fish they drew a metre-wide cage of lines
                    float k = partK * fx.Size;
                    var noise = ps.noise;
                    if (noise.enabled) noise.strengthMultiplier *= k;
                    var trails = ps.trails;
                    if (trails.enabled)
                    {
                        // a ribbon joins each particle to the next: on a blade they're born in a row (a jagged bolt), on
                        // our mesh at random spots, so the ribbon drew straight lines across the fish (a cage). Each
                        // particle trails on its own instead: short crackling sparks over the body.
                        if (trails.mode == ParticleSystemTrailMode.Ribbon) { trails.mode = ParticleSystemTrailMode.PerParticle; trails.lifetimeMultiplier = 0.35f; }
                        trails.lifetimeMultiplier *= k; trails.widthOverTrailMultiplier *= Mathf.Max(k, 0.5f);
                    }
                    var pr = ps.GetComponent<ParticleSystemRenderer>();
                    if (pr != null && pr.renderMode == ParticleSystemRenderMode.Stretch) { pr.lengthScale *= k; pr.velocityScale *= k; }
                    var vel = ps.velocityOverLifetime;
                    if (vel.enabled) { vel.orbitalXMultiplier = 0f; vel.orbitalYMultiplier = 0f; vel.orbitalZMultiplier = 0f; vel.radialMultiplier = 0f; }
                    if (fx.Orbit > 0f)
                    {
                        // circle the body: orbit about the model's long axis, centred on the model, kept in the fish's
                        // own space so the swirls ride along with it
                        var b = mesh.bounds; var e = b.extents;
                        int ax = e.x >= e.y && e.x >= e.z ? 0 : e.y >= e.z ? 1 : 2;
                        main.simulationSpace = ParticleSystemSimulationSpace.Local;
                        vel.enabled = true; vel.space = ParticleSystemSimulationSpace.Local;
                        vel.x = vel.y = vel.z = new ParticleSystem.MinMaxCurve(0f);
                        vel.orbitalX = new ParticleSystem.MinMaxCurve(ax == 0 ? fx.Orbit : 0f);
                        vel.orbitalY = new ParticleSystem.MinMaxCurve(ax == 1 ? fx.Orbit : 0f);
                        vel.orbitalZ = new ParticleSystem.MinMaxCurve(ax == 2 ? fx.Orbit : 0f);
                        vel.orbitalOffsetX = new ParticleSystem.MinMaxCurve(b.center.x);
                        vel.orbitalOffsetY = new ParticleSystem.MinMaxCurve(b.center.y);
                        vel.orbitalOffsetZ = new ParticleSystem.MinMaxCurve(b.center.z);
                        vel.radial = new ParticleSystem.MinMaxCurve(0f);
                        main.startSpeedMultiplier = 0f;
                        main.startLifetimeMultiplier *= 1.5f;           // long enough to wrap round the body
                    }
                    var sh = ps.shape;
                    sh.enabled = true;
                    if (emitter is SkinnedMeshRenderer smr) { sh.shapeType = ParticleSystemShapeType.SkinnedMeshRenderer; sh.skinnedMeshRenderer = smr; }
                    else { sh.shapeType = ParticleSystemShapeType.MeshRenderer; sh.meshRenderer = (MeshRenderer)emitter; }
                    sh.position = Vector3.zero; sh.rotation = Vector3.zero; sh.scale = Vector3.one;
                    if (fx.AlongBody)
                    {
                        // a line of crackles down the body: a box as long as the model and a fraction as thick, centred
                        // on it, in the fish's own space; nothing thrown outward and the jitter kept small, so the bolts
                        // hug the body instead of bunching into a ball round its middle
                        var bb = mesh.bounds; var ex = bb.extents;
                        int la = ex.x >= ex.y && ex.x >= ex.z ? 0 : ex.y >= ex.z ? 1 : 2;
                        var size = bb.size * 0.35f; size[la] = bb.size[la] * 0.9f;
                        sh.shapeType = ParticleSystemShapeType.Box; sh.boxThickness = Vector3.zero;
                        sh.position = bb.center; sh.scale = size;
                        main.simulationSpace = ParticleSystemSimulationSpace.Local;
                        main.startSpeedMultiplier = 0f;
                        if (noise.enabled) noise.strengthMultiplier *= 0.3f;
                        if (vel.enabled) { vel.x = vel.y = vel.z = new ParticleSystem.MinMaxCurve(0f); }
                    }
                    var em = ps.emission;
                    em.rateOverTimeMultiplier *= fx.Rate * Mathf.Sqrt(sizeK);
                    ps.Play(true);
                }
                var lights = go.GetComponentsInChildren<Light>(true);
                for (int i = 0; i < lights.Length; i++)
                {
                    if (!fx.Light || i > 0) { UnityEngine.Object.DestroyImmediate(lights[i]); continue; }
                    lights[i].range = Mathf.Max(lights[i].range, 2f) * Mathf.Clamp(sizeK, 0.6f, 3f);
                    lights[i].transform.localPosition = mesh.bounds.center;
                    if (fx.Tint is Color c) lights[i].color = c;
                }
                made++;
            }
            if (made > 0) Plugin.Log.LogDebug($"Effects: '{what}' carries {made} vanilla effect(s).");
        }
    }
}
