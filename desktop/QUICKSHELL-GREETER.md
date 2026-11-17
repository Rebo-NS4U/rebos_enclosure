# Quickshell login greeter

The default installer login choice is now `quickshell`; `regreet` remains a
supported legacy option, and `keep` leaves login configuration alone. The
Quickshell greeter uses the existing greetd PAM stack, Quickshell and Cage;
no new package or user session backend is required. ReGreet stays installed
for rollback. No running desktop or login service is restarted.

The MIT-licensed quickshell-greetd core and launcher are vendored under
`system/etc/rebos-greeter/quickshell`, with their source revision in `UPSTREAM`.
The Enclosure interface is separate from the session lockscreen. It supports
user and session selection, password failures, additional PAM prompts,
cancellation and power actions. Theme load failures use the upstream fallback.

`regreet-sync` publishes the current wallpaper and a restricted appearance JSON
containing only color roles, font, font size, radius and style. Existing path
and timer units keep both greeters updated. The interface uses the shared
ShellStyles surface colors; session-only widgets and decorative shell material
shaders are not loaded. When updating ShellStyles.js, synchronize the greeter's
copy. Installation also copies the canonical shell version.

To migrate an existing Enclosure installation after deploying its sync helper:

```sh
~/.local/bin/assistant-sudo --reason 'Switch to the Quickshell login greeter' -- \
  /usr/bin/bash desktop/scripts/install-quickshell-greeter.sh
~/.local/bin/regreet-sync
systemctl --user daemon-reload
```

The install script preserves `/etc/greetd/config.toml` under a timestamped
`/var/backups/rebos-greeter/` directory before changing it. It does not alter
PAM or restart greetd. To roll back, restore that backup using assistant-sudo
(or sudo on other installations); it takes effect on the next greeter launch.
Never restart greetd from an active desktop to test this change. A nested Cage
preview and the mock-protocol authentication test allow validation beforehand.
