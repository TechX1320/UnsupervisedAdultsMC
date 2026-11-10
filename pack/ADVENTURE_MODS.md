# Unsupervised SMP — Adventure pack 0.5.0-alpha

**Minecraft:** 1.21.1 Fabric (Loader 0.19.5+, Java 21)  
**Purpose:** cozy chaos, questionable group expeditions, impressive landmarks, loot, pets, and a place to build afterward.

All entries below have Modrinth project pages for 1.21.1/Fabric. The resolver still needs to download **exact versions**, and Minecraft/Prism/Crafty must be tested before considering this a stable modpack. **Do not put a Forge/NeoForge JAR in a Fabric mods folder.**

## Dungeon and structure exploration

* Dungeons and Taverns — forts, taverns, and smaller discoveries.
* Structory + Structory: Towers — themed ruins, settlements and exploration landmarks.
* Moog's Voyager, Nether and End Structures (+ Moog's Structure Lib) — vanilla-style landmarks and loot.
* Tidal Towns — floating ocean villages.
* YUNG's Better Strongholds, Desert Temples, Nether Fortresses, Ocean Monuments and Bridges — major landmark improvements.
* Already in pack: When Dungeons Arise, YUNG's Better Dungeons and Mineshafts, Towns and Towers.
* **Optional, off by default:** YUNG's Better Jungle Temples, Better Witch Huts, ChoiceTheorem's Overhauled Villages. Enable only after checking structure density and other village mods.

## World generation

* Biomes O' Plenty (+ TerraBlender/GlitchCore from the resolver): already present.
* Incendium: significant Nether overhaul.
* Nullscape: dramatic End terrain (End untouched until generation; safest in a fresh world).
* Lithostitched: worldgen compatibility library.
* Terralith is **already optional/disabled**. Avoid stacking it with BOP without a dedicated compatibility test and world backup.

## Mobs, combat, loot and travel

* Creeper Overhaul, Illager Invasion, Mutant Monsters, More Mobs, Breed More Mobs.
* Lootr — each player can loot a dungeon chest independently, reducing group loot arguments.
* Nature's Compass and Explorer's Compass — locate biomes and structures.
* Immersive Aircraft, Small Ships and Traveler's Backpack — expeditions and travel.
* Already present: Naturalist, Critters and Companions, Friends & Foes, Simply Swords, Mythic Metals, Better Combat and Artifacts.
* **Optional, off by default:** Deeper and Darker and AdventureZ (large extra dimension/boss features), YUNG's Better End Island (changes the dragon arena), Mob AI Tweaks.

## Home life between adventures

* Farmer's Delight Refabricated — cooking/farming.
* Supplementaries + Amendments + Moonlight Lib — functional decorative details.
* Another Furniture — vanilla-style furniture.
* **Optional, off by default:** Let's Do Furniture (additional models, extra dependencies).

## Performance and convenience

* ModernFix, Chunky (server pregeneration), Fast Leaf Decay, EMI (client recipes), Mouse Tweaks.
* **Optional, off by default:** Noisium until tested against the existing Fast Noise configuration.
* **Explicit hard dependencies:** Fabric Language Kotlin and Simply Tooltips, plus Moonlight and Moog's Structure Lib. These avoid the missing-dependency messages seen in the first server test.

## Publishing and testing

1. Use **`update_pack.cmd`** at the repo root. This resolves the exact Minecraft 1.21.1 Fabric versions and builds `pack/pack-lock.json`; review `pack/resolution-report.txt` for missing entries.
2. **Commit both `pack/catalog.json` and `pack/pack-lock.json` to `main`.** The client's Play button and the Crafty ZIP then use the same version-pinned mod list. Without a published lock, downloads can drift.
3. Run **`Create Server ZIP`** in our Windows launcher, import the new ZIP into Crafty, select `fabric-server-launch.jar`, and use Java 21. Confirm Fabric Loader **0.19.5** on server and client.
4. **Make a fresh test world**, with `online-mode=true`, `white-list=true`, `enforce-whitelist=true`. Worldgen changes do not retroactively populate old chunks. Never delete the live world without a backup.
5. Test first start, login, Nether, End, newly generated chunks, raid structures, dimension travel, and each player's client mod set. Check Fabric logs for missing dependencies and duplicate mods.
6. If too many structures overlap or spawn too frequently, tune structure spacing or disable one structure collection before committing to a permanent world.

**Compatibility reality:** A 1.21.1 Fabric release page isn't proof that 100 mods work together. This is an expanded **alpha selection**, not a tested server installation. The catalog permits optional mods to be skipped and documents why; missing **required** dependencies block the pack.

## EggMorph client startup hotfix

EggMorph v0.2.0-alpha.2 is pinned to its release SHA-256 in `pack/catalog.json`, but remains optional while the new Fabric client refmap fix is tested. For the automatic download to work, the owner must change the private EggMorph repository to **public** through GitHub settings. The first test should replace the old JAR on the Prism client; after confirming startup and multiplayer, replace the server JAR too, avoiding duplicate versions.

## EggMorph Alpha 3 edible-eggs test

EggMorph 0.2.0-alpha.3 is pinned in `pack/catalog.json` for both client and server. The prerelease now registers Morph Eggs as always-edible food (zero nutrition), waits until eating finishes to morph, and offers pre-imprinted Zombie, Cow, Bee eggs in Creative → Ingredients. A generic `/give @s eggmorph:morph_egg` has no Mob data and will not morph; for a specific mob use `/give @s eggmorph:morph_egg[minecraft:custom_data={Mob:"minecraft:zombie"}]`.

The GitHub EggMorph repository remains private. Change its visibility to public (Settings → General → Danger Zone) before sharing the launcher; do not embed access tokens. Back up the server, remove the old EggMorph JAR, and install alpha3 on both sides. Test in Prism before making it required. Update and publish the modpack lock after testing.
