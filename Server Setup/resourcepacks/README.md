# Unsupervised SMP - shared server resource pack

**You do NOT need to combine the normal client resource packs.** Our launcher already downloads Fresh Animations and Better Crops to each client's `resourcepacks/` folder. Players can stack those locally, and shaders are entirely separate.

The `resource-pack=` line in the vanilla `server.properties` supports one HTTPS ZIP. If you specifically want one *server-pushed* resource pack (for server logos, textures, custom sounds), use the merger:

1. Put only resource pack ZIPs that you **created or have permission to redistribute** into `input/`. Name them `10-base.zip`, `20-overrides.zip`, etc. Every input pack must target Minecraft **1.21.1**, `pack_format: 34`.
2. Run `Server Setup/merge_resourcepacks.cmd` on your Windows owner PC (Python 3.11+ on owner PC only).
3. Check `output/merge-report.txt`. When two packs replace the same `assets/` path, **the pack whose filename sorts later wins**. Combining assets is not the same as making incompatible animation/model formats work together.
4. Host `output/UnsupervisedSMP-ServerResourcePack.zip` over public HTTPS with distribution permission. Paste the URL and `resource-pack-sha1` from `output/resource-pack.properties` into Crafty's `server.properties` and restart. Decide whether to set `require-resource-pack=true`.

The tool deliberately ignores `data/` entries, which are **datapacks**, not client visual assets. Keep datapacks in the world `datapacks/` folder or install their Fabric mod version. It does not merge shaders and it never pulls third-party resource packs from Modrinth into a redistributable bundle automatically.

**Never publish a merged pack that contains copyrighted assets you do not have permission to redistribute.** A client-only pack can remain in the private launcher modpack without being merged/hosted by you.
