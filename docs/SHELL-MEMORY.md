# Shell UI memory lifecycle

Island dashboard and settings panels load on demand. Their loaders keep the
outgoing panel alive until its opacity reaches zero, then destroy its object
tree. Reopening recreates transient panel state; shared services retain device
and application state. Power-menu keyboard navigation goes through the loaded
item.

Typing keeps its session and book helper alive so closing the panel does not
lose input or interrupt pending saves. Its word and character delegates exist
only while visible, practicing, and outside reading mode. Existing delegate
destruction unregisters glyphs and clears the caret target.

Run the isolated desktop checks from the checkout:

```sh
python3 desktop/tests/check_typing_practice.py island_lifecycle.qml
python3 desktop/tests/check_typing_practice.py
```

The first check opens and closes all 13 panels and verifies object lifetimes,
heights, and power selection. The typing check covers input, saved progress,
reading mode, and hidden character cleanup. These require desktop-session access.
Allocator retention means object destruction need not immediately reduce RSS;
these checks establish lifetimes, not a guaranteed RAM reduction.
