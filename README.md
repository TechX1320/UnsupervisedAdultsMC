# Unsupervised Adults MC

**One-click Windows launcher for the Unsupervised Adults SMP** — Minecraft Java **1.21.1**, **Fabric** and our maintained modpack. The EXE is our own interface. It uses the **official portable [Prism Launcher](https://prismlauncher.org/)** as an *external backend* for Microsoft account login, Minecraft installation, the Fabric loader, Java, and actually starting the game.

**Alpha**: The Prism download/hash/instance/command flows have unit tests, but the executable and live Minecraft login/install must be tested on Windows before sending it to friends. No GitHub Actions are used.

**Fabric Loader compatibility (0.4.1-alpha):** The current adventure modpack requires **Fabric Loader 0.19.5+**, not the old 0.16.14. The launcher now upgrades the Fabric component of **existing** Prism instances on Play/Check & Repair, while preserving their saves/settings. **Close Prism before clicking Play** so its cached instance settings cannot overwrite the updated version. Run `update_pack.cmd` to refresh `pack/pack-lock.json` and publish it along with the catalog. Rebuild the **Crafty ZIP** so the server has the matching Fabric Loader 0.19.5; the builder now validates its local cached Fabric server JAR version and replaces old binaries. To upgrade an **existing** Crafty instance safely without touching the world, follow `Server Setup/README.md` → **URGENT: Fix existing Crafty server**. An existing Crafty server should be stopped and backed up before updating its Fabric launcher; **do not import the ZIP as a second live server over your world**.

## For players (no Python or Java installation required)

1. Download `UnsupervisedAdultsMC.exe` from the owner and place it in a writable folder such as `D:\Games\UnsupervisedAdultsMC` (not Program Files).
2. Open the EXE and click **PLAY SMP**. It downloads the SHA256-verified official Prism portable release and sets up a dedicated Minecraft 1.21.1 Fabric instance with our modpack. **On the first run**, the Prism window opens for its initial setup and Microsoft account sign-in. Choose **Accounts → Add Microsoft** if necessary; sign in with the Microsoft account that owns Minecraft Java Edition.
3. Close Prism after signing in, return to our launcher and click **PLAY SMP** again. Prism downloads/verifies Java and the Minecraft files and launches the SMP. It can automatically join the server address entered in our launcher.
4. On later launches, click **PLAY SMP**. The launcher checks modpack updates and asks Prism to launch the instance with the remembered account. Prism may show its UI for authentication renewal or errors.

Friends **do not install Prism separately** or need Crafty access. The portable Prism binary is downloaded by our launcher into its own folder beside the EXE. There is **no Azure application registration** required from the SMP owner for this Prism-based flow.

## Storage — portable beside the EXE

```text
D:\Games\UnsupervisedAdultsMC\
  UnsupervisedAdultsMC.exe
  UnsupervisedAdultsMC_Data\
    prism-bin\                  # verified Prism portable executable
    prism-data\                 # Prism account settings, game downloads, Java
      instances\
        UnsupervisedAdultsSMP\
          mmc-pack.json         # Minecraft 1.21.1 + Fabric Loader
          instance.cfg
          .minecraft\          # mods, packs, saves, config, screenshots
    settings.json               # SMP server address
    lock-cache.json             # last valid modpack lock
```

The launcher uses Prism's `-d` option so all persistent game and account data is under `UnsupervisedAdultsMC_Data` beside the EXE, **not** the regular `%APPDATA%\.minecraft` folder. Normal Windows temporary files and caches can still be created by Windows/Prism.

If you tested the old direct-launch version, the new launcher automatically **moves** nonconflicting mods, configs, saves, resource packs, shader packs and options to Prism's instance (not a duplicate copy). It leaves the old `UnsupervisedAdultsMC_Data\instance` directory containing older downloaded game assets/Java intact. **Delete that old directory manually only after confirming your Prism version works and your saves/settings have moved.** The old `account.dpapi` belongs to the obsolete authentication system; it is not migrated or used by Prism.

## Owner — build on your Windows PC

1. Download/clone this repo; install Python 3.11+ **only on the build PC**.
2. Run **`build.cmd`**. This creates `.venv`, installs PyInstaller, runs source tests and packages a self-contained `dist\UnsupervisedAdultsMC.exe`.
3. Place the built EXE in a **writable folder**, not under Program Files, and test **Play SMP** with your own account before sharing.
4. No GitHub Actions or cloud builds are necessary. Windows SmartScreen may warn because the EXE is unsigned; the owner can code-sign it later.

## Owner — modpack changes and Crafty

- Edit `pack/catalog.json` to select compatible mods. Increment `pack_version` when changing them.
- Run **`update_pack.cmd`** to resolve and hash exact 1.21.1 Fabric Modrinth releases and dependencies. Review `pack/resolution-report.txt`, then commit `pack/catalog.json` and **`pack/pack-lock.json`** to `main`. Clients fetch only changed files, verify hashes, and remove only files previously managed by our updater.
- **New: `CREATE SERVER ZIP`** in the launcher builds a full **Crafty-importable Fabric 1.21.1 server** containing the Fabric server launcher JAR, `server.properties` and matching `server` + `both` mod JARs. The archive is written to `UnsupervisedAdultsMC_Data/Server Setup/UnsupervisedSMP-Crafty-<pack version>.zip` beside the EXE. The first server start downloads remaining Fabric/Minecraft dependencies through Fabric's official launcher. In Crafty's **Upload Zip Archive** panel, choose this archive, use its root, select `fabric-server-launch.jar` as executable, and use Java 21. Review `CRAFTY-IMPORT.txt` inside.
- **Owner CLI alternative:** run `Server Setup/build_server.cmd` after pulling source. It resolves the exact pinned mod versions and generates the same complete Crafty ZIP under the repository's `Server Setup/` folder. `export_server_pack.cmd` remains available to create a **mods-only update ZIP** for an existing server.
- Preserve **online-mode=true**, **white-list=true**, **enforce-whitelist=true**; add each friend through the Crafty console. The new server ZIP does not contain an accepted EULA, world, passwords, or Crafty credentials.
- Mods not available for permitted automatic downloads are reported (e.g. **Cinematic Interactions**); they need an authorized source or manual installation. **EggMorph**'s GitHub repo is **private**, so public launcher clients receive a download error. If you own the JAR, download it from your signed-in private release and place `eggmorph-0.2.0-alpha.jar` into the owner-side `Server Setup/mods/` cache before making the Crafty ZIP; a matching SHA-256 is required. **To make EggMorph automatically downloadable for friends, publish the compiled JAR at a publicly accessible HTTPS location and update the catalog URL/lock.** Do not embed GitHub access tokens in a launcher. EggMorph remains experimental and should be tested separately. **Voxy** remains disabled on 1.21.1; the catalog lists Distant Horizons instead. Shaders/resource packs download without being force-enabled.
- The launcher EXE is *not* self-updating. For changes to the launcher program itself, rebuild and share a new EXE. The modpack can update independently from GitHub.

## Architecture and limits

- `launcher.py`: custom Tkinter GUI / one-click modpack update + Play
- `ua_prism.py`: official pinned Prism portable bootstrap, instance profile, optional migration, CLI launch
- `ua_core.py`: Modrinth/GitHub modpack resolver and checksum-verified updates
- `ua_server.py`: owner-only full Crafty server ZIP builder (Fabric launcher, JARs, properties, reports)
- `pack/catalog.json`: selected modpack items and Minecraft/Fabric versions
- `tools/` and the `.cmd` scripts: owner-only pack generation/export
- `tests/`: mocked unit tests; no tokens and no live Minecraft install required to run them

Prism **11.1.1** Windows x64 portable is downloaded on first run from the [official release](https://github.com/PrismLauncher/PrismLauncher/releases/tag/11.1.1) and pinned to its published SHA256. We **do not bundle or modify Prism** in our EXE. Prism is licensed under [GPL-3.0](https://github.com/PrismLauncher/PrismLauncher/blob/develop/LICENSE), and all Prism/Minecraft/third-party software remains the work of its respective authors. Minecraft ownership and Microsoft sign-in remain required; no offline authentication bypass.

## Unsupervised SMP - server-owner setup (Minecraft 1.21.1 Fabric)

The modpack is now themed **Unsupervised SMP** with exploration biomes, structures, wildlife, tools, weapons and treasure. Run [`Server Setup/build_server.cmd`](Server%20Setup/build_server.cmd) on your **owner PC** to generate the actual server JARs under `Server Setup/mods/` plus a ZIP. The generated server folder and installed-mod list are not published as third-party binaries in GitHub. Follow the full **[Server Setup README](Server%20Setup/README.md)** before uploading files to Crafty.

For optional owner-supplied resource packs, run [`Server Setup/merge_resourcepacks.cmd`](Server%20Setup/merge_resourcepacks.cmd) to build a combined 1.21.1 ZIP. Most client visual packs should remain separate under the custom launcher's automatically installed `resourcepacks/` directory—there's no need to merge Fresh Animations, Better Crops, or Solas shaders into a server pack. Only merge assets you are licensed to redistribute.

**Important:** Adding biome generators, ores, and structure mods is best done with a **fresh world**. Server and clients must use the same generated `pack/pack-lock.json`. Preserve `online-mode=true` and the whitelist; players don't get Crafty access.

## Create Server ZIP button (quick reference)

Run the newly built `UnsupervisedAdultsMC.exe`, click **CREATE SERVER ZIP**, and upload the generated archive using the **right-side Upload Zip Archive** section in Crafty's Create New Server page. This **does not upload the ZIP for you** or require your Crafty password. The file is stored beside the EXE under `UnsupervisedAdultsMC_Data/Server Setup/`. Select the ZIP root and executable `fabric-server-launch.jar`; use Java 21 and confirm the Minecraft EULA when Crafty prompts. The ZIP is for creating a **new** server; back up existing worlds separately and do not overwrite them with a new-generation pack. Read `Server Setup/README.md` for troubleshooting.

## Unsupervised SMP 0.5.0-alpha — expanded adventures

The catalog now includes exploration structures from **Dungeons and Taverns, Structory, Moog's Voyager/Nether/End Structures, Tidal Towns, and additional YUNG's overhauls**, plus Incendium and Nullscape terrain, additional wildlife/hostile mobs, travel equipment, cooking, furniture, Lootr, EMI, and server pregeneration. See **[pack/ADVENTURE_MODS.md](pack/ADVENTURE_MODS.md)** for the full theme and compatibility plan. Some high-impact or overlapping mods remain **disabled until tested**.

**Important:** Run `update_pack.cmd` and commit the resulting `pack/pack-lock.json` before sharing a new client or Crafty server ZIP. Start a **fresh test world**: adding worldgen and structure mods to existing chunks does not regenerate them. Fabric Loader **0.19.5+** and Java **21** are still required.
