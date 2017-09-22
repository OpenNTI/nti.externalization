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
