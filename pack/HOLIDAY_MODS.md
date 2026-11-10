# Unsupervised SMP: Merry Mayhem
**Christmas / winter expansion - 0.6.0-alpha**  
**Game:** Minecraft 1.21.1, Fabric Loader 0.19.5+, Java 21.

The Unsupervised Adults get a Christmas village, snowy adventures, gifts for each other, festive mobs, and a few new reasons to explore. This update adds six default holiday mods and four optional alternatives. The full pack now has **106 enabled catalog entries** (including libraries and resources), not 106 separately verified working JARs.

## Enabled Christmas additions

| Mod | What it adds | Project |
| --- | --- | --- |
| Macaw's Holidays | Christmas trees, lighting, stockings, garlands, decorations (and Halloween for later) | [Modrinth](https://modrinth.com/mod/macaws-holidays) |
| Snowy Spirit | Sleds, winter decorations, village snowball fun | [Modrinth](https://modrinth.com/mod/snowy-spirit) |
| Winterly | Santa hats, presents, additional winter decorations | [Modrinth](https://modrinth.com/mod/winterly) |
| Festivities | Seasonal mob looks, villager gifts, food and the Magic Snowglobe | [Modrinth](https://modrinth.com/mod/festivities) |
| Gingerbread Houses | Christmas structures, decorated trees, gifts, reindeer and Krampus in compatible releases | [Modrinth](https://modrinth.com/mod/gingerbread-houses) |
| Big Gift Snowglobe | Snowy-biome landmark with a small loot dungeon and Strays | [Modrinth](https://modrinth.com/mod/big-gift-snowglobe) |

Each project lists Minecraft **1.21.1 Fabric** support on its published page. Our modpack resolver still needs to select a specific compatible file and dependencies. These additions are **both-side** mods: install on the Fabric server and every player's Prism client. They are optional from a download-failure standpoint until the entire combination is proven in-game.

Snowy Spirit's **Fabric API** and **Moonlight** dependencies are already in the SMP catalog; the Modrinth resolver also checks declared transitive dependencies.

## Optional - intentionally disabled

- [Rainbow Christmas](https://modrinth.com/mod/rainbow-christmas): candy blocks, lights and its own gingerbread structure; some overlap with the main choices.
- [DecorationX: Christmas](https://modrinth.com/mod/decorationx-christmas): 235 decorative blocks, snowball siege tools, snowman helpers and a winter boss. It is very newly released, so test separately first; check snowball block-damage settings.
- [Seasonal Additions](https://modrinth.com/mod/seasonal-additions): additional winter items and holiday chests.
- [Season's Greetings](https://modrinth.com/mod/seasons-greetings): presents, cocoa and snow golems; the 1.21.1 release is listed in maintenance.

To enable an optional mod later, change only its `enabled` field in `pack/catalog.json`, update and publish a new pack-lock, and update both sides together. Don't mix Fabric, Forge and NeoForge files.

## Seasonal behavior and world safety

- **Festivities is calendar-driven**: its Christmas features ordinarily activate during **December**; its in-game Magic Snowglobe can enable Christmas outside December. The other holiday mods can be used all year.
- **Structures generate only in new chunks**, not in areas the server has already explored. You do **not** need to erase an existing world. Visit new snowy biomes to look for gingerbread houses and the Snowglobe.
- Avoid removing these mods after Christmas if people have placed their blocks, stored items in presents, or discovered modded structures; removing world-content mods can damage saves. Back up the world before both installing and uninstalling.

## Owner installation (Crafty + Prism)

1. Stop the Minecraft server in Crafty; **back up the world, mods and configs**.
2. Download the new catalog via the normal launcher **Check / Repair**. This updates the client instance, not Crafty.
3. On your Windows build machine, run **`update_pack.cmd`** and inspect `pack/resolution-report.txt`. Fix missing dependencies; commit **`pack/pack-lock.json`** to GitHub `main` so the client and Crafty use the same builds.
4. For the **existing Crafty server**, run **`Server Setup/build_server.cmd`**, then copy only the required new/updated server JARs into the server's `mods/` while it is stopped. Do not import a full new server ZIP over the existing world. For a new Crafty instance, **Create Server ZIP** is appropriate.
5. Start Crafty, verify no missing-mod or registry errors, then restart the Prism game client and test login, a present, a sled and generation of a new holiday structure.

**Validation status:** Project pages show compatible releases, and the catalog's holiday selection is unit-tested. No full Windows Prism launch or Crafty startup with all 106 enabled entries has been performed yet. Watch startup logs and disable only the failing new mod if an incompatibility appears.

**Licensing:** Download files via each project's official Modrinth distribution; do not mirror other authors' JARs or redistribute bundled artwork without permission.
