# Quickshell login greeter

The installer login choices are `quickshell` and `keep` (leave login configuration alone). The
Quickshell greeter uses the existing greetd PAM stack, Quickshell and Cage;
no additional user session backend is required. ReGreet is retired. No running desktop or login service is restarted.

The MIT-licensed quickshell-greetd core and launcher are vendored under
`system/etc/rebos-greeter/quickshell`, with their source revision in `UPSTREAM`.
The Enclosure interface is separate from the session lockscreen. It supports
user and session selection, password failures, additional PAM prompts,
cancellation and power actions. Theme load failures use the upstream fallback.

`greeter-sync` publishes the current wallpaper and a restricted appearance JSON
containing color roles, typography, geometry, transparency, dithering and
custom surface definitions. Existing path and timer units keep the greeter
updated. Only explicitly allowed visual fields are published.

The greeter uses the shell's actual `StyledRect`, `Styling`, `Motion` and
`ShellStyles` components, including material canvases and compiled linear,
radial, halftone and dither shaders. The panel and login controls use the same
renderer. Buttons, input fields and labels are the canonical `ThemeButton`,
`SearchInput` and `StyledText` components, with the shell's hinted text rendering,
semantic colors, focus/hover/disabled states, corner sizing and layout density.
The background uses `TintedWallpaper` and its palette shaders plus the lockscreen's
palette-colored dim overlay. The exported display settings follow wallpaper
tinting and the bar's 12/24-hour clock preference. Entry motion uses the shared
Motion durations and respects zero-duration motion; capped panels scroll at
large font sizes and keyboard focus keeps the active control visible. `prepare-quickshell-greeter.py` assembles these dependencies directly
from canonical shell source during installation, so no separate material copy
needs maintaining. Small Config/Colors adapters consume the public appearance
export without loading session services.

For a nested material check, assemble into a temporary directory, copy
`desktop/tests/fixtures/greeter-materials.qml` into its
`themes/enclosure/shell/` directory, and run that file through `cage -- quickshell -p`.
The fixture cycles the material finishes plus custom radial/halftone shaders,
saves snapshots under `/tmp/rebos-material-*.png`, and exits automatically.

To migrate an existing Enclosure installation after deploying its sync helper:

```sh
~/.local/bin/assistant-sudo --reason 'Switch to the Quickshell login greeter' -- \
  /usr/bin/bash desktop/scripts/install-quickshell-greeter.sh
~/.local/bin/greeter-sync
systemctl --user daemon-reload
```

The install script preserves `/etc/greetd/config.toml` under a timestamped
`/var/backups/rebos-greeter/` directory before changing it. It does not alter
PAM or restart greetd. To roll back, restore that backup using assistant-sudo
(or sudo on other installations); it takes effect on the next greeter launch.
Never restart greetd from an active desktop to test this change. A nested Cage
preview and the mock-protocol authentication test allow validation beforehand.
