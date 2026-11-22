# Rebos Enclosure v2.1.0

- **Rebos Streamer** adds episode and TV season downloads, cancellation, and a Downloads view with Play and Delete actions. Anime catalogue cards group seasons under one show. Playback remembers series subtitle choices and shows the target time while a skip buffers. The HLS relay reuses recently fetched segments when seeking. Whisper adds French and German audio translation modes.
- **Enclosure Music** adds fullscreen listening, Spotify playlist suggestions, Daily Mixes, playlist sync and a shared ten-band PipeWire equalizer. Music can import, preview and download tracks from supported playlists.
- **Desktop** adds independent background and button finishes, a Wallpaper gallery, a theme-synced Quickshell login greeter and laptop lid action choices. Starwake adds difficulty settings, boss encounters and a timed Warp Run.
- **Dweebo** adds account switching, chat-scoped auto approval, and keyboard shortcuts for opening, closing and navigating chats. Neovim adds an integrated Dweebo chat.

## Install or update

```sh
bash install.sh --release v2.1.0 --interactive --dry-run
bash install.sh --release v2.1.0

./update.sh --release v2.1.0 --files-only --dry-run
./update.sh --release v2.1.0 --files-only
```

The source archive includes an adjacent SHA-256 checksum. Verify it with `sha256sum -c rebos_enclosure-v2.1.0.tar.gz.sha256` before extracting. See the attached `acceptance.json` for file deployment, upgrade and recovery results.
