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

async function playlistItems(api, uri) {
    const items = [];
    while (true) {
        const page = await api.getContents(uri, {offset: items.length, limit: 100});
        if (!Array.isArray(page.items)) throw Error('Missing playlist contents');
        items.push(...page.items);
        if (page.items.length < 100 || items.length >= page.totalLength) return items;
        if (items.length >= 10000) throw Error('Playlist exceeds 10,000 tracks');
    }
}

async function syncPlaylist(api, uri, tracks) {
    if (!api?.add || !api?.remove || !api?.resync) throw Error('Spotify playlist editing is unavailable');
    await api.resync(uri);
    const items = await playlistItems(api, uri);
    const removals = [];
    const insertions = [];
    let offset = 0;
    // Keep existing rows that already appear in the requested relative order.
    for (const {uri: itemUri, uid} of items) {
        const next = tracks.indexOf(itemUri, offset);
        if (next === -1) {
            removals.push({uri: itemUri, uid});
        } else {
            if (next > offset) insertions.push({tracks: tracks.slice(offset, next), location: {before: {uid}}});
            offset = next + 1;
        }
    }
    if (offset < tracks.length) insertions.push({tracks: tracks.slice(offset), location: {after: 'end'}});
    if (removals.some(item => !item.uid) || insertions.some(batch => batch.location.before && !batch.location.before.uid))
        throw Error('Spotify did not return the playlist row IDs needed to edit it');
    for (let i = 0; i < removals.length; i += 100)
        await api.remove(uri, removals.slice(i, i + 100));
    for (const batch of insertions) {
        for (let i = 0; i < batch.tracks.length; i += 100)
            await api.add(uri, batch.tracks.slice(i, i + 100), batch.location);
    }
    await api.resync(uri);
    const saved = await playlistItems(api, uri);
    if (saved.length !== tracks.length || saved.some((item, i) => item.uri !== tracks[i]))
        throw Error('Spotify did not confirm the requested playlist contents');
}

// Daily Mix metadata only. Learn playlist links from Spotify's visible Daily Mix cards.
(function dailyMixes() {
    let collecting = false;
    let suggesting = false;
    let writing = false;
    const written = new Map();
    let lastCollection = 0;
    let cached = null;
    const learned = new Map();
    async function publishMixes() {
        if (!cached) return;
        try { await fetch('http://127.0.0.1:19838/mixes', {method: 'POST', credentials: 'omit',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify(cached)}); } catch (_) {}
    }
    async function collect(force = false, refreshId = "", playlistUri = "") {
        if (collecting || !globalThis.Spicetify?.Platform?.PlaylistAPI) return;
        collecting = true;
        try {
            const previousSize = learned.size;
            document.querySelectorAll('a[href*="/playlist/"]').forEach(a => {
                const card = a.closest('[data-testid="card"]') || a.parentElement;
                const name = (a.textContent + ' ' + (a.getAttribute('aria-label') || '') + ' ' + (card?.textContent || '')).match(/Daily Mix [1-6]\b/);
                const id = a.getAttribute('href').match(/\/playlist\/([A-Za-z0-9]{22})(?:[/?#]|$)/);
                if (name && id) learned.set('spotify:playlist:' + id[1], name[0]);
            });
            if (!force && learned.size === previousSize && Date.now() - lastCollection < 60 * 60 * 1000) return;
            lastCollection = Date.now();
            const mixes = [];
            let failure = '';
            const requested = /^spotify:playlist:[A-Za-z0-9]{22}$/.test(playlistUri);
            const targets = requested ? [[playlistUri, 'Playlist ' + playlistUri.split(':').pop()]] : [...learned];
            for (const [uri, name] of targets) {
                try {
                    const items = await playlistItems(Spicetify.Platform.PlaylistAPI, uri);
                    const tracks = items.map(row => row.track || row).filter(t => t && /^spotify:track:[A-Za-z0-9]{22}$/.test(t.uri || '')).map(t => ({uri: t.uri,
                        title: t.name || '', artist: (t.artists || []).map(a => a.name).join(', ')}));
                    if (!tracks.length) throw Error('No playable Spotify tracks in this playlist');
                    let title = name;
                    if (requested && typeof Spicetify.Platform.PlaylistAPI.getMetadata === 'function') {
                        try {
                            const metadata = await Spicetify.Platform.PlaylistAPI.getMetadata(uri);
                            if (metadata?.name?.trim()) title = metadata.name.trim().slice(0, 200);
                        } catch (_) { /* Tracks remain usable without a display name. */ }
                    }
                    mixes.push({uri, name: title, tracks});
                } catch (error) { failure = 'Could not load playlist. Check Spotify access and try again. ' + String(error.message || '').slice(0, 150); console.warn('Enclosure playlist refresh failed', name, error); }
            }
            if (mixes.length && !requested) { cached = {mixes}; await publishMixes(); }
            if (refreshId) {
                await fetch('http://127.0.0.1:19838/mixes', {method: 'POST', credentials: 'omit',
                    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({mixes, refresh_id: refreshId, error: requested ? failure : ""})});
            }
        } finally { collecting = false; }
    }
    collect();
    setInterval(collect, 60000);
    // Navigating to Made for You teaches the collector all visible mix links.
    let timer;
    new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(() => {
        collect();
    }, 2000); }).observe(document.documentElement, {childList: true, subtree: true});
    setInterval(publishMixes, 15000);
    let lastPreview;
    async function pollPreview() {
        try {
            if (!Spicetify.Player?.origin?.play) return;
            const response = await fetch('http://127.0.0.1:19838/mixes', {credentials: 'omit', cache: 'no-store'});
            if (!response.ok) return;
            const {preview} = await response.json();
            if (!preview) return;
            if (lastPreview?.preview_id !== preview.id) {
                let error = '';
                try {
                    if (!/^spotify:track:[A-Za-z0-9]{22}$/.test(preview.uri)) throw Error('Invalid Spotify track');
                    await Spicetify.Player.playUri(preview.uri);
                } catch (e) {
                    error = 'Spotify could not play this suggestion. ' + String(e.message || e).slice(0, 180);
                }
                lastPreview = {preview_id: preview.id, error};
            }
            await fetch('http://127.0.0.1:19838/mixes', {method: 'POST', credentials: 'omit',
                headers: {'Content-Type': 'application/json'}, body: JSON.stringify(lastPreview)});
        } catch (_) { /* Music may be closed. Retry an unacknowledged result. */ }
        finally {
            // Schedule from the completed network request to avoid a chained
            // interval being throttled while Spotify is in the tray.
            setTimeout(pollPreview, 500);
        }
    }
    pollPreview();
    // Music's explicit update button bypasses the hourly schedule.
    setInterval(async () => {
        if (collecting) return;
        try {
            const response = await fetch('http://127.0.0.1:19838/mixes', {credentials: 'omit', cache: 'no-store'});
            if (!response.ok) return;
            const command = await response.json();
            if (command.playlist_write && !writing) {
                const job = command.playlist_write;
                writing = true;
                try {
                    if (!written.has(job.id)) {
                        let error = '';
                        try {
                            if (!/^spotify:playlist:[A-Za-z0-9]{22}$/.test(job.uri) ||
                                !Array.isArray(job.tracks) || job.tracks.length > 10000 ||
                                job.tracks.some(uri => !/^spotify:track:[A-Za-z0-9]{22}$/.test(uri)))
                                throw Error('Invalid playlist update');
                            await syncPlaylist(Spicetify.Platform.PlaylistAPI, job.uri, job.tracks);
                        } catch (e) {
                            error = 'Spotify update failed or may be partial. Check playlist edit permission and its contents before retrying. ' + String(e.message || e).slice(0, 180);
                        }
                        written.set(job.id, error);
                    }
                    await fetch('http://127.0.0.1:19838/mixes', {method:'POST', credentials:'omit',
                        headers:{'Content-Type':'application/json'}, body:JSON.stringify({playlist_write_id:job.id, error:written.get(job.id)})});
                } finally { writing = false; }
            }
            if (command.suggestion && !suggesting) {
                suggesting = true;
                const job = command.suggestion;
                try {
                    let tracks = [], error = '';
                    try {
                        const api = Spicetify.Platform.PlaylistAPI;
                        if (typeof api.getRecommendedTracks !== 'function') throw Error('Update the Spotify integration to load recommendations.');
                        const rows = await api.getRecommendedTracks(job.uri, job.skip || [], 100);
                        tracks = rows.map(row => row.track || row)
                            .filter(t => /^spotify:track:[A-Za-z0-9]{22}$/.test(t.uri || ''))
                            .map(t => ({uri: t.uri, title: t.name || '',
                                artist: (t.artists || []).map(a => a.name).join(', '),
                                art: t.album?.imageUrl || ''}));
                    } catch (e) { error = 'Could not load Spotify suggestions. ' + String(e.message || e).slice(0, 180); }
                    await fetch('http://127.0.0.1:19838/mixes', {method:'POST', credentials:'omit', headers:{'Content-Type':'application/json'}, body:JSON.stringify({suggestion_id:job.id, tracks, error})});
                } finally { suggesting = false; }
            }
            if (command.refresh_id) await collect(true, command.refresh_id, command.playlist_uri);
        } catch (_) { /* Music may be closed. */ }
    }, 5000);
})();
