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
assert.equal(game.playerRadius(1000),11);
assert.equal(game.roundDuration('gauntlet'),60);
assert(!game.roundComplete('gauntlet',59.99)); assert(game.roundComplete('gauntlet',60));
assert(!game.roundComplete('survival',10000));

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

// Touch targets are slower, start visibly inside the arena, and traverse it.
for (let d=0; d<4; d++) for (let i=0; i<100; i++) {
    const target = game.spawnTarget(480,480,d);
    assert(target.x >= target.r && target.x <= 480-target.r);
    assert(target.y >= target.r && target.y <= 480-target.r);
    assert(Math.hypot(target.vx,target.vy) <= 85);
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
console.log('Near misses and quick star rewards: PASS');

// Objectives use single-flight totals, capped display values, and exact thresholds.
let missions = game.objectives(29.99,4,7);
assert(missions.every(o=>o.progress<o.goal));
missions = game.objectives(30,5,8);
assert(missions.every(o=>o.progress===o.goal));
assert(game.objectives(1000,1000,1000).every(o=>o.progress===o.goal));
for (const [points,medal,next] of [[0,'UNRANKED',1000],[999,'UNRANKED',1000],[1000,'BRONZE',3000],[2999,'BRONZE',3000],[3000,'SILVER',6000],[5999,'SILVER',6000],[6000,'GOLD',0]]) {
 assert.equal(game.medal(points),medal); assert.equal(game.nextMedal(points),next);
}
assert.equal(game.scoreKey('survival',1),'pressure:survival1');
assert.notEqual(game.scoreKey('gauntlet',1),game.scoreKey('survival',1));
console.log('Career objectives, medals and new-rules records: PASS');

// Patterns always enter from a distant edge and expose the promised safe gate.
vm.runInContext('{ let seed=91; Math.random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;}; }',game);
for (let d=0;d<4;d++) for (let i=0;i<30;i++) for(const [px,py] of [[0,0],[240,240],[480,480],[80,400]]) {
 const plan=game.encounter(i,480,480,d,300,px,py);
 assert(plan.warning>=0.85); assert(plan.events.length>0);
 assert(plan.events.every(event=>event.enemies.length>0));
 for(const event of plan.events) for(const e of event.enemies) {
  assert(e.x<0 || e.x>480 || e.y<0 || e.y>480);
  assert(Math.hypot(e.vx,e.vy)<=[225,290,325,350][d]+1e-8);
  assert(Number.isFinite(e.vx) && Number.isFinite(e.vy));
  const hit=game.contact([{x:px,y:py,r:11}],e.x,e.y,e.x+e.vx*10,e.y+e.vy*10,e.r);
  if(hit) assert(hit.t*10>=0.6); // In addition to the visible warning.
 }
 if(plan.gap) {
  const gap=plan.gap;
  assert(gap.position-gap.half>0 && gap.position+gap.half<480);
  assert(gap.half*2>2*game.playerRadius(300)+28);
  for(const event of plan.events) for(const e of event.enemies)
   assert(Math.abs((event.gap.vertical?e.x:e.y)-event.gap.position)-e.r>=event.gap.half);
 }
 assert(game.launchEvents(plan.events,-0.01).launched.length===0);
 let pending=plan.events,total=0;
 for(let age=0;age<=2;age+=.02) { const batch=game.launchEvents(pending,age);total+=batch.launched.length;pending=batch.pending; }
 assert.equal(total,plan.events.reduce((sum,event)=>sum+event.enemies.length,0));
 assert.equal(pending.length,0);
}
assert.equal(game.encounter(0,480,480,1,0,240,240).name,'METEOR GATE');
assert.equal(game.encounter(1,480,480,1,0,240,240).events.length,3);
assert.equal(game.encounter(2,480,480,1,0,240,240).events.length,7);
assert.equal(game.encounter(0,480,480,0,0,240,240).gap.half,52);
assert.equal(game.encounter(0,480,480,3,0,240,240).gap.half,26);
console.log('Formation geometry, minimum warning, speed caps, safe gaps and exactly-once event launches: PASS');

// Pressure ramps, launches finish before the director advances, and gates force weaving.
for(let d=0;d<4;d++) {
 assert(game.encounterInterval(d,60)<game.encounterInterval(d,0));
 assert(game.encounterInterval(d,1000)>3);
 for(let kind=0;kind<3;kind++) {
  const plan=game.encounter(kind,480,480,d,1000,240,240);
  assert(plan.warning+Math.max(...plan.events.map(e=>e.delay))<game.encounterInterval(d,1000));
 }
 const gate=game.encounter(0,480,480,d,0,240,240);
 assert.notEqual(gate.events[0].gap.position,gate.events[1].gap.position);
 const train=game.encounter(2,480,480,d,0,240,240);
 // No automatic safe center rail: one comet heads directly down the aimed lane.
 assert(train.events[0].enemies.some(e=>game.sweptHit([{x:240,y:240,r:11}],e.x,e.y,e.x+e.vx*5,e.y+e.vy*5,e.r)));
}
console.log('Escalating cadence, changing gates, completed queues and occupied center rail: PASS');
