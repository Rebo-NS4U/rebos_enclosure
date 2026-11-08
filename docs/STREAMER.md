# Standalone Rebos Streamer

The independent checkout is https://github.com/Rebo-NS4U/Rebos_Streamer.
Its `ui/shell.qml` runs in a separate Quickshell process. Enclosure ships a
portable snapshot under `system/apps/media`, including the required Dweebo
visual components and the ani-cli resolver. The panel no longer instantiates
AnimeMenu. The existing launcher delegates to the media app's `launch` script.
The playback user service and runtime socket retain their names, preserving
playback across UI reloads. No installation step restarts active playback.

For standalone development, clone Rebos_Streamer and run `python3 install.py`.
Enclosure updates own its managed launchers and may restore their bundled
paths; run the standalone installer again to select the external checkout.
Keep task changes synchronized between this portable snapshot and upstream.
