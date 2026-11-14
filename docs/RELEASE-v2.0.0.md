# Rebos Enclosure 2.0.0 — draft

Unpublished release notes. The current published release remains v1.8.0.
These notes describe the candidate source since v1.8.0; they are not a support
certification or an instruction to fetch a nonexistent v2.0.0 tag.

## Candidate changes

- More consistent shell appearance controls: semantic bar colors, microphone
  island control, improved brightness/sound/battery spacing, filled color
  previews, hue-arranged wallpaper suggestions and ordered RGB dithering.
- Terminal bonsai gains symmetrical pot ornaments, trunk hollows, and blossoms
  that follow the pot accent. Experimental vine and bare-tree changes were
  reverted and are excluded from the final behavior.
- Streamer uses the current Enclosure theme and live OLED settings, opaque
  content sheets, themed keyboard controls and full-title tooltips.
- Assistant conversations gain a responsive compact header, aligned wider
  composer, concise activity labels and collapsed completed-command details.
  Approval commands remain visible; chat switches reset editing/retry/disclosure
  state without disrupting streaming updates.
- Playback service clients have bounded queues and write deadlines. Relay
  metadata is bounded by complete source families with active/paused ownership,
  atomic playlist admission and cached-source refresh. Settings reconcile with
  persisted backend values after save failures and disconnects.
- Relay connections enforce public DNS answers at connection time while keeping
  original-host TLS verification. Environment proxies are bypassed only for
  relay upstream requests. Runtime socket cleanup refuses regular files,
  symlinks, foreign-owned sockets and uncertain listener failures.
- Subtitle assets have pinned revisions, SHA-256 verification and atomic
  replacement. Adapter provenance/license files are included. EPUB decompression
  work now has a cumulative limit; rejected imports preserve the existing library.
- RealtimeKit is a declared core dependency. The assistant shares the panel's
  existing hash-checked Qt screen guard, and greeter builds avoid the unused
  deprecated GTK color query. The guard is a mitigation, not a blanket crash fix.
- CI includes shell, assistant, Node, Lua and isolated Wayland screenshot checks.
  Committed-source exports include checksums; archive acceptance exercises
  fresh files, updates, preference preservation and journal-based file recovery.

## Update and recovery notes

Current installations keep personal preferences and accounts. Application source
links stay linked. No update restarts active playback or assistant backends;
Python changes take effect on the next normal backend start. File recovery uses
the reported deployment journal and does not downgrade packages, undo service
changes or reverse Git history. Read [source links and recovery](../desktop/SOURCE-LINKS.md).

2.0 version metadata/tag and final installation commands should be switched
only after acceptance is complete. Do not use `--release v2.0.0` yet.

## Verification and remaining gates

See [the release checklist](RELEASE-2.0-CHECKLIST.md) and
[validation record](../desktop/VALIDATION.md) for executed results. Temporary-home
file deployment and an isolated software-rendered compositor do not establish
fresh Arch package installation, AUR builds, boot/login, GPU support, suspend,
docking, lock/unlock, screen sharing, or authenticated provider/account behavior.

The relay still rejects a protected source family exceeding 32,768 routes;
indefinitely growing live streams need a separate retirement design. General
PDF/Calibre process sandboxing remains outside these repairs. Existing crash,
audio, portal and hardware investigations from the [audit](RELEASE-2.0-AUDIT.md)
remain acceptance work where they have no reproduced, safe automatic remedy.
