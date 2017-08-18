#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

try:
    from pyramid.threadlocal import ThreadLocalManager
    from pyramid.threadlocal import get_current_request

    ThreadLocalManager = ThreadLocalManager
    get_current_request = get_current_request

except ImportError:
    import threading

    class ThreadLocalManager(threading.local):

        def __init__(self, default=None):
            self.stack = []
            self.default = default

        def push(self, info):
            self.stack.append(info)

        set = push  # b/c

        def pop(self):
            if self.stack:
                return self.stack.pop()

        def get(self):
            try:
                return self.stack[-1]
            except IndexError:
                return self.default()

        def clear(self):
            self.stack[:] = []

    def get_current_request():
        return None
