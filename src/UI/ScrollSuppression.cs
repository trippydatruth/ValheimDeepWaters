using HarmonyLib;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Stops the mouse wheel zooming the camera while the rod is out, since the wheel sets drag. The camera reads
    /// the wheel through ZInput, so that's what's zeroed. Drag itself reads the wheel from IMGUI events
    /// (FishingController.ProcessScrollEvent), which these patches don't touch.
    /// </summary>
    [HarmonyPatch]
    internal static class ScrollSuppression
    {
        [HarmonyPatch(typeof(ZInput), "GetMouseScrollWheel")]
        [HarmonyPostfix]
        private static void ZInputScrollPostfix(ref float __result)
        {
            if (FishingController.RodEquippedNow) __result = 0f;
        }

        [HarmonyPatch(typeof(ZInput), "Internal_GetMouseScrollWheel")]
        [HarmonyPostfix]
        private static void ZInputInternalScrollPostfix(ref float __result)
        {
            if (FishingController.RodEquippedNow) __result = 0f;
        }
    }
}
