"""Reproduce rejected settings and same-length chat switches in isolated real QML."""
from pathlib import Path
import shutil
import unittest

from test_visual_polish import run_qml

ROOT = Path(__file__).resolve().parents[2] / 'system/apps'


@unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
class ReleaseFailureTests(unittest.TestCase):
    def run_case(self, app, harness, **options):
        status, output = run_qml(ROOT / app, harness, **options)
        self.assertEqual(status, 0, output[-6500:])
        self.assertIn('FAILURE REGRESSION PASSED', output)

    def test_settings_rejection_queue_stale_replies_and_disconnect(self):
        self.run_case('media/ui', '''import QtQuick
import QtTest
import Quickshell
ShellRoot {
 FloatingWindow {visible:true
  TestCase {id:test;when:false
   function check(ok,message){if(!ok)throw Error(message);}
  }
  Timer {interval:400;running:true;onTriggered:{
   try {
    let c=Qt.createComponent("AnimeMenu.qml");
    if(c.status!==Component.Ready)throw Error(c.errorString());
    let menu=c.createObject(null);
    menu.receive(JSON.stringify({event:"ready",settings:{volume:80,quality:"1080p",caption_delay:0}}));test.wait(40);
    menu.updateSetting("volume",5);let first=menu.settingsInFlight;
    test.check(first>0,"Change needs an acknowledgement");
    menu.updateSetting("quality","720p");menu.updateSetting("volume",10);
    test.check(menu.settingsInFlight===first&&menu.pendingSettings.volume===10,"Changes coalesce behind the outstanding save");
    menu.receive(JSON.stringify({event:"error",action:"settings",request:first,text:"disk full",settings:{volume:80,quality:"1080p",caption_delay:0}}));test.wait(40);
    let second=menu.settingsInFlight;
    test.check(second>first&&menu.settings.volume===10,"Newer user changes survive an earlier rejection");
    test.check(menu.inFlightSettings.quality==="720p"&&menu.inFlightSettings.volume===10,"Only the queued patch is sent next");
    menu.receive(JSON.stringify({event:"settings",request:first,data:{volume:5,quality:"1080p"}}));test.wait(40);
    test.check(menu.settings.volume===10&&menu.settingsInFlight===second,"Stale success cannot replace newer values");
    menu.receive(JSON.stringify({event:"settings",request:second,data:{volume:10,quality:"720p",caption_delay:0}}));test.wait(40);
    test.check(menu.settingsInFlight===0&&menu.confirmedSettings.volume===10,"Successful save becomes canonical");
    menu.updateSetting("volume",5);let rejected=menu.settingsInFlight;
    menu.receive(JSON.stringify({event:"error",action:"settings",request:rejected,text:"disk full"}));test.wait(40);
    test.check(menu.settings.volume===10&&menu.settingsError==="disk full","Old backends without error snapshots still roll back");
    menu.updateSetting("caption_delay",2);let lost=menu.settingsInFlight;
    menu.receive(JSON.stringify({event:"connection-lost"}));test.wait(40);
    test.check(!menu.ready&&menu.settings.caption_delay===0&&!menu.settingsInFlight,"Disconnect discards unconfirmed changes");
    menu.updateSetting("volume",5);
    test.check(menu.settings.volume===10&&!menu.settingsInFlight,"Offline controls cannot commit local-only settings");
    menu.receive(JSON.stringify({event:"settings",request:lost,data:{volume:5,caption_delay:2}}));test.wait(40);
    test.check(menu.settings.volume===10,"Late disconnected save cannot overwrite confirmed state");
    menu.receive(JSON.stringify({event:"ready",settings:{volume:70,quality:"720p",caption_delay:0}}));test.wait(40);
    test.check(menu.settings.volume===70&&menu.settingsError===""&&Object.keys(menu.pendingSettings).length===0,"Reconnect refreshes actual saved values without replay");
    menu.destroy();console.log("FAILURE REGRESSION PASSED");Qt.quit();
   }catch(e){console.error(e);Qt.exit(1);}
  }}
 }
}''')

    def test_chat_identity_resets_interaction_but_stream_updates_do_not(self):
        harness = '''import QtQuick
import QtTest
import Quickshell
import qs.config
import qs.modules.globals
import qs.modules.services
import qs.modules.sidebar
ShellRoot {
 FloatingWindow {visible:true;implicitWidth:1200;implicitHeight:1000
  Item {id:host;width:1100;height:950}
  TestCase {id:test;when:false
   function check(ok,message){if(!ok)throw Error(message);}
  }
  Timer {interval:900;running:true;onTriggered:{
   try {
    Config.ai.enabled=true;Config.ai.sidebarEnabled=true;
    Ai.addSession("default","codex");Ai.activeSession=Ai;Ai.currentChatId="one";
    Ai.currentChat=[{id:"reply",role:"assistant",content:"Original reply"},
     {id:"tool",role:"assistant",content:"",functionCall:{name:"run_shell_command",args:{command:"echo one"}},functionApproved:true,toolStatus:"completed"}];
    GlobalStates.assistantScreenName=Quickshell.screens[0].name;GlobalStates.assistantVisible=true;
    let c=Qt.createComponent("modules/sidebar/AssistantSidebar.qml");
    if(c.status!==Component.Ready)throw Error(c.errorString());
    let sidebar=c.createObject(host,{targetScreen:Quickshell.screens[0],tiled:true});test.wait(250);
    let first=test.findChild(sidebar,"assistantMessage_default_0");
    let tool=test.findChild(sidebar,"assistantMessage_default_1");
    first.isEditing=true;first.retryMode=true;tool.toolExpanded=true;
    test.findChild(sidebar,"assistantToolDetails_1").clicked();
    let same=Ai.currentChat.slice();same[0]=Object.assign({},same[0],{content:"Streamed reply"});Ai.currentChat=same;test.wait(80);
    test.check(first.isEditing&&tool.toolDetailsExpanded,"Streaming keeps existing widget state");
    sidebar.currentPage.retryIndex=0;
    Ai.currentChatId="two";
    Ai.currentChat=[{id:"reply",role:"assistant",content:"Different chat"},
     {id:"tool",role:"assistant",content:"",functionCall:{name:"run_shell_command",args:{command:"echo two"}},functionApproved:true,toolStatus:"completed"}];test.wait(100);
    test.check(!first.isEditing&&!first.retryMode&&!tool.toolExpanded&&!tool.toolDetailsExpanded,"Chat switch clears all local interaction state");
    test.check(sidebar.currentPage.retryIndex===-1,"Chat switch cancels the old model-retry target");
    first.isEditing=true;let replacement=Ai.currentChat.slice();replacement[0]=Object.assign({},replacement[0],{id:"replacement"});Ai.currentChat=replacement;test.wait(80);
    test.check(!first.isEditing,"Message identity replacement clears editing within a chat");
    console.log("FAILURE REGRESSION PASSED");Qt.quit();
   }catch(e){console.error(e);Qt.exit(1);}
  }}
 }
}'''
        for app in ('assistant', 'shell'):
            with self.subTest(app=app):
                self.run_case(app, harness, assistant=True)
