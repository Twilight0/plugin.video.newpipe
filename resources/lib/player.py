# -*- coding: utf-8 -*-

# NewPipe Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

# Playback resolution is delegated to ResolveURL (YouTubeGR resolver from
# PluginsGR): watch URLs in, playable localhost DASH proxy URLs out.
import inspect
from urllib.parse import parse_qsl, urlencode

from resolveurl import add_plugin_dirs
from resolveurl.hmf import HostedMediaFile
from tulip import directory, kodi
from tulip.log import log

from .constants import PLUGINS_PATH, YT_WATCH


def _audio_stream(resolver, url):
    spec = inspect.getfullargspec(resolver.get_media_url)
    if 'audio_only' not in (spec.args or []) + (spec.kwonlyargs or []):
        return None
    host, media_id = resolver.get_host_and_id(url)
    res = resolver.get_media_url(host, media_id, audio_only=True)
    if isinstance(res, (tuple, list)):
        res = res[0]
    return res


def resolve(video_id, audio_only=False):
    url = video_id if (video_id or '').startswith('http') else YT_WATCH + video_id
    add_plugin_dirs(kodi.transPath(PLUGINS_PATH))
    hmf = HostedMediaFile(url)
    if not hmf.valid_url():
        return None
    if audio_only:
        try:
            for resolver in hmf.get_resolvers(validated=True):
                stream = _audio_stream(resolver, url)
                if stream:
                    return stream
        except Exception as e:
            log('NewPipe audio-only resolve failed: {0}'.format(e))
    try:
        return hmf.resolve() or None
    except Exception as e:
        log('NewPipe resolve failed: {0}'.format(e))
        return None


def _isa_enabled():
    try:
        return kodi.addon_details('inputstream.adaptive').get('enabled')
    except Exception:
        return False


def play(video_id, title='', image=''):
    audio_only = kodi.setting('audio_only') == 'true'
    stream = resolve(video_id, audio_only=audio_only)

    if not stream:
        kodi.infoDialog('No playable stream found')
        from tulip.init import syshandle
        kodi.resolve(syshandle, False, kodi.item())
        return

    if '|' in stream:
        stream, _, headers = stream.rpartition('|')
        stream = '|'.join([stream, urlencode(dict(parse_qsl(headers)))])

    dash = ('.mpd' in stream or 'dash' in stream) and _isa_enabled()

    log('NewPipe playing: ' + stream)
    directory.resolve(
        stream, meta={'title': title}, icon=image,
        dash=bool(dash), manifest_type='mpd' if dash else None
    )
