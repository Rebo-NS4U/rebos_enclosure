// Distance along a chamfered loop, starting at the platform.
function loop(width, height, slot, count) {
    const band = height * .65 / count;
    const h = Math.min(height * .29, band * .65);
    const y = height * .5 + (slot - (count-1)/2)*band - h*.42;
    const x = width * (.12 + .045 * (slot % 3));
    const span = width * (.74 - .035 * (slot % 3));
    const bevel = Math.min(h*.32, span*.08);
    const stop = x + span * (.64 - .06 * (slot % 3));
    // Two offset straights and a dogleg form the mainline through the valley.
    const vertices = [[stop,y],[x+span-bevel,y],[x+span,y+bevel],
        [x+span,y+h*.63],[x+span-bevel,y+h*.63+bevel],
        [x+span*.55,y+h*.63+bevel],[x+span*.55-h*.18,y+h*.45+bevel],
        [x+bevel,y+h*.45+bevel],[x,y+h*.45],[x,y+h*.12],
        [x+bevel,y+h*.12-bevel],[x+span*.32,y+h*.12-bevel],
        [x+span*.32+bevel-h*.12,y],[stop,y]];
    const segments = [];
    let length = 0;
    for (let i = 1; i < vertices.length; ++i) {
        const a = vertices[i-1], b = vertices[i];
        const dx = b[0]-a[0], dy = b[1]-a[1], size = Math.hypot(dx,dy);
        if (size > 0) segments.push({x:a[0], y:a[1], dx:dx/size, dy:dy/size, start:length, size:size});
        length += size;
    }
    return {segments, length, stop, y, x, h, sidingY:y+h*.45+bevel};
}

function point(loop, phase) {
    const d = ((phase % 1 + 1) % 1) * loop.length;
    const s = loop.segments.find(seg => d < seg.start + seg.size) || loop.segments[0];
    return {x:s.x+s.dx*(d-s.start), y:s.y+s.dy*(d-s.start), angle:Math.atan2(s.dy,s.dx)};
}
