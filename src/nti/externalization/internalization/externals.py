# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
Functions for translating external object references into internal
objects.

"""



from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


# stdlib imports
try:
    from collections.abc import MutableSequence
except ImportError:
    from collections import MutableSequence


from zope import component


from nti.externalization.interfaces import IExternalReferenceResolver


__all__ = [
    'resolve_externals',
]

def resolve_externals(object_io, updating_object, externalObject,
                      registry=component, context=None):
    # Run the resolution steps on the external object
    # TODO: Document this.

    for keyPath in getattr(object_io, '__external_oids__', ()):
        # TODO: This version is very simple, generalize it
        # TODO: This check seems weird. Why do we do it this way
        # instead of getting the object and seeing if it's false?
        if keyPath not in externalObject:
            continue
        externalObjectOid = externalObject[keyPath]
        unwrap = False
        if not isinstance(externalObjectOid, MutableSequence):
            externalObjectOid = [externalObjectOid, ]
            unwrap = True

        for i in range(0, len(externalObjectOid)): # pylint:disable=consider-using-enumerate
            resolver = registry.queryMultiAdapter((updating_object, externalObjectOid[i]),
                                                  IExternalReferenceResolver)
            if resolver:
                externalObjectOid[i] = resolver.resolve(externalObjectOid[i])
        if unwrap and keyPath in externalObject:  # Only put it in if it was there to start with
            externalObject[keyPath] = externalObjectOid[0]

    for ext_key, resolver_func in getattr(object_io, '__external_resolvers__', {}).items():
        extValue = externalObject.get(ext_key)
        if not extValue:
            continue
        # classmethods and static methods are implemented with descriptors,
        # which don't work when accessed through the dictionary in this way,
        # so we special case it so instances don't have to.
        if isinstance(resolver_func, (classmethod, staticmethod)):
            resolver_func = resolver_func.__get__(None, object_io.__class__)

        try:
            extValue = resolver_func(context, externalObject, extValue)
        except TypeError:
            # instance function?
            # Note that the try/catch is still faster than
            # what we were doing to detect instance functions, which was to use
            # len(inspect.getargspec(func)[0]) == 4 by about 4,000X !
            extValue = resolver_func(object_io, context, externalObject, extValue)

        externalObject[ext_key] = extValue



from nti.externalization._compat import import_c_accel # pylint:disable=wrong-import-position,wrong-import-order
import_c_accel(globals(), 'nti.externalization.internalization._externals')
