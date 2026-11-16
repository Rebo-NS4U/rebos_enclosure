// Pure game mechanics; coordinates and speeds are logical pixels.
function playerRadius(elapsed) { return Math.min(11, 9 + elapsed * 0.025); }
function roundDuration(mode) { return mode === "gauntlet" ? 60 : 0; }
function roundComplete(mode, elapsed) { return roundDuration(mode) > 0 && elapsed >= roundDuration(mode); }
function pressure(mode, elapsed) {
    return mode === "gauntlet" ? 1 + Math.min(5, Math.floor(elapsed / 10)) * 0.08 : 1;
}
// Independent caps keep speed, density and hitbox growth from compounding forever.
function enemySpeed(difficulty, elapsed, mode) {
    return (difficulty === 1 ? 0.8 : 1) * (110 + difficulty * 35 + Math.min(60, elapsed * 0.8)) * Math.sqrt(pressure(mode, elapsed));
}
function spawnInterval(difficulty, elapsed, mode) {
    const floors = [0.5, 0.4, 0.32, 0.26];
    return Math.max(floors[difficulty], (difficulty === 1 ? 0.65 : 1 - difficulty * 0.15) / (1 + Math.min(90, elapsed) * 0.006) / pressure(mode, elapsed));
}
function spawn(w, h, px, py, difficulty, elapsed, mode) {
    const speed = enemySpeed(difficulty, elapsed, mode);
    // At least 650 ms from first appearance to a stationary cursor on this edge.
    // Choose a distant edge instead of silently killing a player near the border.
    const clearance = speed * 0.65 + playerRadius(elapsed);
    const distances = [px * w, (1 - px) * w, py * h, (1 - py) * h];
    let edges = [0, 1, 2, 3].filter(i => distances[i] >= clearance);
    if (!edges.length) edges = [distances.indexOf(Math.max.apply(null, distances))];
    const edge = edges[Math.floor(Math.random() * edges.length)], r = 9 + Math.random() * 16;
    let x = Math.random() * w, y = Math.random() * h;
    if (edge === 0) x = -r - 20;
    if (edge === 1) x = w + r + 20;
    if (edge === 2) y = -r - 20;
    if (edge === 3) y = h + r + 20;
    const angle = Math.atan2(py * h - y, px * w - x) + (Math.random() - 0.5) * 0.8;
    return {x:x, y:y, r:r, vx:Math.cos(angle)*speed, vy:Math.sin(angle)*speed, orbiting: elapsed >= 12 && Math.random() < 0.25};
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
    let grazes = 0;
    for (const e of enemies) {
        if (!collision && !e.grazed && nearPass(e.x, e.y, e.x + e.vx * advance, e.y + e.vy * advance, px, py, radius + e.r)) {
            e.grazed = true; grazes++;
        }
        e.x += e.vx * advance; e.y += e.vy * advance;
        if (e.x > -100 && e.x < w+100 && e.y > -100 && e.y < h+100) live.push(e);
    }
    return {enemies:live, hit:collision !== null, collision:collision, grazes:grazes};
}

// One slow, harmless touch target at a time. Keep its lane clear of the HUD.
function spawnTarget(w, h, difficulty) {
    const edge = Math.floor(Math.random() * 4), r = 22, speed = 70 + difficulty * 5;
    const laneX = w * (0.2 + Math.random() * 0.6), laneY = h * (0.2 + Math.random() * 0.6);
    if (edge === 0) return {x:r+8,y:laneY,r:r,vx:speed,vy:0};
    if (edge === 1) return {x:w-r-8,y:laneY,r:r,vx:-speed,vy:0};
    if (edge === 2) return {x:laneX,y:r+8,r:r,vx:0,vy:speed};
    return {x:laneX,y:h-r-8,r:r,vx:0,vy:-speed};
}
function stepTarget(target, dt, w, h, px, py, radius = 9) {
    const next = {x:target.x+target.vx*dt,y:target.y+target.vy*dt,r:target.r,vx:target.vx,vy:target.vy};
    const collected = px !== undefined && py !== undefined && sweptHit([{x:px,y:py,r:radius}], target.x,target.y,next.x,next.y,target.r);
    return {target:next, collected:collected, missed:next.x < -next.r || next.x > w+next.r || next.y < -next.r || next.y > h+next.r};
}

// Curved debris turns gently; swept collision still checks every frame.
function steerDebris(enemies, dt) {
    const angle = dt * 0.45, c = Math.cos(angle), s = Math.sin(angle);
    for (const e of enemies) if (e.orbiting) {
        const vx = e.vx; e.vx = vx * c - e.vy * s; e.vy = vx * s + e.vy * c;
    }
}
function pulse(enemies, x, y, radius) {
    const live = enemies.filter(e => Math.hypot(e.x - x, e.y - y) > radius + e.r);
    return {enemies: live, count: enemies.length - live.length};
}

// Closest point on the swept path. Actual contacts never earn a near-miss.
function nearPass(x, y, nx, ny, cx, cy, radius) {
    const dx = nx-x, dy = ny-y, length = dx*dx+dy*dy;
    const t = length ? Math.max(0, Math.min(1, ((cx-x)*dx+(cy-y)*dy)/length)) : 0;
    const distance = Math.hypot(x+dx*t-cx, y+dy*t-cy);
    return distance > radius && distance <= radius + 14;
}
function graze(enemies, x, y, nx, ny, radius) {
    let count = 0;
    for (const e of enemies) if (!e.grazed && nearPass(x,y,nx,ny,e.x,e.y,radius+e.r)) {
        e.grazed = true; count++;
    }
    return count;
}
function starReward(combo, age) {
    const chain = Math.min(5, combo + 1);
    return {combo:chain, points:chain * (age <= 2 ? 150 : 100), quick:age <= 2};
}
function award(score, points, elapsed, overdriveUntil, milestone) {
    const next = score + points * (elapsed < overdriveUntil ? 2 : 1);
    const reached = Math.floor(next / 1000);
    return {score:next, milestone:Math.max(milestone,reached),
        overdriveUntil:reached > milestone ? elapsed + 6 : overdriveUntil,
        activated:reached > milestone};
}
