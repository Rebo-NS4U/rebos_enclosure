import QtQuick
import "ReachLines.js" as Rail
import "Estuary.js" as Terrain

Rectangle {
    id: rail
    color: "black"
    required property var workspaces
    required property var windows
    required property string output
    readonly property color accent: "#ffcc74"
    readonly property var inks: ["#eab875","#8bc5b1","#cab4cd","#98b9cf"]
    property bool paused: false
    signal workspaceClicked(double desk)
    property var systems: []
    property var routes: []
    property var cars: ({})
    property bool arranging: false
    property var hits: []
    property var hover: null
    property var districtLights: []
    property var echo: null
    property double previous: 0

    function reconcile() {
        if (!width || !height || !workspaces || !windows) return;
        const ordered = workspaces.filter(s => s.output === output &&
            windows.some(w => w.workspace_id === s.id)).sort((a,b) => a.idx-b.idx);
        const now = Date.now();
        for (const line of systems) {
            if (line.width !== width || line.height !== height) {
                line.path = Rail.line(width,height,line.index);
                line.width = width;
                line.height = height;
            }
        }
        const assigned = routes.filter(r=>ordered.some(s=>s.id===r.id));
        const next = ordered.map(s => {
            const old = assigned.find(r=>r.id===s.id);
            let system = old?.system;
            if (!system) {
                const load = line=>assigned.filter(r=>r.system===line).length;
                system = systems.find(line=>!load(line));
                if (!system && systems.length<4) {
                    const index=systems.length;
                    system={index,path:Rail.line(width,height,index),width,height,openedAt:Math.max(now,systems.length ? systems[systems.length-1].openedAt+1450 : now),opening:0};
                    systems=systems.concat([system]);
                }
                if (!system) system=systems.reduce((a,b)=>load(a)<=load(b)?a:b);
            }
            let berth=old?.berth ?? 0;
            if (!old) while (assigned.some(r=>r.system===system && r.berth===berth)) berth++;
            const home=(system.path.stops[(system.index+berth)%5]+(berth ? .035+Math.floor(berth/5)*.037 : 0))%1;
            const platform=Rail.point(system.path,home);
            const present=windows.filter(w=>w.workspace_id===s.id);
            const previousIds=(old?.members??[]).map(w=>w.id);
            const members=previousIds.map(id=>present.find(w=>w.id===id)).filter(Boolean)
                .concat(present.filter(w=>!previousIds.includes(w.id)));
            const r={id:s.id,idx:s.idx,active:s.is_active,system,berth,home,platform,members,
                departAt:s.is_active ? (old?.active ? old.departAt : now+3200) : 0,
                atPlatform:old?.atPlatform??false, arrival:old?.arrival??0, phase:old?.phase ?? 0};
            if (!old) assigned.push(r);
            for (const w of members) {
                let car = cars[w.id];
                if (!car) car = cars[w.id] = {desk:s.id, born:now};
                if (car.desk !== s.id && car.pos) {
                    car.from = car.pos;
                    car.legs=Rail.transferLegs(systems,car.index,car.phase,system.index);
                    car.transfer=0;
                }
                car.desk = s.id;
                car.closed = 0;
            }
            return r;
        });
        for (const id in cars) {
            if (!next.some(r => r.members.some(w => w.id === Number(id))) && !cars[id].closed)
                cars[id].closed = now;
        }
        routes = next;
        arranging=systems.some(line=>line.opening<1);
        track.requestPaint();
        traffic.requestPaint();
    }
    function advanceLayout(now) {
        for (const line of systems)
            { const t=Math.max(0,Math.min(1,(now-line.openedAt-(line.index?250:0))/1200)); line.opening=t*t*(3-2*t); }
        arranging=systems.some(line=>line.opening<1);
        track.requestPaint();
    }
    onWorkspacesChanged: Qt.callLater(reconcile)
    onWindowsChanged: Qt.callLater(reconcile)
    onOutputChanged: Qt.callLater(reconcile)
    onWidthChanged: Qt.callLater(reconcile)
    onHeightChanged: Qt.callLater(reconcile)
    onAccentChanged: track.requestPaint()
    Component.onCompleted: reconcile()

    Canvas {
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d");
            c.reset();
            rail.districtLights=Terrain.draw(c,width,height);
            for(let district=0;district<4;district++){
                const path=Rail.line(width,height,district);
                for(const stop of path.stops){
                    const p=Rail.point(path,stop);
                    c.save();c.translate(p.x,p.y);c.rotate(p.angle);
                    c.fillStyle="#172b2f";c.fillRect(-8,5,16,7);
                    c.fillStyle="#7a8278";c.fillRect(-8,5,16,1);
                    for(let step=0;step<4;step++)c.fillRect(-5+step*3,7,1,4);
                    c.restore();
                }
            }
        }
    }
    Canvas {
        id: track
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d");
            c.reset();
            for (const line of rail.systems) {
                const p = line.path;
                c.setLineDash([]);
                c.beginPath();
                Rail.trace(c,p,line.opening);
                c.lineJoin="round";
                c.strokeStyle="#111f25"; c.lineWidth=8; c.stroke();
                c.strokeStyle=rail.inks[line.index]; c.lineWidth=4; c.stroke();
                c.strokeStyle="#334649"; c.lineWidth=2; c.stroke();
                for(const stop of p.stops){
                    if(stop>line.opening)continue;
                    const pt=Rail.point(p,stop);
                    c.save();c.translate(pt.x,pt.y);c.rotate(pt.angle);
                    c.fillStyle="#182c31";c.fillRect(-8,-8,16,5);
                    c.fillStyle=rail.inks[line.index];c.fillRect(-8,-5,16,2);c.restore();
                }
                if(line.opening>=p.exit){
                    const pt=Rail.point(p,p.exit),next=(line.index+1)%4;
                    const outgoing=Rail.point(Rail.line(width,height,next),.009);
                    const t=Math.min(1,Math.max(0,(Date.now()-(rail.systems[next]?.openedAt??Infinity))/250));
                    c.strokeStyle="#efc994";c.lineWidth=1.6;c.beginPath();c.moveTo(pt.x,pt.y);
                    c.lineTo(outgoing.x,outgoing.y+(1-t)*4);c.stroke();
                    c.fillStyle=t===1?"#a2d3a8":"#c77759";c.fillRect(pt.x+1,pt.y-7,3,3);
                }
            }
            for (const r of rail.routes) {
                if (r.system.opening<r.home) continue;
                const pt=r.platform,ink=r.active?"#ffdb8e":rail.inks[r.system.index];
                c.fillStyle="#10232a";c.fillRect(pt.x-23,pt.y-25,46,20);
                c.fillStyle=ink;c.fillRect(pt.x-23,pt.y-6,46,2);
                c.font="bold 11px sans-serif";c.fillText("▸  "+String(r.idx).padStart(2,"0"),pt.x-16,pt.y-11);

            }
        }
    }
    function sprite(c,pt,id,engine,marked,alpha) {
        c.save();
        c.translate(Math.round(pt.x),Math.round(pt.y)); c.rotate(pt.angle);
        c.globalAlpha = alpha;
        c.fillStyle="#101e24";c.fillRect(-8,-4,16,8);
        c.fillStyle=engine?"#ffe3a6":"#c6dbcb";c.beginPath();c.moveTo(-7,-3);c.lineTo(5,-3);
        c.lineTo(engine?9:7,0);c.lineTo(5,3);c.lineTo(-7,3);c.closePath();c.fill();
        c.fillStyle="#415659";c.fillRect(-4,-2,6,4);
        c.fillStyle="#fff3bc";c.fillRect(5,-1,3,2);
        if(marked){c.fillStyle="#ffad65";c.fillRect(-5,-5,6,2);}
        c.restore();
    }
    function illuminate(c,lights,x,y,radius,strength,ring){
        for(const lamp of lights){
            const d=Math.hypot(x-lamp.x,y-lamp.y);
            const a=ring?1-Math.abs(radius-d)/20:1-d/radius;
            if(a<=0)continue;
            c.fillStyle="rgba(255,211,141,"+(strength*a)+")";c.fillRect(lamp.x,lamp.y,3,2);
        }
    }
    function hit(x,y) {
        return hits.find(h => Math.abs(x-h.x)<h.w && Math.abs(y-h.y)<h.h) || null;
    }
    Canvas {
        id: traffic
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d");
            c.reset();
            const now = Date.now(), dt = Math.min(.1,(now-rail.previous)/1000);
            rail.previous = now;
            if (pointer.containsMouse && !rail.hit(pointer.mouseX,pointer.mouseY)) {
                const x=pointer.mouseX, y=pointer.mouseY;
                const glow=c.createRadialGradient(x,y,0,x,y,85);
                glow.addColorStop(0,"rgba(182,192,202,0.09)");
                glow.addColorStop(1,"transparent");
                c.fillStyle=glow;
                c.fillRect(x-85,y-85,170,170);
                rail.illuminate(c,rail.districtLights,x,y,115,.9,false);
            }
            if (rail.echo) {
                const t=Math.min(1,(now-rail.echo.start)/950);
                const radius=8+Math.min(width,height)*.34*t;
                c.save();
                c.globalAlpha=.46*(1-t);
                c.strokeStyle="#ddd"; c.lineWidth=1;
                c.setLineDash([3,5]); c.beginPath();
                c.arc(rail.echo.x,rail.echo.y,radius,0,Math.PI*2);
                c.stroke(); c.restore();
                rail.illuminate(c,rail.districtLights,rail.echo.x,rail.echo.y,radius,1-t,true);
                if (t===1) rail.echo=null;
            }
            for(const row of [4,10,16]){
                const t=((now/3500+row*3)%34)-2;
                const a=Terrain.corner(Math.floor(t),row),b=Terrain.corner(Math.floor(t)+1,row);
                const f=t-Math.floor(t);
                c.fillStyle="#d5c497";c.fillRect((a[0]+(b[0]-a[0])*f)*width/1200,(a[1]+(b[1]-a[1])*f)*height/750,2,1);
            }
            const targets = [];
            for (const r of rail.routes) {
                const p = r.system.path;
                if(r.system.opening>=r.home)targets.push({r,x:r.platform.x,y:r.platform.y-14,w:24,h:12});
                if (r.system.opening<1) {
                    for(const w of r.members) {
                        const car=rail.cars[w.id];
                        if(car.from) rail.sprite(c,car.from,w.id,false,w.is_focused,1);
                    }
                    continue;
                }
                if (r.active && now < r.departAt) {
                    if (r.phase > .5) r.phase -= 1;
                    r.phase *= Math.exp(-7*dt);
                    if (Math.abs(r.phase)<.00015) r.phase=0;
                } else r.phase = (r.phase + dt*22/p.length + 1)%1;
                const engine = Rail.point(p,r.home+r.phase);
                rail.sprite(c,engine,0,true,false,1);
                targets.push({r,x:engine.x,y:engine.y,w:15,h:10});
                r.members.forEach((w,i) => {
                    const car = rail.cars[w.id];
                    const age = Math.min(1,(now-car.born)/460);
                    const spacing = Math.min(18,p.length/(r.members.length+2));
                    const phase=((r.home+r.phase-((i+1)*spacing+24*(1-age)*(1-age))/p.length)%1+1)%1;
                    let pt=Rail.point(p,phase);
                    car.index=r.system.index;
                    car.phase=phase;
                    if(car.from) {
                        if(!car.transfer) car.transfer=now;
                        const t=Math.min(1,(now-car.transfer)/2800);
                        const sample=Rail.transferPoint(rail.systems,car.legs,phase,t);
                        pt=sample.pt; car.index=sample.index; car.phase=sample.phase;
                        if(t===1)car.from=null;
                    }
                    car.pos = pt;
                    rail.sprite(c,pt,w.id,false,w.is_focused,age);
                    targets.push({r,x:pt.x,y:pt.y,w:13,h:10});
                });
                const distance=Math.hypot(engine.x-r.platform.x,engine.y-r.platform.y);
                if(distance<85){
                    if(distance<9 && !r.atPlatform)r.arrival=now;
                    r.atPlatform=distance<9;
                    const crowd=r.arrival && now-r.arrival<3800 ?
                        Math.max(0,6-Math.floor((now-r.arrival)/160)) : Math.min(6,Math.floor((85-distance)/9));
                    c.fillStyle="#dbbe8e";
                    for(let k=0;k<crowd;k++)c.fillRect(r.platform.x-12+k*4,r.platform.y-3+k%2,1.5,1.5);
                }
                if(r.system.index===3 && engine.x<width*.28 && engine.y>height*.70){
                    c.fillStyle="#dbab6b";for(let k=0;k<5;k++)c.fillRect(width*.15+k*5,height*.76,2,2);
                }
            }
            for (const id in rail.cars) {
                const car=rail.cars[id];
                if (!car.closed) continue;
                const t=(now-car.closed)/400;
                if (t>=1 || !car.pos) { delete rail.cars[id]; continue; }
                const pt=car.pos;
                rail.sprite(c,{x:pt.x-18*t*Math.cos(pt.angle),y:pt.y-18*t*Math.sin(pt.angle),angle:pt.angle},Number(id),false,false,1-t);
            }
            rail.hits=targets;
            rail.hover=pointer.containsMouse ? rail.hit(pointer.mouseX,pointer.mouseY) : null;
        }
    }
    Timer {
        interval: rail.arranging ? 16 : 40
        repeat: true
        running: rail.visible && !rail.paused
        onTriggered: {
            if (rail.arranging) rail.advanceLayout(Date.now());
            traffic.requestPaint();
        }
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: rail.hover ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: mouse => {
            const h=rail.hit(mouse.x,mouse.y);
            if (h) rail.workspaceClicked(h.r.id);
            else rail.echo={x:mouse.x,y:mouse.y,start:Date.now()};
        }
    }
    Text {
        visible: !!rail.hover
        x: Math.max(4,Math.min(parent.width-width-4,pointer.mouseX+14))
        y: Math.max(4,pointer.mouseY-height-12)
        color: "#ddd"; font.family: "monospace"; font.pixelSize: 11
        text: rail.hover ? "Workspace "+rail.hover.r.idx+" · "+rail.hover.r.members.length+
            (rail.hover.r.members.length===1 ? " window" : " windows") : ""
    }
}
