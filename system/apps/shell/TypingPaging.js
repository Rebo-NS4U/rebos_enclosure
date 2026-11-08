.pragma library

function characters(text) { return text.match(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\s\S]/g) || []; }

// Books use typographic quotes and dashes absent from ordinary keyboard keys.
// Compare equivalent quote styles without altering source text or saved offsets.
function matchingCharacter(input, target) {
    if (input === target) return true;
    function canonical(value) {
        return value.replace(/[\u2018\u2019\u201a\u201b]/g, "'")
                    .replace(/[\u201c\u201d\u201e\u201f]/g, '\"')
                    .replace(/[\u2010-\u2015]/g, '-');
    }
    return canonical(input) === canonical(target);
}

// Compose three keyboard periods only where the book expects one ellipsis.
function prepareInput(input, target) {
    // Most edits cannot compose an ellipsis. Avoid allocating and walking two
    // character arrays for every key and every cursor/display recomputation.
    if (target.indexOf("\u2026") < 0 || input.indexOf(".") < 0)
        return {text: input, pending: false};
    var source = characters(input), expected = characters(target), result = "";
    for (var i = 0, j = 0; i < source.length; j++) {
        if (expected[j] === "\u2026" && source[i] === ".") {
            var dots = source.slice(i, i + 3).join("");
            if (dots === "...") { result += "\u2026"; i += 3; continue; }
            if (/^\.{1,2}$/.test(source.slice(i).join("")))
                return {text: result + source.slice(i).join(""), pending: true};
        }
        result += source[i++];
    }
    return {text: result, pending: false};
}

// Incomplete keyboard ellipses must not consume following book characters.
function displayInput(input, target) {
    var prepared = prepareInput(input, target);
    return prepared.pending ? prepared.text.replace(/\.+$/, "") : prepared.text;
}

// Match the renderer's word rows and measured character widths. Never discard
// whitespace or split surrogate pairs.
function layout(source, width, measure, maxLines) {
    maxLines = Math.max(1, maxLines || 2);
    width = Math.max(1, width);
    var words = [], lineWidths = [], used = 0, line = 1, rowWidth = 0;
    var tokens = source.match(/\S+\s*|\s+/g) || [];
    for (var tokenIndex = 0; tokenIndex < tokens.length; tokenIndex++) {
        var letters = characters(tokens[tokenIndex]);
        var offset = 0;
        while (offset < letters.length) {
            var chunk = "", chunkWidth = 0, chunkCount = 0;
            while (offset < letters.length && chunkCount < 36) {
                var nextWidth = measure(letters[offset]);
                if (chunkCount && chunkWidth + nextWidth > width) break;
                chunk += letters[offset++]; chunkWidth += nextWidth; chunkCount++;
            }
            if (rowWidth && rowWidth + chunkWidth > width) {
                if (line >= maxLines)
                    return {text: source.slice(0, used), words: words, lines: line, lineWidths: lineWidths};
                line++; rowWidth = 0;
            }
            words.push({text: chunk, start: used, line: line - 1});
            used += chunk.length; rowWidth += chunkWidth;
            lineWidths[line - 1] = rowWidth;
        }
    }
    return {text: source.slice(0, used), words: words, lines: line, lineWidths: lineWidths};
}

// Roll before the loaded window ends, retaining enough rows for the viewport.
// Offsets are UTF-16 indices, matching layout words and QML's text cursor.
function slideOffset(page, cursor, keepLines) {
    var line = 0;
    for (var i = 0; i < page.words.length; i++) {
        if (page.words[i].start > cursor) break;
        line = page.words[i].line;
    }
    if (line < keepLines * 2 || page.lines - line > keepLines + 1) return 0;
    for (var j = 0; j < page.words.length; j++)
        if (page.words[j].line >= line - keepLines) return page.words[j].start;
    return 0;
}

// Keep one document separator per source space so word cursor offsets agree.
function readerHtml(value, starts, lineHeight, indent) {
    lineHeight = lineHeight || 31;
    indent = indent || 40;
    var paragraphs = [], start = 0;
    for (var i = 0; i < starts.length; i++) {
        var offset = starts[i];
        if (offset <= start || offset >= value.length) continue;
        paragraphs.push(value.slice(start, offset).replace(/ $/, ""));
        start = offset;
    }
    paragraphs.push(value.slice(start));
    return paragraphs.map(function (paragraph) {
        var escaped = paragraph.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        return '<p align="left" style="line-height:155%; margin-top:0px; margin-bottom:' + lineHeight + 'px; text-indent:' + indent + 'px;">' + escaped + '</p>';
    }).join("");
}

// Use only a small excerpt from the current page, never later loaded windows.
// Prefer the selected occurrence; typed dictionary searches use the nearest one.
function wordContext(source, term, cursor) {
    if (!term || term.length > 128) return "";
    var lower = source.toLowerCase(), needle = term.toLowerCase();
    var nearest = -1, distance = Infinity;
    function wordCharacter(value) {
        return value && (/[0-9_]/.test(value) || value.toUpperCase() !== value.toLowerCase());
    }
    for (var at = lower.indexOf(needle); at >= 0; at = lower.indexOf(needle, at + 1)) {
        if ((at > 0 && wordCharacter(source[at - 1]))
                || (at + term.length < source.length && wordCharacter(source[at + term.length]))) continue;
        var delta = Math.abs(at - Math.max(0, cursor));
        if (delta < distance) { nearest = at; distance = delta; }
    }
    if (nearest < 0) return "";
    var start = Math.max(0, nearest - 240), end = Math.min(source.length, nearest + term.length + 160);
    if (start > 0) { var space = source.indexOf(" ", start); if (space < nearest) start = space + 1; }
    if (end < source.length) { var boundary = source.lastIndexOf(" ", end); if (boundary > nearest + term.length) end = boundary; }
    return source.slice(start, end).trim();
}
