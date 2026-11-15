---
name: light-linux
description: Diagnose Linux configuration, desktop integration and small-script failures. Use for concrete Linux fixes; skip for unrelated explanations.
---

Start with the failing command, log excerpt or config. Choose the narrow probe that separates the likely causes. For platform and tool availability, run `python3 ../../scripts/preset_tools.py environment` relative to this skill directory; it reads platform metadata and executable locations only. It does not establish desktop connectivity or service health.

For a service failure, inspect the named unit and its recent logs, distinguishing `systemctl --user` from system units. For desktop connectivity, inspect the session environment and the named service through approved tools; request supported approval on restricted access. An empty process list is not evidence a service stopped.

For config changes, resolve the installed symlink and owning source before editing. Use the actual program's parser or dry-run if available. QML and Niri hot-reload; preserve running apps. Check both the requested behavior and an obvious neighboring behavior. If a command is unavailable, report it rather than installing packages as an incidental diagnostic step.

Use connected documentation tools for unfamiliar library APIs; Context7 is optional and must be discovered before use. Prefer the installed version's official documentation. Existing repository and permission policies still apply.
