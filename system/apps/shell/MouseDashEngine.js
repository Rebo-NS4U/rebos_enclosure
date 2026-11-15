// Pure game mechanics; coordinates and speeds are logical pixels.
function spawn(w, h, px, py, difficulty, elapsed) {
    const edge = Math.floor(Math.random() * 4), r = 9 + Math.random() * 16;
    let x = Math.random() * w, y = Math.random() * h;
    if (edge === 0) x = -r - 20;
    if (edge === 1) x = w + r + 20;
    if (edge === 2) y = -r - 20;
    if (edge === 3) y = h + r + 20;
    const angle = Math.atan2(py * h - y, px * w - x) + (Math.random() - 0.5) * 0.8;
    const speed = 110 + difficulty * 55 + Math.min(180, elapsed * 3);
    return {x:x, y:y, r:r, vx:Math.cos(angle)*speed, vy:Math.sin(angle)*speed};
}
function sweptHit(enemies, x, y, nx, ny) {
    const dx = nx-x, dy = ny-y, length = dx*dx+dy*dy;
    return enemies.some(e => {
        const t = length ? Math.max(0, Math.min(1, ((e.x-x)*dx+(e.y-y)*dy)/length)) : 0;
        return Math.hypot(e.x-x-t*dx, e.y-y-t*dy) <= e.r+6;
    });
}
function step(enemies, dt, px, py, w, h) {
    let hit = false;
    const live = [];
    for (const e of enemies) {
        const nx = e.x+e.vx*dt, ny = e.y+e.vy*dt;
        if (sweptHit([{x:px,y:py,r:e.r}], e.x,e.y,nx,ny)) hit = true;
        e.x=nx; e.y=ny;
        if (e.x > -100 && e.x < w+100 && e.y > -100 && e.y < h+100) live.push(e);
    }
    return {enemies:live, hit:hit};
}
