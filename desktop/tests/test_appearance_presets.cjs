const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../system/apps/shell/modules/widgets/dashboard/wallpapers/Wallpaper.qml'), 'utf8');
const functions = source.slice(source.indexOf('    function saveAppearancePreset'), source.indexOf('    function scanColorPresets'));
const adapter = {appearancePresets: [], wallpaperAccentColors: {'/wall.png': ['#123456', '']}};
const state = {wallpaperAdapter: adapter, currentWallpaper: '/wall.png', paletteBusy: false,
    perScreenWallpapers: {DP1: '/other.png'}, currentMatugenScheme: 'scheme-tonal-spot',
    activeColorPreset: '', wallpaperMode: 'crop', tintEnabled: true,
    presetThemeKeys: ['lightMode'], Config: {theme: {lightMode: true, srBg: {opacity: 0.7}}},
    Qt: {callLater: f => f()}, setWallpaper(p) { this.applied = p; },
    setWallpaperMode(p) { this.mode = p; }, runMatugenForCurrentWallpaper() {}, applyColorPreset() {}};
state.setWallpaper = p => { state.applied = p; };
state.setWallpaperMode = p => { state.mode = p; };
Object.defineProperty(state, 'appearancePresets', {get: () => adapter.appearancePresets});
vm.createContext(state);
vm.runInContext(functions, state);
assert.equal(state.saveAppearancePreset('  Evening  '), true);
assert.equal(state.saveAppearancePreset('Evening'), false);
assert.equal(state.saveAppearancePreset('   '), false);
state.perScreenWallpapers.DP1 = '/changed.png';
assert.equal(adapter.appearancePresets[0].screens.DP1, '/other.png');
// JSON round trip represents a fresh load from the persistent JsonAdapter.
adapter.appearancePresets = JSON.parse(JSON.stringify(adapter.appearancePresets));
state.Config.theme.lightMode = false;
state.applyAppearancePreset('Evening');
assert.equal(state.Config.theme.lightMode, true);
assert.equal(state.Config.theme.srBg.opacity, 0.7);
assert.equal(state.applied, '/wall.png');
assert.equal(adapter.perScreenWallpapers.DP1, '/other.png');
assert.equal(adapter.wallpaperAccentColors['/wall.png'][0], '#123456');
state.currentWallpaper = '/replacement.png';
assert.equal(state.saveAppearancePreset('Evening', true), true);
assert.equal(adapter.appearancePresets.length, 1);
assert.equal(adapter.appearancePresets[0].wallpaper, '/replacement.png');
state.paletteBusy = true;
assert.equal(state.saveAppearancePreset('Busy'), false);
state.deleteAppearancePreset('Evening');
assert.equal(adapter.appearancePresets.length, 0);
console.log('Appearance presets: save, duplicate protection, restore, replace, delete passed');
