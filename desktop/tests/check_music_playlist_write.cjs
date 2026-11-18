const fs = require('node:fs');
const assert = require('node:assert/strict');
const vm = require('node:vm');

const source = fs.readFileSync('system/apps/shell/scripts/lyrics_plus_extension.js', 'utf8');
const playlist = 'spotify:playlist:' + 'a'.repeat(22);
const tracks = Array.from({length: 201}, (_, i) => 'spotify:track:' + String(i).padStart(22, '0'));
let rows = [];
let command;
const calls = [];
const replies = [];
const api = {
    async resync() {},
    async getContents(_, {offset, limit}) {
        return {items: rows.slice(offset, offset + limit), totalLength: rows.length};
    },
    async add(uri, items, location) {
        assert.equal(uri, playlist);
        assert.equal(location.after, 'end');
        calls.push(['add', items.length]);
        rows.push(...Array.from(items, track => ({uri: track, uid: track})));
    },
    async remove(uri, items) {
        assert.equal(uri, playlist);
        calls.push(['remove', items.length]);
        const removed = new Set(Array.from(items, item => item.uid));
        rows = rows.filter(row => !removed.has(row.uid));
    }
};
const intervals = new Map();
const context = vm.createContext({
    Spicetify: {Platform: {PlaylistAPI: api}},
    MutationObserver: class { observe() {} },
    document: {documentElement: {}, querySelectorAll: () => []},
    setTimeout() {},
    setInterval(callback, delay) { intervals.set(delay, callback); },
    fetch: async (_, options) => {
        if (options.method === 'POST') replies.push(JSON.parse(options.body));
        return {ok: true, json: async () => command};
    }
});
vm.runInContext(source, context);

async function write(id, items) {
    command = {playlist_write: {id, uri: playlist, tracks: items}};
    await intervals.get(5000)();
    assert.equal(replies.at(-1).playlist_write_id, id);
    return replies.at(-1).error;
}

(async () => {
    assert.equal(await write('one', tracks), '');
    assert.deepEqual(calls, [['add', 100], ['add', 100], ['add', 1]]);
    assert.deepEqual(rows.map(row => row.uri), tracks);
    assert.equal(await write('one', tracks), '');
    assert.equal(calls.length, 3);
    assert.equal(await write('empty', []), '');
    assert.deepEqual(calls.slice(3), [['remove', 100], ['remove', 100], ['remove', 1]]);
    assert.deepEqual(rows, []);
    api.add = async () => { throw Error('403 Forbidden'); };
    assert.match(await write('failed', tracks), /403 Forbidden/);
    const before = calls.length;
    assert.match(await write('invalid', ['file:///private']), /Invalid playlist/);
    assert.equal(calls.length, before);
    console.log('Playlist writes: ordered batches, clearing, errors, validation and duplicate delivery passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
