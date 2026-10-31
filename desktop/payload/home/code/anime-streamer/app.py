#!/usr/bin/env python3
"""GTK anime browser using the user's installed ani-cli resolver and mpv."""
import concurrent.futures
import hashlib
import html
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import threading
import time
from urllib.parse import quote_plus, urlencode

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, GLib

ROOT = Path.home()
STATE = ROOT / '.local/state/anime-streamer'
CACHE = ROOT / '.cache/anime-streamer'
CONFIG = ROOT / '.config/anime-streamer/settings.json'
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=8)
BASE = 'https://hianime.at'
DEFAULTS = dict(auto_next=True, quality='best', mode='sub', fullscreen=False, volume=80, live_subtitles=True, caption_delay=0)


def read_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default.copy()


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2))
    temp.replace(path)


def fetch(url):
    if not url.startswith('https://'):
        raise ValueError('Only HTTPS catalogue and image URLs are supported')
    result = subprocess.run(['curl', '-fLsS', '--max-time', '25', '--max-filesize', '12000000', '-A', 'Mozilla/5.0', url], capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-300:] or 'Provider unavailable')
    return result.stdout


def parse_catalogue(page):
    shows = []
    seen = set()
    for block in re.split(r'<div class="flw-item\b', page)[1:]:
        name = re.search(r'<h3 class="film-name">\s*<a[^>]*href="[^"]*/([^"/]+)"[^>]*title="([^"]+)"', block)
        image = re.search(r'<img\s[^>]*(?:data-src|src)="([^"]+)"', block)
        description = re.search(r'<div class="description">(.*?)</div>', block, re.S)
        if name and name[1] not in seen:
            seen.add(name[1])
            shows.append(dict(id=name[1], title=html.unescape(name[2]), image=html.unescape(image[1]) if image else '', description=html.unescape(re.sub('<[^>]+>', '', description[1]).strip()) if description else ''))
    return shows


def catalogue(category, query, page, filters=None):
    filters = validate_filters(filters or {})
    if filters:
        parameters = {('genre[]' if key == 'genres' else key): value for key, value in filters.items()}
        route = '/filter?' + urlencode(dict(keyword=query, **parameters, page=page))
    else:
        route = f'/search?keyword={quote_plus(query)}&page={page}' if query else f'/{category}?page={page}'
    content = fetch(BASE + route).decode()
    if 'Just a moment' in content[:3000]:
        raise RuntimeError('The catalogue provider is blocking this request. Please try again later.')
    return parse_catalogue(content)


def filter_fields():
    return json.loads(Path(__file__).with_name('filter_options.json').read_text())['fields']


def validate_filters(filters):
    if not isinstance(filters, dict):
        raise ValueError('Invalid search filters')
    allowed = {field['key']: {option['value'] for option in field['options']} for field in filter_fields()}
    result = {}
    for key, value in filters.items():
        if key not in allowed or not isinstance(value, str) or value not in allowed[key]:
            raise ValueError('Unsupported search filter: ' + str(key))
        if value:
            result[key] = value
    if result.get('sy') and result.get('ey') and int(result['sy']) > int(result['ey']):
        raise ValueError('From year must be earlier than or equal to To year')
    return result


def ani_bridge(action, show_id, episode='', mode='sub', quality='best'):
    # Reuse upstream functions without running its interactive main program.
    source = (ROOT / '.local/bin/ani-cli').read_text()
    functions = source.split('# MAIN')[0]
    required = ('hianime_episodes()', 'hianime_m3u8()', 'select_quality()')
    if not all(item in functions for item in required):
        raise RuntimeError('ani-cli changed its resolver API; the browser bridge needs updating.')
    script = functions + '''
base_api="https://hianime.at"
episodes_api="${base_api}/api/theme/episode/list/%s"
servers_api="${base_api}/api/theme/episode/servers?episodeId=%s"
agent="Mozilla/5.0"
curl_exe=$(dep_ch_failover "curl_firefox135,curl_chrome136,curl_chrome116,curl_ff117,curl")
cipher_flag=""
episode_maps=$(hianime_episodes "$2") || exit 1
[ -n "$episode_maps" ] || { echo "No episodes available from the provider" >&2; exit 1; }
if [ "$1" = episodes ]; then
    printf '%s\\n' "$episode_maps"
else
    hianime_m3u8 "$3" "$4" || { echo "No playable source for this episode and language" >&2; exit 1; }
    select_quality "$5"
    printf '%s\\n%s\\n%s\\n%s\\n' "$video_link" "$refr" "$sub_link" "$audio_link"
fi
'''
    result = subprocess.run(['sh', '-c', script, 'anime-streamer', action, show_id, str(episode), mode, quality], capture_output=True, text=True, timeout=110)
    if result.returncode:
        message = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', result.stderr or result.stdout)
        raise RuntimeError(message.strip()[-450:] or 'The provider did not return a playable source')
    if action == 'episodes':
        return [line.split('\t', 1)[1] for line in result.stdout.splitlines() if '\t' in line]
    parts = result.stdout.splitlines()
    parts += [''] * (4 - len(parts))
    if not parts[0].startswith('https://'):
        raise RuntimeError('The provider returned an invalid stream URL')
    return parts[:4]


def completed_episode(event):
    return event.get('event') == 'end-file' and event.get('reason') == 'eof'


class Browser(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='local.rebo.AnimeStreamer')
        self.settings = DEFAULTS | read_json(CONFIG, DEFAULTS)
        self.history = read_json(STATE / 'history.json', {})
        self.generation = 0
        self.selection = 0
        self.play_token = 0
        self.player = None
        self.current = None
        self.episodes = []
        self.query = ''
        self.category = 'most-popular'
        self.page = 1
        self.loading = False
        self.has_more = True
        self.load_error = False
        self.connect('activate', self.activate)
        self.connect('shutdown', self.shutdown)

    def background(self, work, done, failed=None):
        def finished(future):
            try:
                result = future.result()
            except Exception as exc:
                GLib.idle_add(failed or self.error, str(exc))
            else:
                GLib.idle_add(done, result)
        POOL.submit(work).add_done_callback(finished)

    def error(self, message):
        self.status.set_text(message)
        self.spinner.stop()
        return False

    def activate(self, *_):
        if hasattr(self, 'window'):
            self.window.present()
            return
        self.window = Gtk.ApplicationWindow(application=self, title='Anime Streamer', default_width=1180, default_height=800)
        self.window.maximize()
        self.theme()
        header = Gtk.HeaderBar()
        header.set_title_widget(Gtk.Label(label='Anime Streamer', css_classes=['title']))
        settings = Gtk.Button(icon_name='emblem-system-symbolic', tooltip_text='Playback settings')
        settings.connect('clicked', self.show_settings)
        header.pack_end(settings)
        self.window.set_titlebar(header)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_top=18, margin_bottom=18, margin_start=24, margin_end=24)
        self.window.set_child(outer)
        intro = Gtk.Label(label='Find your next episode', xalign=0, css_classes=['hero'])
        outer.append(intro)
        toolbar = Gtk.Box(spacing=10)
        self.search = Gtk.SearchEntry(placeholder_text='Search anime…', hexpand=True)
        self.search.connect('activate', self.search_shows)
        toolbar.append(self.search)
        button = Gtk.Button(label='Search', css_classes=['suggested-action'])
        button.connect('clicked', self.search_shows)
        toolbar.append(button)
        self.categories = Gtk.DropDown.new_from_strings(['Popular', 'Recently updated', 'Top rated', 'Watch history'])
        self.categories.connect('notify::selected', self.change_category)
        toolbar.append(self.categories)
        outer.append(toolbar)
        feedback = Gtk.Box(spacing=10)
        self.spinner = Gtk.Spinner()
        feedback.append(self.spinner)
        self.status = Gtk.Label(label='Loading shows…', xalign=0, wrap=True, selectable=True, hexpand=True)
        feedback.append(self.status)
        outer.append(feedback)
        panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, wide_handle=True, vexpand=True)
        outer.append(panes)
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.connect('edge-reached', self.scroll_edge)
        scroll.get_vadjustment().connect('value-changed', self.scroll_changed)
        self.grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True, max_children_per_line=5, min_children_per_line=1, row_spacing=16, column_spacing=16, valign=Gtk.Align.START)
        scroll.set_child(self.grid)
        panes.set_start_child(scroll)
        panes.set_resize_start_child(True)
        side_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, width_request=340)
        self.side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_start=20, margin_end=8)
        side_scroll.set_child(self.side)
        panes.set_end_child(side_scroll)
        panes.set_resize_end_child(False)
        self.detail_title = Gtk.Label(label='Choose a show', xalign=0, wrap=True, css_classes=['heading'])
        self.side.append(self.detail_title)
        self.description = Gtk.Label(label='Browse the posters, then pick an episode to watch in mpv.', xalign=0, wrap=True)
        self.side.append(self.description)
        self.episode_choice = Gtk.DropDown.new_from_strings([])
        self.episode_choice.set_sensitive(False)
        self.side.append(self.episode_choice)
        self.play_button = Gtk.Button(label='Play episode', css_classes=['suggested-action'])
        self.play_button.set_sensitive(False)
        self.play_button.connect('clicked', self.play_selected)
        self.side.append(self.play_button)
        self.stop_button = Gtk.Button(label='Stop playback')
        self.stop_button.set_sensitive(False)
        self.stop_button.connect('clicked', self.stop)
        self.side.append(self.stop_button)
        self.play_status = Gtk.Label(label='Auto-next is on. Playback opens in mpv.', wrap=True, xalign=0)
        self.side.append(self.play_status)
        self.more = Gtk.Button(label='Retry loading shows', visible=False)
        self.more.connect('clicked', lambda *_: self.load(True))
        outer.append(self.more)
        self.window.present()
        self.load()

    def theme(self):
        palette = read_json(ROOT / '.cache/rebos_shell/effective-palette.json', {})
        bg = palette.get('background', '#17151e')
        surface = palette.get('surfaceContainerHigh', '#292535')
        fg = palette.get('overSurface', '#eeeaf4')
        accent = palette.get('primary', '#bda5f8')
        over = palette.get('overPrimary', '#261c3c')
        css = Gtk.CssProvider()
        css.load_from_data(f'''window {{ background: {bg}; color: {fg}; }} headerbar {{ background: {bg}; color: {fg}; }} .hero {{ font-size: 28px; font-weight: 800; }} .title, .heading {{ font-size: 18px; font-weight: 700; }} button.card {{ background: {surface}; border-radius: 16px; padding: 10px; border: 1px solid alpha({accent}, 0.15); }} button.card:hover {{ border-color: {accent}; }} button.suggested-action {{ background: {accent}; color: {over}; }} entry, dropdown {{ border-radius: 10px; }}'''.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def clear_grid(self):
        while self.grid.get_first_child():
            self.grid.remove(self.grid.get_first_child())

    def search_shows(self, *_):
        self.query = self.search.get_text().strip()
        self.load()

    def change_category(self, *_):
        self.query = ''
        self.search.set_text('')
        self.category = ['most-popular', 'recently-updated', 'top-rated', 'history'][self.categories.get_selected()]
        self.load()

    def load(self, append=False):
        if append and (self.loading or not self.has_more):
            return
        self.loading = True
        self.load_error = False
        self.generation += 1
        generation = self.generation
        if not append:
            self.page = 1
            self.has_more = True
            self.clear_grid()
            self.seen = set()
        else:
            self.page += 1
        self.more.set_sensitive(False)
        self.more.set_visible(False)
        self.spinner.start()
        self.status.set_text('Loading shows…')
        category, query, page = self.category, self.query, self.page
        def done(shows):
            if generation != self.generation:
                return
            new_shows = [show for show in shows if show['id'] not in self.seen]
            self.has_more = bool(new_shows) and (category != 'history' or bool(query))
            self.spinner.stop()
            self.status.set_text(f'{len(self.seen) + len(new_shows)} shows · Scroll down for more' if self.has_more else f'{len(self.seen) + len(new_shows)} shows · End of results')
            for show in new_shows:
                self.seen.add(show['id'])
                self.add_card(show)
            self.loading = False
        def failed(message):
            if generation == self.generation:
                self.loading = False
                self.load_error = True
                if append:
                    self.page -= 1
                self.more.set_sensitive(True)
                self.more.set_visible(True)
                self.error(message + ' · Use Search or Retry loading shows to retry.')
        self.background(lambda: list(reversed([h['show'] for h in self.history.values()])) if category == 'history' and not query else catalogue(category, query, page), done, failed)

    def scroll_edge(self, scroll, edge):
        if edge == Gtk.PositionType.BOTTOM:
            self.load_at_bottom()

    def scroll_changed(self, adjustment):
        if adjustment.get_value() > 0 and adjustment.get_upper() - adjustment.get_page_size() - adjustment.get_value() < 160:
            self.load_at_bottom()

    def load_at_bottom(self):
        if not self.loading and self.has_more and not self.load_error:
            self.load(True)

    def add_card(self, show):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, width_request=160)
        picture = Gtk.Picture(width_request=150, height_request=210, can_shrink=True)
        picture.set_content_fit(Gtk.ContentFit.COVER)
        box.append(picture)
        label = Gtk.Label(label=show['title'], wrap=True, lines=2, max_width_chars=20, height_request=44)
        label.set_ellipsize(3)
        box.append(label)
        button = Gtk.Button(child=box, css_classes=['card'], tooltip_text=show['title'])
        button.connect('clicked', lambda *_: self.select_show(show))
        self.grid.append(button)
        if show.get('image'):
            def image():
                CACHE.mkdir(parents=True, exist_ok=True)
                path = CACHE / (hashlib.sha256(show['image'].encode()).hexdigest() + '.jpg')
                if not path.exists():
                    data = fetch(show['image'])
                    path.write_bytes(data)
                return str(path)
            self.background(image, lambda path: picture.set_filename(path), lambda _: None)

    def select_show(self, show):
        self.selection += 1
        selection = self.selection
        self.current = show
        self.episodes = []
        self.detail_title.set_text(show['title'])
        self.description.set_text(show.get('description') or 'Choose an episode below.')
        self.play_button.set_sensitive(False)
        self.episode_choice.set_sensitive(False)
        self.episode_choice.set_model(Gtk.StringList.new([]))
        self.status.set_text('Loading episodes…')
        def done(episodes):
            if selection != self.selection:
                return
            self.episodes = episodes
            self.episode_choice.set_model(Gtk.StringList.new(['Episode ' + ep for ep in episodes]))
            saved = self.history.get(show['id'], {}).get('episode')
            if saved in episodes:
                position = episodes.index(saved)
                if self.history[show['id']].get('completed') and position + 1 < len(episodes):
                    position += 1
                self.episode_choice.set_selected(position)
            self.play_button.set_sensitive(bool(episodes))
            self.episode_choice.set_sensitive(bool(episodes))
            self.status.set_text(f'{len(episodes)} episodes available' if episodes else 'No episodes available for this show.')
        self.background(lambda: ani_bridge('episodes', show['id']), done, lambda e: self.error(e) if selection == self.selection else None)

    def play_selected(self, *_):
        index = self.episode_choice.get_selected()
        if self.current and index < len(self.episodes):
            self.stop()
            self.start_episode(self.current.copy(), self.episodes.copy(), index, self.play_token)

    def start_episode(self, show, episodes, index, token):
        if token != self.play_token:
            return
        ep = episodes[index]
        settings = self.settings.copy()
        self.stop_button.set_sensitive(True)
        self.play_status.set_text(f'Resolving {show["title"]} · Episode {ep}…')
        def ready(links):
            if token != self.play_token:
                return
            self.launch_player(show, episodes, index, token, links, settings)
        def failed(message):
            if token == self.play_token:
                self.stop_button.set_sensitive(False)
                self.play_status.set_text(message)
        self.background(lambda: ani_bridge('resolve', show['id'], ep, settings['mode'], settings['quality']), ready, failed)

    def launch_player(self, show, episodes, index, token, links, settings):
        video, referer, subtitles, audio = links
        ep = episodes[index]
        sockdir = tempfile.TemporaryDirectory(prefix='anime-mpv-')
        sockpath = sockdir.name + '/ipc'
        args = ['mpv', '--no-terminal', '--idle=no', '--force-window=yes', '--save-position-on-quit=yes', f'--volume={settings["volume"]}', f'--input-ipc-server={sockpath}', f'--title={show["title"]} · Episode {ep}', '--referrer=' + referer]
        if settings['fullscreen']:
            args.append('--fullscreen')
        if subtitles:
            args.append('--sub-file=' + subtitles)
        if audio:
            args.append('--audio-file=' + audio)
        args += ['--', video]
        logpath = STATE / 'mpv.log'
        STATE.mkdir(parents=True, exist_ok=True)
        try:
            with logpath.open('w') as log:
                process = subprocess.Popen(args, stdout=log, stderr=log)
        except OSError as exc:
            sockdir.cleanup()
            self.error(str(exc))
            return
        self.player = process
        self.history.pop(show['id'], None)
        self.history[show['id']] = dict(show=show, episode=ep, completed=False)
        save_json(STATE / 'history.json', self.history)
        self.play_status.set_text(f'Playing {show["title"]} · Episode {ep}')
        def monitor():
            natural_end = False
            try:
                connection = socket.socket(socket.AF_UNIX)
                for _ in range(150):
                    if process.poll() is not None:
                        break
                    try:
                        connection.connect(sockpath)
                        break
                    except OSError:
                        time.sleep(.04)
                else:
                    raise RuntimeError('Could not connect to mpv playback events')
                if process.poll() is None:
                    with connection, connection.makefile('r') as stream:
                        for line in stream:
                            try:
                                natural_end |= completed_episode(json.loads(line))
                            except ValueError:
                                pass
                else:
                    connection.close()
                process.wait()
            except (OSError, RuntimeError):
                # If IPC fails, never infer completion from process exit alone.
                process.wait()
            finally:
                sockdir.cleanup()
            GLib.idle_add(self.player_finished, show, episodes, index, token, natural_end, process.returncode)
        threading.Thread(target=monitor, daemon=True).start()

    def player_finished(self, show, episodes, index, token, natural_end, code):
        if token != self.play_token:
            return
        self.player = None
        self.stop_button.set_sensitive(False)
        if natural_end:
            self.history[show['id']]['completed'] = True
            save_json(STATE / 'history.json', self.history)
        if natural_end and self.settings['auto_next'] and index + 1 < len(episodes):
            if self.current and self.current['id'] == show['id']:
                self.episode_choice.set_selected(index + 1)
            self.start_episode(show, episodes, index + 1, token)
        else:
            self.play_status.set_text('Playback failed. See ~/.local/state/anime-streamer/mpv.log' if code else 'Show finished.' if natural_end and index + 1 == len(episodes) else 'Episode finished.' if natural_end else 'Playback stopped.')

    def stop(self, *_):
        self.play_token += 1
        if self.player and self.player.poll() is None:
            self.player.terminate()
        self.player = None
        if hasattr(self, 'stop_button'):
            self.stop_button.set_sensitive(False)
            self.play_status.set_text('Playback stopped.')

    def shutdown(self, *_):
        self.stop()
        POOL.shutdown(wait=False, cancel_futures=True)

    def show_settings(self, *_):
        window = Gtk.Window(title='Playback settings', transient_for=self.window, modal=True, default_width=440)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
        window.set_child(box)
        box.append(Gtk.Label(label='Playback settings', xalign=0, css_classes=['heading']))
        def change(key, value):
            self.settings[key] = value
            save_json(CONFIG, self.settings)
        def toggle(title, key):
            row = Gtk.Box(spacing=16)
            row.append(Gtk.Label(label=title, hexpand=True, xalign=0))
            switch = Gtk.Switch(active=self.settings[key], valign=Gtk.Align.CENTER)
            switch.connect('notify::active', lambda s, _: change(key, s.get_active()))
            row.append(switch)
            box.append(row)
        toggle('Automatically play the next episode', 'auto_next')
        toggle('Start videos fullscreen', 'fullscreen')
        for title, key, values in [('Quality', 'quality', ['best', '1080p', '720p', '480p', 'worst']), ('Audio', 'mode', ['sub', 'dub'])]:
            row = Gtk.Box(spacing=16)
            row.append(Gtk.Label(label=title, hexpand=True, xalign=0))
            dropdown = Gtk.DropDown.new_from_strings(values)
            dropdown.set_selected(values.index(self.settings[key]) if self.settings[key] in values else 0)
            dropdown.connect('notify::selected', lambda d, _, k=key, v=values: change(k, v[d.get_selected()]))
            row.append(dropdown)
            box.append(row)
        box.append(Gtk.Label(label='Starting volume', xalign=0))
        volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        volume.set_value(self.settings['volume'])
        volume.set_draw_value(True)
        volume.connect('value-changed', lambda s: change('volume', int(s.get_value())))
        box.append(volume)
        box.append(Gtk.Label(label='Settings save automatically. Quality, audio and fullscreen apply to the next video. Auto-next stops when you close mpv. Unavailable quality falls back to the best source.', wrap=True, xalign=0))
        close = Gtk.Button(label='Done', css_classes=['suggested-action'])
        close.connect('clicked', lambda *_: window.close())
        box.append(close)
        window.present()


if __name__ == '__main__':
    Browser().run()
