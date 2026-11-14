# Visual review fixes — 2026-11-14

This change addresses all nine findings from the desktop visual review without
changing saved theme, model, playback or account preferences.

| Finding | Result |
| --- | --- |
| Shadow label overlaps its slider | “Blur radius” has a font-scaled label column; verified at 14, 18 and 24px in a narrow panel. |
| Assistant composer is disconnected from messages | Composer and conversation share a centered responsive column, capped at 1000px. Narrow panels retain margins. |
| Activity labels expose Markdown | Plain activity wording removes emphasis, headings, inline-code delimiters and link markup. Original command data remains available in details. |
| Media reveals distracting background text | The media content sheet uses the existing opaque theme variant. Wallpaper colors, fonts, OLED and light-mode preferences still apply. |
| Media checkboxes/sliders differ from other controls | Themed controls use semantic colors, visible focus, 36px hit areas and clearer indicators/handles. Native checkbox and slider behavior is retained. |
| Repeated settings headings | Removed repeated appearance, style, color and shadow headings; distinct group labels remain. |
| Wallpaper controls are under fonts | Folder and icon tinting now live in Wallpaper colors. Settings search keywords point there. |
| Assistant header/tool history is crowded | Preset/model selectors share a row where space allows and stack on narrow panels or while expanded. Quota display remains accessible. Tool command details start collapsed after approval; pending approval commands remain visible. Duplicate model captions are omitted on tool calls. |
| Catalogue titles are elided | Cards expose the full title on hover and keyboard selection; Play tooltips and accessible names include the title. Paging and card density are unchanged. |

The shell's legacy assistant keeps the shared activity-text, conversation-width
and tool-disclosure fixes; the separate Dweebo application's picker header uses
its existing preset/model components.

## Verification

- Full desktop suite: 532 tests, 530 passing and the same two explicitly opt-in
  Wayland screenshot tests skipped. All 91 media tests, 45 shell Python tests
  and three standalone Node regression files passed.
- New QML regressions exercise wide/narrow assistant alignment, adaptive header
  columns, completed-tool disclosure, visible pending-approval details, large-font
  shadow labels, moved wallpaper controls, keyboard checkbox/slider handling,
  disabled controls and original slider value units. Markdown normalization is
  checked for both assistant entry points.
- CI's offscreen Qt platform has no native PanelWindow backend. The media fixture
  substitutes ordinary windows only for native layer-window plumbing; production
  content, theme bindings and controls are exercised. Live media catalogue and
  playback-settings screenshots separately confirmed the opaque sheet and new
  controls after automatic reload.
- The live assistant automatically reloaded successfully. Its compact header,
  composer and collapsed tool cards were inspected. The isolated settings render
  reported no remaining shadow-label overflow. Custom clipped-surface rendering
  limitations in offscreen captures are not treated as desktop defects.
- Installed application paths resolve to this checkout. Payload checksums,
  Ruff and the 70-exception design gate passed. Personal screenshots/logs remain
  private under `/tmp/enclosure-ui-fixes/`; none are included in the payload.

No desktop process, playback service or assistant backend was manually restarted.
Media UI visibility was restored after inspection; no playback command was sent.
The desktop panel was not restarted to force configuration loading. Physical
multi-monitor/scaling acceptance remains part of the existing release checklist.
