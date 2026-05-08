#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Thread local utilities.
"""

# stdlib imports
import threading
from collections.abc import Callable
from typing import Generic
from typing import TypeVar

T = TypeVar("T")

# This cannot be optimized (much) with cython, threading.local could be monkey-patched by gevent,
# so this cannot be a cdef class
class ThreadLocalManager(threading.local, Generic[T]):

    def __init__(self, default:Callable[[], T]):
        # This is called once in each thread, the first time the object
        # is used in the thread. The super class does nothing. We use lots
        # of threads/greenlets, so save the time.
        # pylint:disable=super-init-not-called
        self.stack: list[T] = []
        self.default = default

    def push(self, info:T) -> None:
        self.stack.append(info)

    set = push  # b/c

    def pop(self) -> T|None:
        return self.stack.pop() if self.stack else None

    def get(self) -> T:
        stack = self.stack
        if not stack:
            return self.default() # Note we're not storing it!

        return self.stack[-1]
