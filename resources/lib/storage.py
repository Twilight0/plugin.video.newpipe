# -*- coding: utf-8 -*-

# NewPipe Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

# Privacy-first local storage: subscriptions, watch history and search
# history live in plain JSON files inside the addon profile. Nothing is
# uploaded anywhere; deleting the files (or uninstalling) wipes everything.
import json
import os
import time

from tulip.kodi import dataPath

PROFILE = os.environ.get('NEWPIPE_PROFILE') or dataPath

_SUBS = 'subscriptions.json'
_HISTORY = 'watch_history.json'
_SEARCHES = 'search_history.json'

_SUBS_CAP = 500
_HISTORY_CAP = 100
_SEARCHES_CAP = 25


def _path(name):
    return os.path.join(PROFILE, name)


def _load(name, default):
    try:
        with open(_path(name), encoding='utf-8') as f:
            payload = json.load(f)
        return payload if isinstance(payload, list) else default
    except (OSError, ValueError):
        return default


def _save(name, payload):
    os.makedirs(PROFILE, exist_ok=True)
    with open(_path(name), 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)


def get_subscriptions():
    return _load(_SUBS, [])


def subscribe(title, url):
    subs = [s for s in get_subscriptions() if s.get('url') != url]
    subs.append({'title': title, 'url': url, 'added': int(time.time())})
    _save(_SUBS, subs[:_SUBS_CAP])


def unsubscribe(url):
    _save(_SUBS, [s for s in get_subscriptions() if s.get('url') != url])


_BOOKMARKS = 'bookmarks.json'
_BOOKMARKS_CAP = 200


def get_bookmarks():
    return _load(_BOOKMARKS, [])


def bookmark(title, url, image=''):
    marks = [m for m in get_bookmarks() if m.get('url') != url]
    marks.append({'title': title, 'url': url, 'image': image or '', 'added': int(time.time())})
    _save(_BOOKMARKS, marks[:_BOOKMARKS_CAP])


def unbookmark(url):
    _save(_BOOKMARKS, [m for m in get_bookmarks() if m.get('url') != url])


def get_history():
    return _load(_HISTORY, [])


def add_history(entry):
    history = [h for h in get_history() if h.get('video_id') != entry.get('video_id')]
    entry['watched'] = int(time.time())
    history.insert(0, entry)
    _save(_HISTORY, history[:_HISTORY_CAP])


def clear_history():
    _save(_HISTORY, [])


def get_searches():
    return _load(_SEARCHES, [])


def add_search(query):
    query = (query or '').strip()
    if not query:
        return
    searches = [q for q in get_searches() if q != query]
    searches.insert(0, query)
    _save(_SEARCHES, searches[:_SEARCHES_CAP])


def remove_search(query):
    _save(_SEARCHES, [q for q in get_searches() if q != query])


def clear_searches():
    _save(_SEARCHES, [])
