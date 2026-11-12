// Shared by the lyrics service and its parser regression tests.
function parseLrc(text) {
    const lines = [];
    const offset = /\[offset:([+-]?\d+)\]/i.exec(text);
    const shift = offset ? Number(offset[1]) / 1000 : 0;
    for (const raw of text.split(/\r?\n/)) {
        const lyric = raw.replace(/\[[^\]]*\]/g, "").trim();
        const stamps = raw.match(/\[\d+:\d+(?:\.\d+)?\]/g) || [];
        for (const stamp of stamps) {
            const parts = stamp.slice(1, -1).split(":");
            lines.push({time: Number(parts[0]) * 60 + Number(parts[1]) + shift, text: lyric});
        }
    }
    return lines.sort((a, b) => a.time - b.time);
}

function activeLine(lines, position) {
    let index = -1;
    for (let i = 0; i < lines.length && lines[i].time <= position; ++i) index = i;
    return index;
}

// Text alone cannot reveal vocal timing. Distribute the song duration by word
// count as an explicitly approximate fallback; never replace genuine cues.
function estimateLines(text, duration) {
    if (!Number.isFinite(duration) || duration <= 0) return [];
    const rows = text.split(/\r?\n/).map(line => line.trim()).filter(line => line.length > 0);
    const weights = rows.map(line => Math.max(1, line.split(/\s+/).length));
    const total = weights.reduce((sum, weight) => sum + weight, 0);
    let elapsed = 0;
    return rows.map((text, index) => {
        const time = duration * elapsed / total;
        elapsed += weights[index];
        return {time, text};
    });
}

function playerLyrics(metadata) {
    for (const key of ["xesam:asText", "xesam:lyrics", "lyrics", "spotify:lyrics"]) {
        const value = metadata?.[key];
        if (typeof value === "string" && value.trim()) return value;
    }
    return "";
}

function normalizedName(value) {
    return String(value || "").toLowerCase().replace(/[\s.,!?"'’“”:;()[\]_-]+/g, "");
}

function primaryArtist(artists) {
    return String(artists || "").split(/,|;| & | feat\.? | ft\.? /i)[0].trim();
}

// Search is broader than /get: never accept an unrelated song or recording.
function bestMatch(records, title, artists, album, duration) {
    if (!Array.isArray(records)) return null;
    const artist = normalizedName(primaryArtist(artists));
    let best = null;
    let bestScore = -Infinity;
    for (const record of records) {
        if (!record || normalizedName(record.trackName) !== normalizedName(title)
            || normalizedName(primaryArtist(record.artistName)) !== artist) continue;
        const difference = Math.abs(Number(record.duration) - duration);
        if (duration > 0 && (!isFinite(difference) || difference > 5)) continue;
        const synced = typeof record.syncedLyrics === "string" && record.syncedLyrics.trim();
        const plain = typeof record.plainLyrics === "string" && record.plainLyrics.trim();
        if (!synced && !plain && !record.instrumental) continue;
        const score = (synced ? 5 : plain ? 1 : 0) - (duration > 0 ? difference * 2 : 0)
            + (album && normalizedName(record.albumName) === normalizedName(album) ? 0.5 : 0);
        if (score > bestScore) { best = record; bestScore = score; }
    }
    return best;
}
