# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
# -*- coding: utf-8 -*-
"""
A cache based on the interfaces provided by an object.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from weakref import WeakSet

from zope.interface import providedBy

cache_instances = WeakSet()


class InterfaceCache(object):
    # Although having a __dict__ would be more convenient,
    # since this object is used from multiple modules,
    # Cython code is much more effective if the fields are
    # defined in the .pxd --- which translate to slots
    # in Python

    __slots__ = (
        'iface',
        'ext_all_possible_keys',
        'ext_accept_external_id',
        'ext_primitive_out_ivars',
        'modified_event_attributes',
        '__weakref__'
    )

    def __init__(self):
        self.iface = None
        self.ext_all_possible_keys = None
        self.ext_accept_external_id = None
        self.ext_primitive_out_ivars = None
        # {'attrname': InterfaceDeclaringAttrname}
        self.modified_event_attributes = {}


def cache_for_key_in_providedBy(key, provided_by): # type: (object, object) -> InterfaceCache
    # The Declaration objects returned from ``providedBy(obj)`` maintain a _v_attrs that
    # gets blown away on changes to themselves or their
    # dependents, including adding interfaces dynamically to an instance
    # (In that case, the provided object actually gets reset)
    attrs = provided_by._v_attrs # pylint:disable=protected-access
    if attrs is None:
        attrs = provided_by._v_attrs = {}

    try:
        cache = attrs[key]
    except KeyError:
        cache = InterfaceCache()
        attrs[key] = cache
        cache_instances.add(cache)

    return cache


def cache_for(externalizer, ext_self): # type: (object, object) -> InterfaceCache
    return cache_for_key_in_providedBy(type(externalizer), providedBy(ext_self))


def _cache_cleanUp(instances):
    # XXX: On PyPy (3 only?) ``list(instances)`` has been
    # seen to raise "RuntimeError: set changed size during iteration."
    # We should probably try to run a gc.collect() before iterating it.
    for x in list(instances):
        x.__init__() # pylint:disable=unnecessary-dunder-call


try:
    from zope.testing import cleanup
except ImportError: # pragma: no cover
    pass
else:
    cleanup.addCleanUp(_cache_cleanUp, args=(cache_instances,))


# pylint:disable=wrong-import-position
from nti.externalization._compat import import_c_accel
import_c_accel(globals(), 'nti.externalization.__interface_cache')
