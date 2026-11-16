// Pure game mechanics; coordinates and speeds are logical pixels.
function playerRadius(elapsed) { return Math.min(18, 9 + elapsed * 0.12); }
function roundDuration(mode) { return mode === "blitz" ? 45 : mode === "gauntlet" ? 60 : 0; }
function roundComplete(mode, elapsed) { return roundDuration(mode) > 0 && elapsed >= roundDuration(mode); }
function pressure(mode, elapsed) {
    return mode === "blitz" ? 1.45 : mode === "gauntlet" ? 1 + Math.min(5, Math.floor(elapsed / 10)) * 0.22 : 1;
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
function sweptHit(enemies, x, y, nx, ny, radius = 9) {
    const dx = nx-x, dy = ny-y, length = dx*dx+dy*dy;
    return enemies.some(e => {
        const t = length ? Math.max(0, Math.min(1, ((e.x-x)*dx+(e.y-y)*dy)/length)) : 0;
        return Math.hypot(e.x-x-t*dx, e.y-y-t*dy) <= e.r+radius;
    });
}
function step(enemies, dt, px, py, w, h, radius = 9) {
    let hit = false;
    const live = [];
    for (const e of enemies) {
        const nx = e.x+e.vx*dt, ny = e.y+e.vy*dt;
        if (sweptHit([{x:px,y:py,r:e.r}], e.x,e.y,nx,ny,radius)) hit = true;
        e.x=nx; e.y=ny;
        if (e.x > -100 && e.x < w+100 && e.y > -100 && e.y < h+100) live.push(e);
    }
    return {enemies:live, hit:hit};
}
