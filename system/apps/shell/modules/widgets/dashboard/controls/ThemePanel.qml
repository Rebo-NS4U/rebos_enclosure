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

    property string currentSection: ""
    onCurrentSectionChanged: mainFlickable.contentY = 0
    property string selectedVariant: "bg"

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
                Layout.preferredHeight: titlebar.height

                PanelTitlebar {
                    id: titlebar
                    width: root.contentWidth
                    anchors.horizontalCenter: parent.horizontalCenter
                    title: ({style: "Theme & app style", general: "Text & shape", motion: "Motion", performance: "Visual effects", blur: "Transparency and blur", shadow: "Shadows", colors: "Wallpaper & palette", variants: "Custom surfaces"})[root.currentSection] || "Appearance"
                    description: root.currentSection === "" ? "Theme & app style, colors, fonts and backgrounds." : ""

                    actions: {
                        if (root.currentSection !== "") {
                            return [
                                {
                                    icon: Icons.arrowLeft,
                                    tooltip: "Back",
                                    onClicked: function () {
                                        root.currentSection = "";
                                    }
                                }
                            ];
                        }

                        return [];
                    }
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
                    SettingsSubnav {
                        visible: root.currentSection !== ""
                        currentSection: root.currentSection
                        sections: [{"id": "colors", "label": "Wallpaper & palette"}, {"id": "style", "label": "Theme & app style"}, {"id": "general", "label": "Text & shape"}, {"id": "variants", "label": "Custom surfaces"}, {"id": "blur", "label": "Transparency & blur"}, {"id": "shadow", "label": "Shadows"}, {"id": "motion", "label": "Animation"}, {"id": "performance", "label": "Visual effects"}]
                        onSelected: section => root.currentSection = section
                    }

                    ColumnLayout {
                        visible: root.currentSection === ""
                        Layout.fillWidth: true
                        spacing: Styling.spacing(20)
                        SettingsMenuGroup {
                            title: "Wallpaper & color"
                            description: "Choose a wallpaper, build your palette and save appearances."
                            entries: [
                                {"id": "colors", "label": "Wallpaper & palette", "description": "Palette, wallpaper color picker and saved appearance presets.", "glyph": Icons.palette},
                                {"id": "style", "label": "Theme & app style", "description": "Choose the shell style and its appearance.", "glyph": Icons.palette}
                            ]
                            onSelected: section => root.currentSection = section
                        }
                        SettingsMenuGroup {
                            title: "Text & surfaces"
                            description: "Fonts, corner shape and custom background details."
                            entries: [
                                {"id": "general", "label": "Text & shape", "description": "Text size, fonts and corner roundness.", "glyph": Icons.gear},
                                {"id": "variants", "label": "Custom surfaces", "description": "Set colors, gradients and outlines.", "glyph": Icons.paintBrush}
                            ]
                            onSelected: section => root.currentSection = section
                        }
                        SettingsMenuGroup {
                            title: "Depth & movement"
                            description: "Transparency, shadows and animation behavior."
                            entries: [
                                {"id": "blur", "label": "Transparency and blur", "description": "Shell transparency, blur strength and where blur appears.", "glyph": Icons.drop},
                                {"id": "shadow", "label": "Shadows", "description": "Shadow size, opacity and position.", "glyph": Icons.drop},
                                {"id": "motion", "label": "Animation", "description": "Panel transitions, selection and button feedback.", "glyph": Icons.lightning},
                                {id: "performance", label: "Visual effects", description: "Window previews, animated blur and artwork effects.", glyph: Icons.lightning}
                            ]
                            onSelected: section => root.currentSection = section
                        }
                    }

                    PerformanceSettings { visible: root.currentSection === "performance" }

                    MotionSettings {
                        Layout.fillWidth: true
                        visible: root.currentSection === "motion"
                    }

                    BlurSettings {
                        Layout.fillWidth: true
                        visible: root.currentSection === "blur"
                    }

                    ShellStyleSettings {
                        visible: root.currentSection === "style"
                        Layout.fillWidth: true
                    }

                    PaletteSettings {
                        onCurrentPageChanged: mainFlickable.contentY = 0
                        visible: root.currentSection === "colors"
                        Layout.fillWidth: true
                    }

                    // General section
                    SettingsGroup {
                        visible: root.currentSection === "general"
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

                            SettingsTextField {
                                Layout.fillWidth: true

                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                id: fontInput


                                font.family: Config.theme.font
                                font.pixelSize: Styling.fontSize(0)
                                color: Colors.overBackground
                                selectByMouse: true
                                clip: true
                                verticalAlignment: TextInput.AlignVCenter

                                readonly property string configValue: Config.theme.font

                                onConfigValueChanged: {
                                    if (text !== configValue) {
                                        text = configValue;
                                    }
                                }

                                Component.onCompleted: text = configValue

                                onEditingFinished: {
                                    if (text !== Config.theme.font && text.trim() !== "") {
                                        Config.theme.font = text.trim();
                                    }
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

                            SettingsTextField {
                                Layout.fillWidth: true

                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                id: monoFontInput


                                font.family: Config.theme.monoFont
                                font.pixelSize: Styling.monoFontSize(0)
                                color: Colors.overBackground
                                selectByMouse: true
                                clip: true
                                verticalAlignment: TextInput.AlignVCenter

                                readonly property string configValue: Config.theme.monoFont

                                onConfigValueChanged: {
                                    if (text !== configValue) {
                                        text = configValue;
                                    }
                                }

                                Component.onCompleted: text = configValue

                                onEditingFinished: {
                                    if (text !== Config.theme.monoFont && text.trim() !== "") {
                                        Config.theme.monoFont = text.trim();
                                    }
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
                                scroll: true
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
                        visible: root.currentSection === "shadow"
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
                                scroll: true
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
                                scroll: true
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
                                scroll: true
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
                                scroll: true
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
                        visible: root.currentSection === "variants"
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
                        visible: root.currentSection === "variants"
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
