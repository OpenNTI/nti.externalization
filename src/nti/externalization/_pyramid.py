#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extension points for connecting to Pyramid.

XXX TODO: Define get_current_request as a zope.hookable function
and let the application determine what framework to connect to.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import threading

try:
    from pyramid.threadlocal import get_current_request
except ImportError:
    def get_current_request():
        return None
else: # pragma: no cover
    get_current_request = get_current_request

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
