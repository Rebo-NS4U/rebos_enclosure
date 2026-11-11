# Media lyrics

The island Media Center and dashboard player include a Lyrics section. Choose
Top or Bottom to keep a lyrics card over the desktop after closing the menu;
Unpin closes that card. The card uses the menu's screen, follows the active
player, hides on the lockscreen, and falls back to the first screen if its
monitor disconnects. Pin placement lasts for the current shell session.

The pinned card hides its controls, title and attribution after three seconds
without pointer or keyboard activity. A subtle themed surface remains behind
the lyrics for contrast; text uses the shell's configured font, size and native
rendering, and follows theme changes. Move the pointer over the card to reveal
its options.
Turn off **Auto-hide** to keep the full card visible. The media menu itself
always keeps its controls visible. The overlay keeps its size so lyrics do not
jump when controls disappear; Auto-hide resets when the shell starts.

The pinned overlay hides while loading or whenever the current song has no
nonempty lyrics (including instrumental, missing, offline and no-player
states). Its pin placement is retained so it returns automatically when lyrics
become available. Loading messages and Retry remain accessible in the media menu.

Player-supplied lyrics take priority, including Spotify lyrics when exposed in
MPRIS metadata (`xesam:asText`, `xesam:lyrics`, `lyrics`, or `spotify:lyrics`).
Spotify does not necessarily expose lyrics through its desktop player. No
Spotify account credentials or private APIs are used.

Otherwise, opening lyrics or keeping them pinned sends the current song title,
artist, album and duration to [LRCLIB](https://lrclib.net/docs). Timed lyrics show
the current and next line, following playback and seeks. Unsynced lyrics are
scrollable. Missing, instrumental and offline results have explicit states and
a Retry button. Requests expire after 12 seconds; old track responses are
ignored. Successful lookups are cached in memory for up to 40 songs.

The feature uses Qt's HTTP support and adds no package dependencies. Regression
check: `python3 -m unittest discover -s desktop/tests -p test_lyrics.py`.
