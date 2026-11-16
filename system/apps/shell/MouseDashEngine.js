// Pure game mechanics; coordinates and speeds are logical pixels.
function playerRadius(elapsed) { return Math.min(18, 9 + elapsed * 0.12); }
function roundDuration(mode) { return mode === "gauntlet" ? 60 : 0; }
function roundComplete(mode, elapsed) { return roundDuration(mode) > 0 && elapsed >= roundDuration(mode); }
function pressure(mode, elapsed) {
    return mode === "gauntlet" ? 1 + Math.min(5, Math.floor(elapsed / 10)) * 0.22 : 1;
}
function spawnInterval(difficulty, elapsed, mode) {
    return Math.max(0.09, (0.64 - difficulty * 0.14) / (1 + elapsed * 0.045) / pressure(mode, elapsed));
}
function spawn(w, h, px, py, difficulty, elapsed, mode) {
    const edge = Math.floor(Math.random() * 4), r = 9 + Math.random() * 16;
    let x = Math.random() * w, y = Math.random() * h;
    if (edge === 0) x = -r - 20;
    if (edge === 1) x = w + r + 20;
    if (edge === 2) y = -r - 20;
    if (edge === 3) y = h + r + 20;
    const angle = Math.atan2(py * h - y, px * w - x) + (Math.random() - 0.5) * 0.8;
    const speed = (145 + difficulty * 70 + Math.min(360, elapsed * 5)) * Math.sqrt(pressure(mode, elapsed));
    return {x:x, y:y, r:r, vx:Math.cos(angle)*speed, vy:Math.sin(angle)*speed};
}
// First contact along a segment, including fast crossings with clear endpoints.
function contact(enemies, x, y, nx, ny, radius = 9) {
    const dx = nx - x, dy = ny - y, a = dx * dx + dy * dy;
    let first = null;
    for (const e of enemies) {
        const ox = x - e.x, oy = y - e.y, rr = radius + e.r;
        const c = ox * ox + oy * oy - rr * rr;
        let t = 0;
        if (c > 0) {
            if (!a) continue;
            const b = 2 * (ox * dx + oy * dy), discriminant = b * b - 4 * a * c;
            if (discriminant < 0) continue;
            t = (-b - Math.sqrt(discriminant)) / (2 * a);
            if (t < 0 || t > 1) continue;
        }
        if (!first || t < first.t)
            first = {t:t, x:x + dx * t, y:y + dy * t, fromX:x, fromY:y,
                     enemy:{x:e.x, y:e.y, r:e.r}, cause:"cursor"};
    }
    return first;
}
function sweptHit(enemies, x, y, nx, ny, radius = 9) {
    return contact(enemies, x, y, nx, ny, radius) !== null;
}
function step(enemies, dt, px, py, w, h, radius = 9) {
    let collision = null;
    for (const e of enemies) {
        const hit = contact([{x:px, y:py, r:radius}], e.x, e.y, e.x + e.vx * dt, e.y + e.vy * dt, e.r);
        if (hit && (!collision || hit.t < collision.t))
            collision = {t:hit.t, x:px, y:py, fromX:px, fromY:py,
                         enemy:{x:hit.x, y:hit.y, r:e.r}, cause:"enemy",
                         enemyFromX:e.x, enemyFromY:e.y};
    }
    // Freeze the entire field at first contact, rather than past the collision.
    const advance = dt * (collision ? collision.t : 1), live = [];
    for (const e of enemies) {
        e.x += e.vx * advance; e.y += e.vy * advance;
        if (e.x > -100 && e.x < w+100 && e.y > -100 && e.y < h+100) live.push(e);
    }
    return {enemies:live, hit:collision !== null, collision:collision};
}
