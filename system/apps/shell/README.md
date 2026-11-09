# <img src="./assets/rebos_shell/rebos_shell-logo-color.svg" alt="" width="40" height="40"> rebos_shell

**rebos_shell** is a Niri-first Wayland desktop shell built with
[Quickshell](https://quickshell.org).

## Hard fork

This project is a **hard fork** of
[Ambxst](https://github.com/Axenide/Ambxst) by
[Axenide](https://github.com/Axenide).

It is not Ambxst, does not track Ambxst as an upstream merge target for
day-to-day work, and ships under its own name, branding, config paths, and
release process. The fork keeps a lean runtime focus:

- wallpaper
- one unified bar
- floating run menu
- lockscreen
- reactive JSON configuration

Multi-monitor support uses Quickshell `Variants` on `Quickshell.screens`.

## Features

Version **1.1.6** adds the redesigned clock dashboard, edge window navigation,
desktop shortcut creation and adjustable window corners. It also updates shell
outlines, media handling, blur and idle network resource use.

Published source and the complete Arch desktop are maintained in the
[rebos_enclosure installer](https://github.com/Rebo-NS4U/rebos_enclosure).

- Runs directly on [Niri](https://github.com/YaLTeR/niri) via its JSON event stream
- Normalized monitor, workspace, and window state for multi-monitor setups
- Unified bar with workspaces/taskbar, clock, system status, and systray
- Floating run menu and power menu
- Wallpaper picker and secure `WlSessionLock` session lock
- Isolated `rebos_shell` config, state, cache, data, and IPC paths
- [Persistent assistant](scripts/ai_bridge.md) that keeps working across shell reloads

## Direct commands

The shell exposes lightweight commands through its IPC runner. For example,
`rebos_shell run wallpapers` opens the wallpaper picker on the focused monitor
and toggles it closed when invoked again. This can be bound from Niri with:

```kdl
Mod+Shift+W hotkey-overlay-title="Open Wallpapers" { spawn "rebos_shell" "run" "wallpapers"; }
```

## Run the development tree

Install Quickshell and the runtime tools needed by the shell. Install fonts once,
then run from a checkout:

```bash
./scripts/install-fonts.sh
qs -p /path/to/rebos_shell
```

Or use the CLI wrapper:

```bash
./cli.sh
```

## Updater

Use the [rebos_enclosure updater](https://github.com/Rebo-NS4U/rebos_enclosure/blob/main/update.sh)
from your enclosure checkout to update the bundled desktop while keeping saved
preferences:

```bash
cd /path/to/rebos_enclosure
./update.sh --dry-run     # Fetch and verify without changing installed files
./update.sh --files-only  # Apply desktop files without upgrading packages
```

The updater fetches the remote default branch, verifies the payload, and creates
a recovery backup under `~/.local/state/rebos-desktop/backups`. Git and Python 3
are required; run it as your normal user. Standard XDG paths under HOME are required.
Existing preferences and wallpapers are retained. Without `--files-only`, the
updater also upgrades installed packages. Log out and back in after applying an
update to load the updated desktop.

The installer and Nix package are still inherited scaffolding and may need
adjustment for this fork.

## Attribution and license

rebos_shell is a customized desktop shell derived from Ambxst by Axenide and contributions by jR4dh3y. Full copyright and
contributor history from that lineage is preserved in this repository’s Git
history.

This project is licensed under the GNU Affero General Public License v3.0 or
later. See [LICENSE](./LICENSE).

### Continuous typing dropdown

Fullscreen typing uses the original animated glyphs, row highlight and smooth
cursor, with visible lines expanding to fill the available height. Compact
typing keeps seven rows. Text scrolls continuously and bounded loading retains
visible context through window handoffs. Both activities use the shell font
and a centered 720px column. Ctrl+Tab switches typing and reading while the
passage is active (not while editing notes). F11 switches sizes; Escape leaves
fullscreen while keeping the activity. Appearance motion controls typing
animations in both sizes.

Typing preserves paragraph indentation and blank rows from the reader. Press
Tab at ⇥ and Return at each ↵ (two Returns between paragraphs), then Tab for
the next indent. Tab and Return have outlined key markers. Correct Tab presses slide forward;
Return presses dip down and left, with a brief press and glow. These effects
share the bounded key-animation budget and stop when Appearance motion is off. Wrong keys, including
spaces at these markers or Tab/Return at a letter, advance and count as errors;
Backspace lets you correct them. Existing bookmarks
and partial input are mapped to the formatted target without changing book
identity or source positions. Backspace edits text and does not jump to an
earlier window. Saved-progress revisions reject writes from an outdated view;
a conflict asks you to reopen the book instead of overwriting newer progress.
The invisible typing input ignores Select All. Printable keys, including
Shift+A, preserve existing text even if an old keyboard selection remains;
Backspace cannot delete that entire hidden selection.

Open typing with its keyboard shortcut or `qs ipc call typing toggle`. Typing
replaces the expanded bar contents, using the same input and dismissal behavior
as its other panels. The compact typing surface uses a faint glass fill, soft blur and a subtle rim;
controls are text only. The typing panel fits around seven rows total, including blank rows above and below the text, with only
Library, Import and Close in the header. Setup controls stay hidden while typing. Panel
resizing, passage reveals and typed characters animate smoothly, respecting the
Appearance motion setting (zero disables animations). Upcoming characters are faint, and typed characters become opaque
(errors use the error color). Type directly over the passage. Backspace to correct.
Paste text or import documents, then select **Start practice**. Completed passages
advance and the document loops forever, without a timer or failure state. **Library** opens book management; **Back** returns to the typing field.
Escape moves between typing and the library; **Close** collapses the bar. Clicking outside collapses the bar.
Imported books, pasted text, and progress are now cached locally under
`$XDG_DATA_HOME/rebos_shell/typing-books/library.sqlite3` (normally
`~/.local/share/rebos_shell/typing-books/`). Nothing is uploaded. Choose a saved
book and **Resume** to continue, including a partially typed passage. Progress
saves after a short pause, every five seconds during typing, when a passage is
completed, and when the view is closed. Re-importing identical text resumes its
existing location instead of duplicating the book.

Book mode supports EPUB and MOBI as well as the existing document formats, up to 100 MB
and 20 million extracted characters. EPUB chapters follow the book's spine;
chapter/part/book/section headings, prologues and epilogues, isolated numbered or
Roman-numeral headings, and Markdown headings are detected in other formats
when their structure is available. Use **Library** for chapter navigation and a
position slider. Scanned PDFs still need OCR first; legacy DOC and RTF are not
supported. PDF extraction uses Poppler's `pdftotext`.

Only the current passage (at most 90 Unicode code points) enters the practice
renderer. The backend caches one active book in memory and stores books in
SQLite, with bookmark records separate from immutable content; it does not send a whole book through the text editor on every page.
Letter lifts, color shimmers, and staggered passage entrances remain bounded to
this small window and respect the Appearance motion setting. Chapter and overall
progress stay visible in a quiet footer. IPC:
`qs -p ~/.config/quickshell/shell.qml ipc call typing toggle`.

The secondary **Practice samples** section includes six original CC0 passages: a lowercase
warmup, two short stories, a reflective passage, dialogue and punctuation, and
numbers and everyday details. Expand the section, select one, then choose **Start practice**. These
passages may be copied, changed and shared freely. Choosing a passage replaces
the text in the editor; pasting and document import remain available.

Open typing practice with `t` in a terminal. The shell IPC
command `rebos_shell run t` also opens it. Repeating `t` closes the panel; reopening resumes the saved book.
Choose **Import** while typing, or **Import EPUB / MOBI / PDF** in the library, to open
the native file chooser. The bar temporarily releases keyboard and pointer input
until you select a document or cancel. EPUB and other document formats are
included in the Books filter. Niri focuses this import dialog automatically.

Press **Mod+T** to open book typing practice directly from the desktop. The top
bar keeps the book title and **Notes** visible; **⋯** groups Reading mode (F11),
Book library and Import book actions. Each library card has **Remove**, followed
by confirmation. Removal clears only that book's local text, progress and notes;
the original imported file stays on disk.

F11 opens a fullscreen **reading mode** with plain, selectable book text and
no typing input, accuracy effects, caret or WPM. The fullscreen page uses a
centered 720-pixel reading column, centered 20px text in your configured theme font,
and the same glass surface, opacity and palette as typing mode. Subtle directional
page slides and fades follow the shared motion setting, including reduced motion.
Use Left/Right arrows, Page Up/Page Down, Space/Shift+Space to turn pages; [ and ]
change chapters. Vim keys **h/l** turn pages and **k/j** change chapters.
N opens book notes, and **?** shows the keyboard guide.
Escape or F11 returns to typing at the current
reading position. Switching modes without navigating preserves partial typing.
Right-click a word or select it and press Ctrl+Space for definitions and notes.

Press **Ctrl+Space** while typing to open definitions and notes for the current
word. Definitions, word notes and the notebook open directly below the typing
panel, aligned to its left edge and matching its width and height. Both menus
reveal downward from the panel edge when opened and retract upward when closed;
reopening during a close reverses the motion, and reduced motion is respected.
The fullscreen notebook has a book header, highlighted section tabs, note counts,
a responsive two-column card grid, and a larger editor with pinned save controls. Press it again (or Escape) to close the panel and return to
typing after saving or discarding edits. The word panel uses the same themed
background, accent border and reading font as the typing panel. Right-click a
word to inspect it. Use **Notes** to open this book's notebook, browse **People**,
**Settings**, **Mysteries**, **Plot**, or **General**, and create a titled note.
Search filters titles and content without creating notes. Choose **New note**,
enter its title and section, then **Create note** to start writing. Navigation
and save/cancel actions stay visible while the contents scroll. **Cancel**
restores the saved note. Each note can be moved between sections;
**Insert outline** supplies an editable outline for characters, places, clues, or
plot connections. Existing word notes stay in **General** until you categorize
them, and word-popup notes appear in the same notebook. Definitions appear inside the reader
using the [Free Dictionary API](https://dictionaryapi.dev/) (English, internet
required). **Online definitions: On/Off** is saved across reader sessions; turning
it off cancels lookup and keeps notes available offline. Only the selected term
is sent to the dictionary service.

The word menu shows the selected word, its definition and any saved note.
**Add note** or **Edit note** opens the editor; **Options** reveals search, saved
words and the online dictionary switch.

Notes are stored locally per book and case-insensitive word/name. Choose **Save
note** to keep a reminder, select a saved term to reopen it, or clear its note and
save to remove it. Unsaved edits must be saved or discarded before changing terms
or closing the panel. Notes survive reader restarts and re-importing identical
book text without changing reading progress.

The active typing cursor is a slim rounded accent caret with a soft halo and
a subtle current-character highlight. It glides between letters on the same
line, snaps cleanly at line wraps, and gently breathes while idle. It follows the editing position, including
arrow keys, and remains visible during passage animations. Chapter selectors,
scrollbars and the position slider use the same semantic palette as the shell.
A large title card marks the opening page of each chapter, including chapter
jumps. It stays above the passage until that page is completed; reading windows
stop at chapter boundaries so the next chapter begins on a fresh page.
The chapter menu is scrollable, shows the current section, and provides previous
and next controls. Selecting an entry jumps to that exact section and resumes
typing. EPUB navigation follows NCX/EPUB3 file and anchor targets, including
multiple chapters within one file and chapters spanning file boundaries, with image
heading alternatives as a fallback. Re-importing identical book text refreshes
its title and chapter labels without resetting saved progress.

Opening typing practice with Mod+T or the control panel automatically resumes
the last opened book, including a partially typed passage. The last-book selection
and bookmarks survive shell restarts. The library uses scrollable book cards
with completion percentages and progress bars; selecting a card resumes that
book. Completed books retain 100% completion when continuous practice loops.
Built-in samples are kept out of book cards and live in a collapsed secondary
section.

The live WPM counter uses net correct characters and five characters per word.
It updates twice a second, starts after one second of activity, and pauses its
clock after five idle seconds. Restored text and chapter jumps do not earn WPM;
opening the library, hiding typing, or switching books starts a fresh session.

Mod+T toggles typing open and closed. Passages are fitted to the available viewport (at most 36 measured lines)
instead of a fixed character count. Completing the final character advances
automatically, fading only the passage while the header and WPM stay steady.
Keystrokes received during the short page fetch are queued for the next passage.
Existing saved partial passages remain intact when switching to the new layout.
Continuous practice advances after the visible page is typed, even
if some characters differ; errors stay highlighted and WPM counts only correct
characters. Saved windows from older layouts are carried into the new pages
without changing the absolute position in the book.

Reading mode displays the imported paragraph breaks with a full empty line between paragraphs and an indented first line.
Bookmarks and typing positions continue to use the original normalized text.

Typing IPC status includes the latest animation frame timing sample (up to 120
frames), live glyph/word counts, layout-fit count, loaded text size, and motion
duration for investigating slow sessions. Sampling runs only during active typing
effects; it keeps one sample in memory and does not log keystrokes or text.

The typing workspace stays open on outside clicks; use Close, Escape, or the
typing shortcut to leave it. Reopening an already loaded session reuses its text
and layout; resizing or switching reading mode still refits the page.

In the small typing menu, the chapter card appears at the chapter opening and
hides as soon as typing begins. It stays hidden mid-chapter and returns at the
next chapter opening. Fullscreen keeps the current chapter title visible. Its surfaces and the typing panel follow
the selected shell theme. Reading mode keeps its chapter-opening title layout.

Select a word and choose **Definition & context** to show its surrounding
passage and fetch English definitions directly from the Free Dictionary API.
No AI agent or assistant connection is required. Only the selected word is sent
to the dictionary service; the passage stays local and remains readable if the
network lookup fails. This explicit lookup works independently of the automatic
online dictionary switch. Selecting another word clears the previous results;
closing the popup cancels the dictionary request.

Word lookups use a content-sized popup capped at 520px wide; longer results scroll.
Notes use a compact browser (up to 640px wide, 900px in fullscreen) with search
and section filters pinned above the results. Cards show title, category, and a
two-line preview. The editor gives the note more room while keeping Save and
Cancel visible; Ctrl+S or Ctrl+Enter saves. Popup sizes stay within the typing
workspace, and long lists scroll.

Typing begins near the top and scrolls once the active row reaches the vertical
midpoint, keeping that row centered in both sizes. The chapter-opening card sits
above the compact passage until typing starts. Rapid keys, Tab, Return, and
Backspace are buffered during page handoffs; glyph updates avoid duplicate work
and use a native prefix check for appended input.

Chapter selection shows durable completion percentages and progress bars. Completion tracks the union of typed text ranges from this version onward; chapter jumps and reading mode do not mark skipped text complete. Older bookmarks are preserved but cannot reconstruct historical typing coverage.

MOBI import uses Calibre’s `ebook-convert` locally to preserve book metadata and chapter navigation through the EPUB importer. Install `calibre` (included in the core package selection). DRM-protected books are unsupported. Conversion uses temporary files, cleaned up after import, and has a two-minute timeout.

The typer adapts to each output’s logical resolution (Qt handles DPI scaling). Compact and fullscreen panel widths scale within screen bounds; compact row counts shrink on short displays, fullscreen passage text grows up to 1.5×, and narrow-window actions wrap. Pinned reader defaults and minimum sizes are capped to the output. Resizing reflows the passage without navigating or changing its bookmark.
