# UNSUPERVISED SMP — server setup

**Theme:** An exploration-first survival world for the Unsupervised Adults crew: *questionable decisions, beautiful wilderness, improbable pets, and dangerous group expeditions*. Minecraft **Java 1.21.1 + Fabric**. This guide is for the **server owner only**. Friends need only `UnsupervisedAdultsMC.exe`; they never need Crafty.

## What is in this folder?

```text
Server Setup/
  build_server.cmd              <-- Run on your Windows owner PC
  mods/                         <-- Actual server .jar files appear here after running
  installed-mods.md             <-- Generated exact names and versions
  unavailable-mods.txt          <-- Generated report of manual/failed mods
  fabric-server-launch.jar       <-- Downloaded official Fabric server executable
  UnsupervisedSMP-Crafty-*.zip    <-- Full NEW-SERVER ZIP for Crafty Import
  UnsupervisedSMP-ServerMods-*.zip  <-- Older mods-only update ZIP (optional)
  server.properties.example     <-- Whitelist / server resource-pack examples
  merge_resourcepacks.cmd       <-- Optional: merge permitted resource packs
  resourcepacks/
    input/                      <-- Put resource pack ZIPs here
    output/                     <-- Merged ZIP, checksum, collision report
```

The repository does **not** contain downloaded third-party JAR binaries. The generator downloads the correct files directly from their original Modrinth/GitHub release sources with checksums, and writes them into `mods/`. A separate HTTPS download from Fabric provides the executable server launcher. This avoids shipping outdated binaries and respects authors' distribution requirements.

## One-click Crafty import from our launcher (recommended)

1. Build the latest `UnsupervisedAdultsMC.exe` locally using the repo `build.cmd`. The **CREATE SERVER ZIP** button is for the server owner; your friends just use **PLAY SMP**.
2. Open the EXE and click **CREATE SERVER ZIP**. It downloads the official **Fabric 1.21.1 server launcher** from Fabric's versioned endpoint and SHA-verified compatible server/shared mods. Output: `UnsupervisedAdultsMC_Data/Server Setup/UnsupervisedSMP-Crafty-<pack version>.zip` **beside your EXE**. You do **not** need Crafty API access or to install the server on your Windows PC.
3. On Crafty's **Create New Server** page, use the **Upload Zip Archive** section at the right (not the normal Build Server button). Enter the name **UnsupervisedSMP**, browse for the generated ZIP, click **Upload**, then **Import Server**. In the import wizard select the archive's **root directory**, where `fabric-server-launch.jar` and `server.properties` are together.
4. Select executable **`fabric-server-launch.jar`**, **Java 21**, port **25565** (or your chosen forwarded port), minimum RAM **2 GB** and maximum **6 GB** as an initial test. If Crafty does not create the command correctly, set **`java -Xms2G -Xmx6G -jar fabric-server-launch.jar nogui`** in the server configuration. Fabric's official launcher fetches remaining Minecraft/Fabric files during first start. This ZIP contains no world or automatically accepted EULA; confirm Minecraft's EULA only when Crafty asks you.
5. **First start, confirm whitelist settings** from `server.properties`, read the Fabric logs for missing dependencies, and add friends with `whitelist add PlayerName`. Back up before making changes. Start a **fresh world** because of biomes, structures and ores.
6. Keep the client and Crafty mod sets tied to the same published `pack/pack-lock.json`. Until you commit the lock to the public GitHub repository, the launcher's resolver may pick different versions at different times.

**EggMorph:** the current URL points to your *private* EggMorph GitHub release; anonymous requests fail. The built ZIP will report it as optional/missing. As the repo owner, you can download `eggmorph-0.2.0-alpha.jar` while signed in and put it in the generated `Server Setup/mods/` folder before clicking the button again; if the binary SHA-256 matches the catalog, the ZIP builder will include it **without attempting the private download**. Players still need the JAR: for automatic updates you'll need a **publicly accessible compiled JAR** and a new catalog URL + lock. Do not give friends a GitHub access token. EggMorph remains an untested alpha; leave it off the public SMP until verified.

**Server resource packs:** the server supports one `resource-pack=` URL, but client-side packs can be layered and do not need to be merged. The optional resource-pack merge tool is separate and only for assets you have permission to redistribute.

## Alternative: updating a Fabric server that already exists in Crafty

1. **Make a backup** of any existing world and server files. Ideally start a **brand-new world** for the new biomes, ores, and structures. Existing chunks do not regenerate simply because you installed mods.
2. In Crafty, create/select a **Fabric 1.21.1 dedicated server** running **Java 21**. Do not choose Paper, Spigot, Forge or NeoForge. Start it once, then stop it so the standard folders are created. Ensure your Fabric Loader version matches `pack/catalog.json`.
3. On your **Windows PC**, download this GitHub repo, run **`update_pack.cmd`** to pin the 1.21.1 Fabric mods, and run **`export_server_pack.cmd`** to produce the older **mods-only** ZIP plus verified server/shared JARs in `Server Setup/mods/`. For a whole **new** Crafty instance, use the launcher **CREATE SERVER ZIP** button or `Server Setup/build_server.cmd` instead. Python 3.11+ is needed **only on this owner PC**, not for your friends or the Debian server.
4. Open `Server Setup/installed-mods.md` and `unavailable-mods.txt`. **Do not start the real SMP if required mods failed**. If the optional EggMorph JAR is unavailable, remember its repo is private and the current build is experimental.
5. **Stop Crafty server**, back it up again, then upload the contents of `Server Setup/mods/` into the **server's own** `mods/` folder via Crafty. Replace older versions; do not leave duplicate versions of the same mod. *Do not* upload Sodium, Iris, shaders, or client-only effects.
6. In Crafty's `server.properties`, set these values:

   ```properties
   level-name=UnsupervisedSMP
   motd=Unsupervised SMP | Exploration, Chaos, Questionable Decisions
   online-mode=true
   white-list=true
   enforce-whitelist=true
   ```

7. Start the server and read the logs. Fabric will tell you if any dependency is missing. Fix that **before** letting friends join. Add each friend by their exact Minecraft account name with `whitelist add PlayerName` in the Crafty console. Keep Crafty private; only give friends our launcher.
8. **Commit `pack/catalog.json` and the generated `pack/pack-lock.json` to GitHub `main`.** Client launchers use that same lock on their next **Play** click. Don't send friends onto the modded world until both sides are on the same pack.

### Updating later

Back up your world, stop the server, re-run `update_pack.cmd` followed by `export_server_pack.cmd` for an existing server (or **CREATE SERVER ZIP** for a brand-new instance), review reports, upload new/replacement JARs, restart, then publish the updated lock. The script manages only its own previously downloaded JARs in the **local generated** `mods/` folder. It does not directly access or delete your Crafty server files.

**Changing biome generators or ore generation mid-world is especially risky.** New content appears only in new chunks and may create hard biome seams; removing a worldgen mod can break existing save data. World generation mods are best finalized before launching the public SMP.

## Chosen adventure mods

The current `pack/catalog.json` contains the following verified **1.21.1 Fabric candidates**. A compatible published version exists, but the full mod combination still requires an actual multiplayer smoke test. The generator checks every chosen release and its dependencies when you run it.

| Purpose | Mod | Installed on | Why it fits |
|---|---|---|---|
| Wild worlds | [Biomes O' Plenty](https://modrinth.com/mod/biomes-o-plenty) | Both | Unusual exploration terrain, plants and building blocks. Requires **TerraBlender**, **GlitchCore**, Fabric API |
| Wildlife | [Naturalist](https://modrinth.com/mod/naturalist) | Both | More ambient and interactive animals |
| Pets | [Critters and Companions](https://modrinth.com/mod/critters-and-companions) | Both | Otters, ferrets and other little companions |
| Mobs | [Friends & Foes](https://modrinth.com/mod/friends-and-foes) | Both | Vanilla-style creatures and challenges |
| Ores & tools | [Mythic Metals](https://modrinth.com/mod/mythicmetals) | Both | New ore types, tools and armor |
| Weapons | [Simply Swords](https://modrinth.com/mod/simply-swords) | Both | Fun loot and weapons for dungeon raids |
| Combat | [Better Combat](https://modrinth.com/mod/better-combat) | Both | Animations and usable sword styles; test with existing visual mods |
| Loot | [Artifacts](https://modrinth.com/mod/artifacts) | Both | Rare, weird exploration rewards |
| Group travel | [Waystones](https://modrinth.com/mod/waystones) | Both | Find and travel between distant builds |
| Expeditions | [Comforts](https://modrinth.com/mod/comforts) | Both | Sleeping bags that don't reset home spawn |
| Dungeons | [YUNG's Better Dungeons](https://modrinth.com/mod/yungs-better-dungeons) | Server | Redesigned and expanded dungeons |
| Underground | [YUNG's Better Mineshafts](https://modrinth.com/mod/yungs-better-mineshafts) | Server | Better mines and underground exploration |
| Villages | [Towns and Towers](https://modrinth.com/mod/towns-and-towers) | Server | Varied villages and pillager outposts |
| Huge landmarks | [When Dungeons Arise](https://modrinth.com/mod/when-dungeons-arise) | Server | Big adventures and some dangerous raids |

Other core shared/server mods from the original SMP pack remain, including Fabric API, Lithium, FerriteCore, Easy Magic, Easy Anvils, and required libraries. The generator includes the exact **server-only + both** list (not client-only graphics). Actual dependencies may include **YUNG's API, Cloth Config, Architectury, Player Animator**, and others: trust the generated lock and Fabric logs instead of manually guessing versions.

### Later / optional chaos

- [Bosses of Mass Destruction](https://modrinth.com/mod/bosses-of-mass-destruction): boss raids for endgame expeditions. **Disabled initially** to let us test difficulty and EggMorph interactions first.
- [Simple Voice Chat](https://modrinth.com/mod/simple-voice-chat): optional proximity voice for recording. **Disabled initially**. Requires the voice UDP port (typically 24454) forwarded/configured in addition to the Minecraft TCP port.
- [Petting - Tame Any Mob](https://modrinth.com/mod/petting): optional pet shenanigans, **disabled** until mob AI and EggMorph compatibility are checked.
- [Terralith](https://modrinth.com/mod/terralith): optional *alternative* major terrain generator, **disabled** to avoid combining competing terrain systems without tests.
- **Inventory Pets / Cloud Pet**: the original mod has a current **NeoForge/Forge 1.21.1** build, **not a suitable Fabric 1.21.1 build**. It is intentionally not installed. Critters and Companions fills the pet niche for now.

## About resource packs

A vanilla dedicated server's `resource-pack=` field takes one download URL, but **clients can stack multiple local resource packs**. Our launcher already downloads separate client packs like Fresh Animations and Better Crops; no server-side merge is needed for those, and shaders are never server resource packs.

If you want a *single server-pushed ZIP*, read [`resourcepacks/README.md`](resourcepacks/README.md) and run `merge_resourcepacks.cmd`. It builds `resourcepacks/output/UnsupervisedSMP-ServerResourcePack.zip`, gives you the SHA-1 for Crafty, and reports file conflicts. **You must host it yourself on an HTTPS URL** and only merge assets you are permitted to redistribute. The server cannot automatically send arbitrary locally installed ZIP files without a public URL or supporting mod.

## Server safety

- **Keep** `online-mode=true`, `white-list=true`, `enforce-whitelist=true`. A whitelist is not secure if online authentication is disabled.
- Keep Crafty credentials, server backups and admin commands private. Port-forward only what is necessary.
- **New mod list = fresh test world first.** Launch once, explore, generate new chunks, test multiple player logins, animal animations, dungeon loot, and check log for Fabric mixin errors before migrating a real save.
- The experimental EggMorph alpha may mishandle modded entities; don't use its current build on your production world until that is tested separately.
