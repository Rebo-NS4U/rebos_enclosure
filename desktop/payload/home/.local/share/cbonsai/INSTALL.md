# Local cbonsai installation

Installed 2026-10-16 from https://github.com/h0ethan04/cbonsai/blob/master/cbonsai.c (a mirror of John Allbritten's cbonsai). Source and GPL license are kept in this directory.

Rebuild from the home directory:

```sh
gcc -O2 ~/.local/share/cbonsai/cbonsai.c -lpanelw -lncursesw -o ~/.local/bin/cbonsai
```

`~/.local/bin/terminal-bonsai` captures cbonsai print mode, adds a rounded frame, and applies true colors from `~/.cache/rebos_shell/effective-palette.json`. Fish calls it through `fish_greeting` in `~/.config/fish/config.fish`. It displays only in interactive terminals with at least 36 columns and 18 rows.

Refined on 2026-10-16: the original 12 curated silhouettes sized for the terminal, rounded foliage with the original two tones, a ceramic-style Unicode pot with a freshly generated symmetric geometric pattern on each launch, and centered double-line framing without labels. Soil dots, extra silhouettes, and added foliage shading were reverted at the user's request. All colors follow the wallpaper palette. The previous renderer is preserved as `terminal-bonsai.original.py`.

Refined on 2026-10-17: continuous tapered planter sides with 21/19-cell patterned rows; Unicode wood strokes and a smoothed, tapered exposed trunk with a centered root flare. The cbonsai C generator still supplies the original silhouettes; the greeting renderer refines the exposed stem afterward. Bark stays dark walnut (`#553f31`, restrained `#694f3e` highlights) independent of the wallpaper. Checked 384 renders spanning all 12 silhouettes, 16 motifs, and both motif spacings. Backup: `terminal-bonsai.before-trunk-refinement-2026-10-17.py`.
