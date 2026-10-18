using HarmonyLib;
using System.Linq;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// A boss fish brings the weather of the boss it's named after, from its omen to the end of the fight, for everyone
    /// near it: the angler shares which boss they're facing on their own player (synced like the rest of the player),
    /// and every client puts the nearest such encounter's weather in place through the same environment override
    /// Valheim's raids use, so it rolls in and clears with the usual fade. Players who arrive mid-fight get it too, and
    /// it ends when the fight does (landed, lost or the angler gone). Its music is shared the same way.
    /// </summary>
    internal static class BossWeather
    {
        private const float Radius = 150f;                 // how near a boss encounter you have to be to be in its weather
        private static readonly int Key = "vdw_boss".GetStableHashCode();

        private static string _sent = "";
        private static float _nextScan;
        private static BossInfo? _near;

        private static ZDO? Zdo(Player p)
        {
            var nview = p.GetComponent<ZNetView>();
            return nview != null && nview.IsValid() ? nview.GetZDO() : null;
        }

        /// <summary>The boss the local angler is facing (omen or fight), shared on their player. Called every frame.</summary>
        public static void Share(Player local)
        {
            var s = FishingController.Session;
            string id = s?.Boss != null && (s.Phase != FishingPhase.Waiting || s.OmenStep >= 1) && !local.IsDead() ? s.Boss.FishId : "";
            if (id == _sent) return;
            var zdo = Zdo(local);
            if (zdo == null || !zdo.IsOwner()) return;
            zdo.Set(Key, id);
            _sent = id;
            _nextScan = 0f;
        }

        /// <summary>The nearest boss encounter (anyone's, the local player's too) within reach, looked for twice a second.</summary>
        public static BossInfo? Near()
        {
            if (Time.time < _nextScan) return _near;
            _nextScan = Time.time + 0.5f;
            var me = Player.m_localPlayer;
            BossInfo? found = null;
            if (me != null && VdwConfig.Enabled.Value)
            {
                float best = Radius * Radius;
                foreach (var p in Player.GetAllPlayers())
                {
                    if (p == null) continue;
                    string id = Zdo(p)?.GetString(Key, "") ?? "";
                    if (id.Length == 0) continue;
                    float d = (p.transform.position - me.transform.position).sqrMagnitude;
                    if (d > best) continue;
                    var boss = BossFish.ForFish(id);
                    if (boss == null) continue;
                    best = d;
                    found = boss;
                }
            }
            if (found != _near)
                Plugin.Log.LogDebug(found != null
                    ? $"Boss weather: {found.FishId} near you - {EnvFor(found) ?? "no matching environment"}."
                    : "Boss weather: clearing.");
            _near = found;
            return _near;
        }

        /// <summary>The first of the boss's weathers this world has (Valheim's own boss weathers first, then storms).</summary>
        public static string? EnvFor(BossInfo boss)
        {
            if (boss.Environment != null) return boss.Environment.Length > 0 ? boss.Environment : null;
            var envs = EnvMan.instance?.m_environments;
            if (envs == null) return null;
            boss.Environment = boss.Weathers.FirstOrDefault(w => envs.Any(e => e != null && e.m_name == w)) ?? "";
            if (boss.Environment.Length == 0)
                Plugin.Log.LogWarning($"Boss weather: none of {string.Join(", ", boss.Weathers)} exist for {boss.FishId}; the environments are: " +
                                      string.Join(", ", envs.Where(e => e != null).Select(e => e.m_name)));
            return boss.Environment.Length > 0 ? boss.Environment : null;
        }

        [HarmonyPatch(typeof(EnvMan), "GetEnvironmentOverride")]
        private static class EnvironmentPatch
        {
            private static void Postfix(ref string __result)
            {
                if (Player.m_localPlayer != null && Player.m_localPlayer.InIntro()) return;
                var boss = Near();
                var env = boss != null ? EnvFor(boss) : null;
                if (env != null) __result = env;
            }
        }
    }
}
