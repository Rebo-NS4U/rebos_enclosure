"""Apply the approved component geometry to GTK, Qt widgets and browser chrome."""
import json
import re
from pathlib import Path

from apply_desktop_palette import update_ini, write


def metrics(home):
    try:
        theme = json.loads((home / '.config/enclosure/shell/config/theme.json').read_text())
    except (OSError, ValueError):
        theme = {}
    font = str(theme.get('font', 'JetBrains Mono'))
    # Keep font names safe in CSS, INI and QFont serialization.
    if not re.fullmatch(r'[\w .+-]{1,80}', font):
        font = 'JetBrains Mono'
    def number(key, default, low, high):
        try:
            return max(low, min(high, int(theme.get(key, default))))
        except (TypeError, ValueError):
            return default
    return {'font': font, 'size': number('fontSize', 14, 8, 32),
            'radius': number('roundness', 16, 0, 40),
            'duration': number('animDuration', 300, 0, 2000)}


def gtk_css(p, m):
    roles = {'accent_color': 'primary', 'accent_bg_color': 'primary',
             'accent_fg_color': 'overPrimary', 'theme_selected_bg_color': 'primary',
             'theme_selected_fg_color': 'overPrimary',
             'theme_unfocused_selected_bg_color': 'primary',
             'theme_unfocused_selected_fg_color': 'overPrimary',
             'window_bg_color': 'background', 'window_fg_color': 'overSurface',
             'headerbar_bg_color': 'background', 'headerbar_fg_color': 'overSurface',
             'popover_bg_color': 'surface', 'popover_fg_color': 'overSurface',
             'view_bg_color': 'surfaceContainerLowest', 'view_fg_color': 'overSurface',
             'card_bg_color': 'surfaceContainer', 'card_fg_color': 'overSurface',
             'sidebar_bg_color': 'surfaceContainerLowest', 'sidebar_fg_color': 'overSurface',
             'sidebar_border_color': 'outlineVariant', 'sidebar_backdrop_color': 'surface',
             'error_color': 'error', 'error_bg_color': 'error', 'error_fg_color': 'overError'}
    base = '/* Enclosure standard: generated from the active desktop theme. */\n'
    base += ''.join(f'@define-color {name} {p.get(role, p["overSurface"])};\n' for name, role in roles.items())
    r = m['radius']
    rgb = ', '.join(str(int(p['background'][i:i+2], 16)) for i in (1, 3, 5))
    alpha = max(0, min(1, float(p.get('opacity', 1))))
    css = base + f'''
* {{ font-family: "{m['font']}"; font-size: {m['size']}px; }}
window.background {{ background-color: rgba({rgb}, {alpha}); color: @window_fg_color; }}
menu, .menu, popover > contents {{
  background-color: @popover_bg_color; color: @popover_fg_color;
  border: 1px solid {p['outlineVariant']}; border-radius: {r}px; padding: 6px;
  box-shadow: 0 8px 24px alpha(black, 0.25);
}}
menuitem, modelbutton, popover row {{
  min-height: 24px; padding: 8px 12px; border-radius: {r}px;
  color: @window_fg_color;
}}
menuitem:hover, modelbutton:hover, popover row:hover, row:hover {{
  background-color: {p['surfaceContainerHigh']}; color: @window_fg_color;
}}
menuitem:disabled, button:disabled, entry:disabled {{ opacity: 0.45; }}
button {{
  min-height: 24px; padding: 7px 14px; border-radius: {r}px;
  background-image: none; background-color: {p['surfaceContainer']};
  color: @window_fg_color; border: 1px solid {p['outlineVariant']}; box-shadow: none;
}}
button:hover {{ background-color: {p['surfaceContainerHigh']}; }}
button:active, button:checked, button.suggested-action {{ background-color: @accent_bg_color; color: @accent_fg_color; }}
button.destructive-action {{ background-color: @error_bg_color; color: @error_fg_color; }}
button.flat {{ background-color: transparent; border-color: transparent; }}
button.flat:hover {{ background-color: {p['surfaceContainerHigh']}; }}
entry, spinbutton, textview.view {{
  min-height: 30px; padding: 8px 12px; border-radius: {r}px;
  background-color: {p['surfaceContainerLowest']}; color: @view_fg_color;
  border: 1px solid {p['outlineVariant']}; box-shadow: none;
}}
entry:focus, button:focus, spinbutton:focus {{ border-color: @accent_color; outline: 1px solid @accent_color; outline-offset: -1px; }}
entry.error {{ border-color: @error_color; }}
row, treeview.view {{ color: @view_fg_color; }}
row:selected, treeview.view:selected, iconview:selected {{ background-color: @accent_bg_color; color: @accent_fg_color; }}
notebook > header {{ background-color: {p['surfaceContainerLowest']}; }}
notebook > header tab {{ padding: 8px 14px; border-radius: {r}px; }}
notebook > header tab:checked {{ background-color: {p['surfaceContainerHigh']}; color: @accent_color; }}
check, radio {{ min-width: 18px; min-height: 18px; border: 1px solid {p['outline']}; background-color: {p['surfaceContainerLowest']}; }}
check {{ border-radius: {r}px; }} radio {{ border-radius: 99px; }}
check:checked, radio:checked, switch:checked {{ background-color: @accent_bg_color; color: @accent_fg_color; }}
switch {{ border-radius: 99px; background-color: {p['surfaceContainerHigh']}; }}
scale trough, progressbar trough {{ background-color: {p['surfaceContainerHigh']}; border-radius: 99px; }}
scale highlight, progressbar progress {{ background-color: @accent_color; border-radius: 99px; }}
tooltip, tooltip.background {{ background-color: @popover_bg_color; color: @popover_fg_color; border: 1px solid {p['outlineVariant']}; border-radius: {r}px; }}
separator {{ background-color: {p['outlineVariant']}; min-height: 1px; }}
'''
    return base, css


def qt_css(p, m):
    r = m['radius']
    bg, fg, pane, focus = (p[k] for k in ('background', 'overSurface', 'surfaceContainer', 'surfaceContainerHigh'))
    accent, on = p['primary'], p['overPrimary']
    return f'''/* Enclosure standard — generated; app content remains app-owned. */
QWidget {{ font-family: "{m['font']}"; font-size: {m['size']}px; }}
QMenu, QToolTip {{ background: {p['surface']}; color: {fg}; border: 1px solid {p['outlineVariant']}; border-radius: {r}px; padding: 6px; }}
QMenu::item {{ min-height: 24px; padding: 8px 28px 8px 12px; margin: 1px; border-radius: {r}px; }}
QMenu::item:selected {{ background: {focus}; color: {fg}; }}
QMenu::item:disabled {{ color: {p['outline']}; }}
QMenu::separator {{ height: 1px; background: {p['outlineVariant']}; margin: 4px 8px; }}
QMenuBar {{ background: {bg}; color: {fg}; }}
QMenuBar::item {{ padding: 8px 12px; border-radius: {r}px; background: transparent; }}
QMenuBar::item:selected {{ background: {focus}; }}
QPushButton, QToolButton {{ min-height: 24px; padding: 7px 14px; border-radius: {r}px; border: 1px solid {p['outlineVariant']}; background: {pane}; color: {fg}; }}
QPushButton:hover, QToolButton:hover {{ background: {focus}; }}
QPushButton:default, QPushButton:checked, QToolButton:checked {{ background: {accent}; color: {on}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {p['outline']}; background: {pane}; }}
QPushButton:focus, QToolButton:focus {{ border: 2px solid {accent}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ min-height: 30px; padding: 8px 12px; border-radius: {r}px; border: 1px solid {p['outlineVariant']}; background: {p['surfaceContainerLowest']}; color: {fg}; selection-background-color: {accent}; selection-color: {on}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 2px solid {accent}; }}
QComboBox QAbstractItemView {{ padding: 6px; background: {p['surface']}; color: {fg}; selection-background-color: {focus}; selection-color: {fg}; border: 1px solid {p['outlineVariant']}; }}
QAbstractItemView {{ background: {p['surfaceContainerLowest']}; color: {fg}; selection-background-color: {accent}; selection-color: {on}; alternate-background-color: {pane}; }}
QListView::item, QTreeView::item {{ min-height: 32px; padding: 4px; }}
QTabBar::tab {{ padding: 8px 14px; background: {pane}; color: {fg}; border-radius: {r}px; }}
QTabBar::tab:selected {{ background: {focus}; color: {accent}; }}
QHeaderView::section {{ padding: 8px; background: {pane}; color: {fg}; border: none; }}
QProgressBar {{ border: 1px solid {p['outlineVariant']}; border-radius: {r}px; background: {pane}; color: {fg}; text-align: center; }}
QProgressBar::chunk {{ background: {accent}; border-radius: {r}px; }}
'''


def browser_css(p, m):
    return f'''\n/* Enclosure standard components */
#navigator-toolbox, menupopup, panel, #urlbar, #searchbar {{ font-family: "{m['font']}" !important; font-size: {m['size']}px !important; }}
menupopup, panel {{ --panel-background: {p['surface']} !important; --panel-color: {p['overSurface']} !important; --panel-border-color: {p['outlineVariant']} !important; --panel-border-radius: {m['radius']}px !important; }}
menupopup > menuitem, menupopup > menu, .subviewbutton {{ min-height: 32px !important; padding: 6px 12px !important; border-radius: {m['radius']}px !important; }}
menupopup > menuitem[_moz-menuactive="true"], menupopup > menu[_moz-menuactive="true"], .subviewbutton:hover {{ background-color: {p['surfaceContainerHigh']} !important; color: {p['overSurface']} !important; }}
#urlbar-background, #searchbar {{ border-radius: {m['radius']}px !important; }}
'''


def apply(p, home):
    m = metrics(home)
    cfg = home / '.config'
    base, css = gtk_css(p, m)
    for version in (3, 4):
        directory = cfg / f'gtk-{version}.0'
        write(directory / 'enclosure-standard.css', css)
        write(directory / 'colors.css', base)
        target = directory / 'gtk.css'
        old = target.read_text() if target.exists() else ''
        # Retain custom CSS; replace only the previous owned generated file.
        if old.startswith('/* GTK Colors generated by rebos_shell */'):
            old = ''
        include = '@import url("enclosure-standard.css");'
        if include not in old:
            write(target, include + '\n' + old)
        update_ini(directory / 'settings.ini', {'Settings': {
            'gtk-font-name': f'{m["font"]} {m["size"] * .75:g}'}})
    stylesheet = cfg / 'enclosure/theme/widgets.qss'
    write(stylesheet, qt_css(p, m))
    for version in (5, 6):
        target = cfg / f'qt{version}ct/qt{version}ct.conf'
        # qtct uses a QStringList; retain user stylesheets, replacing only ours.
        text = target.read_text() if target.exists() else ''
        match = re.search(r'^stylesheets=(.*)$', text, re.M)
        previous = match.group(1).strip() if match else ''
        entries = [x.strip() for x in previous.split(',') if x.strip() and x.strip() != '@Invalid()' and x.strip() != str(stylesheet)]
        entries.append(str(stylesheet))
        weight = 50 if version == 5 else 400
        font = f'"{m["font"]},{m["size"]*.75:g},-1,5,{weight},0,0,0,0,0"'
        update_ini(target, {'Fonts': {'general': font, 'fixed': font},
                            'Interface': {'stylesheets': ', '.join(entries)}})
    update_ini(cfg / 'kdeglobals', {'General': {
        'font': f'{m["font"]},{m["size"]*.75:g},-1,5,50,0,0,0,0,0',
        'menuFont': f'{m["font"]},{m["size"]*.75:g},-1,5,50,0,0,0,0,0'}})
    update_ini(cfg / 'fuzzel/fuzzel.ini', {'main': {'font': f'{m["font"]}:size={m["size"]*.75:g}'},
                                           'border': {'radius': m['radius'], 'width': 1}})
    from apply_app_palette import zen_profiles, patch_jsonc, read_jsonc
    for profile in zen_profiles(home):
        target = profile / 'chrome/rebos_shell.css'
        if target.exists():
            old = target.read_text().split('/* Enclosure standard components */')[0].rstrip()
            write(target, old + '\n' + browser_css(p, m))
    vscode = cfg / 'Code/User/settings.json'
    if vscode.exists():
        custom = read_jsonc(vscode.read_text()).get('workbench.colorCustomizations', {}).copy()
        custom.update({'menu.selectionBackground': p['surfaceContainerHigh'], 'menu.selectionForeground': p['overSurface'], 'menu.border': p['outlineVariant'], 'menu.separatorBackground': p['outlineVariant'], 'dropdown.border': p['outlineVariant'], 'focusBorder': p['primary']})
        write(vscode, patch_jsonc(vscode.read_text(), {'workbench.colorCustomizations': custom}))
    report = {'source': 'System Theme Playground', 'metrics': m,
              'adapters': ['GTK3', 'GTK4', 'Qt5 widgets', 'Qt6 widgets', 'KDE palette', 'Fuzzel', 'Zen chrome', 'VS Code colors'],
              'limits': ['App-provided or sandboxed themes can override toolkit rules.',
                         'Qt Quick apps need their own shared QML components.',
                         'Proprietary clients and games require app-specific support.',
                         'Running apps that cache styles may need a later manual reopen.']}
    write(home / '.cache/rebos_shell/theme-standard-status.json', json.dumps(report, indent=2) + '\n')
