"""Request routing for the menu's JSON-lines API, independent of playback state."""
import hashlib
import io
import json
import math
import re
from urllib.parse import quote, urlparse, parse_qs

import app
import youtube_account
import media_sources
import media_download
import torbox_source
from PIL import Image
from gi.repository import GLib
from live_subtitles import CAPTION_LANGUAGES

def clean(text):
    return re.sub(r'\s+', ' ', app.html.unescape(re.sub(r'<[^>]+>', ' ', text))).strip()


def parse_details(page):
    description = re.search(r'<span class="item-head">Overview:</span>\s*<div class="text">(.*?)</div>', page, re.S)
    info = []
    for block in re.split(r'<div class="item\b', page)[1:]:
        head = re.search(r'<span class="item-head">(.*?)</span>', block, re.S)
        if head and clean(head[1]) != 'Overview:':
            content = block[head.end():].split('</div>', 1)[0]
            value = clean(content)
            if value:
                info.append(clean(head[1]) + ' ' + value)
        if len(info) >= 12:
            break
    return dict(description=clean(description[1]) if description else '', metadata=info)


def resume_index(episodes, entry):
    saved = entry.get('episode')
    index = episodes.index(saved) if saved in episodes else 0
    if entry.get('completed') and index + 1 < len(episodes):
        index += 1
    return index


def anime_season(show, season_id, history):
    seasons = sorted(json.loads(show['seasonEntries']),
                     key=lambda season: (season.get('final', False), season['number'], season['part']))
    entry = history.get(show['id'], {})
    if not entry:
        legacy = next((key for key in reversed(history) if any(season['id'] == key for season in seasons)), '')
        if legacy:
            entry = dict(history[legacy], episode=f"{legacy}:{history[legacy]['episode']}")
    saved_season = entry.get('episode', '').partition(':')[0]
    selected = next((season for season in seasons if season['id'] == (season_id or saved_season)), None)
    if selected is None:
        if season_id:
            raise ValueError('Choose an available season')
        selected = seasons[0]
    provider_id = selected['id']
    data = dict(show=show, seasons=seasons, seasonId=provider_id, episodes=[], episodeLabels={}, warning='')
    try:
        numbers = app.ani_bridge('episodes', provider_id)
        data['episodeLabels'] = {f'{provider_id}:{number}': f'Episode {number}' for number in numbers}
        data['episodes'] = list(data['episodeLabels'])
    except Exception as error:
        data['warning'] = 'Episodes unavailable: ' + str(error)
    data['resumeIndex'] = resume_index(data['episodes'], entry if saved_season == provider_id else {})
    return data


def anime_details(show, history):
    try:
        related = app.catalogue('most-popular', show['title'], 1)
        show = next(group for group in app.anime_groups([show, *related]) if group['id'] == show['id'])
    except (OSError, RuntimeError):
        pass  # Already discovered seasons still work when catalogue search is unavailable.
    data = anime_season(show, '', history)
    try:
        data.update(parse_details(app.fetch(app.BASE + '/' + quote(data['seasonId'], safe='')).decode()))
    except Exception as error:
        data['warning'] += ' Show information unavailable: ' + str(error)
    return data


def card_selection(show, history):
    entry = history.get(show['id'], {}) or history.get(show.get('historyId', ''), {})
    if media_sources.kind_of(show) == 'youtube':
        url = media_sources.youtube_url(show['url'])
        parsed = urlparse(url)
        # Feed cards already contain everything needed to play a single video.
        # Playlist/channel cards still need enumeration before queue selection.
        if (parse_qs(parsed.query).get('v') or
                (parsed.hostname == 'youtu.be' and parsed.path.strip('/'))) and 'list' not in parse_qs(parsed.query):
            return dict(show, episodeLabels={url: show['title']}), [url], 0
    if show.get('seasonEntries'):
        data = anime_season(show, '', history)
        entry = {'episode': data['episodes'][data['resumeIndex']]} if data['episodes'] else {}
    elif media_sources.kind_of(show) == 'anime':
        data = dict(episodes=app.ani_bridge('episodes', show['id']))
    else:
        data = media_sources.details(show, app.fetch, entry.get('episode'))
    episodes = data['episodes']
    if not episodes:
        raise ValueError('No playable videos or episodes are available for this title.')
    show = dict(data.get('show') or show, episodeLabels=data.get('episodeLabels') or {})
    return show, episodes, resume_index(episodes, entry)


class MenuRequest:
    """Keep one request's routing, replies and asynchronous callbacks together."""
    def __init__(self, request, engine, send):
        self.request, self.engine, self.send = request, engine, send

    def result(self, data):
        request = self.request
        self.send(dict(event=request.get('action'), request=request.get('request', 0),
                       data=data, client=request.get('_client')))

    def fail(self, error):
        request = self.request
        message = dict(event='error', action=request.get('action'), request=request.get('request', 0),
                       text=str(error), client=request.get('_client'))
        if request.get('action') == 'settings':
            message['settings'] = dict(self.engine.settings)
        self.send(message)

    def handle_catalogue(self):
        request = self.request
        engine = self.engine
        send = self.send
        result = self.result
        fail = self.fail
        request_id = request.get("request", 0)
        def catalogue_ready(data):
            result(data)
            if kind in ('movies', 'tv'):
                items = data if isinstance(data, list) else data['items']
                media_sources.refresh_availability(items, lambda labels: send(dict(
                    event='availability', request=request_id, data=labels, client=request.get('_client'))))
                if isinstance(data, dict) and data.get('hasMore'):
                    media_sources.discovery_catalogue.prefetch(kind, category, page + 1, app.fetch, query)
        category = request.get('category', 'most-popular')
        query = request.get('query', '')
        kind = request.get('kind', 'anime')
        if kind not in media_sources.KINDS:
            raise ValueError('Unsupported media type')
        filters = app.validate_filters(request.get('filters', {})) if kind == 'anime' else {}
        if category == 'history' and not query and not filters:
            history = list(reversed([entry['show'] for entry in engine.history.values() if media_sources.kind_of(entry['show']) == kind]))
            if kind in ('movies', 'tv'):
                engine.background(lambda: media_sources.direct_source.filter_history(history), catalogue_ready, fail)
            else:
                result(app.anime_groups(history) if kind == 'anime' else history)
        else:
            page = max(1, int(request.get('page', 1)))
            def load_catalogue():
                if kind != 'anime':
                    return media_sources.catalogue(kind, category, query, page, fetch=app.fetch, check_availability=False)
                items = app.catalogue(category, query, page, filters)
                return dict(items=app.anime_groups(items), hasMore=bool(items))
            engine.background(load_catalogue, catalogue_ready, fail)


    def handle_details(self):
        request = self.request
        engine = self.engine
        result = self.result
        fail = self.fail
        show_id = request['show']['id']
        def details():
            if request['show'].get('seasonEntries'):
                return anime_details(request['show'], engine.history)
            entry = engine.history.get(show_id, {}) or engine.history.get(request['show'].get('historyId', ''), {})
            if media_sources.kind_of(request['show']) != 'anime':
                data = media_sources.details(request['show'], app.fetch, entry.get('episode'))
                data['resumeIndex'] = resume_index(data['episodes'], entry)
                return data
            # Metadata and episode failures remain independent.
            data = dict(description='', metadata=[], episodes=[], warning='')
            try:
                data.update(parse_details(app.fetch(app.BASE + '/' + quote(show_id, safe='')).decode()))
            except Exception as error:
                data['warning'] = 'Show information unavailable: ' + str(error)
            try:
                data['episodes'] = app.ani_bridge('episodes', show_id)
            except Exception as error:
                data['warning'] += ' Episodes unavailable: ' + str(error)
            entry = engine.history.get(show_id, {})
            data['resumeIndex'] = resume_index(data['episodes'], entry)
            return data
        def details_ready(data):
            result(data)
            if media_sources.kind_of(request['show']) == 'youtube' and data.get('episodes'):
                index = data.get('resumeIndex', 0)
                episode = data['episodes'][index]
                engine.resolve((show_id, episode, engine.settings['mode'], engine.settings['quality']),
                               lambda links: None, lambda error: None)
        engine.background(details, details_ready, fail)


    def handle_season(self):
        request = self.request
        engine = self.engine
        result = self.result
        fail = self.fail
        show = request['show']
        def load_season():
            season_id = str(request['seasonId'])
            if show.get('seasonEntries'):
                return anime_season(show, season_id, engine.history)
            if media_sources.kind_of(show) != 'tv':
                raise ValueError('Season selection requires a series')
            return media_sources.season_episodes(show, season_id)
        engine.background(load_season, result, fail)


    def handle_quick_play(self):
        request = self.request
        engine = self.engine
        result = self.result
        fail = self.fail
        show = request['show']
        engine.stop()
        token = engine.play_token
        engine.ensure_player(token)
        engine.play_status.set_text('Preparing ' + show['title'] + '…')
        def start(selection):
            if token == engine.play_token:
                selected, episodes, index = media_sources.youtube_queue(*selection, request.get('queue', []))
                engine.current = None
                engine.start_episode(selected, episodes, index, token)
                result(True)
        def failed(error):
            if token == engine.play_token:
                engine.discard_preparing_player(token)
                engine.play_status.set_text(str(error))
                fail(error)
        engine.background(lambda: card_selection(show, engine.history), start, failed)


    def handle_play(self):
        request = self.request
        engine = self.engine
        result = self.result
        show, episodes = request['show'], request['episodes']
        index = int(request['index'])
        if index < 0 or index >= len(episodes):
            raise ValueError('Choose an available episode')
        engine.stop()
        engine.current = None
        show, episodes, index = media_sources.youtube_queue(show, episodes, index, request.get('queue', []))
        engine.start_episode(show, episodes, index, engine.play_token)
        result(True)


    def handle_downloads(self):
        self.engine.background(media_download.list_downloads, self.result, self.fail)

    def handle_trash_download(self):
        name = self.request.get('name')
        self.engine.background(lambda: media_download.trash_download(name), self.result, self.fail)

    def handle_download(self):
        engine = self.engine
        if engine.download_active:
            return
        request = self.request
        show = request['show']
        episode = request['episode']
        if not isinstance(episode, str) or not episode:
            raise ValueError('Choose an available episode')
        title = engine.media_title(show, episode)
        mode, quality = engine.settings['mode'], engine.settings['quality']
        self.start_download('Downloading · ' + title)
        self.download_episode(show, episode, title, mode, quality,
                              lambda path: self.download_status(False, 'Saved to ' + path),
                              self.download_failed)

    def start_download(self, text):
        self.download_job = self.engine.download_job = media_download.Download()
        self.download_status(True, text)

    def handle_stop_download(self):
        download = self.engine.download_job
        if download is not None:
            download.cancel()
            self.download_status(False, 'Download stopped.')

    def download_status(self, active, text):
        self.engine.download_active = active
        if not active:
            self.engine.download_job = None
        self.send(dict(event='download', active=active, text=text))

    def download_failed(self, message):
        if not self.download_job.cancelled.is_set():
            self.download_status(False, 'Download failed: ' + message)

    def download_episode(self, show, episode, title, mode, quality, done, failed):
        engine = self.engine
        download = self.download_job

        def on_done(path):
            if not download.cancelled.is_set():
                done(path)

        def on_failed(message):
            if not download.cancelled.is_set():
                failed(message)

        def transfer(write):
            if not download.cancelled.is_set():
                engine.background(lambda: media_download.save(title, write, download), on_done, on_failed)

        try:
            kind = media_sources.kind_of(show)
            if kind == 'youtube':
                transfer(lambda path: media_download.download_youtube(episode, quality, path, download))
            else:
                key = engine.source_key(show, episode, {'mode': mode, 'quality': quality})
                engine.resolve(key,
                               lambda links: transfer(lambda path: media_download.download_stream(links, kind, path, download)),
                               on_failed)
        except Exception as error:
            on_failed(str(error))

    def handle_download_season(self):
        engine = self.engine
        if engine.download_active:
            return
        show = self.request['show']
        if media_sources.kind_of(show) != 'tv':
            raise ValueError('Season downloads require a TV show')
        season_id = str(self.request['seasonId'])
        mode, quality = engine.settings['mode'], engine.settings['quality']
        season_title = 'Specials' if season_id == '0' else 'Season ' + season_id
        title = show['title'] + ' · ' + season_title

        def download_season(data):
            if self.download_job.cancelled.is_set():
                return
            episodes = list(dict.fromkeys(data['episodes']))
            if not episodes:
                self.download_failed('No episodes are available for ' + title)
                return
            saved = 0
            failures = []

            def next_episode(index):
                if self.download_job.cancelled.is_set():
                    return
                if index == len(episodes):
                    text = f'{title} · Saved {saved} of {len(episodes)} episodes'
                    if failures:
                        text += ' · Failed: ' + ', '.join(failures)
                    self.download_status(False, text)
                    return
                episode = episodes[index]
                number = episode.split(':')[1]
                episode_title = f'{title} · Episode {number}'
                self.download_status(True, f'Downloading {index + 1}/{len(episodes)} · {episode_title}')

                def done(_path):
                    nonlocal saved
                    saved += 1
                    next_episode(index + 1)

                def failed(_message):
                    failures.append(number)
                    GLib.idle_add(next_episode, index + 1)

                self.download_episode(show, episode, episode_title, mode, quality, done, failed)

            next_episode(0)

        self.start_download('Preparing download · ' + title)
        engine.background(lambda: media_sources.season_episodes(show, season_id),
                          download_season, self.download_failed)


    def handle_youtube_account(self):
        result = self.result
        result(youtube_account.status())


    def handle_youtube_connect(self):
        request = self.request
        engine = self.engine
        result = self.result
        fail = self.fail
        engine.background(lambda: youtube_account.connect(str(request.get('browser', '')), media_sources.fetch_youtube_feed), result, fail)


    def handle_youtube_disconnect(self):
        result = self.result
        result(youtube_account.disconnect())


    def handle_stop(self):
        engine = self.engine
        result = self.result
        engine.stop()
        result(True)


    def handle_next_episode(self):
        engine = self.engine
        result = self.result
        engine.skip_to_next()
        result(True)


    def handle_resume(self):
        engine = self.engine
        result = self.result
        if engine.session is not None:
            engine.session.command(['set_property', 'pause', False])
        result(True)

    def handle_skip(self):
        direction = self.request.get('direction')
        if direction not in ('back', 'forward'):
            raise ValueError('Choose a skip direction.')
        self.engine.skip(10 if direction == 'forward' else -10)


    def handle_subtitle_source(self):
        request = self.request
        engine = self.engine
        result = self.result
        engine.select_subtitles(str(request.get('source', 'off')))
        result(True)


    def handle_show_captions(self):
        engine = self.engine
        result = self.result
        if engine.session is not None and engine.context and media_sources.kind_of(engine.context[0]) != 'youtube':
            engine.settings_changed()
            engine.session.show_captions()
        result(True)


    def handle_poster(self):
        request = self.request
        engine = self.engine
        result = self.result
        fail = self.fail
        url = request['url']
        def poster():
            app.CACHE.mkdir(parents=True, exist_ok=True)
            path = app.CACHE / (hashlib.sha256(url.encode()).hexdigest() + '-menu.png')
            if not path.exists():
                with Image.open(io.BytesIO(app.fetch(url))) as image:
                    image.thumbnail((480, 720))
                    image.convert('RGB').save(path, 'PNG')
            return dict(id=request['id'], image=path.as_uri())
        engine.background(poster, result, fail)


    def handle_torbox(self):
        request = self.request
        engine = self.engine
        send = self.send
        result = self.result
        fail = self.fail
        action = self.request.get("action")
        def connected(data):
            engine.resolved.clear()
            send(dict(event='torbox', data=data))
            return False
        if action == 'torbox_connect':
            engine.background(lambda: torbox_source.start_link(lambda data: GLib.idle_add(connected, data)), result, fail)
        elif action == 'torbox_check':
            engine.background(torbox_source.account, result, fail)
        elif action == 'torbox_disconnect':
            engine.resolved.clear()
            result(torbox_source.disconnect())
        else:
            key = request.pop('key', '')
            def save_connection():
                data = torbox_source.connect_key(key)
                engine.resolved.clear()
                return data
            engine.background(save_connection, result, fail)


    def handle_settings(self):
        request = self.request
        engine = self.engine
        result = self.result
        new = request.get('settings', {})
        if not isinstance(new, dict):
            raise ValueError('Settings must be an object')
        settings = engine.settings.copy()
        for key in ['auto_next', 'youtube_auto_next', 'fullscreen', 'live_subtitles', 'audio_normalization']:
            if key in new:
                settings[key] = bool(new[key])
        for key, values in [('quality', ['best', '1080p', '720p', '480p', 'worst']), ('mode', ['sub', 'dub']), ('caption_language', CAPTION_LANGUAGES), ('subtitle_font', app.SUBTITLE_FONTS)]:
            if new.get(key) in values:
                settings[key] = new[key]
        if 'volume' in new:
            settings['volume'] = max(0, min(100, int(new['volume'])))
        if 'caption_delay' in new:
            delay = float(new['caption_delay'])
            if not math.isfinite(delay):
                raise ValueError('Caption timing must be a finite number')
            settings['caption_delay'] = max(-10, min(10, round(delay, 1)))
        app.save_json(app.CONFIG, settings)
        engine.settings.update(settings)
        engine.settings_changed()
        result(engine.settings)


REQUEST_HANDLERS = {'catalogue': 'handle_catalogue', 'details': 'handle_details', 'season': 'handle_season', 'quick_play': 'handle_quick_play', 'play': 'handle_play', 'downloads': 'handle_downloads', 'trash_download': 'handle_trash_download', 'download': 'handle_download', 'download_season': 'handle_download_season', 'stop_download': 'handle_stop_download', 'youtube_account': 'handle_youtube_account', 'youtube_connect': 'handle_youtube_connect', 'youtube_disconnect': 'handle_youtube_disconnect', 'stop': 'handle_stop', 'next_episode': 'handle_next_episode', 'resume': 'handle_resume', 'skip': 'handle_skip', 'subtitle_source': 'handle_subtitle_source', 'show_captions': 'handle_show_captions', 'poster': 'handle_poster', 'torbox_connect': 'handle_torbox', 'torbox_check': 'handle_torbox', 'torbox_disconnect': 'handle_torbox', 'torbox_key': 'handle_torbox', 'settings': 'handle_settings'}


def dispatch(request, engine, send):
    handler = MenuRequest(request, engine, send)
    try:
        method = REQUEST_HANDLERS.get(request.get('action'))
        if method is None:
            raise ValueError('Unknown request')
        getattr(handler, method)()
    except Exception as error:
        handler.fail(error)
    return False
