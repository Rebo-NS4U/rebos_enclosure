import QtQuick
import "RailGeometry.js" as Rail

Rectangle {
    id: rail
    color: "black"
    required property var workspaces
    required property var windows
    required property string output
    required property color accent
    property bool paused: false
    signal workspaceClicked(double desk)
    property var routes: []
    property var cars: ({})
    property var hits: []
    property var hover: null
    property var sparks: ({})
    property double previous: 0

    function reconcile() {
        if (!width || !height || !workspaces || !windows) return;
        const ordered = workspaces.filter(s => s.output === output &&
            windows.some(w => w.workspace_id === s.id)).sort((a,b) => a.idx-b.idx);
        const now = Date.now();
        const next = ordered.map((s,i) => {
            const old = routes.find(r => r.id === s.id);
            const path = Rail.loop(width,height,i,ordered.length);
            const members = windows.filter(w => w.workspace_id === s.id).sort((a,b) => a.id-b.id);
            const r = {id:s.id, idx:s.idx, active:s.is_active, path, members,
                departAt:s.is_active ? (old?.active ? old.departAt : now+3200) : 0,
                phase:old ? old.phase : (s.is_active ? 0 : .14 + .11*(i%5))};
            for (const w of members) {
                let car = cars[w.id];
                if (!car) car = cars[w.id] = {desk:s.id, born:now};
                if (car.desk !== s.id && car.pos) {
                    car.from = car.pos;
                    car.transfer = now;
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
        track.requestPaint();
        traffic.requestPaint();
    }
    onWorkspacesChanged: Qt.callLater(reconcile)
    onWindowsChanged: Qt.callLater(reconcile)
    onOutputChanged: Qt.callLater(reconcile)
    onWidthChanged: Qt.callLater(reconcile)
    onHeightChanged: Qt.callLater(reconcile)
    onAccentChanged: track.requestPaint()
    Component.onCompleted: reconcile()

    Canvas {
        id: track
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d");
            c.reset();
            for (const r of rail.routes) {
                const p = r.path;
                c.fillStyle = "#a6a6a6";
                for (let d=0; d<p.length; d+=5) {
                    const pt = Rail.point(p,d/p.length);
                    c.fillRect(Math.round(pt.x),Math.round(pt.y),1,1);
                }
                c.fillStyle = r.active ? rail.accent : "#686868";
                c.fillRect(p.stop-21,p.y-10,42,2);
                c.fillRect(p.stop+19,p.y-14,2,4);
                c.font = "10px monospace";
                c.fillText(String(r.idx).padStart(2,"0"),p.stop-21,p.y-15);
                // A short parallel passing siding branches off the lower straight.
                c.strokeStyle = "#555";
                c.setLineDash([1,4]);
                c.beginPath();
                const sx = p.x + width*.18, sy = p.y+p.h;
                c.moveTo(sx,sy); c.lineTo(sx+10,sy+10);
                c.lineTo(sx+width*.13,sy+10); c.lineTo(sx+width*.13+10,sy);
                c.stroke();
            }
        }
    }
    function sprite(c,pt,id,engine,marked,alpha) {
        c.save();
        c.translate(Math.round(pt.x),Math.round(pt.y)); c.rotate(pt.angle);
        c.globalAlpha = alpha;
        c.fillStyle = "#cecece";
        c.fillRect(-7,-3,engine ? 11 : 14,6);
        if (engine) { c.fillRect(4,-1,4,4); c.fillRect(-6,-5,6,2); }
        c.fillStyle = "#161616";
        for (let x=-5; x<4; x+=3) {
            c.fillRect(x,-2,2,2);
            c.fillRect(x+1,1+(id%2),1,1);
        }
        if (marked) { c.fillStyle = accent; c.fillRect(-3,-7,6,2); }
        c.restore();
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
            const targets = [];
            for (const r of rail.routes) {
                const p = r.path;
                if (r.active && now < r.departAt) {
                    if (r.phase > .5) r.phase -= 1;
                    r.phase *= Math.exp(-7*dt);
                    if (Math.abs(r.phase)<.00015) r.phase=0;
                } else r.phase = (r.phase + dt*7/p.length + 1)%1;
                const engine = Rail.point(p,r.phase);
                rail.sprite(c,engine,0,true,false,1);
                targets.push({r,x:p.stop,y:p.y-10,w:27,h:14},{r,x:engine.x,y:engine.y,w:12,h:9});
                r.members.forEach((w,i) => {
                    const car = rail.cars[w.id];
                    const age = Math.min(1,(now-car.born)/460);
                    const spacing = Math.min(19,p.length/(r.members.length+2));
                    const pt = Rail.point(p,r.phase-((i+1)*spacing+24*(1-age)*(1-age))/p.length);
                    if (car.from) {
                        const t = Math.min(1,(now-car.transfer)/620);
                        // Draw the temporary crossover and traverse its three legs.
                        const mid = (car.from.x+pt.x)/2;
                        c.strokeStyle="#737373"; c.setLineDash([1,4]); c.beginPath();
                        c.moveTo(car.from.x,car.from.y); c.lineTo(mid-10,car.from.y);
                        c.lineTo(mid+10,pt.y); c.lineTo(pt.x,pt.y); c.stroke();
                        const xs=[car.from.x,mid-10,mid+10,pt.x], ys=[car.from.y,car.from.y,pt.y,pt.y];
                        const u=t*t*(3-2*t)*3, k=Math.min(2,Math.floor(u));
                        pt.x=xs[k]+(xs[k+1]-xs[k])*(u-k);
                        pt.y=ys[k]+(ys[k+1]-ys[k])*(u-k);
                        if (t<1) pt.angle=Math.atan2(ys[k+1]-ys[k],xs[k+1]-xs[k]);
                        else car.from=null;
                    }
                    car.pos = pt;
                    rail.sprite(c,pt,w.id,false,w.is_focused,age);
                    targets.push({r,x:pt.x,y:pt.y,w:10,h:9});
                });
                for (let i=0;i<8;i++) {
                    const pt=Rail.point(p,(i+.35)/8), key=r.id+"/"+i;
                    const age=now-(rail.sparks[key] || 0);
                    c.fillStyle=age<280 && Math.floor(age/55)%2===0 ? "#fff" : "#515151";
                    c.fillRect(pt.x-1,pt.y-1,3,3);
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
    Timer { interval: 40; repeat: true; running: rail.visible && !rail.paused; onTriggered: traffic.requestPaint() }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: rail.hover ? Qt.PointingHandCursor : Qt.ArrowCursor
        onPositionChanged: mouse => {
            for (const r of rail.routes) for (let i=0;i<8;i++) {
                const pt=Rail.point(r.path,(i+.35)/8);
                if (Math.hypot(pt.x-mouse.x,pt.y-mouse.y)<34) rail.sparks[r.id+"/"+i]=Date.now();
            }
        }
        onClicked: mouse => {
            const h=rail.hit(mouse.x,mouse.y);
            if (h) rail.workspaceClicked(h.r.id);
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
