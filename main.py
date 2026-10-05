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


def run(argv):
    params = dict(parse_qsl(argv[2][1:]))
    urldispatcher.dispatch(params.get('action') or 'root', params)


if __name__ == '__main__':
    run(argv)
