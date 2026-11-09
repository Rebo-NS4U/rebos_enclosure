# Reader pinning

Click **Pin** in the reader header to move the open reader into a normal desktop window, like the assistant. It stays available while using other panels. **Unpin** returns the same reader to the island panel; **Close** closes it. Pinning lasts for the current shell session.

Verify with `python3 desktop/tests/check_typing_practice.py typing_reader_pin.qml` in a Wayland session.

Pinned readers always use the fullscreen reading layout. The window retains the panel’s themed translucent surface and compositor blur; compact layout controls are hidden while pinned.
