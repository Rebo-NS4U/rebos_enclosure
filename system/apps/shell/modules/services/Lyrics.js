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

function playerLyrics(metadata) {
    for (const key of ["xesam:asText", "xesam:lyrics", "lyrics", "spotify:lyrics"]) {
        const value = metadata?.[key];
        if (typeof value === "string" && value.trim()) return value;
    }
    return "";
}
