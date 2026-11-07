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

The typing menu opens with a panel expansion followed by a content fade, keeping text at its final width throughout. Reduced motion shows it immediately. Typing practice displays the complete loaded section in a viewport capped at six lines. The viewport keeps the active typing line vertically centered, including the first and last lines, and also supports mouse-wheel scrolling; typing resumes centered tracking. Animated character components are created only near the visible lines, and character measurements and word offsets are reused for long sections; reading mode keeps its page navigation. New imports and pasted text stop at paragraph boundaries. Reimport an existing book to recover paragraph boundaries while keeping its ID and saved progress. Books without paragraph metadata use the existing bounded sections; paragraphs over 4,096 characters continue in the next section.
