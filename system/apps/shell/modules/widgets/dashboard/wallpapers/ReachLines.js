// Clockwise from the Exchange. Each route begins at the preceding district's turnout.
const loops=[
 [[.24,.5],[.24,.44],[.13,.44],[.08,.36],[.08,.18],[.15,.13],[.38,.13],[.44,.20],[.50,.20],[.45,.26],[.36,.26],[.36,.41],[.28,.45]],
 [[.5,.2],[.58,.2],[.75,.2],[.79,.13],[.91,.13],[.94,.23],[.89,.34],[.80,.39],[.80,.50],[.75,.44],[.74,.26],[.64,.20],[.54,.25]],
 [[.80,.50],[.85,.53],[.94,.60],[.94,.78],[.87,.88],[.75,.88],[.71,.80],[.56,.80],[.50,.80],[.55,.74],[.56,.60],[.56,.50],[.74,.50]],
 [[.50,.80],[.45,.84],[.37,.91],[.14,.91],[.08,.83],[.08,.72],[.27,.72],[.32,.66],[.29,.57],[.24,.50],[.20,.56],[.16,.64],[.34,.65],[.41,.72]]
];
const exits=[8,8,8,9];
function line(w,h,index){
    const pts=loops[index], segments=[], stops=[];let length=0;
    for(let i=0;i<pts.length;i++){
        const a=pts[i],b=pts[(i+1)%pts.length],x=a[0]*w,y=a[1]*h,dx=b[0]*w-x,dy=b[1]*h-y,size=Math.hypot(dx,dy);
        segments.push({x,y,dx:dx/size,dy:dy/size,size,start:length});length+=size;
    }
    for(const i of [2,4,6,9,11])stops.push(segments[i].start/length);
    return {segments,length,stops,exit:segments[exits[index]].start/length};
}
function point(path,phase) {
    const d=((phase%1+1)%1)*path.length;
    const s=path.segments.find(seg=>d<seg.start+seg.size)||path.segments[0];
    return {x:s.x+s.dx*(d-s.start),y:s.y+s.dy*(d-s.start),angle:Math.atan2(s.dy,s.dx)};
}
function trace(c,path,progress) {
    c.moveTo(path.segments[0].x,path.segments[0].y);
    for(const s of path.segments) {
        const d=Math.min(s.size,progress*path.length-s.start);
        if(d<=0) break;
        c.lineTo(s.x+d*s.dx,s.y+d*s.dy);
    }
}

// In clockwise service order the district edges meet at Hill Terrace,
// East Docks, South Yard and West Bank.
function transferLegs(lines,source,phase,target) {
    const queue=[[source]],seen=[source];
    while(queue.length) {
        const chain=queue.shift(), current=chain[chain.length-1];
        if(current===target) {
            const legs=[];
            for(let i=1;i<chain.length;i++) {
                const a=chain[i-1],b=chain[i];
                const edge=(a+1)%4===b?a:b;
                const end=a===edge ? lines[a].path.exit : 0;
                legs.push({index:a,start:phase,end});
                phase=b===edge ? lines[b].path.exit : 0;
            }
            legs.push({index:target,start:phase});
            return legs;
        }
        for(const n of [(current+1)%4,(current+3)%4])
            if(lines[n] && !seen.includes(n)){seen.push(n);queue.push(chain.concat(n));}
    }
    return [];
}
function transferPoint(lines,legs,end,t) {
    let total=0;
    const spans=legs.map(leg=>{
        const delta=(( (leg.end ?? end)-leg.start+1.5)%1)-.5;
        const length=Math.abs(delta)*lines[leg.index].path.length;
        total+=length;
        return {delta,length};
    });
    let remaining=t*total;
    for(let i=0;i<legs.length;i++) {
        const leg=legs[i],span=spans[i];
        if(remaining<=span.length || i===legs.length-1) {
            const phase=leg.start+span.delta*Math.min(1,remaining/Math.max(.000001,span.length));
            return {index:leg.index,phase,pt:point(lines[leg.index].path,phase)};
        }
        remaining-=span.length;
    }
}
