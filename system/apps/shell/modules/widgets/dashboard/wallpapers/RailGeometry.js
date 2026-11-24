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
    return measure(vertices, x, y+h*.45+bevel);
}

function measure(vertices, x, sidingY) {
    const segments = [];
    let length = 0;
    for (let i = 1; i < vertices.length; ++i) {
        const a = vertices[i-1], b = vertices[i];
        const dx = b[0]-a[0], dy = b[1]-a[1], size = Math.hypot(dx,dy);
        if (size > 0) segments.push({x:a[0], y:a[1], dx:dx/size, dy:dy/size, start:length, size:size});
        length += size;
    }
    return {vertices, segments, length, stop:vertices[0][0], y:vertices[0][1], x, sidingY};
}

function point(loop, phase) {
    const d = ((phase % 1 + 1) % 1) * loop.length;
    const s = loop.segments.find(seg => d < seg.start + seg.size) || loop.segments[0];
    return {x:s.x+s.dx*(d-s.start), y:s.y+s.dy*(d-s.start), angle:Math.atan2(s.dy,s.dx)};
}

// Every loop has the same ordered landmarks, so trains and sidings follow the
// same deforming rails while adjacent workspaces make room.
function blend(a,b,t) {
    const mix=(u,v)=>u+(v-u)*t;
    const vertices=a.vertices.map((v,i)=>[mix(v[0],b.vertices[i][0]),mix(v[1],b.vertices[i][1])]);
    return measure(vertices,mix(a.x,b.x),mix(a.sidingY,b.sidingY));
}

// Trace away from the platform in both directions. The two ends meet on the far side.
function trace(c,path,progress) {
    if (progress>=1) {
        c.moveTo(path.stop,path.y);
        for (const v of path.vertices.slice(1)) c.lineTo(v[0],v[1]);
        c.closePath();
        return;
    }
    for (const reverse of [false,true]) {
        let left=path.length*.5*progress;
        let x=path.stop,y=path.y;
        c.moveTo(x,y);
        for (let i=0;i<path.segments.length && left>0;i++) {
            const seg=path.segments[reverse ? path.segments.length-1-i : i];
            const distance=Math.min(left,seg.size)*(reverse ? -1 : 1);
            x+=distance*seg.dx; y+=distance*seg.dy;
            c.lineTo(x,y);
            left-=Math.abs(distance);
        }
    }
}
