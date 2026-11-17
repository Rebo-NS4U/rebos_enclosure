const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const qml = fs.readFileSync(path.join(__dirname, '../../system/apps/shell/modules/widgets/music/MusicWindow.qml'), 'utf8');
const body = qml.split('readonly property var suggestedTracks: {')[1].split('    readonly property var albums:')[0].trim().slice(0, -1);
const suggest = new Function('page', 'detail', 'playlists', 'tracks', body);
const tracks = [
 {path:'a', title:'One', artist:'Artist'},
 {path:'b', title:'Two', artist:'ARTIST'},
 {path:'c', title:'Two', artist:'Artist'},
 {path:'d', title:'Other', artist:'Different'},
 {path:'e', title:'One', artist:'Artist'}
];
const lists = [{id:'downloaded', paths:['a']}];
assert.deepEqual(suggest('Playlist','downloaded',lists,tracks).map(t=>t.path), ['b']);
assert.deepEqual(suggest('Songs','downloaded',lists,tracks), []);
assert.deepEqual(suggest('Playlist','missing',lists,tracks), []);
lists[0].paths.push('b');
assert.deepEqual(suggest('Playlist','downloaded',lists,tracks), []);
console.log('Playlist suggestions: artist matching, duplicate exclusion, navigation and add removal passed');
