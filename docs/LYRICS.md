# Media lyrics

**Mod+M** toggles the media menu instead of launching Spotify. It keeps the
menu open rather than using the two-second playback-key preview, and leaves
the active player and playback unchanged. **Mod+Ctrl+T** separately toggles
the pinned lyrics overlay.

The island Media Center and dashboard player include a Lyrics section. Choose
Top or Bottom to keep a lyrics card over the desktop after closing the menu;
Unpin closes that card. **Mod+Ctrl+T** toggles the pinned overlay on and off.
It opens on the focused monitor, reuses the last chosen edge, and defaults to
Bottom before a placement is chosen. Holding the key does not repeatedly toggle.
The shortcut uses `qs ipc -p ~/.config/quickshell call lyrics toggle`. The card uses the menu's screen, follows the active
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

Lyrics sections in the media menu and dashboard, and the pinned overlay, appear
only when the current song has nonempty timestamped lyrics. They disappear for
text-only, loading, missing, instrumental and offline results, without a manual
text-only mode or empty lyrics card. Pin placement is retained so the overlay
returns automatically when timed lyrics become available. Opening the media
menu still requests lyrics while its lyrics section is hidden.

Player-supplied lyrics take priority, including Spotify lyrics when exposed in
MPRIS metadata (`xesam:asText`, `xesam:lyrics`, `lyrics`, or `spotify:lyrics`).
Spotify does not necessarily expose lyrics through its desktop player. No
Spotify account credentials or private APIs are used.

Otherwise, opening lyrics or keeping them pinned sends the current song title,
artist, album and duration to [LRCLIB](https://lrclib.net/docs). Timed lyrics use
a scrolling stack of rows: the active line centers smoothly with a tinted
accent gradient, an edge marker and larger text; nearby lines stay subdued.
Row colors, scale and control opacity animate using the shell's Motion settings.
Turning motion off makes scrolling and highlights immediate. Manual scrolling
pauses auto-follow until **Follow playback** is pressed. Forward and
backward seeks update the highlighted row. Long lines wrap to fit the card.
Untimed lyrics are hidden. Playback following and highlights require real
timestamps; song duration and word counts are not used to guess vocal timing.
Requests expire after 12 seconds; old track responses are ignored. Successful
lookups are cached in memory for up to 40 songs.

LRCLIB lookup first uses `/api/get` with the player's track signature. If that
returns no match, invalid parameters, or an empty lyrics record, `/api/search`
tries title and primary artist without requiring the same album. Search results
must match the title and artist (ignoring punctuation and spacing) and stay
within five seconds of the known track duration. The closest matching synced
record is preferred; plain and instrumental results keep the view hidden.
Unrelated songs and recordings outside that duration tolerance are rejected.
Rate limits and network errors show a retry message without automatic retry
loops. Requests identify Enclosure using LRCLIB's `Lrclib-Client` header; no API
key or additional packages are required.

The feature uses Qt's HTTP support and adds no package dependencies. Regression
check: `python3 -m unittest discover -s desktop/tests -p test_lyrics.py`.

## Playback timing and scrolling

Lyrics Plus remains the lyrics provider; the shell computes highlights from
line timestamps and its own playback clock, rather than copying Spotify's UI
highlight. The clock anchors to MPRIS position and respects pause, seeks and
playback speed. A one-shot timer schedules each lyric cue and the preceding
centering cue, so transitions do not wait for the panel's 250 ms position tick.
Player position updates correct differences larger than 120 ms.

The scroll target is separate from the sung line: it moves toward the next row
160–400 ms before its timestamp, based on the spacing between lines. A critically
damped spring preserves velocity when retargeting. Highlighting starts at the
actual timestamp. Text-only lyrics stay hidden until genuine timestamps
become available. This uses
the Dux timing approach with the existing Enclosure typography, palette and Motion setting.

A plain-text provider result stays internal while the shell checks LRCLIB for
timed lyrics, including search when the exact result is untimed. Failed timing
lookups keep the lyrics view hidden. `qs ipc -p ~/.config/quickshell call lyrics timing`
reports the clock and active/follow indices without lyric text.

Regression checks: `python3 -m unittest discover -s desktop/tests -p 'test_lyrics*.py'`.

## Lyrics Plus bridge

The optional Spicetify Lyrics Plus integration runs its installed provider code
inside Spotify. The shell receives only track URI, provider name, lyric text and
line timestamps through a loopback bridge at `127.0.0.1:19837`. It accepts the
Spotify UI origin only; it does not export tokens, cookies or account data.
Track URI matching prevents another song's lyrics from appearing. Heartbeats
restore the bridge after a panel reload without reloading Spotify.

Install the media package group (`spicetify-cli`, `spotify-launcher`, `nodejs`),
then run from the shell source directory:

```sh
python3 scripts/setup_lyrics_plus.py
spicetify backup apply -n
```

The setup assembles the adapter from the package's actual Lyrics Plus provider
files and enables both the Lyrics Plus custom app and the adapter extension.
The `-n` flag preserves the running Spotify session. Reload Spotify when ready
to activate them. Rebuild the adapter after a Spicetify package upgrade. This
was prepared against Spicetify 2.46.4 and Spotify from spotify-launcher.

The adapter tries Spotify, LRCLIB, Musixmatch (only when a token was configured
in Lyrics Plus), then NetEase. The existing shell lookup remains available when
the bridge has no result. Native Spotify lyrics from Lyrics Plus take priority.
Karaoke word timing is not exported; line timing and plain text are supported.
Provider availability and account/region restrictions still apply. Configure
Lyrics Plus inside Spotify for any provider credentials; never put those in
shell configuration. `qs ipc -p ~/.config/quickshell call lyrics status` reports
provider and line counts without printing lyrics or credentials.
