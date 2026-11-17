# Output equalizer

Open **Media Center** for the compact equalizer beneath the playback controls,
in the former embedded-lyrics area. Both island and standard players use the same
compact vertical EQ controls: all ten faders are visible together, with a preset
card carousel and bypass/reset actions. Music/Other tabs filter the cards; arrow
buttons, touchpad scrolling and keyboard focus reveal additional cards. The media panel widens within the screen bounds;
smaller layouts wrap faders into rows and shorten them to fit available height. The on-screen
lyrics strip remains separate. The full editor is also available at
**Sound → EQ & mixer → Equalizer** or **Settings → Sound → Equalizer**.
The output/input device controls and application mixer remain in the same audio
page. The equalizer is initially bypassed; choose a preset and enable it when
wanted. Each of the ten vertical bands (31 Hz–16 kHz) adjusts from −12 to +12 dB in 0.5 dB
steps using the mouse or arrow keys. Edits select Custom. Reset to flat clears the
curve; bypass removes processing and restores the physical output route.

Music cards: Flat, Pop, Rock, Hip-Hop, Electronic, Jazz, Classical, Acoustic and
Lo-fi. Other cards: YouTube, Podcasts, Movies and Gaming. Existing Music, Speech,
Bass and Treble saved selections remain readable as legacy presets. These are tonal curves;
Gaming does not add surround and Movies does not add a dynamic-range compressor.
The complete curve's frequency response is swept to calculate automatic headroom
with a 1 dB margin above its highest steady-state response. Boosted presets can
sound quieter. This is gain compensation, not a peak limiter or hearing protection.

The themed interface uses the canonical SettingsGroup, StyledText, ThemeButton,
ThemeSlider, StandardProgressBar, Colors, Styling and Motion components. Presets
wrap, bands change to one column on narrow screens, and text/controls scale with
the theme. Keyboard focus, reduced motion and all material finishes are inherited.

## Backend and persistence

`rebos-equalizer.service` runs independently of the panel. It uses PipeWire's built-in
filter-chain with ten peaking biquads at Q=1.4 and a linear input gain stage. The
processing rate is 48 kHz, with PipeWire handling device/application conversion.
Existing `pipewire`, `libpipewire` and `libpulse` packages provide the filters and
control tools; no separate effects application or DSP plugin package is required.

Enabling creates `enclosure.equalizer`, routes default playback through it and
moves existing streams from the former default output. Explicitly routed streams
on other devices are left alone. Output selection while enabled changes its
physical destination. Master volume and mute continue to control the physical
output; the filter's own playback stream and virtual device are excluded from
application/device lists. Microphone routing and controls remain unchanged.

Bypass restores streams to the output and removes the filter. The service does
not restart PipeWire, WirePlumber, applications or playback. A crashed filter is
recreated; audio-backend outages report an error and are retried. Graceful service
shutdown restores routing before stopping its child filter. Panel restarts leave
the independent equalizer service running.

Preferences are saved atomically with mode 0600 in
`~/.config/enclosure/audio-equalizer.json` (or under XDG_CONFIG_HOME). Runtime
configuration and the private control socket live in XDG_RUNTIME_DIR. Only EQ
preferences and the selected output are persisted; no audio is recorded by the
production service. Quickshell starts the service on demand through its user unit.

## Verification

- `test_audio_equalizer.py`: invalid values, UI/backend preset consistency,
  frequency response/headroom, saved preferences and backend error intent.
- `test_audio_equalizer_pipewire.py`: private PipeWire, PulseAudio compatibility
  and WirePlumber session with hardware monitors disabled. Synthetic tones verify
  measured Flat/Bass gain, live control updates, filter recovery and bypass.
- `test_audio_equalizer_ui.py`: production audio tab and actual private EQ worker;
  mouse preset selection, keyboard slider adjustment, persistence, material styles
  and narrow/large-text layout. It can also run in the isolated native Wayland
  preview session.

The real desktop is left bypassed after deployment checks. Do not reset or restart
its audio server to activate this feature. This installation disables panel file
watching, so activating QML changes requires a separately approved panel restart.
