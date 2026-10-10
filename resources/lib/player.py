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


def _chooser_family():
    """Map the direct_max_height setting to ISA's resolution families."""
    try:
        height = int(kodi.setting('direct_max_height') or 720)
    except (TypeError, ValueError):
        height = 720
    return 480 if height <= 480 else 720 if height <= 720 else 1080


def play(video_id, title='', image='', profile=None):
    # 'profile' (default/trailer/music) selects the quality/engine path in
    # engines that support it; the ResolveURL path ignores it.
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

    base = stream.split('|', 1)[0].lower()
    is_hls = ('.m3u8' in base or '/manifest/hls' in base) and _isa_enabled()
    dash = ('.mpd' in stream or 'dash' in stream) and _isa_enabled()

    log('NewPipe playing: ' + stream)
    if is_hls:
        # Pin ISA's chooser to the configured family instead of letting it
        # follow the display resolution (tulip inputstream_properties support).
        family = _chooser_family()
        directory.resolve(
            stream, meta={'title': title}, icon=image,
            dash=True, manifest_type='hls', inputstream_type='adaptive',
            mimetype='application/x-mpegURL',
            inputstream_properties={
                'inputstream.adaptive.stream_selection_type': 'fixed-res',
                'inputstream.adaptive.chooser_resolution_max': '{0}p'.format(family),
            },
        )
    else:
        directory.resolve(
            stream, meta={'title': title}, icon=image,
            dash=bool(dash), manifest_type='mpd' if dash else None
        )
