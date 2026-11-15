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
assert.equal(game.playerRadius(1000), 18);
for (let d = 0; d < 3; d++) {
    assert(game.spawnInterval(d, 30) < game.spawnInterval(d, 0));
    assert(game.spawnInterval(d, 10000) >= .09);
}
assert(game.spawnInterval(2, 0) < game.spawnInterval(0, 0));
assert(game.sweptHit([{x:50,y:70,r:5}],0,50,100,50,18));
assert(!game.sweptHit([{x:50,y:70,r:5}],0,50,100,50,9));
console.log('Difficulty progression and growing hitbox: PASS');
