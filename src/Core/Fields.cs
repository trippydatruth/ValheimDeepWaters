using HarmonyLib;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Fast access to Valheim's private fields for code that runs every frame (no reflection or boxing per read).
    /// A field a game update renamed gives null and one warning, instead of breaking the class that asked for it.
    /// </summary>
    internal static class Fields
    {
        public static AccessTools.FieldRef<T, F>? Ref<T, F>(string name) where T : class
        {
            try { return AccessTools.FieldRefAccess<T, F>(name); }
            catch (System.Exception ex)
            {
                Plugin.Log.LogWarning($"{typeof(T).Name}.{name} wasn't found ({ex.GetType().Name}); what uses it is skipped.");
                return null;
            }
        }
    }
}
