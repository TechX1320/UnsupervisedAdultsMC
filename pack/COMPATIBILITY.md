# Unsupervised SMP - compatibility fixes (0.5.3-alpha)

**EMI/REI:** Use EMI only. The old `RoughlyEnoughItems-*.jar` is not in our catalog and duplicates EMI's full-screen item panel. Check/Repair moves manually-added REI into `ua-disabled-mods`.

**Distant Horizons:** A Fabric 1.21.1 multiplayer server should run DH as well as clients if players want the impressive singleplayer-style LOD views beyond explored chunks. Our catalog marks DH as `both`, so the **next Create Server ZIP** includes it. For an already-running Crafty instance, **stop/back up**, use a mods-only update package to add the matching DH JAR, and restart without deleting the world. It may require significant server generation CPU/storage: start conservatively, and watch Crafty memory/CPU. Check F3's Distant Horizons server status.

**DH not rendering:** Distant Horizons **3.3.3** introduced config version 5 and resets old config values. In-game Options > Distant Horizons, ensure rendering is enabled and test 128-256 chunk LOD distance. Disable Iris shaders temporarily to see whether a shader blocks the LOD; re-enable only one that supports DH. On existing worlds, allow LODs time to generate; your new server does not automatically inherit the LOD database from a former singleplayer world. Do not indiscriminately delete DH's SQLite data.

**C2ME:** Manually installed C2ME alpha can slow or complicate DH generation; Check/Repair reversibly isolates it as a baseline test. This is a precaution, not a universally proven incompatibility. Avoid enabling it on the Crafty server until the worldgen stack is verified.

**EggMorph:** v0.2.0-alpha.4 is SHA-pinned in catalog and optional until in-game tested. Replaces newly dropped generic eggs with native mob spawn eggs where one exists; right-click marked eggs to morph instead of eating them. Normal unmarked spawn eggs stay normal. The proxy mob renderer now copies movement and yaw interpolation instead of teleporting each rendered frame. Install the same release on client and server. Old JARs are backed up; the repo must be PUBLIC for anonymous downloads.

After testing, run `update_pack.cmd` and commit a compatible **pack/pack-lock.json**. Without this, clients and Crafty can resolve different third-party mod builds at different times.
