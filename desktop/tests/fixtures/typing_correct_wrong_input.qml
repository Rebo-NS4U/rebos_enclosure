import QtQuick
import Quickshell
import QtTest
ShellRoot {
 PanelWindow {
  implicitWidth:960; implicitHeight:800
  TestEvent { id: keys }
  TypingMenu { id: menu; anchors.fill:parent }
 }
 function find(item,name) {
  if (item.objectName===name) return item;
  for (const child of item.children || []) { const found=find(child,name); if(found)return found; }
  return null;
 }
 Timer {
  interval:350; running:true; repeat:true
  property int phase:0
  onTriggered: {
   try {
    const input=find(menu,"typing-input");
    if(phase===0) {
     menu.practicing=true; menu.pageSource="Abc words to type. ".repeat(100);
     menu.fitPage(); menu.focusPassage(); phase++; return;
    }
    if(phase===1) {
     keys.keyClickChar("A",Qt.ShiftModifier,0);
     const a=find(menu,"typing-character-0");
     if(input.text!=="A" || a.incorrect || a.failedFeedback || menu.failureEvents) throw Error("Correct A rejected");
     keys.keyClickChar("x",0,0);
     const b=find(menu,"typing-character-1");
     if(!b.incorrect || !b.failedFeedback || menu.failureEvents!==1) throw Error("Wrong x accepted");
     keys.keyClick(Qt.Key_Backspace,0,0);
     keys.keyClickChar("b",0,0);
     if(b.incorrect || b.failedFeedback || menu.failureEvents!==1) throw Error("Corrected b rejected");
     keys.keyClickChar("c",0,0);
     if(find(menu,"typing-character-2").incorrect || menu.failureEvents!==1) throw Error("Correct c rejected");
     console.log("PASS: real correct, wrong and corrected keys produce distinct feedback"); Qt.quit();
    }
   } catch(e) { console.error(e);Qt.exit(1); }
  }
 }
}
