# Unsupervised Adults MC

A **Windows launcher for the Unsupervised Adults Minecraft SMP**. Minecraft **1.21.1**, Fabric, and the agreed mod list. Built locally; **no GitHub Actions, Docker, hosting panel access, or Java programming required**.

**Status: early alpha / not yet tested on a real Windows machine.** The source and Python tests work, but the Prism download/bootstrap and actual Minecraft launch need a Windows playtest before distributing to friends.

## What friends do

1. Download **`UnsupervisedAdultsMC.exe`** from you (after you build it).
2. Launch it. The first time, click **MICROSOFT LOGIN** and sign into their *own purchased Minecraft Java Edition* account through official Prism Launcher.
3. Enter the SMP server address (once, if the pack owner has not configured it), then click **PLAY SMP**.
4. The launcher checks GitHub for the pinned modpack, downloads or repairs compatible mods, and launches the Fabric 1.21.1 instance. Later: **PLAY SMP** again for updates.

**No one needs Crafty access.** Authentication uses Prism/Microsoft (this program neither collects nor stores Microsoft passwords/tokens). The SMP should have `online-mode=true`, `white-list=true`, and `enforce-whitelist=true`.

## Building locally on Windows

1. Download/cl​one the repo, with GitHub Desktop or **Code → Download ZIP**, then extract it.
2. Install [Python 3.11+](https://www.python.org/downloads/windows/). Check **Add Python to PATH** during setup.
3. Double-click **`build.cmd`**. It creates `.venv`, installs PyInstaller there, and creates **`dist\UnsupervisedAdultsMC.exe`**.
4. Send that one EXE to your friends. Initial execution downloads official verified Prism Launcher 11.1.1 into `%LOCALAPPDATA%\UnsupervisedAdultsMC\prism-bin`. It does **not** bundle/distribute Prism itself.

The EXE needs internet access, but players do **not** need Python after you build it. Because this local build is unsigned, Windows SmartScreen may ask about an unknown publisher. Only share trusted builds; source is in this repository.

## Your modpack updates (the owner workflow)

**`pack/catalog.json`** is the human-edited mod list: name, Modrinth project slug, client/server side, resource pack/shader/mod type, and whether to include it.

1. Edit `pack/catalog.json` to add, disable, or remove mods. Increase **`pack_version`** for changed packs.
2. Run **`update_pack.cmd`**. It resolves published versions compatible with **Minecraft 1.21.1 Fabric**, recursively includes required dependencies, and generates **`pack/pack-lock.json`** plus `pack/resolution-report.txt`.
3. Review `pack/resolution-report.txt` for unavailable/restricted mods. Fix the catalog or choose an alternative.
4. Commit `pack/catalog.json` **and** `pack/pack-lock.json` to this repository's **`main`** branch. No recompiling and no GitHub Actions needed.
5. Friends' launchers fetch the new lock the next time they click **PLAY SMP**, download only changed files, verify checksums and clean up only previously launcher-managed files. Their own worlds, saves, screenshots, options and other unmanaged files are not touched.

If `pack-lock.json` has not been published, the launcher can still query Modrinth directly and cache compatible files, but **different players might resolve different mod versions**. Generate and commit a lock file before inviting friends.

## For your Crafty server

Run **`export_server_pack.cmd`** *after* `update_pack.cmd`. It makes a ZIP of only **server** and **both**-side mod JARs from the same pinned versions, with a report of any missing mods. Install a Fabric 1.21.1 server in Crafty, stop it, back it up, then upload the extracted mod JARs to the server's `mods` folder. The ZIP is *not* a standalone Fabric server installation.

For `server.properties`:

```properties
online-mode=true
white-list=true
enforce-whitelist=true
```

Add approved users in the Crafty console with `whitelist add MinecraftUsername`. The launcher's direct-connect button is convenient but does not conceal your server address from scanners.

## Limits and caveats

- **Most mods and resource packs** use [Modrinth's public API](https://docs.modrinth.com/api/) and official CDN downloads. Files are pinned and verified by SHA before installation. Each request has an identifying User-Agent. Mod version compatibility is based on published metadata; **visual conflicts still require actual testing**.
- **CurseForge-only files** may be blocked from automated downloads without permission or a suitable API/integration. The current catalog marks **Cinematic Interactions** for manual handling. Do not redistribute someone else's mod JAR just to bypass download restrictions. Ask for a redistributable/authorized download URL when possible.
- **EggMorph v0.2 alpha** is referenced by a pinned release URL and SHA256, but **the EggMorph repository is currently private**. That means friends cannot download it until you publish an accessible release. It is an optional download for the initial launcher preview and will be reported as unavailable instead of stopping the entire install. Publish it before using it on the actual SMP. EggMorph itself is not gameplay-complete.
- **Voxy** has no official Minecraft 1.21.1 Fabric release; the catalog disables Voxy and enables Distant Horizons as a candidate alternative.
- **Visual Workbench** and **Enhanced Block Entities Reloaded** are disabled pending compatibility testing. Shaders/resource packs are downloaded but **not force-enabled**; friends can choose their visual settings.
- This is an **auto-updating modpack**, not yet a self-updating launcher binary. When the launcher program changes, build and share a new EXE.
- Client only installs `client` and `both` modules. Dedicated server only gets `server` and `both`. Do not put client rendering/shader mods into Crafty.
- Supports Windows 10/11 64-bit for this alpha. Tested with Python unit tests; **no in-game Windows test has yet been run**.

## Source layout

```
build.cmd                 Build the EXE locally
update_pack.cmd           Pin exact versions for the group
export_server_pack.cmd    Create Crafty server mods ZIP
launcher.py               Windows desktop UI
ua_core.py                Network/API/update/Prism logic
pack/catalog.json         Mod list
pack/pack-lock.json       Generated by owner, commit to main
pack/resolution-report.txt Generated warnings for review
tools/                    Pack maintenance
 tests/                   Unit tests
```

## Security and privacy

The only executable game launcher provisioned is the **official [Prism Launcher](https://prismlauncher.org/)** portable build, downloaded from its official GitHub release, pinned to a known SHA256 digest. Minecraft files are downloaded by Prism. Mod downloads are HTTPS from Modrinth's CDN or explicit GitHub Releases with checksums; unexpected mod file hosts and redirects are blocked. No offline-mode authentication and no password collection.

Launcher settings and installed files are under `%LOCALAPPDATA%\UnsupervisedAdultsMC`; you can uninstall by removing that folder after backing up any saves. GitHub and Modrinth must be reachable for first-time setup and pack updates.

### Acknowledgments

Uses official Prism Launcher as an independently distributed program, under its own terms and licenses. Does not embed or claim ownership of Prism, Minecraft, or the listed third-party mods. All respective authors retain ownership of their files and releases.
