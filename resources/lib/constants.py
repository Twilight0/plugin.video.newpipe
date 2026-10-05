# -*- coding: utf-8 -*-

# NewPipe Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

from tulip.kodi import cacheDirectory
from tulip import kodi
from pickled import FunctionCache

cache_function = FunctionCache(cacheDirectory).cache_function
reset_cache = FunctionCache(cacheDirectory).reset_cache

ADDON_ID = 'plugin.video.newpipe'
PLUGINS_ID = 'script.module.resolveurl.pluginsgr'
PLUGINS_PATH = 'special://home/addons/{0}/resources/plugins/'.format(PLUGINS_ID)
YT_WATCH = 'https://www.youtube.com/watch?v='


def cache_duration(minutes):
    if kodi.setting('debug') == 'true':
        return 0
    return minutes
