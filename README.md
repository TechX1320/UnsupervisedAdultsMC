# Unsupervised Adults MC

**One-click Windows launcher for the Unsupervised Adults SMP** — Minecraft Java **1.21.1**, **Fabric** and our maintained modpack. The EXE is our own interface. It uses the **official portable [Prism Launcher](https://prismlauncher.org/)** as an *external backend* for Microsoft account login, Minecraft installation, the Fabric loader, Java, and actually starting the game.

**Alpha**: The Prism download/hash/instance/command flows have unit tests, but the executable and live Minecraft login/install must be tested on Windows before sending it to friends. No GitHub Actions are used.

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
- Run **`export_server_pack.cmd`** to create a matching set of `server` + `both` mod JARs for Crafty. Fabric itself is installed/configured on the Debian server separately. Keep **online-mode=true**, **white-list=true**, **enforce-whitelist=true**; add each friend through the server console.
- Mods not legally available for automated downloads are reported (e.g. **Cinematic Interactions**); they must have an authorized direct source or be installed manually. Experimental **EggMorph**'s release repository is presently private, so friends cannot fetch that JAR without access. **Voxy** remains disabled on 1.21.1; the catalog lists Distant Horizons instead. Shaders and resource packs download without being forced on.
- The launcher EXE is *not* self-updating. For changes to the launcher program itself, rebuild and share a new EXE. The modpack can update independently from GitHub.

## Architecture and limits

- `launcher.py`: custom Tkinter GUI / one-click modpack update + Play
- `ua_prism.py`: official pinned Prism portable bootstrap, instance profile, optional migration, CLI launch
- `ua_core.py`: Modrinth/GitHub modpack resolver and checksum-verified updates
- `pack/catalog.json`: selected modpack items and Minecraft/Fabric versions
- `tools/` and the `.cmd` scripts: owner-only pack generation/export
- `tests/`: mocked unit tests; no tokens and no live Minecraft install required to run them

Prism **11.1.1** Windows x64 portable is downloaded on first run from the [official release](https://github.com/PrismLauncher/PrismLauncher/releases/tag/11.1.1) and pinned to its published SHA256. We **do not bundle or modify Prism** in our EXE. Prism is licensed under [GPL-3.0](https://github.com/PrismLauncher/PrismLauncher/blob/develop/LICENSE), and all Prism/Minecraft/third-party software remains the work of its respective authors. Minecraft ownership and Microsoft sign-in remain required; no offline authentication bypass.
