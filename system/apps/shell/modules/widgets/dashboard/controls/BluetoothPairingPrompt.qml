import QtQuick
import QtQuick.Layouts
import qs.modules.components
import qs.modules.services
import qs.modules.theme

ColumnLayout {
    visible: BluetoothService.pairingAddress.length > 0
    spacing: Styling.spacing(4)
    readonly property var prompt: BluetoothService.pairingPrompt
    readonly property bool inputRequired: prompt && (prompt.kind === "RequestPinCode" || prompt.kind === "RequestPasskey")
    StyledText {
        Layout.fillWidth: true
        visible: prompt !== null
        text: inputRequired ? "Enter the pairing PIN or passkey" : prompt?.kind === "RequestConfirmation" ? "Does this code match the device? " + prompt.code : "Allow this device to pair?"
        wrapMode: Text.Wrap
    }
    SearchInput {
        id: response
        Layout.fillWidth: true
        visible: inputRequired
        passwordMode: true
        placeholderText: "Pairing PIN or passkey"
        onAccepted: { BluetoothService.respondPairing(true, text); clear(); }
        onEscapePressed: { BluetoothService.respondPairing(false); clear(); }
        onVisibleChanged: { clear(); if (visible) Qt.callLater(() => focusInput()); }
    }
    RowLayout {
        ThemeButton { text: "Cancel pairing"; onClicked: { BluetoothService.cancelPairing(); response.clear(); } }
        ThemeButton {
            visible: prompt !== null
            text: inputRequired ? "Submit" : "Confirm"
            onClicked: { BluetoothService.respondPairing(true, response.text); response.clear(); }
        }
    }

    StyledText {
        Layout.fillWidth: true
        visible: BluetoothService.pairingCode.length > 0
        text: "Type this code on " + BluetoothService.pairingDeviceName + ", then press Enter:"
        wrapMode: Text.Wrap
    }

    StyledText {
        Layout.fillWidth: true
        visible: BluetoothService.pairingCode.length > 0
        text: BluetoothService.pairingCode
        font.pixelSize: Styling.fontSize(10)
        font.bold: true
        color: Styling.srItem("overprimary")
        horizontalAlignment: Text.AlignHCenter
    }

    StyledText {
        Layout.fillWidth: true
        visible: BluetoothService.pairingEntered > 0
        text: Math.min(BluetoothService.pairingEntered, BluetoothService.pairingCode.length)
            + " of " + BluetoothService.pairingCode.length + " digits entered"
        horizontalAlignment: Text.AlignHCenter
    }
}
