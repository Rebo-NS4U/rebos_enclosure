import QtQuick
import QtTest
import "../../../system/apps/shell/modules/widgets/dashboard/wallpapers"
Item {
    width: 960; height: 600
    NightRail {
        id: scene
        anchors.fill: parent
        output: "A"; accent: "#845ebd"
        workspaces: [{id:2,idx:1,output:"A",is_active:true},{id:7,idx:2,output:"A"}, {id:9,idx:1,output:"B"}]
        windows: [{id:42,workspace_id:2,is_focused:true},{id:54,workspace_id:2},{id:55,workspace_id:7},{id:12,workspace_id:9}]
    }
    SignalSpy { id: spy; target: scene; signalName: "workspaceClicked" }
    TestCase {
        name: "NightRail"; when: windowShown
        function test_transitions() {
            tryCompare(scene.routes,"length",2)
            wait(550)
            const r=scene.routes[1], start=r.phase
            wait(160)
            verify(r.phase>start)
            mouseMove(scene,r.path.stop,r.path.y-10)
            tryVerify(()=>scene.hover && scene.hover.r.id===7)
            mouseClick(scene,r.path.stop,r.path.y-10)
            compare(spy.signalArguments[0][0],7)
            scene.workspaces=scene.workspaces.map(s=>Object.assign({},s,{is_active:s.id===7}))
            wait(900)
            verify(Math.abs(scene.routes[1].phase)<.001)
            const car=scene.cars[54]
            scene.windows=scene.windows.concat([{id:60,workspace_id:2}])
            wait(80)
            verify(Date.now()-scene.cars[60].born<450)
            scene.windows=scene.windows.map(w=>w.id===54?{id:54,workspace_id:7}:w)
            wait(100)
            compare(scene.cars[54],car)
            verify(!!car.from)
            wait(650)
            verify(!car.from)
            scene.windows=scene.windows.filter(w=>w.id!==60)
            wait(90)
            verify(!!scene.cars[60].closed)
            wait(430)
            verify(!scene.cars[60])
        }
    }
}
