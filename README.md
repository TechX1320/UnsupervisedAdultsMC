# Unsupervised Adults MC

**All-in-one Windows launcher for the Unsupervised Adults SMP**, Minecraft **Java 1.21.1 + Fabric**. This is *our own launcher*: **no Prism, CurseForge application, Modrinth application, stock Minecraft launcher, or other executable launcher is installed**. Uses the [minecraft-launcher-lib](https://github.com/JakobDev/minecraft-launcher-lib) BSD-licensed Python *library* to communicate with official Minecraft services. The launcher itself packages all Python dependencies into one `.exe`.

**Status: 0.2 development alpha. Unit-tested but not yet tested end-to-end on Windows/Minecraft.** Always test with a throwaway world and an approved account before distributing to friends.

## What friends do

1. Download **`UnsupervisedAdultsMC.exe`** from you. No Python, separate Java, Fabric installer, Prism, or third-party Minecraft launcher needed.
2. Double-click **PLAY SMP**. On first launch, Microsoft sign-in opens in their normal browser and returns automatically to the app. This requires a valid purchased **Minecraft Java Edition** account.
3. The app fetches the pinned modpack, downloads official Minecraft game files, its Java runtime, Fabric, mods, shaders and resources, then launches Minecraft directly (and connects to the configured SMP).
4. Next time: click **PLAY SMP** again; files are verified, changed mods download automatically, and the remembered Microsoft account is refreshed.

**Players never need Crafty access.** The server must still use `online-mode=true`, `white-list=true`, `enforce-whitelist=true`, and you add approved users using `whitelist add MinecraftUsername`.

## Owner: Microsoft login setup — REQUIRED

Microsoft does **not** permit arbitrary custom launchers to impersonate the official Minecraft launcher. The owner must configure an Azure public-client application and request Minecraft API approval. Without a permitted Microsoft App ID, **the launcher can install files, but cannot log in or start online-mode Minecraft**. We intentionally don't ship borrowed or unofficial client IDs.

1. Follow [Microsoft's desktop app registration instructions](https://learn.microsoft.com/en-us/entra/identity-platform/scenario-desktop-app-registration). Register a personal-account-compatible **public client** application. Under **Authentication → Mobile and desktop applications**, add `http://localhost` as the loopback redirect URI. Allow public client flows. **Do not create or distribute a client secret.**
2. Request Minecraft API access for your new application through [Minecraft's application approval instructions](https://help.minecraft.net/hc/en-us/articles/16254801392141). You may need to wait for approval, and access is not guaranteed.
3. Copy the **Application (client) ID** (a UUID) into `pack/catalog.json` as `microsoft_client_id` and commit it to `main`. **The client ID is public, not a password.** Do not commit any tokens or secrets.
4. Test **SIGN IN WITH MICROSOFT** on your own Windows account. If you get an API permission error, confirm the app is approved; it isn't a missing launcher feature.

Sign-in uses PKCE and `state`, with a temporary local-only callback on an available port. Browser passwords are never shown to the launcher. Refresh tokens are stored under your Windows user profile using Windows **DPAPI** encryption and never committed to GitHub. Sign-in is personal to each friend.

## Build locally on Windows

1. Use **Code → Download ZIP** in this repo, unzip, and install [Python 3.11+](https://www.python.org/downloads/windows/) **on your build PC only** (check *Add Python to PATH*).
2. Double-click **`build.cmd`**. It creates `.venv`, installs pinned build dependencies, runs unit tests, and uses PyInstaller to create **`dist\UnsupervisedAdultsMC.exe`**.
3. Share that **one `.exe`** with friends. This is an unsigned personal build, so Windows SmartScreen may warn about an unknown publisher. You can code-sign it later.

There are **no GitHub Actions workflows** and no hosted launcher infrastructure required. The EXE auto-downloads Minecraft's official assets when first opened; it does not redistribute the proprietary Minecraft game inside the binary.

## Owner: modpack updates

- Edit `pack/catalog.json`: compatible mods, `side=client/server/both`, shader/resourcepack type, and `enabled` flag. Increase `pack_version` when modifying the pack.
- Run **`update_pack.cmd`**; it checks the Modrinth API for **1.21.1 + Fabric**, resolves required dependencies and creates `pack/pack-lock.json` plus an unresolved-mod report.
- Review the report, then commit `pack/catalog.json` and `pack/pack-lock.json` to **main**. Friend launchers read this lock on Play, download only changed files, verify SHA hashes, and remove only files they themselves previously installed. Their personal settings, worlds and screenshots remain untouched.
- `export_server_pack.cmd` prepares the same pinned `server`+`both` mod JARs for Crafty. It **does not** install Fabric on the Debian server; configure that inside Crafty separately.

**Publish a lock before inviting friends**. Until it exists, the launcher can resolve the catalog dynamically, but different players may select different releases.

## Current modpack limitations

- Mods hosted on **Modrinth** with a compatible Fabric 1.21.1 file can be fetched by the launcher; some authors publish only on CurseForge or block direct downloads. These are **reported as missing**, not silently pirated or rehosted.
- **Cinematic Interactions** is currently marked manual. Request a permitted direct URL or a compatible alternative.
- **EggMorph** is referenced as an optional direct GitHub release, but its repository is **private**; friends cannot download it until it becomes accessible. It is experimental and not ready for a production SMP.
- **Voxy** is disabled because there is no official 1.21.1 release. **Distant Horizons** is a possible alternative, but test it alongside shaders.
- Shaders and resource packs are downloaded, **not forced on**; people with weaker PCs can use their own video settings. Visual Workbench and EBE Reloaded are disabled pending tests.
- The EXE **updates the modpack**, not its own binary. For launcher software updates, rebuild with `build.cmd` and send a new EXE.

## Local game files

The isolated Minecraft installation lives at `%LOCALAPPDATA%\UnsupervisedAdultsMC\instance\.minecraft`; it does not modify the player's official `.minecraft`. Cached account credentials are protected in `%LOCALAPPDATA%\UnsupervisedAdultsMC\account.dpapi`. The latest Minecraft process log is `logs\latest-game.log` (tokens and launch arguments are not recorded by our code). The launcher downloads game files from Mojang/Fabric and mod files from checksum-verified allowlisted hosts.

## Source structure

```
launcher.py                  Tkinter desktop interface
ua_auth.py                   Microsoft OAuth PKCE, login refresh, encrypted token storage
ua_minecraft.py              Vanilla/Java/Fabric installer and direct game launch
ua_core.py                   Verified modpack resolver/updater, app folders
build.cmd                    Owner's local Windows EXE build
requirements-build.txt       Pinned Minecraft/PyInstaller build libraries
update_pack.cmd              Generate a reproducible modpack lock
export_server_pack.cmd       Generate server mods ZIP for Crafty
pack/catalog.json            Modpack catalog + public Azure client ID
pack/pack-lock.json          Generated/committed pinned version manifest
tests/                      Mocked tests (no Microsoft login required)
```

## License and acknowledgments

Our launcher project is provided as-is for hobby SMP use. Uses [minecraft-launcher-lib](https://github.com/JakobDev/minecraft-launcher-lib) (BSD-2-Clause), [PyInstaller](https://pyinstaller.org/), official Microsoft Minecraft services, and third-party mod authors' downloads according to their terms. It is **not** affiliated with Mojang or Microsoft and does not circumvent Minecraft ownership or server authentication.
