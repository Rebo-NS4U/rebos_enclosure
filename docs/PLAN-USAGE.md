# Assistant plan usage

The plan usage button shows shared Codex account allowance as a percentage left
for each quota window, with reset times in its tooltip. Other Codex clients count
against the same allowance.

In the Google Gemini backend, the same display shows `Gemini: Ready`,
`Gemini: Rate limited`, or `Gemini: Quota exhausted` from the session's latest
provider responses. Ready means no limit has been reported; it does not guarantee
remaining allowance. A successful completed response clears a reported limit.
When the provider supplies a retry delay, the display counts down in seconds.
After the delay elapses the limit status remains until a successful response.

Opening the menu and automatic refreshes never open a browser or clear a reported
limit. Clicking the indicator reports the current status in chat. This API-key
backend has separate quota from a Gemini subscription; no remaining percentage
is inferred. Codex continues to show its account's percentage left.
