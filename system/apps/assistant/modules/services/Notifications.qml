pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
Singleton {
    id: root
    property list<QtObject> list: []
    property Component notificationFactory: Component {
        Process {
            id: notice
            property var details
            property int notificationId: 0
            readonly property string replaceKey: details.replaceKey
            command: ["notify-send", "--print-id", "--app-name=Assistant", "--icon=dialog-question", "--expire-time=10000", "--action=answer=Answer", "--wait", details.summary, details.body]
            stdout: SplitParser {
                onRead: data => {
                    if (/^\d+$/.test(data.trim())) notice.notificationId = Number(data.trim());
                    else if (data.trim() === "answer") notice.details.actionHandlers.answer();
                }
            }
            onExited: Qt.callLater(() => {
                root.list = root.list.filter(item => item !== notice);
                notice.destroy();
            })
        }
    }
    function notifyInternal(details) {
        let notice = notificationFactory.createObject(root, {details: details});
        if (notice) {
            list = list.concat([notice]);
            notice.running = true;
        }
    }
    function discardNotifications(ids) {
        for (let notificationId of ids) {
            if (notificationId > 0) Quickshell.execDetached(["gdbus", "call", "--session", "--dest", "org.freedesktop.Notifications", "--object-path", "/org/freedesktop/Notifications", "--method", "org.freedesktop.Notifications.CloseNotification", String(notificationId)]);
        }
    }
}
