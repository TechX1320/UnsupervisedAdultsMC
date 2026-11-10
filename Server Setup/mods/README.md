# Generated Fabric server mod folder

Run **`Server Setup/build_server.cmd`** from the repository root on your Windows owner PC.
It downloads the exact Minecraft **1.21.1 Fabric** server-only and shared mods into this folder, checking publisher checksums. The new `UnsupervisedSMP-Crafty-...zip` contains these mods plus the runnable Fabric server launcher, `server.properties` and Crafty instructions. `export_server_pack.cmd` at the repo root still makes the older mods-only ZIP when updating an existing server.

This folder is intentionally **empty in GitHub**: third-party JARs can be large or redistribution-restricted. Do not manually download every dependency or push mod binaries to the repository. Check `../installed-mods.md` and `../unavailable-mods.txt` after a run. Your friends' launcher downloads the corresponding client and shared files from the same pinned `pack/pack-lock.json`.

In Crafty, **stop the server and back up the world first**, then upload the generated `*.jar` files into the Fabric dedicated server's `mods/` folder. Never upload client-only render mods like Iris, Sodium, shaders, or Voxy. Replacing world-generation mods on an existing map can damage terrain continuity.
