"""Cinemeta discovery with English-edition metadata checks.

Discovery uses Stremio's public addon catalogue protocol:
https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/api/requests/catalog.md
Playback uses the independent HTTPS-only adapter; metadata is not proof of playback.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from functools import lru_cache
import json
from pathlib import Path
import re
import sqlite3
import time
import threading
from datetime import datetime, timezone
from urllib.parse import quote
import unicodedata
import moviebox_source as movies

BASE = 'https://v3-cinemeta.strem.io'
PAGE_SIZE = 12
TARGET_SIZE = 12
MAX_SCAN_CHUNKS = 8
CACHE = Path.home() / '.cache/anime-streamer/discovery.sqlite3'
LOOKUPS = ThreadPoolExecutor(max_workers=4, thread_name_prefix='media-discovery')
PREFETCH = ThreadPoolExecutor(max_workers=1, thread_name_prefix='catalogue-prefetch')
PREFETCH_SLOT = threading.Lock()
GENRES = ('Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime',
          'Documentary', 'Drama', 'Family', 'Fantasy', 'History', 'Horror',
          'Mystery', 'Romance', 'Sci-Fi', 'Sport', 'Thriller', 'War', 'Western',
          'Reality-TV', 'Talk-Show', 'Game-Show')


def search_terms(query):
    mode, separator, value = query.partition(':')
    mode = mode.strip().casefold()
    if not separator or mode not in ('actor', 'genre', 'title'):
        return 'title', query.strip()
    value = value.strip()
    if not value:
        raise ValueError('Enter an actor name, genre or title after the colon.')
    if mode == 'genre':
        aliases = {'science fiction': 'Sci-Fi', 'scifi': 'Sci-Fi', 'sci fi': 'Sci-Fi'}
        value = aliases.get(value.casefold(), value)
        value = next((genre for genre in GENRES if genre.casefold() == value.casefold()), '')
        if not value:
            raise ValueError('Unknown genre. Try Comedy, Drama, Horror or Sci-Fi.')
    if mode == 'actor' and len(normalized_title(value)) < 2:
        raise ValueError('Enter at least two characters of an actor name.')
    return mode, value


@lru_cache(maxsize=1024)
def page_lock(kind, category, page, query):
    return threading.RLock()


def prefetch(kind, category, page, fetch, query=''):
    """Warm one following page, without building a queue during rapid tab changes."""
    if page > 200 or not PREFETCH_SLOT.acquire(blocking=False):
        return
    def work():
        try:
            catalogue(kind, category, page, fetch, query)
        except Exception:
            pass  # Foreground requests retain the normal retry behavior.
        finally:
            PREFETCH_SLOT.release()
    PREFETCH.submit(work)


def cached(key, ttl):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(CACHE, timeout=10)) as database:
        database.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, updated REAL, payload TEXT)')
        row = database.execute('SELECT updated, payload FROM cache WHERE key = ?', (key,)).fetchone()
    if row and time.time() - row[0] < ttl:
        return True, json.loads(row[1])
    return False, None


def remember(key, value):
    with closing(sqlite3.connect(CACHE, timeout=10)) as database:
        with database:
            database.execute('INSERT OR REPLACE INTO cache VALUES (?, ?, ?)', (key, time.time(), json.dumps(value)))


def normalized_title(title):
    title = re.sub(r'\[[^]]*\]', '', title)
    title = re.sub(r'\s+S\d+(?:-S?\d+)?$', '', title, flags=re.I)
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', title)
    title = unicodedata.normalize('NFKD', title).casefold().replace('&', 'and')
    return ''.join(character for character in title if character.isalnum())


def release_year(item):
    match = re.search(r'\d{4}', str(item.get('releaseDate') or item.get('releaseInfo') or item.get('year') or ''))
    return match[0] if match else ''


def matches(meta, item):
    if normalized_title(item.get('title', '')) != normalized_title(meta['name']):
        return False
    wanted, actual = release_year(meta), release_year(item)
    return not (wanted and actual and wanted != actual)


def lookup(kind, meta):
    import primewire_source
    key = 'match-direct-v1:' + kind + ':' + meta['id']
    hit, value = cached(key, 6 * 3600)
    if hit and (value is not None or cached(key, 15 * 60)[0]):
        return value
    card = primewire_source.lookup(kind, meta)
    if card:
        card = dict(card, id='direct:' + ('movie' if kind == 'movies' else 'series') + ':' + meta['id'])
    remember(key, card)
    return card


def _page(kind, category, page, fetch, query=""):
    mode, term = search_terms(query)
    page_key = f'page-search-v2:{kind}:{category}:{page}:{query}'
    hit, plan = cached(page_key, 3600)
    if hit:
        return plan
    previous = _page(kind, category, page - 1, fetch, query) if page > 1 else dict(cursor=0, seen=[], hasMore=True)
    if not previous['hasMore']:
        return dict(items=[], hasMore=False, cursor=previous['cursor'], seen=previous['seen'])
    media_type = 'movie' if kind == 'movies' else 'series'
    catalogue_id = 'top' if query else 'imdbRating' if category == 'featured' else 'year' if category == 'recently-updated' else 'top'
    cursor, seen = previous['cursor'], set(previous['seen'])
    items, item_ids, has_more = [], set(previous.get('matchedIds', [])), True
    for _ in range(MAX_SCAN_CHUNKS):
        parameters = ['search=' + quote(term, safe='')] if term and mode == 'title' else []
        if mode == 'genre':
            parameters.append('genre=' + quote(term, safe=''))
        elif catalogue_id == 'year':
            parameters.append('genre=' + str(datetime.now(timezone.utc).year))
        if cursor or mode == 'genre':
            parameters.append('skip=' + str(cursor))
        extra = '/' + '&'.join(parameters) if parameters else ''
        url = f'{BASE}/catalog/{media_type}/{catalogue_id}{extra}.json'
        hit, payload = cached(url, 3600)
        if not hit:
            payload = json.loads(fetch(url))
            if not isinstance(payload.get('metas'), list):
                raise RuntimeError('The discovery catalogue returned an invalid response')
            remember(url, payload)
        metas = [meta for meta in payload['metas'] if meta.get('id') and meta.get('name')]
        batch = metas if mode == 'actor' else metas[:PAGE_SIZE]
        candidates = [meta for meta in batch if meta['id'] not in seen]
        has_more = len(metas) >= PAGE_SIZE
        if not candidates:
            has_more = False
            break
        seen.update(meta['id'] for meta in candidates)
        cursor += len(batch) if mode == 'actor' else PAGE_SIZE
        if mode == 'genre':
            candidates = [meta for meta in candidates if term in (meta.get('genres') or [])]
        if mode == 'actor':
            # ponytail: catalogue cast only; a filmography provider can widen coverage later.
            actor = normalized_title(term)
            candidates = [meta for meta in candidates if any(
                actor in normalized_title(name) for name in (meta.get('cast') or []) if isinstance(name, str))]
        futures = [LOOKUPS.submit(lookup, kind, meta) for meta in candidates]
        failures = []
        for future in futures:
            try:
                card = future.result()
            except Exception as error:
                failures.append(error)
                continue
            if card and card['id'] not in item_ids:
                items.append(card)
                item_ids.add(card['id'])
        if failures:
            raise RuntimeError('Some titles could not be checked. Retry this page.') from failures[0]
        if len(items) >= TARGET_SIZE or not has_more:
            break
    plan = dict(items=items, hasMore=has_more, cursor=cursor, seen=sorted(seen), matchedIds=sorted(item_ids))
    remember(page_key, plan)
    return plan


def catalogue(kind, category, page, fetch, query=""):
    if kind not in ('movies', 'tv') or not 1 <= page <= 200:
        raise ValueError('Invalid discovery request')
    # A foreground request can reuse an in-flight prefetch instead of repeating it.
    with page_lock(kind, category, page, query):
        plan = _page(kind, category, page, fetch, query)
    return dict(items=plan['items'], hasMore=plan['hasMore'], discovery='Cinemeta')
