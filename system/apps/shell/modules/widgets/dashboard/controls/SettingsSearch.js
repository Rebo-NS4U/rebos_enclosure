// Shared by QML and the search regression tests; no desktop state required.
function normalize(value) {
    return String(value || "").toLowerCase().replace(/[^a-z0-9\u0080-\uffff]+/g, " ").trim();
}

const synonymGroups = [
    ["wifi", "wireless", "wlan"],
    ["sound", "audio", "volume"],
    ["mic", "microphone"],
    ["screen", "display", "monitor"],
    ["font", "text", "typography"],
    ["transparent", "transparency", "opacity"],
    ["animation", "animations", "motion"],
    ["shortcut", "shortcuts", "hotkey", "hotkeys", "keybind", "keybinding"],
    ["colour", "color", "colors", "colours"],
    ["ai", "assistant"],
    ["disable", "off"],
    ["enable", "on"]
];

// Allow one inserted, deleted, replaced or transposed character in longer words.
function nearby(a, b) {
    if (a.length < 4 || b.length < 4 || Math.abs(a.length - b.length) > 1) return false;
    let i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    if (a.length === b.length) {
        return a.slice(i + 1) === b.slice(i + 1)
            || (a[i] === b[i + 1] && a[i + 1] === b[i]
                && a.slice(i + 2) === b.slice(i + 2));
    }
    return a.length > b.length ? a.slice(i + 1) === b.slice(i) : a.slice(i) === b.slice(i + 1);
}

function wordScore(term, words) {
    let best = 0;
    const group = synonymGroups.find(values => values.includes(term)) || [];
    for (const word of words) {
        if (word === term) best = Math.max(best, 100);
        else if (word.startsWith(term)) best = Math.max(best, 75);
        else if (group.includes(word)) best = Math.max(best, 65);
        else if (nearby(term, word)) best = Math.max(best, 40);
    }
    return best;
}

function search(query, items) {
    const phrase = normalize(query).replace(/\bwi fi\b/g, "wifi");
    const ignored = ["how", "do", "i", "my", "the", "a", "an", "to", "please", "change", "set", "settings", "turn"];
    const terms = phrase.split(/\s+/).filter(word => word && !ignored.includes(word));
    if (!terms.length) return [];
    const results = [];
    for (const item of items) {
        const label = normalize(item.label);
        const labelWords = label.split(/\s+/);
        const contextWords = normalize(item.subLabel).split(/\s+/);
        const keywords = normalize(item.keywords).split(/\s+/);
        let score = 0;
        let matches = true;
        for (const term of terms) {
            const match = Math.max(wordScore(term, labelWords) * 3,
                wordScore(term, contextWords) * 2, wordScore(term, keywords));
            if (!match) { matches = false; break; }
            score += match;
        }
        if (!matches) continue;
        if (label === phrase) score += 2000;
        else if (label.includes(phrase)) score += 800;
        results.push(Object.assign({}, item, {score: score}));
    }
    return results.sort((a, b) => b.score - a.score || a.label.localeCompare(b.label));
}
