# -*- coding: utf-8 -*-

# NewPipe Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

# All routes registered on urldispatcher; main.py only dispatches.
# Cached scrapetube listings (yt.py) keep page loads fast and anonymous.
#
# Tulip contract notes (source of the kodi.log crash):
# - directory.builder: 'title' MUST be str (int ids crash setTitle);
#   resolved here via _text() before building.
# - 'query' MUST be str; dict queries are only valid inside 'cm' entries.
from urllib.parse import urlparse, parse_qsl, parse_qs

from scrapetube import get_search
from tulip import directory, kodi
from tulip.log import log
from urldispatcher import urldispatcher

from . import player as playback
from . import storage
from . import yt


def _text(value, fallback=''):
    """Resolve int string ids via i18n; pass through real titles."""
    if isinstance(value, int):
        try:
            return kodi.i18n(value)
        except Exception:
            return fallback
    return value or fallback


def _item(entry):
    entry = dict(entry)
    if 'title' in entry:
        entry['title'] = _text(entry['title'], 'Unknown')
    if isinstance(entry.get('cm'), list):
        fixed = []
        for cm in entry['cm']:
            cm = dict(cm)
            cm['title'] = _text(cm.get('title'), '')
            fixed.append(cm)
        entry['cm'] = fixed
    if 'query' in entry and not isinstance(entry['query'], str):
        entry.pop('query')
    return entry


def _build(items, **kwargs):
    directory.builder([_item(i) for i in items], **kwargs)


def _setting(key, default=''):
    try:
        value = kodi.setting(key)
        return value if value not in (None, '') else default
    except Exception:
        return default


def _limit(default_key='results_per_page', fallback=25):
    try:
        return max(1, int(_setting(default_key, fallback)))
    except (TypeError, ValueError):
        return fallback


def _icon(name):
    try:
        return kodi.addonmedia(name + '.png')
    except Exception:
        return ''


def _video_id(url):
    if not url:
        return ''
    if url.startswith('http'):
        query = parse_qs(urlparse(url).query)
        if 'v' in query:
            return query['v'][0]
        tail = url.rstrip('/').rsplit('/', 1)[-1]
        return tail[:11] if len(tail) >= 11 else tail
    return url


def _channel_cm(channel_url, channel_title=''):
    if not channel_url:
        return []
    return [{
        'title': 30026,
        'query': {'action': 'channel', 'url': channel_url, 'title': channel_title or ''},
    }]


def _video_item(item, channel_url='', channel_title=''):
    video_id = _video_id(item.get('url', ''))
    title = item.get('title') or 'Unknown title'
    if item.get('is_live'):
        title = '[LIVE] ' + title
    cm = _channel_cm(channel_url, channel_title)
    # Every video also offers subscribe/unsubscribe for its channel.
    if channel_url:
        known = any(s.get('url') == channel_url for s in storage.get_subscriptions())
        cm.append({
            'title': 30015 if known else 30013,
            'query': {'action': 'unsubscribe' if known else 'subscribe',
                      'url': channel_url, 'title': channel_title or ''},
        })
    return {
        'title': title,
        'action': 'play',
        'url': video_id,
        'image': item.get('image', ''),
        'duration': item.get('duration') or 0,
        'isFolder': 'False',
        'isPlayable': 'True',
        'cm': cm,
    }


def _channel_thumb(item):
    try:
        thumbs = item.get('thumbnail', {}).get('thumbnails') or []
        return thumbs[-1].get('url', '') if thumbs else ''
    except (AttributeError, IndexError):
        return ''


def _channel_title(item):
    title = item.get('title', '')
    if isinstance(title, dict):
        return title.get('simpleText') or ''
    return title if isinstance(title, str) else ''


def _channel_id(item):
    return item.get('channelId') or item.get('browseId') or ''


TRENDING_CATEGORIES = ['Music', 'Gaming', 'News', 'Movies', 'Live']
LIVE_CATEGORIES = ['News', 'Music', 'Gaming', 'Sports', 'Podcasts']


@urldispatcher.register('root')
def root():
    _build([
        {'title': 30001, 'action': 'search', 'icon': _icon('search'), 'image': _icon('search'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30025, 'action': 'trending', 'icon': _icon('trending'), 'image': _icon('trending'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30018, 'action': 'live', 'icon': _icon('live'), 'image': _icon('live'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30002, 'action': 'subscriptions', 'icon': _icon('subscriptions'),
         'image': _icon('subscriptions'), 'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30027, 'action': 'bookmarks', 'icon': _icon('bookmarks'), 'image': _icon('bookmarks'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30003, 'action': 'feed', 'icon': _icon('feed'), 'image': _icon('feed'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30004, 'action': 'history', 'icon': _icon('history'), 'image': _icon('history'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30005, 'action': 'open_settings', 'icon': _icon('settings'), 'image': _icon('settings'),
         'isFolder': 'False', 'isPlayable': 'False'},
    ])


@urldispatcher.register('open_settings')
def open_settings():
    kodi.openSettings()


@urldispatcher.register('search', kwargs=['query'])
def search(query=None):
    if not query:
        history = [{
            'title': 30006, 'action': 'search_input', 'icon': _icon('search'), 'image': _icon('search'),
            'isFolder': 'True', 'isPlayable': 'False',
        }]
        history += [
            {'title': q, 'action': 'search_results', 'url': q, 'isFolder': 'True', 'isPlayable': 'False',
             'cm': [{'title': 30008, 'query': {'action': 'forget_search', 'url': q}}]}
            for q in storage.get_searches()
        ]
        _build(history)
        return
    search_results(query)


@urldispatcher.register('search_input')
def search_input():
    query = kodi.dialog.input(heading=kodi.i18n(30001))
    if query:
        storage.add_search(query)
        search_results(query)
    else:
        kodi.close_all()


@urldispatcher.register('clear_searches')
def clear_searches():
    storage.clear_searches()
    kodi.refresh()


@urldispatcher.register('clear_cache')
def clear_cache():
    from .constants import reset_cache
    ok = bool(reset_cache())
    kodi.infoDialog(kodi.i18n(30032 if ok else 30033))
    kodi.refresh()


@urldispatcher.register('trending')
def trending():
    choice = kodi.selectDialog(TRENDING_CATEGORIES, heading=kodi.i18n(30025))
    if choice < 0:
        kodi.close_all()
        return
    query = TRENDING_CATEGORIES[choice]
    _build(
        [_video_item(i, curl, ctitle) for i, curl, ctitle in yt.trending_videos(query, limit=_limit())],
        content='videos'
    )


@urldispatcher.register('live')
def live():
    choice = kodi.selectDialog(LIVE_CATEGORIES, heading=kodi.i18n(30018))
    if choice < 0:
        kodi.close_all()
        return
    query = LIVE_CATEGORIES[choice]
    enriched = [(i, curl, ctitle) for i, curl, ctitle in yt.live_videos(query, limit=_limit())
                if i.get('is_live')]
    if not enriched:
        enriched = [(i, curl, ctitle) for i, curl, ctitle in yt.live_videos(query + ' live', limit=_limit())]
    _build([_video_item(i, curl, ctitle) for i, curl, ctitle in enriched], content='videos')


@urldispatcher.register('forget_search', kwargs=['url'])
def forget_search(url):
    storage.remove_search(url)
    kodi.refresh()


@urldispatcher.register('search_results', kwargs=['url'])
def search_results(url):
    kinds = [kodi.i18n(30010), kodi.i18n(30011), kodi.i18n(30012)]
    choice = kodi.selectDialog(kinds, heading=kodi.i18n(30001))
    if choice < 0:
        kodi.close_all()
        return
    storage.add_search(url)
    limit = _limit()
    if choice == 1:
        _list_channels(url, limit)
    elif choice == 2:
        _list_playlist_results(url, limit)
    else:
        _build(
            [_video_item(i, curl, ctitle) for i, curl, ctitle in yt.search_videos(url, limit=limit)],
            content='videos'
        )


def _list_videos(items, channel_url='', channel_title=''):
    _build([_video_item(i, channel_url, channel_title) for i in items], content='videos')


def _list_channels(query, limit):
    items = []
    try:
        for raw in get_search(query, limit=limit, sleep=0, results_type='channel'):
            cid = _channel_id(raw)
            if not cid:
                continue
            url = 'https://www.youtube.com/channel/' + cid
            title = _channel_title(raw) or cid
            items.append({
                'title': title, 'action': 'channel', 'url': url, 'image': _channel_thumb(raw),
                'isFolder': 'True', 'isPlayable': 'False',
                'cm': [
                    {'title': 30013, 'query': {'action': 'subscribe', 'url': url, 'title': title}},
                ],
            })
    except Exception as e:
        log('NewPipe channel search failed: {0}'.format(e))
    _build(items, content='videos')


def _playlist_item(item):
    title = item.get('title') or 'Untitled playlist'
    url = item.get('url', '')
    marked = any(m.get('url') == url for m in storage.get_bookmarks())
    return {
        'title': title, 'action': 'playlist', 'url': url, 'image': item.get('image', ''),
        'isFolder': 'True', 'isPlayable': 'False',
        'cm': [{
            'title': 30029 if marked else 30028,
            'query': {'action': 'unbookmark' if marked else 'bookmark',
                      'url': url, 'title': title, 'image': item.get('image', '')},
        }],
    }


def _list_playlist_results(query, limit):
    from scrapetube.wrapper import list_search as wrapper_search
    _build(
        [_playlist_item(p) for p in wrapper_search(query, limit=limit, sleep=0, results_type='playlist') or []],
        content='videos'
    )


@urldispatcher.register('channel', kwargs=['url', 'title'])
def channel(url, title=''):
    subs = storage.get_subscriptions()
    known = next((s for s in subs if s.get('url') == url), None)
    name = title or (known.get('title') if known else '') or url
    toggle = {'title': 30015, 'query': {'action': 'unsubscribe', 'url': url}} if known else \
        {'title': 30013, 'query': {'action': 'subscribe', 'url': url, 'title': name}}
    _build([
        {'title': 30016, 'action': 'channel_videos', 'url': url, 'tab': 'videos',
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30017, 'action': 'channel_videos', 'url': url, 'tab': 'shorts',
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30018, 'action': 'channel_videos', 'url': url, 'tab': 'streams',
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 30012, 'action': 'channel_playlists', 'url': url, 'isFolder': 'True', 'isPlayable': 'False'},
        dict(toggle, action='unsubscribe' if known else 'subscribe', isFolder='False', isPlayable='False'),
    ])


@urldispatcher.register('channel_videos', kwargs=['url', 'tab'])
def channel_videos(url, tab='videos', query=None):
    # 'query' kept for links built before the tab rename.
    tab = query or tab or 'videos'
    subs = storage.get_subscriptions()
    known = next((s for s in subs if s.get('url') == url), None)
    _list_videos(yt.channel_videos(url, tab=tab, limit=_limit()),
                 channel_url=url, channel_title=known.get('title') if known else '')


@urldispatcher.register('channel_playlists', kwargs=['url'])
def channel_playlists(url):
    _build([_playlist_item(p) for p in yt.channel_playlists(url)], content='videos')


@urldispatcher.register('playlist', kwargs=['url'])
def playlist(url):
    _list_videos(yt.playlist_videos(url))


@urldispatcher.register('subscribe', kwargs=['url', 'title'])
def subscribe(url, title=''):
    storage.subscribe(title or url, url)
    kodi.infoDialog(kodi.i18n(30014))
    kodi.refresh()


@urldispatcher.register('unsubscribe', kwargs=['url'])
def unsubscribe(url):
    storage.unsubscribe(url)
    kodi.refresh()


@urldispatcher.register('bookmark', kwargs=['url', 'title', 'image'])
def bookmark(url, title='', image=''):
    storage.bookmark(title or url, url, image)
    kodi.infoDialog(kodi.i18n(30030))
    kodi.refresh()


@urldispatcher.register('unbookmark', kwargs=['url'])
def unbookmark(url):
    storage.unbookmark(url)
    kodi.refresh()


@urldispatcher.register('bookmarks')
def bookmarks():
    _build([_playlist_item(m) for m in storage.get_bookmarks()], content='videos')


@urldispatcher.register('subscriptions')
def subscriptions():
    subs = storage.get_subscriptions()
    _build([
        {'title': s.get('title') or s.get('url'), 'action': 'channel', 'url': s.get('url'),
         'isFolder': 'True', 'isPlayable': 'False',
         'cm': [{'title': 30015, 'query': {'action': 'unsubscribe', 'url': s.get('url')}}]}
        for s in subs
    ], content='videos')


@urldispatcher.register('feed')
def feed():
    per_channel = _limit(default_key='feed_per_channel', fallback=5)
    items = []
    for sub in storage.get_subscriptions():
        try:
            for video in yt.channel_videos(sub.get('url'), limit=per_channel)[:per_channel]:
                title = video.get('title') or 'Unknown title'
                entry = _video_item(video, sub.get('url'), sub.get('title') or '')
                entry['title'] = '{0} - {1}'.format(sub.get('title') or '', title)
                items.append(entry)
        except Exception as e:
            log('NewPipe feed error for {0}: {1}'.format(sub.get('url'), e))
    _build(items, content='videos')


@urldispatcher.register('history')
def history():
    entries = storage.get_history()
    items = [
        {'title': h.get('title') or h.get('video_id'), 'action': 'play', 'url': h.get('video_id'),
         'image': h.get('image', ''), 'isFolder': 'False', 'isPlayable': 'True'}
        for h in entries
    ]
    if entries:
        items.append({'title': 30007, 'action': 'clear_history', 'isFolder': 'False', 'isPlayable': 'False'})
    _build(items, content='videos')


@urldispatcher.register('clear_history')
def clear_history():
    storage.clear_history()
    kodi.refresh()


@urldispatcher.register('play', kwargs=['url', 'title', 'image'])
def play(url, title='', image=''):
    video_id = _video_id(url)
    storage.add_history({'video_id': video_id, 'title': title or video_id, 'image': image or ''})
    playback.play(video_id, title=title, image=image)
