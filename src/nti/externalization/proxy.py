#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with various kinds of transparent proxies.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope.dottedname import resolve as dottedname

_unwrappers = []

def _init_unwrappers():
    del _unwrappers[:]
    for funcname in (
            'zope.proxy.removeAllProxies',
            'zope.container.contained.getProxiedObject',
            'Acquisition.aq_base',
    ):
        try:
            func = dottedname.resolve(funcname)
        except ImportError: # pragma: no cover
            pass
        else:
            registerProxyUnwrapper(func)

def removeAllProxies(proxy):
    """
    If the object in *proxy* is proxied by one of the types
    of proxies known about by this module, remove all of the
    known proxies, unwrapping down to the original base object.

    This module may know about :mod:`zope.proxy`,
    :mod:`zope.container.contained`, and :mod:`Acquisition`,
    if they are installed.

    .. versionchanged:: 1.0
       The default proxy unwrappers are all optional and will only
       be registered if they can be imported.
    """

    go_again = True
    while go_again:
        for unwrapper in _unwrappers:
            unwrapped = unwrapper(proxy)
            if unwrapped is not proxy:
                proxy = unwrapped
                break
        else:
            # We didn't break. Nothing unwrapped.
            go_again = False
    return unwrapped

def registerProxyUnwrapper(func):
    """
    Register a function that can unwrap a single proxy from
    a proxied object. If there is nothing to unwrap, the function
    should return the given object.

    .. versionadded:: 1.0
       This is a provisional way to extend the unwrapping functionality
       (where speed is critical). It may not be supported in the future.
    """
    _unwrappers.append(func)

try:
    from zope.testing import cleanup
except ImportError: # pragma: no cover
    pass
else:
    cleanup.addCleanUp(_init_unwrappers)

_init_unwrappers()
