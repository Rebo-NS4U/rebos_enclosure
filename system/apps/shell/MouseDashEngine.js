// Pure game mechanics; coordinates and speeds are logical pixels.
function playerRadius(elapsed) { return Math.min(11, 9 + elapsed * 0.025); }
function roundDuration(mode, difficulty) { return difficulty === 3 ? 0 : mode === "gauntlet" ? 60 : 0; }
function roundComplete(mode, elapsed, difficulty) { return roundDuration(mode, difficulty) > 0 && elapsed >= roundDuration(mode, difficulty); }
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
    const edge = Math.floor(Math.random() * 4), r = 22, speed = difficulty === 0 ? 45 : 70 + difficulty * 5;
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
// New rules use separate records; older scores remain untouched in settings.
function scoreKey(mode, difficulty) { return "tailored:" + (difficulty === 3 ? "boss" : mode) + difficulty; }

// Each tier has its own rhythm, targeting rules and collection pressure.
function difficultyHint(d) {
    return ["Easy · Rising drift: faster volleys and more aimed shots as you survive.",
        "Normal · Meteor field: unpredictable angles and aimed bursts.",
        "Hard · Crossfire: irregular mixed-angle bursts from changing borders.",
        "Extreme · Endless bosses: survive 3 attack phases for a clear bonus. No time limit."][d];
}
function bossState(elapsed) {
    const round = Math.floor(elapsed / 36), time = elapsed % 36;
    const names = ["THE HUNTER", "TWIN SENTINELS", "THE WEAVER"];
    return {round:round + 1, name:names[round % 3], kind:round % 3,
        level:Math.floor(round / 3), phase:time < 3 ? "warning" : time < 30 ? "attack" : "recovery",
        attack:Math.min(2, Math.max(0, Math.floor((time - 3) / 9))),
        remaining:time < 3 ? 3-time : time < 30 ? 30-time : 36-time};
}
function bossClears(elapsed) { return Math.floor((elapsed + 6) / 36); }
function encounterLabel(d, elapsed) {
    if (d === 3) {
        const b = bossState(elapsed);
        return "BOSS " + b.round + " · " + b.name + " · " + (b.phase === "attack" ? "PHASE " + (b.attack+1) : b.phase.toUpperCase()) + " · " + Math.ceil(b.remaining) + "s";
    }
    if (d === 2) return "CROSSFIRE · EXPECT THE UNEXPECTED";
    return d === 0 ? "RISING DRIFT" : "METEOR FIELD";
}
function spawnInterval(difficulty, elapsed) {
    if (difficulty === 0) return Math.max(0.36, 0.8-Math.min(120,elapsed)*0.004) + Math.random()*0.18;
    if (difficulty === 2) return Math.max(0.26,0.46-Math.min(120,elapsed)*0.0015)*(0.55+Math.random()*1.15);
    if (difficulty === 3) return Math.max(0.22, 0.52-bossState(elapsed).level*0.035)*(0.55+Math.random()*1.1);
    return Math.max(0.3, 0.55-Math.min(90,elapsed)*0.004)*(0.7+Math.random()*0.6);
}
function spawnBurst(w, h, difficulty, elapsed, px, py) {
    const boss = bossState(elapsed);
    if (difficulty === 3 && boss.phase !== "attack") return [];
    const cap = [245,290,325,350][difficulty];
    const baseSpeed = difficulty === 0 ? Math.min(cap,150+elapsed*0.9) : Math.min(cap,[110,215,245,230][difficulty]+(difficulty === 3 ? boss.level*12+boss.attack*20 : elapsed*1.2));
    const count = difficulty === 0 ? (elapsed >= 60 ? 2 : 1)+Math.floor(Math.random()*2) : difficulty === 1 ? 1+Math.floor(Math.random()*4) : difficulty === 2 ? 1+Math.floor(Math.random()*4) : 2+Math.floor(Math.random()*(2+boss.attack));
    const grouped = difficulty === 0 || Math.random() < (difficulty === 2 ? 0.25 : 0.35);
    const sharedLane = 0.1 + Math.random()*0.8;
    const distances = [px,w-px,py,h-py];
    const eligible = [0,1,2,3].filter(edge=>distances[edge]>=Math.min(180,baseSpeed*0.55+35));
    let edges = eligible.length ? eligible : [distances.indexOf(Math.max.apply(null,distances))];
    const sharedEdge = edges[Math.floor(Math.random()*edges.length)];
    const enemies=[];
    for(let i=0;i<count;i++) {
        const edge = grouped ? sharedEdge : edges[Math.floor(Math.random()*edges.length)];
        const r = difficulty === 0 ? 10 : 9+Math.random()*8, vertical=edge>=2, span=vertical ? w : h;
        const sweep = difficulty === 3 && boss.kind === 2 && Math.random()<0.55;
        const lane = Math.max(r+2, Math.min(span-r-2, sweep ? span*(0.5+0.36*Math.sin(elapsed*1.4+Math.random()*2.4+i*0.3)) : grouped ? sharedLane*span+(difficulty >= 2 ? (Math.random()-0.5)*120 : (i-(count-1)/2)*45) : r+2+Math.random()*(span-2*r-4)));
        const x = vertical ? lane : edge===0 ? r+2 : w-r-2;
        const y = vertical ? (edge===2 ? r+2 : h-r-2) : lane;
        const aimed = difficulty === 0 ? Math.random() < Math.min(0.55,0.2+elapsed*0.003) : difficulty === 1 ? Math.random()<0.75 : difficulty === 2 ? Math.random()<0.6 : Math.random() < (boss.kind === 0 ? 0.85 : boss.kind === 1 ? 0.55 : 0.3);
        const tx = aimed ? px : difficulty >= 1 ? w*(0.15+Math.random()*0.7) : vertical ? x : w/2;
        const ty = aimed ? py : difficulty >= 1 ? h*(0.15+Math.random()*0.7) : vertical ? h/2 : y;
        const angle = Math.atan2(ty-y,tx-x)+(difficulty >= 2 ? (Math.random()-0.5)*0.7 : aimed ? (i-(count-1)/2)*0.17 : 0);
        // Visible border births retain at least 550ms reaction time at every tier.
        const safeSpeed = Math.max(40,(distances[edge]-2*r-playerRadius(elapsed)-6)/0.55);
        const speed = Math.min(cap,baseSpeed*(0.8+Math.random()*0.35),safeSpeed);
        enemies.push({x:x,y:y,r:r,vx:Math.cos(angle)*speed,vy:Math.sin(angle)*speed,orbiting:false,spin:Math.random()*360});
    }
    return enemies;
}
