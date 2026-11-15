pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Quickshell
import qs.config
import qs.modules.globals
import qs.modules.services
import qs.modules.theme
import qs.modules.components
import "../../../theme/PaletteSchemes.js" as PaletteSchemes

SettingsGroup {
    id: root
    title: "Wallpaper colors"
    collapsible: true
    objectName: "wallpaper-colors"
    property string settingsSection: "colors"
    readonly property PanelWindow manager: GlobalStates.wallpaperManager
    readonly property bool busy: manager?.paletteBusy ?? false
    readonly property string preset: manager?.activeColorPreset ?? ""
    property var draftColors: manager?.pickedAccentColors ?? ["", ""]
    property int pickedRole: 0
    property string currentPage: ""
    readonly property string pickerWallpaper: manager?.currentWallpaper ?? ""
    readonly property string pickerSource: manager && pickerWallpaper ? manager.getColorSource(pickerWallpaper) : ""
    function resetPicks() { draftColors = (manager?.pickedAccentColors ?? ["", ""]).slice(); }
    function pickColor(color) {
        const colors = draftColors.slice();
        colors[pickedRole] = color;
        draftColors = colors;
    }
    onPickerWallpaperChanged: resetPicks()
    Connections {
        target: root.manager
        function onPickedAccentColorsChanged() { root.resetPicks(); }
    }

    component Caption: Text {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        font.family: Config.theme.font
        font.pixelSize: Styling.fontSize(-1)
        color: Colors.overSurfaceVariant
    }

    component Action: SettingsButton {
        property bool selected: false
        highlighted: selected
        Layout.fillWidth: true
    }

    component ColorAction: Action {
        id: colorButton
        required property color swatchColor
        readonly property color inkColor: {
            const linear = v => v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
            const c = swatchColor;
            return 0.2126 * linear(c.r) + 0.7152 * linear(c.g) + 0.0722 * linear(c.b) > 0.179 ? "#000000" : "#ffffff";
        }
        background: Rectangle {
            color: colorButton.swatchColor
            radius: Styling.radius(-4)
            border.width: colorButton.selected || colorButton.activeFocus ? 3 : 1
            border.color: colorButton.selected || colorButton.activeFocus ? colorButton.inkColor : Colors.outline
        }
        contentItem: Text {
            text: colorButton.text
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(-1)
            color: colorButton.inkColor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    component ColorSection: SettingsGroup { Layout.minimumWidth: 0; Layout.alignment: Qt.AlignTop }





    GridLayout {
        id: paletteGrid
        objectName: "palette-sections"
        Layout.fillWidth: true
        columns: root.width >= 620 ? 2 : 1
        columnSpacing: Styling.spacing(12)
        rowSpacing: Styling.spacing(12)
        ColorSection {
            title: "Palette"
            objectName: "palette-page-palette"
            collapsible: false
            property string settingsAnchor: "palette"
            Layout.columnSpan: !collapsible || expanded ? paletteGrid.columns : 1
            RowLayout {
                Action {
                    text: "Dark"
                    selected: !Config.theme.lightMode
                    onClicked: Config.theme.lightMode = false
                }
                Action {
                    text: "Light"
                    selected: Config.theme.lightMode
                    onClicked: Config.theme.lightMode = true
                }
                Action {
                    text: "OLED blacks"
                    selected: Config.oledMode
                    enabled: !Config.theme.lightMode
                    onClicked: Config.theme.oledMode = !Config.theme.oledMode
                }
            }
            Caption { text: "Wallpaper scheme" }
            SettingsComboBox {
                id: schemeSelector
                Layout.fillWidth: true
                enabled: root.manager !== null
                model: PaletteSchemes.schemes
                textRole: "label"
                valueRole: "id"
                currentIndex: PaletteSchemes.schemes.findIndex(scheme => scheme.id === (root.manager?.currentMatugenScheme ?? "scheme-tonal-spot"))
                palette.button: Colors.surface
                palette.buttonText: Colors.overSurface
                palette.base: Colors.surface
                palette.text: Colors.overSurface
                palette.highlight: Colors.primary
                palette.highlightedText: Colors.overPrimary
                onActivated: root.manager.setMatugenScheme(currentValue)
            }
            Caption {
                visible: root.preset !== ""
                text: "Preset active: " + root.preset + ". Choose a wallpaper scheme to resume wallpaper colors."
            }
            RowLayout {
                Action {
                    text: root.busy ? "Generating…" : "Regenerate colors"
                    enabled: root.manager !== null && !root.busy && root.preset === "" && !!root.manager.currentWallpaper
                    onClicked: root.manager.runMatugenForCurrentWallpaper()
                }
                Action {
                    text: "Choose wallpaper / preset"
                    onClicked: {
                        GlobalStates.settingsWindowVisible = false;
                        GlobalShortcuts.toggleWallpapers();
                    }
                }
            }
            Caption {
                visible: !!root.manager?.paletteError
                text: root.manager?.paletteError ?? ""
                color: Colors.error
            }
            RowLayout {
                Repeater {
                    model: ["background", "surface", "primary", "secondary", "tertiary", "overSurface"]
                    delegate: StyledRect {
                        id: paletteSwatch
                        variant: "common"
                        required property string modelData
                        Layout.fillWidth: true
                        implicitHeight: 36
                        radius: Styling.radius(-4)
                        fillColor: Colors[modelData]
                        backgroundOpacity: 1
                        StyledToolTip {
                            show: hover.hovered
                            tooltipText: paletteSwatch.modelData + ": " + paletteSwatch.fillColor
                        }
                        HoverHandler { id: hover }
                    }
                }
            }
        }
        ColorSection {
            title: "Pick wallpaper colors"
            objectName: "palette-page-picker"
            property string settingsAnchor: "picker"
            Layout.columnSpan: !collapsible || expanded ? paletteGrid.columns : 1
            Caption {
                text: "Select Main or Accent, then click the wallpaper. Matugen builds your theme from these colors, and the bonsai uses the same pair. Picks are saved for each wallpaper."
            }
            RowLayout {
                ColorAction {
                    swatchColor: root.draftColors[0] || Colors.primary
                    text: "Main: " + (root.draftColors[0] || "Auto")
                    selected: root.pickedRole === 0
                    onClicked: root.pickedRole = 0
                }
                ColorAction {
                    swatchColor: root.draftColors[1] || Colors.secondary
                    text: "Accent: " + (root.draftColors[1] || "Auto")
                    selected: root.pickedRole === 1
                    onClicked: root.pickedRole = 1
                }
            }
            StyledRect {
                Layout.fillWidth: true
                implicitHeight: Math.max(240, Math.min(420, width * 0.55))
                variant: "common"
                clip: true
                WallpaperSampler {
                    id: wallpaperSampler
                    anchors.fill: parent
                    anchors.margins: 6
                    source: root.pickerSource ? "file://" + root.pickerSource.split("/").map(encodeURIComponent).join("/") : ""
                    onPicked: color => root.pickColor(color)
                }
                Caption {
                    anchors.centerIn: parent
                    width: parent.width - 24
                    horizontalAlignment: Text.AlignHCenter
                    visible: !wallpaperSampler.ready
                    text: !root.pickerSource ? "Choose a wallpaper to pick its colors." :
                        wallpaperSampler.failed ? "Wallpaper preview is unavailable. You can still choose a custom color." : "Loading wallpaper…"
                }
            }
            Caption {
                visible: wallpaperSampler.suggestedColors.length > 0
                text: "Wallpaper color options · choose for " + (root.pickedRole === 0 ? "Main" : "Accent")
            }
            GridLayout {
                Layout.fillWidth: true
                columns: width >= 560 ? 4 : width >= 320 ? 3 : 2
                columnSpacing: Styling.spacing(6)
                rowSpacing: Styling.spacing(6)
                Repeater {
                    model: wallpaperSampler.suggestedColors
                    delegate: Button {
                        id: suggestedSwatch
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 100
                        Layout.minimumWidth: 0
                        contentItem: Text {
                            text: suggestedSwatch.modelData.toUpperCase()
                            font.family: Config.theme.monoFont
                            font.pixelSize: Styling.fontSize(-1)
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            color: {
                                const c = Qt.color(suggestedSwatch.modelData);
                                const linear = v => v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                                return 0.2126 * linear(c.r) + 0.7152 * linear(c.g) + 0.0722 * linear(c.b) > 0.179 ? "#000000" : "#ffffff";
                            }
                        }
                        Accessible.name: "Use " + modelData + " as " + (root.pickedRole === 0 ? "main" : "accent")
                        onClicked: root.pickColor(modelData)
                        background: Rectangle {
                            color: suggestedSwatch.modelData
                            radius: Styling.radius(-4)
                            border.width: suggestedSwatch.activeFocus || root.draftColors[root.pickedRole] === suggestedSwatch.modelData ? 3 : 1
                            border.color: suggestedSwatch.activeFocus || root.draftColors[root.pickedRole] === suggestedSwatch.modelData ? Colors.overSurface : Colors.outline
                        }
                        StyledToolTip {
                            show: suggestedSwatch.hovered
                            tooltipText: suggestedSwatch.modelData
                        }
                    }
                }
            }
            RowLayout {
                Action {
                    text: "−"
                    enabled: wallpaperSampler.ready && wallpaperSampler.zoom > 1
                    onClicked: wallpaperSampler.zoomAt(0.8, wallpaperSampler.width / 2, wallpaperSampler.height / 2)
                }
                Caption { text: Math.round(wallpaperSampler.zoom * 100) + "%"; horizontalAlignment: Text.AlignHCenter }
                Action {
                    text: "+"
                    enabled: wallpaperSampler.ready && wallpaperSampler.zoom < 8
                    onClicked: wallpaperSampler.zoomAt(1.25, wallpaperSampler.width / 2, wallpaperSampler.height / 2)
                }
                Action { text: "Fit"; onClicked: wallpaperSampler.resetView() }
            }
            Caption { text: "Ctrl+scroll over the preview to zoom; drag to move around, then click to pick a color." }
            RowLayout {
                Rectangle {
                    implicitWidth: 24
                    implicitHeight: 24
                    radius: Styling.radius(-4)
                    color: wallpaperSampler.hoverColor || root.draftColors[root.pickedRole] ||
                           (root.pickedRole === 0 ? Colors.primary : Colors.secondary)
                    border.color: Colors.outline
                }
                Caption { text: wallpaperSampler.hoverColor || root.draftColors[root.pickedRole] || "Automatic color" }
                Action {
                    Layout.fillWidth: false
                    text: "Custom color…"
                    onClicked: {
                        customColor.selectedColor = root.draftColors[root.pickedRole] || (root.pickedRole === 0 ? Colors.primary : Colors.secondary);
                        customColor.open();
                    }
                }
                Action {
                    Layout.fillWidth: false
                    text: "Auto"
                    onClicked: root.pickColor("")
                }
            }
            RowLayout {
                Action {
                    text: root.busy ? "Applying…" : "Apply picked colors"
                    enabled: root.manager !== null && !!root.pickerWallpaper && !root.busy && root.draftColors.some(color => color !== "")
                    onClicked: root.manager.setPickedAccentColors(root.draftColors)
                }
                Action {
                    text: "Use automatic colors"
                    enabled: root.manager !== null && !!root.pickerWallpaper && !root.busy
                    onClicked: {
                        root.draftColors = ["", ""];
                        root.manager.setPickedAccentColors(root.draftColors);
                    }
                }
            }
            Caption { text: "Use arrow keys on the preview and Enter to pick; Shift moves faster. The bonsai updates in new terminals." }
            ColorDialog {
                id: customColor
                title: root.pickedRole === 0 ? "Choose main color" : "Choose accent color"
                onAccepted: root.pickColor(selectedColor.toString())
            }
        }
        ColorSection {
            title: "Saved appearances"
            objectName: "palette-page-presets"
            property string settingsAnchor: "presets"
            Layout.columnSpan: !collapsible || expanded ? paletteGrid.columns : 1
            Caption { text: "Save your current wallpaper, monitor overrides, colors and shell appearance together. Apply picked colors before saving." }
            SettingsTextField {
                id: presetName
                Layout.fillWidth: true
                placeholderText: "Preset name"
                Accessible.name: "New appearance preset name"
                maximumLength: 80
            }
            Action {
                text: "Save current appearance"
                enabled: !!root.manager && !!root.pickerWallpaper && !root.busy && !!presetName.text.trim()
                    && !root.manager.appearancePresets.some(entry => entry.name === presetName.text.trim())
                onClicked: {
                    if (root.manager.saveAppearancePreset(presetName.text)) presetName.clear();
                }
            }
            Caption {
                visible: !!root.manager && root.manager.appearancePresets.some(entry => entry.name === presetName.text.trim())
                text: "That name is already saved. Use Replace current below to update it."
            }
            Repeater {
                model: root.manager?.appearancePresets ?? []
                delegate: ColumnLayout {
                    id: savedPreset
                    required property var modelData
                    Layout.fillWidth: true
                    StyledText { text: savedPreset.modelData.name; Layout.fillWidth: true; elide: Text.ElideRight }
                    RowLayout {
                        Layout.fillWidth: true
                        Action { text: "Apply"; enabled: !root.busy; onClicked: root.manager.applyAppearancePreset(savedPreset.modelData.name) }
                        Action { text: "Replace current"; enabled: !root.busy && !!root.pickerWallpaper; onClicked: root.manager.saveAppearancePreset(savedPreset.modelData.name, true) }
                        Action { text: "Delete"; onClicked: root.manager.deleteAppearancePreset(savedPreset.modelData.name) }
                    }
                }
            }

        }
        ColorSection {
            title: "Wallpaper library"
            objectName: "palette-page-wallpaper"
            property string settingsAnchor: "wallpaper"
            Layout.columnSpan: !collapsible || expanded ? paletteGrid.columns : 1
            // Wallpaper Path
            RowLayout {
                Layout.fillWidth: true
                spacing: Styling.spacing(8)

                StyledText {
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: "Folder"
                    font.family: Config.theme.font
                    font.pixelSize: Styling.fontSize(0)
                    color: Colors.overBackground
                    Layout.preferredWidth: 80
                }

                StyledRect {
                    variant: "common"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
                    radius: Styling.radius(-2)

                    TextInput {
                        renderType: Text.NativeRendering
                        font.hintingPreference: Font.PreferFullHinting
                        id: wallPathInput
                        objectName: "palette-wallpaper-folder"
                        Accessible.name: "Wallpaper folder"
                        anchors.fill: parent
                        anchors.margins: 8
                        font.family: Config.theme.font
                        font.pixelSize: Styling.fontSize(0)
                        color: Colors.overBackground
                        selectByMouse: true
                        clip: true
                        verticalAlignment: TextInput.AlignVCenter

                        // Placeholder for default path
                        StyledText {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            text: "Default"
                            font: parent.font
                            color: Colors.overSurfaceVariant
                            visible: !parent.text && !parent.activeFocus
                        }

                        text: GlobalStates.wallpaperManager?.wallpaperDir ?? ""

                        onEditingFinished: {
                            GlobalStates.wallpaperManager?.setWallpaperDirectory(text);
                        }
                    }
                }
            }


        }
        ColorSection {
            title: "App appearance"
            objectName: "palette-page-apps"
            property string settingsAnchor: "apps"
            Layout.columnSpan: !collapsible || expanded ? paletteGrid.columns : 1
            SettingsToggleRow {
                label: "Tint icons"
                description: "Use the theme palette for supported icons."
                checked: Config.theme.tintIcons
                onToggled: checked => Config.theme.tintIcons = checked
            }


            Caption { text: "Background opacity: " + Math.round(Config.theme.srBg.opacity * 100) + "%" }
            ThemeSlider {
                wheelEnabled: false
                Layout.fillWidth: true
                from: 0.2
                to: 1
                stepSize: 0.05
                value: Config.theme.srBg.opacity
                onMoved: Config.theme.srBg.opacity = value
            }
            Caption {
                text: "Opacity applies to supported app backgrounds. The islands bar keeps its transparent outer background."
            }
            Text {
                text: "Connected apps"
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(0)
                font.bold: true
                color: Colors.overSurface
            }
            Caption {
                text: "Updates live: QuickShell, Niri borders, Kitty, fish, fuzzy search, GTK and VS Code. Spotify refreshes through Spicetify after setup."
            }
            Caption {
                text: "Reopen Zen after a palette change. Fuzzel and btop use new colors on launch; some Qt and KDE apps need reopening."
            }
            Action {
                text: "Refresh app themes"
                onClicked: {
                    Colors.refreshApps();
                    refreshNotice.restart();
                }
            }
            Caption {
                visible: refreshNotice.running
                text: "Refreshing apps with the current palette."
            }
            Timer { id: refreshNotice; interval: 3000 }

        }
    }
}
