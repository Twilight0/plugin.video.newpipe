# -*- coding: utf-8 -*-

# NewPipe Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only
# See LICENSES/GPL-3.0-only for more information.

# Minimal entry point: every action lives in resources.lib.routes,
# registered on urldispatcher via decorator (import side effect below).
from sys import argv
from urllib.parse import parse_qsl

from urldispatcher import urldispatcher

from resources.lib import routes  # noqa: F401


_STATE_PREFIX = 'np:'


def _params(query):
    """Expand the compact route state carried in Tulip's ``query`` field.

    Folder routes encode page number, search kind and channel tab as one
    URL-encoded ``np:...`` payload (built by routes._state); restore its
    key/value pairs so paged routes receive real parameters.
    """
    params = dict(parse_qsl(query[1:]))
    state = params.get('query', '')
    if state.startswith(_STATE_PREFIX):
        params.pop('query', None)
        params.update(dict(parse_qsl(state[len(_STATE_PREFIX):])))
    return params


def run(argv):
    params = _params(argv[2])
    urldispatcher.dispatch(params.get('action') or 'root', params)


if __name__ == '__main__':
    run(argv)
