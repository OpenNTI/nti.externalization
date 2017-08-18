#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with various kinds of transparent proxies.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

_unwrappers = []
try:
    import zope.proxy
    _unwrappers.append(zope.proxy.removeAllProxies)
except ImportError:
    pass

try:
    import zope.container.contained
    _unwrappers.append(zope.container.contained.getProxiedObject)
except ImportError:
    pass

try:
    import Acquisition
    aq_base = getattr(Acquisition, 'aq_base')
    _unwrappers.append(aq_base)
except (ImportError, AttributeError):
    pass


def removeAllProxies(proxy):
    """
    If the object in ``proxy`` is proxied by one of the types
    of proxies known about by this module, remove all of the
    known proxies, unwrapping down to the original base object.

    This module may know about :mod:`zope.proxy`, :mod:`zope.container.contained`,
    and :mod:`Acquisition`.
    """

    fully_unwrapped_by = [False] * len(_unwrappers)

    while not all(fully_unwrapped_by):
        for i, unwrapper in enumerate(_unwrappers):
            unwrapped = unwrapper(proxy)
            if unwrapped is not proxy:
                # It changed something. reset the whole state.
                fully_unwrapped_by[:] = [False] * len(_unwrappers)
                proxy = unwrapped
            else:
                # yes, this one is completely done
                fully_unwrapped_by[i] = True
    return proxy
