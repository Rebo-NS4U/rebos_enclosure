const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const qml = fs.readFileSync(path.join(__dirname, '../../system/apps/shell/modules/widgets/music/MusicWindow.qml'), 'utf8');
const body = qml.split('readonly property var suggestedTracks: {')[1].split('    function refreshSuggestions()')[0].trim().slice(0, -1);
const suggest = new Function('page', 'detail', 'playlists', 'tracks', 'spotifySuggestions', body);
const tracks = [
 {path:'a', title:'One', artist:'Artist'},
 {path:'b', title:'Two', artist:'ARTIST'},
 {path:'c', title:'Two', artist:'Artist'},
 {path:'d', title:'Other', artist:'Different'},
 {path:'e', title:'One', artist:'Artist'}
];
const spotify = {playlist:'downloaded', tracks:[{uri:'spotify:track:'+'b'.repeat(22),title:'Two',artist:'Artist'}, {uri:'spotify:track:'+'c'.repeat(22),title:'One',artist:'Artist'}]};
const lists = [{id:'downloaded', paths:['a']}];
assert.deepEqual(suggest('Playlist','downloaded',lists,tracks,spotify).map(t=>t.title), ['Two']);
assert.deepEqual(suggest('Songs','downloaded',lists,tracks,spotify), []);
assert.deepEqual(suggest('Playlist','missing',lists,tracks,spotify), []);
lists[0].paths.push('b');
assert.deepEqual(suggest('Playlist','downloaded',lists,tracks,spotify), []);
const many = {playlist:'downloaded', tracks:Array.from({length:120}, (_,i)=>({uri:'track:'+i,title:'Choice '+i,artist:'New artist'}))};
assert.equal(suggest('Playlist','downloaded',lists,tracks,many).length,100);
console.log('Spotify suggestions: remote tracks, duplicate exclusion, navigation and add removal passed');

(async () => {
 const adapter = fs.readFileSync(path.join(__dirname, '../../system/apps/shell/scripts/lyrics_plus_extension.js'), 'utf8');
 const block = adapter.slice(adapter.indexOf('            if (command.suggestion && !suggesting)'), adapter.indexOf('            if (command.refresh_id)'));
 const run = new (Object.getPrototypeOf(async function(){}).constructor)('command','Spicetify','fetch','let suggesting = false;'+block);
 let posted;
 await run({suggestion:{id:'job',uri:'spotify:playlist:'+'a'.repeat(22)}}, {Platform:{PlaylistAPI:{getRecommendedTracks:async(uri, skip, limit)=> {
   assert.equal(uri,'spotify:playlist:'+'a'.repeat(22)); assert.equal(limit,100);
   return [{uri:'spotify:track:'+'z'.repeat(22),name:'New Spotify song',artists:[{name:'New artist'}]}];
 }}}}, async(url, options)=>{posted=JSON.parse(options.body);});
 assert.equal(posted.suggestion_id,'job'); assert.equal(posted.tracks[0].title,'New Spotify song');
 await run({suggestion:{id:'error',uri:'spotify:playlist:'+'a'.repeat(22)}}, {Platform:{PlaylistAPI:{}}}, async(url, options)=>{posted=JSON.parse(options.body);});
 assert.match(posted.error,/Could not load Spotify suggestions/);
 console.log('Spotify recommendation adapter request, metadata and failure handling passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
