# Art sources

Where textures and reference assets come from (Blender 5.3). Pick the best match for each part across all of these,
and vary the wear/grunge source too: some library materials carry their own.

## Materials

| Source | What | How the tools use it |
|---|---|---|
| Sanctus library (add-on) | procedural materials | `bake_*.py` append them from `%APPDATA%\Blender Foundation\Blender\<version>\extensions\user_default\sanctus_library_starter` |
| Grungit (add-on) | wear, dirt, edge masks | `bake_*.py` append its node groups |
| ambientCG Lite (5.3 online library, CC0) | ~4,900 assets: leather, bark, wood, planks, fabric, rope, metal, rust, snow, ice... | `bake_wood_cooler.py` `ACG` entries: fetched once from the library's CDN, cached in `Desktop\Valheim_DeepWaters\Mesh\_library_cache\ambientcg` |
| Poly Haven Lite (5.3 online library, CC0) | materials, HDRIs, models | Blender's Asset Browser |
| Charge Open Movie Library, Cartesian Caramel's Everyday Nodes (5.3 online libraries) | production assets, node groups | Blender's Asset Browser |
| [rileyb3d.com](https://rileyb3d.com/library?type=texture) (CC0) | 210 PBR textures up to 4K (PNG, OpenGL normals), incl. winter/snow/ice, wood, leather, grunge | downloaded at 1K (signed in) into `Mesh\_library_cache\rileyb3d\<Name>\`; `bake_wood_cooler.py` `RILEY` entries use them. Have: Western Distressed Leather (lavvu hide), Raw Hewn Wood (lavvu poles), Hand-Hewn Timber (ship-tent boards), Compacted Uneven Snow 01/02 (snow banks). Its "rileyb3d Models" online library has models only. |

## Local asset bundles (User Library: `OneDrive\Documents\Blender\Assets`)

- Human Base Meshes v1.4.1 (Blender Studio)
- Ellie Pose Library v2.0.0 (Blender Studio)
- Animal Fur examples (hair nodes: zebra, sheep, highland cattle, beaver)

## Reference files (not assets, open them directly)

- `Desktop\hair_nodes-female_hair_styles.blend`: hair-node grooming examples
- `Desktop\basic_particle_simulation.blend`: a simulation-nodes particle setup
