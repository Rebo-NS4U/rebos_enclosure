// Run with node desktop/tests/test_mousedash.cjs.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const game = {};
vm.createContext(game);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../system/apps/shell/MouseDashEngine.js'), 'utf8'), game);
// Cursor motion must collide even when both endpoints miss the obstacle.
assert(game.sweptHit([{x:50,y:50,r:10}], 0,50,100,50));
assert(!game.sweptHit([{x:50,y:80,r:10}], 0,50,100,50));
assert(game.sweptHit([{x:50,y:50,r:10}], 50,50,50,50));
// Enemy movement also uses swept collision to avoid tunneling.
assert(game.step([{x:0,y:50,r:10,vx:100,vy:0}], 1,50,50,400,400).hit);
assert.equal(game.step([{x:600,y:0,r:10,vx:0,vy:0}], .016,50,50,400,400).enemies.length, 0);
for (let i=0; i<100; i++) {
    const e = game.spawn(800,500,.5,.5,2,10);
    assert(Number.isFinite(e.vx) && Number.isFinite(e.vy));
    assert(e.x<0 || e.x>800 || e.y<0 || e.y>500);
}
console.log('MouseDash mechanics: PASS');

// Survival progressively enlarges the player and increases spawn pressure.
assert(game.playerRadius(30) > game.playerRadius(0));
assert.equal(game.playerRadius(1000), 11);
for (let d = 0; d < 3; d++) {
    assert(game.spawnInterval(d, 30) < game.spawnInterval(d, 0));
    assert(game.spawnInterval(d, 10000) >= .09);
}
assert(game.spawnInterval(2, 0) < game.spawnInterval(0, 0));
assert(game.sweptHit([{x:50,y:70,r:5}],0,50,100,50,18));
assert(!game.sweptHit([{x:50,y:70,r:5}],0,50,100,50,9));
console.log('Difficulty progression and growing hitbox: PASS');

// Timed modes must win only at their goals; Survival remains endless.
assert.equal(game.roundDuration('gauntlet'), 60);
assert(!game.roundComplete('survival', 100000));
assert(!game.roundComplete('gauntlet', 59.99));
assert(game.roundComplete('gauntlet', 60));
assert.equal(game.pressure('gauntlet', 9.99), 1);
assert(game.pressure('gauntlet', 10) > game.pressure('gauntlet', 9.99));
assert.equal(game.pressure('gauntlet', 1000), game.pressure('gauntlet', 50));
assert(game.spawnInterval(3, 0) < game.spawnInterval(2, 0));
vm.runInContext('Math.random = () => 0.5', game);
const normal = game.spawn(300, 300, .5, .5, 1, 50, 'survival');
const wave = game.spawn(300, 300, .5, .5, 1, 50, 'gauntlet');
assert(Math.hypot(wave.vx, wave.vy) > Math.hypot(normal.vx, normal.vy));
for (const mode of ['survival', 'gauntlet'])
    for (let d = 0; d < 4; d++)
        assert(game.spawnInterval(d, 10000, mode) >= .09);
console.log('Timed goals, wave escalation and Extreme difficulty: PASS');

// Death inspection must identify the earliest obstacle and exact first contact.
const cursorHit = game.contact([{x:80,y:50,r:10}, {x:50,y:50,r:10}], 0,50,100,50);
assert.equal(cursorHit.enemy.x, 50);
assert.equal(cursorHit.x, 31);
assert.equal(cursorHit.t, .31);
assert.equal(cursorHit.cause, 'cursor');
assert.equal(game.contact([{x:50,y:80,r:10}], 0,50,100,50), null);
assert.equal(game.contact([{x:50,y:50,r:10}], 50,50,50,50).t, 0);
const fatalFrame = game.step([{x:0,y:50,r:10,vx:100,vy:0}, {x:0,y:200,r:10,vx:100,vy:0}], 1,50,50,400,400);
assert.equal(fatalFrame.collision.cause, 'enemy');
assert.equal(fatalFrame.collision.enemy.x, 31);
assert.equal(fatalFrame.collision.x, 50);
assert.equal(fatalFrame.enemies[0].x, 31);
assert.equal(fatalFrame.enemies[1].x, 31); // The whole field stops at that instant.
console.log('Exact death position, cause and earliest obstacle: PASS');

// Balance guardrails for the shipped 480px arena.
vm.runInContext('{ let seed=91; Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;}; }', game);
for (let d = 0; d < 4; d++) {
    assert(game.enemySpeed(d, 10000, 'gauntlet') <= 326);
    assert(game.spawnInterval(d, 10000, 'gauntlet') >= [0.5, 0.4, 0.32, 0.26][d]);
    for (const [px, py] of [[0,0], [0.02,0.5], [0.5,0.5], [0.98,0.98]]) for (let sample=0; sample<100; sample++) {
        const e = game.spawn(480,480,px,py,d,60,'gauntlet');
        const hit = game.contact([{x:px*480, y:py*480, r:game.playerRadius(60)}], e.x,e.y,e.x+e.vx*10,e.y+e.vy*10,e.r);
        if (hit) {
            // Discount the offscreen approach; count only visible warning time.
            const offscreenTime = e.x < -e.r ? 20 / e.vx : e.x > 480+e.r ? -20 / e.vx
                : e.y < -e.r ? 20 / e.vy : -20 / e.vy;
            assert(hit.t * 10 - offscreenTime >= 0.65 - 1e-6);
        }
    }
}
console.log('Capped difficulty and visible spawn reaction margin: PASS');

// Touch targets are slower, start visibly inside the arena, and traverse it.
for (let d=0; d<4; d++) for (let i=0; i<100; i++) {
    const target = game.spawnTarget(480,480,d);
    assert(target.x >= target.r && target.x <= 480-target.r);
    assert(target.y >= target.r && target.y <= 480-target.r);
    assert(Math.hypot(target.vx,target.vy) < game.enemySpeed(d,0,'survival'));
    assert(!game.stepTarget(target,4,480,480).missed);
    assert(game.stepTarget(target,10,480,480).missed);
    assert(game.sweptHit([target],target.x,target.y,target.x,target.y,0));
    assert(game.sweptHit([target],target.x,target.y,target.x+target.r,target.y,0));
    assert(!game.sweptHit([target],target.x+target.r+1,target.y,target.x+target.r+1,target.y,0));
    const frozen = game.stepTarget(target,0,480,480).target;
    assert.equal(frozen.x,target.x); assert.equal(frozen.y,target.y);
}
assert(!game.sweptHit([],0,0,0,0));
console.log('Slow touch targets, hit area and escape deadline: PASS');

// Collect on swept contact in either direction, including clear endpoints.
const pickup = {x:100,y:100,r:22,vx:80,vy:0};
assert(game.sweptHit([pickup],0,100,200,100,9));
assert(!game.sweptHit([pickup],0,140,200,140,9));
assert(game.stepTarget(pickup,2,480,480,180,100,9).collected);
assert(!game.stepTarget(pickup,2,480,480,180,140,9).collected);
assert(game.stepTarget(pickup,0,480,480,130,100,9).collected);
console.log('Cursor and target swept touch collection: PASS');

// BASE/Normal favors denser, slower lanes while preserving reaction margins.
for (const mode of ['survival', 'gauntlet']) for (const elapsed of [0, 30, 60, 300]) {
    const previousSpeed = (145 + Math.min(60, elapsed * .8)) * Math.sqrt(game.pressure(mode, elapsed));
    const previousGap = Math.max(.4, .85 / (1 + Math.min(90, elapsed) * .006) / game.pressure(mode, elapsed));
    assert(Math.abs(game.enemySpeed(1, elapsed, mode) - previousSpeed * .8) < 1e-9);
    assert(game.spawnInterval(1, elapsed, mode) <= previousGap);
}
assert.equal(game.spawnInterval(1, 0, 'survival'), .65);
assert.equal(game.enemySpeed(1, 0, 'survival'), 116);
console.log('Denser, slower default difficulty: PASS');

// Pulse removes only intersecting hazards and reports points without mutating input.
const hazards = [{x:0,y:0,r:10}, {x:125,y:0,r:10}, {x:126,y:0,r:10}];
const blast = game.pulse(hazards,0,0,115);
assert.equal(blast.count,2); assert.equal(blast.enemies.length,1);
assert.equal(blast.enemies[0].x,126); assert.equal(hazards.length,3);
assert.equal(game.pulse([],0,0,115).count,0);
const debris = [{vx:100,vy:0,orbiting:true}, {vx:100,vy:0}];
game.steerDebris(debris,0); assert.equal(debris[0].vx,100);
game.steerDebris(debris,1);
assert(debris[0].vy > 0); assert(Math.abs(Math.hypot(debris[0].vx,debris[0].vy)-100)<1e-9);
assert.equal(debris[1].vy,0);
console.log('Starwake pulse boundary and orbital steering: PASS');

// A swept close pass earns once per hazard, including clear endpoints.
const closePass = [{x:50,y:25,r:10}];
assert.equal(game.graze(closePass,0,0,100,0,9),1);
assert.equal(game.graze(closePass,100,0,0,0,9),0);
assert.equal(game.graze([{x:50,y:19,r:10}],0,0,100,0,9),0); // Contact.
assert.equal(game.graze([{x:50,y:34,r:10}],0,0,100,0,9),0); // Too far.
const incomingGraze = [{x:0,y:25,r:10,vx:100,vy:0}];
assert.equal(game.step(incomingGraze,1,50,0,480,480).grazes,1);
assert.equal(game.step(incomingGraze,0,50,0,480,480).grazes,0);
const lethal = game.step([{x:0,y:25,r:10,vx:100,vy:0},{x:0,y:0,r:10,vx:100,vy:0}],1,50,0,480,480);
assert(lethal.hit); assert.equal(lethal.grazes,0);
for (const [age,points] of [[0,150],[2,150],[2.001,100]]) assert.equal(game.starReward(0,age).points,points);
assert.equal(game.starReward(5,1).combo,5);
assert.equal(game.starReward(5,1).points,750);
let bonus = game.award(960,40,10,0,0);
assert.equal(bonus.score,1000); assert(bonus.activated); assert.equal(bonus.overdriveUntil,16);
bonus = game.award(1000,100,15,16,1);
assert.equal(bonus.score,1200); assert(!bonus.activated); assert.equal(bonus.overdriveUntil,16);
assert.equal(game.award(1000,100,16,16,1).score,1100); // Exact expiry.
bonus = game.award(1900,100,15,16,1);
assert.equal(bonus.score,2100); assert.equal(bonus.overdriveUntil,21);
console.log('Near-miss sweeps, anti-repeat, fatal-frame exclusion, quick stars and overdrive milestones: PASS');

// Objectives use single-flight totals, capped display values, and exact thresholds.
let missions = game.objectives(29.99,4,7);
assert(missions.every(o=>o.progress<o.goal));
missions = game.objectives(30,5,8);
assert(missions.every(o=>o.progress===o.goal));
assert(game.objectives(1000,1000,1000).every(o=>o.progress===o.goal));
assert(game.styleAvailable('scout',{}));
assert(!game.styleAvailable('collector',{}));
assert(!game.styleAvailable('surfer',{surfer:1}));
assert(game.styleAvailable('collector',{collector:true}));
assert(!game.styleAvailable('unknown',{unknown:true}));
const scout = game.loadout('scout'), collector = game.loadout('collector'), surfer = game.loadout('surfer');
assert.equal(game.loadout('unknown').id,'scout');
assert.equal(collector.pickupBonus,12); assert(collector.pulseRadius<scout.pulseRadius);
assert(surfer.grazePoints>scout.grazePoints); assert(surfer.pulseRadius<scout.pulseRadius);
assert(!game.sweptHit([{x:50,y:0,r:22}],10,0,10,0,9));
assert(game.sweptHit([{x:50,y:0,r:22}],10,0,10,0,9+collector.pickupBonus));
assert.equal(game.pulse([{x:110,y:0,r:10}],0,0,collector.pulseRadius).count,0);
assert.equal(game.pulse([{x:110,y:0,r:10}],0,0,scout.pulseRadius).count,1);
for (const [points,medal,next] of [[0,'UNRANKED',1000],[999,'UNRANKED',1000],[1000,'BRONZE',3000],[2999,'BRONZE',3000],[3000,'SILVER',6000],[5999,'SILVER',6000],[6000,'GOLD',0]]) {
 assert.equal(game.medal(points),medal); assert.equal(game.nextMedal(points),next);
}
assert.equal(game.scoreKey('survival',1,'scout'),'survival1');
assert.equal(game.scoreKey('survival',1,'collector'),'survival1:collector');
assert.notEqual(game.scoreKey('gauntlet',1,'surfer'),game.scoreKey('survival',1,'surfer'));
console.log('Career thresholds, unlock gates, style tradeoffs, medals and isolated record keys: PASS');
