import QtQuick
import QtTest
import "../../../system/apps/shell/modules/widgets/dashboard/wallpapers"
import "../../../system/apps/shell/modules/widgets/dashboard/wallpapers/ReachLines.js" as Rail
Item {
    width: 1200; height: 750
    NightRailCity { id: city; anchors.fill: parent; windows: []; workspaces: []; output: "A" }
    SignalSpy {id: switches;target:city;signalName:"workspaceClicked"}
    TestCase {
        name: "VesperReach"; when: windowShown
        function snapshot(name) {
            wait(100)
            grabImage(city).save("/tmp/night-rail-"+name+".png")
        }
        function test_service(){
            tryVerify(()=>city.districtLights.length>0)
            snapshot("survey")
            for(let i=1;i<=5;i++){
                city.workspaces=city.workspaces.concat([{id:i,idx:i,output:"A",is_active:i===1}])
                city.windows=city.windows.concat([{id:i,workspace_id:i}])
                tryCompare(city,"arranging",i<=4)
                if(i===1 || i===4) {
                    tryCompare(city,"arranging",false,6000)
                    snapshot(String(i))
                }
                tryVerify(()=>city.routes.length===i)
                compare(city.systems.length,Math.min(4,i))
            }
            const original=city.routes.map(r=>[r.id,r.system.index,r.berth])
            city.workspaces=city.workspaces.map(w=>Object.assign({},w,{idx:10-w.idx}))
                .concat([{id:77,idx:1,output:"B"}])
            city.windows=city.windows.concat([{id:77,workspace_id:77}])
            tryVerify(()=>city.routes[0].idx===5)
            compare(city.routes.length,5)
            for(const [id,index,berth] of original){
                const r=city.routes.find(route=>route.id===id)
                compare(r.system.index,index)
                compare(r.berth,berth)
            }
            const fifth=city.routes.find(r=>r.id===5),first=city.routes.find(r=>r.id===1)
            compare(fifth.system,first.system)
            verify(fifth.home!==first.home)
            for(let i=0;i<4;i++){
                const a=Rail.point(city.systems[i].path,city.systems[i].path.exit)
                const b=Rail.point(city.systems[(i+1)%4].path,0)
                verify(Math.hypot(a.x-b.x,a.y-b.y)<.01)
            }
            city.paused=true
            wait(120)
            const phase=fifth.phase
            wait(150)
            compare(fifth.phase,phase)
            city.paused=false
            tryVerify(()=>fifth.phase!==phase)
            const car=city.cars[1]
            city.windows=city.windows.map(w=>w.id===1?{id:1,workspace_id:3}:w)
            tryVerify(()=>car.legs?.length===3)
            compare(car.legs.map(l=>l.index).join(","),"0,1,2")
            tryVerify(()=>!car.from,4000)
            compare(car.index,2)
            compare(city.systems.length,4)
            const r=city.routes[0]
            mouseMove(city,r.platform.x,r.platform.y-12)
            tryVerify(()=>city.hover?.r.id===r.id)
            mouseClick(city,r.platform.x,r.platform.y-12)
            compare(switches.signalArguments[0][0],r.id)
            mouseClick(city,25,50)
            verify(!!city.echo)
            city.workspaces=city.workspaces.map(w=>Object.assign({},w,{is_active:w.id===r.id}))
            tryVerify(()=>Math.abs(city.routes[0].phase)<.001)
            city.windows=city.windows.filter(w=>w.id!==1)
            tryVerify(()=>!city.cars[1])
        }
    }
}
