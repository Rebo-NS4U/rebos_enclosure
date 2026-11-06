"""Request routing for the menu's JSON-lines API, independent of playback state."""
import hashlib
import io
import math
import re
from urllib.parse import quote

import app
import youtube_account
import media_sources
import torbox_source
from PIL import Image
from gi.repository import GLib

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


def card_selection(show, history):
    entry = history.get(show['id'], {}) or history.get(show.get('historyId', ''), {})
    if media_sources.kind_of(show) == 'anime':
        data = dict(episodes=app.ani_bridge('episodes', show['id']))
    else:
        data = media_sources.details(show, app.fetch, entry.get('episode'))
    episodes = data['episodes']
    if not episodes:
        raise ValueError('No playable videos or episodes are available for this title.')
    show = dict(data.get('show') or show, episodeLabels=data.get('episodeLabels') or {})
    return show, episodes, resume_index(episodes, entry)


def dispatch(request, engine, send):
    action = request.get('action')
    request_id = request.get('request', 0)
    def result(data):
        send(dict(event=action, request=request_id, data=data, client=request.get('_client')))
    def fail(error):
        send(dict(event='error', action=action, request=request_id, text=str(error), client=request.get('_client')))
    def catalogue_ready(data):
        result(data)
        if kind in ('movies', 'tv'):
            items = data if isinstance(data, list) else data['items']
            media_sources.refresh_availability(items, lambda labels: send(dict(
                event='availability', request=request_id, data=labels, client=request.get('_client'))))
            if isinstance(data, dict) and data.get('hasMore'):
                media_sources.discovery_catalogue.prefetch(kind, category, page + 1, app.fetch, query)
    try:
        if action == 'catalogue':
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
                    result(history)
            else:
                page = max(1, int(request.get('page', 1)))
                engine.background(lambda: app.catalogue(category, query, page, filters) if kind == 'anime' else media_sources.catalogue(kind, category, query, page, app.fetch, check_availability=False), catalogue_ready, fail)
        elif action == 'details':
            show_id = request['show']['id']
            def details():
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
            engine.background(details, result, fail)
        elif action == 'season':
            show = request['show']
            if media_sources.kind_of(show) != 'tv':
                raise ValueError('Season selection requires a TV show')
            def load_season():
                season_id = str(request['seasonId'])
                data = media_sources.season_episodes(show, season_id)
                return data
            engine.background(load_season, result, fail)
        elif action == 'quick_play':
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
        elif action == 'play':
            show, episodes = request['show'], request['episodes']
            index = int(request['index'])
            if index < 0 or index >= len(episodes):
                raise ValueError('Choose an available episode')
            engine.stop()
            engine.current = None
            show, episodes, index = media_sources.youtube_queue(show, episodes, index, request.get('queue', []))
            engine.start_episode(show, episodes, index, engine.play_token)
            result(True)
        elif action == 'youtube_account':
            result(youtube_account.status())
        elif action == 'youtube_connect':
            engine.background(lambda: youtube_account.connect(str(request.get('browser', '')), media_sources.fetch_youtube_feed), result, fail)
        elif action == 'youtube_disconnect':
            result(youtube_account.disconnect())
        elif action == 'stop':
            engine.stop()
            result(True)
        elif action == 'next_episode':
            engine.skip_to_next()
            result(True)
        elif action == 'resume':
            if engine.session is not None:
                engine.session.command(['set_property', 'pause', False])
            result(True)
        elif action == 'subtitle_source':
            engine.select_subtitles(str(request.get('source', 'off')))
            result(True)
        elif action == 'show_captions':
            if engine.session is not None and engine.context and media_sources.kind_of(engine.context[0]) != 'youtube':
                engine.settings_changed()
                engine.session.show_captions()
            result(True)
        elif action == 'poster':
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
        elif action in ('torbox_connect', 'torbox_check', 'torbox_disconnect', 'torbox_key'):
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
        elif action == 'settings':
            new = request.get('settings', {})
            if not isinstance(new, dict):
                raise ValueError('Settings must be an object')
            settings = engine.settings.copy()
            for key in ['auto_next', 'youtube_auto_next', 'fullscreen', 'live_subtitles', 'audio_normalization']:
                if key in new:
                    settings[key] = bool(new[key])
            for key, values in [('quality', ['best', '1080p', '720p', '480p', 'worst']), ('mode', ['sub', 'dub']), ('caption_language', ['en', 'es', 'auto']), ('subtitle_font', app.SUBTITLE_FONTS)]:
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
        else:
            raise ValueError('Unknown request')
    except Exception as error:
        fail(error)
    return False
