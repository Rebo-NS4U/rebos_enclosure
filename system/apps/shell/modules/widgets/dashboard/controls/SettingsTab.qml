pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.theme
import QtQuick.Effects
import qs.modules.components
import qs.modules.services
import qs.config
import qs.modules.globals
import "SettingsCrawler.js" as SettingsCrawler

Item {
    id: root
    implicitWidth: 400
    implicitHeight: 300
    // Section IDs stay stable for saved selections and search links, including GitHub (10).

    property int currentSection: GlobalStates.settingsCurrentTab
    property int selectedIndex: -1
    property bool syncingSelection: false
    Component.onCompleted: openSection(currentSection, "")
    property string searchQuery: ""

    onFilteredSectionsChanged: {
        if (searchQuery.length > 0) {
            syncingSelection = true;
            selectedIndex = filteredSections.length ? 0 : -1;
            syncingSelection = false;
            activateSelection();
        } else {
            syncSelection();
        }
    }

    function syncSelection() {
        syncingSelection = true;
        selectedIndex = searchQuery.length > 0
            ? filteredSections.findIndex(item => item.section === currentSection)
            : categoryModel.findIndex(item => item.sections.includes(currentSection));
        syncingSelection = false;
        scrollSidebarToSelection();
    }

    function openSection(section, subSection) {
        if (section === 5) {
            section = subSection === "performance" ? 4 : 6;
            subSection = subSection === "system" ? "storage" : subSection || "weather";
        }
        currentSection = section;
        GlobalStates.settingsCurrentTab = section;
        dispatchSubSection(section, subSection);
        syncSelection();
    }

    // Timer to restore focus after panel transitions
    Timer {
        id: focusRestoreTimer
        interval: 50
        onTriggered: searchInput.focusInput()
    }

    onSelectedIndexChanged: if (!syncingSelection) activateSelection()

    function activateSelection(): void {
        if (!filteredSections || selectedIndex < 0 || selectedIndex >= filteredSections.length)
            return;
        const item = filteredSections[selectedIndex];
        root.openSection(item.section, item.subSection);
        root.scrollSidebarToSelection();
        focusRestoreTimer.restart();
    }

    Connections {
        target: GlobalStates
        function onSettingsCurrentTabChanged() {
            if (root.currentSection !== GlobalStates.settingsCurrentTab)
                root.openSection(GlobalStates.settingsCurrentTab, "");
        }
    }

    // Focus the search input (called from parent Dashboard)
    function focusSearchInput() {
        searchInput.focusInput();
    }

    SettingsIndex {
        id: searchIndex
    }

    // Dynamic Settings Indexer
    Item {
        id: settingsIndexer
        visible: false // Headless

        property int currentPanelIndex: 0
        property var aggregatedItems: []
        property bool isIndexing: false

        // Helper to load panels one by one
        Loader {
            id: indexerLoader
            active: settingsIndexer.isIndexing
            asynchronous: true
            source: settingsIndexer.isIndexing && settingsIndexer.currentPanelIndex < contentArea.panelComponents.length ? contentArea.panelComponents[settingsIndexer.currentPanelIndex].component : ""

            onStatusChanged: {
                if (status === Loader.Ready && item) {
                    // Scrape
                    const sectionId = contentArea.panelComponents[settingsIndexer.currentPanelIndex].section;
                    const newItems = SettingsCrawler.crawl(item, sectionId);
                    settingsIndexer.aggregatedItems = settingsIndexer.aggregatedItems.concat(newItems);

                    // Move to next
                    settingsIndexer.currentPanelIndex++;
                } else if (status === Loader.Error) {
                    console.warn("Failed to load panel for indexing:", source);
                    settingsIndexer.currentPanelIndex++;
                }
            }
        }

        onCurrentPanelIndexChanged: {
            if (currentPanelIndex >= contentArea.panelComponents.length) {
                // Done
                if (isIndexing) {
                    isIndexing = false;
                    searchIndex.addDynamicItems(aggregatedItems);
                }
            }
        }

        Component.onCompleted: {
            // Start indexing after a short delay to allow UI to settle
            indexingTimer.start();
        }

        Timer {
            id: indexingTimer
            interval: 500
            onTriggered: {
                settingsIndexer.isIndexing = true;
            }
        }
    }

    // Store pending subsection to apply when panel loads
    property string pendingSubSection: ""

    function dispatchSubSection(sectionId, subSectionId) {
        root.pendingSubSection = subSectionId || "";
        Qt.callLater(scrollToSelection);
    }

    function scrollToSelection() {
        for (let i = 0; i < categoryPanels.count; i++) {
            const loader = categoryPanels.itemAt(i);
            if (loader.sectionId !== currentSection || !loader.item) continue;
            if (loader.item.currentSection !== undefined) loader.item.currentSection = pendingSubSection;
            Qt.callLater(() => {
                if (loader.item.scrollToSection) loader.item.scrollToSection();
                const inner = loader.scrollContent;
                const offset = loader.item.sectionOffset ?? (inner ? inner.contentY : 0);
                if (inner) inner.contentY = 0;
                categoryScroll.contentY = Math.max(0, Math.min(loader.y + offset, categoryScroll.contentHeight - categoryScroll.height));
            });
        }
    }

    function combineThemeDropdowns() {
        let theme = null, shell = null;
        for (let i = 0; i < categoryPanels.count; i++) {
            const loader = categoryPanels.itemAt(i);
            if (loader.sectionId === 4) theme = loader.item;
            if (loader.sectionId === 6) shell = loader.item;
        }
        if (theme && shell) {
            theme.combinedSettings = true;
            shell.groupContainer = theme.dropdownGrid;
            shell.overlayContainer = contentArea;
        }
        Qt.callLater(scrollToSelection);
    }

    // Scroll sidebar to ensure visible selection
    function scrollSidebarToSelection() {
        if (searchResults.visible && selectedIndex >= 0)
            searchResults.positionViewAtIndex(selectedIndex, ListView.Contain);
    }

    // Fuzzy match: checks if all characters of query appear in order in target
    function fuzzyMatch(query, target) {
        if (query.length === 0)
            return true;
        if (target.length === 0)
            return false;
        const lowerQuery = query.toLowerCase();
        const lowerTarget = target.toLowerCase();
        let queryIndex = 0;
        for (let i = 0; i < lowerTarget.length && queryIndex < lowerQuery.length; i++) {
            if (lowerTarget[i] === lowerQuery[queryIndex]) {
                queryIndex++;
            }
        }
        return queryIndex === lowerQuery.length;
    }

    // Score a fuzzy match (higher is better)
    function fuzzyScore(query, target) {
        if (query.length === 0)
            return 0;
        if (target.length === 0)
            return -1;
        const lowerQuery = query.toLowerCase();
        const lowerTarget = target.toLowerCase();

        // Exact match gets highest score
        if (lowerTarget.includes(lowerQuery))
            return 1000 + (100 - target.length);

        // Fuzzy scoring
        let queryIndex = 0, score = 0, consecutive = 0, maxConsecutive = 0;
        for (let i = 0; i < lowerTarget.length && queryIndex < lowerQuery.length; i++) {
            if (lowerTarget[i] === lowerQuery[queryIndex]) {
                queryIndex++;
                consecutive++;
                maxConsecutive = Math.max(maxConsecutive, consecutive);
                if (i === 0 || " -_".includes(lowerTarget[i - 1]))
                    score += 10;
            } else {
                consecutive = 0;
            }
        }
        return queryIndex === lowerQuery.length ? score + maxConsecutive * 5 : -1;
    }

    readonly property var categoryModel: [
        {label: "Theme & appearance", subLabel: "Colors, wallpaper and shell style", icon: Icons.paintBrush, isIcon: true, section: 4, sections: [4, 6]},
        {label: "Desktop & system", subLabel: "Displays, shortcuts and window rules", icon: Icons.layout, isIcon: true, section: 9, sections: [9, 7, 8]},
        {label: "Devices & connections", subLabel: "Wi-Fi, Bluetooth and audio", icon: Icons.wifiHigh, isIcon: true, section: 0, sections: [0, 1, 2]},
        {label: "Assistant & GitHub", subLabel: "AI preferences and repositories", icon: Icons.robot, isIcon: true, section: 3, sections: [3, 10]}
    ]
    readonly property var activeCategory: categoryModel.find(item => item.sections.includes(currentSection)) || categoryModel[0]
    readonly property var categoryPages: activeCategory.sections.map(id => sectionModel.find(item => item.section === id))

    // Original sections model
    readonly property var sectionModel: [
        {
            icon: Icons.paintBrush,
            label: "Appearance",
            section: 4,
            isIcon: true
        },
        {
            icon: Icons.gear,
            label: "Panels & widgets",
            section: 6,
            isIcon: true
        },
        {
            icon: Icons.layout,
            label: "Display",
            section: 9,
            isIcon: true
        },
        {
            icon: Icons.keyboard,
            label: "Keyboard shortcuts",
            section: 7,
            isIcon: true
        },
        {
            icon: Icons.layout,
            label: "Window rules",
            section: 8,
            isIcon: true
        },
        {
            icon: Icons.wifiHigh,
            label: "Network",
            section: 0,
            isIcon: true
        },
        {
            icon: Icons.bluetooth,
            label: "Bluetooth",
            section: 1,
            isIcon: true
        },
        {
            icon: Icons.faders,
            label: "Sound",
            section: 2,
            isIcon: true
        },
        {
            icon: Icons.robot,
            label: "Assistant",
            section: 3,
            isIcon: true
        },
        {
            icon: Icons.circuitry,
            label: "GitHub",
            section: 10,
            isIcon: true
        }
    ]

    // Filtered sections based on search query
    readonly property var filteredSections: {
        if (searchQuery.length === 0)
            return categoryModel;

        const query = searchQuery.toLowerCase();
        return searchIndex.items.filter(item => {
            return fuzzyMatch(query, item.label) || (item.keywords && item.keywords.includes(query));
        }).map(item => {
            // Find section metadata
            const sectionMeta = sectionModel.find(s => s.section === item.section) || {};
            return {
                label: item.label,
                section: item.section,
                subSection: item.subSection || "",
                subLabel: item.subLabel || "",
                // Use section icon instead of item icon
                icon: sectionMeta.icon || item.icon,
                isIcon: sectionMeta.isIcon !== undefined ? sectionMeta.isIcon : (item.isIcon !== undefined ? item.isIcon : true),
                score: fuzzyScore(query, item.label)
            };
        }).sort((a, b) => b.score - a.score);
    }

    // Find the index of current section in filtered list
    function getFilteredIndex(sectionId) {
        for (let i = 0; i < filteredSections.length; i++) {
            if (filteredSections[i].section === sectionId)
                return i;
        }
        return -1;
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            StyledText { text: "Settings"; font.pixelSize: Styling.fontSize(14); font.bold: true; Layout.fillWidth: true }
            SearchInput {
                id: searchInput
                Layout.preferredWidth: Math.min(380, root.width * 0.5)
                placeholderText: "Find a setting…"
                clearOnEscape: true

                onSearchTextChanged: text => {
                    root.searchQuery = text;
                }
                // ESC to escape dashboard
                onEscapePressed: {
                    searchInput.focus = false;
                    root.forceActiveFocus();
                }

                onAccepted: {
                    // If single result, select it; if multiple, select top one
                    if (root.filteredSections.length > 0) {
                        const item = root.filteredSections[root.selectedIndex];
                        root.openSection(item.section, item.subSection);
                    }
                }

                onDownPressed: {
                    if (root.selectedIndex < root.filteredSections.length - 1) {
                        root.selectedIndex++;
                    } else {
                        root.selectedIndex = 0;
                    }
                }

                onUpPressed: {
                    if (root.selectedIndex > 0) {
                        root.selectedIndex--;
                    } else {
                        root.selectedIndex = root.filteredSections.length - 1;
                    }
                }
            }
        }
        Flow {
            id: mainTabs
            objectName: "settings-main-tabs"
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: root.categoryModel
                delegate: SettingsButton {
                    required property var modelData
                    objectName: "settings-category-" + modelData.section
                    text: modelData.label
                    highlighted: modelData.sections.includes(root.currentSection)
                    onClicked: root.openSection(modelData.section, "")
                }
            }
        }
        ListView {
            id: searchResults
            objectName: "settings-search-results"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, root.height * 0.3)
            visible: root.searchQuery.length > 0
            clip: true
            model: visible ? root.filteredSections : []
            currentIndex: root.selectedIndex
            ScrollBar.vertical: ScrollBar {}
            delegate: SettingsButton {
                required property var modelData
                required property int index
                width: searchResults.width
                text: modelData.label + (modelData.subLabel ? " · " + modelData.subLabel : "")
                highlighted: index === root.selectedIndex
                onClicked: root.openSection(modelData.section, modelData.subSection)
            }
        }
        // Content area with animated transitions
        Item {
            id: contentArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            property int previousSection: 0
            readonly property int maxContentWidth: Math.max(0, width - 24)

            // Track section changes for animation direction
            onVisibleChanged: {
                if (visible) {
                    contentArea.previousSection = root.currentSection;
                }
            }

            Connections {
                target: root
                function onCurrentSectionChanged() {
                    contentArea.previousSection = root.currentSection;
                }
            }

            // Panel definitions for Loader
            readonly property var panelComponents: [
                {
                    component: "WifiPanel.qml",
                    section: 0
                },
                {
                    component: "BluetoothPanel.qml",
                    section: 1
                },
                {
                    component: "AudioMixerPanel.qml",
                    section: 2
                },
                {
                    component: "../../config/AiPanel.qml",
                    section: 3
                },
                {
                    component: "ThemePanel.qml",
                    section: 4
                },
                {
                    component: "SystemPanel.qml",
                    section: 5
                },
                {
                    component: "ShellPanel.qml",
                    section: 6
                },
                {
                    component: "KeybindingsPanel.qml",
                    section: 7
                },
                {
                    component: "WindowRulesPanel.qml",
                    section: 8
                },
                {
                    component: "DisplayPanel.qml",
                    section: 9
                },
                {
                    component: "GithubPanel.qml",
                    section: 10
                }
            ]

            Column {
                id: categoryHeading
                visible: root.width < 1280
                width: parent.width
                spacing: 6
                StyledText { text: root.activeCategory.label; font.pixelSize: Styling.fontSize(10); font.bold: true }
                StyledText { text: root.activeCategory.subLabel; color: Colors.overSurfaceVariant; width: parent.width; wrapMode: Text.WordWrap }
            }

            // Wheel input belongs to navigation. This layer accepts no clicks or drags.
            MouseArea {
                id: wheelNavigation
                objectName: "settings-scroll-wheel"
                scrollGestureEnabled: true
                enabled: {
                    for (let i = 0; i < categoryPanels.count; i++) {
                        if (categoryPanels.itemAt(i)?.item?.colorPickerActive) return false;
                    }
                    return true;
                }
                anchors.fill: categoryScroll
                z: 2
                acceptedButtons: Qt.NoButton
                onWheel: wheel => {
                    const delta = wheel.pixelDelta.y !== 0 ? wheel.pixelDelta.y : wheel.angleDelta.y / 2;
                    if (delta === 0 || (wheel.modifiers & Qt.ControlModifier)) { wheel.accepted = false; return; }
                    function scrollerAt(item) {
                        if (!item.visible || !item.enabled) return null;
                        const point = item.mapFromItem(wheelNavigation, wheel.x, wheel.y);
                        if (item.clip && !item.contains(point)) return null;
                        // Prefer the deepest list that can still scroll in this direction.
                        for (let i = item.children.length - 1; i >= 0; i--) {
                            const nested = scrollerAt(item.children[i]);
                            if (nested) return nested;
                        }
                        if (item.interactive && item.contentY !== undefined && item.contentHeight > item.height && item.contains(point)) {
                            const start = item.originY || 0;
                            const end = start + item.contentHeight - item.height;
                            if ((delta > 0 && item.contentY > start) || (delta < 0 && item.contentY < end)) return item;
                        }
                        return null;
                    }
                    const target = scrollerAt(categoryScroll.contentItem) || categoryScroll;
                    const start = target.originY || 0;
                    target.cancelFlick();
                    target.contentY = Math.max(start, Math.min(start + Math.max(0, target.contentHeight - target.height), target.contentY - delta));
                    wheel.accepted = true;
                }
            }

            Flickable {
                id: categoryScroll
                objectName: "settings-category-scroll"
                anchors.fill: parent
                anchors.topMargin: categoryHeading.visible ? categoryHeading.height + 20 : 0
                clip: true
                contentHeight: categoryColumn.height
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                Column {
                    id: categoryColumn
                    width: parent.width
                    spacing: Styling.spacing(32)
                    Repeater {
                        id: categoryPanels
                        model: root.activeCategory.sections
                        delegate: Loader {
                            id: categoryLoader
                            required property int modelData
                            readonly property int sectionId: modelData
                            objectName: "settings-panel-" + sectionId
                            width: categoryColumn.width
                            readonly property var scrollContent: item ? Array.from(item.children).find(child => child.contentHeight !== undefined && child.contentY !== undefined) || null : null
                            // Unroll ordinary panel scrollers; device lists retain their own bounded viewport.
                            readonly property bool expandContent: sectionId !== 7 && scrollContent !== null && scrollContent.model === undefined
                            height: item?.groupContainer ? 0 : expandContent ? Math.max(1, scrollContent.contentHeight) : Math.max(500, categoryScroll.height)
                            source: contentArea.panelComponents[sectionId]?.component ?? ""
                            asynchronous: true
                            onLoaded: {
                                item.maxContentWidth = Qt.binding(() => contentArea.maxContentWidth);
                                if (expandContent) {
                                    scrollContent.interactive = false;
                                    scrollContent.clip = false;
                                }
                                Qt.callLater(root.combineThemeDropdowns);
                            }
                        }
                    }
                }
            }

        }
    }
}
