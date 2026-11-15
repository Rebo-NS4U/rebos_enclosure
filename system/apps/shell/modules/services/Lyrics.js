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

// For Music and the desktop strip. Keep estimates out of exported/player lyrics.
function splitPlainLine(line) {
    // Some plain-text providers join verses with a single space. Prefer a new
    // capitalized phrase, then an explicit clause boundary on very long rows.
    // Require substantial text on both sides; never split on the pronoun "I".
    if (line.length < 60 || line.split(/\s+/).length < 12) return [line];
    const pattern = /\s+(?=[A-Z][a-z]+\b|I['’](?:m|ll|ve|d)\b|(?:until|but|because|while)\b)/g;
    let match, best = -1, score = Infinity;
    while ((match = pattern.exec(line)) !== null) {
        const left = line.slice(0, match.index).trim();
        const right = line.slice(match.index).trim();
        if (left.split(/\s+/).length < 4 || right.split(/\s+/).length < 4) continue;
        const distance = Math.abs(left.length - right.length);
        if (distance < score) { best = match.index; score = distance; }
    }
    if (best < 0) return [line];
    return splitPlainLine(line.slice(0, best).trim())
        .concat(splitPlainLine(line.slice(best).trim()));
}

function estimatedLines(text, duration) {
    if (!isFinite(duration) || duration <= 0) return [];
    const rows = String(text || "").split(/\r?\n/)
        .map(line => line.trim()).filter(line => line && !/^\[[^\]]*\]$/.test(line))
        .reduce((result, line) => result.concat(splitPlainLine(line)), []);
    return rows.map((line, index) => ({time: index * duration / rows.length, text: line}));
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

// Visual estimates within a line, not phoneme timestamps. Vowels linger,
// consonants snap, and whitespace/punctuation give the marker a short rest.
function letterCues(text) {
    const cues = [];
    let total = 0, index = 0;
    for (const letter of text) {
        const vowel = /[aeiouyà-åè-ïò-öù-ü]/i.test(letter);
        const rest = /[\s.,!?;:…'’"-]/.test(letter);
        const sharp = /[bcdgkptqx]/i.test(letter);
        const weight = rest ? 0.45 : vowel ? 1.65 : sharp ? 0.7 : 1;
        cues.push({index: index, length: letter.length, start: total,
            end: total + weight, strength: rest ? 0 : sharp ? 1 : vowel ? 0.8 : 0.6});
        total += weight;
        index += letter.length;
    }
    return {cues: cues, duration: total};
}

function letterMotion(timing, progress) {
    if (!timing.cues.length) return {index: 0, length: 0, phase: 0, bounce: 0, strength: 0};
    const at = Math.max(0, Math.min(1, isFinite(progress) ? progress : 0)) * timing.duration;
    const cue = timing.cues.find(cue => at < cue.end) || timing.cues[timing.cues.length - 1];
    const phase = Math.max(0, Math.min(1, (at - cue.start) / (cue.end - cue.start)));
    return {index: cue.index, length: cue.length, phase: phase,
        bounce: Math.pow(Math.max(0, Math.sin(phase * Math.PI)), 0.65) * cue.strength,
        strength: cue.strength};
}
