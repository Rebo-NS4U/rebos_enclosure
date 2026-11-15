# Upstream sources and licenses

Enclosure began from [jR4dh3y's dots-niri](https://github.com/jR4dh3y/dots-niri).
Its shell derives from [Ambxst by Axenide](https://github.com/Axenide/Ambxst)
with subsequent contributor changes. The current application source is
[`system/apps/shell/`](system/apps/shell/), retaining its
[AGPL-3.0 license](system/apps/shell/LICENSE). Other bundled components retain
licenses alongside their source, fonts and assets.

The MovieBox protocol adapter retains its upstream
[provenance record](system/apps/media/vendor/moviebox-tui/SOURCE.md) and
[MIT notice](system/apps/media/vendor/moviebox-tui/LICENSE-MIT).

The current wallpaper collections are:

- [Ismail Inceoglu / Seventeenth](https://seventeenth.artstation.com/): 60 images, with [per-image artwork sources](system/share/wallpapers/Ismail%20Inceoglu%20-%20Seventeenth/sources.json).
- [Cycle Circle / Zombie012](https://zombie012.artstation.com/): 10 images, with [per-image artwork sources](system/share/wallpapers/Cycle%20Circle%20-%20Zombie012/sources.json).
- “my wolpapors :3”: 62 images from a user-supplied shared album. Individual artists are unidentified; [metadata](system/share/wallpapers/My%20Wolpapors%20-%20Shared%20Album/sources.json) records hashes and dimensions without account/album access links.

The [MAKC collection](https://github.com/makccr/wallpapers) is historical provenance,
not one of the current bundled collections. Artwork rights remain with the
respective artists; a collection curator is not automatically its artist.

Additional asset attribution:

- “Polite Warning Tone” by [nlux](https://freesound.org/s/622773/), Attribution 4.0: [bundled notice](system/apps/shell/assets/sound/attribution.txt).
- OpenDyslexic by Abbie Gonzalez: [copyright and SIL OFL 1.1 notice](system/share/fonts/opendyslexic/OFL.txt).
- Bundled font/icon families: JetBrains Mono, League Gothic and Phosphor.
- GoogleDot-Black cursor contributors: the bundled metadata identifies a Google-inspired theme but does not name an individual creator. Google is not credited as its author.
- Papirus icon contributors: installed icon-theme dependency.

The expanded [README credits inventory](README.md#credits) also acknowledges
Arch/package maintainers and desktop, media, lyrics, captioning and narration
projects. Dependency acknowledgement is distinct from adapted-source provenance
and does not imply project endorsement.

Old root dotfile snapshots, duplicate wallpaper/font copies and retired
hardware-specific installers have been removed from the working source tree.
Git history retains provenance; it is not a second installation source.
Use [the current installation guide](desktop/README.md) and
[filesystem guide](docs/FILESYSTEM.md), rather than archived upstream commands.
