# art-tools

The Blender (and a few PowerShell) tools that build every model, rig, texture and icon in the mod. They run against the
art in `Desktop\Valheim_DeepWaters` (not in this repo): `blender --factory-startup -b <file> --python art-tools\<tool>.py`
with settings passed as `VDW_*` environment variables (each tool's header says which).

This folder is the real copy; `Desktop\Valheim_DeepWaters\Mesh\tools` is a junction pointing here, so old paths still work.
`unity-editor\` is the same for the Unity project's `Assets\DeepWaters\Editor` (the model importer and bundle builder).
