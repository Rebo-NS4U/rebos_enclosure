pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import qs.modules.components
import Quickshell
import Quickshell.Io
import qs.config
import qs.modules.globals

Item {
    id: root

    property int maxContentWidth: 760
    readonly property int contentWidth: Math.min(width, maxContentWidth)
    readonly property real sideMargin: (width - contentWidth) / 2

    property string navigationTab: ""
    readonly property bool tabbedNavigation: navigationTab.length > 0
    property string currentSection: ""
    property real sectionOffset: 0
    onCurrentSectionChanged: Qt.callLater(scrollToSection)
    function scrollToSection() {
        function find(item) {
            let target = item.settingsAnchor === root.currentSection ? item : null;
            if (target && item.collapsible) item.expanded = true;
            for (const child of item.children || []) {
                const match = find(child);
                if (!target && match) target = match;
            }
            return target;
        }
        const target = find(mainColumn);
        sectionOffset = target ? target.mapToItem(mainColumn, 0, 0).y : 0;
        mainFlickable.contentY = target ? Math.max(0, Math.min(target.mapToItem(mainColumn, 0, 0).y, mainFlickable.contentHeight - mainFlickable.height)) : 0;
    }
    property string selectedVariant: "bg"
    property alias dropdownGrid: advancedGrid
    property bool combinedSettings: false

    component SectionButton: SettingsSectionCard {
        required property string sectionId
        objectName: "settings-section-" + sectionId
        onClicked: root.currentSection = sectionId
    }

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

    // Convert sr property name to variant id (srBg -> bg, srPrimaryFocus -> primaryfocus)
    function srNameToId(srName: string): string {
        return srName.substring(2).toLowerCase();
    }

    // Dynamically generate allVariants from Config.theme properties starting with "sr"
    // Reads the label property from each variant config
    readonly property var allVariants: {
        let variants = [];
        let theme = Config.theme;

        // Get all property names from theme that start with "sr"
        for (let prop in theme) {
            if (prop.startsWith("sr") && theme[prop] && typeof theme[prop] === "object") {
                // Read label from the variant config itself, fallback to property name
                let label = theme[prop].label || prop.substring(2);
                variants.push({
                    id: srNameToId(prop),
                    label: label
                });
            }
        }

        return variants;
    }

    function getVariantLabel(variantId: string): string {
        for (var i = 0; i < allVariants.length; i++) {
            if (allVariants[i].id === variantId) {
                return allVariants[i].label;
            }
        }
        return variantId;
    }

    // Main content - single Flickable for everything, fills entire width
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
            id: mainTranslate
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
                visible: !root.combinedSettings
                Layout.preferredHeight: visible ? titlebar.height : 0

                PanelTitlebar {
                    id: titlebar
                    width: root.contentWidth
                    anchors.horizontalCenter: parent.horizontalCenter
                    title: "Appearance"
                    description: ""

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
                    spacing: Styling.spacing(12)

                    // ═══════════════════════════════════════════════════════════════
                    // MENU SECTION
                    // ═══════════════════════════════════════════════════════════════




                    ShellStyleSettings {
                        visible: !root.tabbedNavigation || root.navigationTab === "style"
                        property string settingsAnchor: "style"
                        Layout.fillWidth: true
                    }


                    GridLayout {
                        id: advancedGrid
                        objectName: "theme-advanced-grid"
                        visible: !root.tabbedNavigation || root.navigationTab !== "style"
                        Layout.fillWidth: true
                        columns: 1
                        readonly property bool tabbedNavigation: root.tabbedNavigation
                        readonly property string navigationTab: root.navigationTab
                        property bool exclusiveSettingsGroups: !root.tabbedNavigation
                        columnSpacing: Styling.spacing(12)
                        rowSpacing: Styling.spacing(12)
                    WallpaperSettings {
                        visible: (!root.tabbedNavigation || root.navigationTab === "wallpaper")
                            && !(GlobalStates.wallpaperManager?.orbitSelected ?? false)
                        collapsible: !root.tabbedNavigation
                    }
                    OrbitWallpaperSettings {
                        visible: (!root.tabbedNavigation || root.navigationTab === "wallpaper")
                            && (GlobalStates.wallpaperManager?.orbitSelected ?? false)
                        collapsible: !root.tabbedNavigation
                    }
                    PaletteSettings {
                        collapsible: !root.tabbedNavigation
                        onCurrentPageChanged: mainFlickable.contentY = 0
                        visible: !root.tabbedNavigation || root.navigationTab === "colors"
                        property string settingsAnchor: "colors"
                        Layout.fillWidth: true
                        Layout.columnSpan: expanded ? Math.min(2, advancedGrid.columns) : 1
                        Layout.alignment: Qt.AlignTop
                    }
                    PerformanceSettings {
                        visible: !root.tabbedNavigation || root.navigationTab === "effects"
                        property string settingsAnchor: "performance"
                        collapsible: !root.tabbedNavigation
                        Layout.columnSpan: expanded ? Math.min(2, advancedGrid.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        objectName: "theme-group-performance"
                    }

                    MotionSettings {
                        Layout.fillWidth: true
                        visible: !root.tabbedNavigation || root.navigationTab === "effects"
                        property string settingsAnchor: "motion"
                        collapsible: !root.tabbedNavigation
                        Layout.columnSpan: expanded ? Math.min(2, advancedGrid.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        objectName: "theme-group-motion"
                    }

                    BlurSettings {
                        Layout.fillWidth: true
                        visible: !root.tabbedNavigation || root.navigationTab === "effects"
                        property string settingsAnchor: "blur"
                        collapsible: !root.tabbedNavigation
                        Layout.columnSpan: expanded ? Math.min(2, advancedGrid.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        objectName: "theme-group-blur"
                    }


                    // General section
                    SettingsGroup {
                        visible: !root.tabbedNavigation || root.navigationTab === "typography"
                        property string settingsAnchor: "general"
                        collapsible: !root.tabbedNavigation
                        Layout.columnSpan: expanded ? Math.min(2, advancedGrid.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        objectName: "theme-group-general"
                        title: "Typography & shape"


                        StyledText {
                            renderType: Text.NativeRendering
                            font.hintingPreference: Font.PreferFullHinting
                            text: "Fonts"
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-1)
                            font.weight: Font.Medium
                            color: Colors.overSurfaceVariant
                            Layout.bottomMargin: -4
                        }

                        // UI Font row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Styling.spacing(8)

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "UI Font"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                Layout.preferredWidth: 80
                            }

                            SettingsComboBox {
                                id: fontInput
                                previewFonts: true
                                Layout.fillWidth: true
                                readonly property string configValue: Config.theme.font
                                model: {
                                    const families = Qt.fontFamilies();
                                    if (families.indexOf(configValue) < 0)
                                        families.push(configValue);
                                    return families.sort();
                                }
                                currentIndex: model.indexOf(configValue)
                                editable: true
                                onActivated: Config.theme.font = currentText
                                onAccepted: {
                                    const family = editText.trim();
                                    if (family.length > 0)
                                        Config.theme.font = family;
                                    else
                                        editText = configValue;
                                }
                            }

                            SettingsTextField {
                                Layout.preferredWidth: 80

                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                id: fontSizeInput


                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                selectByMouse: true
                                clip: true
                                verticalAlignment: TextInput.AlignVCenter
                                horizontalAlignment: TextInput.AlignHCenter
                                validator: IntValidator {
                                    bottom: 8
                                    top: 32
                                }

                                readonly property int configValue: Config.theme.fontSize

                                onConfigValueChanged: {
                                    if (text !== configValue.toString()) {
                                        text = configValue.toString();
                                    }
                                }

                                Component.onCompleted: text = configValue.toString()

                                onEditingFinished: {
                                    let newSize = parseInt(text);
                                    if (!isNaN(newSize) && newSize >= 8 && newSize <= 32 && newSize !== Config.theme.fontSize) {
                                        Config.theme.fontSize = newSize;
                                    }
                                }

                            }

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "px"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overSurfaceVariant
                            }
                        }

                        // Mono Font row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Styling.spacing(8)

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "Mono Font"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                Layout.preferredWidth: 80
                            }

                            SettingsComboBox {
                                id: monoFontInput
                                previewFonts: true
                                Layout.fillWidth: true
                                readonly property string configValue: Config.theme.monoFont
                                model: {
                                    const families = Qt.fontFamilies();
                                    if (families.indexOf(configValue) < 0)
                                        families.push(configValue);
                                    return families.sort();
                                }
                                currentIndex: model.indexOf(configValue)
                                editable: true
                                onActivated: Config.theme.monoFont = currentText
                                onAccepted: {
                                    const family = editText.trim();
                                    if (family.length > 0)
                                        Config.theme.monoFont = family;
                                    else
                                        editText = configValue;
                                }
                            }

                            SettingsTextField {
                                Layout.preferredWidth: 80

                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                id: monoFontSizeInput


                                font.family: Config.theme.monoFont
                                font.pixelSize: Styling.monoFontSize(0)
                                color: Colors.overBackground
                                selectByMouse: true
                                clip: true
                                verticalAlignment: TextInput.AlignVCenter
                                horizontalAlignment: TextInput.AlignHCenter
                                validator: IntValidator {
                                    bottom: 8
                                    top: 32
                                }

                                readonly property int configValue: Config.theme.monoFontSize

                                onConfigValueChanged: {
                                    if (text !== configValue.toString()) {
                                        text = configValue.toString();
                                    }
                                }

                                Component.onCompleted: text = configValue.toString()

                                onEditingFinished: {
                                    let newSize = parseInt(text);
                                    if (!isNaN(newSize) && newSize >= 8 && newSize <= 32 && newSize !== Config.theme.monoFontSize) {
                                        Config.theme.monoFontSize = newSize;
                                    }
                                }

                            }

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "px"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overSurfaceVariant
                            }
                        }

                        Separator {
                            Layout.fillWidth: true
                        }

                        StyledText {
                            renderType: Text.NativeRendering
                            font.hintingPreference: Font.PreferFullHinting
                            text: "Shell corner radius"
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-1)
                            font.weight: Font.Medium
                            color: Colors.overSurfaceVariant
                            Layout.bottomMargin: -4
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Styling.spacing(8)

                            StyledSlider {
                                id: roundnessSlider
                                Layout.fillWidth: true
                                Layout.preferredHeight: 20
                                progressColor: Styling.srItem("overprimary")
                                tooltipText: `${Math.round(value * 20)}`
                                scroll: false
                                stepSize: 0.05  // 1/20 = 0.05 for integer steps in 0-20 range
                                snapMode: "always"

                                // Use a computed property that always reads from Config
                                readonly property real configValue: Config.theme.roundness / 20

                                // Sync value when configValue changes (e.g., after discard)
                                onConfigValueChanged: {
                                    if (Math.abs(value - configValue) > 0.001) {
                                        value = configValue;
                                    }
                                }

                                Component.onCompleted: value = configValue

                                onValueChanged: {
                                    let newRoundness = Math.round(value * 20);
                                    if (newRoundness !== Config.theme.roundness) {
                                        Config.theme.roundness = newRoundness;
                                    }
                                }
                            }

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: Math.round(roundnessSlider.value * 20)
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 24
                            }
                        }

                    }

                    // Shadow section
                    SettingsGroup {
                        visible: !root.tabbedNavigation || root.navigationTab === "effects"
                        property string settingsAnchor: "shadow"
                        collapsible: !root.tabbedNavigation
                        Layout.columnSpan: expanded ? Math.min(2, advancedGrid.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        objectName: "theme-group-shadow"
                        title: "Shadow appearance"


                        StyledText {
                            Layout.fillWidth: true
                            text: "Shadows apply to shell surfaces that enable them. App window shadows are managed separately."
                            wrapMode: Text.WordWrap
                            color: Colors.overSurfaceVariant
                        }
                        Item {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 160
                            StyledRect {
                                objectName: "shadow-preview"
                                anchors.centerIn: parent
                                width: Math.min(240, parent.width - 80)
                                height: 70
                                variant: "bg"
                                enableShadow: true
                                StyledText { anchors.centerIn: parent; text: "Shadow preview" }
                            }
                        }
                        // Opacity row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Styling.spacing(8)

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "Opacity"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                Layout.preferredWidth: Styling.fontSize(0) * 8
                            }

                            StyledSlider {
                                id: shadowOpacitySlider
                                objectName: "shadow-opacity"
                                Layout.fillWidth: true
                                Layout.preferredHeight: 48
                                progressColor: Styling.srItem("overprimary")
                                tooltipText: `${Math.round(value * 100)}%`
                                scroll: false
                                stepSize: 0.01
                                snapMode: "always"

                                readonly property real configValue: Config.theme.shadowOpacity

                                onConfigValueChanged: {
                                    const wasReady = ready; ready = false;
                                    if (Math.abs(value - configValue) > 0.001) {
                                        value = configValue;
                                    }
                                    ready = wasReady;
                                }

                                Component.onCompleted: { value = configValue; ready = true; }
                                property bool ready: false

                                onValueChanged: {
                                    if (!ready) return;
                                    if (Math.abs(value - Config.theme.shadowOpacity) > 0.001) {
                                        Config.theme.shadowOpacity = value;
                                    }
                                }
                            }

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: Math.round(shadowOpacitySlider.value * 100) + "%"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 40
                            }
                        }

                        // Blur row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Styling.spacing(8)

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "Blur radius"
                                objectName: "shadow-blur-label"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                Layout.preferredWidth: Styling.fontSize(0) * 8
                            }

                            StyledSlider {
                                id: shadowBlurSlider
                                objectName: "shadow-blur"
                                Layout.fillWidth: true
                                Layout.preferredHeight: 48
                                progressColor: Styling.srItem("overprimary")
                                tooltipText: `${(value * 4).toFixed(1)}`
                                scroll: false
                                stepSize: 0.01
                                snapMode: "always"

                                readonly property real configValue: Config.theme.shadowBlur / 4

                                onConfigValueChanged: {
                                    const wasReady = ready; ready = false;
                                    if (Math.abs(value - configValue) > 0.001) {
                                        value = configValue;
                                    }
                                    ready = wasReady;
                                }

                                Component.onCompleted: { value = configValue; ready = true; }
                                property bool ready: false

                                onValueChanged: {
                                    if (!ready) return;
                                    let newBlur = value * 4;
                                    if (Math.abs(newBlur - Config.theme.shadowBlur) > 0.01) {
                                        Config.theme.shadowBlur = newBlur;
                                    }
                                }
                            }

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: Config.theme.shadowBlur.toFixed(1)
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 40
                            }
                        }

                        // Offset row (X and Y)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Styling.spacing(8)

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "Offset X"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                Layout.preferredWidth: Styling.fontSize(0) * 8
                            }

                            StyledSlider {
                                id: shadowXOffsetSlider
                                objectName: "shadow-x"
                                Layout.fillWidth: true
                                Layout.preferredHeight: 48
                                progressColor: Styling.srItem("overprimary")
                                tooltipText: `${Math.round((value - 0.5) * 40)}`
                                scroll: false
                                stepSize: 0.025  // 1/40 for integer steps in -20 to +20 range
                                snapMode: "always"

                                readonly property real configValue: (Config.theme.shadowXOffset + 20) / 40

                                onConfigValueChanged: {
                                    const wasReady = ready; ready = false;
                                    if (Math.abs(value - configValue) > 0.001) {
                                        value = configValue;
                                    }
                                    ready = wasReady;
                                }

                                Component.onCompleted: { value = configValue; ready = true; }
                                property bool ready: false

                                onValueChanged: {
                                    if (!ready) return;
                                    let newOffset = Math.round((value - 0.5) * 40);
                                    if (newOffset !== Config.theme.shadowXOffset) {
                                        Config.theme.shadowXOffset = newOffset;
                                    }
                                }
                            }

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: Config.theme.shadowXOffset
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 40
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Styling.spacing(8)

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "Offset Y"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                Layout.preferredWidth: Styling.fontSize(0) * 8
                            }

                            StyledSlider {
                                id: shadowYOffsetSlider
                                objectName: "shadow-y"
                                Layout.fillWidth: true
                                Layout.preferredHeight: 48
                                progressColor: Styling.srItem("overprimary")
                                tooltipText: `${Math.round((value - 0.5) * 40)}`
                                scroll: false
                                stepSize: 0.025  // 1/40 for integer steps in -20 to +20 range
                                snapMode: "always"

                                readonly property real configValue: (Config.theme.shadowYOffset + 20) / 40

                                onConfigValueChanged: {
                                    const wasReady = ready; ready = false;
                                    if (Math.abs(value - configValue) > 0.001) {
                                        value = configValue;
                                    }
                                    ready = wasReady;
                                }

                                Component.onCompleted: { value = configValue; ready = true; }
                                property bool ready: false

                                onValueChanged: {
                                    if (!ready) return;
                                    let newOffset = Math.round((value - 0.5) * 40);
                                    if (newOffset !== Config.theme.shadowYOffset) {
                                        Config.theme.shadowYOffset = newOffset;
                                    }
                                }
                            }

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: Config.theme.shadowYOffset
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                horizontalAlignment: Text.AlignRight
                                Layout.preferredWidth: 40
                            }
                        }

                        // Color row
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Styling.spacing(8)

                            StyledText {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: "Color"
                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                Layout.preferredWidth: Styling.fontSize(0) * 8
                            }

                            StyledRect {
                                id: shadowColorButton
                                variant: "common"
                                Layout.fillWidth: true
                                Layout.preferredHeight: 48
                                radius: Styling.radius(-2)

                                property bool isHovered: false

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: Styling.spacing(8)

                                    Rectangle {
                                        Layout.preferredWidth: 16
                                        Layout.preferredHeight: 16
                                        radius: 4
                                        color: Config.resolveColor(Config.theme.shadowColor)
                                        border.width: 1
                                        border.color: Colors.outline
                                    }

                                    StyledText {
                                        renderType: Text.NativeRendering
                                        font.hintingPreference: Font.PreferFullHinting
                                        Layout.fillWidth: true
                                        text: Config.theme.shadowColor
                                        font.family: Config.theme.font
                                        font.pixelSize: Styling.fontSize(0)
                                        color: shadowColorButton.item
                                        elide: Text.ElideRight
                                    }
                                }

                                Rectangle {
                                    anchors.fill: parent
                                    color: Styling.srItem("overprimary")
                                    radius: shadowColorButton.radius ?? 0
                                    opacity: shadowColorButton.isHovered ? 0.15 : 0

                                    Behavior on opacity {
                                        enabled: (Config.animDuration ?? 0) > 0
                                        NumberAnimation {
                                            duration: (Config.animDuration ?? 0) / 2
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor

                                    onEntered: shadowColorButton.isHovered = true
                                    onExited: shadowColorButton.isHovered = false

                                    onClicked: {
                                        root.openColorPicker(Colors.availableColorNames, Config.theme.shadowColor, "Select Shadow Color", function (color) {
                                            Config.theme.shadowColor = color;
                                        });
                                    }
                                }
                            }
                        }

                    }

                    // Variant selector section
                    SettingsGroup {
                        visible: !root.tabbedNavigation || root.navigationTab === "effects"
                        property string settingsAnchor: "variants"
                        collapsible: !root.tabbedNavigation
                        Layout.columnSpan: expanded ? Math.min(2, advancedGrid.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        objectName: "theme-group-variants"
                        title: "Surface to edit"
                        description: Styling.unifiedStyle ? "Choose Custom under Theme & app style to apply individual surface changes." : "Changes apply to the selected surface."
                        SettingsComboBox {
                            objectName: "surface-selector"
                            Layout.fillWidth: true
                            model: root.allVariants
                            textRole: "label"
                            valueRole: "id"
                            currentIndex: root.allVariants.findIndex(item => item.id === root.selectedVariant)
                            onActivated: root.selectedVariant = currentValue
                        }
                    }

                    // Editor section
                    SettingsGroup {
                        visible: !root.tabbedNavigation || root.navigationTab === "effects"
                        property string settingsAnchor: "variants"
                        collapsible: !root.tabbedNavigation
                        Layout.columnSpan: expanded ? Math.min(2, advancedGrid.columns) : 1
                        Layout.alignment: Qt.AlignTop
                        objectName: "theme-group-variants"
                        title: "Custom surface editor"
                        property string settingsSection: "variants"


                        StyledText {
                            renderType: Text.NativeRendering
                            font.hintingPreference: Font.PreferFullHinting
                            text: "Editor - " + root.getVariantLabel(root.selectedVariant)
                            font.family: Config.theme.font
                            font.pixelSize: Styling.fontSize(-1)
                            font.weight: Font.Medium
                            color: Colors.overSurfaceVariant
                            Layout.bottomMargin: -4
                        }

                        VariantEditor {
                            Layout.fillWidth: true
                            variantId: root.selectedVariant
                            onClose: {}
                            onOpenColorPickerRequested: (colorNames, currentColor, dialogTitle, callback) => {
                                root.openColorPicker(colorNames, currentColor, dialogTitle, callback);
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
        anchors.fill: parent
        clip: true

        // Horizontal slide + fade animation (enters from right)
        opacity: root.colorPickerActive ? 1 : 0
        transform: Translate {
            id: pickerTranslate
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
            // Consume all mouse events to prevent pass-through
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
