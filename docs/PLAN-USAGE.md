# Assistant plan usage

The plan usage button shows shared Codex account allowance as a percentage left
for each quota window, with reset times in its tooltip. Other Codex clients count
against the same allowance.

In the Google Gemini backend, the button opens Google AI Studio's rate limit
page. This backend uses a Google API key; its quota is separate from a Gemini
subscription. The API-key integration does not provide an exact remaining quota,
so the panel does not estimate a percentage or display Codex quota for Gemini.
Switching between these backends clears the previous provider's quota display.
