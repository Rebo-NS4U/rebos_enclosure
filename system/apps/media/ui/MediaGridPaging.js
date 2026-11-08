.pragma library

function needsMore(count, width, height, cellWidth, cellHeight, scroll, contentHeight, ahead) {
    if (width <= 0 || height <= 0 || cellWidth <= 0 || cellHeight <= 0) return false;
    var columns = Math.max(1, Math.round(width / cellWidth));
    var offset = Math.max(0, scroll);
    // Include a complete row below the viewport so its bottom never looks empty.
    var target = Math.ceil((offset + height) / cellHeight) * columns + columns;
    return count < target || (offset > 0 && offset + height + ahead >= contentHeight);
}
