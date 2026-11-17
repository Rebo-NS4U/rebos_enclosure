// Pure game mechanics; coordinates and speeds are logical pixels.
function playerRadius(elapsed) { return Math.min(11, 9 + elapsed * 0.025); }
function roundDuration(mode) { return mode === "gauntlet" ? 60 : 0; }
function roundComplete(mode, elapsed) { return roundDuration(mode) > 0 && elapsed >= roundDuration(mode); }
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
// Career badges require a single flight; completed badges survive retries.
function objectives(elapsed, stars, grazes) {
    return [
        {id:"collector", name:"STAR COLLECTOR", progress:Math.min(5,stars), goal:5, reward:"Career badge"},
        {id:"surfer", name:"DEBRIS SURFER", progress:Math.min(8,grazes), goal:8, reward:"Career badge"},
        {id:"voyager", name:"VOYAGER", progress:Math.min(30,Math.floor(elapsed)), goal:30, reward:"Career badge"}
    ];
}
function medal(score) { return score >= 6000 ? "GOLD" : score >= 3000 ? "SILVER" : score >= 1000 ? "BRONZE" : "UNRANKED"; }
function nextMedal(score) { return score < 1000 ? 1000 : score < 3000 ? 3000 : score < 6000 ? 6000 : 0; }
// New rules use separate records; older scores remain untouched in settings.
function scoreKey(mode, difficulty) { return "drift:" + mode + difficulty; }

// Irregular bursts, not a repeating formation sequence. Every meteor gets its own
// speed and aim; grouped births sometimes share a patch of the border.
function spawnInterval(difficulty, elapsed) {
    const base = Math.max([0.48,0.3,0.24,0.2][difficulty], [0.8,0.55,0.43,0.35][difficulty] - Math.min(90,elapsed)*0.004);
    return base * (0.7 + Math.random()*0.6);
}
function spawnBurst(w, h, difficulty, elapsed, px, py) {
    const cap = [225,290,325,350][difficulty];
    const baseSpeed = Math.min(cap,[175,215,245,270][difficulty]+elapsed*1.2);
    const count = 1 + Math.floor(Math.random() * (difficulty === 0 ? 3 : 4));
    const grouped = Math.random() < 0.35;
    const sharedLane = 0.1 + Math.random()*0.8;
    const distances = [px,w-px,py,h-py];
    // Exclude nearby borders rather than materializing hazards on the ship.
    const eligible = [0,1,2,3].filter(edge=>distances[edge]>=Math.min(180,baseSpeed*0.55+35));
    const edges = eligible.length ? eligible : [distances.indexOf(Math.max.apply(null,distances))];
    const sharedEdge = edges[Math.floor(Math.random()*edges.length)];
    const enemies=[];
    for(let i=0;i<count;i++) {
        const edge = grouped ? sharedEdge : edges[Math.floor(Math.random()*edges.length)];
        const r = 9+Math.random()*8, vertical=edge>=2, span=vertical ? w : h;
        const lane = Math.max(r+2, Math.min(span-r-2, grouped ? sharedLane*span+(Math.random()-0.5)*65 : r+2+Math.random()*(span-2*r-4)));
        const x = vertical ? lane : edge===0 ? r+2 : w-r-2;
        const y = vertical ? (edge===2 ? r+2 : h-r-2) : lane;
        const aimed = Math.random()<0.75;
        const tx = aimed ? px : w*(0.15+Math.random()*0.7);
        const ty = aimed ? py : h*(0.15+Math.random()*0.7);
        const angle = Math.atan2(ty-y,tx-x)+(Math.random()-0.5)*0.65;
        // At least 550ms before reaching a stationary ship, even without advance cues.
        const safeSpeed = Math.max(40,(distances[edge]-2*r-playerRadius(elapsed)-6)/0.55);
        const speed = Math.min(cap,baseSpeed*(0.8+Math.random()*0.35),safeSpeed);
        enemies.push({x:x,y:y,r:r,vx:Math.cos(angle)*speed,vy:Math.sin(angle)*speed,orbiting:false,spin:Math.random()*360});
    }
    return enemies;
}
