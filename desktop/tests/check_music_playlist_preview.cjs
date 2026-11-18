// Exercise explicit playlist loading independently of visible Daily Mix cards.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('system/apps/shell/scripts/lyrics_plus_extension.js', 'utf8');
const uri = 'spotify:playlist:' + 'c'.repeat(22);
const track = {track: {uri: 'spotify:track:' + 'b'.repeat(22), name: 'Song', artists: [{name: 'Artist'}]}};
const intervals = [], posts = [], offsets = [];
let fail = false;
const context = {
    console, Date,
    document: {documentElement: {}, querySelectorAll: () => []},
    MutationObserver: class {observe() {}}, clearTimeout() {}, setTimeout() {},
    setInterval: (fn, ms) => intervals.push({fn, ms}),
    Spicetify: {Platform: {PlaylistAPI: {
        getMetadata: async () => ({name: 'My playlist'}),
        getContents: async (requested, {offset}) => {
            assert.equal(requested, uri); offsets.push(offset);
            if (fail) throw Error('Access denied');
            return offset === 0 ? {items: Array(100).fill(track), totalLength: 102}
                : {items: [track, {track: null}], totalLength: 102};
        }
    }}},
    fetch: async (_, options) => {
        if (options.method === 'POST') {
            posts.push(JSON.parse(options.body)); return {ok: true};
        }
        return {ok: true, json: async () => ({refresh_id: 'load', playlist_uri: uri})};
    }
};
(async () => {
    vm.runInNewContext(source, context);
    await new Promise(resolve => setImmediate(resolve));
    const poll = intervals.find(t => t.ms === 5000).fn;
    await poll();
    assert.deepEqual(offsets, [0, 100]);
    const result = posts.find(p => p.refresh_id === 'load');
    assert.equal(result.mixes.length, 1);
    assert.equal(result.mixes[0].uri, uri);
    assert.equal(result.mixes[0].name, 'My playlist');
    assert.equal(result.mixes[0].tracks.length, 101);
    posts.length = 0; fail = true;
    await poll();
    assert.equal(posts[0].mixes.length, 0);
    assert.match(posts[0].error, /Could not load playlist/);
    console.log('Playlist loading, pagination, unavailable tracks and access failure passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
