// Verify hourly collection and Music's manual command with a simulated Spotify client.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('system/apps/shell/scripts/lyrics_plus_extension.js', 'utf8').split('// Daily Mix metadata only.')[1];
let now = 3600000, calls = 0, command = '', posts = [];
const intervals = [];
const settle = () => new Promise(resolve => setImmediate(resolve));
const context = {
    Date: {now: () => now}, console,
    document: {documentElement: {}, querySelectorAll: () => [{textContent: 'Daily Mix 1',
        closest: () => null, parentElement: null,
        getAttribute: key => key === 'href' ? '/playlist/' + 'a'.repeat(22) : ''}]},
    MutationObserver: class {observe() {}}, clearTimeout() {}, setTimeout() {},
    setInterval: (fn, ms) => intervals.push({fn, ms}),
    Spicetify: {Platform: {PlaylistAPI: {getContents: async () => {
        calls++;
        return {items: [{track: {uri: 'spotify:track:' + 'b'.repeat(22), name: 'Song', artists: []}}]};
    }}}},
    fetch: async (url, options) => {
        if (options.method === 'POST') {
            const body = JSON.parse(options.body); posts.push(body);
            if (body.refresh_id === command) command = '';
            return {ok: true};
        }
        return {ok: true, json: async () => ({refresh_id: command})};
    }
};
(async () => {
    vm.runInNewContext("//" + source, context);
    await settle(); assert.equal(calls, 1);
    const scheduled = intervals.find(t => t.ms === 60000).fn;
    now += 3599999; await scheduled(); assert.equal(calls, 1);
    now++; await scheduled(); assert.equal(calls, 2);
    command = 'manual-request';
    await intervals.find(t => t.ms === 5000).fn();
    assert.equal(calls, 3);
    assert(posts.some(p => p.refresh_id === 'manual-request' && p.mixes.length === 1));
    console.log('Hourly schedule and immediate manual refresh passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
