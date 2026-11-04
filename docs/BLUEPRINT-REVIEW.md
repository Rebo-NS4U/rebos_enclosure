# Blueprint review

Reviewed with Blueprint Studio 1.1.4 on 2026-11-04.

- **Missing CI: confirmed.** `.github/workflows/checks.yml` now verifies the
  payload, installer syntax, desktop tests and media tests with read-only
  repository permissions. Actions are pinned to reviewed commit IDs.
- **48 tests without obvious assertions: false positives.** 47 files contain
  Python assertion calls. `test_assistant_startup_preset.py` delegates to the
  existing QML harness and uses QML `check()` calls that exit on failure.
  The local desktop and media suites passed; these tests need no cosmetic rewrites.
- **Missing environment template: false positive.** The JavaScript environment
  reference is `process.env.HOME` in `primewire_browser.cjs`, used to locate
  local browser files. A dotenv template would not improve this setup.

Blueprint's framework-specific analysis does not cover this desktop stack.
Treat static findings as review prompts; passing tests and payload verification
remain the acceptance criteria. CI installs native dependencies in an Arch Linux
container and runs tests as an unprivileged user, including the Quickshell,
Niri and media checks. This avoids relying on tools present only on a
maintainer's desktop. Physical hardware verification remains a local check.
Installer tests record the AUR helper alongside system package commands, so
they cannot accidentally clone or build an AUR helper on a clean runner.
The container includes the compiler, GTK/ncurses headers, Fish and font tools
needed to exercise the real installer builds in temporary directories.

No application payload changed in this review. No installed service reload or
restart is needed. The workflows become active when these commits are pushed.
