// Adapter bundled with the installed Lyrics Plus providers by setup_lyrics_plus.py.
// No credentials leave Spotify: the local bridge receives lyrics and track URI only.
const CONFIG = {visual: {"musixmatch-translation-language": "none"},
    providers: {musixmatch: {token: ""}}};
let lastPayload = null;
let generation = 0;
async function publish() {
    if (!lastPayload) return;
    try {
        await fetch('http://127.0.0.1:19837/lyrics', {method: 'POST', credentials: 'omit',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify(lastPayload)});
    } catch (_) { /* A restarted shell will receive the next heartbeat. */ }
}
function payload(info, result) {
    const timed = result.synced?.length ? result.synced : null;
    const lines = timed || result.unsynced;
    if (!lines?.some(line => line.text?.trim())) return null;
    return {uri: info.uri, provider: result.provider, synced: !!timed,
        lines: lines.map(line => timed
            ? {time: Number(line.startTime) / 1000, text: line.text || ''}
            : {text: line.text || ''})};
}
async function refresh() {
    const owned = ++generation;
    const item = Spicetify.Player.data?.item;
    if (!/^spotify:track:[A-Za-z0-9]{22}$/.test(item?.uri || '')) return;
    const meta = item.metadata || {};
    const info = {uri: item.uri, title: meta.title || item.name,
        artist: meta.artist_name || item.artists?.[0]?.name || '',
        album: meta.album_title || item.album?.name || '', duration: Number(meta.duration || item.duration?.milliseconds || 0)};
    lastPayload = {uri: info.uri, provider: 'Spotify', synced: false, lines: []};
    await publish();
    CONFIG.providers.musixmatch.token = localStorage.getItem('lyrics-plus:provider:musixmatch:token') || '';
    // Use Lyrics Plus's own implementations, with Spotify first as requested.
    for (const provider of ['spotify', 'lrclib', 'musixmatch', 'netease']) {
        if (provider === 'musixmatch' && !CONFIG.providers.musixmatch.token) continue;
        try {
            const result = await Providers[provider](info);
            if (owned !== generation) return;
            const value = payload(info, result);
            if (value) { lastPayload = value; await publish(); return; }
        } catch (_) { /* Try the next Lyrics Plus provider. */ }
    }
}
(function start() {
    if (!globalThis.Spicetify?.Player?.addEventListener || !Spicetify.CosmosAsync) {
        setTimeout(start, 1000); return;
    }
    Spicetify.Player.addEventListener('songchange', refresh);
    refresh();
    setInterval(publish, 5000);
})();
