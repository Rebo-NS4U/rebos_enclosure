# Rebos Enclosure 2.0.1

This patch improves terminal bonsai presentation and includes desktop refinements since 2.0.0.

## Changes

- Bonsai: a glass terrarium with theme-tinted edges, side-pane reflections and a weighted base. A uniform charcoal background keeps the tree readable across wallpapers and transparent themes. Wood and ceramic shading respond to surface opacity; foliage and enamel keep their theme colors. Applies on the next terminal bonsai launch.
- Themes: refined Canopy fabric styling in the bar and assistant header, with varied header silhouettes.
- Settings: direct theme-section tabs and faster mouse-wheel scrolling.
- Greeter: centered time with white clock text.
- Assistant: specialist presets include task methods, verification criteria, bundled skills and read-only helpers.

## Update

```sh
./update.sh --release v2.0.1 --files-only --dry-run
./update.sh --release v2.0.1 --files-only
```

Download the release archive with its adjacent `.sha256` file or `SHA256SUMS`, then verify with `sha256sum -c SHA256SUMS` before extracting.

## Verification

The bonsai regression suite passed all 78 tests, including uniform background coverage, prompt color reset, preserved tree geometry and plain output. Payload checksums and installed bonsai source comparisons passed. Release archive deployment and recovery results are attached as `acceptance.json`.

Package installation, boot and hardware acceptance are not covered by these file-deployment checks. Existing limitations from the [2.0 audit](RELEASE-2.0-AUDIT.md) remain applicable.
