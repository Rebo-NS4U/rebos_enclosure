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
function scoreKey(mode, difficulty) { return "patterns:" + mode + difficulty; }

// Snapshot the player's position once, during the warning. No homing or late aim.
function encounter(index, w, h, difficulty, elapsed, px, py) {
    const distances = [px, w-px, py, h-py];
    const edge = distances.indexOf(Math.max.apply(null, distances));
    const vertical = edge >= 2, span = vertical ? w : h;
    const speed = Math.min(230, 135 + difficulty * 18 + Math.min(35, elapsed * 0.4));
    const type = index % 3, events = [];
    const gap = span * (0.25 + Math.random() * 0.5), halfGap = difficulty === 0 ? 82 : 68;
    function meteor(lane, angleOffset, r) {
        const x = vertical ? lane : edge === 0 ? -r-20 : w+r+20;
        const y = vertical ? (edge === 2 ? -r-20 : h+r+20) : lane;
        const base = edge === 0 ? 0 : edge === 1 ? Math.PI : edge === 2 ? Math.PI/2 : -Math.PI/2;
        return {x:x,y:y,r:r,vx:Math.cos(base+angleOffset)*speed,vy:Math.sin(base+angleOffset)*speed,orbiting:false};
    }
    if (type === 0) {
        const wall=[];
        for(let lane=24;lane<span;lane+=40) if(Math.abs(lane-gap)>halfGap) wall.push(meteor(lane,0,12));
        events.push({delay:0,enemies:wall});
    } else if(type === 1) {
        const origin = span * 0.5;
        const source = meteor(origin,0,10);
        const angle = Math.atan2(py-source.y,px-source.x);
        const fan=[];
        for(let i=-2;i<=2;i++) fan.push({x:source.x,y:source.y,r:10,vx:Math.cos(angle+i*0.27)*speed,vy:Math.sin(angle+i*0.27)*speed,orbiting:false});
        events.push({delay:0,enemies:fan});
        events.push({delay:1.1,enemies:fan.map(e=>Object.assign({},e))});
    } else {
        // Two parallel trains leave the rest of the arena open for routing.
        const lane = Math.max(55,Math.min(span-55,vertical ? px : py));
        for(let i=0;i<5;i++) events.push({delay:i*0.32,enemies:[meteor(lane-34,0,11),meteor(lane+34,0,11)]});
    }
    const preview=events[0].enemies.map(e=>({x:Math.max(0,Math.min(w,e.x)),y:Math.max(0,Math.min(h,e.y)),angle:Math.atan2(e.vy,e.vx)*180/Math.PI}));
    return {name:["METEOR GATE","FAN VOLLEY","COMET TRAINS"][type],
        hint:["Find the marked gap","Move between the spreading lanes","Leave the twin comet lanes"][type],
        warning:1.5, events:events, preview:preview,
        gap:type===0 ? {vertical:vertical,position:gap,half:halfGap-12,edge:edge} : null};
}
// A queue is advanced only by gameplay time, so pause freezes all launches.
function launchEvents(events, age) {
    return {launched:events.filter(e=>e.delay<=age).reduce((all,e)=>all.concat(e.enemies),[]),
        pending:events.filter(e=>e.delay>age)};
}
