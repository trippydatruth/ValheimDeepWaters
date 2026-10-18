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
            public bool NoTrails;           // drop the trails
            public float TrailLife;         // >0: per-particle trails this short (seconds share) - quick crackles that stay on a small fish
            public float Orbit;             // >0: particles circle the body along its length at this speed
            public bool AlongBody;          // emit from a thin box down the body's length (not the mesh surface), no throw, little jitter
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
            ["ashwood"] = new[] { new Fx("StaffFireball", "attach/equiped/embers") },
            ["frostwood"] = new[] { new Fx("MaceSilver", "attach/effects/vfx_BloodHit 1") },
            ["leviathan"] = new[] { new Fx("SwordMistwalker", "attach/Mistwalker/Particle System") },
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
            Attach(attach, list, Emitter(attach), "rod_" + rodId);
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
                    if (fx.NoTrails) trails.enabled = false;
                    if (trails.enabled)
                    {
                        // a ribbon joins each particle to the next: on a blade they're born in a row (a jagged bolt), on
                        // our mesh at random spots, so the ribbon drew straight lines across the fish (a cage). Each
                        // particle trails on its own instead: short crackling sparks over the body.
                        if (trails.mode == ParticleSystemTrailMode.Ribbon) { trails.mode = ParticleSystemTrailMode.PerParticle; trails.lifetimeMultiplier = 0.35f; }
                        if (fx.TrailLife > 0f) { trails.mode = ParticleSystemTrailMode.PerParticle; trails.lifetimeMultiplier = fx.TrailLife; }
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
            if (made > 0) Plugin.Log.LogInfo($"Effects: '{what}' carries {made} vanilla effect(s).");
        }
    }
}
