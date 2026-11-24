// Distance along a chamfered loop, starting at the platform.
function loop(width, height, slot, count) {
    const band = height * .64 / count;
    const y = height * .18 + slot * band;
    const x = width * (.15 + .045 * (slot % 3));
    const span = width * (.62 + .04 * (slot % 2));
    const h = Math.min(height * .16, band * .66);
    const bevel = Math.min(h * .48, span * .08);
    const stop = x + span * (.58 - .08 * (slot % 3));
    const vertices = [[stop,y],[x+span-bevel,y],[x+span,y+bevel],
        [x+span,y+h-bevel],[x+span-bevel,y+h],[x+bevel,y+h],
        [x,y+h-bevel],[x,y+bevel],[x+bevel,y],[stop,y]];
    const segments = [];
    let length = 0;
    for (let i = 1; i < vertices.length; ++i) {
        const a = vertices[i-1], b = vertices[i];
        const dx = b[0]-a[0], dy = b[1]-a[1], size = Math.hypot(dx,dy);
        if (size > 0) segments.push({x:a[0], y:a[1], dx:dx/size, dy:dy/size, start:length, size:size});
        length += size;
    }
    return {segments, length, stop, y, x, h};
}

function point(loop, phase) {
    const d = ((phase % 1 + 1) % 1) * loop.length;
    const s = loop.segments.find(seg => d < seg.start + seg.size) || loop.segments[0];
    return {x:s.x+s.dx*(d-s.start), y:s.y+s.dy*(d-s.start), angle:Math.atan2(s.dy,s.dx)};
}
