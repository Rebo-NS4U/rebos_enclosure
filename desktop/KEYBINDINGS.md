# Replacing shortcuts

Settings → Keyboard shortcuts changes a binding's key while preserving its
action, options and command text. The old key is explicitly disabled so an older
mapping in an included file cannot become active again. An occupied key still
requires choosing another shortcut; editing does not silently replace a different
action.

Reusing an old disabled key replaces that declaration instead of appending a
second Niri node. The same rule applies when adding a new shortcut. Managed
`keybindings-defaults` files remain unchanged; overrides go into the corresponding
`keybindings-personal` file. Legacy/custom configuration files remain supported.

Before saving, Niri/Kitty validates the candidate. Changes to the source action or
target file during validation cancel the save. Successful changes retain a backup
beside the edited file. Niri reloads automatically; no desktop restart is needed.

Regression coverage: `desktop/tests/test_personal_bindings.py` and
`system/apps/shell/scripts/test_keybindings.py`.

`Mod+T` toggles book typing practice in the bar. Repeating the shortcut closes it, and `repeat=false` prevents key-hold repeats. Niri hot-reloads this binding. In typing practice, Backspace deletes normally; on an empty page it returns to the previous page with its last character removed so you can correct it. This also works after reopening a saved book.
