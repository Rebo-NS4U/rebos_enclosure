#!/usr/bin/env python3
"""JSON-lines transport for the QuickShell menu and existing playback engine."""
import json
import hashlib
import io
import math
import re
import signal
import sys
import threading
import time
from urllib.parse import quote
import app
import media_sources
import browser_bridge
import torbox_source
import stream_relay
from PIL import Image
from gi.repository import GLib
from vlc_session import VlcSession
from live_subtitles import LiveSubtitles

OUTPUT_LOCK = threading.Lock()
ENDING_CHAPTER = re.compile(r'(?:end|ending|closing)(?: credits| titles)?|credits|outro|ed(?: \d+)?')


def ending_chapter(name):
    return bool(ENDING_CHAPTER.fullmatch(re.sub(r'[^a-z0-9]+', ' ', str(name).lower()).strip()))


def next_offer_start(duration, chapters=()):
    if duration <= 0:
        return None
    start = duration - min(90, max(5, duration * .08), duration * .2)
    for chapter in chapters:
        try:
            position = float(chapter['start_time'])
            title = chapter.get('title') or (chapter.get('tags') or {}).get('title', '')
            if ending_chapter(title) and 0 <= duration - position <= min(600, duration * .25):
                start = min(start, position)
        except (KeyError, TypeError, ValueError):
            continue
    return start


def send(message):
    with OUTPUT_LOCK:
        print(json.dumps(message), flush=True)


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


class Status:
    def __init__(self, field='playback'):
        self.field = field

    def set_text(self, text):
        send(dict(event=self.field, text=text))

    def set_sensitive(self, value):
        pass

    def stop(self):
        pass


class Engine(app.Browser):
    def __init__(self):
        super().__init__()
        self.stop_button = Status()
        self.play_status = Status()
        self.status = Status()
        self.spinner = Status()
        self.session = None
        self.context = None
        self.resolved = {}
        self.resolving = {}
        self.duration = 0
        self.chapter = -1
        self.chapter_count = 0
        self.chapter_name = ''
        self.position = 0
        self.prefetch_key = None
        self.prefetch_retry_at = 0
        self.paused = False
        self.captions = None
        self.links = None
        self.file_loaded = False
        self.subtitle_sid = False
        self.subtitles_visible = True
        self.whisper_selected = False
        self.last_progress_save = 0
        self.next_requested = False
        self.next_episode_paused = False
        self.episode_ended = False
        self.last_next_offer = None

    def publish_next_episode(self):
        available = False
        label, target = 'Next episode', ''
        if self.session is not None and self.context and not self.next_requested:
            show, episodes, index, _ = self.context
            kind = media_sources.kind_of(show)
            remaining = self.duration - self.position
            # Generic chapter counts say nothing about where the story ends.
            planned = next_offer_start(self.duration, getattr(getattr(self, 'links', None), 'chapters', ()))
            near_end = planned is not None and planned <= self.position <= self.duration
            if ending_chapter(self.chapter_name) and self.chapter_count > 0 and 0 <= self.chapter < self.chapter_count:
                near_end |= self.duration > 0 and 0 <= remaining <= min(600, self.duration * .25)
            available = kind != 'movies' and self.file_loaded and self.next_episode_paused
            available |= kind != 'movies' and index + 1 < len(episodes) and (
                self.episode_ended or (self.file_loaded and near_end))
            if kind == 'youtube':
                label = 'Play video' if self.next_episode_paused else 'Next video'
            elif self.next_episode_paused:
                label = 'Start episode'
            target_index = index if self.next_episode_paused else index + 1
            if available:
                target = self.media_title(show, episodes[target_index])
        offer = dict(available=bool(available), label=label, target=target,
                     resumes=bool(available and self.next_episode_paused))
        if offer != self.last_next_offer:
            self.last_next_offer = offer
            send(dict(event='next-episode', **offer))

    def skip_to_next(self):
        self.publish_next_episode()
        if not self.last_next_offer['available']:
            return
        if self.next_episode_paused:
            self.next_episode_paused = False
            self.session.command(['set_property', 'pause', False])
        else:
            self.save_progress(force=True)
            self.next_requested = True
            show, episodes, index, token = self.context
            self.start_episode(show, episodes, index + 1, token)
        self.publish_next_episode()

    def resolve(self, key, done, failed, preload=False):
        cached = self.resolved.get(key)
        if cached and time.monotonic() - cached[0] < 300:
            done(cached[1])
            return
        if key in self.resolving:
            self.resolving[key].append((done, failed))
            return
        self.resolving[key] = [(done, failed)]
        def ready(links):
            self.resolved[key] = (time.monotonic(), links)
            for callback, _ in self.resolving.pop(key, []):
                callback(links)
        def failure(message):
            for _, callback in self.resolving.pop(key, []):
                callback(message)
        show_id, ep, mode, quality = key
        def resolve_source():
            if show_id.startswith('youtube:'):
                links = media_sources.resolve_youtube(ep, quality)
            elif show_id.startswith(('direct:', 'primewire:', 'moviebox:')):
                links = media_sources.resolve_movie(show_id, ep, quality)
            else:
                links = app.ani_bridge('resolve', show_id, ep, mode, quality)
            if preload and not getattr(links, 'is_hls', False):
                for index in (0, 3):  # Video and optional separate audio.
                    try:
                        if not links[index]:
                            continue
                        if links[index].startswith('https://'):
                            links[index] = stream_relay.register(links[index], {'Referer': links[1]} if links[1] else {})
                        stream_relay.preload(links[index])
                    except (OSError, ValueError, stream_relay.HTTPException):
                        pass  # A startup buffer is optional; verified links remain usable.
            return links
        self.background(resolve_source, ready, failure)

    def start_episode(self, show, episodes, index, token, automatic=False, _queue_ready=False):
        if token != self.play_token:
            return
        if media_sources.kind_of(show) == 'tv' and not _queue_ready:
            stop_count = getattr(self.session, 'stop_count', 0)
            def prepared(selection):
                if token != self.play_token:
                    return
                if automatic and (not self.settings['auto_next'] or getattr(self.session, 'stop_count', 0) != stop_count):
                    self.next_requested = False
                    self.publish_next_episode()
                    return
                self.start_episode(*selection, token, automatic=automatic, _queue_ready=True)
            def failed_queue(message):
                if token == self.play_token:
                    self.next_requested = False
                    self.publish_next_episode()
                    self.play_status.set_text(message)
            self.background(lambda: media_sources.playback_selection(show, episodes, index), prepared, failed_queue)
            return
        settings = self.settings.copy()
        stop_count = getattr(self.session, 'stop_count', 0)
        ep = episodes[index]
        self.play_status.set_text('Preparing ' + self.media_title(show, ep) + '…')
        def ready(links):
            if token == self.play_token:
                if automatic and getattr(self.session, 'stop_count', 0) != stop_count:
                    return
                if automatic and not self.settings['auto_next']:
                    self.next_requested = False
                    self.publish_next_episode()
                    self.play_status.set_text('Episode finished. Loading the next episode is off.')
                    return
                self.launch_player(show, episodes, index, token, links, settings, paused=automatic)
        def failed(message):
            if token == self.play_token:
                self.next_requested = False
                self.publish_next_episode()
                self.play_status.set_text(message)
        self.resolve((show['id'], ep, settings['mode'], settings['quality']), ready, failed)

    def launch_player(self, show, episodes, index, token, links, settings, paused=False):
        if token != self.play_token:
            return
        self.context = (show, episodes, index, token)
        self.close_captions()
        self.links = links
        self.file_loaded = False
        self.duration = self.position = 0
        self.chapter, self.chapter_count = -1, 0
        self.chapter_name = ''
        self.prefetch_key = None
        self.prefetch_retry_at = 0
        self.paused = paused
        self.next_episode_paused = paused
        self.next_requested = False
        self.episode_ended = False
        self.publish_next_episode()
        try:
            if self.session is None:
                self.session = VlcSession(settings, lambda event: self.player_event(event, token), app.STATE / 'vlc.log')
                self.player = self.session.process
            self.session.load(links, self.media_title(show, episodes[index]), paused=paused, whisper_only=media_sources.kind_of(show) != 'youtube')
            self.stop_button.set_sensitive(True)
        except OSError as error:
            self.error(str(error))

    @staticmethod
    def media_title(show, episode):
        kind = media_sources.kind_of(show)
        if kind == 'movies':
            return show['title']
        label = show.get('episodeLabels', {}).get(episode, episode if kind == 'youtube' else 'Episode ' + episode)
        return show['title'] if label == show['title'] else show['title'] + ' · ' + label

    def save_progress(self, force=False):
        if not self.context or not self.file_loaded:
            return
        show, episodes, index, _ = self.context
        entry = self.history.get(show['id'])
        if not entry or entry.get('episode') != episodes[index]:
            return
        entry.update(position=round(self.position, 1), duration=round(self.duration, 1))
        if force or time.monotonic() - self.last_progress_save > 15:
            app.save_json(app.STATE / 'history.json', self.history)
            self.last_progress_save = time.monotonic()

    def prefetch_next(self):
        if not self.context or not self.file_loaded or self.paused or self.next_episode_paused or self.next_requested:
            return
        show, episodes, index, token = self.context
        if media_sources.kind_of(show) == 'movies' or token != self.play_token or index + 1 >= len(episodes):
            return
        planned = next_offer_start(self.duration, getattr(self.links, 'chapters', ()))
        # Resolve and validate ahead of the offer, without switching players.
        if planned is None or self.position < max(0, planned - min(120, self.duration * .1)):
            return
        key = (show['id'], episodes[index + 1], self.settings['mode'], self.settings['quality'])
        now = time.monotonic()
        cached = self.resolved.get(key)
        if (cached and now - cached[0] < 300) or key in self.resolving:
            return
        if key == self.prefetch_key and now < self.prefetch_retry_at:
            return
        self.prefetch_key = key
        self.prefetch_retry_at = now + 30
        self.resolve(key, lambda _: None, lambda _: None, preload=True)

    def settings_changed(self):
        if self.captions is not None and self.captions.language != self.settings.get('caption_language', 'auto'):
            self.close_captions()
        if not self.settings.get('live_subtitles', True):
            if self.captions is not None:
                self.close_captions()
        elif self.captions is None and self.file_loaded and self.session is not None:
            self.start_captions()
        if self.captions is not None:
            self.captions.set_delay(self.settings.get('caption_delay', 0))
        self.prefetch_next()

    def close_captions(self):
        if self.captions is not None:
            self.captions.close()
            self.captions = None
            if self.session is not None:
                self.session.clear_captions()
        send(dict(event='captions', text=''))
        self.whisper_selected = False
        send(dict(event='subtitle-state', off=True, whisper=False))

    def start_captions(self):
        if not self.settings.get('live_subtitles', True) or self.links is None:
            return
        if self.context and media_sources.kind_of(self.context[0]) == 'youtube':
            return  # YouTube supplies its own native/automatic caption track.
        try:
            def ready(path):
                if self.captions is service and self.session is not None:
                    self.session.update_captions(path)
            def status(text):
                if self.captions is service:
                    send(dict(event='captions', text=text))
            service = LiveSubtitles(self.links, app.CACHE, ready, status,
                                    delay=self.settings.get('caption_delay', 0),
                                    language=self.settings.get('caption_language', 'auto'))
            self.captions = service
            self.session.show_captions()
            service.update_position(self.position, self.duration)
        except Exception as error:
            send(dict(event='captions', text='Live captions unavailable: ' + str(error)))

    def player_event(self, event, token):
        if token != self.play_token:
            return False
        kind = event.get('event')
        if kind == 'process-exited':
            self.save_progress(force=True)
            self.close_captions()
            self.file_loaded = False
            self.session = None
            self.player = None
            self.context = None
            self.play_token += 1
            failed = event.get('error') or event.get('code', 0) != 0
            self.play_status.set_text('Player closed unexpectedly. Try playing again.' if failed else 'Playback stopped.')
            self.next_episode_paused = self.episode_ended = self.next_requested = False
            self.publish_next_episode()
            send(dict(event='paused', value=False))
            self.stop_button.set_sensitive(False)
            return False
        if not self.context:
            return False
        show, episodes, index, _ = self.context
        if kind == 'file-loaded':
            self.file_loaded = True
            previous = self.history.pop(show['id'], {}) or self.history.get(show.get('historyId', ''), {})
            resume = previous.get('position', 0) if previous.get('episode') == episodes[index] and not previous.get('completed') else 0
            if previous.get('duration', 0) > 0 and previous['duration'] - resume <= 15:
                resume = 0
            self.history[show['id']] = dict(show=show, episode=episodes[index], completed=False, position=resume, duration=0)
            if resume > 1 and not self.paused:
                self.session.command(['seek', resume, 'absolute+exact'])
            app.save_json(app.STATE / 'history.json', self.history)
            self.play_status.set_text(('Paused' if self.paused else 'Playing') + ' · ' + self.media_title(show, episodes[index]))
            send(dict(event='paused', value=self.paused))
            send(dict(event='episode', show=show['id'], index=index, episode=episodes[index]))
            self.start_captions()
        elif kind == 'property-change':
            if event.get('name') == 'sid':
                self.subtitle_sid = event.get('data')
            elif event.get('name') == 'sub-visibility':
                self.subtitles_visible = bool(event.get('data'))
            elif event.get('name') == 'whisper-captions':
                self.whisper_selected = bool(event.get('data'))
            if event.get('name') in ['sid', 'sub-visibility', 'whisper-captions']:
                send(dict(event='subtitle-state', off=not self.subtitles_visible or self.subtitle_sid in (False, None, 'no'), whisper=self.whisper_selected and self.subtitles_visible))
            if event.get('name') == 'pause':
                self.paused = bool(event.get('data'))
                if not self.paused:
                    self.next_episode_paused = False
                send(dict(event='paused', value=self.paused))
                if self.history.get(show['id'], {}).get('episode') == episodes[index]:
                    self.play_status.set_text(('Paused' if self.paused else 'Playing') + ' · ' + self.media_title(show, episodes[index]))
            if event.get('name') == 'duration':
                self.duration = event.get('data') or 0
            elif event.get('name') == 'chapter-info':
                info = event.get('data') or {}
                self.chapter = info.get('index', -1)
                self.chapter_count = info.get('count', 0)
                self.chapter_name = info.get('name') or ''
            elif event.get('name') == 'time-pos':
                self.position = event.get('data') or 0
            self.save_progress(force=event.get('name') == 'pause')
            self.settings_changed()
            if self.captions is not None:
                self.captions.update_position(self.position, self.duration)
        elif app.completed_episode(event):
            if self.episode_ended or self.next_requested:
                return False
            self.episode_ended = True
            self.file_loaded = False
            self.close_captions()
            if show['id'] in self.history:
                self.history[show['id']]['completed'] = True
                self.history[show['id']]['position'] = 0
                app.save_json(app.STATE / 'history.json', self.history)
            if index + 1 < len(episodes):
                # Keep the player surface alive and wait for the on-screen next card.
                self.next_episode_paused = False
                self.play_status.set_text('Episode finished. Choose the next episode to continue.')
            else:
                self.play_status.set_text('Playback finished.')
        elif kind == 'end-file' and event.get('reason') == 'stop':
            self.save_progress(force=True)
            self.file_loaded = False
            self.close_captions()
            self.next_requested = self.next_episode_paused = self.episode_ended = False
            self.play_status.set_text('Playback stopped.')
        elif kind == 'end-file' and event.get('reason') == 'error':
            self.file_loaded = False
            self.next_requested = self.next_episode_paused = self.episode_ended = False
            self.close_captions()
            self.play_status.set_text('Playback failed. Loading the next episode stopped. See ~/.local/state/anime-streamer/vlc.log')
        elif kind in ('command-error', 'connection-error'):
            self.play_status.set_text('Player error: ' + event.get('error', 'Unknown error'))
        self.publish_next_episode()
        return False

    def stop(self, *_):
        browser_bridge.cancel()
        self.save_progress(force=True)
        self.play_token += 1
        self.close_captions()
        self.file_loaded = False
        if self.session is not None:
            self.session.close()
        self.session = None
        self.player = None
        self.context = None
        self.paused = False
        self.next_requested = self.next_episode_paused = self.episode_ended = False
        self.publish_next_episode()
        send(dict(event='paused', value=False))
        self.play_status.set_text('Playback stopped.')
        self.stop_button.set_sensitive(False)

    def error(self, message):
        send(dict(event='playback', text=message))
        return False


engine = None
loop = GLib.MainLoop()


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


def dispatch(request):
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
            engine.play_status.set_text('Preparing ' + show['title'] + '…')
            def start(selection):
                if token == engine.play_token:
                    selected, episodes, index = selection
                    engine.current = None
                    engine.start_episode(selected, episodes, index, token)
                    result(True)
            def failed(error):
                if token == engine.play_token:
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
            engine.start_episode(show, episodes, index, engine.play_token)
            result(True)
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
            for key in ['auto_next', 'fullscreen', 'live_subtitles', 'audio_normalization']:
                if key in new:
                    engine.settings[key] = bool(new[key])
            for key, values in [('quality', ['best', '1080p', '720p', '480p', 'worst']), ('mode', ['sub', 'dub']), ('caption_language', ['en', 'es', 'auto'])]:
                if new.get(key) in values:
                    engine.settings[key] = new[key]
            if 'volume' in new:
                engine.settings['volume'] = max(0, min(100, int(new['volume'])))
            if 'caption_delay' in new:
                delay = float(new['caption_delay'])
                if not math.isfinite(delay):
                    raise ValueError('Caption timing must be a finite number')
                engine.settings['caption_delay'] = max(-10, min(10, round(delay, 1)))
            app.save_json(app.CONFIG, engine.settings)
            engine.settings_changed()
            result(engine.settings)
        else:
            raise ValueError('Unknown request')
    except Exception as error:
        fail(error)
    return False


def read_requests():
    for line in sys.stdin:
        try:
            request = json.loads(line)
            GLib.idle_add(dispatch, request)
        except ValueError:
            send(dict(event='error', text='Invalid request'))
    GLib.idle_add(loop.quit)


if __name__ == '__main__':
    engine = Engine()
    signal.signal(signal.SIGTERM, lambda *_: loop.quit())
    send(dict(event='ready', settings=engine.settings, filterOptions=app.filter_fields(), mediaGenres=media_sources.discovery_catalogue.GENRES, youtubeRecommendations=media_sources.YOUTUBE_RECOMMENDATIONS))
    threading.Thread(target=read_requests, daemon=True).start()
    try:
        loop.run()
    finally:
        engine.stop()
        app.POOL.shutdown(wait=False, cancel_futures=True)
