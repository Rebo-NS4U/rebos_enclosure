# Rebos Enclosure v1.5.0

Includes completed portable changes since v1.4.1 and OpenRouter model launch support.

- Dweebo offers Free Code (Cohere North Mini Code) and Free Nemotron through the Codex ACP adapter. Credentials stay in a private local file or environment; existing workspace network and approval settings are preserved. Empty workspace configuration defaults to network-enabled workspace mode, consistent with Dweebo's Codex agent.
- Caption generation stays ahead of playback, fills subtitle gaps and keeps captions visible during idle playback. Adds subtitle font selection and OpenDyslexic integration.
- TV details prefer regular seasons. Playback menu reconnection and next-episode timing, placement and preload lead are improved; hidden overlays no longer blur the desktop.
- New Dweebo chats default to Light. Greetd password login unlocks the login keyring.
- GPU caption runtime setup remains local to the machine rather than being shipped as a hardware-specific default.

## Local system comparison

Compared every shipped home file with its installed counterpart and inventoried additional files in the shell, assistant and media source directories. Most application sources already match the repository after home-path substitution. Differences retained locally include generated palettes, wallpaper/weather choices, appearance/performance preferences, personal shortcuts, monitor configuration, editor lockfile state and caption GPU setup. Older installed package wrappers, Fish update function and panel service were not used to overwrite newer repository versions. Retired fan-control state was not reintroduced. Unfinished assistant retry-button changes remain outside this release. No accounts, credentials, histories, downloaded models or unrelated home files were copied.

## Installation

```bash
bash install.sh --release v1.5.0 --dry-run
bash install.sh --release v1.5.0
```

Existing installations can use `./update.sh --release v1.5.0 --dry-run`, then repeat without `--dry-run`. Add `--files-only` to skip package upgrades.

## OpenRouter setup and limits

Save an OpenRouter API key in `~/.config/dweebo/openrouter-api-key` with permissions `600`, or provide `OPENROUTER_API_KEY` in the backend environment, then select either agent in a new chat. Node/npm and Codex ACP are the same prerequisites as the existing Codex agent. Free endpoint availability and limits may change. The public model catalog confirmed both configured IDs with tool support and zero token pricing on 2026-11-02. No OpenRouter credential was available for an authenticated model/tool round trip; these endpoints remain unverified with live inference. Provider protocol follows the [OpenRouter Responses API](https://openrouter.ai/docs/api_reference/responses/overview) and [Codex configuration guidance](https://learn.chatgpt.com/docs/config-file/config-advanced).

No active desktop services, assistant backends or playback sessions were restarted. Fresh hardware, boot/login and package installation require destination-system testing.

## Verification

All 91 desktop regression tests passed, including four new OpenRouter launcher tests for private-key permissions, missing credentials, invalid configuration, scoped provider selection and preservation of workspace permissions. Final payload checksum verification passed for 113 installation entries. No dependency additions were required. QML lint returned exit 255 without diagnostics in this session, so no successful QML lint or live UI validation is claimed.
