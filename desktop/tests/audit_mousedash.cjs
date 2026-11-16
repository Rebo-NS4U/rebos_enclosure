// Obstacle-dodging balance audit only: excludes mandatory click targets.
// Not a full-game completion test or a substitute for human playtesting.
// Usage: node desktop/tests/audit_mousedash.cjs [alternate-engine.js]
const fs=require('fs'),vm=require('vm'),path=require('path');
const g={};vm.createContext(g);vm.runInContext(fs.readFileSync(process.argv[2]||path.join(__dirname, '../../system/apps/shell/MouseDashEngine.js'),'utf8'),g);
function run(seed,difficulty){
 vm.runInContext(`{let s=${seed}; Math.random=()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};}`,g);
 let x=240,y=240,vx=0,vy=0,enemies=[],spawn=0,nextDecision=0;
 const observations=[];
 const dt=1/60, reaction=.25, speed=450;
 for(let t=0;t<60;t+=dt){
  // Only perceive obstacles after they become visible, with 250 ms latency.
  observations.push({time:t, enemies:enemies.filter(e=>e.x+e.r>=0&&e.x-e.r<=480&&e.y+e.r>=0&&e.y-e.r<=480).map(e=>({...e}))});
  while(observations.length>1 && observations[1].time<=t-reaction) observations.shift();
  const seen=observations[0].time<=t-reaction ? observations[0].enemies : [];
  if(t>=nextDecision){
   nextDecision=t+reaction;
   let best=-Infinity,choice=[0,0];
   // No future spawns are visible. Choose bounded straight-line movements,
   // with a 250 ms decision interval and a finite look-ahead.
   for(let a=-1;a<32;a++){
    const cvx=a<0?0:Math.cos(a*Math.PI/16)*speed,cvy=a<0?0:Math.sin(a*Math.PI/16)*speed;
    let score=1e6, valid=true;
    for(let h=.025;h<=.8;h+=.025){
     const duration=Math.min(h,reaction),px=x+cvx*duration,py=y+cvy*duration;
     if(px<22||px>458||py<22||py>458){valid=false;break;}
     for(const e of seen){
      const clearance=Math.hypot(e.x+e.vx*(h+reaction)-px,e.y+e.vy*(h+reaction)-py)-e.r-g.playerRadius(t);
      score=Math.min(score,clearance/(1+h));
     }
    }
    if(!valid)continue;
    score=Math.min(score,140)-Math.hypot(x+cvx*reaction-240,y+cvy*reaction-240)*.09-(a<0?0:3);
    if(score>best){best=score;choice=[cvx,cvy];}
   }
   [vx,vy]=choice;
  }
  spawn+=dt;
  if(spawn>=g.spawnInterval(difficulty,t,'gauntlet')){spawn=0;enemies.push(g.spawn(480,480,x/480,y/480,difficulty,t,'gauntlet'));}
  const nx=x+vx*dt,ny=y+vy*dt;
  if(g.sweptHit(enemies,x,y,nx,ny,g.playerRadius(t)))return t;
  x=nx;y=ny;
  const result=g.step(enemies,dt,x,y,480,480,g.playerRadius(t));enemies=result.enemies;if(result.hit)return t;
 }
 return 60;
}
for(let d=0;d<4;d++){
 const trials=Array.from({length:20},(_,i)=>run(1234+i*79,d));
 console.log(JSON.stringify({difficulty:d,wins:trials.filter(t=>t>=60).length,trials:trials.length,median:trials.slice().sort((a,b)=>a-b)[10].toFixed(1),min:Math.min(...trials).toFixed(1),decisionMs:250,perceptionDelayMs:250,maxCursorSpeed:450}));
}
