# Screenshots

Print opens the Dweebo-themed Quickshell selector and editor on the focused output.
Drag an area, then draw, add arrows, boxes or text, or cover sensitive content with
opaque black redaction. Crop changes the export region; Full image resets it.
Ink colours, Undo and Redo are available in the floating toolbar.

- Print: select an area and edit.
- Ctrl+Print: edit the focused screen.
- Alt+Print: edit the focused window.
- Ctrl+C / Ctrl+S: copy PNG / save PNG to `~/Pictures/Screenshots`.
- Ctrl+Z / Ctrl+Y: undo / redo annotations.
- Escape: cancel without exporting.

The `wayland-screenshot` launcher accepts `area` (default), `edit`, `screen`,
`output` (focused screen), `window`, and `ocr`. OCR retains its existing
slurp/tesseract clipboard flow. Personal Niri overrides take precedence over
shipped defaults and should call the launcher to use the editor.

The UI stays loaded, with its windows hidden between captures, from `system/apps/shell/screenshot.qml`, sharing the shell's
QML theme and components. Niri prewarms it at login with `wayland-screenshot --warm`;
the launcher starts it lazily if needed, then uses IPC for each capture. Cancel,
Copy and Save hide the editor and clean the private capture without unloading
the theme. This avoids paying QML/theme startup costs on every shortcut. It does
not restart the panel or assistant. Temporary screen captures use uncompressed
PNG to avoid compression latency; saved images remain compressed PNG. Capture
uses grim for the focused output and Niri for the focused window. Pillow renders
annotations and crops at original pixel resolution, including scaled outputs;
text uses DejaVu Sans. Niri's window capture also updates the clipboard as part
of its compositor API. Screen/area cancellation leaves the clipboard unchanged.

Private originals and clipboard export intermediates live in a mode-0700 runtime
session directory. Closing cleans that session; abandoned sessions expire on the
next capture after a day. Save and Copy close after successful export; failures
stay open with an error so edits can be retried. Multi-monitor capture operates
on the focused output; selecting across output boundaries is not supported.

Core dependencies are Quickshell, Niri, grim, wl-clipboard, python-pillow and
DejaVu fonts. Satty is no longer required. No screenshot content or personal
shortcut overrides are shipped in the repository.
