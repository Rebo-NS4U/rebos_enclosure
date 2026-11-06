.pragma library

function characters(text) { return text.match(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\s\S]/g) || []; }

// Books use typographic quotes and dashes absent from ordinary keyboard keys.
// Compare equivalent quote styles without altering source text or saved offsets.
function matchingCharacter(input, target) {
    function canonical(value) {
        return value.replace(/[\u2018\u2019\u201a\u201b]/g, "'")
                    .replace(/[\u201c\u201d\u201e\u201f]/g, '\"')
                    .replace(/[\u2010-\u2015]/g, '-');
    }
    return canonical(input) === canonical(target);
}

// Match the renderer's word rows and measured character widths. Never discard
// whitespace or split surrogate pairs.
function layout(source, width, measure) {
    width = Math.max(1, width);
    var words = [], used = 0, line = 1, rowWidth = 0;
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
                if (line >= 2)
                    return {text: source.slice(0, used), words: words, lines: line};
                line++; rowWidth = 0;
            }
            words.push({text: chunk, start: used});
            used += chunk.length; rowWidth += chunkWidth;
        }
    }
    return {text: source.slice(0, used), words: words, lines: line};
}
