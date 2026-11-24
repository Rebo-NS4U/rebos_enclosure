import QtQuick
import "RailGeometry.js" as Rail
import "RailTerrain.js" as Terrain

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
    property bool arranging: false
    property var hits: []
    property var hover: null
    property var sparks: ({})
    property var districtLights: []
    property var echo: null
    property double previous: 0

    function reconcile() {
        if (!width || !height || !workspaces || !windows) return;
        const ordered = workspaces.filter(s => s.output === output &&
            windows.some(w => w.workspace_id === s.id)).sort((a,b) => a.idx-b.idx);
        const now = Date.now();
        const next = ordered.map((s,i) => {
            const old = routes.find(r => r.id === s.id);
            const layoutKey=[width,height,i,ordered.length].join("/");
            const unchanged=old?.layoutKey===layoutKey;
            const destination=unchanged ? old.destination : Rail.loop(width,height,i,ordered.length);
            const path=old?.path ?? destination;
            const members = windows.filter(w => w.workspace_id === s.id).sort((a,b) => a.id-b.id);
            const r = {id:s.id, idx:s.idx, active:s.is_active, path, members, layoutKey, destination,
                origin:unchanged ? old.origin : old?.path,
                layoutStart:unchanged ? old.layoutStart : now,
                opening:old ? old.opening : 0,
                openedAt:old ? old.openedAt : now,
                departAt:s.is_active ? (old?.active ? old.departAt : now+3200) : 0,
                phase:old ? old.phase : 0};
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
        arranging=next.some(r=>r.origin || r.opening<1);
        track.requestPaint();
        traffic.requestPaint();
    }
    function advanceLayout(now) {
        let moving=false;
        for (const r of routes) {
            if (r.origin) {
                const t=Math.min(1,(now-r.layoutStart)/520);
                r.path=t===1 ? r.destination : Rail.blend(r.origin,r.destination,t*t*(3-2*t));
                if (t===1) r.origin=null;
                else moving=true;
            }
            if (r.opening<1) {
                const t=Math.min(1,(now-r.openedAt)/650);
                r.opening=t*t*(3-2*t);
                if (t<1) moving=true;
            }
        }
        arranging=moving;
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
            Terrain.draw(c,width,height);
            rail.districtLights = Terrain.drawDistrict(c,width,height);
        }
    }
    Canvas {
        id: track
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d");
            c.reset();
            for (const r of rail.routes) {
                const p = r.path;
                c.setLineDash([]);
                c.beginPath();
                Rail.trace(c,p,r.opening);
                c.strokeStyle="#292929"; c.lineWidth=8; c.stroke();
                c.strokeStyle="#060606"; c.lineWidth=6; c.stroke();
                c.strokeStyle="#d0d0d0"; c.lineWidth=1.4;
                c.setLineDash([2,4]); c.stroke();
                c.setLineDash([]);
                const ink=r.active ? rail.accent : "#888888";
                const labelSize=Math.min(40,Math.max(12,height*.54/rail.routes.length-30));
                c.font="bold "+labelSize+"px monospace";
                c.fillStyle=ink;
                c.fillText(String(r.idx).padStart(2,"0"),p.stop-44,p.y-22);
                c.fillRect(p.stop-42,p.y-12,84,3);
                for (let dx=-42;dx<40;dx+=5)
                    c.fillRect(p.stop+dx,p.y-8,2,2);
                c.fillStyle="#414141";
                c.fillRect(p.stop+34,p.y-31,1,18);
                c.fillStyle="#141414";
                c.fillRect(p.stop+29,p.y-42,11,16);
                c.fillStyle=ink;
                c.fillRect(p.stop+32,p.y-39,5,5);
                c.fillStyle="#333333";
                c.fillRect(p.stop+32,p.y-32,5,3);
                c.lineWidth=1;
                // The lower siding appears once the main line has reached it.
                c.globalAlpha=Math.max(0,(r.opening-.88)/.12);
                // A short parallel passing siding branches off the lower straight.
                c.strokeStyle = "#888";
                c.setLineDash([1,4]);
                c.beginPath();
                const sx = p.x + width*.18, sy = p.sidingY;
                c.moveTo(sx,sy); c.lineTo(sx+10,sy+10);
                c.lineTo(sx+width*.13,sy+10); c.lineTo(sx+width*.13+10,sy);
                c.stroke();
                c.globalAlpha=1;
            }
        }
    }
    function sprite(c,pt,id,engine,marked,alpha) {
        c.save();
        c.translate(Math.round(pt.x),Math.round(pt.y)); c.rotate(pt.angle);
        c.globalAlpha = alpha;
        c.scale(1.45,1.45);
        if (engine) {
            const light=c.createLinearGradient(6,0,42,0);
            light.addColorStop(0,"#505050"); light.addColorStop(1,"transparent");
            c.fillStyle=light; c.beginPath(); c.moveTo(6,-1); c.lineTo(42,-6);
            c.lineTo(42,6); c.lineTo(6,1); c.fill();
        }
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
            if (pointer.containsMouse && !rail.hit(pointer.mouseX,pointer.mouseY)) {
                const x=pointer.mouseX, y=pointer.mouseY;
                const glow=c.createRadialGradient(x,y,0,x,y,85);
                glow.addColorStop(0,"rgba(182,192,202,0.09)");
                glow.addColorStop(1,"transparent");
                c.fillStyle=glow;
                c.fillRect(x-85,y-85,170,170);
                Terrain.illuminate(c,rail.districtLights,x,y,115,.9,false);
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
                Terrain.illuminate(c,rail.districtLights,rail.echo.x,rail.echo.y,radius,1-t,true);
                if (t===1) rail.echo=null;
            }
            const targets = [];
            for (const r of rail.routes) {
                const p = r.path;
                if (r.active && now < r.departAt) {
                    if (r.phase > .5) r.phase -= 1;
                    r.phase *= Math.exp(-7*dt);
                    if (Math.abs(r.phase)<.00015) r.phase=0;
                } else r.phase = (r.phase + dt*7/p.length + 1)%1;
                const engine = Rail.point(p,r.phase);
                rail.sprite(c,engine,0,true,false,Math.min(1,r.opening*3));
                targets.push({r,x:p.stop,y:p.y-10,w:46,h:23},{r,x:engine.x,y:engine.y,w:15,h:10});
                r.members.forEach((w,i) => {
                    const car = rail.cars[w.id];
                    const age = Math.min(1,(now-car.born)/460);
                    const spacing = Math.min(25,p.length/(r.members.length+2));
                    const pt = Rail.point(p,r.phase-((i+1)*spacing+24*(1-age)*(1-age))/p.length);
                    if (car.from) {
                        const t = Math.min(1,(now-car.transfer)/620);
                        // The turnout leaves the old rail and joins the new one tangentially.
                        const start=car.from;
                        const reach=Math.min(140,Math.hypot(pt.x-start.x,pt.y-start.y)*.42);
                        const ax=start.x+reach*Math.cos(start.angle), ay=start.y+reach*Math.sin(start.angle);
                        const bx=pt.x-reach*Math.cos(pt.angle), by=pt.y-reach*Math.sin(pt.angle);
                        c.save();
                        c.globalAlpha=Math.min(1,t*8,(1-t)*8);
                        c.strokeStyle="#737373"; c.setLineDash([1,4]); c.beginPath();
                        c.moveTo(start.x,start.y); c.bezierCurveTo(ax,ay,bx,by,pt.x,pt.y); c.stroke();
                        c.restore();
                        if (t<1) {
                            const u=t*t*(3-2*t), v=1-u;
                            pt.angle=Math.atan2(v*v*(ay-start.y)+2*v*u*(by-ay)+u*u*(pt.y-by),
                                                v*v*(ax-start.x)+2*v*u*(bx-ax)+u*u*(pt.x-bx));
                            pt.x=v*v*v*start.x+3*v*v*u*ax+3*v*u*u*bx+u*u*u*pt.x;
                            pt.y=v*v*v*start.y+3*v*v*u*ay+3*v*u*u*by+u*u*u*pt.y;
                        } else car.from=null;
                    }
                    car.pos = pt;
                    rail.sprite(c,pt,w.id,false,w.is_focused,age*(car.from ? 1 : Math.min(1,r.opening*3)));
                    targets.push({r,x:pt.x,y:pt.y,w:13,h:10});
                });
                for (let i=0;i<8;i++) {
                    const phase=(i+.35)/8;
                    if (Math.min(phase,1-phase)>r.opening/2) continue;
                    const pt=Rail.point(p,phase), key=r.id+"/"+i;
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
        onPositionChanged: mouse => {
            for (const r of rail.routes) for (let i=0;i<8;i++) {
                const pt=Rail.point(r.path,(i+.35)/8);
                if (Math.hypot(pt.x-mouse.x,pt.y-mouse.y)<34) rail.sparks[r.id+"/"+i]=Date.now();
            }
        }
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
