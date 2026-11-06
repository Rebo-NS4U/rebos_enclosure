#!/usr/bin/env python3
"""JSON-lines transport for the QuickShell menu and existing playback engine."""
import json
import re
import signal
import sys
import threading
import time
import app
import menu_requests
from menu_requests import clean as clean, parse_details as parse_details, resume_index as resume_index, card_selection as card_selection
import media_sources
import browser_bridge
import stream_relay
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
    # Prefer a named ending chapter; otherwise use the final three minutes.
    # Keep short clips from offering the next video immediately.
    start = duration - min(180, duration * .20)
    endings = []
    for chapter in chapters:
        try:
            position = float(chapter['start_time'])
            title = chapter.get('title') or (chapter.get('tags') or {}).get('title', '')
            if ending_chapter(title) and 0 <= duration - position <= min(600, duration * .25):
                endings.append(position)
        except (KeyError, TypeError, ValueError):
            continue
    return min(endings) if endings else start


def send(message):
    with OUTPUT_LOCK:
        print(json.dumps(message), flush=True)


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
        self.subtitle_choice = 'auto'
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

    def ensure_player(self, token):
        """Show the window before episode discovery or network resolution starts."""
        if token != self.play_token:
            return
        if self.session is None:
            def player_event(event):
                # A closed/replaced preparation window cannot affect a new request.
                if self.session is session:
                    return self.player_event(event, token)
                return False
            session = VlcSession(self.settings.copy(), player_event, app.STATE / 'vlc.log')
            self.session = session
            self.player = session.process
            self.stop_button.set_sensitive(True)

    def discard_preparing_player(self, token):
        if token == self.play_token and self.context is None and self.session is not None:
            session = self.session
            self.session = self.player = None
            session.close()
            self.stop_button.set_sensitive(False)

    def start_episode(self, show, episodes, index, token, automatic=False, _queue_ready=False):
        if token != self.play_token:
            return
        try:
            self.ensure_player(token)
        except OSError as error:
            self.play_status.set_text('Could not open VLC: ' + str(error))
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
                    self.discard_preparing_player(token)
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
                if automatic and not self.settings.get('youtube_auto_next' if media_sources.kind_of(show) == 'youtube' else 'auto_next', True):
                    self.next_requested = False
                    self.publish_next_episode()
                    self.play_status.set_text('Episode finished. Loading the next episode is off.')
                    return
                self.launch_player(show, episodes, index, token, links, settings, paused=automatic and media_sources.kind_of(show) != 'youtube')
        def failed(message):
            if token == self.play_token:
                self.discard_preparing_player(token)
                self.next_requested = False
                self.publish_next_episode()
                self.play_status.set_text(message)
        self.resolve((show['id'], ep, settings['mode'], settings['quality']), ready, failed)

    def launch_player(self, show, episodes, index, token, links, settings, paused=False):
        if token != self.play_token:
            return
        self.context = (show, episodes, index, token)
        self.subtitle_choice = 'auto'
        self.close_captions()
        send(dict(event='subtitle-tracks', selected='off', options=[dict(id='off', label='Off')], available=False))
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
            self.ensure_player(token)
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
        if planned is None or self.position < max(0, planned - 30):
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
        if self.session is not None:
            self.session.live_enabled = self.settings.get('live_subtitles', True)
        if self.captions is not None and self.captions.language != self.settings.get('caption_language', 'auto'):
            self.close_captions()
        if getattr(self, 'subtitle_choice', 'auto') == 'off' or (not self.settings.get('live_subtitles', True) and getattr(self, 'subtitle_choice', 'auto') != 'whisper'):
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

    def start_captions(self, force=False):
        error = getattr(self.session, 'caption_error', '')
        if not force and isinstance(error, str) and error:
            return
        if not force and getattr(self, 'subtitle_choice', 'auto') == 'off':
            return
        if not force and getattr(self, 'subtitle_choice', 'auto') != 'whisper' and isinstance(getattr(self.session, 'provided_cues', None), list) and self.session.provided_cues:
            return
        if (not force and not self.settings.get('live_subtitles', True) and getattr(self, 'subtitle_choice', 'auto') != 'whisper') or self.links is None:
            return
        if not force and getattr(self, 'subtitle_choice', 'auto') != 'whisper' and self.context and media_sources.kind_of(self.context[0]) == 'youtube':
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
                                    language=self.settings.get('caption_language', 'auto'),
                                    position=self.position, duration=self.duration)
            self.captions = service
            self.session.show_captions()
            service.update_position(self.position, self.duration)
        except Exception as error:
            if self.session is not None:
                self.session.caption_error = str(error)
            send(dict(event='captions', text='Live captions unavailable: ' + str(error)))

    def select_subtitles(self, source):
        if self.session is None or not self.file_loaded:
            raise ValueError('Start a video before choosing subtitles.')
        tracks = self.session.subtitle_tracks()
        if source not in {row['id'] for row in tracks['options']}:
            raise ValueError('This subtitle source is not available for this video.')
        self.close_captions()
        self.subtitle_choice = source
        self.session.caption_error = ''
        self.session.command(['subtitle-source', source])
        if source == 'whisper':
            self.start_captions(force=True)

    def player_event(self, event, token):
        if token != self.play_token:
            return False
        kind = event.get('event')
        if kind == 'end-file':
            send(dict(event='subtitle-tracks', selected='off', options=[dict(id='off', label='Off')], available=False))
        if kind == 'process-exited':
            self.save_progress(force=True)
            self.close_captions()
            self.file_loaded = False
            self.session = None
            send(dict(event='subtitle-tracks', selected='off', options=[dict(id='off', label='Off')], available=False))
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
            if event.get('name') == 'subtitle-tracks':
                tracks = event.get('data') or {}
                if getattr(self, 'subtitle_choice', 'auto') == 'provided' and tracks.get('selected') != 'provided':
                    self.subtitle_choice = 'auto'
                send(dict(event='subtitle-tracks', **tracks))
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
            if media_sources.kind_of(show) == 'youtube' and index + 1 < len(episodes) and self.settings.get('youtube_auto_next', True):
                self.next_requested = True
                self.start_episode(show, episodes, index + 1, token, automatic=True)
            elif index + 1 < len(episodes):
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
        send(dict(event='subtitle-tracks', selected='off', options=[dict(id='off', label='Off')], available=False))
        self.play_status.set_text('Playback stopped.')
        self.stop_button.set_sensitive(False)

    def error(self, message):
        send(dict(event='playback', text=message))
        return False


engine = None
loop = GLib.MainLoop()


def dispatch(request):
    return menu_requests.dispatch(request, engine, send)


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
    send(dict(event='ready', settings=engine.settings, filterOptions=app.filter_fields(), mediaGenres=media_sources.discovery_catalogue.GENRES, youtubeRecommendations=media_sources.YOUTUBE_RECOMMENDATIONS, youtubeAccount=media_sources.youtube_account.status()))
    threading.Thread(target=read_requests, daemon=True).start()
    try:
        loop.run()
    finally:
        engine.stop()
        app.POOL.shutdown(wait=False, cancel_futures=True)
