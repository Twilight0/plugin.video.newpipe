# -*- coding: utf-8 -*-

# NewPipe Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

# All YouTube browsing goes through scrapetube (page scraping, no API key,
# no account). Results are cached with unicache; durations are in minutes.
from scrapetube.wrapper import list_search, list_channel_videos, list_playlist_videos, list_playlists
from scrapetube.scrapetube import get_search, search_dict, _safe_get

from .constants import cache_function, cache_duration


@cache_function(cache_duration(15))
def search(query, limit=25, sort='relevance'):
    return list_search(query, limit=limit, sleep=0, sort_by=sort)


def _channel_url(raw):
    """First channel browseEndpoint in a raw search item -> /channel/ URL."""
    for endpoint in search_dict(raw, 'browseEndpoint'):
        browse_id = (endpoint or {}).get('browseId', '')
        if browse_id.startswith('UC'):
            return 'https://www.youtube.com/channel/' + browse_id
    return ''


def _channel_name(raw, url):
    owner = raw.get('ownerText') or raw.get('shortBylineText') or raw.get('longBylineText') or {}
    name = owner.get('simpleText') or _safe_get(owner, 'runs', 0, 'text', default='')
    if name:
        return name
    for endpoint in search_dict(raw, 'browseEndpoint'):
        base = (endpoint or {}).get('canonicalBaseUrl', '')
        if base.startswith('/@'):
            return base[2:]
    return url


def _enriched(query, limit, sort):
    # Raw items keep browseEndpoint channel urls; wrapper dicts keep the
    # Kodi-friendly title/url/image/duration shape. Zipped by videoId.
    wrapped = {item.get('url', '')[-11:]: item for item in search(query, limit=limit, sort=sort)}
    enriched = []
    for raw in get_search(query, limit=limit, sleep=0, sort_by=sort):
        video_id = raw.get('videoId', '')
        item = wrapped.get(video_id)
        if not item:
            continue
        url = _channel_url(raw)
        enriched.append((item, url, _channel_name(raw, url)))
    return enriched


@cache_function(cache_duration(15))
def search_videos(query, limit=25, sort='relevance'):
    return _enriched(query, limit, sort)


@cache_function(cache_duration(15))
def trending_videos(query, limit=25):
    # No combined trending page exists anymore (FEtrending is dead server-side);
    # per-category view-count-sorted search is the closest anonymous equivalent.
    return _enriched(query, limit, 'view_count')


@cache_function(cache_duration(10))
def live_videos(query, limit=25):
    return _enriched(query, limit, 'relevance')


@cache_function(cache_duration(30))
def channel_videos(url, tab='videos', limit=25):
    return list_channel_videos(channel_url=url, limit=limit, sleep=0, content_type=tab)


@cache_function(cache_duration(60))
def channel_playlists(url):
    return list_playlists(url.rstrip('/') + '/playlists')


@cache_function(cache_duration(30))
def playlist_videos(playlist_id, limit=50):
    return list_playlist_videos(playlist_id, sleep=0)
