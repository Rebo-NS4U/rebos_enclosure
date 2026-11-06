# Detailed argument, duplication and branch review

This review uses the same Pylint design thresholds as the previous scans. Warnings fell from 150 to 137: duplicated-code blocks 9→7, branch warnings 37→35, positional-argument warnings 10→6. The total-argument warnings remain 10. No rules were disabled.

## All ten argument warnings

| Function | Review and decision |
| --- | --- |
| `deploy.install` | Payload and destination are required; the four independent deployment controls now require keywords. This prevents positional confusion between dry-run, settings, preference preservation and source linking. Total-argument warning retained. |
| `PreparedUpdate.__init__` | Checkout, staged plan, home, revision and working-state fingerprint are used to detect concurrent edits and recover updates. Optional untracked moves now require a keyword. Do not hide distinct recovery inputs in an untyped dictionary. |
| `App.launch_player` | The older GTK player passes show/episode selection, stale-request token, resolved links and settings. A playback-context object shared with its completion callback could be a useful later change; collapsing this signature alone would be cosmetic. Retained. |
| `App.player_finished` | Completion needs the captured show/queue/index/token and natural-end/exit results. The token prevents stale completions from changing new playback. Retained with launch_player pending a coherent playback-context refactor. |
| `LiveSubtitles.__init__` | Media/cache and ready/status callbacks are separate dependencies. Optional delay, language, position and duration now require explicit keywords. These values have different units and must not be accidentally swapped. Total-argument warning retained. |
| `media_sources.catalogue` | Kind, category, query and page select content; fetch is injectable and availability checking controls additional network work. No unrelated values were combined simply to pass a count threshold. Retained. |
| `Engine.launch_player` | Captures the same show/queue/index/token plus links, settings and paused transition state. A shared context refactor needs to cover start_episode, automatic advance, stored context and callbacks together. Retained this pass to preserve transitions. |
| `Redirects.redirect_request` | Required HTTPRedirectHandler override signature; dropping parameters would break the standard-library callback. Retained. |
| `KeyboardAgent.handle` | Required Gio DBus registration callback signature. Changing arity would break pairing. Retained. |
| `edit_keybinding.persist` | Destination, previous/proposed content, parser selection and key are all used by validation and atomic save. Optional concurrency guard now requires a keyword. Total-argument warning retained. |

## Duplication: source compared, not just counted

- ai_plan_usage.py and ai_questions.py were byte-identical between shell and assistant. The shell now launches the canonical assistant implementation through a small wrapper using the shared `system/apps` layout, which exists in both the repository and copied deployment. Existing entry-point paths are retained. No second implementation needs simultaneous fixes. Source and installed protocol tests verify both entry points.
- The bridge copies are **not equivalent**. The assistant adds parked state, resumability checks, preserving checkpoints while stopping, park/wake commands and a capability flag in attach/reset replies. Those differences explain five overlapping similarity findings. Blindly replacing one with the other would change runtime behavior. A future shared bridge should model these capabilities explicitly and cover both lifecycles; no live backend was restarted here.
- lockwall/thumbgen share a small subprocess error/timeout result pattern, while their surrounding responsibilities differ. Introducing cross-command dependencies for this short adapter does not currently buy enough to justify it.
- github_connect/github_update share a short Enter-to-close wrapper. It is small launcher boilerplate; extracting it would add a dependency without removing meaningful logic.

## Branch-heavy code

Question protocol response completion and cancellation now have named helpers separate from input parsing and method dispatch. Regression tests verify accepted answers, canceled requests, late responses, concurrent outstanding questions, unsupported form clients and recovery after invalid messages. The canonical serve function still has 13 branches versus the threshold of 12; the threshold was not relaxed.

The remaining branch warnings are real complexity signals but have different causes. Playback load/poll/event methods combine state transitions and deserve protocol-event tests before decomposition. Catalog and GitHub action dispatchers select distinct operations; eventual per-operation handlers can help, but replacing elif with a dictionary alone does not simplify those operations. Deployment/recovery combines trust-boundary checks with rollback guarantees, so its splits should preserve failure-injection tests. Hardware and monitor setup handle platform combinations; guard conditions must stay explicit. Validation routines have several legitimate rejection paths. No branches were removed simply to get a lower count.

The following inventory identifies every remaining branch warning precisely. It is a follow-up map, not a claim that every function was rewritten.

| File | Function | Report |
| --- | --- | --- |
| `desktop/scripts/deploy.py:287` | `install` | Too many branches (36/12) |
| `desktop/scripts/develop.py:192` | `action` | Too many branches (22/12) |
| `desktop/scripts/develop.py:266` | `menu` | Too many branches (14/12) |
| `desktop/scripts/hardware.py:79` | `detect` | Too many branches (14/12) |
| `desktop/scripts/linked_update.py:122` | `prepare` | Too many branches (18/12) |
| `desktop/scripts/setup.py:147` | `build_plan` | Too many branches (18/12) |
| `desktop/scripts/setup.py:272` | `monitor_wizard` | Too many branches (14/12) |
| `desktop/scripts/setup.py:396` | `main` | Too many branches (13/12) |
| `desktop/scripts/update.py:162` | `main` | Too many branches (14/12) |
| `system/apps/assistant/scripts/ai_bridge.py:156` | `attach` | Too many branches (22/12) |
| `system/apps/assistant/scripts/ai_plan_usage.py:15` | `read_usage` | Too many branches (13/12) |
| `system/apps/assistant/scripts/ai_questions.py:69` | `serve` | Too many branches (13/12) |
| `system/apps/media/discovery_catalogue.py:122` | `_page` | Too many branches (16/12) |
| `system/apps/media/live_subtitles.py:33` | `cues_from_whisper` | Too many branches (18/12) |
| `system/apps/media/live_subtitles.py:101` | `recognize` | Too many branches (14/12) |
| `system/apps/media/media_validation.py:10` | `mp4_duration` | Too many branches (15/12) |
| `system/apps/media/menu_backend.py:380` | `player_event` | Too many branches (30/12) |
| `system/apps/media/menu_client.py:13` | `relay` | Too many branches (17/12) |
| `system/apps/media/menu_requests.py:63` | `dispatch` | Too many branches (39/12) |
| `system/apps/media/mpv_session.py:72` | `monitor` | Too many branches (21/12) |
| `system/apps/media/stream_relay.py:45` | `serve_preloaded` | Too many branches (13/12) |
| `system/apps/media/stream_relay.py:102` | `serve` | Too many branches (13/12) |
| `system/apps/media/vlc_session.py:281` | `apply` | Too many branches (25/12) |
| `system/apps/media/vlc_session.py:366` | `poll` | Too many branches (22/12) |
| `system/apps/media/vlc_session.py:447` | `monitor` | Too many branches (13/12) |
| `system/apps/shell/scripts/ai_bridge.py:153` | `attach` | Too many branches (18/12) |
| `system/apps/shell/scripts/apply_app_palette.py:29` | `patch_jsonc` | Too many branches (16/12) |
| `system/apps/shell/scripts/apply_desktop_palette.py:124` | `apply` | Too many branches (17/12) |
| `system/apps/shell/scripts/edit_keybinding.py:53` | `save` | Too many branches (13/12) |
| `system/apps/shell/scripts/github_projects.py:231` | `action` | Too many branches (30/12) |
| `system/apps/shell/scripts/github_status.py:95` | `check` | Too many branches (20/12) |
| `system/apps/shell/scripts/list_keybindings.py:74` | `niri` | Too many branches (17/12) |
| `system/apps/shell/scripts/list_keybindings.py:138` | `kitty` | Too many branches (14/12) |
| `system/apps/shell/scripts/system_monitor.py:326` | `get_gpu_stats` | Too many branches (18/12) |
| `system/apps/shell/scripts/window_rules.py:25` | `render_rule` | Too many branches (15/12) |

## Verification

Final source passed 347 desktop tests and 84 media tests, plus 13 focused keybinding tests. The question protocol tests also passed against installed entry points. Ruff, payload verification, source/installed comparisons and a preference-preserving deployment preview passed. Active desktop and assistant services were preserved. Installed script changes apply to new helper launches.
