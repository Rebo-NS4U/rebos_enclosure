pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.modules.theme
import qs.modules.components
import qs.config
import qs.modules.bar

Item {
    id: root

    property int maxContentWidth: 760
    readonly property int contentWidth: Math.min(width, maxContentWidth)
    readonly property real sideMargin: (width - contentWidth) / 2

    // Available color names for color picker
    readonly property var colorNames: Colors.availableColorNames

    // Color picker state
    property bool colorPickerActive: false
    property var colorPickerColorNames: []
    property string colorPickerCurrentColor: ""
    property string colorPickerDialogTitle: ""
    property var colorPickerCallback: null

    function openColorPicker(colorNames, currentColor, dialogTitle, callback) {
        colorPickerColorNames = colorNames;
        colorPickerCurrentColor = currentColor;
        colorPickerDialogTitle = dialogTitle;
        colorPickerCallback = callback;
        colorPickerActive = true;
    }

    function closeColorPicker() {
        colorPickerActive = false;
        colorPickerCallback = null;
    }

    function handleColorSelected(color) {
        if (colorPickerCallback) {
            colorPickerCallback(color);
        }
        colorPickerCurrentColor = color;
    }

    property Item groupContainer: null
    property Item overlayContainer: null
    property string currentSection: ""
    property real sectionOffset: 0
    onCurrentSectionChanged: Qt.callLater(scrollToSection)
    function scrollToSection() {
        function find(item) {
            if (item.settingsAnchor === root.currentSection) return item;
            for (const child of item.children || []) { const match = find(child); if (match) return match; }
            return null;
        }
        const target = find(root.groupContainer || mainColumn);
        if (target && target.collapsible) target.expanded = true;
        sectionOffset = target ? target.mapToItem(mainColumn, 0, 0).y : 0;
        mainFlickable.contentY = target ? Math.max(0, Math.min(target.mapToItem(mainColumn, 0, 0).y, mainFlickable.contentHeight - mainFlickable.height)) : 0;
    }

    component SectionButton: SettingsSectionCard {
        required property string sectionId
        objectName: "settings-section-" + sectionId
        onClicked: root.currentSection = sectionId
    }

    component ActionButton: StyledRect {
        id: actionBtn
        required property string text
        property string icon: ""
        property string trailingIcon: Icons.arrowSquareOut
        signal clicked

        property bool isHovered: false

        variant: isHovered ? "focus" : "pane"
        Layout.fillWidth: true
        Layout.preferredHeight: 56
        radius: Styling.radius(0)

        RowLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: Styling.spacing(16)

            StyledText {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: actionBtn.icon
                font.family: Icons.font
                font.pixelSize: Styling.fontSize(6)
                color: Colors.overSurfaceVariant
                visible: actionBtn.icon !== ""
            }

            StyledText {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: actionBtn.text
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(0)
                font.bold: true
                color: Colors.overBackground
                Layout.fillWidth: true
            }

            StyledText {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: actionBtn.trailingIcon
                visible: actionBtn.trailingIcon !== ""
                font.family: Icons.font
                font.pixelSize: Styling.fontSize(4)
                color: Colors.overSurfaceVariant
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onEntered: actionBtn.isHovered = true
            onExited: actionBtn.isHovered = false
            onClicked: actionBtn.clicked()
        }
    }

    // Inline component for toggle rows
    component ToggleRow: SettingsToggleRow {}

    component AppearanceSliderRow: ColumnLayout {
        id: sliderRow
        required property string label
        required property int configValue
        property int minimum: 0
        signal valueEdited(int newValue)
        Layout.fillWidth: true
        spacing: Styling.spacing(8)
        RowLayout {
            Layout.fillWidth: true
            StyledText {
                text: sliderRow.label
                Layout.fillWidth: true
                color: Colors.overBackground
            }
            StyledText {
                text: sliderRow.configValue + "%"
                color: Colors.overSurfaceVariant
            }
        }
        StyledSlider {
            scroll: false
            id: appearanceSlider
            objectName: sliderRow.objectName + "-control"
            Layout.fillWidth: true
            Layout.preferredHeight: Styling.fontSize(0) * 1.5
            property bool ready: false
            readonly property real externalValue: (sliderRow.configValue - sliderRow.minimum) / (100 - sliderRow.minimum)
            stepSize: 1 / (100 - sliderRow.minimum)
            snapMode: "always"
            progressColor: Styling.srItem("overprimary")
            tooltipText: Math.round(sliderRow.minimum + value * (100 - sliderRow.minimum)) + "%"
            onExternalValueChanged: {
                if (Math.abs(value - externalValue) > 0.001) value = externalValue;
            }
            Component.onCompleted: { value = externalValue; ready = true; }
            onValueChanged: {
                if (ready) {
                    const percent = Math.round(sliderRow.minimum + value * (100 - sliderRow.minimum));
                    if (percent !== sliderRow.configValue) sliderRow.valueEdited(percent);
                }
            }
        }
    }

    // Inline component for number input rows
    component NumberInputRow: RowLayout {
        id: numberInputRowRoot
        property string label: ""
        property int value: 0
        property int minValue: 0
        property int maxValue: 100
        property string suffix: ""
        signal valueEdited(int newValue)

        Layout.fillWidth: true
        spacing: Styling.spacing(8)

        StyledText {
            renderType: Text.NativeRendering
            font.hintingPreference: Font.PreferFullHinting
            text: numberInputRowRoot.label
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(0)
            color: Colors.overBackground
            Layout.fillWidth: true
        }

        StyledRect {
            variant: "common"
            Layout.preferredWidth: 60
            Layout.preferredHeight: 48
            radius: Styling.radius(-2)

            TextInput {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                id: numberTextInput
                anchors.fill: parent
                anchors.margins: 8
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(0)
                color: Colors.overBackground
                selectByMouse: true
                clip: true
                verticalAlignment: TextInput.AlignVCenter
                horizontalAlignment: TextInput.AlignHCenter
                validator: IntValidator {
                    bottom: numberInputRowRoot.minValue
                    top: numberInputRowRoot.maxValue
                }

                // Sync text when external value changes
                readonly property int configValue: numberInputRowRoot.value
                onConfigValueChanged: {
                    if (!activeFocus && text !== configValue.toString()) {
                        text = configValue.toString();
                    }
                }
                Component.onCompleted: text = configValue.toString()

                onEditingFinished: {
                    let newVal = parseInt(text);
                    if (!isNaN(newVal)) {
                        newVal = Math.max(numberInputRowRoot.minValue, Math.min(numberInputRowRoot.maxValue, newVal));
                        numberInputRowRoot.valueEdited(newVal);
                    }
                }
            }
        }

        StyledText {
            renderType: Text.NativeRendering
            font.hintingPreference: Font.PreferFullHinting
            text: numberInputRowRoot.suffix
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(0)
            color: Colors.overSurfaceVariant
            visible: suffix !== ""
        }
    }

    // Inline component for text input rows
    component TextInputRow: RowLayout {
        id: textInputRowRoot
        property string label: ""
        property string value: ""
        property string placeholder: ""
        signal valueEdited(string newValue)

        Layout.fillWidth: true
        spacing: Styling.spacing(8)

        StyledText {
            renderType: Text.NativeRendering
            font.hintingPreference: Font.PreferFullHinting
            text: textInputRowRoot.label
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(0)
            color: Colors.overBackground
            Layout.preferredWidth: 100
        }

        StyledRect {
            variant: "common"
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: Styling.radius(-2)

            TextInput {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                id: textInputField
                anchors.fill: parent
                anchors.margins: 8
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(0)
                color: Colors.overBackground
                selectByMouse: true
                clip: true
                verticalAlignment: TextInput.AlignVCenter

                // Sync text when external value changes
                readonly property string configValue: textInputRowRoot.value
                onConfigValueChanged: {
                    if (!activeFocus && text !== configValue) {
                        text = configValue;
                    }
                }
                Component.onCompleted: text = configValue

                StyledText {
                    anchors.fill: parent
                    verticalAlignment: Text.AlignVCenter
                    text: textInputRowRoot.placeholder
                    font.family: Config.theme.font
                    font.pixelSize: Styling.fontSize(0)
                    color: Colors.overSurfaceVariant
                    visible: textInputField.text === ""
                }

                onEditingFinished: {
                    textInputRowRoot.valueEdited(text);
                }
            }
        }
    }

    // Inline component for segmented selector rows
    component SelectorRow: ColumnLayout {
        id: selectorRowRoot
        property string label: ""
        property var options: []  // Array of { label: "...", value: "...", icon: "..." (optional) }
        property string value: ""
        signal valueSelected(string newValue)

        function getIndexFromValue(val: string): int {
            for (let i = 0; i < options.length; i++) {
                if (options[i].value === val)
                    return i;
            }
            return 0;
        }

        Layout.fillWidth: true
        spacing: Styling.spacing(4)

        StyledText {
            renderType: Text.NativeRendering
            font.hintingPreference: Font.PreferFullHinting
            text: selectorRowRoot.label
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(-1)
            font.weight: Font.Medium
            color: Colors.overSurfaceVariant
            visible: selectorRowRoot.label !== ""
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(4)

            Repeater {
                model: selectorRowRoot.options

                delegate: StyledRect {
                    id: optionButton
                    objectName: selectorRowRoot.objectName + "-" + modelData.value
                    required property var modelData
                    required property int index

                    readonly property bool isSelected: selectorRowRoot.getIndexFromValue(selectorRowRoot.value) === index
                    property bool isHovered: false

                    variant: isSelected ? "primary" : (isHovered ? "focus" : "common")
                    enableShadow: false
                    Layout.fillWidth: true
                    height: 36
                    radius: Styling.radius(0)

                    StyledText {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        id: optionIcon
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: optionButton.modelData.icon ?? ""
                        font.family: Icons.font
                        font.pixelSize: Styling.fontSize(0)
                        color: optionButton.item
                        visible: (optionButton.modelData.icon ?? "") !== ""
                    }

                    StyledText {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        anchors.centerIn: parent
                        text: optionButton.modelData.label
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(0)
                        font.bold: true
                        color: optionButton.item
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onEntered: optionButton.isHovered = true
                        onExited: optionButton.isHovered = false

                        onClicked: selectorRowRoot.valueSelected(optionButton.modelData.value)
                    }
                }
            }
        }
    }

    // Inline component for screen list selection
    component ScreenListRow: ColumnLayout {
        id: screenListRowRoot
        property string label: "Screens"
        property var selectedScreens: []  // Array of screen names
        signal screensChanged(var newList)

        Layout.fillWidth: true
        spacing: Styling.spacing(4)

        StyledText {
            renderType: Text.NativeRendering
            font.hintingPreference: Font.PreferFullHinting
            text: screenListRowRoot.label
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(-1)
            font.weight: Font.Medium
            color: Colors.overSurfaceVariant
        }

        StyledText {
            renderType: Text.NativeRendering
            font.hintingPreference: Font.PreferFullHinting
            text: "Empty = all screens"
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(-2)
            color: Colors.outline
            Layout.bottomMargin: 4
        }

        Flow {
            Layout.fillWidth: true
            spacing: Styling.spacing(4)

            Repeater {
                model: Quickshell.screens

                delegate: StyledRect {
                    id: screenButton
                    required property var modelData
                    required property int index

                    readonly property string screenName: modelData.name
                    readonly property bool isSelected: {
                        const list = screenListRowRoot.selectedScreens;
                        return list && list.length > 0 && list.includes(screenName);
                    }
                    property bool isHovered: false

                    variant: isSelected ? "primary" : (isHovered ? "focus" : "common")
                    width: screenLabel.implicitWidth + 24
                    height: 32
                    radius: Styling.radius(-2)

                    StyledText {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        id: screenLabel
                        anchors.centerIn: parent
                        text: screenButton.screenName
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(-1)
                        font.bold: screenButton.isSelected
                        color: screenButton.item
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onEntered: screenButton.isHovered = true
                        onExited: screenButton.isHovered = false

                        onClicked: {
                            let currentList = screenListRowRoot.selectedScreens ? [...screenListRowRoot.selectedScreens] : [];
                            const idx = currentList.indexOf(screenButton.screenName);
                            if (idx >= 0) {
                                currentList.splice(idx, 1);
                            } else {
                                currentList.push(screenButton.screenName);
                            }
                            screenListRowRoot.screensChanged(currentList);
                        }
                    }
                }
            }
        }
    }

    // Main content
    Flickable {
        id: mainFlickable
        anchors.fill: parent
        contentHeight: mainColumn.implicitHeight
        clip: true
        ScrollBar.vertical: ScrollBar {}
        boundsBehavior: Flickable.StopAtBounds
        interactive: !root.colorPickerActive

        // Horizontal slide + fade animation
        opacity: root.colorPickerActive ? 0 : 1
        transform: Translate {
            x: root.colorPickerActive ? -30 : 0

            Behavior on x {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration / 2
                    easing.type: Easing.OutQuart
                }
            }
        }

        Behavior on opacity {
            enabled: Config.animDuration > 0
            NumberAnimation {
                duration: Config.animDuration / 2
                easing.type: Easing.OutQuart
            }
        }

        ColumnLayout {
            id: mainColumn
            width: mainFlickable.width
            spacing: Styling.spacing(16)

            // Header wrapper
            Item {
                Layout.fillWidth: true
                visible: !root.groupContainer
                Layout.preferredHeight: visible ? titlebar.height : 0

                PanelTitlebar {
                    id: titlebar
                    width: root.contentWidth
                    anchors.horizontalCenter: parent.horizontalCenter
                    title: "Shell"
                    description: root.currentSection === "" ? "Bar, assistant panel, lock screen and information widgets." : ""

                    actions: []

                }
            }

            // Content wrapper - centered
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: contentColumn.implicitHeight

                ColumnLayout {
                    id: contentColumn
                    width: root.contentWidth
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: Styling.spacing(16)

                    // ═══════════════════════════════════════════════════════════════
                    // MENU SECTION
                    // ═══════════════════════════════════════════════════════════════




                    WeatherSettings {
                        property string settingsAnchor: "weather"
                        visible: !root.groupContainer?.tabbedNavigation || root.groupContainer.navigationTab === "panels"
                        collapsible: !root.groupContainer?.tabbedNavigation
                        objectName: "shell-group-weather"
                        parent: root.groupContainer || contentColumn
                        Layout.columnSpan: root.groupContainer && expanded ? Math.min(2, root.groupContainer.columns) : 1
                        Layout.alignment: Qt.AlignTop
                    }
                    StorageSettings {
                        property string settingsAnchor: "storage"
                        visible: !root.groupContainer?.tabbedNavigation || root.groupContainer.navigationTab === "panels"
                        collapsible: !root.groupContainer?.tabbedNavigation
                        objectName: "shell-group-storage"
                        parent: root.groupContainer || contentColumn
                        Layout.columnSpan: root.groupContainer && expanded ? Math.min(2, root.groupContainer.columns) : 1
                        Layout.alignment: Qt.AlignTop
                    }

                    // ═══════════════════════════════════════════════════════════════
                    // BAR SECTION
                    // ═══════════════════════════════════════════════════════════════
                    SettingsGroup {
                        property string settingsAnchor: "bar"
                        visible: !root.groupContainer?.tabbedNavigation || root.groupContainer.navigationTab === "panels"
                        collapsible: !root.groupContainer?.tabbedNavigation
                        objectName: "shell-group-bar"
                        parent: root.groupContainer || contentColumn
                        Layout.columnSpan: root.groupContainer && expanded ? Math.min(2, root.groupContainer.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        title: "Desktop bar"
                        Layout.fillWidth: true

                        StyledText {
                            renderType: Text.NativeRendering
                            font.hintingPreference: Font.PreferFullHinting
                            text: "Bar"
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-1)
                            font.weight: Font.Medium
                            color: Colors.overSurfaceVariant
                            Layout.bottomMargin: -4
                        }

                        StyledText {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: "The centered island bar uses expanding panels and circular brightness, volume and battery controls. Shell corner styling is configured under Theme."
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-1)
                            color: Colors.overSurfaceVariant
                        }

                        ToggleRow {
                            label: "12-hour clock"
                            checked: Config.bar.use12hFormat ?? false
                            onToggled: value => {
                                if (value !== Config.bar.use12hFormat) {
                                    Config.bar.use12hFormat = value;
                                }
                            }
                        }

                        ToggleRow {
                            label: "Browser media controls"
                            checked: Config.bar.enableFirefoxPlayer ?? false
                            onToggled: value => {
                                if (value !== Config.bar.enableFirefoxPlayer) {
                                    Config.bar.enableFirefoxPlayer = value;
                                }
                            }
                        }

                        ToggleRow {
                            visible: (Config.bar?.style ?? "default") === "island"
                            label: "Keep bar visible"
                            checked: Config.bar.pinned ?? false
                            onToggled: value => {
                                if (value !== Config.bar.pinned) {
                                    Config.bar.pinned = value;
                                }
                            }
                        }

                        ColumnLayout {
                            visible: (Config.bar?.style ?? "default") === "island"
                            Layout.fillWidth: true
                            spacing: Styling.spacing(12)

                            SelectorRow {
                                objectName: "bar-appearance"
                                label: "Appearance"
                                options: [
                                    { label: "Plain", value: "classic", icon: Icons.circle },
                                    { label: "Bordered", value: "glass", icon: Icons.layout }
                                ]
                                value: Config.bar?.islandAppearance ?? "glass"
                                onValueSelected: newValue => Config.bar.islandAppearance = newValue
                            }

                            BarAppearancePreview { Layout.fillWidth: true }

                            StyledText {
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: "Plain uses a simple theme background. Bordered adds an accent outline and highlights the active workspace. Both follow the shell transparency setting."
                                font.pixelSize: Styling.fontSize(-1)
                                color: Colors.overSurfaceVariant
                            }
                            ActionButton {
                                objectName: "bar-appearance-reset"
                                text: "Reset bar appearance"
                                icon: Icons.arrowCounterClockwise
                                trailingIcon: ""
                                onClicked: BarAppearance.reset()
                            }
                        }

                        ScreenListRow {
                            label: "Screens"
                            selectedScreens: Config.bar.screenList ?? []
                            onScreensChanged: newList => {
                                Config.bar.screenList = newList;
                            }
                        }
                    }

                    Separator {
                        Layout.fillWidth: true
                        visible: false
                    }

                    // ═══════════════════════════════════════════════════════════════
                    // WORKSPACES SECTION
                    // LOCKSCREEN SECTION
                    // ═══════════════════════════════════════════════════════════════
                    SettingsGroup {
                        property string settingsAnchor: "lockscreen"
                        visible: !root.groupContainer?.tabbedNavigation || root.groupContainer.navigationTab === "panels"
                        collapsible: !root.groupContainer?.tabbedNavigation
                        objectName: "shell-group-lockscreen"
                        parent: root.groupContainer || contentColumn
                        Layout.columnSpan: root.groupContainer && expanded ? Math.min(2, root.groupContainer.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        title: "Lock screen"
                        Layout.fillWidth: true

                        StyledText {
                            renderType: Text.NativeRendering
                            font.hintingPreference: Font.PreferFullHinting
                            text: "Lockscreen"
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-1)
                            font.weight: Font.Medium
                            color: Colors.overSurfaceVariant
                            Layout.bottomMargin: -4
                        }

                        SelectorRow {
                            label: ""
                            options: [
                                {
                                    label: "Top",
                                    value: "top",
                                    icon: Icons.arrowUp
                                },
                                {
                                    label: "Bottom",
                                    value: "bottom",
                                    icon: Icons.arrowDown
                                }
                            ]
                            value: Config.lockscreen.position ?? "bottom"
                            onValueSelected: newValue => {
                                if (newValue !== Config.lockscreen.position) {
                                    Config.lockscreen.position = newValue;
                                }
                            }
                        }
                    }

                    // SYSTEM SECTION
                    // ═══════════════════════════════════════════════════════════════
                    SettingsGroup {
                        property string settingsAnchor: "system"
                        visible: !root.groupContainer?.tabbedNavigation || root.groupContainer.navigationTab === "panels"
                        collapsible: !root.groupContainer?.tabbedNavigation
                        objectName: "shell-group-system"
                        parent: root.groupContainer || contentColumn
                        Layout.columnSpan: root.groupContainer && expanded ? Math.min(2, root.groupContainer.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        title: "About"
                        Layout.fillWidth: true

                        StyledText {
                            renderType: Text.NativeRendering
                            font.hintingPreference: Font.PreferFullHinting
                            text: "rebos_enclosure"
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-1)
                            font.weight: Font.Medium
                            color: Colors.overSurfaceVariant
                            Layout.bottomMargin: -4
                        }

                        StyledText {
                            id: enclosureVersion
                            property string revision: ""
                            text: revision ? "Enclosure build " + revision
                                : (versionLookup.running ? "Reading Enclosure build…" : "Enclosure build unavailable")
                            color: Colors.overSurfaceVariant

                            Process {
                                id: versionLookup
                                running: enclosureVersion.visible
                                command: ["python3", "-B", Quickshell.shellPath("scripts/github_status.py"), "--installed-version"]
                                stdout: StdioCollector {
                                    onStreamFinished: enclosureVersion.revision = text.trim()
                                }
                            }
                        }

                        ActionButton {
                            text: "Source on GitHub"
                            icon: Icons.link
                            onClicked: Quickshell.execDetached(["xdg-open", "https://github.com/Rebo-NS4U/rebos_enclosure"])
                        }

                        ActionButton {
                            text: "Latest Enclosure release"
                            icon: Icons.arrowSquareOut
                            onClicked: Quickshell.execDetached(["xdg-open", "https://github.com/Rebo-NS4U/rebos_enclosure/releases/latest"])
                        }

                        ActionButton {
                            text: "Sponsor jR4dh3y"
                            icon: Icons.heart
                            onClicked: Quickshell.execDetached(["xdg-open", "https://github.com/sponsors/jR4dh3y"])
                        }

                    }

                    // ═══════════════════════════════════════════════════════════════
                    // SIDEBAR SECTION
                    // ═══════════════════════════════════════════════════════════════
                    SettingsGroup {
                        property string settingsAnchor: "sidebar"
                        visible: !root.groupContainer?.tabbedNavigation || root.groupContainer.navigationTab === "panels"
                        collapsible: !root.groupContainer?.tabbedNavigation
                        objectName: "shell-group-sidebar"
                        parent: root.groupContainer || contentColumn
                        Layout.columnSpan: root.groupContainer && expanded ? Math.min(2, root.groupContainer.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        title: "Assistant panel"
                        Layout.fillWidth: true

                        StyledText {
                            renderType: Text.NativeRendering
                            font.hintingPreference: Font.PreferFullHinting
                            text: "Sidebar"
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-1)
                            font.weight: Font.Medium
                            color: Colors.overSurfaceVariant
                            Layout.bottomMargin: -4
                        }

                        ToggleRow {
                            label: "Show assistant panel"
                            checked: Config.ai.sidebarEnabled ?? true
                            onToggled: value => {
                                if (value !== Config.ai.sidebarEnabled) {
                                    Config.ai.sidebarEnabled = value;
                                }
                            }
                        }

                        SelectorRow {
                            label: "Position"
                            enabled: Config.ai.sidebarEnabled ?? true
                            opacity: enabled ? 1 : 0.5
                            options: [
                                {
                                    label: "Left",
                                    value: "left",
                                    icon: Icons.arrowLeft
                                },
                                {
                                    label: "Right",
                                    value: "right",
                                    icon: Icons.arrowRight
                                }
                            ]
                            value: Config.ai.sidebarPosition ?? "right"
                            onValueSelected: newValue => {
                                if (newValue !== Config.ai.sidebarPosition) {
                                    Config.ai.sidebarPosition = newValue;
                                }
                            }
                        }

                        NumberInputRow {
                            label: "Width"
                            enabled: Config.ai.sidebarEnabled ?? true
                            opacity: enabled ? 1 : 0.5
                            value: Config.ai.sidebarWidth ?? 400
                            minValue: 300
                            maxValue: 800
                            suffix: "px"
                            onValueEdited: newValue => {
                                if (newValue !== Config.ai.sidebarWidth) {
                                    Config.ai.sidebarWidth = newValue;
                                }
                            }
                        }

                        ToggleRow {
                            label: "Open as a tiled window"
                            enabled: Config.ai.sidebarEnabled ?? true
                            opacity: enabled ? 1 : 0.5
                            checked: Config.ai.sidebarPinnedOnStartup ?? false
                            onToggled: value => {
                                if (value !== Config.ai.sidebarPinnedOnStartup) {
                                    Config.ai.sidebarPinnedOnStartup = value;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Color picker view (shown when colorPickerActive)
    Item {
        id: colorPickerContainer
        parent: root.overlayContainer || root
        z: 100
        anchors.fill: parent
        clip: true

        // Horizontal slide + fade animation (enters from right)
        opacity: root.colorPickerActive ? 1 : 0
        transform: Translate {
            x: root.colorPickerActive ? 0 : 30

            Behavior on x {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration / 2
                    easing.type: Easing.OutQuart
                }
            }
        }

        Behavior on opacity {
            enabled: Config.animDuration > 0
            NumberAnimation {
                duration: Config.animDuration / 2
                easing.type: Easing.OutQuart
            }
        }

        // Prevent interaction when hidden
        enabled: root.colorPickerActive

        // Block interaction with elements behind when active
        MouseArea {
            anchors.fill: parent
            enabled: root.colorPickerActive
            hoverEnabled: true
            acceptedButtons: Qt.AllButtons
            onPressed: event => event.accepted = true
            onReleased: event => event.accepted = true
            onWheel: event => event.accepted = true
        }

        ColorPickerView {
            id: colorPickerContent
            anchors.fill: parent
            anchors.leftMargin: root.sideMargin
            anchors.rightMargin: root.sideMargin
            colorNames: root.colorPickerColorNames
            currentColor: root.colorPickerCurrentColor
            dialogTitle: root.colorPickerDialogTitle

            onColorSelected: color => root.handleColorSelected(color)
            onClosed: root.closeColorPicker()
        }
    }
}
