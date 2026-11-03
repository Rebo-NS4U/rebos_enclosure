// App-private normal browser verification; never fabricate challenge tokens.
const { chromium } = require(process.env.HOME + '/.local/share/anime-streamer/browser/node_modules/playwright');
const fs = require('fs');
const readline = require('readline');
const profile = process.env.HOME + '/.local/share/anime-streamer/primewire-browser';
fs.mkdirSync(profile, {recursive:true, mode:0o700});
fs.chmodSync(profile, 0o700);
const input = readline.createInterface({input:process.stdin});
input.once('line', async line => {
    let context;
    let timer;
    const finish = result => process.stdout.write(JSON.stringify(result) + '\n');
    try {
        const config = JSON.parse(line);
        if (!/^https:\/\/primewire\.mov\/(?:movie|tv|embed)\//.test(config.url)) throw Error('Invalid Primewire page');
        context = await chromium.launchPersistentContext(profile, {headless:false, viewport:{width:1100,height:780}, acceptDownloads:false});
        process.on('SIGTERM', async () => { await context.close().catch(()=>{}); process.exit(0); });
        const page = context.pages()[0] || await context.newPage();
        let master = null;
        let allowedKeys = new Set();
        let eligibleRelease = false;
        let settled = false;
        let resolve;
        const selected = new Promise(r => resolve=r);
        const minimum = Math.max(120, Number(config.expected || 0) * .65);
        const headersFor = async request => {
            const all = await request.allHeaders();
            const headers = {};
            for (const key of ['user-agent','referer','origin','cookie','authorization']) if (all[key]) headers[key] = all[key];
            return headers;
        };
        context.on('response', async response => {
            if (settled || ![200,206].includes(response.status())) return;
            const type = (response.headers()['content-type'] || '').toLowerCase();
            const url = response.url();
            try {
                const parsed = new URL(url);
                if (parsed.origin === 'https://primewire.mov' && parsed.pathname === '/api/v1/s') {
                    const data = await response.json();
                    allowedKeys = new Set((data.servers || []).filter(server => {
                        const language = String(server.audio_language || '').toLowerCase();
                        const quality = String(server.quality || '').toUpperCase();
                        return ['en','eng','english'].includes(language) && !['CAM','TS','TC','HDCAM','HDTS'].includes(quality)
                            && !/\b(?:HDCAM|HDTS|TELESYNC|TELECINE|CAMRIP)\b|[. _\[]CAM[. _\]]/i.test(server.file_name || '');
                    }).map(server => server.key));
                    return;
                }
                if (parsed.origin === 'https://primewire.mov' && parsed.pathname === '/api/v1/l') {
                    eligibleRelease = allowedKeys.has(parsed.searchParams.get('key'));
                    master = null;
                    return;
                }
                if (!eligibleRelease) return;
                if (type.includes('mpegurl') || /\.m3u8(?:\?|$)/i.test(url)) {
                    const body = await response.text();
                    if (!body.trimStart().startsWith('#EXTM3U')) return;
                    const headers = await headersFor(response.request());
                    if (body.includes('#EXT-X-STREAM-INF')) { master = {url,headers}; return; }
                    const duration = Array.from(body.matchAll(/#EXTINF:([\d.]+)/g)).reduce((n,m)=>n+Number(m[1]),0);
                    if (duration >= minimum && body.includes('#EXT-X-ENDLIST')) {
                        settled = true;
                        resolve({url:master?.url || url, headers:master?.headers || headers, duration, format:'hls'});
                    }
                } else if (type.startsWith('video/') && Number(response.headers()['content-length'] || 0) > 20000000) {
                    // A direct file is verified again by the Python media probe.
                    settled = true;
                    resolve({url,headers:await headersFor(response.request()),duration:0,format:'file'});
                }
            } catch (_) { /* Ignore unrelated/closed ad requests. */ }
        });
        await page.goto(config.url, {waitUntil:'domcontentloaded',timeout:45000});
        timer = setTimeout(()=>resolve(null), 150000);
        const stream = await selected;
        clearTimeout(timer);
        if (!stream) throw Error('No full video was selected. Complete the browser verification and start the video, then retry.');
        // Keep only this app's selected source headers; no browser-profile export.
        finish({ok:true,stream});
    } catch (error) {
        finish({ok:false,error:error.message?.includes('No full video') ? error.message : 'Could not open Primewire verification. Close its old verification window and retry.'});
    } finally {
        clearTimeout(timer);
        if (context) await context.close().catch(()=>{});
        input.close();
    }
});
