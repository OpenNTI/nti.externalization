#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thread local utilities.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# stdlib imports
import threading

# This cannot be optimized (much) with cython, threading.local could be monkey-patched by gevent,
# so this cannot be a cdef class
class ThreadLocalManager(threading.local):

    def __init__(self, default):
        self.stack = []
        self.default = default

    def push(self, info):
        self.stack.append(info)

    set = push  # b/c

    def pop(self):
        if self.stack:
            return self.stack.pop()

    def get(self):
        stack = self.stack
        if not stack:
            return self.default() # Note we're not storing it!

        return self.stack[-1]
