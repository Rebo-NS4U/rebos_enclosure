# Integrated desktop interfaces

The existing Enclosure Quickshell remains the shell. Its launcher, Wi-Fi panel,
Bluetooth panel, PipeWire device/application mixer, notification server/history,
and session menu are reused. No greeter files or wallpaper treatments change.

`DesktopDialogs.qml` adds the polkit agent and a shared searchable selection
window. It uses StyledRect, StyledText, SearchInput and ThemeButton, inheriting
Colors, Styling, Motion and ShellStyles through the canonical components. Its
surface follows the selected material, corner frame, font and opacity, with no
full-screen dimming. Content scrolls within the available screen. Search arrows,
Enter, Escape and tab focus work without animation. Authentication responses
are cleared on submission, prompt changes, completion and cancellation.

`rebos-menu` accepts newline-separated choices on stdin and returns a selected
line, or exit status 1 on cancellation/unavailability. Clipboard (`Mod+V`), emoji,
and editor-specific project selection use it; the existing app/project launcher
continues to own launcher shortcuts. The optional terminal project picker remains
available. The shell starts `scripts/menu_broker.py`; its mode-0600 socket is in
XDG_RUNTIME_DIR. Selection/clipboard contents travel in memory, never temporary
files, command arguments or logs. Concurrent selectors are rejected. The shell
restarts a failed bridge and polkit registration retries after backend outages.

BlueZ and NetworkManager remain the connection backends. Bluetooth keyboards
retain displayed passkeys; other devices now receive themed confirmation,
permission and masked PIN/passkey prompts with cancellation. Agent registration
is scoped to the device being paired and cleaned up when Pair completes or
fails. No Blueman activation is needed by this path. Network passwords continue
to use nmcli stdin, not process arguments. Advanced network/Bluetooth buttons
open the corresponding integrated settings page. Audio device, microphone and
application controls remain in the existing panels/settings mixer.

The portable Niri profile no longer starts the external polkit agent. Quickshell
owns org.freedesktop.Notifications and the polkit session agent. Keep recovery
packages installed until successful password authentication and physical device
pairing have been checked; this change does not uninstall packages or overwrite
personal theme/network settings. Fuzzel palette exports are retained for other
user-installed consumers, but shipped selection scripts no longer invoke it.

## Verification and activation

Run the menu transport and emoji tests in desktop/tests; Bluetooth pairing,
Bluetooth scrolling/credential-stdin and connectivity tests live under the shell's
scripts directory. `qs ipc -p ~/.config/quickshell call desktopDialogs status`
reports registration and dialog visibility without exposing secrets.

This installation's rebos-panel.service sets QS_DISABLE_FILE_WATCHER=1 as an
existing crash mitigation. Source edits therefore require an explicitly approved
panel service restart to activate; do not restart Niri or assistant/media services.
Normal installations that enable watching can hot-reload QML. After startup,
verify polkitRegistered is true and use a harmless `pkexec /usr/bin/true` request
to check authentication and cancellation. Do not run two session agents.

Live checks in this change verified Quickshell registration, authentication
cancellation (pkexec exit 126), synthetic menu selection, rendered dialog
appearance, the existing panels opening, active notification ownership, Niri
configuration validation, and connected backend discovery. Successful-password,
wrong-password and physical pairing/connection tests require user participation;
existing Wi-Fi connections and audio mute/volume were preserved. Do not claim
these interaction paths were verified against physical devices from mocks alone.
