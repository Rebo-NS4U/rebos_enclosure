const fs = require('node:fs');
const assert = require('node:assert/strict');
const source = fs.readFileSync('system/apps/shell/scripts/lyrics_plus_extension.js', 'utf8');
const block = source.slice(source.indexOf('            if (command.playlist_write && !writing)'), source.indexOf('            if (command.suggestion && !suggesting)'));
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
const run = new AsyncFunction('command', 'Spicetify', 'fetch', 'written', 'let writing = false;' + block);
const uri = 'spotify:track:' + 'b'.repeat(22);
(async () => {
    let calls = [], replies = [], written = new Map();
    const api = {CosmosAsync:{put:async (url, data) => calls.push(['put', url, data]), post:async (url, data) => calls.push(['post', url, data])}};
    const fetch = async (_, data) => {replies.push(JSON.parse(data.body));};
    const job = {id:'one', uri:'spotify:playlist:'+'a'.repeat(22), tracks:Array(201).fill(uri)};
    await run({playlist_write:job}, api, fetch, written);
    assert.deepEqual(calls.map(c => [c[0], c[2].uris.length]), [['put',100],['post',100],['post',1]]);
    assert.ok(calls[0][1].endsWith('/items'));
    assert.equal(replies[0].error, '');
    await run({playlist_write:job}, api, fetch, written);
    assert.equal(calls.length, 3); // Retried acknowledgement must not repeat remote writes.
    await run({playlist_write:{...job,id:'empty',tracks:[]}}, api, fetch, written);
    assert.deepEqual(calls.at(-1)[2].uris, []);
    const failed = {CosmosAsync:{put:async()=>{throw Error('403 Forbidden');}}};
    await run({playlist_write:{...job,id:'failed'}}, failed, fetch, written);
    assert.match(replies.at(-1).error, /403 Forbidden/);
    const before = calls.length;
    await run({playlist_write:{...job,id:'invalid',tracks:['file:///private']}}, api, fetch, written);
    assert.equal(calls.length, before);
    assert.match(replies.at(-1).error, /Invalid playlist/);
    console.log('Playlist writes: ordered batches, clearing, errors, validation and duplicate delivery passed');
})().catch(error => {console.error(error); process.exitCode=1;});
