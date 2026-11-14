# Final release bug repairs — 2026-11-14

Four reproduced failures from the final review are repaired:

- **Relay route lifetime:** players retain their source families through pause
  and playback. Requests and fresh preloads protect their families too. Eviction
  removes whole inactive families; playlist registration reserves the complete
  batch before publishing links. Equivalent header capitalization/defaults share
  routes, and evicted resolution-cache entries are resolved again. Failed VLC
  replacement keeps the previous source; closing a player releases ownership.
  Both session players and the legacy GTK launch path participate.
- **Settings recovery:** the menu tracks confirmed, in-flight and queued values,
  sends serialized patches and filters acknowledgements by request identity.
  Errors reconcile with the backend snapshot, including rollback support for
  older backends without snapshots. Disconnect discards unconfirmed edits;
  reconnect refreshes persisted settings. Offline controls are disabled and
  save errors appear inside Settings. Backend save-before-publish behavior stays
  intact.
- **Chat interaction identity:** both assistant sidebars reset editing, retries
  and tool disclosure on chat/message identity changes. Chat switches also clear
  the retry target. Same-message streaming updates preserve interaction state.
- **Socket preservation:** startup checks type, ownership and listener state
  before removing a stale socket. Regular files, symlinks, foreign-owned sockets,
  live listeners and unexpected probe errors are preserved. Shutdown checks
  socket identity before removal, preserving a replacement file.

## Verification and limits

New regressions exercise active HTTP reads under route pressure, paused player
ownership, atomic manifest admission at capacity, VLC failed replacement/close,
header deduplication, close-during-load and stale cached URLs. Socket tests cover
sentinel files, symlinks, live/stale listeners, ownership, unexpected probe errors
and replacement files at shutdown. Isolated real-QML scenarios exercise settings
rejection/coalescing/stale replies/disconnect/reconnect and equal-length chat
switches in both sidebars, plus same-message streaming and replaced messages.

These tests use temporary origins, players and homes; they do not change real
conversations or interrupt current playback. QML's offscreen media harness adapts
native window plumbing only. Existing live Python services load the fixes on
their next normal start; no backend or desktop restart is required for source
synchronization. Installed application directories already link into this checkout.

The relay remains bounded at 32,768 routes. If a single protected family exceeds
that limit, it fails clearly rather than publishing broken links. Indefinitely
growing live playlists still need a separate sliding-window retirement design.
Provider uptime, real network/account failures and fresh-machine hardware/boot
acceptance remain outside this focused repair pass. This is not a claim that no
other bugs exist. See [validation](../desktop/VALIDATION.md) for executed checks.
